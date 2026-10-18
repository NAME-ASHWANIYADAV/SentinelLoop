"""E6 — Auditability (hypothesis H6): re-derive every decision from every per-subset audit log; tamper-detect."""
from __future__ import annotations

import json
import shutil

from common import ARTIFACTS, RESULTS, log, save
from sentinelloop import audit


def main():
    logs = audit.audit_logs(ARTIFACTS)
    rep = audit.replay_check_all(ARTIFACTS)
    tmp = RESULTS / "e6_audit_check"
    tmp.mkdir(parents=True, exist_ok=True)
    tampered_results = {}
    for p in logs:
        copy = tmp / f"tampered_{p.name}"
        shutil.copy(p, copy)
        lines = copy.read_text(encoding="utf-8").splitlines()
        rec = json.loads(lines[len(lines) // 2])
        rec["severity"] = "NONE" if rec["severity"] != "NONE" else "CRITICAL"
        lines[len(lines) // 2] = json.dumps(rec)
        copy.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tampered_results[p.name] = {"chain_valid_after_tamper": audit.AuditLog(copy).verify_chain(), "rederivation_mismatches_after_tamper": audit.replay_check(copy)["mismatches"]}
    orders = []
    for sub in sorted(p.name for p in ARTIFACTS.iterdir() if p.is_dir() and (p / "work_orders.json").exists()):
        orders += json.loads((ARTIFACTS / sub / "work_orders.json").read_text(encoding="utf-8"))
    orders_traceable = all(o.get("model_version") and o.get("severity") for o in orders)
    tamper_detected = all(not v["chain_valid_after_tamper"] for v in tampered_results.values()) if tampered_results else False
    ok = rep["mismatches"] == 0 and rep["chain_valid"] and tamper_detected and orders_traceable and rep["n"] > 0
    conclusion = (f"H6: {rep['n']} decisions across {len(logs)} subset logs re-derived with {rep['mismatches']} mismatches; chains valid {rep['chain_valid']}; "
                  f"tampering detected in every log {tamper_detected}; {len(orders)} work orders carry model version and severity: {orders_traceable}. {'SUPPORTED' if ok else 'NOT SUPPORTED'}.")
    readme = "# E6 — Auditability (H6)\n\n" + conclusion + "\n\n```json\n" + json.dumps({"per_log": rep["logs"], "tampered": tampered_results, "n_orders": len(orders)}, indent=1) + "\n```\n"
    save("e6_audit_check", {"hypothesis": "H6", "replay": {k: v for k, v in rep.items() if k != "logs"}, "per_log": rep["logs"], "tampered": tampered_results, "n_orders": len(orders), "orders_traceable": orders_traceable, "conclusion": conclusion}, readme)
    log(conclusion)


if __name__ == "__main__":
    main()
