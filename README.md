# Intelligent Monitoring and Prediction of Conveyor Belt Joint Rupture and Damages in Iron Ore Mining Industry

> **AI-Powered Industrial SCADA Command Center & Digital Twin Monitoring System**  
> Final Year / Smart India Hackathon (SIH) Flagship Project

---

## 1. Project Overview

In continuous iron ore mining and bulk material logistics, conveyor belts represent the critical arterial transport mechanism. A sudden conveyor belt splice failure or catastrophic joint rupture can shut down mining operations, costing hundreds of thousands of dollars in downtime and presenting severe personnel hazards.

This project delivers an **end-to-end industrial AI condition monitoring and prediction web application**. It integrates real-time electrical, kinetic, and vibration sensor telemetry with a trained **XGBoost machine learning classifier** to identify conveyor operational states, predict impending joint ruptures, stream live dataset telemetry over WebSockets, compute running classification metrics, simulate degradation horizons, and prepare an extensible architecture for edge hardware (Raspberry Pi) and computer vision (YOLO).

---

## 2. Problem Statement

Conveyor belt systems in iron ore handling face severe operating stressors:
1. **Dynamic Heavy Loading**: Ore surges create massive tensile transients.
2. **Belt Splice Joint Fatigue**: Vulcanized joints fatigue over operating cycles.
3. **Tracking & Misalignment**: Off-center loading causes belt edge wear against structural frames.
4. **Catastrophic Rupture Risk**: Unmonitored splice delamination leads to catastrophic tear and total line stoppage.

Traditional monitoring relies on periodic manual inspections or simple threshold tripwires that trigger only *after* damage has occurred. This system enables **proactive, condition-based predictive monitoring** using machine learning.

---

## 3. System Architecture

```
                    CONVEYOR BELT SYSTEM
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
           Voltage        Current       Vibration (ADXL345)
          (ZMPT101B)     (SCT-013)      Temperature (DS18B20)
              │              │              │
              └──────────────┬──────────────┘
                             │
                     Raspberry Pi 4B/5
                     (Future Hardware)
                             │
                             ▼
                      FastAPI Backend
                             │
                             ▼
                   Exact Feature Validation
                             │
                             ▼
                   XGBoost ML Classifier
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         AI Condition    Confidence     Probabilities
                             │
                             ▼
                   WebSocket Distribution (/ws)
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
       Laptop 1 (Display)            Laptop 2 (Controller)
      /dashboard Command Center      /control Simulation Engine
```

---

## 4. Final Dataset Specification

- **File**: `data/synthetic_motor_fault_dataset.csv`
- **Total Rows**: `2,000 Verified Samples`
- **Total Columns**: `19 Columns`
- **Target Column**: `Belt_Condition` *(Strictly isolated and NEVER fed into the model)*
- **Identifier Column**: `ID` *(Used solely for tracking/logging, omitted from model)*
- **Operational Life Feature**: `Operating_Hours` *(Included in telemetry and feature input)*

### Dataset Columns (19)

| # | Column Name | Type | Description |
|---|-------------|------|-------------|
| 1 | `ID` | Integer | Row identifier (1 to 2000) |
| 2 | `Operating_Hours` | Float | Cumulative operational running hours |
| 3 | `Voltage_RMS` | Float | 3-Phase RMS supply voltage (V) |
| 4 | `Irms` | Float | Drive motor root-mean-square current (A) |
| 5 | `Power_Factor` | Float | Ratio of active power to apparent power |
| 6 | `Phase_Angle` | Float | Voltage-to-current phase angle (°) |
| 7 | `I_THD` | Float | Current Total Harmonic Distortion (%) |
| 8 | `Vibration_X` | Float | Radial vibration acceleration (g) |
| 9 | `Vibration_Y` | Float | Axial vibration acceleration (g) |
| 10 | `Vibration_Z` | Float | Vertical vibration acceleration (g) |
| 11 | `RMS_Vibration` | Float | Root-mean-square vibration velocity (mm/s) |
| 12 | `Peak_Acceleration` | Float | Maximum transient acceleration (g) |
| 13 | `Kurtosis` | Float | Vibration wave peakedness statistic |
| 14 | `Skewness` | Float | Asymmetry of sensor signal distribution |
| 15 | `Variance` | Float | Signal statistical variance |
| 16 | `Peak_to_Peak` | Float | Peak-to-peak vibration displacement |
| 17 | `Dominant_Frequency` | Float | Spectral FFT peak frequency (Hz) |
| 18 | `Spectral_Energy` | Float | Cumulative energy under frequency spectrum |
| 19 | `Belt_Condition` | String | Ground-truth machine condition class |

---

## 5. Four Condition Classes & Dynamic Mapping

The dataset contains **4 balanced condition classes (500 samples each)**:

| Class in Dataset | Display Name | SCADA Severity | Color Code | Prescribed Action |
|---|---|---|---|---|
| `normal load` | **NORMAL LOAD** | NORMAL | `#00ff9d` (Green) | MONITOR |
| `overload` | **OVERLOAD** | WARNING | `#f59e0b` (Amber) | INSPECT LOAD / DRIVE SYSTEM |
| `misalignment` | **MISALIGNMENT** | WARNING | `#f97316` (Orange) | INSPECT BELT ALIGNMENT |
| `splice rupture` | **SPLICE RUPTURE** | CRITICAL | `#ef4444` (Red) | IMMEDIATE INSPECTION |

### Extensible Class Support (`belt tear`)
The backend and frontend are architected so that if the dataset is updated to replace `misalignment` with `belt tear`:
- The backend automatically detects `belt tear` from the dataset.
- The UI condition status cards, probability distributions, digital twin, and maintenance protocols automatically display **BELT TEAR** without hardcoded changes.

---

## 6. Machine Learning Model Integration

- **Model File**: `models/conveyor_xgboost_model.pkl`
- **Encoder File**: `models/label_encoder.pkl`
- **Loader**: `joblib.load()` executed once at backend startup.
- **Algorithm**: Multi-Class Extreme Gradient Boosting (`XGBClassifier`) with softprob objective.

### Strict Feature Validation (`validate_features()`)
Before any inference is executed:
1. Ground-truth `Belt_Condition` is isolated and stripped.
2. Identifier `ID` and `Timestamp` are dropped.
3. Missing features are detected. If missing, a strict `FEATURE ERROR: Missing feature: <name>` is raised.
4. Input features are reordered into the exact 17-feature vector expected by the booster:
   `['Operating_Hours', 'Voltage_RMS', 'Irms', 'Power_Factor', 'Phase_Angle', 'I_THD', 'Vibration_X', 'Vibration_Y', 'Vibration_Z', 'RMS_Vibration', 'Peak_Acceleration', 'Kurtosis', 'Skewness', 'Variance', 'Peak_to_Peak', 'Dominant_Frequency', 'Spectral_Energy']`
5. Cast to numeric `float64` and passed to `model.predict()` and `model.predict_proba()`.

---

## 7. Real-Time Telemetry & Running Accuracy

During continuous dataset simulation or live row injection:
1. Each row is read sequentially from `synthetic_motor_fault_dataset.csv`.
2. Actual condition is extracted and stored.
3. Model generates prediction and confidence percentage.
4. Ground truth is compared against predicted condition: `correct = (actual == predicted)`.
5. Running accuracy is calculated dynamically:
   $$\text{Running Accuracy} = \frac{\text{Correct Predictions}}{\text{Total Predictions}} \times 100$$
6. Real-time telemetry packet is broadcast to all connected WebSocket clients (`/ws`).

---

## 8. Simulated Remaining Useful Life (RUL) Disclaimer

> [!IMPORTANT]
> **SIMULATED RUL – DEMONSTRATION ONLY**  
> The current machine learning model is an **XGBoost classification model** that identifies the operating condition. It does **NOT** forecast continuous degradation or physical remaining hours.  
> The RUL shown on the dashboard is generated by `getRemainingLife()` for interactive presentation purposes. The system architecture is prepared for future **LSTM / GRU** recurrent neural network integration trained on run-to-failure degradation trajectories.

---

## 9. Two-Laptop Presentation Setup

The system natively supports a dual-workstation setup for project demonstrations:

- **Laptop 1 (Monitoring Display)**: Displays the **Command Center** (`http://SERVER_IP:8000/dashboard`).
- **Laptop 2 (Simulation Controller)**: Controls the **Data Simulation Engine** (`http://SERVER_IP:8000/control`).

When Laptop 2 starts the stream, adjusts speed, or injects a specific row, Laptop 1 automatically receives and renders the live update via WebSocket with zero latency.

---

## 10. Folder Structure

```
conveyor_ai_system/
├── backend/
│   ├── main.py                  # FastAPI application entrypoint & REST/WS routes
│   ├── config.py                # Configuration, class maps, paths, and sensor specs
│   ├── dataset_service.py       # CSV dataset loader & dynamic class detector
│   ├── model_service.py         # XGBoost model loader & feature validation
│   ├── prediction_service.py    # Telemetry enrichment & simulated RUL calculation
│   ├── stream_service.py        # Sequential streaming engine & running accuracy
│   └── websocket_manager.py     # Connection manager & broadcasting
│
├── frontend/
│   ├── index.html               # Entrypoint redirect
│   ├── dashboard.html           # Command Center with Digital Twin & Sensor Matrix
│   ├── control.html             # Data Simulation & Stream Control Station
│   ├── fault-analysis.html      # Diagnostic Analytics & Condition Distribution
│   ├── predictive-maintenance.html # Predictive Maintenance & RUL Advisory
│   ├── sensor-health.html       # Hardware Architecture & Transducer Specs
│   │
│   ├── css/
│   │   └── style.css            # Dark graphite SCADA industrial styling
│   │
│   └── js/
│       ├── dashboard.js         # Command center telemetry & SVG twin animations
│       ├── control.js           # Streaming controls & running accuracy tracking
│       ├── charts.js            # Chart.js multi-channel trend & bar graphs
│       └── websocket.js         # Auto-reconnecting WebSocket client
│
├── data/
│   └── synthetic_motor_fault_dataset.csv # 2,000-row, 19-column final dataset
│
├── models/
│   ├── conveyor_xgboost_model.pkl        # Trained XGBoost classifier
│   └── label_encoder.pkl                 # LabelEncoder artifact
│
├── results/                     # Diagnostic reports & outputs
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

---

## 11. Installation & Running Instructions

### Step 1: Create Virtual Environment
```bash
python -m venv venv
```

### Step 2: Activate Environment
- **Windows (PowerShell)**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt)**:
  ```cmd
  venv\Scripts\activate.bat
  ```
- **Linux / macOS**:
  ```bash
  source venv/bin/activate
  ```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Launch Backend Server
From the root workspace directory:
```bash
uvicorn conveyor_ai_system.backend.main:app --host 0.0.0.0 --port 8000
```
Or use the launcher script:
```bash
python run_server.py
```

### Step 5: Access the Web Applications
- **Local Single-Laptop Use**:
  - Command Center: `http://127.0.0.1:8000/dashboard`
  - Data Simulation: `http://127.0.0.1:8000/control`
- **Two-Laptop Demonstration**:
  - Laptop 1 (Display): `http://<SERVER_IP>:8000/dashboard`
  - Laptop 2 (Control): `http://<SERVER_IP>:8000/control`

---

## 12. Future Hardware & AI Roadmap

### Raspberry Pi 4B/5 Hardware Ingestion
Transducers (`ADXL345`, `DS18B20`, `ZMPT101B`, `SCT-013`, `MCP3208`) sample vibration, voltage, and current on the physical belt structure. A lightweight client daemon on the Raspberry Pi computes windowed RMS/FFT statistics and sends HTTP POST payloads to `/api/inject`.

### Computer Vision (YOLO) Integration
An optical line-scan camera mounted over the belt flight captures surface video. A future YOLO model detects mechanical rips, tears, and splice separation in real time. The predictions fuse with the XGBoost sensor model to generate a **Combined AI Condition Index**.

### LSTM / GRU Degradation Model
By tracking historical operating hours and vibration trend escalation, a recurrent neural network will replace the simulated RUL engine to provide continuous physical remaining hours before joint failure.
