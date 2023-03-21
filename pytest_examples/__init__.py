from pathlib import Path

import pytest

from .find_examples import CodeExample, find_examples
from .run_examples import ExampleRunner

__version__ = '0.0.2'
__all__ = 'find_examples', 'CodeExample', 'ExampleRunner'


def pytest_addoption(parser):
    group = parser.getgroup('examples')
    group.addoption(
        '--update-example-prints',
        action='store_true',
        help='update examples to reflect print output',
    )


@pytest.fixture(name='run_example')
def run_example(tmp_path: Path, pytestconfig: pytest.Config):
    return ExampleRunner(tmp_path=tmp_path, pytest_config=pytestconfig)
