import json

from sentinelloop import agent, audit

THR = agent.Thresholds(t_critical=10, t_high=25, t_medium=50, max_width=60, quality_max_imputed_frac=0.2)


def _decision(unit, cycle, lb):
    o = agent.Observation(unit=unit, cycle=cycle, rul_point=lb + 10, rul_lower=lb, rul_upper=lb + 30, anomaly_flag=False,
                          anomaly_score=0.0, drift_flag=False, imputed_frac=0.0, missing_sensors=0, model_version="run-abc")
    return agent.triage(o, THR)


def test_audit_log_chains_hashes_and_verifies(tmp_path):
    log = audit.AuditLog(tmp_path / "decisions.jsonl")
    for i, lb in enumerate([60.0, 40.0, 20.0, 5.0]):
        log.append(_decision(1, 100 + i, lb))
    assert log.verify_chain() is True
    lines = (tmp_path / "decisions.jsonl").read_text().splitlines()
    assert len(lines) == 4
    first = json.loads(lines[0])
    assert first["prev_hash"] == audit.GENESIS and len(first["hash"]) == 64


def test_tampering_breaks_the_chain(tmp_path):
    p = tmp_path / "decisions.jsonl"
    log = audit.AuditLog(p)
    for lb in [60.0, 20.0, 5.0]:
        log.append(_decision(2, 1, lb))
    lines = p.read_text().splitlines()
    rec = json.loads(lines[1])
    rec["severity"] = "NONE"
    lines[1] = json.dumps(rec)
    p.write_text("\n".join(lines) + "\n")
    assert audit.AuditLog(p).verify_chain() is False


def test_every_decision_can_be_rederived_from_its_record(tmp_path):
    log = audit.AuditLog(tmp_path / "decisions.jsonl")
    for lb in [60.0, 20.0, 5.0]:
        log.append(_decision(3, 7, lb))
    report = audit.replay_check(tmp_path / "decisions.jsonl")
    assert report["n"] == 3 and report["mismatches"] == 0
