"""Streamlit Community Cloud entry point: the competition dashboard on a committed snapshot of the last full run.

The snapshot (deploy/dashboard_data/) holds only the dashboard's JSON/CSV outputs from the 2026-10-18 full run on
NASA C-MAPSS (simulated engines): predictions, decisions, work orders and audit logs. No raw NASA data, no models.
Locally, `python -m sentinelloop dashboard` reads the live artifacts/ folder instead.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.argv = [sys.argv[0], "--", "--out-dir", str(ROOT / "deploy" / "dashboard_data"),
            "--experiments-dir", str(ROOT / "experiments" / "results")]

from sentinelloop import dashboard  # noqa: E402

dashboard.main()
