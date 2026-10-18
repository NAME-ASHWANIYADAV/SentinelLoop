"""Start the API on the local DEMO site (artifacts_demo/console/demo.db) on 127.0.0.1:8080.

Reads the demo audit key from artifacts_demo/demo_key.env (created with the demo site, git-ignored).
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
env = dict(os.environ)
for line in (ROOT / "artifacts_demo" / "demo_key.env").read_text(encoding="utf-8").splitlines():
    k, _, v = line.partition("=")
    if k:
        env[k.strip()] = v.strip()
env["PYTHONPATH"] = str(ROOT / "src")
sys.exit(subprocess.call([sys.executable, "-m", "sentinelloop.app.admin", "serve", "--db", str(ROOT / "artifacts_demo" / "console" / "demo.db"),
                          "--port", "8080", "--policy", str(ROOT / "configs" / "platform.yaml")], cwd=str(ROOT), env=env))
