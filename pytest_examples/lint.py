from __future__ import annotations as _annotations

import re
import subprocess
from pathlib import Path
from textwrap import indent
from typing import TYPE_CHECKING, Any

import pytest
from black import format_str as black_format_str
from black.mode import DEFAULT_LINE_LENGTH
from black.mode import Mode as BlackMode
from black.output import diff as black_diff

if TYPE_CHECKING:
    from .find_examples import CodeExample

__all__ = 'ruff_check', 'ruff_format', 'black_check', 'black_format', 'code_diff', 'DEFAULT_LINE_LENGTH'


def ruff_format(
    example: CodeExample,
    python_file: Path,
    extra_ruff_args: tuple[str, ...] = (),
    line_length: int = DEFAULT_LINE_LENGTH,
    ruff_config: dict[str, Any] | None = None,
) -> str:
    args = ('--fix',) + extra_ruff_args
    ruff_check(example, python_file, args, line_length, ruff_config)
    return python_file.read_text()


def ruff_check(
    example: CodeExample,
    python_file: Path,
    extra_ruff_args: tuple[str, ...] = (),
    line_length: int = DEFAULT_LINE_LENGTH,
    ruff_config: dict[str, Any] | None = None,
) -> None:
    args = 'ruff', 'check', str(python_file), *extra_ruff_args

    config_content = ''
    if line_length is not None:
        config_content = f'line-length = {line_length}\n'
    if ruff_config is not None:
        config_content += '\n'.join(f'{k} = {v}' for k, v in ruff_config.items())

    if config_content:
        if '--config' in args:
            raise RuntimeError("Custom `--config` can't be combined with `line_length` or `ruff_config` arguments")
        config_file = python_file.parent / 'ruff.toml'
        config_file.write_text(config_content)
        args += '--config', str(config_file)

    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode == 1 and p.stdout:

        def replace_offset(m: re.Match):
            line_number = int(m.group(1))
            return f'{example.path}:{line_number + example.start_line}'

        output = re.sub(rf'^{re.escape(str(python_file))}:(\d+)', replace_offset, p.stdout, flags=re.M)
        pytest.fail(f'ruff failed:\n{indent(output, "  ")}', pytrace=False)
    elif p.returncode != 0:
        raise RuntimeError(f'Error running ruff, return code {p.returncode}:\n{p.stderr or p.stdout}')


def black_format(source: str, line_length: int = DEFAULT_LINE_LENGTH, black_mode: BlackMode | None = None) -> str:
    # hack to avoid black complaining about our print output format
    before_black = re.sub(r'^( *#)> ', r'\1 > ', source, flags=re.M)
    after_black = black_format_str(before_black, mode=black_mode or BlackMode(line_length=line_length))
    # then revert it back
    return re.sub(r'^( *#) > ', r'\1> ', after_black, flags=re.M)


def black_check(
    example: CodeExample, line_length: int = DEFAULT_LINE_LENGTH, black_mode: BlackMode | None = None
) -> None:
    after_black = black_format(example.source, line_length, black_mode)
    if example.source != after_black:
        diff = code_diff(example, after_black)
        pytest.fail(f'black failed:\n{indent(diff, "  ")}', pytrace=False)


def code_diff(example: CodeExample, after: str) -> str:
    diff = black_diff(example.source, after, 'before', 'after')

    def replace_at_line(match: re.Match) -> str:
        offset = re.sub(r'\d+', lambda m: str(int(m.group(0)) + example.start_line), match.group(2))
        return f'{match.group(1)}{offset}{match.group(3)}'

    return re.sub(r'^(@@\s*)(.*)(\s*@@)$', replace_at_line, diff, flags=re.M)
