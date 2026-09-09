.PHONY: help install dev install-docs fix lint type-check test audit docs docs-serve check check-ci clean build logo ui ui-demo

EXTRAS := --all-extras

help:
	@echo "Dev (modify files):  fix"
	@echo "Checks (read-only):  audit | lint | type-check | test | docs | check"
	@echo "CI parity:           check-ci"
	@echo "Setup:               install | dev | install-docs"
	@echo "Run:                 ui | ui-demo   (PORT=8080 DB=...)"
	@echo "Docs:                docs-serve"
	@echo "Package:             build | logo"
	@echo "Cleanup:             clean"

# -- Setup --------------------------------------------------------------------

install:
	uv sync

dev:
	uv sync --all-extras

install-docs:
	uv sync --extra docs

# -- Dev helpers (modify files) -----------------------------------------------

fix:
	uv run ruff format .
	uv run ruff check --fix .

# -- Checks (read-only, mirrors GitHub CI) ------------------------------------

lint:
	uv run $(EXTRAS) ruff check .
	uv run $(EXTRAS) ruff format --check .

type-check:
	uv run $(EXTRAS) ty check personality_questionnaire

# RUN_PACKAGING_TESTS is set here, not only in CI: `check` must be the same gate
# the runner applies, and a packaging regression that only CI catches is a
# regression found too late.
test:
	RUN_PACKAGING_TESTS=1 uv run $(EXTRAS) coverage run -m unittest discover -s tests -v
	uv run $(EXTRAS) coverage report
	uv run $(EXTRAS) coverage html
	uv run $(EXTRAS) coverage xml -o coverage.xml

audit:
	uv run $(EXTRAS) --with pip-audit pip-audit || \
	  echo "  (advisories above are a warning, as in CI)"

docs:
	uv run $(EXTRAS) sphinx-build -b html -W docs/ site/

docs-serve:
	uv run $(EXTRAS) sphinx-autobuild docs/ site/

# Every step the GitHub runner performs, in the runner's order. If this passes and
# CI fails, the two have drifted and that is a bug in one of them.
check: audit lint type-check test docs

# `check` runs against the developer's environment, which is a strict superset of
# CI's. That gap is structural -- no amount of care with `check` closes it -- so
# this target rebuilds CI's exact environment and runs CI's exact steps.
SHELL := /bin/bash
CI_VENV := .venv-ci
CI_PY   ?= 3.12   # the declared floor: what CI checks first

check-ci:
	@echo "-- Building CI-equivalent environment ($(CI_VENV), python $(CI_PY)) --"
	@rm -rf $(CI_VENV)
	@uv venv $(CI_VENV) --python $(CI_PY) --seed >/dev/null
	@VIRTUAL_ENV=$(CI_VENV) uv pip install --quiet -e ".[ui,mysql,analysis,dev,docs]"
	@echo "-- Audit dependencies --"
	@PIPAPI_PYTHON_LOCATION=$(CURDIR)/$(CI_VENV)/bin/python \
	  VIRTUAL_ENV=$(CI_VENV) uvx pip-audit || \
	  echo "  (advisories above are a warning, as in CI)"
	@echo "-- Ruff lint --"
	@VIRTUAL_ENV=$(CI_VENV) uv run --no-project ruff check .
	@echo "-- Ruff format --"
	@VIRTUAL_ENV=$(CI_VENV) uv run --no-project ruff format --check .
	@echo "-- Type check (ty) --"
	@VIRTUAL_ENV=$(CI_VENV) uv run --no-project ty check personality_questionnaire
	@echo "-- Tests (same env flags as CI) --"
	@set -o pipefail; RUN_PACKAGING_TESTS=1 \
	  VIRTUAL_ENV=$(CI_VENV) uv run --no-project coverage run -m unittest discover -s tests -v 2>&1 \
	  | tee $(CI_VENV)/test.log | tail -3
	@VIRTUAL_ENV=$(CI_VENV) uv run --no-project coverage report
	@echo "-- Docs (warnings as errors) --"
	@VIRTUAL_ENV=$(CI_VENV) uv run --no-project sphinx-build -b html -W docs/ site/
	@echo ""
	@echo "-- Skipped tests --"
	@grep -oE "skipped '[^']+'" $(CI_VENV)/test.log | sort | uniq -c || echo "  none"
	@echo ""
	@echo "CI parity check passed -- the runner should agree."

# -- Run ----------------------------------------------------------------------

# The data-collection application. Binds to 127.0.0.1 by default; records go to
# ~/.personality_questionnaire/records.db unless PQ_DATABASE_URL says otherwise.
# Override either without editing this file:
#   make ui PORT=9000
#   make ui DB=sqlite:///$(PWD)/tmp/records.db
PORT ?= 8080
DB   ?=

ui:
	uv run $(EXTRAS) pq ui --port $(PORT) $(if $(DB),--db $(DB),)

# The same application against a throwaway database, so a trial run cannot touch
# real participant records.
ui-demo:
	@mkdir -p tmp
	uv run $(EXTRAS) pq ui --port $(PORT) --db "sqlite:///$(CURDIR)/tmp/demo.db" --show

# -- Assets -------------------------------------------------------------------

# The SVG is the source of truth; this renders the raster fallback the README needs,
# because PyPI strips SVG from project descriptions. Pure Python and deterministic,
# so it runs anywhere and produces a byte-identical file.
logo:
	uv run python scripts/render_logo.py

# -- Package ------------------------------------------------------------------

build:
	uv build

clean:
	rm -rf .venv .venv-ci coverage_html dist/ site/ .ruff_cache/
	rm -f .coverage coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} +
