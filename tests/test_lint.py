import pytest

from pytest_examples import CodeExample
from pytest_examples.config import ExamplesConfig
from pytest_examples.lint import FormatError, black_check, ruff_check

long_function = 'def this_is_a_very_long_function_name_to_cause_errors(the_argument): pass\n'


def test_ruff():
    example = CodeExample.create(long_function)
    ruff_check(example, ExamplesConfig())


def test_ruff_config():
    code = 'from typing import Union\n\n\ndef foo(x: Union[int, str]):\n    pass\n'
    example = CodeExample.create(code)
    ruff_check(example, ExamplesConfig())

    with pytest.raises(FormatError, match='real/file.py:4:12: UP007 [*] Use `X | Y` for type annotations'):
        ruff_check(example, ExamplesConfig(target_version='py311', upgrade=True))


def test_ruff_offset():
    code = 'print(x)\n'
    example = CodeExample.create(code)
    with pytest.raises(FormatError, match='testing.md:1:7: F821 Undefined name'):
        ruff_check(example, ExamplesConfig())

    example = CodeExample.create(code, start_line=10)
    with pytest.raises(FormatError, match='testing.md:11:7: F821 Undefined name'):
        ruff_check(example, ExamplesConfig())


def test_black_line_length():
    example = CodeExample.create(long_function, start_line=4)
    with pytest.raises(FormatError, match='^black failed:\n'):
        black_check(example, ExamplesConfig(line_length=40))
