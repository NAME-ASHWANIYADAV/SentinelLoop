"""Users, credentials, role permissions and rate limiting.

API keys are random 256-bit tokens shown once at issue and stored only as SHA-256 hashes (adequate for high-entropy
tokens). Passwords (for the operator console) are hashed with scrypt and a per-user salt. Roles are fixed; what each
role may do is defined here for the API and enforced again inside each service.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from collections import OrderedDict

from . import auditlog
from .timeutil import now_iso

ROLES = ("viewer", "technician", "planner", "reliability_engineer", "admin", "integration")
PERMISSIONS = {
    "read": set(ROLES),
    "assets.write": {"admin"},
    "resources.write": {"admin", "planner"},
    "resources.read": {"admin", "planner", "reliability_engineer"},          # technician names and shifts are personal data
    "ingest": {"integration", "admin"},
    "assess": {"integration", "admin", "reliability_engineer", "planner"},
    "decisions.generate": {"integration", "admin", "reliability_engineer", "planner"},
    "workorders.write": {"technician", "planner", "reliability_engineer", "admin", "integration"},
    "schedules": {"planner", "admin"},
    "models.decide": {"reliability_engineer", "admin"},
    "asset_state.clear": {"planner", "reliability_engineer", "admin"},     # dismissal only; maintenance clears via its work order
    "assets.commission": {"reliability_engineer", "admin"},
    "audit.read": {"admin", "reliability_engineer"},
    "users.admin": {"admin"},
    "integrations.manage": {"admin"},
    "integrations.dispatch": {"admin", "integration"},
    "integrations.read": {"admin", "integration", "planner", "reliability_engineer"},
}
MIN_PASSWORD = 12
SCRYPT = (2 ** 14, 8, 1)


class SecurityError(ValueError):
    pass


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def allowed(role: str, permission: str) -> bool:
    return role in PERMISSIONS.get(permission, set())


def _audit(db, c, actor, action, user_id, payload):
    auditlog.append(c, actor=actor, action=action, entity="user", entity_id=user_id, payload=payload, key=db.audit_key, key_id=db.audit_key_id)


def create_user(db, user_id: str, display_name: str, role: str, actor: str) -> dict:
    if role not in ROLES:
        raise SecurityError(f"unknown role {role!r}")
    with db.tx() as c:
        if c.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone():
            raise SecurityError(f"user {user_id} exists")
        c.execute("INSERT INTO users (user_id, display_name, role, active, created_at) VALUES (?,?,?,1,?)", (user_id, display_name, role, now_iso()))
        _audit(db, c, actor, "user.created", user_id, {"role": role})
    return {"user_id": user_id, "display_name": display_name, "role": role}


def issue_api_key(db, user_id: str, actor: str) -> str:
    key = "slk_" + secrets.token_urlsafe(32)
    with db.tx() as c:
        if c.execute("UPDATE users SET api_key_hash = ? WHERE user_id = ? AND active = 1", (hash_key(key), user_id)).rowcount != 1:
            raise SecurityError(f"no active user {user_id}")
        _audit(db, c, actor, "user.api_key_issued", user_id, {"key_prefix": key[:8]})
    return key


def revoke_api_key(db, user_id: str, actor: str):
    with db.tx() as c:
        c.execute("UPDATE users SET api_key_hash = NULL WHERE user_id = ?", (user_id,))
        _audit(db, c, actor, "user.api_key_revoked", user_id, {})


def list_users(db) -> list[dict]:
    with db.connect() as c:
        return [{"user_id": r["user_id"], "display_name": r["display_name"], "role": r["role"], "active": bool(r["active"]),
                 "has_api_key": r["api_key_hash"] is not None, "has_password": r["password_hash"] is not None, "created_at": r["created_at"]}
                for r in c.execute("SELECT * FROM users ORDER BY user_id")]


def deactivate(db, user_id: str, actor: str, reason: str):
    with db.tx() as c:
        c.execute("UPDATE users SET active = 0, api_key_hash = NULL WHERE user_id = ?", (user_id,))
        _audit(db, c, actor, "user.deactivated", user_id, {"reason": reason})


def authenticate_key(db, key: str | None) -> dict | None:
    if not key or not key.startswith("slk_"):
        return None
    h = hash_key(key)
    with db.connect() as c:
        r = c.execute("SELECT user_id, display_name, role, active, api_key_hash FROM users WHERE api_key_hash = ?", (h,)).fetchone()
    if r is None or not r["active"] or not hmac.compare_digest(r["api_key_hash"], h):
        return None
    return {"user_id": r["user_id"], "display_name": r["display_name"], "role": r["role"]}


def set_password(db, user_id: str, password: str, actor: str):
    if len(password) < MIN_PASSWORD:
        raise SecurityError(f"passwords need at least {MIN_PASSWORD} characters")
    salt = secrets.token_bytes(16)
    n, r, p = SCRYPT
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32)
    stored = f"scrypt${n}${r}${p}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"
    with db.tx() as c:
        if c.execute("UPDATE users SET password_hash = ? WHERE user_id = ? AND active = 1", (stored, user_id)).rowcount != 1:
            raise SecurityError(f"no active user {user_id}")
        _audit(db, c, actor, "user.password_set", user_id, {})


def verify_password(db, user_id: str, password: str) -> dict | None:
    with db.connect() as c:
        r = c.execute("SELECT user_id, display_name, role, active, password_hash FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if r is None or not r["active"] or not r["password_hash"]:
        hashlib.scrypt(b"x", salt=b"0" * 16, n=SCRYPT[0], r=SCRYPT[1], p=SCRYPT[2], dklen=32)    # similar timing for unknown users
        return None
    _, n, rr, p, salt, dk = r["password_hash"].split("$")
    got = hashlib.scrypt(password.encode("utf-8"), salt=base64.b64decode(salt), n=int(n), r=int(rr), p=int(p), dklen=32)
    if not hmac.compare_digest(got, base64.b64decode(dk)):
        return None
    return {"user_id": r["user_id"], "display_name": r["display_name"], "role": r["role"]}


class RateLimiter:
    """Token bucket per client (in-process; one bucket set per API process - documented limitation).

    The API keys buckets by authenticated user id, or by client address for requests without a valid credential, so
    a client cannot get a fresh bucket by changing how it presents its key. At most `max_buckets` buckets are kept;
    the least recently used one is dropped first (a dropped bucket starts full again, which only matters for a
    client that has been idle longest).
    """

    def __init__(self, capacity: int = 60, refill_per_s: float = 1.0, max_buckets: int = 10_000):
        self.capacity, self.rate, self.max_buckets = float(capacity), float(refill_per_s), int(max_buckets)
        self._b: OrderedDict[str, tuple[float, float]] = OrderedDict()
        self._lock = threading.Lock()

    def allow(self, key: str, cost: float = 1.0) -> tuple[bool, float]:
        """Take `cost` tokens if the bucket holds that many (nothing is taken otherwise); returns (allowed, seconds to wait).
        Requests that do more work (assess-range) pay more than one token."""
        now = time.monotonic()
        with self._lock:
            tokens, last = self._b.pop(key, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - last) * self.rate)
            ok = tokens >= cost
            self._b[key] = (tokens - cost if ok else tokens, now)
            while len(self._b) > self.max_buckets:
                self._b.popitem(last=False)
            if ok:
                return True, 0.0
            return False, (cost - tokens) / self.rate if self.rate > 0 else 60.0
