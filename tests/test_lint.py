from pathlib import Path

import pytest
from _pytest.outcomes import Failed

from pytest_examples import CodeExample
from pytest_examples.lint import ruff_check

long_function = 'def this_is_a_very_long_function_name_to_cause_errors(the_argument): pass'


def fake_example(code: str, start_line: int = 0) -> CodeExample:
    return CodeExample(
        Path('real/file.py'),
        start_line=start_line,
        end_index=0,
        start_index=0,
        end_line=0,
        prefix='',
        source=code,
        indent=0,
    )


def test_ruff(tmp_path: Path):
    p = tmp_path / 'test.py'
    p.write_text(long_function)
    example = fake_example(long_function)
    ruff_check(example, p, ())


def test_ruff_line_length(tmp_path: Path):
    p = tmp_path / 'test.py'
    p.write_text(long_function)
    example = fake_example(long_function, start_line=4)
    with pytest.raises(Failed) as exc_info:
        ruff_check(example, p, line_length=40)
    assert str(exc_info.value) == (
        'ruff failed:\n  real/file.py:5:41: E501 Line too long (73 > 40 characters)\n  Found 1 error.\n'
    )


def test_ruff_config(tmp_path: Path):
    p = tmp_path / 'test.py'
    code = 'from typing import Union\n\n\ndef foo(x: Union[int, str]):\n    pass\n'
    p.write_text(code)
    example = fake_example(code)
    ruff_check(example, p)

    with pytest.raises(Failed, match='real/file.py:4:12: UP007 [*] Use `X | Y` for type annotations'):
        ruff_check(example, p, ruff_config={'target-version': "'py311'", 'select': "['UP']"})


def test_ruff_offset(tmp_path: Path):
    p = tmp_path / 'test.py'
    p.write_text(long_function)
    example = fake_example(long_function, start_line=10)
    with pytest.raises(Failed, match='real/file.py:11:41: E501 Line too long'):
        ruff_check(example, p, line_length=40)
