from pathlib import Path

import pytest

from .eval_example import EvalExample
from .find_examples import CodeExample, find_examples

__version__ = '0.0.3'
__all__ = 'find_examples', 'CodeExample', 'EvalExample'


def pytest_addoption(parser):
    group = parser.getgroup('examples')
    group.addoption(
        '--update-example-prints',
        action='store_true',
        help='update examples to reflect print output',
    )


@pytest.fixture(name='eval_example')
def eval_example(tmp_path: Path, pytestconfig: pytest.Config):
    return EvalExample(tmp_path=tmp_path, pytest_config=pytestconfig)
