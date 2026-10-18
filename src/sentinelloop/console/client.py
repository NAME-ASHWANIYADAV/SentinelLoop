"""Thin client for the SentinelLoop REST API, used by the operator console.

The console never touches the database: every read and action goes through the API with the signed-in user's own
key, so the API's role checks, validation and audit apply to the console exactly as to any other client.
"""
from __future__ import annotations

import re
import uuid

import httpx

def md(s) -> str:
    """Wrap text that came from the API in an inline code span for st.markdown. Inside a code span markdown is not
    interpreted and no link, image or autolink can form; backticks and line breaks are replaced so nothing can close it."""
    text = re.sub(r"[\r\n\t]+", " ", str(s if s is not None else "")).replace("`", "'")
    return f"`{text}`" if text else "` `"


STATE_ORDER =["URGENT_REVIEW", "INSPECTION_RECOMMENDED", "DATA_QUALITY_FAILURE", "MODEL_UNAVAILABLE", "MODEL_OUT_OF_SCOPE", "AWAITING_ASSESSMENT",
               "NOT_ASSESSED", "NORMAL_MONITORING"]


class ApiError(RuntimeError):
    def __init__(self, status: int, message: str, request_id: str | None):
        super().__init__(f"{status}: {message}")
        self.status, self.message, self.request_id = status, message, request_id


class ConsoleClient:
    def __init__(self, http: httpx.Client, api_key: str, prefix: str = "/api/v1"):
        self.http, self.key, self.prefix = http, api_key, prefix.rstrip("/")

    @classmethod
    def connect(cls, base_url: str, api_key: str, timeout_s: float = 30.0) -> "ConsoleClient":
        u = base_url.rstrip("/")
        prefix = "/api/v1" if not u.endswith("/api/v1") else ""
        return cls(httpx.Client(base_url=u, timeout=timeout_s), api_key, prefix or "")

    def _req(self, method: str, path: str, **kw):
        headers = {"Authorization": f"Bearer {self.key}", **kw.pop("headers", {})}
        r = self.http.request(method, f"{self.prefix}{path}", headers=headers, **kw)
        if r.status_code >= 400:
            try:
                body = r.json()
            except Exception:
                body = {}
            msg = body.get("error") if isinstance(body, dict) else None
            raise ApiError(r.status_code, str(msg) if msg else f"the API returned HTTP {r.status_code}",   # never echo raw upstream bodies
                           body.get("request_id") if isinstance(body, dict) else None)
        return r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text

    # identity
    def me(self):
        return self._req("GET", "/me")

    # fleet
    def assets(self):
        rows = self._req("GET", "/assets")
        return sorted(rows, key=lambda a: (STATE_ORDER.index(a["state"][0]) if a["state"][0] in STATE_ORDER else 99, a["criticality"], a["asset_id"]))

    def asset(self, asset_id):
        return self._req("GET", f"/assets/{asset_id}")

    def assessment(self, asset_id):
        try:
            return self._req("GET", f"/assets/{asset_id}/assessment")
        except ApiError as e:
            if e.status == 404:
                return None
            raise

    def assess(self, asset_id, as_of: str | None = None):
        return self._req("POST", f"/assets/{asset_id}/assess", json={"as_of": as_of} if as_of else {})

    def clear_risk(self, asset_id, event, reason):
        return self._req("POST", f"/assets/{asset_id}/clear-risk", json={"event": event, "reason": reason})

    def sites(self):
        return self._req("GET", "/sites")

    def asset_types(self):
        return self._req("GET", "/asset-types")

    def models(self):
        return self._req("GET", "/models")

    # work
    def generate(self):
        return self._req("POST", "/decisions/generate")

    def orders(self, states=None):
        return self._req("GET", "/work-orders", params=[("state", s) for s in (states or [])])

    def order(self, wo_id):
        return self._req("GET", f"/work-orders/{wo_id}")

    def history(self, wo_id):
        return self._req("GET", f"/work-orders/{wo_id}/history")

    def transition(self, wo_id, action, expected_version=None, reason=None, data=None):
        return self._req("POST", f"/work-orders/{wo_id}/transitions", json={"action": action, "expected_version": expected_version, "reason": reason,
                                                                            "data": data or {}},
                         headers={"Idempotency-Key": f"console-{uuid.uuid4().hex}"})

    def complete(self, wo_id, outcome: dict, expected_version=None):
        return self._req("POST", f"/work-orders/{wo_id}/complete", json={"outcome": outcome, "expected_version": expected_version},
                         headers={"Idempotency-Key": f"console-{uuid.uuid4().hex}"})

    def reprioritise(self, wo_id, priority_class, reason):
        return self._req("POST", f"/work-orders/{wo_id}/reprioritise", json={"priority_class": priority_class, "reason": reason})

    def missing_outcomes(self):
        return self._req("GET", "/work-orders/missing-outcomes")

    # schedules
    def plan(self, site_id, policy="risk_greedy", horizon_h=72.0, t0=None):
        return self._req("POST", "/schedules", json={"site_id": site_id, "policy": policy, "horizon_h": horizon_h, "t0": t0})

    def apply(self, run_id):
        return self._req("POST", f"/schedules/{run_id}/apply")

    # audit and integrations
    def audit(self, entity, entity_id):
        return self._req("GET", f"/audit/{entity}/{entity_id}")

    def verify_audit(self):
        return self._req("GET", "/audit/verify")

    def integrations(self):
        return self._req("GET", "/integrations")

    def integration_items(self, target_id, status=None):
        return self._req("GET", f"/integrations/{target_id}/items", params={"status": status} if status else None)


def explanation_lines(wo: dict, fmt_time=str) -> list[str]:
    """Human-readable lines for an order's explanation; never shows a probability that does not exist. `fmt_time`
    formats instants (the console passes its site-local formatter)."""
    ex = wo.get("explanation") or {}
    out = []
    if ex.get("why"):
        out.append(f"Why: {ex['why']}")
    if ex.get("reasons"):
        out.append("Assessment reasons: " + "; ".join(ex["reasons"][:4]))
    if ex.get("p_fail_decision_horizon") is not None:
        out.append(f"Model-implied P(failure before {ex.get('decision_horizon_hours')} h): {ex['p_fail_decision_horizon']:.2f} "
                   f"(not calibrated: on simulated data the observed rate was higher, see evidence C2)")
    else:
        out.append("No failure probability: the model gives none for this case (anomaly model, or no valid prediction).")
    if ex.get("due_by"):
        out.append(f"Due by {fmt_time(ex['due_by'])} ({ex.get('due_by_rule', '')})")
    return out
