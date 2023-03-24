from __future__ import annotations as _annotations

from pathlib import Path

import pytest

from .eval_example import EvalExample
from .find_examples import CodeExample, find_examples

__version__ = '0.0.7'
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
    group.addoption(
        '--update-examples-disable-summary',
        action='store_true',
        help='Disable the summary of updated examples at the end of the test run.',
    )


summary: str | None = None


@pytest.fixture(scope='session')
def _examples_to_update(pytestconfig: pytest.Config) -> list[CodeExample]:
    """
    Don't use this directly, it's just  used by
    """
    global summary

    examples_to_update: list[CodeExample] = []
    yield examples_to_update
    if pytestconfig.getoption('update_examples') and examples_to_update:
        from .modify_files import _modify_files

        summary_ = _modify_files(examples_to_update)
        if not pytestconfig.getoption('update_examples_disable_summary'):
            summary = summary_


@pytest.fixture(name='eval_example')
def eval_example(tmp_path: Path, request: pytest.FixtureRequest, _examples_to_update) -> EvalExample:
    """
    Fixture to return a `EvalExample` instance for running and linting examples.
    """
    eval_ex = EvalExample(tmp_path=tmp_path, pytest_request=request)
    yield eval_ex
    if request.config.getoption('update_examples'):
        _examples_to_update.extend(eval_ex.to_update)


def pytest_terminal_summary() -> None:
    if summary:
        print(summary)
