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
import time
import uuid

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from . import auditlog, decision, health, ingest, modelreg, planning, registry, resources, security, workorders
from .errors import PermissionDenied
from .models import AssetSpec
from .timeutil import iso, parse_ts

log = logging.getLogger("sentinelloop.api")
API = "/api/v1"
# audit histories any authenticated role may read; every other entity (users, credentials, ...) needs audit.read
OPEN_AUDIT_ENTITIES = {"asset", "assessment", "work_order", "schedule_run", "model", "ingestion_batch"}
FORMULA_LEAD = ("=", "+", "-", "@", "\t", "\r")


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
    slot_h: float = Field(default=1.0, gt=0, le=24)
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


def create_app(db, policy_set, decision_cfg: decision.DecisionConfig | None = None, rate_limit: tuple = (120, 2.0),
               max_body_bytes: int = 10 * 1024 * 1024) -> FastAPI:
    app = FastAPI(title="SentinelLoop platform API", version="1", docs_url=f"{API}/docs", openapi_url=f"{API}/openapi.json", redoc_url=None)
    limiter = security.RateLimiter(*rate_limit)
    dcfg = decision_cfg or decision.DecisionConfig()
    app.add_middleware(BodyLimit, limit=max_body_bytes)

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
            if request.url.path.endswith(("/health", "/ready")):
                ok, retry = True, 0
            else:
                u = security.authenticate_key(db, _presented_key(request.headers))
                bucket = f"user:{u['user_id']}" if u else f"addr:{request.client.host if request.client else 'unknown'}"
                ok, retry = limiter.allow(bucket)
            if not ok:
                resp = JSONResponse({"error": "rate limit exceeded", "request_id": rid}, status_code=429, headers={"Retry-After": f"{max(1, int(retry + 0.999))}"})
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
        return _err(request, exc.status_code, str(exc.detail))

    # -- health ---------------------------------------------------------------------------------------------------------
    @app.get(f"{API}/health")
    def health_():
        return {"status": "ok"}

    @app.get(f"{API}/ready")
    def ready():
        try:
            v = db.schema_version()
            with db.connect() as c:
                n_models = c.execute("SELECT COUNT(*) FROM models WHERE status = 'approved'").fetchone()[0]
            latest = len(db.migration_files())
            return {"database": "ok", "schema_version": v, "schema_current": v == latest, "approved_models": n_models,
                    "audit_key": "DEV-INSECURE" if db.insecure_dev_key else "configured"}
        except Exception as e:  # readiness must not raise
            return JSONResponse({"database": "error", "detail": type(e).__name__}, status_code=503)

    @app.get(f"{API}/me")
    def me(u: dict = Depends(current_user)):
        return u

    # -- registry -------------------------------------------------------------------------------------------------------
    @app.get(f"{API}/assets")
    def assets(site_id: str | None = None, status: str | None = None, u: dict = Depends(need("read"))):
        out = []
        for a in registry.list_assets(db, site_id=site_id, status=status):
            st = health.asset_state(db, a.asset_id)
            out.append({**a.model_dump(), "state": st.labels() if st else ["NOT_ASSESSED"]})
        return out

    @app.get(f"{API}/assets/{{asset_id}}")
    def asset(asset_id: str, u: dict = Depends(need("read"))):
        a = registry.get_asset(db, asset_id)
        if a is None:
            raise HTTPException(404, f"unknown asset {asset_id}")
        st = health.asset_state(db, a.asset_id)
        return {**a.model_dump(), "state": st.labels() if st else ["NOT_ASSESSED"], "state_notes": list(st.notes) if st else []}

    @app.post(f"{API}/assets", status_code=201)
    def create_asset(spec: AssetSpec, u: dict = Depends(need("assets.write"))):
        return registry.create_asset(db, spec, actor=u["user_id"]).model_dump()

    @app.patch(f"{API}/assets/{{asset_id}}")
    def patch_asset(asset_id: str, body: AssetPatchBody, u: dict = Depends(need("assets.write"))):
        return registry.update_asset(db, asset_id, body.changes, actor=u["user_id"], reason=body.reason).model_dump()

    @app.get(f"{API}/asset-types")
    def asset_types(u: dict = Depends(need("read"))):
        return [t.model_dump() for t in registry.list_asset_types(db)]

    # -- ingestion ------------------------------------------------------------------------------------------------------
    @app.post(f"{API}/ingest/readings")
    def ingest_readings(body: IngestBody, u: dict = Depends(need("ingest"))):
        return ingest.ingest_records(db, body.records, source=body.source, actor=u["user_id"], default_tz=body.default_tz).to_dict()

    @app.post(f"{API}/ingest/csv")
    async def ingest_csv(request: Request, source: str = Query(min_length=1), default_tz: str | None = None, wide_units: str | None = None,
                         u: dict = Depends(need("ingest"))):
        raw = await request.body()                     # BodyLimit caps it while it streams
        units = json.loads(wide_units) if wide_units else None
        return ingest.ingest_csv(db, raw, source=source, actor=u["user_id"], wide_units=units, default_tz=default_tz).to_dict()

    @app.get(f"{API}/ingest/batches/{{batch_id}}")
    def batch(batch_id: str, u: dict = Depends(need("read"))):
        b = ingest.batch(db, batch_id)
        if b is None:
            raise HTTPException(404, f"unknown batch {batch_id}")
        return b

    @app.get(f"{API}/ingest/staleness")
    def staleness(max_age_h: float = 6.0, site_id: str | None = None, u: dict = Depends(need("read"))):
        return ingest.staleness(db, max_age_ms=int(max_age_h * 3_600_000), site_id=site_id)

    # -- assessments and states -------------------------------------------------------------------------------------------
    @app.post(f"{API}/assets/{{asset_id}}/assess")
    def assess(asset_id: str, body: AssessBody = Body(default_factory=AssessBody), u: dict = Depends(need("assess"))):
        return health.assess(db, asset_id, policy=policy_set, as_of_ms=parse_ts(body.as_of) if body.as_of else None, actor=u["user_id"])

    @app.get(f"{API}/assets/{{asset_id}}/assessment")
    def latest(asset_id: str, u: dict = Depends(need("read"))):
        a = health.latest_assessment(db, asset_id)
        if a is None:
            raise HTTPException(404, f"no assessment for asset {asset_id}")
        return a

    @app.post(f"{API}/assets/{{asset_id}}/clear-risk")
    def clear_risk(asset_id: str, body: ClearRiskBody, u: dict = Depends(need("asset_state.clear"))):
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
        if registry.get_asset(db, body.asset_id) is None:
            raise HTTPException(404, f"unknown asset {body.asset_id}")
        return workorders.create(db, asset_id=body.asset_id, job_type=body.job_type, priority_class=body.priority_class, title=body.title,
                                 origin="external" if u["role"] == "integration" else "manual", actor=u["user_id"], role=u["role"],
                                 idempotency_key=idempotency_key, due_by=body.due_by, description=body.description)

    @app.post(f"{API}/work-orders/{{wo_id}}/transitions")
    def transition(wo_id: str, body: TransitionBody, idempotency_key: str | None = Header(default=None), u: dict = Depends(need("workorders.write"))):
        return workorders.transition(db, wo_id, body.action, actor=u["user_id"], role=u["role"], reason=body.reason, data=body.data,
                                     expected_version=body.expected_version, idempotency_key=idempotency_key)

    @app.post(f"{API}/work-orders/{{wo_id}}/complete")
    def complete(wo_id: str, body: CompleteBody, idempotency_key: str | None = Header(default=None), u: dict = Depends(need("workorders.write"))):
        return workorders.complete(db, wo_id, actor=u["user_id"], role=u["role"], outcome=body.outcome, expected_version=body.expected_version,
                                   idempotency_key=idempotency_key)

    # -- schedules ------------------------------------------------------------------------------------------------------
    @app.post(f"{API}/schedules")
    def plan(body: PlanBody, u: dict = Depends(need("schedules"))):
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
        return modelreg.list_models(db, asset_type_id=asset_type_id, status=status)

    @app.post(f"{API}/models/{{model_id}}/decision")
    def model_decision(model_id: str, body: ModelDecisionBody, u: dict = Depends(need("models.decide"))):
        return modelreg.decide(db, model_id, body.decision, actor=u["user_id"], role=u["role"], reason=body.reason)

    @app.post(f"{API}/models/rollback")
    def rollback(body: RollbackBody, u: dict = Depends(need("models.decide"))):
        return modelreg.rollback(db, body.asset_type_id, body.to_model_id, actor=u["user_id"], role=u["role"], reason=body.reason)

    # -- audit ----------------------------------------------------------------------------------------------------------
    @app.get(f"{API}/audit/verify")
    def audit_verify(anchor_seq: int | None = None, anchor_hash: str | None = None, u: dict = Depends(need("audit.read"))):
        anchor = {"seq": anchor_seq, "hash": anchor_hash} if anchor_seq is not None and anchor_hash else None
        with db.connect() as c:
            return auditlog.verify(c, db.audit_key, anchor=anchor)

    @app.get(f"{API}/audit/anchor")
    def audit_anchor(u: dict = Depends(need("audit.read"))):
        with db.connect() as c:
            return auditlog.anchor(c)

    @app.get(f"{API}/audit/{{entity}}/{{entity_id}}")
    def audit_entity(entity: str, entity_id: str, u: dict = Depends(need("read"))):
        if entity not in OPEN_AUDIT_ENTITIES and not security.allowed(u["role"], "audit.read"):
            raise PermissionDenied(f"role {u['role']!r} may not read the audit history of {entity!r} records")
        with db.connect() as c:
            return auditlog.history(c, entity, entity_id)

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
