"""SQLite storage with versioned, checksummed migrations.

One file per installation. WAL journal, foreign keys on, explicit IMMEDIATE transactions for writes.
A migration whose text changed after it was applied is refused, so a deployed schema always matches
a reviewed migration file.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .timeutil import now_iso

MIGRATIONS_DIR = Path(__file__).with_name("migrations")
_MIG_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")
DEV_AUDIT_KEY = b"sentinelloop-dev-insecure-audit-key"


class MigrationError(RuntimeError):
    pass


class _Conn(sqlite3.Connection):
    """A connection that closes itself at the end of a `with` block (sqlite3's default only commits)."""

    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


MIN_AUDIT_KEY_BYTES = 32


class Database:
    """`audit_key` signs the audit chain. It is required: without one the database refuses to open, unless the caller
    explicitly opts into the built-in development key (`allow_dev_key=True`), whose events are labelled `dev-insecure`
    and counted by `auditlog.verify` so they can never pass as production evidence."""

    def __init__(self, path, audit_key: bytes | None = None, audit_key_id: str | None = None, allow_dev_key: bool = False):
        self.path = Path(path)
        if audit_key is None:
            if not allow_dev_key:
                raise ValueError("an audit key is required (set SENTINELLOOP_AUDIT_KEY); pass allow_dev_key=True only for local development")
            self.audit_key, self.audit_key_id = DEV_AUDIT_KEY, "dev-insecure"
        else:
            if len(audit_key) < MIN_AUDIT_KEY_BYTES:
                raise ValueError(f"the audit key must be at least {MIN_AUDIT_KEY_BYTES} bytes")
            if audit_key == DEV_AUDIT_KEY:
                raise ValueError("the built-in development key cannot be supplied as a configured key")
            self.audit_key, self.audit_key_id = audit_key, (audit_key_id or "configured")
            if self.audit_key_id == "dev-insecure":
                raise ValueError("key id 'dev-insecure' is reserved for the development key")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def insecure_dev_key(self) -> bool:
        return self.audit_key_id == "dev-insecure"

    # -- connections ---------------------------------------------------------------------------
    def connect(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=30.0, isolation_level=None, factory=_Conn)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        c.execute("PRAGMA busy_timeout = 30000")
        return c

    @contextmanager
    def tx(self):
        """A write transaction: BEGIN IMMEDIATE ... COMMIT, rolled back on any exception."""
        c = self.connect()
        try:
            c.execute("BEGIN IMMEDIATE")
            yield c
            c.execute("COMMIT")
        except BaseException:
            if c.in_transaction:
                c.execute("ROLLBACK")
            raise
        finally:
            c.close()

    # -- migrations ----------------------------------------------------------------------------
    @staticmethod
    def migration_files() -> list[tuple[int, str, Path]]:
        out = []
        for p in sorted(MIGRATIONS_DIR.glob("*.sql")):
            m = _MIG_RE.match(p.name)
            if not m:
                raise MigrationError(f"badly named migration file {p.name}")
            out.append((int(m.group(1)), p.stem, p))
        versions = [v for v, _, _ in out]
        if versions != list(range(1, len(versions) + 1)):
            raise MigrationError(f"migration versions must be consecutive from 1, got {versions}")
        return out

    def migrate(self) -> list[str]:
        applied: list[str] = []
        with self.connect() as c:
            c.execute("PRAGMA journal_mode = WAL")
            c.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                      "checksum TEXT NOT NULL, applied_at TEXT NOT NULL)")
            done = {r["version"]: r for r in c.execute("SELECT * FROM schema_migrations")}
            for version, name, path in self.migration_files():
                sql = path.read_text(encoding="utf-8")
                checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
                if version in done:
                    if done[version]["checksum"] != checksum:
                        raise MigrationError(f"migration {name} was changed after it was applied (checksum mismatch); "
                                             "write a new migration instead of editing an applied one")
                    continue
                try:
                    c.executescript(f"BEGIN IMMEDIATE;\n{sql}\n;INSERT INTO schema_migrations (version, name, checksum, applied_at) "
                                    f"VALUES ({version}, '{name}', '{checksum}', '{now_iso()}');\nCOMMIT;")
                except sqlite3.Error as e:
                    if c.in_transaction:
                        c.execute("ROLLBACK")
                    raise MigrationError(f"migration {name} failed: {e}") from e
                applied.append(name)
        return applied

    def schema_version(self) -> int:
        with self.connect() as c:
            row = c.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        return int(row[0] or 0)

    # -- backup --------------------------------------------------------------------------------
    def backup(self, dest) -> Path:
        """Consistent online copy using SQLite's backup API (safe while other connections write)."""
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        src = self.connect()
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        return dest
