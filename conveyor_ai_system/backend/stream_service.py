"""Stream Service for Conveyor Belt AI System.
Manages continuous dataset streaming, row-by-row prediction,
running accuracy calculation, and real-time WebSocket distribution.
"""

import asyncio
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
import pandas as pd

from .config import SEVERITY_MAP
from .dataset_service import dataset_service
from .prediction_service import prediction_service
from .websocket_manager import ws_manager

logger = logging.getLogger("conveyor_ai.stream_service")


class StreamService:
    def __init__(self):
        # Streaming loop state
        self.is_streaming: bool = False
        self.is_paused: bool = False
        self.current_row: int = 1  # 1-indexed
        self.start_row: int = 1
        self.end_row: int = 2000
        self.speed_seconds: float = 2.0
        self.mode: str = "DEMO"  # "DEMO" (CSV simulation) or "LIVE" (Raspberry Pi/Transducers)
        self._stream_task: Optional[asyncio.Task] = None

        # Cumulative Running Performance & Statistics (Calculated dynamically, NEVER hardcoded)
        self.total_processed: int = 0
        self.correct_predictions: int = 0
        self.incorrect_predictions: int = 0
        self.running_accuracy: float = 100.0
        self.condition_counts: Dict[str, int] = {}
        self.recent_history: List[Dict[str, Any]] = []
        self.recent_alerts: List[Dict[str, Any]] = []

        self._init_condition_counts()

    def _init_condition_counts(self):
        """Initialize condition count dictionary based on detected classes."""
        classes = dataset_service.detected_classes
        self.condition_counts = {c: 0 for c in classes}

    @property
    def total_rows(self) -> int:
        return dataset_service.total_rows

    @property
    def is_loaded(self) -> bool:
        return dataset_service.is_loaded

    @property
    def load_error(self) -> Optional[str]:
        return dataset_service.load_error

    def update_metrics(self, packet: Dict[str, Any]):
        """Update running accuracy, condition counts, history log, and alerts."""
        pred = packet["prediction"]
        is_corr = packet["correct"]
        status = packet["status"]

        self.total_processed += 1
        if pred in self.condition_counts:
            self.condition_counts[pred] += 1
        else:
            self.condition_counts[pred] = 1

        if is_corr is True:
            self.correct_predictions += 1
        elif is_corr is False:
            self.incorrect_predictions += 1

        total_eval = self.correct_predictions + self.incorrect_predictions
        if total_eval > 0:
            self.running_accuracy = round((self.correct_predictions / total_eval) * 100, 2)
        else:
            self.running_accuracy = 100.0

        # Prediction History item (stores last 100 entries)
        history_item = {
            "row": packet["row_number"],
            "row_id": packet.get("row_id", packet["row_number"]),
            "timestamp": packet["timestamp"],
            "operating_hours": packet["operating_hours"],
            "actual": packet["actual_condition"],
            "actual_display": packet["actual_display_name"],
            "predicted": pred,
            "predicted_display": packet["prediction_display_name"],
            "confidence": packet["confidence"],
            "correct": is_corr,
            "status": status
        }
        self.recent_history.insert(0, history_item)
        if len(self.recent_history) > 100:
            self.recent_history.pop()

        # Alert Event stream (stores all condition transitions & warning/critical items)
        if status in ["WARNING", "CRITICAL"] or self.total_processed == 1:
            alert_item = {
                "id": f"alert_{self.total_processed}",
                "timestamp": packet["timestamp"],
                "condition": pred,
                "display_name": packet["prediction_display_name"],
                "status": status,
                "confidence": packet["confidence"],
                "actual": packet["actual_condition"],
                "action": packet["recommendation"]
            }
            self.recent_alerts.insert(0, alert_item)
            if len(self.recent_alerts) > 50:
                self.recent_alerts.pop()

    def get_fault_summary(self) -> Dict[str, Any]:
        """Return cumulative metrics and analytics summary for Fault Analysis."""
        return {
            "total_samples": self.total_rows,
            "total_processed": self.total_processed,
            "correct_predictions": self.correct_predictions,
            "incorrect_predictions": self.incorrect_predictions,
            "running_accuracy": self.running_accuracy,
            "current_condition": self.recent_history[0]["predicted"] if self.recent_history else "normal load",
            "condition_counts": self.condition_counts,
            "dataset_distribution": dataset_service.class_counts,
            "recent_history": self.recent_history[:50],
            "recent_alerts": self.recent_alerts[:25]
        }

    async def inject_row(self, row_idx: int) -> Dict[str, Any]:
        """Manually process and broadcast a single CSV row (1-indexed)."""
        if not dataset_service.is_loaded or dataset_service.df is None:
            raise RuntimeError("Dataset is not loaded.")

        if row_idx < 1 or row_idx > self.total_rows:
            raise IndexError(f"Row {row_idx} is out of bounds (1 to {self.total_rows}).")

        self.current_row = row_idx
        row_data = dataset_service.df.iloc[row_idx - 1]
        packet = prediction_service.process_telemetry(row_data, row_number=row_idx, mode="DEMO")
        self.update_metrics(packet)

        # Attach streaming state snapshot
        packet["stream_status"] = self.get_stream_status()
        await ws_manager.broadcast(packet)
        return packet

    async def inject_sensor_payload(self, sensor_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Process external sensor telemetry (Raspberry Pi integration ready)."""
        self.mode = "LIVE"
        row_number = self.total_processed + 1
        packet = prediction_service.process_telemetry(sensor_dict, row_number=row_number, mode="LIVE")
        self.update_metrics(packet)

        packet["stream_status"] = self.get_stream_status()
        await ws_manager.broadcast(packet)
        return packet

    async def _streaming_loop(self):
        """Background continuous streaming loop reading dataset rows sequentially."""
        logger.info(
            f"Streaming engine active: rows {self.start_row} to {self.end_row} "
            f"at {self.speed_seconds}s interval."
        )
        try:
            while self.is_streaming:
                if self.is_paused:
                    await asyncio.sleep(0.5)
                    continue

                if self.current_row > self.end_row:
                    logger.info("Reached end of stream range. Looping to start row.")
                    self.current_row = self.start_row

                # Process current row
                row_data = dataset_service.df.iloc[self.current_row - 1]
                packet = prediction_service.process_telemetry(
                    row_data,
                    row_number=self.current_row,
                    mode=self.mode
                )
                self.update_metrics(packet)

                # Attach stream status
                packet["stream_status"] = self.get_stream_status()
                await ws_manager.broadcast(packet)

                # Move to next row
                self.current_row += 1
                if self.current_row > self.end_row:
                    self.current_row = self.start_row

                # Wait selected interval
                await asyncio.sleep(self.speed_seconds)

        except asyncio.CancelledError:
            logger.info("Streaming loop received cancellation signal.")
        except Exception as e:
            logger.error(f"Error in streaming loop: {e}", exc_info=True)
            self.is_streaming = False
        finally:
            self.is_streaming = False
            logger.info("Streaming loop terminated.")

    def start_stream(
        self,
        start_row: Optional[int] = None,
        end_row: Optional[int] = None,
        speed: Optional[float] = None
    ):
        """Start or resume continuous dataset streaming."""
        if not dataset_service.is_loaded or dataset_service.df is None:
            raise RuntimeError("Cannot start stream: Dataset CSV is not loaded.")

        if start_row is not None:
            self.start_row = max(1, min(start_row, self.total_rows))
            self.current_row = self.start_row
        if end_row is not None:
            self.end_row = max(self.start_row, min(end_row, self.total_rows))
        else:
            self.end_row = self.total_rows
        if speed is not None:
            self.speed_seconds = max(0.2, float(speed))

        self.is_paused = False
        self.mode = "DEMO"

        if not self.is_streaming:
            self.is_streaming = True
            loop = asyncio.get_event_loop()
            self._stream_task = loop.create_task(self._streaming_loop())
            logger.info("Background streaming task created.")

    def pause_stream(self):
        """Pause continuous streaming."""
        self.is_paused = True
        logger.info("Streaming paused.")

    def stop_stream(self):
        """Stop streaming loop and cancel task."""
        self.is_streaming = False
        self.is_paused = False
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
        logger.info("Streaming stopped.")

    def reset_stream(self):
        """Reset streaming pointer, metrics, and history."""
        self.stop_stream()
        self.current_row = 1
        self.start_row = 1
        self.end_row = self.total_rows
        self.total_processed = 0
        self.correct_predictions = 0
        self.incorrect_predictions = 0
        self.running_accuracy = 100.0
        self.recent_history.clear()
        self.recent_alerts.clear()
        self._init_condition_counts()
        logger.info("Streaming engine and running accuracy reset to initial state.")

    def get_stream_status(self) -> Dict[str, Any]:
        """Return streaming engine snapshot."""
        progress_pct = round((self.current_row / max(1, self.total_rows)) * 100, 2)
        return {
            "is_streaming": self.is_streaming,
            "is_paused": self.is_paused,
            "current_row": self.current_row,
            "start_row": self.start_row,
            "end_row": self.end_row,
            "total_rows": self.total_rows,
            "progress_percentage": progress_pct,
            "speed_seconds": self.speed_seconds,
            "mode": self.mode,
            "active_mode_label": "DATASET SIMULATION ACTIVE" if self.mode == "DEMO" else "LIVE SENSOR STREAM",
            "total_processed": self.total_processed,
            "correct_predictions": self.correct_predictions,
            "incorrect_predictions": self.incorrect_predictions,
            "running_accuracy": self.running_accuracy
        }


# Singleton instance
stream_service = StreamService()
