from pathlib import Path

import pytest
from _pytest.outcomes import Failed

from pytest_examples import CodeExample
from pytest_examples.eval_example import ExamplesConfig
from pytest_examples.lint import black_check, ruff_check

long_function = 'def this_is_a_very_long_function_name_to_cause_errors(the_argument): pass\n'


def test_ruff(tmp_path: Path):
    p = tmp_path / 'test.py'
    p.write_text(long_function)
    example = CodeExample.create(long_function)
    ruff_check(example, p, ExamplesConfig())


def test_ruff_config(tmp_path: Path):
    p = tmp_path / 'test.py'
    code = 'from typing import Union\n\n\ndef foo(x: Union[int, str]):\n    pass\n'
    p.write_text(code)
    example = CodeExample.create(code)
    ruff_check(example, p, ExamplesConfig())

    with pytest.raises(Failed, match='real/file.py:4:12: UP007 [*] Use `X | Y` for type annotations'):
        ruff_check(example, p, ExamplesConfig(target_version='py311', upgrade=True))


def test_ruff_offset(tmp_path: Path):
    p = tmp_path / 'test.py'
    code = 'print(x)\n'
    p.write_text(code)
    example = CodeExample.create(code)
    with pytest.raises(Failed, match='testing.md:1:7: F821 Undefined name'):
        ruff_check(example, p, ExamplesConfig())

    example = CodeExample.create(code, start_line=10)
    with pytest.raises(Failed, match='testing.md:11:7: F821 Undefined name'):
        ruff_check(example, p, ExamplesConfig())


def test_black_line_length(tmp_path: Path):
    example = CodeExample.create(long_function, start_line=4)
    with pytest.raises(Failed, match='^black failed:\n'):
        black_check(example, ExamplesConfig(line_length=40))
