from __future__ import annotations as _annotations

import re
import subprocess
from pathlib import Path
from textwrap import indent
from typing import TYPE_CHECKING

import pytest
from black import format_str as black_format_str
from black.mode import DEFAULT_LINE_LENGTH
from black.mode import Mode as BlackMode
from black.mode import TargetVersion as BlackTargetVersion
from black.output import diff as black_diff

if TYPE_CHECKING:
    from .eval_example import ExamplesConfig
    from .find_examples import CodeExample

__all__ = 'ruff_check', 'ruff_format', 'black_check', 'black_format', 'code_diff', 'DEFAULT_LINE_LENGTH'


def ruff_format(
    example: CodeExample,
    python_file: Path,
    config: ExamplesConfig | None,
) -> str:
    args = ('--fix',)
    ruff_check(example, python_file, config, extra_ruff_args=args)
    return python_file.read_text()


def ruff_check(
    example: CodeExample,
    python_file: Path,
    config: ExamplesConfig,
    *,
    extra_ruff_args: tuple[str, ...] = (),
) -> None:
    args = 'ruff', 'check', str(python_file), *extra_ruff_args

    ruff_config = to_ruff_config(config)
    if ruff_config:
        (python_file.parent / 'ruff.toml').write_text(ruff_config)

    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode == 1 and p.stdout:

        def replace_offset(m: re.Match):
            line_number = int(m.group(1))
            return f'{example.path}:{line_number + example.start_line}'

        output = re.sub(rf'^{re.escape(str(python_file))}:(\d+)', replace_offset, p.stdout, flags=re.M)
        pytest.fail(f'ruff failed:\n{indent(output, "  ")}', pytrace=False)
    elif p.returncode != 0:
        raise RuntimeError(f'Error running ruff, return code {p.returncode}:\n{p.stderr or p.stdout}')


def to_ruff_config(config: ExamplesConfig) -> str | None:
    config_lines = []
    # line length is enforced by black

    select = []
    if config.quotes == 'single':
        # enforce single quotes using ruff, black will enforce double quotes
        select.append('Q')
        config_lines.append("flake8-quotes = {inline-quotes = 'single', multiline-quotes = 'double'}")

    if config.target_version:
        config_lines.append(f'target-version = "{config.target_version}"')

    if config.upgrade:
        select.append('UP')
    if config.isort:
        select.append('I')

    if select:
        config_lines.append(f'select = {select}')

    if config_lines:
        return '\n'.join(config_lines)


def black_format(source: str, config: ExamplesConfig, *, remove_double_blank: bool = False) -> str:
    # hack to avoid black complaining about our print output format
    before_black = re.sub(r'^( *#)> ', r'\1 > ', source, flags=re.M)
    after_black = black_format_str(before_black, mode=to_black_config(config))
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


def to_black_config(config: ExamplesConfig) -> BlackMode:
    return BlackMode(
        line_length=config.line_length,
        target_versions={BlackTargetVersion[config.target_version.upper()]} if config.target_version else set(),
        string_normalization=config.quotes == 'double',
        magic_trailing_comma=config.magic_trailing_comma,
    )


def code_diff(example: CodeExample, after: str) -> str:
    diff = black_diff(example.source, after, 'before', 'after')

    def replace_at_line(match: re.Match) -> str:
        offset = re.sub(r'\d+', lambda m: str(int(m.group(0)) + example.start_line), match.group(2))
        return f'{match.group(1)}{offset}{match.group(3)}'

    return re.sub(r'^(@@\s*)(.*)(\s*@@)$', replace_at_line, diff, flags=re.M)
