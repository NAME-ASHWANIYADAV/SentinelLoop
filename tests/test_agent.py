import pytest

from sentinelloop import agent

THR = agent.Thresholds(t_critical=10, t_high=25, t_medium=50, max_width=60, quality_max_imputed_frac=0.2)


def obs(**kw):
    base = dict(unit=1, cycle=100, rul_point=80.0, rul_lower=60.0, rul_upper=100.0, anomaly_flag=False,
                anomaly_score=0.0, drift_flag=False, imputed_frac=0.0, missing_sensors=0, model_version="v1")
    base.update(kw)
    return agent.Observation(**base)


def test_severity_is_driven_by_the_interval_lower_bound():
    assert agent.triage(obs(rul_lower=5.0), THR).severity == "CRITICAL"
    assert agent.triage(obs(rul_lower=20.0), THR).severity == "HIGH"
    assert agent.triage(obs(rul_lower=40.0), THR).severity == "MEDIUM"
    assert agent.triage(obs(rul_lower=70.0), THR).severity == "NONE"


def test_point_estimate_alone_does_not_trigger_an_order():
    d = agent.triage(obs(rul_point=8.0, rul_lower=30.0, rul_upper=60.0), THR)
    assert d.severity == "MEDIUM"


def test_sustained_anomaly_without_low_rul_gives_watch():
    d = agent.triage(obs(anomaly_flag=True, rul_lower=70.0), THR)
    assert d.severity == "WATCH"
    assert "R_ANOMALY_WATCH" in d.rules_fired


def test_wide_interval_escalates_as_insufficient_evidence():
    d = agent.triage(obs(rul_lower=5.0, rul_upper=120.0), THR)
    assert d.escalate_to_human and "insufficient_evidence" in d.escalation_reasons


def test_bad_input_quality_escalates_and_never_issues_a_confident_order():
    d = agent.triage(obs(rul_lower=5.0, imputed_frac=0.5), THR)
    assert d.escalate_to_human and "data_quality" in d.escalation_reasons
    assert d.action == "INSPECT"


def test_drift_active_escalates_high_and_critical_decisions_only():
    assert "drift_active" in agent.triage(obs(rul_lower=20.0, drift_flag=True), THR).escalation_reasons
    assert not agent.triage(obs(rul_lower=70.0, drift_flag=True), THR).escalate_to_human


def test_conflicting_evidence_escalates():
    d = agent.triage(obs(anomaly_flag=True, rul_point=120.0, rul_lower=110.0, rul_upper=125.0), THR)
    assert d.escalate_to_human and "conflicting_evidence" in d.escalation_reasons


def test_decision_records_inputs_thresholds_and_rules_for_audit():
    d = agent.triage(obs(rul_lower=5.0), THR)
    rec = d.to_record()
    assert rec["inputs"]["rul_lower"] == 5.0 and rec["thresholds"]["t_critical"] == 10
    assert "R_CRITICAL" in rec["rules_fired"] and rec["model_version"] == "v1"


def test_severity_is_monotone_in_lower_bound():
    order = {"NONE": 0, "WATCH": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    prev = 5
    for lb in [1, 9, 10, 11, 24, 25, 26, 49, 50, 51, 100]:
        s = order[agent.triage(obs(rul_lower=float(lb), rul_upper=float(lb) + 20), THR).severity]
        assert s <= prev
        prev = s


def test_work_order_book_keeps_one_open_order_per_unit_and_upgrades():
    book = agent.WorkOrderBook()
    d1 = agent.triage(obs(rul_lower=20.0), THR)       # HIGH
    d2 = agent.triage(obs(rul_lower=18.0, cycle=101), THR)  # HIGH again -> no new order
    d3 = agent.triage(obs(rul_lower=5.0, cycle=102), THR)   # CRITICAL -> upgrade
    e1 = book.apply(d1)
    e2 = book.apply(d2)
    e3 = book.apply(d3)
    assert e1["event"] == "created" and e2["event"] == "unchanged" and e3["event"] == "upgraded"
    assert len(book.open_orders()) == 1 and book.open_orders()[0]["severity"] == "CRITICAL"


def test_watch_and_none_do_not_create_work_orders():
    book = agent.WorkOrderBook()
    assert book.apply(agent.triage(obs(rul_lower=70.0), THR))["event"] == "none"
    assert book.apply(agent.triage(obs(anomaly_flag=True, rul_lower=70.0), THR))["event"] == "none"
    assert book.open_orders() == []


def test_escalated_decision_creates_an_inspection_order_not_a_maintenance_order():
    book = agent.WorkOrderBook()
    e = book.apply(agent.triage(obs(rul_lower=5.0, imputed_frac=0.9), THR))
    assert e["event"] == "created" and e["order"]["type"] == "INSPECTION"


def test_work_order_carries_actionable_content():
    book = agent.WorkOrderBook()
    d = agent.triage(obs(rul_lower=8.0, rul_point=15.0, rul_upper=30.0, cycle=200, top_sensors=["s4_rm", "s11"]), THR)
    e = book.apply(d)
    o = e["order"]
    assert o["action"] == "STOP_AND_REPAIR" and o["type"] == "MAINTENANCE"
    assert o["rul_point"] == 15.0 and o["rul_lower"] == 8.0 and o["rul_upper"] == 30.0
    assert o["due_by_cycle"] == 208                       # created_cycle + lower bound
    assert o["top_sensors"] == ["s4_rm", "s11"] and o["ts"]
    d2 = agent.triage(obs(rul_lower=5.0, rul_point=9.0, rul_upper=20.0, cycle=203, top_sensors=["s11"]), THR)
    o2 = book.apply(d2)["order"]
    assert o2["due_by_cycle"] == 208 and o2["rul_lower"] == 5.0   # upgrade refreshes the interval, keeps the earlier due-by
    assert book.close(1, cycle=210)["status"] == "CLOSED" and book.open_orders() == []
