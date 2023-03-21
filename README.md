# pytest-examples

[![CI](https://github.com/pydantic/pytest-examples/workflows/CI/badge.svg?event=push)](https://github.com/pydantic/pytest-examples/actions?query=event%3Apush+branch%3Amain+workflow%3ACI)
[![pypi](https://img.shields.io/pypi/v/pytest-examples.svg)](https://pypi.python.org/pypi/pytest-examples)
[![versions](https://img.shields.io/pypi/pyversions/pytest-examples.svg)](https://github.com/pydantic/pytest-examples)
[![license](https://img.shields.io/github/license/pydantic/pytest-examples.svg)](https://github.com/pydantic/pytest-examples/blob/main/LICENSE)

Pytest plugin for testing examples in docstrings and markdown files.

## Installation

```bash
pip install -U pytest-examples
```

## Usage

```py
import pytest
from pytest_examples import find_examples, CodeExample, ExampleRunner

@pytest.mark.parametrize('example', find_examples('foo_dir', 'bar_file.py'))
def test_docstrings(example: CodeExample, run_example: ExampleRunner):
    run_example.run(example)
```
