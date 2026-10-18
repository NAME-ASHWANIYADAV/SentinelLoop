"""Versioned REST API (/api/v1) over the platform services.

Authentication: `Authorization: Bearer <api key>` (or `X-API-Key`). Authorisation: role permissions from
security.PERMISSIONS, enforced here and again inside the services. Every response carries `X-Request-ID`; errors are
JSON `{"error", "request_id"}` without internal details. Work-order creation requires an `Idempotency-Key` header;
transitions accept one. Request bodies above `max_body_bytes` are refused (413); clients over their rate are told to
retry (429 with Retry-After). Read-only by default for integrations: nothing here sends data to another system.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import math
import threading
import time
import uuid

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from . import auditlog, decision, health, ingest, integration, modelreg, nbm, planning, registry, resources, security, workorders
from .errors import PermissionDenied
from .models import AssetSpec
from .timeutil import iso, now_ms, parse_ts

log = logging.getLogger("sentinelloop.api")
API = "/api/v1"
# audit histories any authenticated role may read; every other entity (users, credentials, ...) needs audit.read
OPEN_AUDIT_ENTITIES = {"asset", "assessment", "work_order", "schedule_run", "model", "ingestion_batch"}
FORMULA_LEAD = ("=", "+", "-", "@", "\t", "\r")
RANGE_STEPS_PER_TOKEN = 10          # assess-range pays one rate-limit token per this many steps (each step is a full assessment)
RANGE_WORKERS = 2                   # assess-range calls running at once on the server (of the 40 worker threads), at most one per user
RANGE_BUSY_RETRY_S = 5              # Retry-After for a range refused because another is running
MILP_MAX_ORDER_SLOTS = 5_000        # milp refused above approved orders x slots: building it grows with (orders x slots) squared
SQLITE_MAX_INT = 2 ** 63 - 1
# CMMS error text can name credential variables, and base_url names the host: shown to admins only, in every route
WITHHELD = "withheld: ask an administrator for the details"
INTEGRATION_DETAIL = ("base_url", "error")      # payload fields of integration.* audit events withheld from non-admins


class BodyTooLarge(Exception):
    pass


class BodyLimit:
    """ASGI middleware: refuse bodies over `limit` bytes, counted while they stream in (chunked bodies have no
    Content-Length to check up front)."""

    def __init__(self, app, limit: int):
        self.app, self.limit = app, int(limit)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        seen, exceeded, replied = 0, False, False

        async def limited():
            nonlocal seen, exceeded
            msg = await receive()
            if msg["type"] == "http.request":
                seen += len(msg.get("body", b""))
                if seen > self.limit:
                    exceeded = True
                    raise BodyTooLarge()
            return msg

        async def reply_413():
            nonlocal replied
            if replied:
                return
            replied = True
            rid = scope.get("state", {}).get("request_id")
            body = json.dumps({"error": f"request body larger than {self.limit} bytes", "request_id": rid}).encode()
            await send({"type": "http.response.start", "status": 413, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
            await send({"type": "http.response.body", "body": body})

        async def guarded_send(msg):
            # once the cap is crossed the app's own reply (FastAPI turns a failed body read into 400) is replaced by 413
            if exceeded:
                if msg["type"] == "http.response.start":
                    await reply_413()
                return
            await send(msg)

        try:
            await self.app(scope, limited, guarded_send)
        except BodyTooLarge:
            await reply_413()


def _csv_safe(v):
    """Neutralise spreadsheet formulas in exported text (CSV injection): prefix risky leading characters with '."""
    if isinstance(v, str) and v.startswith(FORMULA_LEAD):
        return "'" + v
    return v


def _model_view(u: dict, m):
    """artifact_path is a server filesystem path: admins only."""
    return m if u["role"] == "admin" or not isinstance(m, dict) else {k: v for k, v in m.items() if k != "artifact_path"}


def _withhold_integration_detail(r: dict) -> dict:
    p = r["payload"]
    if not (r["action"].startswith("integration.") and isinstance(p, dict) and any(p.get(k) for k in INTEGRATION_DETAIL)):
        return r
    return {**r, "payload": {**p, **{k: WITHHELD for k in INTEGRATION_DETAIL if p.get(k)}}}


def _presented_key(headers) -> str | None:
    auth = headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return headers.get("x-api-key")


# -- request bodies -------------------------------------------------------------------------------------------------
class IngestBody(BaseModel):
    records: list[dict] = Field(max_length=200_000)
    source: str = Field(min_length=1, max_length=200)
    default_tz: str | None = None


class AssessBody(BaseModel):
    as_of: str | None = None


class AssessRangeBody(BaseModel):
    start: str
    end: str
    step_minutes: int = Field(default=60, ge=1, le=24 * 60)


class ReprioritiseBody(BaseModel):
    priority_class: str
    reason: str = Field(min_length=1)
    due_by: str | None = None
    expected_version: int | None = None


class ClearRiskBody(BaseModel):
    event: str
    reason: str


class CreateOrderBody(BaseModel):
    asset_id: str
    job_type: str
    priority_class: str
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    due_by: str | None = None


class TransitionBody(BaseModel):
    action: str
    reason: str | None = None
    data: dict = Field(default_factory=dict)
    expected_version: int | None = None


class CompleteBody(BaseModel):
    outcome: dict
    expected_version: int | None = None


class PlanBody(BaseModel):
    site_id: str
    policy: str = "risk_greedy"
    horizon_h: float = Field(default=72.0, gt=0, le=24 * 14)
    slot_h: float = Field(default=1.0, ge=0.25, le=24)       # at most 336 / 0.25 = 1344 slots: planning cost grows with the slot count
    t0: str | None = None


class ModelDecisionBody(BaseModel):
    decision: str
    reason: str


class RollbackBody(BaseModel):
    asset_type_id: str
    to_model_id: str
    reason: str


class AssetPatchBody(BaseModel):
    changes: dict
    reason: str


class TechnicianBody(BaseModel):
    tech_id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=200)
    skills: list[str] = Field(min_length=1)
    active: bool = True


class ShiftsBody(BaseModel):
    shifts: list[tuple[str, str]]
    replace_from: str | None = None


class PartBody(BaseModel):
    part_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    on_hand: int = Field(ge=0)
    lead_time_h: float = Field(ge=0)
    orderable: bool = True
    unit_cost: float | None = None


class DeliveryBody(BaseModel):
    qty: int = Field(gt=0)
    eta: str
    reference: str = Field(min_length=1, max_length=200)


class UserBody(BaseModel):
    user_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    display_name: str = Field(min_length=1, max_length=200)
    role: str


class ReasonBody(BaseModel):
    reason: str = Field(min_length=1)


class TargetBody(BaseModel):
    target_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    kind: str
    base_url: str
    config: dict = Field(default_factory=dict)
    mode: str = "shadow"
    reason: str | None = None


class ModeBody(BaseModel):
    mode: str
    reason: str = Field(min_length=1)


class BaselineBody(BaseModel):
    model_id: str
    start: str
    end: str
    reason: str = Field(min_length=1)


# Idempotency keys the platform itself uses (recommendations, deferral reactivation, schedule application). A client that
# pre-claimed one could turn the engine's later action into a silent replay, so clients may not use these prefixes.
RESERVED_KEY_PREFIXES = ("rec:", "reactivate:", "apply:")


def _client_key(key: str | None) -> str | None:
    if key is not None and key.startswith(RESERVED_KEY_PREFIXES):
        raise HTTPException(400, f"Idempotency-Key prefixes {', '.join(RESERVED_KEY_PREFIXES)} are reserved for the platform")
    return key


def create_app(db, policy_set, decision_cfg: decision.DecisionConfig | None = None, rate_limit: tuple = (120, 2.0),
               max_body_bytes: int = 10 * 1024 * 1024) -> FastAPI:
    app = FastAPI(title="SentinelLoop platform API", version="1", docs_url=f"{API}/docs", openapi_url=f"{API}/openapi.json", redoc_url=None)
    limiter = security.RateLimiter(*rate_limit)
    dcfg = decision_cfg or decision.DecisionConfig()
    range_slots, range_users, range_lock = threading.BoundedSemaphore(RANGE_WORKERS), set(), threading.Lock()
    app.add_middleware(BodyLimit, limit=max_body_bytes)

    def _bucket(u: dict) -> str:
        return f"user:{u['user_id']}"

    def _retry_after(retry: float) -> dict:
        return {"Retry-After": f"{max(1, int(retry + 0.999))}"}

    # -- middleware ---------------------------------------------------------------------------------------------------
    @app.middleware("http")
    async def envelope(request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = rid
        t = time.time()
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > max_body_bytes:
            resp = JSONResponse({"error": f"request body larger than {max_body_bytes} bytes", "request_id": rid}, status_code=413)
        else:
            if request.url.path in (f"{API}/health", f"{API}/ready"):
                ok, retry = True, 0
            else:
                u = security.authenticate_key(db, _presented_key(request.headers))
                bucket = _bucket(u) if u else f"addr:{request.client.host if request.client else 'unknown'}"
                ok, retry = limiter.allow(bucket)
            if not ok:
                resp = JSONResponse({"error": "rate limit exceeded", "request_id": rid}, status_code=429, headers=_retry_after(retry))
            else:
                resp = await call_next(request)
        resp.headers["X-Request-ID"] = rid
        log.info(json.dumps({"request_id": rid, "method": request.method, "path": request.url.path, "status": resp.status_code,
                             "ms": round((time.time() - t) * 1000, 1), "user": getattr(request.state, "user_id", None)}))
        return resp

    # -- error mapping ------------------------------------------------------------------------------------------------
    def _err(request, status, msg):
        return JSONResponse({"error": msg, "request_id": getattr(request.state, "request_id", None)}, status_code=status)

    @app.exception_handler(PermissionDenied)
    async def _perm(request, exc):
        return _err(request, 403, str(exc))

    @app.exception_handler(RequestValidationError)
    async def _val(request, exc):
        return _err(request, 422, "; ".join(f"{'.'.join(str(x) for x in e.get('loc', []))}: {e.get('msg')}" for e in exc.errors()[:10]))

    @app.exception_handler(ValueError)
    async def _value(request, exc):
        msg = str(exc)
        if isinstance(exc, (workorders.IdempotencyConflict, workorders.ConcurrencyConflict)):
            return _err(request, 409, msg)
        if msg.startswith("unknown ") or " unknown " in msg[:40]:
            return _err(request, 404, msg)
        if isinstance(exc, (workorders.WorkflowError, planning.PlanningError, modelreg.ModelRegistryError)) or exc.__class__.__name__ == "TransitionError":
            return _err(request, 409, msg)
        return _err(request, 422, msg)

    @app.exception_handler(BodyTooLarge)
    async def _too_large(request, exc):
        return _err(request, 413, f"request body larger than {max_body_bytes} bytes")

    @app.exception_handler(Exception)
    async def _any(request, exc):
        log.exception("unhandled error %s", getattr(request.state, "request_id", None))
        return _err(request, 500, "internal error; quote the request id when reporting it")

    # -- auth ---------------------------------------------------------------------------------------------------------
    def current_user(request: Request) -> dict:
        u = security.authenticate_key(db, _presented_key(request.headers))
        if u is None:
            raise HTTPException(status_code=401, detail="missing or invalid API key")
        request.state.user_id = u["user_id"]
        return u

    def need(permission: str):
        def dep(u: dict = Depends(current_user)) -> dict:
            if not security.allowed(u["role"], permission):
                raise PermissionDenied(f"role {u['role']!r} may not perform {permission}")
            return u
        return dep

    @app.exception_handler(HTTPException)
    async def _http(request, exc):
        resp = _err(request, exc.status_code, str(exc.detail))
        for k, v in (exc.headers or {}).items():       # e.g. Retry-After on a 429 raised by a route
            resp.headers[k] = v
        return resp

    # -- health ---------------------------------------------------------------------------------------------------------
    @app.get(f"{API}/health")
    async def health_():
        # on the event loop, not in a worker thread: liveness still answers while every worker is busy
        return {"status": "ok"}

    @app.get(f"{API}/ready")
    def ready():
        try:
            v = db.schema_version()
            with db.connect() as c:
                n_models = c.execute("SELECT COUNT(*) FROM models WHERE status = 'approved'").fetchone()[0]
            latest = len(db.migration_files())
            return {"database": "ok", "schema_version": v, "schema_current": v == latest, "approved_models": n_models,
                    "audit_key": "DEV-INSECURE" if db.insecure_dev_key else "configured",
                    "decision_config": "site-configured" if dcfg.site_configured else
                                       "placeholder defaults (downtime cost 0, illustrative due dates): set them with serve --decision-config"}
        except Exception as e:  # readiness must not raise
            return JSONResponse({"database": "error", "detail": type(e).__name__}, status_code=503)

    @app.get(f"{API}/me")
    def me(u: dict = Depends(current_user)):
        return u

    # -- registry -------------------------------------------------------------------------------------------------------
    @app.get(f"{API}/assets")
    def assets(site_id: str | None = None, status: str | None = None, u: dict = Depends(need("read"))):
        return [{**a.model_dump(), **health.asset_view(db, a, policy_set)} for a in registry.list_assets(db, site_id=site_id, status=status)]

    @app.get(f"{API}/assets/{{asset_id}}")
    def asset(asset_id: str, u: dict = Depends(need("read"))):
        a = registry.get_asset(db, asset_id)
        if a is None:
            raise HTTPException(404, f"unknown asset {asset_id}")
        st = health.asset_state(db, a.asset_id)
        return {**a.model_dump(), **health.asset_view(db, a, policy_set), "state_notes": list(st.notes) if st else []}

    @app.post(f"{API}/assets", status_code=201)
    def create_asset(spec: AssetSpec, u: dict = Depends(need("assets.write"))):
        return registry.create_asset(db, spec, actor=u["user_id"]).model_dump()

    @app.patch(f"{API}/assets/{{asset_id}}")
    def patch_asset(asset_id: str, body: AssetPatchBody, u: dict = Depends(need("assets.write"))):
        return registry.update_asset(db, asset_id, body.changes, actor=u["user_id"], reason=body.reason).model_dump()

    @app.get(f"{API}/sites")
    def sites(u: dict = Depends(need("read"))):
        return registry.list_sites(db)

    @app.get(f"{API}/asset-types")
    def asset_types(u: dict = Depends(need("read"))):
        return [t.model_dump() for t in registry.list_asset_types(db)]

    @app.post(f"{API}/assets/{{asset_id}}/baseline")
    def commission(asset_id: str, body: BaselineBody, u: dict = Depends(need("assets.commission"))):
        return nbm.commission(db, asset_id, body.model_id, parse_ts(body.start), parse_ts(body.end), actor=u["user_id"], role=u["role"],
                              reason=body.reason)

    # -- resources ------------------------------------------------------------------------------------------------------
    @app.get(f"{API}/sites/{{site_id}}/technicians")
    def techs(site_id: str, u: dict = Depends(need("resources.read"))):
        return resources.technicians(db, site_id)

    @app.post(f"{API}/sites/{{site_id}}/technicians")
    def upsert_tech(site_id: str, body: TechnicianBody, u: dict = Depends(need("resources.write"))):
        if registry.get_site(db, site_id) is None:
            raise HTTPException(404, f"unknown site {site_id}")
        resources.upsert_technician(db, body.tech_id, body.display_name, site_id, body.skills, actor=u["user_id"], active=body.active)
        return {"tech_id": body.tech_id, "site_id": site_id}

    @app.put(f"{API}/technicians/{{tech_id}}/shifts")
    def shifts(tech_id: str, body: ShiftsBody, u: dict = Depends(need("resources.write"))):
        resources.set_shifts(db, tech_id, [tuple(s) for s in body.shifts], actor=u["user_id"], replace_from=body.replace_from)
        return {"tech_id": tech_id, "shifts": len(body.shifts)}

    @app.get(f"{API}/sites/{{site_id}}/parts")
    def parts_(site_id: str, u: dict = Depends(need("read"))):
        return resources.parts(db, site_id)

    @app.post(f"{API}/sites/{{site_id}}/parts")
    def upsert_part(site_id: str, body: PartBody, u: dict = Depends(need("resources.write"))):
        if registry.get_site(db, site_id) is None:
            raise HTTPException(404, f"unknown site {site_id}")
        resources.upsert_part(db, body.part_id, site_id, body.name, body.on_hand, body.lead_time_h, actor=u["user_id"], orderable=body.orderable,
                              unit_cost=body.unit_cost)
        return {"part_id": body.part_id, "site_id": site_id}

    @app.post(f"{API}/sites/{{site_id}}/parts/{{part_id}}/deliveries")
    def delivery(site_id: str, part_id: str, body: DeliveryBody, u: dict = Depends(need("resources.write"))):
        resources.add_delivery(db, part_id, site_id, body.qty, body.eta, body.reference, actor=u["user_id"])
        return {"part_id": part_id, "qty": body.qty, "eta": body.eta}

    # -- users ----------------------------------------------------------------------------------------------------------
    @app.get(f"{API}/users")
    def users(u: dict = Depends(need("users.admin"))):
        return security.list_users(db)

    @app.post(f"{API}/users", status_code=201)
    def create_user(body: UserBody, u: dict = Depends(need("users.admin"))):
        return security.create_user(db, body.user_id, body.display_name, body.role, actor=u["user_id"])

    @app.post(f"{API}/users/{{user_id}}/api-key")
    def issue_key(user_id: str, u: dict = Depends(need("users.admin"))):
        return {"user_id": user_id, "api_key": security.issue_api_key(db, user_id, actor=u["user_id"]),
                "note": "shown once; stored only as a hash"}

    @app.post(f"{API}/users/{{user_id}}/deactivate")
    def deactivate(user_id: str, body: ReasonBody, u: dict = Depends(need("users.admin"))):
        if user_id == u["user_id"]:
            raise HTTPException(409, "an admin cannot deactivate their own account")
        security.deactivate(db, user_id, actor=u["user_id"], reason=body.reason)
        return {"user_id": user_id, "active": False}

    # -- integrations (CMMS, webhooks): shadow mode by default --------------------------------------------------------
    @app.get(f"{API}/integrations")
    def targets(u: dict = Depends(need("integrations.read"))):
        rows = integration.list_targets(db)
        if u["role"] != "admin":                       # config names credential variables, base_url the host: admins only
            rows = [{k: v for k, v in t.items() if k not in ("config", "base_url")} for t in rows]
        return rows

    @app.post(f"{API}/integrations", status_code=201)
    def register_target(body: TargetBody, u: dict = Depends(need("integrations.manage"))):
        return integration.register_target(db, body.target_id, body.kind, body.base_url, body.config, actor=u["user_id"], role=u["role"],
                                           mode=body.mode, reason=body.reason)

    @app.post(f"{API}/integrations/{{target_id}}/mode")
    def target_mode(target_id: str, body: ModeBody, u: dict = Depends(need("integrations.manage"))):
        return integration.set_mode(db, target_id, body.mode, actor=u["user_id"], role=u["role"], reason=body.reason)

    @app.post(f"{API}/integrations/{{target_id}}/dispatch")
    def dispatch(target_id: str, u: dict = Depends(need("integrations.dispatch"))):
        return integration.dispatch(db, target_id, actor=u["user_id"], role=u["role"])

    @app.get(f"{API}/integrations/{{target_id}}/items")
    def target_items(target_id: str, status: str | None = None, u: dict = Depends(need("integrations.read"))):
        rows = integration.items(db, target_id, status)
        if u["role"] != "admin":                       # the status says that it failed; the error text stays with admins
            rows = [{**r, "last_error": WITHHELD if r.get("last_error") else r.get("last_error")} for r in rows]
        return rows

    @app.post(f"{API}/integrations/{{target_id}}/items/{{wo_id}}/requeue")
    def requeue(target_id: str, wo_id: str, body: ReasonBody, u: dict = Depends(need("integrations.manage"))):
        integration.requeue(db, target_id, wo_id, actor=u["user_id"], role=u["role"], reason=body.reason)
        return {"target_id": target_id, "wo_id": wo_id, "status": "retry"}

    # -- ingestion ------------------------------------------------------------------------------------------------------
    @app.post(f"{API}/ingest/readings")
    def ingest_readings(body: IngestBody, u: dict = Depends(need("ingest"))):
        return ingest.ingest_records(db, body.records, source=body.source, actor=u["user_id"], default_tz=body.default_tz).to_dict()

    @app.post(f"{API}/ingest/csv")
    async def ingest_csv(request: Request, source: str = Query(min_length=1), default_tz: str | None = None, wide_units: str | None = None,
                         u: dict = Depends(need("ingest"))):
        raw = await request.body()                     # BodyLimit caps it while it streams
        units = json.loads(wide_units) if wide_units else None
        res = await run_in_threadpool(ingest.ingest_csv, db, raw, source=source, actor=u["user_id"], wide_units=units, default_tz=default_tz)
        return res.to_dict()                           # parsed off the event loop so one upload cannot stall the API

    @app.get(f"{API}/ingest/batches/{{batch_id}}")
    def batch(batch_id: str, u: dict = Depends(need("read"))):
        b = ingest.batch(db, batch_id)
        if b is None:
            raise HTTPException(404, f"unknown batch {batch_id}")
        return b

    @app.get(f"{API}/ingest/staleness")
    def staleness(max_age_h: float = Query(default=6.0, gt=0, le=24 * 365, allow_inf_nan=False), site_id: str | None = None,
                  u: dict = Depends(need("read"))):
        return ingest.staleness(db, max_age_ms=int(max_age_h * 3_600_000), site_id=site_id)

    # -- assessments and states -------------------------------------------------------------------------------------------
    @app.post(f"{API}/assets/{{asset_id}}/assess")
    def assess(asset_id: str, body: AssessBody = Body(default_factory=AssessBody), u: dict = Depends(need("assess"))):
        return health.assess(db, asset_id, policy=policy_set, as_of_ms=parse_ts(body.as_of) if body.as_of else None, actor=u["user_id"])

    @app.post(f"{API}/assets/{{asset_id}}/assess-range")
    def assess_range(asset_id: str, body: AssessRangeBody, u: dict = Depends(need("assess"))):
        """Assess every step from start to end, oldest first (e.g. after a periodic export arrives).

        Cost: every step is a full assessment, so the request costs one rate-limit token per RANGE_STEPS_PER_TOKEN (10)
        steps, at least one (the request's own token counts). A bucket that cannot pay now is refused with 429 and
        Retry-After before any work; a range that costs more than the bucket can ever hold is refused with 422 (split it).
        The whole range is checked first: the asset (id or tag), end >= start, end no later than now plus the allowed
        clock skew, and at most health.MAX_RANGE_STEPS steps. A refused range stores nothing. The work runs in a worker
        thread, never on the event loop.

        Concurrency: one range per user at a time, and at most RANGE_WORKERS (2) on the server, so ranges can never hold
        the worker threads the other routes need. A range over either limit is refused at once (429, Retry-After), not
        queued, and is not charged beyond its request's own token.
        """
        a = registry.get_asset(db, asset_id)
        if a is None:
            raise HTTPException(404, f"unknown asset {asset_id}")
        start, end, step = parse_ts(body.start), parse_ts(body.end), body.step_minutes * 60_000
        if end < start:
            raise health.AssessmentError("assess-range needs end >= start")
        if end > now_ms() + health.MAX_FUTURE_SKEW_MS:
            raise health.AssessmentError(f"range end {iso(end)} is in the future; assessments are for now or the past")
        n = (end - start) // step + 1
        if n > health.MAX_RANGE_STEPS:
            raise health.AssessmentError(f"{n} steps requested; at most {health.MAX_RANGE_STEPS} per call")
        cost = max(1, -(-n // RANGE_STEPS_PER_TOKEN))
        if cost > limiter.capacity:
            raise health.AssessmentError(f"{n} steps cost {cost} rate-limit tokens, more than this server's bucket holds "
                                         f"({limiter.capacity:.0f}, i.e. {limiter.capacity * RANGE_STEPS_PER_TOKEN:.0f} steps): split the range")
        uid = u["user_id"]
        with range_lock:                               # refused, never queued: a waiting range would still hold a worker thread
            if uid in range_users:
                raise HTTPException(429, "your previous assess-range call is still running: send the next range when it has finished",
                                    headers=_retry_after(RANGE_BUSY_RETRY_S))
            if not range_slots.acquire(blocking=False):
                raise HTTPException(429, f"{RANGE_WORKERS} assess-range calls are already running on this server: retry later",
                                    headers=_retry_after(RANGE_BUSY_RETRY_S))
            range_users.add(uid)
        try:
            if cost > 1:
                ok, retry = limiter.allow(_bucket(u), cost - 1)      # the envelope already took the request's own token
                if not ok:                             # a retry pays the envelope's token again first: wait for the whole cost
                    raise HTTPException(429, f"rate limit exceeded: {n} steps cost {cost} tokens",
                                        headers=_retry_after(retry + (1 / limiter.rate if limiter.rate > 0 else 0)))
            return health.assess_range(db, a.asset_id, policy_set, start, end, step, actor=uid)
        finally:
            with range_lock:
                range_users.discard(uid)
            range_slots.release()

    @app.get(f"{API}/assets/{{asset_id}}/assessment")
    def latest(asset_id: str, u: dict = Depends(need("read"))):
        a = health.latest_assessment(db, asset_id)
        if a is None:
            raise HTTPException(404, f"no assessment for asset {asset_id}")
        return a

    @app.post(f"{API}/assets/{{asset_id}}/clear-risk")
    def clear_risk(asset_id: str, body: ClearRiskBody, u: dict = Depends(need("asset_state.clear"))):
        if body.event != "dismissed":
            raise HTTPException(422, "maintenance is recorded by completing its work order with an outcome; only 'dismissed' (with a reason) "
                                     "can be recorded here")
        return {"state": health.clear_latched_risk(db, asset_id, body.event, actor=u["user_id"], role=u["role"], reason=body.reason).labels()}

    @app.post(f"{API}/decisions/generate")
    def generate(site_id: str | None = None, u: dict = Depends(need("decisions.generate"))):
        return decision.generate(db, dcfg, actor=u["user_id"], site_id=site_id)

    # -- work orders ----------------------------------------------------------------------------------------------------
    @app.get(f"{API}/work-orders")
    def orders(state: list[str] | None = Query(default=None), asset_id: str | None = None, u: dict = Depends(need("read"))):
        return workorders.list_orders(db, states_in=state, asset_id=asset_id)

    @app.get(f"{API}/work-orders/missing-outcomes")
    def missing(u: dict = Depends(need("read"))):
        return workorders.missing_outcomes(db)

    @app.get(f"{API}/work-orders/{{wo_id}}")
    def order(wo_id: str, u: dict = Depends(need("read"))):
        o = workorders.get(db, wo_id)
        if o is None:
            raise HTTPException(404, f"unknown work order {wo_id}")
        return o

    @app.get(f"{API}/work-orders/{{wo_id}}/history")
    def order_history(wo_id: str, u: dict = Depends(need("read"))):
        return workorders.history(db, wo_id)

    @app.post(f"{API}/work-orders", status_code=201)
    def create_order(body: CreateOrderBody, idempotency_key: str | None = Header(default=None), u: dict = Depends(need("workorders.write"))):
        if not idempotency_key:
            raise HTTPException(400, "the Idempotency-Key header is required to create a work order")
        _client_key(idempotency_key)
        if registry.get_asset(db, body.asset_id) is None:
            raise HTTPException(404, f"unknown asset {body.asset_id}")
        return workorders.create(db, asset_id=body.asset_id, job_type=body.job_type, priority_class=body.priority_class, title=body.title,
                                 origin="external" if u["role"] == "integration" else "manual", actor=u["user_id"], role=u["role"],
                                 idempotency_key=idempotency_key, due_by=body.due_by, description=body.description)

    @app.post(f"{API}/work-orders/{{wo_id}}/transitions")
    def transition(wo_id: str, body: TransitionBody, idempotency_key: str | None = Header(default=None), u: dict = Depends(need("workorders.write"))):
        return workorders.transition(db, wo_id, body.action, actor=u["user_id"], role=u["role"], reason=body.reason, data=body.data,
                                     expected_version=body.expected_version, idempotency_key=_client_key(idempotency_key))

    @app.post(f"{API}/work-orders/{{wo_id}}/reprioritise")
    def reprioritise(wo_id: str, body: ReprioritiseBody, u: dict = Depends(need("workorders.write"))):
        o = workorders.get(db, wo_id)
        if o is None:
            raise HTTPException(404, f"unknown work order {wo_id}")
        return workorders.reprioritise(db, wo_id, body.priority_class, None, parse_ts(body.due_by) if body.due_by else None,
                                       {**(o.get("explanation") or {}), "manual_reprioritisation": body.reason}, actor=u["user_id"], role=u["role"],
                                       reason=body.reason, expected_version=body.expected_version)

    @app.post(f"{API}/work-orders/{{wo_id}}/complete")
    def complete(wo_id: str, body: CompleteBody, idempotency_key: str | None = Header(default=None), u: dict = Depends(need("workorders.write"))):
        return workorders.complete(db, wo_id, actor=u["user_id"], role=u["role"], outcome=body.outcome, expected_version=body.expected_version,
                                   idempotency_key=_client_key(idempotency_key), non_clearing_jobs=decision.non_clearing_jobs(dcfg))

    # -- schedules ------------------------------------------------------------------------------------------------------
    @app.post(f"{API}/schedules")
    def plan(body: PlanBody, u: dict = Depends(need("schedules"))):
        if body.policy == "milp":                      # building the MILP does not stop at time_limit_s: bound its size first
            n_slots = math.floor(body.horizon_h / body.slot_h)
            n_orders = sum(1 for o in workorders.list_orders(db, states_in=["APPROVED"])
                           if (a := registry.get_asset(db, o["asset_id"])) is not None and a.site_id == body.site_id)
            if n_orders * n_slots > MILP_MAX_ORDER_SLOTS:
                raise HTTPException(422, f"milp is limited to {MILP_MAX_ORDER_SLOTS:,} approved orders x slots; site {body.site_id} has {n_orders} "
                                         f"approved orders x {n_slots} slots: use risk_greedy, a shorter horizon_h or a longer slot_h")
        return planning.plan(db, body.site_id, body.policy, actor=u["user_id"], role=u["role"], t0=parse_ts(body.t0) if body.t0 else None,
                             horizon_h=body.horizon_h, slot_h=body.slot_h)

    @app.get(f"{API}/schedules/{{run_id}}")
    def schedule(run_id: str, u: dict = Depends(need("read"))):
        r = planning.get(db, run_id)
        if r is None:
            raise HTTPException(404, f"unknown schedule run {run_id}")
        return r

    @app.post(f"{API}/schedules/{{run_id}}/apply")
    def apply(run_id: str, u: dict = Depends(need("schedules"))):
        return planning.apply(db, run_id, actor=u["user_id"], role=u["role"])

    # -- models ---------------------------------------------------------------------------------------------------------
    @app.get(f"{API}/models")
    def models_(asset_type_id: str | None = None, status: str | None = None, u: dict = Depends(need("read"))):
        return [_model_view(u, m) for m in modelreg.list_models(db, asset_type_id=asset_type_id, status=status)]

    @app.post(f"{API}/models/{{model_id}}/decision")
    def model_decision(model_id: str, body: ModelDecisionBody, u: dict = Depends(need("models.decide"))):
        return _model_view(u, modelreg.decide(db, model_id, body.decision, actor=u["user_id"], role=u["role"], reason=body.reason))

    @app.post(f"{API}/models/rollback")
    def rollback(body: RollbackBody, u: dict = Depends(need("models.decide"))):
        return _model_view(u, modelreg.rollback(db, body.asset_type_id, body.to_model_id, actor=u["user_id"], role=u["role"], reason=body.reason))

    # -- audit ----------------------------------------------------------------------------------------------------------
    @app.get(f"{API}/audit/verify")
    def audit_verify(anchor_seq: int | None = Query(default=None, ge=1, le=SQLITE_MAX_INT),
                     anchor_hash: str | None = Query(default=None, pattern=r"^[0-9a-f]{64}$"), u: dict = Depends(need("audit.read"))):
        """Without an anchor only the chain's internal consistency is checked (deleting the newest events cannot be
        detected): the result then says anchor_checked: false. An anchor needs both anchor_seq and anchor_hash."""
        if (anchor_seq is None) != (anchor_hash is None):
            raise HTTPException(422, "an anchor needs both anchor_seq and anchor_hash")
        anchor = {"seq": anchor_seq, "hash": anchor_hash} if anchor_seq is not None else None
        with db.connect() as c:
            return {**auditlog.verify(c, db.audit_key, anchor=anchor), "anchor_checked": anchor is not None}

    @app.get(f"{API}/audit/anchor")
    def audit_anchor(u: dict = Depends(need("audit.read"))):
        with db.connect() as c:
            return auditlog.anchor(c)

    @app.get(f"{API}/audit/{{entity}}/{{entity_id}}")
    def audit_entity(entity: str, entity_id: str, u: dict = Depends(need("read"))):
        if entity not in OPEN_AUDIT_ENTITIES and not security.allowed(u["role"], "audit.read"):
            raise PermissionDenied(f"role {u['role']!r} may not read the audit history of {entity!r} records")
        with db.connect() as c:
            rows = auditlog.history(c, entity, entity_id)
        if u["role"] != "admin":                       # integration hosts and error text, for audit.read too: see WITHHELD
            rows = [_withhold_integration_detail(r) for r in rows]
        return rows

    # -- exports --------------------------------------------------------------------------------------------------------
    @app.get(f"{API}/export/work-orders.csv", response_class=PlainTextResponse)
    def export_csv(state: list[str] | None = Query(default=None), u: dict = Depends(need("read"))):
        rows = workorders.list_orders(db, states_in=state)
        cols = ["wo_id", "asset_id", "origin", "job_type", "priority_class", "state", "title", "due_by", "scheduled_start", "scheduled_end",
                "duration_h", "required_skill", "external_ref", "created_by", "created_at", "updated_at"]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _csv_safe(r.get(k)) for k in cols})
        return PlainTextResponse(buf.getvalue(), media_type="text/csv")

    return app
