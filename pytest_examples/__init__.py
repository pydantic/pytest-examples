from pathlib import Path

import pytest

from .eval_example import EvalExample
from .find_examples import CodeExample, find_examples

__version__ = '0.0.3'
__all__ = 'find_examples', 'CodeExample', 'EvalExample'


def pytest_addoption(parser):
    group = parser.getgroup('examples')
    group.addoption(
        '--update-examples',
        action='store_true',
        help=(
            '[WARNING: this will allow files to be changed in place!] '
            'Update code examples to reflect print output and linting.'
        ),
    )


@pytest.fixture(scope='session')
def _examples_to_update(pytestconfig: pytest.Config) -> list[CodeExample]:
    """
    Don't use this directly, it's just  used by
    """
    examples_to_update: list[CodeExample] = []
    yield examples_to_update
    if pytestconfig.getoption('update_examples'):
        from .eval_example import _update_examples

        _update_examples(examples_to_update)


@pytest.fixture(name='eval_example')
def eval_example(tmp_path: Path, pytestconfig: pytest.Config, _examples_to_update) -> EvalExample:
    """
    Fixture to return a `EvalExample` instance for running and linting examples.
    """
    eval_ex = EvalExample(tmp_path=tmp_path, pytest_config=pytestconfig)
    yield eval_ex
    _examples_to_update.extend(eval_ex.to_update)
