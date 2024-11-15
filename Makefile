.DEFAULT_GOAL := all
sources = pytest_examples tests example

.PHONY: .uv  # Check that uv is installed
.uv:
	@uv --version || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

.PHONY: install  # Install the package, dependencies, and pre-commit for local development
install: .uv
	uv sync --frozen
	uv run pre-commit install --install-hooks

.PHONY: format  # Format the code
format:
	uv run ruff format
	uv run ruff check --fix --fix-only

.PHONY: lint  # Lint the code
lint:
	uv run ruff format --check
	uv run ruff check

.PHONY: test
test:
	pytest

.PHONY: testcov  # Run tests and collect coverage data
testcov:
	uv run coverage run -m pytest
	@uv run coverage report
	@uv run coverage html

.PHONY: all
all: lint testcov
