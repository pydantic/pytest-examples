from pathlib import Path

import pytest
from _pytest.outcomes import Failed

from pytest_examples.lint import ruff_check

long_function = 'def this_is_a_very_long_function_name_to_cause_errors(the_argument):\n  pass'


def test_ruff(tmp_path: Path):
    p = tmp_path / 'test.py'
    p.write_text(long_function)
    ruff_check(p, tmp_path, 0, (), None, None)


def test_ruff_line_length(tmp_path: Path):
    p = tmp_path / 'test.py'
    p.write_text(long_function)
    with pytest.raises(Failed, match='<path>/test.py:1:41: E501 Line too long'):
        ruff_check(p, tmp_path, 0, (), 40, None)


def test_ruff_config(tmp_path: Path):
    p = tmp_path / 'test.py'
    p.write_text('from typing import Union\n\n\ndef foo(x: Union[int, str]):\n    pass\n')
    ruff_check(p, tmp_path, 0, (), None, None)

    with pytest.raises(Failed, match='test.py:4:12: UP007 [*] Use `X | Y` for type annotations'):
        ruff_check(p, tmp_path, 0, (), None, {'target-version': "'py311'", 'select': "['UP']"})


def test_ruff_offset(tmp_path: Path):
    p = tmp_path / 'test.py'
    p.write_text(long_function)
    with pytest.raises(Failed, match='<path>/test.py:11:41: E501 Line too long'):
        ruff_check(p, tmp_path, 10, (), 40, None)
