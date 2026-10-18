# L1 load test (generated; SYNTHETIC wind data; this machine only)

Machine: Windows-11-10.0.26200-SP0, 12 logical CPUs, Python 3.12.1. Server: one uvicorn process, SQLite WAL. 50 turbines x 8 days of 10-minute SCADA (10 signals); 45 turbines commissioned.

| measure | result |
|---|---|
| ingestion | 576,000 rows in 400 requests (1440 rows each), 4 clients, 39.3 s: 14,670 rows/s; request p50 385.8 ms, p95 432.1 ms; errors 0 |
| fleet assessment | 50 turbines: sequential 14.5 s, 4 clients 5.0 s (budget: one 10-minute interval = 600 s; fits: True); per assessment p50 285.6 ms, p95 310.6 ms; errors 0; states {'URGENT_REVIEW': 2, 'MODEL_OUT_OF_SCOPE': 28, 'NORMAL_MONITORING': 20} |
| decision generation | 0.62 s for the fleet; orders created 10 |
| reads (8 clients, 20 s) | 90.0 req/s; /assets p50 287.7 ms, p95 457.2 ms, p99 558.4 ms; /work-orders p50 40.9 ms, p95 129.4 ms; status codes {200: 1800} |
| audit chain after load | valid True, 615 events |
| database size | 68.8 MB |
