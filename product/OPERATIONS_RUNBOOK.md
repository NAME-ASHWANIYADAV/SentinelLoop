# Operations runbook

These procedures are for the people who run a SentinelLoop deployment.
- **Exercised end-to-end:** backup, restore, audit verification against the backup's anchor, restart after a crash, and tamper and truncation detection, in recovery drill R1 (`product/evidence/recovery/r1.md`, re-run in Phase 9) on the development laptop.
- **Not yet exercised:** everything else here, on any real deployment.

Commands assume `SENTINELLOOP_AUDIT_KEY`, `SENTINELLOOP_AUDIT_KEY_ID` and `SENTINELLOOP_DB` are set (`DEPLOYMENT_GUIDE.md` §3). API paths are under `/api/v1`.

## 1. Daily checks (about 10 minutes)

1. `GET /api/v1/ready` returns `database: ok`, `schema_current: true`, `audit_key: configured`, `decision_config: site-configured` and the expected `approved_models`.
2. `GET /api/v1/ingest/staleness?max_age_h=<expected delivery interval>` returns empty: 1 for a live 10-minute feed; for daily exports, the export interval plus a margin. If it does not, see §3.1.
3. **Fleet** (console Fleet page, or `GET /api/v1/assets`):
   - Count of DATA_QUALITY_FAILURE and MODEL_OUT_OF_SCOPE assets. A sudden rise is a data or model problem, not a fleet problem (§3.1, §3.3).
   - If many assets show DATA_QUALITY_FAILURE at once, read the reasons of a few (`GET /api/v1/assets/{id}/assessment`). Reasons starting `data_delivery_delay` mean the whole feed is late: a data-path problem, for which no work order is raised (§3.1).
   - Any `ASSESSMENT_OVERDUE` label: assessments have stopped being applied for that asset (§3.7). Its state is the last known one; `last_assessed_at` says when.
   - A fleet-wide out-of-scope or unavailable state means the site's own inspection programme is the only schedule until it is fixed (`RELIABILITY_AND_SAFETY.md` §5).
   - **Replays that raised a warning** (export-fed sites). In the assessment job's `assess-range` responses, `replays_escalated` > 0 means that a replayed instant found URGENT_REVIEW or INSPECTION_RECOMMENDED and raised the asset's latch (PD-28). Check that the recommendations job ran after it, and read its result for that asset (`POST /api/v1/decisions/generate`). `created`, `escalated` or `linked` (or `unchanged`, naming an open order that already covers the warning) means the asset has its order. Running the job does not always give it one: the recommendation is built from the latest applied assessment, so if that assessment already produced an order for the same job, even one completed since, the result is `already_decided` and nothing is raised; `suppressed` means a rejection still holds (`decision._create_checked`). In either case the latch has no order: raise one by hand (`POST /api/v1/work-orders`; created after the warning began, it can clear it), or, if a person has established that the warning is not valid, dismiss it with a reason (§3.8). Tell the approver that the order's explanation cites the latest applied assessment, not the replay (KNOWN_LIMITATIONS M10). The durable record of the replay is the asset's audit history (`GET /api/v1/audit/asset/{id}`, action `asset_state.escalated_by_replay`, with the replayed instant). The asset's notes ("latch escalated by a historical replay ...", console Asset page) show it only until the next applied assessment, which rebuilds the notes (`states.advance`).
4. **Work queue.**
   - **P1 waiting time.** In the console each card waiting for approval shows "waiting N h", counted from the order's creation. Through the API: `GET /api/v1/work-orders?state=PENDING_APPROVAL` and compare `created_at` with now. No P1 should wait longer than the limit agreed with the site. For reference, a P1 without a failure-time prediction (every wind order) is due 24 h after the recommendation by default (`default_due_h`, `configs/decision.example.yaml`). Deferred orders whose date has passed reappear here after the recommendations job runs.
   - **Superseded and separate orders.** A system order whose explanation (`explanation.why`) contains "raised although WO-..." was raised next to an older open order for the same asset, which was left as it was. Either the older order was raised before the current warning began and was already approved, scheduled or in progress ("it was raised before the current latched condition began ..."), so completing it cannot clear the warning (§3.8). Or the older order is in progress for the current warning and the condition became more urgent ("the condition became more urgent": a separate, more urgent order). The planner decides whether the older order is still needed, and cancels it with a reason if not.
   - **Linked orders.** An older order for the recommended, inspection or urgent job that was awaiting approval or deferred is linked to the new warning instead. The engine escalates it in place, and a deferred one comes back for approval. Its explanation says "linked to it by this escalation": that is the reliable sign of a link. The console's generate message counts "earlier orders linked to a latched warning", but only links that changed neither the order's class nor its due date; a link that raised the class or brought the due date earlier (the usual case, e.g. a P2 inspection linked to an URGENT warning) is counted under "escalated" (`decision._escalate`). Approving it and completing it with a real finding clears the warning.
5. **Kept latches.** Completed orders whose outcome carries flags appear in the console under "Completed orders whose outcome needs review" (planners, reliability engineers, admins), or through `GET /api/v1/work-orders?state=COMPLETED` (`outcome.flags`). Treat `latch_kept` as in §3.8. Also read `asset_not_inspected` and `urgent_recommendation_not_confirmed`.
6. **Integrations:**
   - `GET /api/v1/integrations/{id}/items?status=dead` is empty. Every dead letter is read by a person (§3.5). The error text (`last_error`) is shown to admins only; other roles see "withheld: ask an administrator for the details".
   - A dead letter naming two or more CMMS request ids (a duplicate) needs a person in the CMMS before it is requeued (§3.5).
   - In the dispatch job's output, `busy: true` means another dispatch of the same target was still running, so this one sent nothing. Now and then it is harmless; the lease of a crashed run lapses after 10 minutes. A non-empty `stopped` gives the reason whenever a run sent less than it could: another run held the lease (with `busy: true`, so check `busy` first), the run's own lease lapsed, or the target's mode was changed or the target disabled during the run (`integration.STOPPED`); the next run carries on.
7. **Audit:** last night's backup exists and its anchor is off the host, and `admin verify-audit` on the live database against the previous anchor exits 0 (§2.1).

## 2. Routine procedures

### 2.1 Backup and verification

```bash
python -m sentinelloop.app.admin backup --to /backups/plant-2026-10-18.db
```

- This writes `/backups/plant-2026-10-18.db.anchor.json` beside the backup: the latest audit event's seq and hash.
- Copy the backup and the anchor off the host. **Keep every anchor**, in a place the database host cannot write to.
- A backup made while the API is writing is consistent (SQLite online backup API, as used in R1).

Verify the live database against the **previous** day's anchor, copied back from off the host:

```bash
python -m sentinelloop.app.admin verify-audit --db /srv/sentinelloop/plant.db --anchor /offhost/anchors/plant-2026-10-17.db.anchor.json
```

- Exit 0: every audit event up to that anchor is intact, and the chain after it is consistent.
- What it cannot show (PD-22): deletion of events newer than the anchor used; direct edits of state tables (users, asset states, work orders, readings).
- Without `--anchor` (and with no `<db>.anchor.json` next to the database) it exits 1. `--allow-no-anchor` checks internal consistency only; do not use it for the daily check. The same holds for `GET /api/v1/audit/verify` without `anchor_seq` and `anchor_hash`, and for the console's "Verify the audit chain" button, which sends no anchor: a truncated chain still shows `valid: True`. Both say that no anchor was checked (`anchor_checked: false`; the console shows "not verified against an anchor").
- An anchor file without an integer `seq` and a 64-hex `hash` is a configuration error (exit 2), never treated as "no anchor". A scheduled check must therefore alert on any exit other than 0, not only on exit 1.
- Verifying a backup against the anchor beside it shows only that the copy is self-consistent.
- Each new anchor's `seq` should be at least the previous one's. This comparison is manual; it is not automated.

### 2.2 Restore after loss or corruption

1. Stop the API.
2. Move the damaged database aside. Never delete it during an incident.
3. Restore to a **new path**. Restore copies the backup's anchor next to the restored file:

```bash
python -m sentinelloop.app.admin restore --from /backups/plant-2026-10-18.db --db /srv/sentinelloop/plant-restored.db
```
```bash
python -m sentinelloop.app.admin verify-audit --db /srv/sentinelloop/plant-restored.db --anchor /offhost/anchors/plant-2026-10-17.db.anchor.json
```

4. Point `SENTINELLOOP_DB` at the restored file and start the API. Check `/ready`.
5. **Lost window.** Data and decisions after the backup are lost (RPO). Re-send the SCADA exports for the gap: ingestion is idempotent, so re-sending the overlap is safe. Re-run the assessments for the gap in time order (`assess-range`, oldest first, one range at a time, at most 1,200 steps per call with the shipped rate limit; honour 429 `Retry-After`: `DEPLOYMENT_GUIDE.md` §6). Pause the scheduled assessment job before the API starts (step 4), and keep it, and the console's "Assess now", stopped until the gap ranges have run: an assessment at the default instant ("now" on a live-feed site, the new latest reading on an export-fed site) moves the last applied instant past the gap, and every gap instant after it is a replay that never moves the live state; only a new urgent or inspection finding raises the latch (`health.assess`, §3.1). Then run the recommendations job and restart the scheduled jobs.
6. Ask planners to check orders approved or completed during the gap against the CMMS, which keeps its own records.

R1 re-run timings on the laptop: backup 0.21 s for 1.0 MB; restore to ready 6.34 s; restart to ready after a hard kill 4.85 s.

### 2.3 Model change and rollback

- A new model arrives as a bundle and is registered on the host as a **candidate**. Registration refuses a bundle whose `bundle.pkl` does not match its manifest.
- A reliability engineer reads its manifest (data class, evaluation, limitations) and approves it with a reason. Approving retires the previous model for the same scope.
- For wind models, **re-commission** each turbine: baselines are per model.
- Rollback: `POST /api/v1/models/rollback` with `asset_type_id`, `to_model_id` and a reason. Assessments switch to the old model immediately.

### 2.4 Re-commissioning a turbine

Re-commission after any drivetrain component replacement, sensor replacement or retrofit:
1. Wait for at least two days of normal operation.
2. `POST /api/v1/assets/{id}/baseline` with the healthy period and the reason.

A period that already contains a developing fault hides that fault, so choose it with care.

### 2.5 Users and keys

| task | how |
|---|---|
| new user | `POST /api/v1/users`, then `POST /api/v1/users/{id}/api-key` (shown once) |
| leaver | `POST /api/v1/users/{id}/deactivate` with a reason; their key stops working at once |
| lost key | issue a new key (the old one is replaced) |

### 2.6 Audit-key rotation (PLANNED; procedure only)

There is no in-place re-keying.
1. Take a final backup and verify it with the old key. Archive the old key with that backup.
2. Start a new database generation under the new key.
3. Note the change in `DECISION_LOG`.

## 3. Incidents

### 3.1 Data stops or degrades (stale, missing, stuck, rejected rows)

- **Symptoms:** staleness report; DATA_QUALITY_FAILURE with `stale_data`, `missing_signal`, `excessive_missing`, `stuck_signal` or `out_of_range`; or `data_delivery_delay` when every required signal stopped together; batches with `rows_rejected`.
- **Actions:**
  1. Check the export job and the source system. `data_delivery_delay` is a feed problem, not an asset problem: no work order is raised for it, so nobody is sent to the turbine.
  2. For rejected rows, read the reason codes on the batch (`GET /ingest/batches/{id}`). Fix the mapping or units at the source. **Never** relax the contract to make rows pass.
  3. For export-fed sites, when the late export arrives: load it, then run `POST /assets/{id}/assess-range` over the **whole export**, from its first reading to its last, oldest first.
     - Do this before any assessment at the default instant: the scheduled `/assess`, or the console's "Assess now". The range must respect the limits in `DEPLOYMENT_GUIDE.md` §6 (at most 1,200 steps per call with the shipped rate limit, one range at a time per key, 429 with `Retry-After` otherwise).
     - Do not start the range at "the last applied instant". On a site that also assesses at "now", that instant is later than the export's last reading, so the range is refused or holds a single replay. On an export site whose scheduled job has already assessed the new latest reading, it is a single replay (re-review latching-states-01).
     - Instants after the last applied one are applied normally. Instants at or before it are stored as replays. A replay never lowers a latch or moves the live state. One that finds URGENT_REVIEW or INSPECTION_RECOMMENDED not already recorded for its instant raises the latch, with the replay's wall-clock time as the latch start. It is audited as `asset_state.escalated_by_replay`, and the response counts it in `replays_escalated` (PD-28).
  4. Run `POST /api/v1/decisions/generate`, and check its result for each asset whose latch a replay raised. `created`, `escalated` or `linked` (or `unchanged`, naming an open order that already covers the warning) means the latch has its order. On `already_decided` or `suppressed` it has none: raise the order by hand or dismiss the warning with a reason (§1 step 3). The order's explanation cites the latest applied assessment, not the replay (KNOWN_LIMITATIONS M10).
  5. After the feed recovers, the state clears after two good assessments (hysteresis). An assessment during a model outage counts only if its data checks passed.
- On an export-fed site (`assess_at: latest_reading`), a missing export shows differently: repeated assessments are for the same latest reading, so they are stored as replays, and after `max_assessment_age_hours` the assets show ASSESSMENT_OVERDUE (§3.7) while the staleness report lists their signals. Such a replay does not raise a finding that an earlier assessment of the same instant already had, so it never undoes a dismissal or a completed inspection.

### 3.2 API errors (500)

- Each 500 carries a `request_id`. Find the line `unhandled error <request_id>` and the traceback after it on the API's **stderr** (`DEPLOYMENT_GUIDE.md` §8: the per-request JSON lines are not emitted, and uvicorn's access log on stdout carries no request id). The response itself carries no internals.
- If errors persist, restart the API. State lives in the database (R1 re-run: restart to ready 4.85 s).

### 3.3 Model unavailable

- **Symptom:** MODEL_UNAVAILABLE with the reason `model_unavailable: <model>: artefact missing or failed its integrity check`, or `model_unavailable: scoring failed (<exception type>)`. Reasons carry no paths or messages; the line `model <id> unavailable: ...` on the API's stderr says whether the file is missing or its checksum does not match.
- **Treat a checksum mismatch as a possible tampering incident** (`THREAT_MODEL.md` T3). Preserve the bundle directory and redeploy the bundle from its source. Otherwise roll back (§2.3).
- A bundle already loaded is cached in the API process, so a file changed or removed while the API runs is noticed after the next restart.
- Latched warnings stay visible throughout.

### 3.4 Audit verification fails

1. Freeze changes: stop the API.
2. Preserve the database, the WAL files, the backups and the anchors.
3. Run `verify-audit` on the last backups and against the older anchors to find when the chain was last good. `first_bad_seq` gives the first altered or missing event.
4. Treat it as a security incident: who had write access to the file, and to the key?

### 3.5 CMMS integration dead letters

The connector has been tested against a contract test double only; it has never run against real Odoo (`INTEGRATION_GUIDE.md`, KNOWN_LIMITATIONS S1). The error text is in `last_error` of `GET /api/v1/integrations/{id}/items?status=dead`, shown in full to admins only.

- **401/403:** the CMMS key expired or was revoked (Odoo keys last at most 3 months). Rotate the `SENTINELLOOP_CRED_*` variable, restart the API, then requeue with a reason.
- **422:** the CMMS rejected the data, e.g. a required field differs in this CMMS configuration. Fix the mapping before requeueing.
- **"host ... is not in SENTINELLOOP_INTEGRATION_HOSTS"**, or a URL or credential-name error: the allowlist and the target's settings are checked again at every dispatch. If the host was removed on purpose, leave the items dead; otherwise correct `SENTINELLOOP_INTEGRATION_HOSTS`, restart the API, and requeue.
- **"credential environment variable ... is not set":** set the `SENTINELLOOP_CRED_*` variable in the API's environment, restart, requeue.
- **A config error** (for example "config 'database' must be an Odoo database name"): a value stored by an earlier version fails the check made at every live dispatch. A stored config cannot be changed; register the target again under a new id (`DEPLOYMENT_GUIDE.md` §7, KNOWN_LIMITATIONS S11).
- **"HTTP 200 from ... with a body that is not JSON (a sign-in or proxy page?)":** something other than Odoo's API answered, for example a single-sign-on or proxy page. Fix the URL or the proxy, then requeue. (A create or write answered this way is retried instead, because it may have been committed.)
- **`unexpected <type> while delivering this order (details in the server log)`:** read the traceback after `unexpected error delivering <wo_id> to <target>` on the API's stderr. Only that order failed; the run went on.
- **Duplicates: two CMMS requests for one order.** SentinelLoop never closes or deletes a CMMS record, so a person acts in the CMMS, then requeues. Which request is SentinelLoop's depends on the error:

  | error starts | meaning | what the person does |
  |---|---|---|
  | `more than one CMMS request carries the marker for <wo_id> (ids [...])` | after a lost mapping or a lost create answer, the search found several requests with the marker `[SentinelLoop-Ref:<wo_id>]`, and none was adopted | decide which request is SentinelLoop's, and make sure only that one carries the marker in its description (remove the marker from the others, or delete them in the CMMS). After the requeue, the next dispatch adopts the one left |
  | `CMMS requests [...] also carry the marker for <wo_id>; SentinelLoop's request is <id> (updated)` | a create whose answer was lost committed late. SentinelLoop's own request was updated first, so a withdrawal has reached it. The other request keeps whatever was written to it when it was created, possibly an approved, high-priority request | close or delete the other request in the CMMS. After the requeue, only SentinelLoop's request is written |
  | `two CMMS requests belong to <wo_id>: <first> (stored) and <second> (from a dispatch whose lease had lapsed)` | a dispatcher hung past its lease while another delivered the order | close or delete the second request. After the requeue, only the stored one is written |

  A create that commits after the re-check made about an hour after the recovery is not detected (KNOWN_LIMITATIONS S10).
- **`busy` and `stopped`** in the dispatch response are not dead letters. `busy: true` means another run of the target held the lease; nothing was sent, and `stopped` says so too. Otherwise a non-empty `stopped` names a lapsed lease, or a mode change or disabled target during the run; the next run carries on. A crashed run's lease lapses within 10 minutes, so `busy` for longer than that means a dispatch is still running: check the scheduler for overlapping or long-running dispatch jobs.
- Requeue: `POST /api/v1/integrations/{id}/items/{wo_id}/requeue` with a reason (admin).

### 3.6 Disk filling up

- Check the database size and the backup directory.
- Readings retention is PLANNED. Until then, archive old backups off the host.
- SQLite needs free space roughly equal to the database size for a backup copy.

### 3.7 Assessment overdue

- **Symptom:** `ASSESSMENT_OVERDUE` next to an asset's state: its last applied assessment is older than `max_assessment_age_hours` (6 h by default, 26 h for wind).
- **Meaning:** the state shown is the last known one and may be out of date. It is not a statement about the asset. After an upgrade from a database older than migration 0006, an asset whose state has no stored assessment shows it until its next applied assessment (migration 0008).
- **Actions:**
  1. Check the assessment job (cron or Task Scheduler) and its log. Check the API's output for `/assess` or `/assess-range`: uvicorn's access log on stdout shows each call's status, and stderr shows unhandled errors. A 429 on `assess-range` means the job sent ranges in parallel or faster than its rate limit pays for, or two other ranges were already running on the server (the limit of two is shared by all users): it must wait `Retry-After` seconds and resend. A 422 "split the range" means the range is longer than one call may be (`DEPLOYMENT_GUIDE.md` §6).
  2. On an export-fed site, check that the export arrived (§3.1).
  3. Run the assessments; the label goes at the next applied assessment.

### 3.8 A completed order kept the latch (`latch_kept`)

- **Symptom:** a completed order has the outcome flag `latch_kept`, and the asset still shows URGENT_REVIEW or INSPECTION_RECOMMENDED. The asset's notes (`GET /api/v1/assets/{id}`, `state_notes`) and the audit event `asset_state.latch_kept` give the reasons.
- **Why it happens** (PD-16, PD-28):
  - the outcome was `not_inspected` or `other`;
  - the job was a data or review job: `instrument_check`, `desk_review`, or the site's configured `data_job` or `review_job`;
  - it was completed by the `integration` role;
  - the warning's start is unknown;
  - or the order was "raised before the recorded start of the latched condition" and was never linked to it. The engine links an older order only if its job is the recommended, inspection or urgent job and it was awaiting approval or deferred when the recommendations job handled the warning: it escalates the order in place, and that escalation lets a qualifying completion clear the warning. An older order that was already approved, scheduled or in progress is superseded instead: the engine raises a new order that names it ("raised although WO-..."). A person re-prioritising an older order does not link it. A latch raised by a replay starts when the replay ran (§3.1). On a database upgraded to schema 7, the recorded start may be an upper bound set at the upgrade (migration 0007).
- **Actions** (planner or reliability engineer):
  1. If the equipment still needs inspecting, use the order the engine raised for the warning, or raise a **new** inspection order for it (created after the warning began); approve and schedule it. Completing that order with a real finding clears the warning. Completing an older order that was not linked does not. Cancel the older order with a reason if it is no longer needed.
  2. If a person has established that the warning is not valid, dismiss it with a written reason: `POST /api/v1/assets/{id}/clear-risk` with `{"event": "dismissed", "reason": "..."}`.
  3. Never record maintenance through `clear-risk`: it is refused.
