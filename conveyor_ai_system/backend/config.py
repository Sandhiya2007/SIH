"""Configuration module for Conveyor Belt AI Monitoring System.
Contains file paths, class mappings, severity categories, sensor metadata,
and network configuration.
"""

from pathlib import Path
import os
import socket

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"
FRONTEND_DIR = BASE_DIR / "frontend"

# Primary file paths
DATASET_PATH = DATA_DIR / "synthetic_motor_fault_dataset.csv"
MODEL_PATH = MODELS_DIR / "conveyor_xgboost_model.pkl"
LABEL_ENCODER_PATH = MODELS_DIR / "label_encoder.pkl"

# Dataset Columns Configuration
TARGET_COLUMN = "Belt_Condition"
ID_COLUMN = "ID"
OPERATING_HOURS_COLUMN = "Operating_Hours"

# Non-feature columns that MUST NOT be fed to model
NON_FEATURE_COLUMNS = [ID_COLUMN, TARGET_COLUMN]

# Network & Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))


def get_lan_ip() -> str:
    """Retrieve host local network IP for 2-laptop connection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


LAN_IP = get_lan_ip()

# Default 4 classes present in current dataset
# System dynamically extracts actual classes from dataset/encoder
DEFAULT_CLASSES = [
    "normal load",
    "overload",
    "misalignment",
    "splice rupture"
]

# Configurable Class Display Names (Supports dynamic replacement if dataset uses "belt tear")
CLASS_DISPLAY_NAMES = {
    "normal load": "NORMAL LOAD",
    "overload": "OVERLOAD",
    "misalignment": "MISALIGNMENT",
    "splice rupture": "SPLICE RUPTURE",
    "belt tear": "BELT TEAR"
}

# Alert Severity Mapping
SEVERITY_MAP = {
    "normal load": "NORMAL",
    "overload": "WARNING",
    "misalignment": "WARNING",
    "splice rupture": "CRITICAL",
    "belt tear": "CRITICAL"
}

# SCADA Severity Colors
SEVERITY_COLORS = {
    "NORMAL": "#00ff9d",   # Green
    "WARNING": "#f59e0b",  # Amber
    "CRITICAL": "#ef4444"  # Red
}

# Rule-Based Condition Maintenance Recommendations (Clearly noted as rule-based recommendations)
MAINTENANCE_RECOMMENDATIONS = {
    "normal load": "MONITOR",
    "overload": "INSPECT LOAD / DRIVE SYSTEM",
    "misalignment": "INSPECT BELT ALIGNMENT",
    "splice rupture": "IMMEDIATE INSPECTION",
    "belt tear": "IMMEDIATE INSPECTION"
}

# Digital Twin Status & Visual State
DIGITAL_TWIN_STATUS = {
    "normal load": {"color": "#00ff9d", "label": "NORMAL LOAD - NOMINAL OPERATION"},
    "overload": {"color": "#f59e0b", "label": "OVERLOAD - EXCESS CONVEYOR TONNAGE"},
    "misalignment": {"color": "#f97316", "label": "MISALIGNMENT - BELT TRACKING DRIFT"},
    "splice rupture": {"color": "#ef4444", "label": "SPLICE RUPTURE - JOINT FAILURE"},
    "belt tear": {"color": "#ef4444", "label": "BELT TEAR - CRITICAL SURFACE DAMAGE"}
}

# Sensor Hardware Specifications for Raspberry Pi Architecture
SENSOR_SPECS = {
    "ZMPT101B": {
        "name": "ZMPT101B Precision Voltage Transformer",
        "parameter": "Voltage RMS",
        "unit": "V",
        "bus": "MCP3208 Analog CH0",
        "nominal_range": "380 - 440 V",
        "sample_rate": "1000 Hz",
        "description": "High-accuracy micro-voltage transformer module for 3-phase industrial supply monitoring"
    },
    "SCT-013": {
        "name": "SCT-013-000 Non-Invasive Current Transformer",
        "parameter": "Current RMS (Irms)",
        "unit": "A",
        "bus": "MCP3208 Analog CH1",
        "nominal_range": "10 - 30 A",
        "sample_rate": "1000 Hz",
        "description": "Split-core CT measuring AC current draw on conveyor drive motor line"
    },
    "ADXL345": {
        "name": "ADXL345 3-Axis Digital Accelerometer",
        "parameter": "Tri-Axial Vibration (X, Y, Z)",
        "unit": "mm/s, g",
        "bus": "I2C 0x53",
        "nominal_range": "±16g (13-bit)",
        "sample_rate": "3200 Hz",
        "description": "High resolution accelerometer placed on drive bearing housing for joint rupture & vibration diagnostics"
    },
    "DS18B20": {
        "name": "DS18B20 Digital Temperature Sensor",
        "parameter": "Bearing & Motor Temp",
        "unit": "°C",
        "bus": "1-Wire GPIO4",
        "nominal_range": "-55 to +125 °C",
        "sample_rate": "1 Hz",
        "description": "Waterproof digital thermal probe measuring bearing housing and drive gearbox temperatures"
    },
    "MCP3208": {
        "name": "MCP3208 12-Bit 8-Channel SPI ADC",
        "parameter": "Analog Signal Acquisition",
        "unit": "Counts / V",
        "bus": "SPI0 CS0",
        "nominal_range": "0 - 3.3 V",
        "sample_rate": "100 ksps max",
        "description": "Precision analog-to-digital converter interface between industrial transducers and host processor"
    }
}
