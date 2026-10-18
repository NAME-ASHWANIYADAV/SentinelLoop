"""Maintenance resources: technicians with skills, their shifts, spare parts with stock, lead times and known deliveries.

The scheduler only uses what is recorded here: a technician without a shift has no capacity, a part without a record
cannot be used, a delivery without an ETA does not exist. Every change is audited.
"""
from __future__ import annotations

import json

from . import auditlog
from .timeutil import iso, now_iso, parse_ts


class ResourceError(ValueError):
    pass


def _audit(db, c, actor, action, entity, entity_id, payload):
    auditlog.append(c, actor=actor, action=action, entity=entity, entity_id=entity_id, payload=payload, key=db.audit_key, key_id=db.audit_key_id)


def upsert_technician(db, tech_id: str, display_name: str, site_id: str, skills: list[str], actor: str, active: bool = True):
    if not skills:
        raise ResourceError("a technician needs at least one skill")
    with db.tx() as c:
        if c.execute("SELECT 1 FROM sites WHERE site_id = ?", (site_id,)).fetchone() is None:
            raise ResourceError(f"unknown site {site_id}")
        c.execute("INSERT INTO technicians (tech_id, display_name, site_id, skills_json, active, created_at) VALUES (?,?,?,?,?,?) "
                  "ON CONFLICT(tech_id) DO UPDATE SET display_name = excluded.display_name, site_id = excluded.site_id, skills_json = excluded.skills_json, "
                  "active = excluded.active", (tech_id, display_name, site_id, json.dumps(sorted(set(skills))), int(active), now_iso()))
        _audit(db, c, actor, "technician.upserted", "technician", tech_id, {"site_id": site_id, "skills": sorted(set(skills)), "active": active})


def set_shifts(db, tech_id: str, shifts: list[tuple[str, str]], actor: str, replace_from: str | None = None):
    """Record shifts (ISO start, ISO end). With `replace_from`, shifts starting at or after that instant are replaced."""
    parsed = []
    for s, e in shifts:
        a, b = parse_ts(s), parse_ts(e)
        if b <= a:
            raise ResourceError(f"shift {s} - {e} ends before it starts")
        parsed.append((a, b))
    parsed.sort()
    for (a1, b1), (a2, b2) in zip(parsed, parsed[1:]):
        if a2 < b1:
            raise ResourceError(f"overlapping shifts {iso(a1)}-{iso(b1)} and {iso(a2)}-{iso(b2)}")
    with db.tx() as c:
        if c.execute("SELECT 1 FROM technicians WHERE tech_id = ?", (tech_id,)).fetchone() is None:
            raise ResourceError(f"unknown technician {tech_id}")
        if replace_from:
            c.execute("DELETE FROM shifts WHERE tech_id = ? AND start_ms >= ?", (tech_id, parse_ts(replace_from)))
        c.executemany("INSERT OR REPLACE INTO shifts (tech_id, start_ms, end_ms) VALUES (?,?,?)", [(tech_id, a, b) for a, b in parsed])
        _audit(db, c, actor, "shifts.set", "technician", tech_id, {"n": len(parsed), "first": iso(parsed[0][0]) if parsed else None,
                                                                  "last": iso(parsed[-1][1]) if parsed else None, "replace_from": replace_from})


def upsert_part(db, part_id: str, site_id: str, name: str, on_hand: int, lead_time_h: float, actor: str, orderable: bool = True,
                unit_cost: float | None = None):
    if on_hand < 0 or lead_time_h < 0:
        raise ResourceError("stock and lead time cannot be negative")
    with db.tx() as c:
        if c.execute("SELECT 1 FROM sites WHERE site_id = ?", (site_id,)).fetchone() is None:
            raise ResourceError(f"unknown site {site_id}")
        c.execute("INSERT INTO parts (part_id, site_id, name, on_hand, lead_time_h, orderable, unit_cost, updated_at) VALUES (?,?,?,?,?,?,?,?) "
                  "ON CONFLICT(part_id, site_id) DO UPDATE SET name = excluded.name, on_hand = excluded.on_hand, lead_time_h = excluded.lead_time_h, "
                  "orderable = excluded.orderable, unit_cost = excluded.unit_cost, updated_at = excluded.updated_at",
                  (part_id, site_id, name, int(on_hand), float(lead_time_h), int(orderable), unit_cost, now_iso()))
        _audit(db, c, actor, "part.upserted", "part", f"{site_id}/{part_id}", {"on_hand": on_hand, "lead_time_h": lead_time_h, "orderable": orderable})


def add_delivery(db, part_id: str, site_id: str, qty: int, eta: str, reference: str, actor: str):
    if qty <= 0:
        raise ResourceError("delivery quantity must be positive")
    with db.tx() as c:
        if c.execute("SELECT 1 FROM parts WHERE part_id = ? AND site_id = ?", (part_id, site_id)).fetchone() is None:
            raise ResourceError(f"unknown part {part_id} at {site_id}")
        c.execute("INSERT INTO part_deliveries (part_id, site_id, qty, eta_ms, reference) VALUES (?,?,?,?,?)", (part_id, site_id, qty, parse_ts(eta), reference))
        _audit(db, c, actor, "part.delivery_added", "part", f"{site_id}/{part_id}", {"qty": qty, "eta": eta, "reference": reference})


def technicians(db, site_id: str) -> list[dict]:
    with db.connect() as c:
        out = []
        for r in c.execute("SELECT * FROM technicians WHERE site_id = ? AND active = 1 ORDER BY tech_id", (site_id,)):
            sh = [(x["start_ms"], x["end_ms"]) for x in c.execute("SELECT start_ms, end_ms FROM shifts WHERE tech_id = ? ORDER BY start_ms", (r["tech_id"],))]
            out.append({"tech_id": r["tech_id"], "display_name": r["display_name"], "skills": json.loads(r["skills_json"]), "shifts": sh})
        return out


def parts(db, site_id: str) -> list[dict]:
    with db.connect() as c:
        out = []
        for r in c.execute("SELECT * FROM parts WHERE site_id = ? ORDER BY part_id", (site_id,)):
            dl = [(x["eta_ms"], x["qty"]) for x in c.execute("SELECT eta_ms, qty FROM part_deliveries WHERE part_id = ? AND site_id = ? ORDER BY eta_ms",
                                                             (r["part_id"], site_id))]
            out.append({**dict(r), "deliveries": dl})
        return out
