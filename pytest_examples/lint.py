from __future__ import annotations as _annotations

import re
from subprocess import PIPE, Popen
from textwrap import indent
from typing import TYPE_CHECKING

import pytest
from black import format_str as black_format_str
from black.output import diff as black_diff

from .config import ExamplesConfig

if TYPE_CHECKING:
    from .find_examples import CodeExample

__all__ = 'ruff_check', 'ruff_format', 'black_check', 'black_format', 'code_diff'


def ruff_format(
    example: CodeExample,
    config: ExamplesConfig | None,
) -> str:
    args = ('--fix',)
    return ruff_check(example, config, extra_ruff_args=args)


def ruff_check(
    example: CodeExample,
    config: ExamplesConfig,
    *,
    extra_ruff_args: tuple[str, ...] = (),
) -> str:
    args = 'ruff', '-', *config.ruff_config()

    args += extra_ruff_args

    p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    stdout, stderr = p.communicate(example.source, timeout=2)
    if p.returncode == 1 and stdout:

        def replace_offset(m: re.Match):
            line_number = int(m.group(1))
            return f'{example.path}:{line_number + example.start_line}'

        output = re.sub(r'^-:(\d+)', replace_offset, stdout, flags=re.M)
        pytest.fail(f'ruff failed:\n{indent(output, "  ")}', pytrace=False)
    elif p.returncode != 0:
        raise RuntimeError(f'Error running ruff, return code {p.returncode}:\n{stderr or stdout}')
    else:
        return stdout


def black_format(source: str, config: ExamplesConfig, *, remove_double_blank: bool = False) -> str:
    # hack to avoid black complaining about our print output format
    before_black = re.sub(r'^( *#)> ', r'\1 > ', source, flags=re.M)
    after_black = black_format_str(before_black, mode=config.black_mode())
    # then revert it back
    after_black = re.sub(r'^( *#) > ', r'\1> ', after_black, flags=re.M)
    if remove_double_blank:
        after_black = re.sub(r'\n{3}', '\n\n', after_black)
    return after_black


def black_check(example: CodeExample, config: ExamplesConfig) -> None:
    after_black = black_format(example.source, config, remove_double_blank=example.in_py_file())
    if example.source != after_black:
        diff = code_diff(example, after_black)
        pytest.fail(f'black failed:\n{indent(diff, "  ")}', pytrace=False)


def code_diff(example: CodeExample, after: str) -> str:
    diff = black_diff(example.source, after, 'before', 'after')

    def replace_at_line(match: re.Match) -> str:
        offset = re.sub(r'\d+', lambda m: str(int(m.group(0)) + example.start_line), match.group(2))
        return f'{match.group(1)}{offset}{match.group(3)}'

    return re.sub(r'^(@@\s*)(.*)(\s*@@)$', replace_at_line, diff, flags=re.M)
