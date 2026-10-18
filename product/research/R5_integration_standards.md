# R5: Integration surfaces and standards

Research stream R5 for SentinelLoop. Accessed and written on 2026-10-18.

## How to read this document

- Every factual claim cites a source ID, for example [S24]. The Sources section at the end maps each ID to the URL that was opened in this session and gives the access date. Claims I could not verify carry the word **UNVERIFIED**.
- Where a fact comes from a vendor's pricing page or marketing page, it is labelled **vendor claim**. Vendor API documentation, OpenAPI files and Postman collections are treated as primary for what the API does. They are still the vendor's own description.
- Some facts were checked locally rather than read on a web page. These are labelled **local check**: HTTP probes with `curl`, registry metadata from the Docker Hub API, licence fields from the GitHub API, and the specs of the team's own machine. Nothing was installed or run against any vendor system. No account was created.
- **Data provenance.** This stream did not use any field data, laboratory data or new simulated data. It is documentation research. SentinelLoop itself has only been run on NASA C-MAPSS, which is **simulated** turbofan data (see `README.md`). Anything below about plant data, OPC UA tags or historians describes interfaces, not data we hold.
- **Tool limits during this session.** WebSearch hit its per-turn budget (a 200-call limit shared across the agents in this turn) partway through. Later items were checked only by fetching known primary URLs with WebFetch or `curl`. Several vendor documentation sites are JavaScript-rendered and returned no readable text: SAP Business Accelerator Hub, SAP Help Portal and AVEVA docs. These gaps are listed in section 7.

---

## 0. Summary for the team

1. **The only CMMS sandbox that is free, local and unrestricted is self-hosted open source.** Odoo Community (LGPL-3) ships the `maintenance` app and the external RPC/JSON-2 API in its public source [S36][S37][S38][S39], and an official Docker image exists [S40][S41]. Atlas CMMS (AGPL-3.0, Docker Compose, REST with Swagger) [S47][S48][S49] and ERPNext (GPL-3.0, REST `/api/resource/<DocType>`) [S51][S53] are second and third options.
2. **For the commercial SaaS CMMSs we looked at, API access sits on upper paid tiers.** UpKeep is Enterprise only [S21][S23]. MaintainX is Premium and Enterprise [S24][S27]. Limble is Premium+ and Enterprise [S29]. Fiix custom API integrations are Enterprise "for an additional cost" [S20]. eMaint lists "Access to eMaint APIs" under Enterprise [S32]. None of them offers a free API sandbox that we found. **However, MaintainX, Limble and eMaint publish machine-readable API specs that anyone can download without an account** (local check: [S24][S28][S30]). We can write adapters and contract tests against those specs without paying.
3. **SAP and IBM have shared or trial environments, with conditions.** The SAP Business Accelerator Hub sandbox for `API_MAINTNOTIFICATION` exists. It rejects calls without an `APIKey` header (local check [S1]), and the key comes from logging in with an SAP account [S8]. Whether that account is free, and whether the sandbox accepts writes, is **UNVERIFIED**. IBM Maximo offers a 14-day browser trial that expires automatically [S16]. IBM declined a developer-licence request on 10 March 2026 [S18].
4. **Odoo's legacy XML-RPC/JSON-RPC is deprecated.** The `db` service was removed in Odoo 20 (fall 2026). The `common` and `object` services are scheduled for removal in Odoo 22 (fall 2028) [S34]. Build the Odoo adapter on the JSON-2 API (`POST /json/2/<model>/<method>`, bearer API key) [S33][S38].
5. **Plant data access means OPC UA, MQTT/Sparkplug B, Modbus and historian REST APIs.** The safe pattern for an advisory tool is to read from a historian or a DMZ service, never from controllers. NIST SP 800-82r3 says enterprise-to-operations traffic should pass through services in a DMZ and points to unidirectional gateways as an option [S66]. The AVEVA PI Web API exposes a `DisableWrites` configuration setting [S62].
6. **SentinelLoop must sit outside every safety instrumented function (SIF).** IEC 61511 governs SIS in the process sector as an implementation of IEC 61508 [S75][S76]. The 61508 Association explains why a SIS is kept separate from the basic process control system (BPCS) [S77]. HSE counts SIS as part of industrial automation and control systems (IACS) and treats cyber security as part of plant safety [S78]. An ML advisory tool has no SIL claim and no write path, and should be documented as such.
7. **India.** Technician identities in work orders are personal data under the DPDP Act 2023 [S79]. The DPDP Rules 2025 (G.S.R. 846(E), 13 Nov 2025) bring Rule 6 (security safeguards, including keeping logs for one year) and Rule 7 (breach intimation, with details to the Board within 72 hours) into force 18 months after publication [S80]. CERT-In's April 2022 directions require incidents to be reported within 6 hours and ICT logs to be kept for 180 days inside India. They apply to any "body corporate" [S81].
8. **A checklist is not a certification and not a compliance claim.** ISASecure certifications are issued by ISO/IEC 17065-accredited certification bodies [S74]. Achieved security level (SL-A) is measured on the operating system at the plant [S72]. A SIL can only be claimed through the IEC 61508/61511 lifecycle. DPDP compliance is an obligation of the Data Fiduciary, which is the plant operator, and is adjudicated by the Data Protection Board [S79][S82]. See section 5.

---

## 1. (a) CMMS / EAM APIs

### 1.1 Comparison table

| System | API style (documented) | Authentication (documented) | Work-order / notification objects | Free sandbox without a paid account? |
|---|---|---|---|---|
| SAP S/4HANA (PM / EAM) | OData V2. `API_MAINTNOTIFICATION` (catalog ID `OP_API_MAINTNOTIFICATION`) [S3][S6]; `API_MAINTENANCEORDER` [S5] | Sandbox: `APIKey` request header (local check [S1]); key from "Show API Key" after login with an SAP ID [S8]. Production system auth: **UNVERIFIED** (SAP Help pages did not render) | Entity `A_MaintenanceNotification` [S4]; header `MaintenanceNotification` with `to_Item` navigation [S6]; order release action `ReleaseMaintenanceOrder` [S5] | Shared sandbox at `sandbox.api.sap.com`, login required [S1][S7][S8]. Free SAP account: **UNVERIFIED**. Write support in sandbox: **UNVERIFIED** |
| IBM Maximo Manage / MAS | REST/JSON API built on the OSLC code base. Lean JSON with `lean=1` [S14]; object structures as resources; `POST` to the collection URI to create [S13] | API key in an `apikey` header or query parameter; inherits the linked user's permissions [S11]. MAS Manage: API key and SAML. maxauth, BASIC and FORM are "not supported for MAS Manage" [S12] | Object structure `MXAPIWODETAIL` at `/maximo/api/os/mxapiwodetail` [S15]; `MXAPIASSET` in docs examples [S13]. Service request object (`MXAPISR`): **UNVERIFIED** | 14-day browser trial of Manage, Health and Visual Inspection; credentials expire after 14 days [S16][S17]. Developer licence request "Not under consideration" (10 Mar 2026) [S18]. API use inside the trial: **UNVERIFIED** |
| Fiix (Rockwell) | JSON over HTTP, CRUD plus RPC; client methods `find`, `findById`, `add`, `change`, `rpc`, `batch`; base `https://<tenant>.macmms.com/api` [S19] | Application Key + Access Key + Secret Key; secret shown once [S19]. HMAC signature scheme: **UNVERIFIED** (not on the guide page) | `WorkOrder` (needs site ID and status ID), `WorkOrderStatus`, `WorkOrderAsset`, `WorkOrderTask`, `Asset` [S19] | Sandbox only for "Active subscribers on Enterprise plans", on request [S19]. Free plan exists but "does not include custom API integrations" (vendor claim) [S20] |
| UpKeep | REST JSON, base `https://api.onupkeep.com/api/v2`; versioning header `upkeep-version` (default `2022-09-14`) [S21] | Organisation API token as `Authorization: Bearer` (recommended), or legacy `POST /auth` session token sent in a `Session-Token` header [S21] | `POST /api/v2/work-orders/` with `title`, `description`, `priority`, `startDate`, `dueDate`, `asset`, `location` [S21]; also Requests | No. "enabled only for accounts on the Enterprise Plan" [S21][S22][S23] |
| MaintainX | REST JSON, OpenAPI 3 published at `https://api.getmaintainx.com/v1/openapi.json` (local check) [S24] | `Authorization: bearer <key>`; key from Settings > Integrations > API Keys; `x-organization-id` header for multi-org tokens [S24][S25] | `/workorders` (only `title` required; optional `assetId`, `priority`, `dueDate`, `externalId`, `procedure`, …), `/workorders/external/{externalId}`, `/workrequests`, `/assets`, `/meters`, `/meterreadings`, `/metertriggers` [S24] | No. "API access is available on Premium and Enterprise plans" [S24]. Free Basic plan has no API (vendor claim) [S27]. Whether a Premium trial includes API keys: **UNVERIFIED** |
| Limble | REST over HTTPS; regional hosts `api`, `ca-api`, `au-api`, `eu-api`, `21cfr-api` `.limblecmms.com`; list `limit` max 1000 [S28] | HTTP Basic with base64 `client_id:client_secret`; generated by a Super Administrator; secret shown once [S28] | "Tasks (Work Orders, Preventive Maintenance, Work Requests, etc.)"; `POST /v2/tasks?name=&locationID=&due=&type=&templateID=` [S28] | No. Open REST API on Premium+ and Enterprise; no free trial shown (vendor claim) [S29] |
| eMaint (Fluke Reliability) | "eMaint X4 API v2", REST JSON; generic table-record operations [S30] | `GET /api/v2/GetLoginToken` with `username`, `password` and `XT-UserAgent` headers returns a JWT. The token is valid for 7 days and is bound to the same `Xt-UserAgent` [S30][S31] | `PUT /api/v2/record` with `{"table":"WORK","payload":{...}}`; `signOn`, `signOff`, `closeWorkOrder`, `approveRequest`, `rejectRequest`, `getAnyData` [S30] | No. "Access to eMaint APIs" listed under Enterprise; "Sandbox Staging Account" in Professional; only "Book a demo" (vendor claim) [S32] |
| Odoo (Community or Enterprise) | Odoo 19/20: JSON-2 `POST /json/2/<model>/<method>`. XML-RPC/JSON-RPC deprecated [S33][S34] | `Authorization: bearer <API key>`; optional `X-Odoo-Database` header [S33]. Keys need a description and a duration, with a maximum of three months [S33] | `maintenance.request` and `maintenance.equipment` (field list in 1.9) [S36] | Yes, self-hosted Community via Docker (free, LGPL-3) [S39][S40]. Odoo Online: external API "only available on Custom Odoo pricing plans" [S33][S34]. A temporary test database via `https://demo.odoo.com/start` is documented in the Odoo 18 docs [S35] |

### 1.2 SAP S/4HANA (Plant Maintenance / EAM)

- **Service names and protocol.** Cognite's SAP writeback guide is vendor documentation from an industrial data platform. It names the standard OData V2.0 API `OP_API_MAINTNOTIFICATION` for maintenance notifications and supports S/4HANA on-premise 2021 FPS01 and later, plus S/4HANA Cloud [S3]. A third-party integration repository labels the same service with base URL name `API_MAINTNOTIFICATION`, header entity `MaintenanceNotification`, and navigation to `to_Item` and `to_ItemCause` [S6]. SAP KBA 3787252 names the entity `A_MaintenanceNotification`. It reports that POST and full-entity GET can be slow on systems with very large numbers of equipment and functional locations, and that selecting fewer fields speeds things up [S4].
- **Maintenance orders.** SAP KBA 3756977 confirms `API_MAINTENANCEORDER` and its `ReleaseMaintenanceOrder` action. It also documents that a release from CRTD to REL is "rejected silently" when components are short and must then be forced in IW32 [S5]. This matters for an advisory tool. A successful API call is not proof that the order reached the state we expected, so the connector must read the status back.
- **Notification or order?** For an advisory product, the notification is the natural object: it is a report or request that a planner then turns into an order. That is a design judgement, not a documented SAP rule. It matches how Cognite writes back to SAP through notifications [S3].
- **Sandbox.** `https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/API_MAINTNOTIFICATION/$metadata` returns HTTP 401 `"Failed to resolve API Key variable request.header.apikey"` when no key is sent (local check [S1]). The same 401 comes back for `API_MAINTENANCEORDER` [S2]. That error is returned by the gateway before any service lookup, so it does not prove the order service exists in the sandbox. SAP Learning says you get the key by logging in with an SAP ID and choosing "Show API Key" [S8]. The SAP Developers tutorial says you must be logged on to use Try Out [S7]. SAP PRESS notes that OData APIs can be test-called against a sandbox, but SOAP APIs cannot [S9]. **UNVERIFIED:** whether the SAP Universal ID is free (sap.com returned 403), whether the sandbox accepts POST, rate limits, and the exact property list. The Business Accelerator Hub API pages and the catalog OData endpoint redirect to a login and did not render [S10].
- **Production authentication** (communication arrangements, communication users, OAuth or X.509): **UNVERIFIED**. SAP Help pages returned no readable text.

### 1.3 IBM Maximo Manage / Maximo Application Suite (MAS)

- **API style.** The newer REST/JSON API shares its code base with the OSLC API. It drops the OSLC namespaces and uses lean JSON (`lean=1`) [S14]. Records are created with `POST` to an object-structure collection URI such as `/oslc/os/mxapiasset`. The `properties` header controls what the response returns, `x-method-override: PATCH` is used for updates, and `patchtype: MERGE` is used for child objects [S13].
- **Authentication.** API keys can be sent as an `apikey` header or query parameter on every call, and they inherit the permissions of the linked Manage user. Keys are created in Integration > API Keys or by POST to `/oslc/os/mxapiapikey` [S11]. For MAS Manage, the native `maxauth` header, BASIC and FORM login are each marked "Not supported for MAS Manage"; API key and SAML are supported [S12].
- **Work orders.** An IBM Community answer shows `GET https://<host>/maximo/api/os/mxapiwodetail?savedQuery=ASSIGNEDWOLIST&lean=1...` [S15]. This is a community answer, not product documentation. Field-level schema for `MXAPIWODETAIL` and the service request object structure: **UNVERIFIED**.
- **Sandbox.** IBM's trial page says the 14-day trial covers Maximo Manage, Health and Visual Inspection, runs in the browser, and expires automatically after 14 days [S16][S17]. IBM idea MASM-I-1237 asked for a developer or trial licence. It is "Not under consideration" (admin response 10 Mar 2026), and IBM points to its software evaluation programme and to partner entitlements (silver and above) [S18]. The trial page suggests re-registering with a different email to keep exploring [S16]. **Do not** re-register repeatedly to stretch the trial; check IBM's terms first.

### 1.4 Fiix

- API: client methods `find`, `findById`, `add`, `change`, `rpc`, `batch` against `https://<subdomain>.macmms.com/api`. Credentials are Application Key, Access Key and Secret Key, and the guide recommends a restricted user group [S19].
- Work-order objects: `WorkOrder` requires a site ID and a status ID. Related objects are `WorkOrderStatus`, `WorkOrderAsset` and `WorkOrderTask` [S19].
- Sandbox: "Active subscribers on Enterprise plans can request a sandbox environment" [S19].
- Plans (vendor claim): Free, Basic and Professional each "does not include custom API integrations". Enterprise has them "for an additional cost". The Integration Hub offers "an Open API", but the page does not say which plan it belongs to [S20].

### 1.5 UpKeep

- Base URL `https://api.onupkeep.com/api/v2`. The recommended credential is an organisation API token (`Authorization: Bearer`) tied to the account, not to a person. The legacy session token from `POST /auth` is tied to a user and breaks if that user is deactivated or changes password [S21].
- Create work order: `POST /api/v2/work-orders/` with `title`, `description`, `priority`, `startDate`, `dueDate`, `asset`, `location` [S21].
- "The UpKeep API is enabled only for accounts on the Enterprise Plan" [S21]. The help centre lists the feature as "Available On: Enterprise" [S22]. The pricing page lists "API & custom integrations" only on Enterprise and offers a free trial of Essential and Premium (vendor claim) [S23].

### 1.6 MaintainX

- The public OpenAPI file (local check, about 1.39 MB, downloaded without authentication) declares server `https://api.getmaintainx.com/v1`, a bearer security scheme, and "API access is available on Premium and Enterprise plans" [S24].
- `POST /workorders` requires only `title`. Optional fields include `assetId`, `assignees`, `description`, `dueDate`, `externalId`, `priority`, `procedure`, `workRequestId` and `locationId`. `/workorders/external/{externalId}` supports GET, PATCH and DELETE, which gives idempotent upserts keyed on our own order ID. The spec also has `/workrequests`, `/meters`, `/meterreadings` and `/metertriggers` [S24].
- Multi-organisation tokens need `x-organization-id`. A request without it gets a 400 [S25].
- Pricing page (vendor claim): Basic is "Free forever" without the API; Premium lists "Open REST API access" [S27].

### 1.7 Limble

- The public Postman collection (local check) says the API uses "BASIC authorization standards" with a base64 client ID and secret. A Super Administrator generates the keys under Settings > Configuration > API Settings, and the secret is shown once. There are regional hosts, a list limit of 1000 (a request above that returns 422), signed webhooks, and rate limiting [S28].
- Work items are "Tasks (Work Orders, Preventive Maintenance, Work Requests, etc.)". Creation is `POST /v2/tasks?name=&locationID=&due=&type=&templateID=` [S28].
- Pricing (vendor claim): Standard has no "Open REST API". Premium+ and Enterprise include it. The page offers "Schedule demo" and shows no free trial [S29].

### 1.8 eMaint

- The public Postman collection (local check) describes "eMaint X4 API v2": JWT tokens, proper status codes, and a response format driven by the `Accept` header [S30].
- Authentication: `GET https://x46.emaint.com/api/v2/GetLoginToken` with `username`, `password` and `XT-UserAgent` headers. Tokens are "valid for 7 days" and paired with the same `Xt-UserAgent`. `GetLoginToken` may be called from any server, but other calls must go to the returned `serverUrl` [S30]. Tulip's connector documentation describes the same flow [S31].
- Work orders use generic record operations: `PUT /api/v2/record` with `{"table":"WORK","payload":{"wo":"[AUTO]","brief_desc":...,"assignid":...}}`. There are dedicated calls `signOn`, `signOff`, `closeWorkOrder`, `approveRequest` and `rejectRequest` [S30].
- Pricing (vendor claim): Enterprise lists "Access to eMaint APIs". Professional lists a "Sandbox Staging Account". The only call to action is "Book a demo" [S32].

### 1.9 Odoo (models `maintenance.request`, `maintenance.equipment`)

- **API (Odoo 19 and 20).** `POST /json/2/<model>/<method>` with `Authorization: bearer <API key>`, `Content-Type: application/json` and an optional `X-Odoo-Database` header [S33][S34]. In the Community source, the route is defined in `addons/rpc/controllers/json2.py` with `auth='bearer'`. The `rpc` addon is LGPL-3 and `auto_install: True`, so self-hosted Community has it [S38]. API keys are created under Preferences > Account Security, need a description and a duration, and "it is not possible to create keys that last for more than three months" [S33].
- **Deprecation.** The XML-RPC and JSON-RPC endpoints `/xmlrpc`, `/xmlrpc/2` and `/jsonrpc` are deprecated. "The db service was removed in Odoo 20 (fall 2026)". The common and object services "are scheduled for removal in Odoo 22 (fall 2028)" [S34].
- **Hosted plans.** "Access to data via the external API is only available on Custom Odoo pricing plans", not on One App Free or Standard [S33][S34]. This applies to Odoo's paid hosting. Self-hosted Community is not a pricing plan.
- **`maintenance.request` fields** (Odoo 19 source [S36]): `name` (required), `company_id` (required), `description` (HTML), `request_date`, `owner_user_id`, `equipment_id`, `user_id` (string "Technician"), `stage_id`, `priority` (selection '0' Very Low, '1' Low, '2' Normal, '3' High), `maintenance_type` (corrective or preventive, default corrective), `schedule_date`, `schedule_end`, `maintenance_team_id` (required, has a default), `duration`, `kanban_state`, `archive`, `close_date`, and recurrence fields.
- **`maintenance.equipment` fields** [S36]: `name`, `category_id`, `serial_no`, `model`, `partner_id` (vendor), `technician_user_id`, `owner_user_id`, `warranty_date`, `cost`, `effective_date`, `expected_mtbf`, and computed `mtbf`, `mttr`, `estimated_next_failure` ("Computed as Latest Failure Date + MTBF") and `latest_failure_date`.
- Module manifest: `'license': 'LGPL-3'`, depends only on `mail` [S37].

---

## 2. (b) Open-source CMMS a developer can run locally

### 2.1 Comparison table

| Candidate | Licence | How to run | Image sizes (Docker Hub, compressed, amd64; local check of registry metadata) | Stated resource needs | How to create a maintenance request via API |
|---|---|---|---|---|---|
| **Odoo Community 19/20** | LGPLv3 [S39]; maintenance module LGPL-3 [S37] | Official image needs a PostgreSQL container: `docker run -d -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo -e POSTGRES_DB=postgres --name db postgres:15`, then `docker run -p 8069:8069 --name odoo --link db:db -t odoo`. Volumes `/var/lib/odoo` and `/mnt/extra-addons`. No official Enterprise image [S40] | `odoo:19.0` about 699 MB; `odoo:latest` (20.0) about 800 MB; `postgres:15` about 158 MB; `postgres:16-alpine` about 116 MB [S41] | Production sizing guide: about 150 MB per light worker and about 1 GB per heavy worker, for example 9 workers ≈ 3 GB [S42]. Footprint of a single-user development setup: **UNVERIFIED** (not measured) | `POST /json/2/maintenance.request/create` with bearer key (pattern from [S33]; model from [S36]) |
| **Atlas CMMS** | Dual: AGPL-3.0 or commercial; a `LICENSE_KEY` unlocks advanced features, white-label and custom logos [S47] | `docker-compose up -d` with the repo's `docker-compose.yml`, `nginx.conf` and `.env` [S47]. Services: `postgres:16-alpine`, `intelloop/atlas-cmms-backend`, `intelloop/atlas-cmms-frontend`, `pgsty/silo` (object storage), `nginx:1.27-alpine`; no memory limits set [S48] | backend `latest` about 280 MB; frontend about 54 MB [S50] | Not stated [S47][S48] | Spring Boot controllers: `POST /auth/signin`, `/work-orders`, `POST /requests`; Swagger UI at `/swagger-ui/**`, `/v3/api-docs/**` (springdoc dependency) [S49]. Runtime behaviour not tested (**UNVERIFIED**) |
| **ERPNext (Frappe)** | ERPNext GPL-3.0; frappe_docker MIT (GitHub API) [S53] | `docker compose -f pwd.yml up -d` (disposable demo, "non-production") [S53] | `frappe/erpnext:v16` about 972 MB [S53] | Not stated in the README lines checked (**UNVERIFIED**) | `POST /api/resource/<DocType>` with `Authorization: token api_key:api_secret`, or OAuth bearer, or session [S51]. Doctypes: Asset Maintenance (plan with task rows), Asset Maintenance Log (auto-generated), Asset Maintenance Team, Asset Repair [S52] |
| **openMAINT 2.4** (on CMDBuild 4.2) | AGPL, copyright PAT srl. The Mobile App and Self-Service portal are proprietary and only for Maintenance Service subscribers [S44] | Bare install: Tomcat 10, Java 17, PostgreSQL 17.x; download from SourceForge; "Docker: Optional" [S43]. A third-party image `itmicus/cmdbuild:om-2.4.2-4.2.0` exists (not official) [S46] | `itmicus/cmdbuild:om-2.4.2-4.2.0` about 896 MB [S46] | **16 GB RAM, 4 cores, 150 GB free disk per instance**, SSD recommended [S43] | CMDBuild REST v3: `POST http://host:port/cmdbuild/services/rest/v3/sessions` to get a session; send the `Cmdbuild-authorization` header on every request [S45]. Cards are created with `POST /services/rest/v3/classes/{class}/cards` (from the forum snippet in search results; the manual confirms only sessions and the header, so **UNVERIFIED**). openMAINT's maintenance-request process name: **UNVERIFIED** |

**Local check against the team's machine [L1]:** 15.3 GB RAM, 12 logical processors, 24 GB free on C:, Docker 28.5.1 installed. This is below openMAINT's stated minimum of 16 GB RAM and 150 GB disk [S43]. Odoo Community plus PostgreSQL, at roughly 0.9 GB of compressed images [S41], is the realistic first sandbox. I did not pull or run any image. Pulling about 1 GB of images and executing them needs the user's go-ahead. The actual RAM footprint should be measured with `docker stats` once it runs.

### 2.2 Recommendation for the sandbox order (team judgement, not a sourced fact)

1. **Odoo Community** as the reference CMMS. It is LGPL, has a small, well-documented model, and the current JSON-2 API.
2. **Atlas CMMS** as a second, differently shaped schema. It proves that the connector is an adapter and not Odoo-specific. Mind the AGPL: if we modify and serve it over a network, AGPL obligations apply. We only call its API, which is a different case. Have a mentor or lawyer confirm.
3. **ERPNext** if a plant prospect already runs Frappe or ERPNext.
4. **Contract tests** against the MaintainX OpenAPI and the Limble and eMaint Postman collections, using mock servers generated from those files. This proves request shapes without paid accounts. It is not proof of integration, and we should not claim it is.

---

## 3. (c) Industrial data access

### 3.1 Protocols a plant may expose

| Interface | What it is (sourced) | Security notes (sourced) | Free tooling for a student testbed (licence from GitHub; local check [S64]) |
|---|---|---|---|
| **OPC UA** (IEC 62541) | "a platform independent service-oriented architecture". Client/server request-response services: browse, read/write current and historical data, subscriptions, events, methods. PubSub for many-to-many [S54]. IEC 62541-1:2025 replaced IEC TR 62541-1:2020 (withdrawn 2026-01-13) [S55] | Session encryption, message signing, sequenced packets against replay, X.509 application authentication, user authentication, access rights and address-space views, audit logging [S54] | `opcua-asyncio` (LGPL-3.0, Python ≥ 3.10, client and server, history read, encryption) [S56]; `open62541` (MPL-2.0) [S64] |
| **MQTT 5.0** | OASIS Standard, 7 Mar 2019; client-server publish/subscribe over TCP/IP; QoS 0/1/2 [S57] | Implementations "SHOULD offer Authentication, Authorization and secure communication options". TLS servers "should use TCP port 8883". Authorisation should check the client ID. Avoid NULL-encryption cipher suites [S57] | Eclipse Mosquitto broker (EPL-2.0 or BSD-3-Clause), Eclipse Paho Python client (EPL-2.0 / EDL-1.0) [S64] |
| **Sparkplug B** (Sparkplug 3.0, ISO/IEC 20237) | Topic namespace `namespace/group_id/message_type/edge_node_id/[device_id]`. Message types NBIRTH, NDEATH, DBIRTH, DDEATH, NDATA, DDATA, NCMD (Edge Node command), DCMD (Device command), STATE. Protobuf payloads; payload A deprecated [S60]. Sparkplug 3.0 was published as an international standard, "also known as ISO/IEC 20237" (Eclipse, 7 Nov 2023) [S59] | Birth and death certificates give state awareness; "Uses TLS for transport" (Eclipse marketing page) [S58]. **NCMD and DCMD are the write or command channel**, so a read-only consumer must never publish them [S60] | Eclipse Tahu, the Sparkplug reference implementation (EPL-2.0) [S64] |
| **Modbus** | Modbus Application Protocol V1.1b3 defines the function codes [S61] | "The Modbus Security protocol provides protection through the blending of Transport Layer Security (TLS) with the traditional Modbus protocol"; X.509v3 certificates for client and server; "uses port 802" [S61]. NIST: many Purdue Level 0 devices and protocols "cannot be authenticated", which opens them to replay, modification and spoofing [S66]. Classic Modbus/TCP port 502 and the read/write function-code numbers: **UNVERIFIED** (spec PDFs not opened) | `pymodbus` (BSD-style licence) [S64] |
| **AVEVA PI System (PI Web API)** | REST access to PI Data Archive and PI AF. AVEVA's own Python sample calls `/attributes?path=...`, `/streams/{webId}/value` and `/streams/{webId}/recorded?startTime=*-2d` [S62] | Sample supports HTTP Basic and Kerberos (default `kerberos`). PI Web API has a **`DisableWrites`** configuration attribute (the write sample needs it set to False) [S62]. Default value of `DisableWrites`, and OIDC/bearer support: **UNVERIFIED** (AVEVA docs did not render [S63]) | None free. PI is commercial software (licence terms **UNVERIFIED**) |
| Other historians (for example Ignition, Canary, AspenTech IP.21, InfluxDB) | Not researched in this session because the search budget ran out: **UNVERIFIED** | | |

### 3.2 What SentinelLoop must support to read data in a plant (team judgement built on the sources above)

Minimum viable read path, in order of preference:

1. **Historian REST API (PI Web API or equivalent) reached from the DMZ or the enterprise side.** Use recorded and interpolated reads of named tags or attributes with a dedicated read-only service account, and ask the plant to set `DisableWrites` where PI Web API is used [S62]. NIST SP 800-82r3: "Any communications between the enterprise level and the operations management level are required to go through services within the DMZ" [S66].
2. **OPC UA client subscription** to a server the plant chooses (often an aggregating server at Level 2/3, not a PLC), using Sign & Encrypt and a user whose server-side access rights allow reads only. OPC UA supports access rights and views [S54].
3. **MQTT/Sparkplug B subscriber** with a broker ACL that allows `SUBSCRIBE` on `spBv1.0/<group>/#` and denies all publishing. The client never publishes NCMD or DCMD [S57][S60]. If SentinelLoop registers as a Sparkplug Host Application, the spec requires it to publish STATE messages [S60]. An Edge Node may change its behaviour based on its configured Primary Host's state, for example by buffering data while that host is offline [S60]. So SentinelLoop must never be configured as any edge node's Primary Host (team judgement). The simplest read-only stance is a plain MQTT subscriber.
4. **Modbus.** Do not poll field devices from the product. If Modbus is the only option, the plant OT team should run the gateway, and only read function codes should be used (function-code numbers **UNVERIFIED** here).
5. **File or batch export** (CSV or Parquet dropped by the plant) is a valid first pilot path, and it is the one SentinelLoop already handles, since C-MAPSS is file-based.

### 3.3 Read-only patterns (sourced where stated)

- **DMZ mediation.** Enterprise-to-operations traffic goes through DMZ services. The services in the DMZ "must be monitored and protected" against pivoting [S66].
- **Unidirectional gateway or data diode.** "permits authorized communication in only one direction". One deployed between Layers 2 and 3 may protect Levels 0–2 from events at Levels 3–5 [S66].
- **Server-side enforcement, not client discipline.** Rely on PI `DisableWrites`, OPC UA user access rights and MQTT broker ACLs (refs above), not on the product's own promise to read only.
- **Data linkage risk.** NIST lists automatic historian-to-other-database replication as a vulnerability when misconfigured [S66]. Any replica we consume should be set up by the plant and documented.
- **IIoT read-only monitoring** may be secured differently from control devices because its operational impact is lower [S66].

---

## 4. (d) Security and safety standards

### 4.1 IEC 62443 (ISA/IEC 62443)

- **Series structure** (ISA page, titles): 2-1 (2024) asset-owner security programme; TR 2-2 (2025) protection scheme; TR 2-3 (2015) patch management; 2-4 (2018) service providers; 3-2 (2020) security risk assessment for system design; 3-3 (2013) system security requirements and security levels; 4-1 (2018) secure product development lifecycle; 4-2 (2018) component technical requirements. Roles are asset owners, product suppliers, integrators and service suppliers [S69].
- **Zones and conduits.** IEC 62443-3-2:2020 partitions the system under consideration into "zones and conduits", assesses risk for each, and sets a target security level (SL-T) for each [S70]. A zone is "a grouping of systems and components based on their functional, logical, and physical relationship". A conduit is "a logical or physical grouping of communication channels connecting two or more zones" (Dragos, secondary) [S72].
- **Security levels.** IEC 62443-3-3:2013 gives system requirements for the seven foundational requirements and defines capability security levels (SL-C). Practitioners use it with zones and conduits to set SL-T. IEC lists it at CHF 380 [S71]. SL-T is the target, SL-C what a system natively provides, and SL-A the achieved level measured on the operating solution (secondary) [S72]. Attacker-based definitions (secondary, from pera.net) [S73]:
  - SL 1: "Protection against casual or coincidental violation"
  - SL 2: intentional violation "using simple means with low resources, generic skills, and low motivation"
  - SL 3: "sophisticated means with moderate resources", IACS-specific skills, moderate motivation
  - SL 4: "sophisticated means with extended resources", IACS-specific skills, high motivation

  The normative wording is in the paid IEC text, which we have not read (**UNVERIFIED** against the standard itself).
- **Certification.** ISASecure certifies components against IEC 62443-4-2 (CSA), systems against 3-3 (SSA) and development organisations against 4-1 (SDLA). Certification is done by "ISO/IEC 17065 accredited certification bodies" [S74].
- **What it means for SentinelLoop (team judgement).** As a product supplier, the relevant parts are 4-1 (how we develop) and 4-2 (what the component can do). As a deployed tool, SentinelLoop is a component inside the asset owner's zone and conduit design, normally in the DMZ or the enterprise zone, and the asset owner sets SL-T. We can document design choices that map to 4-2 requirement areas. We cannot claim an SL-C without assessment.

### 4.2 NIST SP 800-82 Rev. 3 (and the Rev. 4 draft)

- *Guide to Operational Technology (OT) Security*, final, September 2023 (dated 09/28/23), superseding Rev. 2. It covers ICS, SCADA, DCS, PLCs, building automation and more [S65][S66].
- Segmentation: organisations may use "the Purdue model [Williams], ISA-95 levels [IEC62264], the three-tier IIoT system architecture", and may add a DMZ as an enforcement boundary (Fig. 16) [S66].
- Security objectives include "using unidirectional gateways, utilizing a demilitarized zone (DMZ) network architecture with firewalls", and separate credentials for corporate and OT networks [S66].
- Safety: "Organizations should consider whether the additional communication and cybersecurity requirements of safety systems (e.g., segmentation and the isolation of safety systems from other OT systems) is required". Safety may require physical rather than logical separation [S66].
- **Rev. 4 status:** an Initial Public Draft was published 21 Sep 2026, with comments due 30 Nov 2026. It is reorganised around CSF 2.0 and adds asset management, network monitoring and zero-trust guidance [S67]. The earlier pre-draft call ran from 22 Jan 2026 to 23 Feb 2026 and listed AI/ML, digital twins and behavioural anomaly detection among the topics [S68]. Rev. 3 remains the final version as of 2026-10-18 [S65][S67].

### 4.3 The Purdue model

- NIST traces ISA-95 to the "Purdue Reference Model for Computer Integrated Manufacturing (CIM)". It grew from the Purdue Enterprise Reference Architecture (PERA), which ISA first published in 1992 [S66].
- Level usage in NIST: "site-wide supervisory or optimization servers (i.e., Level 3 and above of the Purdue model)"; "control systems or field devices, such as sensors or final elements (i.e., Level 1 and 0 of the Purdue model)"; "Field I/O (Purdue Level 0)". In the DCS architecture example, the field level covers Purdue levels 0, 1 and 2, the operations management level includes Level 3, and the DMZ bridges operations management and enterprise [S66].
- **Placement for SentinelLoop (team judgement):** analytics and dashboard at Level 3.5 (DMZ) or Level 4 (enterprise). Data comes from a Level 3 historian through a DMZ service or a diode. Writes go only to the CMMS at Level 4. Nothing runs at Levels 0–2.

### 4.4 IEC 61508 / IEC 61511: why an advisory system must not be part of a SIF

- IEC 61508-1:2010 covers E/E/PE safety-related systems and "has the status of a basic safety publication" [S75].
- IEC 61511-1:2016+AMD1:2017 sets requirements for specifying, designing, installing, operating and maintaining a SIS, and is the process-sector implementation of IEC 61508:2010 [S76].
- NIST defines a SIS as "composed of sensors, logic solvers, and final control elements whose purpose is to take the process to a safe state". A SIS is made up of one or more SIFs [S66].
- The 61508 Association gives these reasons a SIS "is normally separated from the BPCS" [S77]:
  - "To reduce common cause, common mode and systematic failures"
  - to keep BPCS changes flexible
  - to make SIS validation easier
  - "To support access security and enhance cyber security for the SIS"

  It also says that compliance with IEC 61511-1 clause 11.2 requires separation considerations across sensors, final elements, logic solver and wiring [S77].
- HSE: SIS are included in IACS, and cyber security "is therefore part of the overall safety of plant and equipment". HSE cites BS EN 61511 and ISA-TR84.00.09-2013 for SIS security [S78].
- **Consequence for SentinelLoop (team judgement grounded in the above).**
  - SentinelLoop is advisory. It has no SIL, no IEC 61508 systematic-capability evidence, and a statistical model whose coverage misses its target on one subset (FD004 0.85, `README.md`).
  - It must never be a sensor, logic solver or final element of a SIF.
  - Its outputs must not be credited as a protection layer in the plant's risk analysis.
  - It must have no network path that can write to the SIS or the BPCS.
  - Work orders it drafts go to people through the CMMS.

  State this in the product documentation and in any pilot agreement.
- IEC 61511's security risk assessment clause (often cited as 8.2.4): **UNVERIFIED**. Only secondary search snippets mention it, and the standard text was not available.

### 4.5 India: Digital Personal Data Protection Act 2023 and DPDP Rules 2025

- **Personal data.** "any data about an individual who is identifiable by or in relation to such data" (s.2(t)). Data Fiduciary: the person who "determines the purpose and means of processing". Data Processor: "processes personal data on behalf of a Data Fiduciary" (s.2(i), 2(k)) [S79]. The Act applies to digital personal data processed in India (s.3) [S79].
- **Technician data is in scope once we integrate with a CMMS.** Odoo has `maintenance.request.user_id` ("Technician"), `owner_user_id` and `maintenance.equipment.technician_user_id` [S36]. MaintainX has `assignees` and `requesterId` [S24]. eMaint has per-technician `signOn` and `signOff` [S30]. If SentinelLoop stores or logs these, it processes personal data.
- **Lawful basis for employers (the plant).** s.7(i) allows processing "for the purposes of employment or those related to safeguarding the employer from loss or liability…" [S79]. Whether this covers analytics on technician performance is a legal question: **UNVERIFIED**, needs counsel.
- **Our likely role** as a vendor is Data Processor under a contract. The Data Fiduciary "may engage… a Data Processor… only under a valid contract" (s.8(2)) and stays responsible (s.8(1)) [S79].
- **Security and breach.** s.8(5) requires "reasonable security safeguards to prevent personal data breach". s.8(6) requires intimation to the Board and to each affected person [S79]. Rule 6 sets minimums [S80]:
  - "encryption, obfuscation, masking or the use of virtual tokens"
  - access control
  - logs and monitoring
  - continued processing after a compromise
  - "retain such logs and personal data for a period of one year"
  - contract clauses with processors

  Rule 7 requires intimation to each affected person "without delay", and to the Board "without delay" plus a detailed report "within seventy-two hours" [S80].
- **Retention and erasure.** s.8(7) requires erasure once "the specified purpose is no longer being served" unless the law requires retention, and the Fiduciary must have its Processor erase too [S79]. s.12 gives a right to erasure "for the processing of which she has previously given consent" [S79]. How that applies to employment-basis processing: **UNVERIFIED**.
- **Penalties (Schedule).** Failure to take reasonable security safeguards: up to ₹250 crore. Failure to notify a breach: up to ₹200 crore [S79].
- **Commencement.** The DPDP Rules 2025 were notified as G.S.R. 846(E), dated 13 November 2025. Rules 1, 2 and 17–21 apply on publication. Rule 4 applies after one year. Rules 3, 5–16, 22 and 23 apply "eighteen months after the date of publication" [S80], which works out to about **13 May 2027** (my calculation). MeitY was inviting applications for Data Protection Board Chairperson and Member posts in May 2026 [S82]. Any later amendment of these dates: **UNVERIFIED**, because the search budget ran out before it could be checked.
- **Design tension with the hash-chained audit log (team judgement).** If technician names or IDs are hashed into the chain, erasure under s.8(7) breaks chain verification. Option: write only a per-deployment pseudonymous token into the chain and keep the token-to-person map in a separate, erasable, access-controlled table owned by the plant. Pseudonymous tokens can still be personal data if the person is identifiable "in relation to such data" [S79], so both stores are in scope. Get legal review before any pilot.

### 4.6 India: CERT-In Directions of 28 April 2022 (No. 20(3)/2022-CERT-In)

- Issued under section 70B(6) of the IT Act 2000. They apply to "service providers, intermediaries, data centres, body corporate and Government organisations" [S81].
- Requirements [S81]:
  - Synchronise ICT clocks to NIC or NPL NTP servers, or sources traceable to them.
  - Report Annexure I incidents "within 6 hours of noticing".
  - Designate a Point of Contact.
  - Keep "logs of all their ICT systems… for a rolling period of 180 days… within the Indian jurisdiction".
  - The directions became effective "after 60 days from the date on which it is issued".
- Annexure I includes "Attacks on Critical infrastructure, SCADA and operational technology systems", "Data Breach", "Data Leak", attacks on IoT, cloud systems, and "Artificial Intelligence and Machine Learning" systems [S81].
- **Relevance (team judgement).** If the team incorporates as a company and hosts SentinelLoop, it becomes a body corporate in scope. The plant is in scope regardless. SentinelLoop's 180-day log retention, NTP sync and incident-reporting hooks should be designed in. Note the different log-retention minimums: 180 days under CERT-In and one year under DPDP Rule 6, for personal-data access logs.
- Later CERT-In guidelines (for example on audits): **UNVERIFIED** (not checked).

---

## 5. What implementing a checklist does NOT achieve

If SentinelLoop builds an "IEC 62443 / NIST 800-82 / DPDP / CERT-In checklist", the following remain **untrue** and must not be claimed:

1. **No IEC 62443 certification.** ISASecure CSA, SSA and SDLA certifications are issued by ISO/IEC 17065-accredited certification bodies [S74]. A self-assessment is not one of them.
2. **No security level claim.** SL-C must be assessed. SL-A is measured on the operating solution at the asset owner's site [S71][S72]. A checklist gives neither.
3. **No "NIST compliant".** SP 800-82r3 is a guide [S65]. Following it is not a compliance status, and Rev. 4 is still a draft [S67].
4. **No functional-safety claim.** No SIL, no suitability for use in a SIF, and no credit as an independent protection layer (section 4.4) [S75][S76][S77].
5. **No DPDP compliance claim.** The obligations fall on the Data Fiduciary (s.8(1)), and breaches are adjudicated by the Data Protection Board [S79][S82]. A vendor can only provide features and contractual support. Most operative Rules are not in force until about May 2027 [S80].
6. **No CERT-In compliance claim.** Reporting duties and log duties sit with each in-scope entity [S81].
7. **No vendor certification or partnership.** Calling the SAP sandbox, the MaintainX spec or Odoo is not an SAP-certified, IBM-validated or vendor-listed integration. Vendor certification programmes: **UNVERIFIED** (not researched).
8. **No evidence of field performance.** Every SentinelLoop result is on simulated C-MAPSS data (`README.md`). Integration with a sandbox CMMS does not change that.

Recommended wording for documents: *"Designed with reference to IEC 62443-4-2 requirement areas and NIST SP 800-82r3 guidance; not assessed or certified. Advisory only; not part of any safety instrumented function."*

---

## 6. Concrete integration design for SentinelLoop (team proposals, labelled as such)

### 6.1 Field mapping from `WorkOrderBook` orders [L2] to CMMS objects

SentinelLoop order fields (from `src/sentinelloop/agent.py`): `id`, `unit`, `type` (INSPECTION or MAINTENANCE), `severity` (CRITICAL, HIGH, MEDIUM, WATCH), `status`, `created_cycle`, `due_by_cycle`, `action`, `rul_point`, `rul_lower`, `rul_upper`, `top_sensors`, `anomaly_score`, `reasons`, `rules_fired`, `model_version`, `ts` [L2].

| SentinelLoop | Odoo `maintenance.request` [S36] | MaintainX `POST /workorders` [S24] | UpKeep `POST /work-orders/` [S21] | eMaint `record` table WORK [S30] | Limble `POST /v2/tasks` [S28] | SAP notification |
|---|---|---|---|---|---|---|
| title (built from action, unit, severity) | `name` (required) | `title` (required) | `title` | `brief_desc` | `name` | Field name **UNVERIFIED** |
| unit, mapped to asset | `equipment_id` | `assetId` | `asset` | **UNVERIFIED** field | via `locationID` and asset link (**UNVERIFIED**) | technical object field **UNVERIFIED** |
| severity | `priority` '0'–'3' | `priority` enum `NONE`, `LOW`, `MEDIUM`, `HIGH` | `priority` (number) | **UNVERIFIED** | **UNVERIFIED** | **UNVERIFIED** |
| type INSPECTION / MAINTENANCE | `maintenance_type` corrective / preventive (mapping is a team choice) | `type` enum `OTHER`, `REACTIVE`, `PREVENTIVE` | n/a | n/a | `type` (integer) | notification type **UNVERIFIED** |
| due_by_cycle, converted to a date | `schedule_date` | `dueDate` (date-time) | `dueDate` | **UNVERIFIED** | `due` | **UNVERIFIED** |
| evidence (RUL interval, top sensors, reasons, model version, audit hash) | `description` (HTML) | `description`; `externalData` | `description` | **UNVERIFIED** | comment via `/v2/tasks/:id/comments` | long text **UNVERIFIED** |
| our order `id` (idempotency) | search by a custom field (team choice) | `externalId` and `/workorders/external/{externalId}` | **UNVERIFIED** | **UNVERIFIED** | **UNVERIFIED** | **UNVERIFIED** |

Design rules:

- Create a **request or notification** (Odoo request, MaintainX work request, SAP notification) when `escalate_to_human` is true. Create a work order only when the plant explicitly opts in. This keeps a person in the loop, which matches SentinelLoop's escalation design.
- Read back the CMMS state after every write, because SAP release can fail silently [S5].
- Use rotating keys: Odoo keys last at most 3 months [S33] and eMaint tokens 7 days [S30]. Keep secrets out of the repository.
- Do not copy technician identities into SentinelLoop's audit chain (section 4.5).

### 6.2 Free, local test bench (all simulated)

- **CMMS:** Odoo Community in Docker [S40][S41].
- **OT side:** `opcua-asyncio` server, Mosquitto broker and Eclipse Tahu for Sparkplug, and `pymodbus`, all free [S56][S64]. Replay C-MAPSS cycles through them.
- **Label every result** "simulated C-MAPSS data replayed through a simulated OT protocol stack". It is not field or laboratory data.
- **Contract tests** against the MaintainX OpenAPI and the Limble and eMaint Postman collections [S24][S28][S30].

---

## 7. Gaps and UNVERIFIED items

- SAP: production authentication (communication arrangements, OAuth, X.509), whether the SAP Universal ID is free, sandbox write support, and full property lists. The SAP Hub and Help Portal render with JavaScript or need a login [S10].
- IBM Maximo: `MXAPIWODETAIL` field schema, the service request object structure, and API-key use inside the 14-day trial.
- Fiix: request-signing details (HMAC) and whether Free-plan users can generate API keys at all.
- MaintainX: whether the Premium "Try for free" trial includes API keys.
- eMaint and Limble: asset, priority and due-date field names for work orders.
- openMAINT: the process or class used for maintenance requests and the card-creation endpoint (forum snippet only).
- Atlas CMMS and Odoo: actual runtime RAM and disk; no container was run.
- PI Web API: default of `DisableWrites` and supported authentication beyond Basic and Kerberos. Other historians not researched.
- Modbus: classic port and function-code numbers (spec PDFs not opened). MQTT 3.1.1 as ISO/IEC 20922 (search snippet only).
- IEC 62443 SL wording (secondary sources only). IEC 61511 security risk assessment clause (secondary only).
- DPDP: amendments to the commencement dates after 13 Nov 2025, and whether the employment legitimate use covers performance analytics.
- CERT-In: guidance issued after 2022. Sector rules, for example power-sector cyber regulations: not researched.

---

## Sources

All accessed 2026-10-18. Pages that returned nothing readable are marked so that the reader knows the claim rests on another source.

**SAP**
- [S1] https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/API_MAINTNOTIFICATION/$metadata (local `curl` probe: HTTP 401, APIKey required)
- [S2] https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/API_MAINTENANCEORDER/$metadata (local `curl` probe: HTTP 401, APIKey required)
- [S3] https://docs.cognite.com/cdf/integration/guides/interfaces/sap_writeback.md
- [S4] https://userapps.support.sap.com/sap/support/knowledge/en/3787252
- [S5] https://userapps.support.sap.com/sap/support/knowledge/en/3756977
- [S6] https://github.com/latonaio/sap-api-integrations-maintenance-notification-reads
- [S7] https://developers.sap.com/tutorials/hcp-abh-getting-started.html
- [S8] https://learning.sap.com/courses/exploring-sap-business-technology-platform/illustrating-the-sap-business-accelerator-hub_c913055d-dbfb-4b85-84c9-508eb7468236
- [S9] https://blog.sap-press.com/connecting-sap-business-accelerator-hub-to-sap-s4hana-cloud
- [S10] https://api.sap.com/api/API_MAINTNOTIFICATION/overview and https://api.sap.com/odata/1.0/catalog.svc/APIContent.APIs('API_MAINTNOTIFICATION') (opened; JavaScript-rendered, redirects to login; no readable content). Also tried with no readable content: https://help.sap.com/docs/SAP_S4HANA_CLOUD/f9ba73d1b8c543c2bd2ba1666271af86/061b31b90a88432fad5e710aa9cd175c.html

**IBM Maximo**
- [S11] https://www.ibm.com/docs/SSLPL8_cd/com.ibm.mif.doc/gp_intfrmwk/c_api_keys_comp.html
- [S12] https://ibm-maximo-dev.github.io/maximo-restapi-documentation/authentication/auth
- [S13] https://ibm-maximo-dev.github.io/maximo-restapi-documentation/crud/create_and_update
- [S14] https://ibm-maximo-dev.github.io/maximo-restapi-documentation/overview/overview
- [S15] https://community.ibm.com/community/user/discussion/rest-call-to-get-all-work-orders-where-user-has-assignments-on
- [S16] https://www.ibm.com/products/maximo/resources/thank-you
- [S17] https://www.ibm.com/products/maximo/resources/trial
- [S18] https://ibm-ai-apps.ideas.ibm.com/ideas/MASM-I-1237

**Fiix, UpKeep, MaintainX, Limble, eMaint**
- [S19] https://fiixlabs.github.io/api-documentation/guide.html (redirect target of https://www.fiixsoftware.com/api/docs/guide.html)
- [S20] https://fiixsoftware.com/pricing/ (vendor pricing page)
- [S21] https://developers.onupkeep.com/
- [S22] https://help.onupkeep.com/en/articles/2477562-how-do-i-use-upkeep-s-public-apis
- [S23] https://upkeep.com/pricing/ (vendor pricing page)
- [S24] https://api.getmaintainx.com/v1/openapi.json (downloaded and parsed locally; also https://api.getmaintainx.com/v1/docs, JavaScript-rendered)
- [S25] https://help.getmaintainx.com/build/authentication
- [S26] https://help.getmaintainx.com/build/getting-started
- [S27] https://www.getmaintainx.com/pricing (vendor pricing page)
- [S28] https://apidocs.limblecmms.com/ and its public Postman collection https://apidocs.limblecmms.com/api/collections/5190375/SVfRsT5S?environment=5035798-41cef2c7-4a31-4972-8c79-c44673fee0f8&segregateAuth=true&versionTag=latest (downloaded and parsed locally)
- [S29] https://limble.com/pricing (vendor pricing page; redirect target of https://limblecmms.com/pricing/)
- [S30] https://api.x4.emaint.com/ and its public Postman collection https://api.x4.emaint.com/api/collections/17558505/2sB2j3Ar6b?environment=8774629-3c8535c4-205e-4903-b047-73340227b57f&segregateAuth=true&versionTag=latest (downloaded and parsed locally)
- [S31] https://support.tulip.co/docs/emaint-connector
- [S32] https://www.emaint.com/pricing/ (vendor pricing page)

**Odoo**
- [S33] https://www.odoo.com/documentation/19.0/developer/reference/external_api.html
- [S34] https://www.odoo.com/documentation/20.0/developer/reference/external_api.html
- [S35] https://www.odoo.com/documentation/18.0/developer/reference/external_api.html
- [S36] https://raw.githubusercontent.com/odoo/odoo/19.0/addons/maintenance/models/maintenance.py
- [S37] https://raw.githubusercontent.com/odoo/odoo/19.0/addons/maintenance/__manifest__.py
- [S38] https://raw.githubusercontent.com/odoo/odoo/19.0/addons/rpc/controllers/json2.py and https://raw.githubusercontent.com/odoo/odoo/19.0/addons/rpc/__manifest__.py (also checked: https://raw.githubusercontent.com/odoo/odoo/19.0/addons/web/controllers/json.py)
- [S39] https://raw.githubusercontent.com/odoo/odoo/19.0/LICENSE
- [S40] https://raw.githubusercontent.com/docker-library/docs/master/odoo/README.md (source of the Docker Hub page https://hub.docker.com/_/odoo)
- [S41] https://hub.docker.com/v2/repositories/library/odoo/tags?page_size=100 and https://hub.docker.com/v2/repositories/library/postgres/tags?page_size=100 (registry metadata via `curl`)
- [S42] https://www.odoo.com/documentation/19.0/administration/on_premise/deploy.html

**Other open-source CMMS**
- [S43] https://www.openmaint.org/en/download/latest-version
- [S44] https://tecnoteca.com/en/products/openmaint
- [S45] https://www.cmdbuild.org/file/manuali/versione-4.0/cmdbuild_webservicemanual_eng_v40.pdf (CMDBuild Webservice Manual v4.0, June 2025; text extracted locally)
- [S46] https://hub.docker.com/v2/repositories/itmicus/cmdbuild/tags?page_size=5&ordering=last_updated (third-party image metadata)
- [S47] https://github.com/Grashjs/cmms (also https://raw.githubusercontent.com/Grashjs/cmms/main/README.MD, https://raw.githubusercontent.com/Grashjs/cmms/main/LICENSE, https://api.github.com/repos/Grashjs/cmms)
- [S48] https://raw.githubusercontent.com/Grashjs/cmms/main/docker-compose.yml
- [S49] https://raw.githubusercontent.com/Grashjs/cmms/main/api/src/main/java/com/grash/controller/WorkOrderController.java, https://raw.githubusercontent.com/Grashjs/cmms/main/api/src/main/java/com/grash/controller/RequestController.java, https://raw.githubusercontent.com/Grashjs/cmms/main/api/src/main/java/com/grash/controller/AuthController.java, https://raw.githubusercontent.com/Grashjs/cmms/main/api/src/main/java/com/grash/configuration/SwaggerSecurityConfig.java, https://raw.githubusercontent.com/Grashjs/cmms/main/api/pom.xml
- [S50] https://hub.docker.com/v2/repositories/intelloop/atlas-cmms-backend/tags?page_size=5&ordering=last_updated and https://hub.docker.com/v2/repositories/intelloop/atlas-cmms-frontend/tags?page_size=5&ordering=last_updated
- [S51] https://docs.frappe.io/framework/user/en/api/rest
- [S52] https://docs.frappe.io/erpnext/user/manual/en/asset-maintenance
- [S53] https://api.github.com/repos/frappe/erpnext, https://api.github.com/repos/frappe/frappe_docker, https://raw.githubusercontent.com/frappe/frappe_docker/main/README.md, https://hub.docker.com/v2/repositories/frappe/erpnext/tags?page_size=5&ordering=last_updated

**Industrial data access**
- [S54] https://opcfoundation.org/about/opc-technologies/opc-ua/
- [S55] https://webstore.iec.ch/publication/61109
- [S56] https://github.com/FreeOpcUa/opcua-asyncio
- [S57] https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html
- [S58] https://sparkplug.eclipse.org/
- [S59] https://newsroom.eclipse.org/node/39754
- [S60] https://sparkplug.eclipse.org/specification/version/3.0/documents/sparkplug-specification-3.0.0.pdf (text extracted locally)
- [S61] https://www.modbus.org/modbus-specifications (fetched with `curl`; https://www.modbus.org/specs.php returned 403 to WebFetch)
- [S62] https://github.com/AVEVA/sample-pi_web_api-common_actions-python (also https://raw.githubusercontent.com/AVEVA/sample-pi_web_api-common_actions-python/main/README.md and https://raw.githubusercontent.com/AVEVA/sample-pi_web_api-common_actions-python/main/read_attributes.py; https://api.github.com/orgs/AVEVA/repos)
- [S63] https://docs.aveva.com/bundle/pi-web-api-reference/page/help.html (opened; JavaScript-rendered, no readable content)
- [S64] Licence checks via GitHub API and licence files: https://api.github.com/repos/eclipse-mosquitto/mosquitto, https://raw.githubusercontent.com/eclipse-mosquitto/mosquitto/master/LICENSE.txt, https://api.github.com/repos/eclipse-tahu/tahu, https://api.github.com/repos/pymodbus-dev/pymodbus, https://raw.githubusercontent.com/pymodbus-dev/pymodbus/dev/LICENSE, https://api.github.com/repos/open62541/open62541, https://api.github.com/repos/FreeOpcUa/opcua-asyncio, https://api.github.com/repos/eclipse-paho/paho.mqtt.python, https://raw.githubusercontent.com/eclipse-paho/paho.mqtt.python/master/LICENSE.txt

**Security and safety standards**
- [S65] https://csrc.nist.gov/pubs/sp/800/82/r3/final
- [S66] https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-82r3.pdf (full text extracted locally)
- [S67] https://csrc.nist.gov/pubs/sp/800/82/r4/ipd
- [S68] https://csrc.nist.gov/pubs/sp/800/82/r4/iprd
- [S69] https://www.isa.org/standards-and-publications/isa-standards/isa-iec-62443-series-of-standards
- [S70] https://webstore.iec.ch/en/publication/30727
- [S71] https://webstore.iec.ch/publication/7033
- [S72] https://dragos.com/blog/isa-iec-62443-concepts (secondary)
- [S73] https://pera.net/FAQ/faq_What_SL0-5.html (secondary)
- [S74] https://isasecure.org/
- [S75] https://webstore.iec.ch/en/publication/5515
- [S76] https://webstore.iec.ch/en/publication/24241
- [S77] https://61508.org/wp-content/uploads/2023/11/Intro-Combined-BPCS-SIS-V2_.pdf (The 61508 Association, Rev 2 18/12/2017; text extracted locally)
- [S78] https://www.hse.gov.uk/eci/cyber-security.htm

**India**
- [S79] https://prsindia.org/files/bills_acts/bills_parliament/2023/Digital_Personal_Data_Protection_Act,_2023.pdf (byte-identical to the MeitY copy https://www.meity.gov.in/static/uploads/2024/06/2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf, compared locally with `cmp`)
- [S80] https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf (DPDP Rules 2025, G.S.R. 846(E); text extracted locally)
- [S81] https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf (text extracted locally)
- [S82] https://www.meity.gov.in/static/uploads/2026/05/53b1bcf01cab9a0adde463e73fbc3417.pdf (MeitY notice inviting applications for Data Protection Board posts)

**Local checks (not web sources)**
- [L1] Team machine, queried 2026-10-18 with PowerShell `Get-CimInstance` and `Get-PSDrive` and with `docker --version`: 15.3 GB RAM, 12 logical processors, 24.0 GB free on C:, Docker 28.5.1.
- [L2] `C:\Users\HP\OneDrive\Desktop\tata\src\sentinelloop\agent.py`: the `Observation`, `Decision` and `WorkOrderBook` structures.

**Opened but unusable (listed for transparency; no claim rests on these)**
- https://ibm-maximo-dev.github.io/maximo-restapi-documentation/ (index page only)
- https://javadoc.io/static/com.sap.cloud.sdk.s4hana/s4hana-api-odata/4.30.0/com/sap/cloud/sdk/s4hana/datamodel/odata/services/MaintenanceNotificationService.html (404)
- https://help.sap.com/doc/68382f23560848b2aed3536c28cfc01a/1.0/en-US/classes/vdm_maintenance_notification_service.maintenancenotification-1.html (empty)
- https://community.sap.com/t5/technology-blog-posts-by-sap/create-maintenance-notification-for-sap-s-4hana-using-ibm-watson-and-sap/ba-p/13550008 (403)
- https://www.npmjs.com/package/@sap/cloud-sdk-vdm-maintenance-notification-service (403)
- https://www.sap.com/account/universal-id.html (403)
- https://wiki.osarch.org/index.php/OpenMAINT (404)
- https://www.iec.ch/functional-safety (403)
- https://gca.isa.org/hubfs/ISAGCA%20Quick%20Start%20Guide%20FINAL.pdf (redirect, then 403)
