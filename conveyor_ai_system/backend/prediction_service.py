"""Prediction Service for Conveyor Belt AI System.
Coordinates model inference, sensor telemetry extraction, condition severity mapping,
and simulated Remaining Useful Life (RUL) demonstration calculation.
"""

from datetime import datetime
import math
from typing import Any, Dict, Optional, Union
import pandas as pd

from .config import (
    TARGET_COLUMN,
    ID_COLUMN,
    OPERATING_HOURS_COLUMN,
    SEVERITY_MAP,
    MAINTENANCE_RECOMMENDATIONS,
    CLASS_DISPLAY_NAMES,
    DIGITAL_TWIN_STATUS
)
from .model_service import model_service


class PredictionService:
    def __init__(self):
        pass

    def get_remaining_useful_life(
        self,
        condition: str,
        confidence: float,
        row_number: int = 1,
        operating_hours: float = 0.0
    ) -> Dict[str, Any]:
        """Generate simulated demonstration RUL for presentation.
        CRITICAL: The current XGBoost model is a classification model and does NOT
        predict continuous degradation RUL. This function is for DEMONSTRATION ONLY
        and is clearly labeled as such. Architecture is prepared for LSTM/GRU RUL integration.
        """
        norm_cond = str(condition).strip().lower()

        # Demonstration baseline hours by condition
        base_hours_map = {
            "normal load": 184.0,       # ~7 days 16 hours
            "overload": 78.0,           # ~3 days 6 hours (high thermal & mechanical stress)
            "misalignment": 44.0,       # ~1 day 20 hours (edge friction & idler wear)
            "splice rupture": 6.0,      # Immediate shutdown / joint failure risk
            "belt tear": 4.0            # Emergency rip shutdown
        }

        base_hours = base_hours_map.get(norm_cond, 96.0)

        # Subtle dynamic variation based on row progression for presentation responsiveness
        fluctuation = (math.sin(row_number * 0.3) * 3.5) - ((1.0 - confidence) * 6.0)
        rul_hours = max(2.0, round(base_hours + fluctuation, 1))

        days = int(rul_hours // 24)
        rem_hours = int(rul_hours % 24)
        formatted_display = f"{days} DAYS {rem_hours} HOURS" if days > 0 else f"{rem_hours} HOURS"

        if rul_hours > 120:
            degradation = "LOW"
            gauge_pct = 92.0
        elif rul_hours > 50:
            degradation = "MEDIUM"
            gauge_pct = 64.0
        elif rul_hours > 15:
            degradation = "HIGH"
            gauge_pct = 35.0
        else:
            degradation = "CRITICAL"
            gauge_pct = 10.0

        recommendation = MAINTENANCE_RECOMMENDATIONS.get(norm_cond, "MONITOR")

        return {
            "rul_hours": rul_hours,
            "rul_formatted": formatted_display,
            "degradation": degradation,
            "maintenance_action": recommendation,
            "gauge_percentage": gauge_pct,
            "is_simulated": True,
            "disclaimer": "SIMULATED RUL – DEMONSTRATION ONLY (XGBoost Classifier active; awaiting LSTM/GRU RUL model)"
        }

    def process_telemetry(
        self,
        raw_row: Union[Dict[str, Any], pd.Series],
        row_number: int = 1,
        mode: str = "DEMO"
    ) -> Dict[str, Any]:
        """Extract sensor features, invoke XGBoost, compare ground truth with prediction,
        and build rich real-time telemetry packet.
        Guarantees that ground-truth Belt_Condition is NEVER fed to the model.
        """
        row_dict = raw_row.to_dict() if isinstance(raw_row, pd.Series) else dict(raw_row)

        # 1. Extract actual ground truth condition BEFORE prediction
        actual_condition = (
            str(row_dict.get(TARGET_COLUMN) or
                row_dict.get(TARGET_COLUMN.lower()) or
                row_dict.get("Label") or
                "UNKNOWN").strip()
        )

        # 2. Extract ID & Operating Hours
        row_id = int(row_dict.get(ID_COLUMN, row_number))
        operating_hours = round(float(row_dict.get(OPERATING_HOURS_COLUMN, 1248.5)), 1)

        # 3. Timestamp
        timestamp = str(row_dict.get("Timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # 4. Run model inference (model_service.predict strips Belt_Condition and ID automatically)
        model_result = model_service.predict(row_dict)
        prediction = model_result["prediction"]
        confidence_ratio = float(model_result["confidence"])
        probabilities = model_result["probabilities"]

        # 5. Evaluate accuracy on this row
        norm_pred = prediction.strip().lower()
        norm_actual = actual_condition.strip().lower()
        is_correct = (norm_actual == norm_pred) if actual_condition != "UNKNOWN" else None

        # 6. Machine condition status & alert severity
        status = SEVERITY_MAP.get(norm_pred, "WARNING")
        recommendation = MAINTENANCE_RECOMMENDATIONS.get(norm_pred, "MONITOR")

        # 7. AI Condition health index score (labeled as AI Condition classification index)
        if status == "NORMAL":
            health_score = round(92.0 + (confidence_ratio * 7.5), 1)
        elif status == "WARNING":
            health_score = round(58.0 + (confidence_ratio * 12.0), 1)
        else:  # CRITICAL
            health_score = round(15.0 + (1.0 - confidence_ratio) * 20.0, 1)
        health_score = min(99.9, max(5.0, health_score))

        # 8. Sensor values from dataset row
        sensor_data = {
            "Voltage_RMS": round(float(row_dict.get("Voltage_RMS", 415.2)), 2),
            "Irms": round(float(row_dict.get("Irms", 18.4)), 2),
            "Power_Factor": round(float(row_dict.get("Power_Factor", 0.91)), 3),
            "Phase_Angle": round(float(row_dict.get("Phase_Angle", 24.5)), 2),
            "I_THD": round(float(row_dict.get("I_THD", 3.2)), 2),
            "Vibration_X": round(float(row_dict.get("Vibration_X", 0.12)), 3),
            "Vibration_Y": round(float(row_dict.get("Vibration_Y", 0.08)), 3),
            "Vibration_Z": round(float(row_dict.get("Vibration_Z", 9.81)), 3),
            "RMS_Vibration": round(float(row_dict.get("RMS_Vibration", 2.84)), 3),
            "Peak_Acceleration": round(float(row_dict.get("Peak_Acceleration", 4.12)), 3),
            "Kurtosis": round(float(row_dict.get("Kurtosis", 3.1)), 2),
            "Skewness": round(float(row_dict.get("Skewness", 0.15)), 3),
            "Variance": round(float(row_dict.get("Variance", 0.85)), 3),
            "Peak_to_Peak": round(float(row_dict.get("Peak_to_Peak", 8.24)), 3),
            "Dominant_Frequency": round(float(row_dict.get("Dominant_Frequency", 49.8)), 1),
            "Spectral_Energy": round(float(row_dict.get("Spectral_Energy", 145.2)), 2),
            "Operating_Hours": operating_hours
        }

        # Conveyor Digital Twin dynamic mechanical telemetry
        v_rms = sensor_data["Voltage_RMS"]
        i_rms = sensor_data["Irms"]
        rms_vib = sensor_data["RMS_Vibration"]

        # Realistic physical temperatures based on load & vibration
        motor_temp = round(52.0 + (i_rms * 0.75) + (14.0 if status == "CRITICAL" else 0.0), 1)
        bearing_temp = round(48.0 + (rms_vib * 4.2) + (18.0 if norm_pred in ["splice rupture", "misalignment"] else 0.0), 1)
        gearbox_temp = round(50.0 + (i_rms * 0.42) + (10.0 if norm_pred == "overload" else 0.0), 1)

        if norm_pred == "overload":
            belt_speed = 2.92
            motor_rpm = 1430
            conveyor_load = 1480.0
            material_flow = 1890.0
            belt_tension = 58.2
        elif norm_pred == "misalignment":
            belt_speed = 3.08
            motor_rpm = 1465
            conveyor_load = 890.0
            material_flow = 1180.0
            belt_tension = 47.4
        elif norm_pred in ["splice rupture", "belt tear"]:
            belt_speed = 2.75
            motor_rpm = 1410
            conveyor_load = 920.0
            material_flow = 1200.0
            belt_tension = 62.5
        else:  # normal load
            belt_speed = round(3.20 + math.sin(row_number * 0.1) * 0.04, 2)
            motor_rpm = int(1480 + (18.4 - i_rms) * 4)
            conveyor_load = round(850.0 + (i_rms - 18.0) * 32.0, 1)
            material_flow = round(conveyor_load * 1.34, 1)
            belt_tension = round(41.5 + (i_rms - 18.0) * 0.5, 1)

        sensor_data["Motor_Temperature"] = motor_temp
        sensor_data["Bearing_Temperature"] = bearing_temp
        sensor_data["Gearbox_Temperature"] = gearbox_temp
        sensor_data["Belt_Speed"] = belt_speed
        sensor_data["Motor_RPM"] = motor_rpm
        sensor_data["Conveyor_Load"] = conveyor_load
        sensor_data["Material_Flow_Rate"] = material_flow
        sensor_data["Belt_Tension"] = belt_tension

        # 9. Simulated RUL
        rul_info = self.get_remaining_useful_life(prediction, confidence_ratio, row_number, operating_hours)

        # 10. Digital Twin visual status
        twin_info = DIGITAL_TWIN_STATUS.get(
            norm_pred,
            {"color": "#00ff9d", "label": f"{prediction.upper()} - MONITORED"}
        )

        display_name = CLASS_DISPLAY_NAMES.get(norm_pred, prediction.upper())
        actual_display_name = CLASS_DISPLAY_NAMES.get(norm_actual, actual_condition.upper())

        return {
            # Standard Section 27 fields
            "row_number": row_number,
            "row_id": row_id,
            "timestamp": timestamp,
            "operating_hours": operating_hours,
            "sensor_data": sensor_data,
            "actual_condition": actual_condition,
            "actual_display_name": actual_display_name,
            "prediction": prediction,
            "prediction_display_name": display_name,
            "confidence": round(confidence_ratio * 100, 2),
            "confidence_ratio": confidence_ratio,
            "correct": is_correct,
            "status": status,
            # Extended fields
            "probabilities": {k: round(v * 100, 2) for k, v in probabilities.items()},
            "probabilities_ratio": probabilities,
            "health_score": health_score,
            "recommendation": recommendation,
            "rul": rul_info,
            "digital_twin": twin_info,
            "mode": mode
        }


# Singleton instance
prediction_service = PredictionService()
