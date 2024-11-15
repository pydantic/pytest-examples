.DEFAULT_GOAL := all
sources = pytest_examples tests example

.PHONY: .uv  # Check that uv is installed
.uv:
	@uv --version || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

.PHONY: install  # Install the package, dependencies, and pre-commit for local development
install: .uv
	uv sync --frozen --group lint
	uv run pre-commit install --install-hooks

.PHONY: format  # Format the code
format:
	uv run ruff format
	uv run ruff check --fix --fix-only

.PHONY: lint  # Lint the code
lint:
	uv run ruff format --check
	uv run ruff check

.PHONY: typecheck
typecheck:
	uv run pyright

.PHONY: test
test:
	uv run pytest

.PHONY: test-all-python  # Run tests on Python 3.9 to 3.13
test-all-python:
	UV_PROJECT_ENVIRONMENT=.venv39 uv run --python 3.9 coverage run -p -m pytest
	UV_PROJECT_ENVIRONMENT=.venv310 uv run --python 3.10 coverage run -p -m pytest
	UV_PROJECT_ENVIRONMENT=.venv311 uv run --python 3.11 coverage run -p -m pytest
	UV_PROJECT_ENVIRONMENT=.venv312 uv run --python 3.12 coverage run -p -m pytest
	UV_PROJECT_ENVIRONMENT=.venv313 uv run --python 3.13 coverage run -p -m pytest
	@uv run coverage combine
	@uv run coverage report

.PHONY: testcov  # Run tests and collect coverage data
testcov:
	uv run coverage run -m pytest
	@uv run coverage report
	@uv run coverage html

.PHONY: all
all: format lint typecheck testcov
