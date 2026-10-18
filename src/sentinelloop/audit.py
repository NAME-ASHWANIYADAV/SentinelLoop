"""Append-only, hash-chained audit log of agent decisions, plus a replay check that re-derives every
decision from its stored inputs and thresholds."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path

from . import agent

GENESIS = "0" * 64


def _canonical(rec: dict) -> bytes:
    return json.dumps({k: v for k, v in rec.items() if k != "hash"}, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _hash(rec: dict) -> str:
    return hashlib.sha256(_canonical(rec)).hexdigest()


class AuditLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.last_hash = GENESIS
        self.n = 0
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self.last_hash = rec["hash"]
                    self.n += 1

    def append(self, decision: agent.Decision, extra: dict | None = None) -> dict:
        rec = decision.to_record()
        if extra:
            rec["extra"] = extra
        rec["seq"] = self.n
        rec["ts"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
        rec["prev_hash"] = self.last_hash
        rec["hash"] = _hash(rec)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
        self.last_hash = rec["hash"]
        self.n += 1
        return rec

    def records(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def verify_chain(self) -> bool:
        prev = GENESIS
        for rec in self.records():
            if rec.get("prev_hash") != prev or _hash(rec) != rec.get("hash"):
                return False
            prev = rec["hash"]
        return True


def audit_logs(out_dir: str | Path) -> list[Path]:
    """All per-subset audit logs under <out_dir>/audit (plus a legacy decisions.jsonl if present)."""
    d = Path(out_dir) / "audit"
    if not d.exists():
        return []
    return sorted(p for p in d.glob("decisions*.jsonl"))


def replay_check_all(out_dir: str | Path) -> dict:
    reports = {p.name: replay_check(p) for p in audit_logs(out_dir)}
    return {"n": sum(r["n"] for r in reports.values()), "mismatches": sum(r["mismatches"] for r in reports.values()),
            "chain_valid": all(r["chain_valid"] for r in reports.values()) if reports else False, "logs": reports}


def replay_check(path: str | Path) -> dict:
    """Re-run the agent on every stored record; report mismatches."""
    log = AuditLog(path)
    mismatches = 0
    details = []
    recs = log.records()
    for rec in recs:
        obs = agent.Observation(model_version=rec["model_version"], subset=rec.get("subset", ""), **rec["inputs"])
        thr = agent.Thresholds(**rec["thresholds"])
        d = agent.triage(obs, thr)
        same = (d.severity == rec["severity"] and d.action == rec["action"] and d.escalate_to_human == rec["escalate_to_human"]
                and d.rules_fired == rec["rules_fired"])
        if not same:
            mismatches += 1
            details.append({"seq": rec["seq"], "stored": rec["severity"], "rederived": d.severity})
    return {"n": len(recs), "mismatches": mismatches, "chain_valid": log.verify_chain(), "details": details[:20]}
