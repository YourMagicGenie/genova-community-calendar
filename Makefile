.PHONY: help test test-python test-sql test-all setup-local setup-python teardown-local clean

# Detect Python in venv or system
PYTHON := $(shell if [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3.12; fi)

# Default target
help:
	@echo "Community Calendar Test Suite"
	@echo ""
	@echo "Targets:"
	@echo "  make test           - Run Python tests"
	@echo "  make test-python    - Run Python tests (pytest)"
	@echo "  make test-sql       - Run database tests (local Supabase via pgTAP)"
	@echo "  make setup-python   - Create venv and install dependencies"
	@echo "  make setup-local    - Start local Supabase and apply schema"
	@echo "  make teardown-local - Stop local Supabase"
	@echo "  make clean          - Clean test artifacts"
	@echo ""
	@echo "Prerequisites:"
	@echo "  - Python 3.12 (run 'make setup-python' for venv)"
	@echo "  - Supabase CLI installed (for database tests)"
	@echo "  - PostgreSQL client (psql) for local database access"

# Run default tests
test: test-python

# Alias for test
test-all: test

# Setup Python environment
setup-python:
	@echo "Setting up Python 3.12 virtual environment..."
	@if [ -f .venv/bin/python ]; then \
		.venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 12), "Delete the old .venv and rerun make setup-python with Python 3.12"'; \
	else \
		python3.12 -m venv .venv; \
		echo "✓ Created .venv with Python 3.12"; \
	fi
	@echo "Installing dependencies..."
	.venv/bin/pip install -q -r requirements-dev.txt
	@echo "✓ Dependencies installed"
	@echo ""
	@echo "Activate venv with: source .venv/bin/activate"

# Run Python tests
test-python:
	@echo "Running Python tests..."
	@if [ -f .venv/bin/pytest ]; then \
		.venv/bin/pytest tests/ -v; \
	elif $(PYTHON) -m pytest --version > /dev/null 2>&1; then \
		$(PYTHON) -m pytest tests/ -v; \
	else \
		echo "ERROR: pytest not found."; \
		echo "Install with: python3.12 -m pip install -r requirements-dev.txt"; \
		echo "Or run: make setup-python"; \
		exit 1; \
	fi

# Run database tests (requires prepared local Supabase project DB)
test-sql:
	@echo "Running database tests..."
	@if ! supabase status > /dev/null 2>&1; then \
		echo "ERROR: Local Supabase is not running."; \
		echo "Run: make setup-local"; \
		exit 1; \
	fi
	@supabase test db supabase/tests/

# Setup local Supabase environment
setup-local:
	@echo "Starting local Supabase..."
	supabase start
	@echo "Applying migrations..."
	supabase db reset
	@echo ""
	@echo "✓ Local environment ready"
	@echo "Run: make test-sql"

# Teardown local Supabase
teardown-local:
	@echo "Stopping local Supabase..."
	supabase stop

# Clean test artifacts
clean:
	@echo "Cleaning test artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned"
