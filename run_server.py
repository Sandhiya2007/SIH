"""Quick Launcher for Conveyor Belt AI System.
Can be executed directly from VS Code or terminal:
    python run_server.py
"""

import sys
from pathlib import Path
import uvicorn

# Ensure package root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR / "conveyor_ai_system"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

if __name__ == "__main__":
    from conveyor_ai_system.backend.config import HOST, PORT, LAN_IP
    print("=" * 70)
    print("  CONVEYOR BELT AI INDUSTRIAL MONITORING SYSTEM")
    print("=" * 70)
    print(f"  Local Dashboard:    http://localhost:{PORT}")
    print(f"  LAN Access:         http://{LAN_IP}:{PORT}")
    print(f"  Laptop 2 Control:   http://{LAN_IP}:{PORT}/control")
    print(f"  Fault Analysis:     http://localhost:{PORT}/fault-analysis")
    print(f"  Predictive Maint:   http://localhost:{PORT}/predictive-maintenance")
    print(f"  Sensor Health:      http://localhost:{PORT}/sensor-health")
    print("=" * 70)
    uvicorn.run("conveyor_ai_system.backend.main:app", host=HOST, port=PORT, reload=False)
