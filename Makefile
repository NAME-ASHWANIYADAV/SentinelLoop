# SentinelLoop — convenience targets. On Windows without make, run the python commands shown.
PY ?= .venv/Scripts/python.exe
ifeq ($(OS),Windows_NT)
PY := .venv/Scripts/python.exe
else
PY := .venv/bin/python
endif
SUBSET ?= FD001
TEAM ?= Team ______  ·  ______ College

.PHONY: venv doctor data test test-fast baseline run audit dashboard demo experiments slide clean-artifacts

venv:
	python -m venv .venv && $(PY) -m pip install --upgrade pip && $(PY) -m pip install -r requirements.lock.txt && $(PY) -m pip install -e . --no-deps

doctor:
	$(PY) -m sentinelloop doctor

data:
	$(PY) -m sentinelloop data --download

test:
	$(PY) -m pytest tests -q

test-fast:
	$(PY) -m pytest tests -q -m "not slow"

baseline:
	$(PY) -m sentinelloop baseline --subset $(SUBSET)

run:
	$(PY) -m sentinelloop run --subset $(SUBSET) --stream-units 5

audit:
	$(PY) -m sentinelloop audit

dashboard:
	$(PY) -m sentinelloop dashboard

# demo: fast FD001 artefacts in ~30 s, then the dashboard (see docs/DEMO_RUNBOOK.md)
demo:
	$(PY) -m sentinelloop run --subset FD001 --fast --stream-units 3 && $(PY) -m sentinelloop dashboard

experiments:
	$(PY) experiments/run_all.py

slide:
	$(PY) submission/make_round1_slide.py --team "$(TEAM)"

clean-artifacts:
	$(PY) -c "import shutil; shutil.rmtree('artifacts', ignore_errors=True)"
