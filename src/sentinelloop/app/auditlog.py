"""Keyed, hash-chained audit events stored in the platform database.

Each event's hash is HMAC-SHA256(key, canonical(seq, ts, actor, action, entity, entity_id, payload_sha256,
prev_hash, key_id)). Editing, reordering or deleting a middle event breaks the chain; forging a chain needs
the key. Deleting the newest events leaves a valid prefix, which only an anchor stored elsewhere (the
latest seq and hash, exported by `anchor`) can reveal. Events are appended inside the same transaction as
the change they describe.
"""
from __future__ import annotations

import hashlib
import hmac
import json

from .timeutil import now_iso

GENESIS = "0" * 64


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _digest(body: dict, key: bytes) -> str:
    return hmac.new(key, canonical(body).encode("utf-8"), hashlib.sha256).hexdigest()


def append(c, actor: str, action: str, entity: str, entity_id: str, payload: dict, key: bytes, key_id: str, ts: str | None = None) -> dict:
    last = c.execute("SELECT seq, hash FROM audit_events ORDER BY seq DESC LIMIT 1").fetchone()
    seq = (last["seq"] + 1) if last else 1
    prev = last["hash"] if last else GENESIS
    payload_json = canonical(payload)
    body = {"seq": seq, "ts": ts or now_iso(), "actor": actor, "action": action, "entity": entity, "entity_id": str(entity_id),
            "payload_sha256": hashlib.sha256(payload_json.encode("utf-8")).hexdigest(), "prev_hash": prev, "key_id": key_id}
    h = _digest(body, key)
    c.execute("INSERT INTO audit_events (seq, ts, actor, action, entity, entity_id, payload_json, payload_sha256, prev_hash, key_id, hash) "
              "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
              (seq, body["ts"], actor, action, entity, body["entity_id"], payload_json, body["payload_sha256"], prev, key_id, h))
    return {**body, "hash": h}


def verify(c, key: bytes, anchor: dict | None = None) -> dict:
    """Check the whole chain, and with an anchor also that the anchored event is still there unchanged (truncation).
    `anchor=None` means no anchor; anything else must be a mapping with `seq` and `hash` (a malformed anchor is an error,
    never silently 'no anchor')."""
    if anchor is not None and not (isinstance(anchor, dict) and "seq" in anchor and "hash" in anchor):
        raise ValueError("an audit anchor must be a mapping with 'seq' and 'hash'")
    prev, n, expected_seq, dev = GENESIS, 0, 1, 0
    for r in c.execute("SELECT * FROM audit_events ORDER BY seq"):
        n += 1
        dev += int(r["key_id"] == "dev-insecure")
        reason = None
        if r["seq"] != expected_seq:
            reason = f"sequence gap: expected {expected_seq}, found {r['seq']}"
        elif hashlib.sha256(r["payload_json"].encode("utf-8")).hexdigest() != r["payload_sha256"]:
            reason = "payload does not match its hash"
        elif r["prev_hash"] != prev:
            reason = "broken link to the previous event"
        else:
            body = {k: r[k] for k in ("seq", "ts", "actor", "action", "entity", "entity_id", "payload_sha256", "prev_hash", "key_id")}
            if not hmac.compare_digest(_digest(body, key), r["hash"]):
                reason = "keyed hash mismatch (edited event or wrong key)"
        if reason:
            return {"n": n, "valid": False, "first_bad_seq": r["seq"], "reason": reason, "events_signed_with_dev_key": dev}
        prev, expected_seq = r["hash"], expected_seq + 1
    if anchor is not None:
        row = c.execute("SELECT hash FROM audit_events WHERE seq = ?", (int(anchor["seq"]),)).fetchone()
        if row is None or row["hash"] != anchor["hash"]:
            return {"n": n, "valid": False, "first_bad_seq": int(anchor["seq"]), "reason": "anchored event missing or changed (truncation or rewrite)",
                    "events_signed_with_dev_key": dev}
    return {"n": n, "valid": True, "first_bad_seq": None, "reason": None, "events_signed_with_dev_key": dev}


def anchor(c) -> dict:
    """The latest (seq, hash): store it outside this database (MLflow tag, ticket, printout) to detect truncation."""
    row = c.execute("SELECT seq, hash, ts FROM audit_events ORDER BY seq DESC LIMIT 1").fetchone()
    return {"seq": row["seq"], "hash": row["hash"], "ts": row["ts"]} if row else {"seq": 0, "hash": GENESIS, "ts": None}


def history(c, entity: str, entity_id: str) -> list[dict]:
    rows = c.execute("SELECT seq, ts, actor, action, payload_json FROM audit_events WHERE entity = ? AND entity_id = ? ORDER BY seq",
                     (entity, str(entity_id))).fetchall()
    return [{"seq": r["seq"], "ts": r["ts"], "actor": r["actor"], "action": r["action"], "payload": json.loads(r["payload_json"])} for r in rows]
