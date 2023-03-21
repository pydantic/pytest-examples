from pathlib import Path

import pytest

from .find_examples import CodeExample, find_examples
from .run_examples import ExampleRunner

__version__ = '0.0.1'
__all__ = 'find_examples', 'CodeExample', 'ExampleRunner'


@pytest.fixture(name='run_example')
def run_example(tmp_path: Path, pytestconfig: pytest.Config):
    return ExampleRunner(tmp_path=tmp_path, pytest_config=pytestconfig)
