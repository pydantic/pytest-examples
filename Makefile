.DEFAULT_GOAL := all
sources = pytest_examples tests example

.PHONY: install
install:
	pip install -U pip
	pip install -r requirements/all.txt
	pip install -e .
	pre-commit install

.PHONY: refresh-lockfiles
refresh-lockfiles:
	find requirements/ -name '*.txt' ! -name 'all.txt' -type f -delete
	make update-lockfiles

.PHONY: update-lockfiles
update-lockfiles:
	@echo "Updating requirements/*.txt files using pip-compile"
	pip-compile -q --resolver backtracking -o requirements/linting.txt requirements/linting.in
	pip-compile -q --resolver backtracking -o requirements/testing.txt requirements/testing.in
	pip-compile -q --resolver backtracking -o requirements/pyproject.txt pyproject.toml
	pip install --dry-run -r requirements/all.txt

.PHONY: format
format:
	black $(sources)
	ruff $(sources) --fix --exit-zero

.PHONY: lint
lint:
	black $(sources) --check --diff
	ruff $(sources)

.PHONY: test
test:
	pytest

.PHONY: all
all: lint test

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -rf .cache
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
