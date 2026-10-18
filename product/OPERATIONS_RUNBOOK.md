# Operations runbook

These procedures are for the people who run a SentinelLoop deployment.
- **Exercised end-to-end:** backup, restore, audit verification, restart after a crash, and tamper detection, in recovery drill R1 (`product/evidence/recovery/r1.md`) on the development laptop.
- **Not yet exercised:** everything else here, on any real deployment.

Commands assume `SENTINELLOOP_AUDIT_KEY`, `SENTINELLOOP_AUDIT_KEY_ID` and `SENTINELLOOP_DB` are set (`DEPLOYMENT_GUIDE.md` §3).

## 1. Daily checks (about 5 minutes)

1. `GET /api/v1/ready` returns `database: ok`, `schema_current: true`, `audit_key: configured` and the expected `approved_models`.
2. `GET /api/v1/ingest/staleness?max_age_h=1` returns empty. If it does not, see §3.1.
3. Fleet in the console: count of DATA_QUALITY_FAILURE and MODEL_OUT_OF_SCOPE assets.
   - A sudden rise is a data or model problem, not a fleet problem (§3.1, §3.3).
   - A fleet-wide out-of-scope or unavailable state means the site's own inspection programme is the only schedule until it is fixed (`RELIABILITY_AND_SAFETY.md` §5).
4. Work queue: nothing P1 waiting more than a few hours for approval.
5. Integrations: `GET /api/v1/integrations/{id}/items?status=dead` is empty. Every dead letter is read by a person (§3.5).
6. Last night's backup exists, and `admin verify-audit` on it exits 0.

## 2. Routine procedures

### 2.1 Backup and verification

```bash
python -m sentinelloop.app.admin backup --to /backups/plant-2026-10-18.db
```
```bash
python -m sentinelloop.app.admin verify-audit --db /backups/plant-2026-10-18.db
```

- Keep the `.anchor.json` file with the backup and a copy apart from it. The anchor reveals truncation.
- Copy backups off the host.
- A backup made while the API is writing is consistent (SQLite online backup API, as used in R1).

### 2.2 Restore after loss or corruption

1. Stop the API.
2. Move the damaged database aside. Never delete it during an incident.
3. Restore to a **new path**:

```bash
python -m sentinelloop.app.admin restore --from /backups/plant-2026-10-18.db --db /srv/sentinelloop/plant-restored.db
```
```bash
python -m sentinelloop.app.admin verify-audit --db /srv/sentinelloop/plant-restored.db
```

4. Point `SENTINELLOOP_DB` at the restored file and start the API. Check `/ready`.
5. **Lost window.** Data and decisions after the backup are lost (RPO). Re-send the SCADA exports for the gap: ingestion is idempotent, so re-sending the overlap is safe. Re-run assessments.
6. Ask planners to check orders approved or completed during the gap against the CMMS, which keeps its own records.

R1 timings on the laptop: restore to ready 3.3 s; backup 0.15 s for 1 MB.

### 2.3 Model change and rollback

- A new model arrives as a bundle and is registered as a **candidate**.
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

- **Symptoms:** staleness report; DATA_QUALITY_FAILURE with `stale_data`, `missing_signal` or `stuck_signal`; batches with `rows_rejected`.
- **Actions:**
  1. Check the export job and the source system.
  2. For rejected rows, read the reason codes on the batch (`GET /ingest/batches/{id}`). Fix the mapping or units at the source. **Never** relax the contract to make rows pass.
  3. After the feed recovers, the state clears after two good assessments (hysteresis).

### 3.2 API errors (500)

- Each 500 carries a `request_id`. Find the JSON log line with that id in stdout. The response itself carries no internals.
- If errors persist, restart the API. State lives in the database (R1: restart to ready 3.0 s).

### 3.3 Model unavailable

- **Symptom:** MODEL_UNAVAILABLE with `checksum mismatch` or `artefact missing`.
- **Treat a checksum mismatch as a possible tampering incident** (`THREAT_MODEL.md` T3). Preserve the bundle directory and redeploy the bundle from its source. Otherwise roll back (§2.3).
- Latched warnings stay visible throughout.

### 3.4 Audit verification fails

1. Freeze changes: stop the API.
2. Preserve the database, the WAL files, the backups and the anchors.
3. Run `verify-audit` on the last backups to find when the chain was last good. `first_bad_seq` gives the first altered event.
4. Treat it as a security incident: who had write access to the file, and to the key?

### 3.5 CMMS integration dead letters

- **401/403:** the CMMS key expired or was revoked (Odoo keys last at most 3 months). Rotate the `SENTINELLOOP_CRED_*` variable, restart the API, then requeue with a reason.
- **422:** the CMMS rejected the data, e.g. a required field differs in this CMMS configuration. Fix the mapping before requeueing.
- **"more than one CMMS request carries the marker":** a person decides which record is SentinelLoop's and deletes or edits the other in the CMMS. Then requeue.

### 3.6 Disk filling up

- Check the database size and the backup directory.
- Readings retention is PLANNED. Until then, archive old backups off the host.
- SQLite needs free space roughly equal to the database size for a backup copy.
