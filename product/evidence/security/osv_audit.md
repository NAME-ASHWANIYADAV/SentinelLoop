# OSV audit of requirements.lock.txt (generated 2026-10-18T07:08:25.038305+00:00)

Packages queried: 94. Findings: 56.

| package | pinned | advisory | aliases | fixed in | summary |
|---|---|---|---|---|---|
| mlflow | 3.0.1 | GHSA-2cm6-r77w-6g96 | BIT-mlflow-2026-8147, CVE-2026-8147, PYSEC-2026-3686 | 3.13.0rc0 | MLflow: trace API endpoints lack proper authorization validators |
| mlflow | 3.0.1 | GHSA-42h5-h8qh-vv9v | BIT-mlflow-2026-2614, CVE-2026-2614, PYSEC-2026-2654 | 3.10.0 | MLflow allows an unauthenticated remote attacker to read arbitrary files from the server's filesystem |
| mlflow | 3.0.1 | GHSA-46r5-x6jq-v8g6 | BIT-mlflow-2026-33866, CVE-2026-33866, PYSEC-2026-94 | 3.11.0rc0 | MLflow is vulnerable to an authorization bypass affecting the AJAX endpoint |
| mlflow | 3.0.1 | GHSA-4x5p-f36r-mxxr | BIT-mlflow-2025-10279, CVE-2025-10279, PYSEC-2026-1639 | 3.4.0rc0 | mlflow Creates of Temporary File in Directory with Insecure Permissions |
| mlflow | 3.0.1 | GHSA-5qmp-p3c4-72qj | BIT-mlflow-2026-10803, CVE-2026-10803, PYSEC-2026-195 | 3.10.1 | MLflow: Deterministic sampling in dataset digest enables predictable collisions |
| mlflow | 3.0.1 | GHSA-65h7-c7c4-mghx | BIT-mlflow-2026-2393, CVE-2026-2393, PYSEC-2026-2219 | 3.9.0 | MLflow Has a Server-Side Request Forgery (SSRF) Vulnerability |
| mlflow | 3.0.1 | GHSA-75cm-x2w3-8mgf | BIT-mlflow-2026-2652, CVE-2026-2652, PYSEC-2026-2221 | 3.11.0 | MLflow: unauthenticated access to certain FastAPI routes |
| mlflow | 3.0.1 | GHSA-7qhf-v65m-g5f3 | CVE-2026-0545, PYSEC-2026-419 |  | mlflow: FastAPI job endpoints under `/ajax-api/3.0/jobs/*` are not protected by authentication or authorization |
| mlflow | 3.0.1 | GHSA-8c7q-86fq-vvmh | BIT-mlflow-2026-2651, CVE-2026-2651, PYSEC-2026-2220 | 3.10.0 | MLflow allows unauthorized access to multipart upload endpoints when the `--serve-artifacts` mode is enabled |
| mlflow | 3.0.1 | GHSA-f2m9-wcf4-cwwx | BIT-mlflow-2026-4137, CVE-2026-4137, PYSEC-2026-2655 | 3.11.0 | MLFlow Creates a Temporary File With Insecure Permissions  |
| mlflow | 3.0.1 | GHSA-fh64-r2vc-xvhr | BIT-mlflow-2026-33865, CVE-2026-33865, PYSEC-2026-93 | 3.11.1 | MLflow is vulnerable to Stored Cross-Site Scripting (XSS) caused by unsafe parsing of YAML-based MLmodel artifacts in it |
| mlflow | 3.0.1 | GHSA-fhff-qmm8-h2fp | BIT-mlflow-2025-15031, CVE-2025-15031, PYSEC-2026-2656 | 3.9.0rc0 | Arbitrary file write via tar traversal in mlflow |
| mlflow | 3.0.1 | GHSA-g35p-px32-whv6 | BIT-mlflow-2026-4035, CVE-2026-4035, PYSEC-2026-2222 | 3.11.0 | MLflow: Environment variable injection in AI Gateway secrets enables server-side credential exfiltration |
| mlflow | 3.0.1 | GHSA-g6pg-52vf-843h | CVE-2025-15381, PYSEC-2026-2657 |  | MLFlow allows Tracing + Assessments Access |
| mlflow | 3.0.1 | GHSA-gq3w-7jj3-x7gr | CVE-2026-2635, PYSEC-2026-421 | 3.8.0rc0 | MLflow Use of Default Password Authentication Bypass Vulnerability |
| mlflow | 3.0.1 | GHSA-gqvg-gmmx-x4hm |  | 3.15.0 | MLFLOW_ALLOW_PICKLE_DESERIALIZATION=False safety control bypassed by mlflow.statsmodels flavor — RCE via crafted model a |
| mlflow | 3.0.1 | GHSA-pgqp-8h46-6x4j | BIT-mlflow-2025-14279, CVE-2025-14279, PYSEC-2026-1656 | 3.5.0 | MLFlow is vulnerable to DNS rebinding attacks due to a lack of Origin header validation |
| mlflow | 3.0.1 | GHSA-q2r8-vmq7-fpx2 | CVE-2026-2033, PYSEC-2026-2658 | 3.8.0rc0 | MLflow Tracking Server Artifact Handler Directory Traversal Remote Code Execution Vulnerability |
| mlflow | 3.0.1 | GHSA-r23q-823p-vmf7 | BIT-mlflow-2025-15379, CVE-2025-15379, PYSEC-2026-423 | 3.8.1 | MLflow Command Injection vulnerability |
| mlflow | 3.0.1 | GHSA-r5m9-wm49-959f | BIT-mlflow-2026-3198, CVE-2026-3198, PYSEC-2026-2659 | 3.11.0rc0 | MLflow: Any authenticated user can enumerate all gateway secrets, endpoints, and model definitions |
| mlflow | 3.0.1 | GHSA-rvhj-8chj-8v3c | BIT-mlflow-2026-0596, CVE-2026-0596, PYSEC-2026-424 | 3.9.0 | Mlflow: Command Injection when serving models with enable_mlserver=True |
| mlflow | 3.0.1 | GHSA-vhcx-3pq2-4fvc | BIT-mlflow-2025-15036, CVE-2025-15036, PYSEC-2026-425 | 3.9.0rc0 | MLFlow path traversal vulnerability |
| mlflow | 3.0.1 | GHSA-w5xq-c4pf-ghq7 | BIT-mlflow-2026-2734, CVE-2026-2734, PYSEC-2026-2660 | 3.10.0 | MLflow authenticated users can enumerate any registered model versions due to lack of per-model permissions checks |
| mlflow | 3.0.1 | GHSA-wf7f-8fxf-xfxc | BIT-mlflow-2024-37059, CVE-2024-37059, PYSEC-2026-1660 |  | MLFlow unsafe deserialization |
| mlflow | 3.0.1 | GHSA-wxj7-3fx5-pp9m | BIT-mlflow-2025-52967, CVE-2025-52967, PYSEC-2025-52 | 2.22.2, 3.1.0 | MLFlow SSRF via gateway_proxy_handler |
| mlflow | 3.0.1 | GHSA-xch3-2f9x-wh9f | BIT-mlflow-2025-14287, CVE-2025-14287, PYSEC-2026-2661 | 3.8.0rc0 | MLflow has a command injection in mlflow/sagemaker/__init__.py |
| mlflow | 3.0.1 | PYSEC-2025-52 | BIT-mlflow-2025-52967, CVE-2025-52967, GHSA-wxj7-3fx5-pp9m | 3.1.0, 39a419b4ec8fd11b59b3e50ab397042a490f2324 | gateway_proxy_handler in MLflow before 3.1.0 lacks gateway_path validation. |
| mlflow | 3.0.1 | PYSEC-2026-1639 | BIT-mlflow-2025-10279, CVE-2025-10279, GHSA-4x5p-f36r-mxxr | 3.4.0rc0 | mlflow Creates of Temporary File in Directory with Insecure Permissions |
| mlflow | 3.0.1 | PYSEC-2026-1656 | BIT-mlflow-2025-14279, CVE-2025-14279, GHSA-pgqp-8h46-6x4j | 3.5.0 | MLFlow is vulnerable to DNS rebinding attacks due to a lack of Origin header validation |
| mlflow | 3.0.1 | PYSEC-2026-1660 | BIT-mlflow-2024-37059, CVE-2024-37059, GHSA-wf7f-8fxf-xfxc |  | MLFlow unsafe deserialization |
| mlflow | 3.0.1 | PYSEC-2026-195 | BIT-mlflow-2026-10803, CVE-2026-10803, GHSA-5qmp-p3c4-72qj | 3.10.1 | A flaw has been found in MLflow up to 3.10.0. This issue affects the function mlflow.data.digest_utils of the file mlflo |
| mlflow | 3.0.1 | PYSEC-2026-2219 | BIT-mlflow-2026-2393, CVE-2026-2393, GHSA-65h7-c7c4-mghx | 3.9.0 | A Server-Side Request Forgery (SSRF) vulnerability exists in MLflow versions prior to 3.9.0. The `_create_webhook()` fun |
| mlflow | 3.0.1 | PYSEC-2026-2220 | BIT-mlflow-2026-2651, CVE-2026-2651, GHSA-8c7q-86fq-vvmh | 3.11.0rc0 | A vulnerability in MLflow versions <=3.10.1.dev0 allows unauthorized access to multipart upload (MPU) endpoints when the |
| mlflow | 3.0.1 | PYSEC-2026-2221 | BIT-mlflow-2026-2652, CVE-2026-2652, GHSA-75cm-x2w3-8mgf | 3.10.0 | A vulnerability in mlflow/mlflow versions 3.9.0 and earlier allows unauthenticated access to certain FastAPI routes when |
| mlflow | 3.0.1 | PYSEC-2026-2222 | BIT-mlflow-2026-4035, CVE-2026-4035, GHSA-g35p-px32-whv6 | 3.11.0 | A vulnerability in mlflow/mlflow versions prior to 3.11.0 allows for the resolution of environment variables in AI Gatew |
| mlflow | 3.0.1 | PYSEC-2026-2654 | BIT-mlflow-2026-2614, CVE-2026-2614, GHSA-42h5-h8qh-vv9v | 3.10.0 | MLflow allows an unauthenticated remote attacker to read arbitrary files from the server's filesystem |
| mlflow | 3.0.1 | PYSEC-2026-2655 | BIT-mlflow-2026-4137, CVE-2026-4137, GHSA-f2m9-wcf4-cwwx | 3.11.0 | MLFlow Creates a Temporary File With Insecure Permissions  |
| mlflow | 3.0.1 | PYSEC-2026-2656 | BIT-mlflow-2025-15031, CVE-2025-15031, GHSA-fhff-qmm8-h2fp | 3.9.0rc0 | Arbitrary file write via tar traversal in mlflow |
| mlflow | 3.0.1 | PYSEC-2026-2657 | CVE-2025-15381, GHSA-g6pg-52vf-843h |  | MLFlow allows Tracing + Assessments Access |
| mlflow | 3.0.1 | PYSEC-2026-2658 | CVE-2026-2033, GHSA-q2r8-vmq7-fpx2 | 3.8.0rc0 | MLflow Tracking Server Artifact Handler Directory Traversal Remote Code Execution Vulnerability |
| mlflow | 3.0.1 | PYSEC-2026-2659 | BIT-mlflow-2026-3198, CVE-2026-3198, GHSA-r5m9-wm49-959f | 3.11.0rc0 | MLflow: Any authenticated user can enumerate all gateway secrets, endpoints, and model definitions |
| mlflow | 3.0.1 | PYSEC-2026-2660 | BIT-mlflow-2026-2734, CVE-2026-2734, GHSA-w5xq-c4pf-ghq7 | 3.10.0 | MLflow authenticated users can enumerate any registered model versions due to lack of per-model permissions checks |
| mlflow | 3.0.1 | PYSEC-2026-2661 | BIT-mlflow-2025-14287, CVE-2025-14287, GHSA-xch3-2f9x-wh9f | 3.8.0rc0 | MLflow has a command injection in mlflow/sagemaker/__init__.py |
| mlflow | 3.0.1 | PYSEC-2026-3686 | BIT-mlflow-2026-8147, CVE-2026-8147, GHSA-2cm6-r77w-6g96 | 3.13.0rc0 | MLflow: trace API endpoints lack proper authorization validators |
| mlflow | 3.0.1 | PYSEC-2026-3687 | BIT-mlflow-2026-64849, CVE-2026-64849, GHSA-7gwp-5pfp-969j | 3.15.0 | MLflow: Unauthenticated full-read SSRF in webhook delivery: _validate_webhook_url bypassed via unvalidated HTTP redirect |
| mlflow | 3.0.1 | PYSEC-2026-419 | CVE-2026-0545, GHSA-7qhf-v65m-g5f3 |  | mlflow: FastAPI job endpoints under `/ajax-api/3.0/jobs/*` are not protected by authentication or authorization |
| mlflow | 3.0.1 | PYSEC-2026-421 | CVE-2026-2635, GHSA-gq3w-7jj3-x7gr | 3.8.0rc0 | MLflow Use of Default Password Authentication Bypass Vulnerability |
| mlflow | 3.0.1 | PYSEC-2026-423 | BIT-mlflow-2025-15379, CVE-2025-15379, GHSA-r23q-823p-vmf7 | 3.8.1 | MLflow Command Injection vulnerability |
| mlflow | 3.0.1 | PYSEC-2026-424 | BIT-mlflow-2026-0596, CVE-2026-0596, GHSA-rvhj-8chj-8v3c | 3.9.0 | Mlflow: Command Injection when serving models with enable_mlserver=True |
| mlflow | 3.0.1 | PYSEC-2026-425 | BIT-mlflow-2025-15036, CVE-2025-15036, GHSA-vhcx-3pq2-4fvc | 3.9.0rc0 | MLFlow path traversal vulnerability |
| mlflow | 3.0.1 | PYSEC-2026-93 | BIT-mlflow-2026-33865, CVE-2026-33865, GHSA-fh64-r2vc-xvhr | 3.11.0rc0 | MLflow is vulnerable to Stored Cross-Site Scripting (XSS) caused by unsafe parsing of YAML-based MLmodel artifacts in it |
| mlflow | 3.0.1 | PYSEC-2026-94 | BIT-mlflow-2026-33866, CVE-2026-33866, GHSA-46r5-x6jq-v8g6 | 3.11.0rc0 | MLflow is vulnerable to an authorization bypass affecting the AJAX endpoint used to download saved model artifacts. Due  |
| pyarrow | 20.0.0 | GHSA-rgxp-2hwp-jwgg | CVE-2026-25087, PYSEC-2026-113 | 23.0.1 | Apache Arrow: Potential use-after-free when reading IPC file with pre-buffering |
| pyarrow | 20.0.0 | PYSEC-2026-113 | CVE-2026-25087, GHSA-rgxp-2hwp-jwgg | 23.0.1 | Use After Free vulnerability in Apache Arrow C++.

This issue affects Apache Arrow C++ from 15.0.0 through 23.0.0. It ca |
| pytest | 8.4.2 | GHSA-6w46-j5rx-g56g | CVE-2025-71176, PYSEC-2026-1845 | 9.0.3 | pytest has vulnerable tmpdir handling |
| pytest | 8.4.2 | PYSEC-2026-1845 | CVE-2025-71176, GHSA-6w46-j5rx-g56g | 9.0.3 | pytest has vulnerable tmpdir handling |
