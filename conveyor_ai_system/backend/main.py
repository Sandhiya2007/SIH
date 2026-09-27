"""FastAPI Application Main Entrypoint.
Conveyor Belt AI System Backend Server.
Provides RESTful APIs, WebSocket streaming, and static frontend hosting.
"""

from contextlib import asynccontextmanager
from datetime import datetime
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import FRONTEND_DIR, HOST, PORT, LAN_IP, SENSOR_SPECS
from .dataset_service import dataset_service
from .model_service import model_service
from .stream_service import stream_service
from .websocket_manager import ws_manager

logger = logging.getLogger("conveyor_ai.main")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: startup and shutdown."""
    logger.info("=" * 65)
    logger.info("  CONVEYOR BELT AI INDUSTRIAL MONITORING SYSTEM")
    logger.info(f"  Local Dashboard:    http://localhost:{PORT}/dashboard")
    logger.info(f"  Laptop 2 Control:   http://{LAN_IP}:{PORT}/control")
    logger.info(f"  Dataset:            {dataset_service.dataset_path.name} ({dataset_service.total_rows} rows)")
    logger.info(f"  Model Loaded:       {model_service.is_loaded}")
    logger.info(f"  Detected Classes:   {dataset_service.detected_classes}")
    logger.info("=" * 65)
    yield
    stream_service.stop_stream()
    logger.info("Conveyor AI System backend shutdown completed.")


app = FastAPI(
    title="Intelligent Conveyor Belt AI Monitoring API",
    description="Real-time condition monitoring, joint rupture detection, and predictive maintenance.",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Middleware for Two-Laptop setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")


# ----------------------------------------------------
# Request / Response Schemas
# ----------------------------------------------------
class StreamStartRequest(BaseModel):
    start_row: Optional[int] = Field(default=1, ge=1)
    end_row: Optional[int] = Field(default=2000, ge=1)
    speed: Optional[float] = Field(default=2.0, ge=0.2)


class InjectRowRequest(BaseModel):
    row_number: int = Field(..., ge=1)


# ----------------------------------------------------
# Frontend Page Routes
# ----------------------------------------------------
@app.get("/", response_class=FileResponse)
async def serve_root():
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/dashboard", response_class=FileResponse)
async def serve_dashboard():
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/control", response_class=FileResponse)
async def serve_control():
    return FileResponse(FRONTEND_DIR / "control.html")


@app.get("/simulation", response_class=FileResponse)
async def serve_simulation():
    return FileResponse(FRONTEND_DIR / "control.html")


@app.get("/fault-analysis", response_class=FileResponse)
async def serve_fault_analysis():
    return FileResponse(FRONTEND_DIR / "fault-analysis.html")


@app.get("/predictive-maintenance", response_class=FileResponse)
async def serve_predictive_maintenance():
    return FileResponse(FRONTEND_DIR / "predictive-maintenance.html")


@app.get("/sensor-health", response_class=FileResponse)
async def serve_sensor_health():
    return FileResponse(FRONTEND_DIR / "sensor-health.html")


# ----------------------------------------------------
# REST API Endpoints (Section 28)
# ----------------------------------------------------
@app.get("/api/health")
async def get_health():
    """Health check endpoint."""
    is_healthy = model_service.is_loaded and dataset_service.is_loaded
    return {
        "status": "healthy" if is_healthy else "degraded",
        "model_loaded": model_service.is_loaded,
        "model_error": model_service.load_error,
        "dataset_loaded": dataset_service.is_loaded,
        "dataset_error": dataset_service.load_error,
        "total_rows": dataset_service.total_rows,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/status")
async def get_system_status():
    """Overall system configuration, network IP, model, and active stream status."""
    return {
        "title": "Intelligent Conveyor Belt AI Monitoring",
        "project": "Monitoring & Prediction of Conveyor Belt Joint Rupture and Damages",
        "industry": "Iron Ore Mining Industry",
        "conveyor_id": "LINE-01-PRIMARY-FEEDER",
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "host": HOST,
        "port": PORT,
        "lan_ip": LAN_IP,
        "dashboard_url": f"http://{LAN_IP}:{PORT}/dashboard",
        "control_url": f"http://{LAN_IP}:{PORT}/control",
        "model_status": {
            "loaded": model_service.is_loaded,
            "classes_count": len(model_service.classes),
            "classes": model_service.classes,
            "feature_count": len(model_service.feature_columns),
            "feature_columns": model_service.feature_columns,
            "algorithm": "XGBoost Classifier"
        },
        "dataset_status": {
            "loaded": dataset_service.is_loaded,
            "filename": dataset_service.dataset_path.name,
            "total_rows": dataset_service.total_rows,
            "detected_classes": dataset_service.detected_classes,
            "class_counts": dataset_service.class_counts
        },
        "stream_status": stream_service.get_stream_status(),
        "connected_ws_clients": len(ws_manager.active_connections)
    }


@app.get("/api/dataset/info")
async def get_dataset_info():
    """Get CSV dataset statistics and dynamically detected target classes."""
    return dataset_service.get_info()


@app.post("/api/predict")
async def predict_sample(payload: Dict[str, Any]):
    """Direct feature vector prediction using the trained XGBoost model.
    Validates features, rejects missing features with FEATURE ERROR, and performs inference.
    """
    try:
        result = model_service.predict(payload)
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/inject")
async def inject_sensor_data(payload: Dict[str, Any]):
    """Inject raw or partial sensor data (Raspberry Pi integration ready)."""
    try:
        packet = await stream_service.inject_sensor_payload(payload)
        return {
            "status": "success",
            "message": "Telemetry received and broadcasted to monitoring displays.",
            "packet": packet
        }
    except Exception as e:
        logger.error(f"Error injecting telemetry: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/stream/start")
async def start_data_stream(req: Optional[StreamStartRequest] = None):
    """Start continuous dataset streaming from Laptop 2 or UI controls."""
    try:
        start_row = req.start_row if req else 1
        end_row = req.end_row if req else dataset_service.total_rows
        speed = req.speed if req else 2.0
        stream_service.start_stream(start_row=start_row, end_row=end_row, speed=speed)
        return {
            "status": "success",
            "message": "Data stream started.",
            "stream_status": stream_service.get_stream_status()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/stream/pause")
async def pause_data_stream():
    """Pause continuous dataset streaming."""
    stream_service.pause_stream()
    return {
        "status": "success",
        "message": "Data stream paused.",
        "stream_status": stream_service.get_stream_status()
    }


@app.post("/api/stream/stop")
async def stop_data_stream():
    """Stop continuous dataset streaming."""
    stream_service.stop_stream()
    return {
        "status": "success",
        "message": "Data stream stopped.",
        "stream_status": stream_service.get_stream_status()
    }


@app.post("/api/stream/reset")
async def reset_data_stream():
    """Reset stream pointer to row 1 and clear running accuracy / history."""
    stream_service.reset_stream()
    return {
        "status": "success",
        "message": "Data stream and metrics reset.",
        "stream_status": stream_service.get_stream_status()
    }


@app.post("/api/stream/inject-row")
async def inject_row(req: InjectRowRequest):
    """Inject single dataset row manually by row number."""
    try:
        packet = await stream_service.inject_row(req.row_number)
        return {
            "status": "success",
            "row_number": req.row_number,
            "packet": packet
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/stream/status")
async def get_stream_status():
    """Get current streaming engine status."""
    return stream_service.get_stream_status()


@app.get("/api/fault-summary")
async def get_fault_summary():
    """Get cumulative condition counts, running accuracy, and recent event logs."""
    return stream_service.get_fault_summary()


@app.get("/api/sensor-status")
async def get_sensor_status():
    """Get sensor hardware architecture specifications and connection statuses."""
    sensors_response = []
    for sensor_id, spec in SENSOR_SPECS.items():
        sensors_response.append({
            "id": sensor_id,
            "name": spec["name"],
            "parameter": spec["parameter"],
            "unit": spec["unit"],
            "bus": spec["bus"],
            "nominal_range": spec["nominal_range"],
            "sample_rate": spec["sample_rate"],
            "description": spec["description"],
            "status": "DEMO / DATASET MODE",
            "signal_quality": "99.2%",
            "last_update": "Synchronized with Dataset Stream"
        })
    return {
        "bus_controller": "Raspberry Pi 4B Industrial Carrier (Future Hardware)",
        "mode": stream_service.mode,
        "mode_label": "DEMO / DATASET MODE" if stream_service.mode == "DEMO" else "LIVE HARDWARE STREAM",
        "note": "Currently operating in DEMO / DATASET SIMULATION mode using synthetic_motor_fault_dataset.csv. Physical sensors will connect via Raspberry Pi SPI/I2C/GPIO.",
        "sensors": sensors_response
    }


# ----------------------------------------------------
# WebSocket Real-Time Telemetry Route (Section 27)
# ----------------------------------------------------
@app.websocket("/ws")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """Real-time bi-directional telemetry broadcast channel."""
    await ws_manager.connect(websocket)
    try:
        # Immediately send current state on connect
        initial_packet = {
            "type": "CONNECTION_ESTABLISHED",
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dataset_info": dataset_service.get_info(),
            "stream_status": stream_service.get_stream_status()
        }
        await websocket.send_json(initial_packet)

        while True:
            text_data = await websocket.receive_text()
            logger.debug(f"Received message from client: {text_data}")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection exception: {e}")
        await ws_manager.disconnect(websocket)
