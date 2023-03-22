from __future__ import annotations as _annotations

import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from textwrap import indent
from typing import TYPE_CHECKING, Any, Callable

import pytest
from black import format_str as black_format_str
from black.files import find_pyproject_toml, parse_pyproject_toml
from black.mode import Mode, TargetVersion
from black.output import diff as black_diff

if TYPE_CHECKING:
    from .find_examples import CodeExample

__all__ = 'ruff_check', 'ruff_format', 'black_check', 'black_format', 'code_diff', 'DEFAULT_LINE_LENGTH'
DEFAULT_LINE_LENGTH = 88


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


def black_format(source: str, line_length: int = DEFAULT_LINE_LENGTH) -> str:
    # hack to avoid black complaining about our print output format
    before_black = re.sub(r'^( *#)> ', r'\1 > ', source, flags=re.M)
    after_black = black_format_str(before_black, mode=_load_black_mode(line_length))
    # then revert it back
    return re.sub(r'^( *#) > ', r'\1> ', after_black, flags=re.M)


def black_check(example: CodeExample, line_length: int = DEFAULT_LINE_LENGTH) -> None:
    after_black = black_format(example.source, line_length)
    if example.source != after_black:
        diff = code_diff(example, after_black)
        pytest.fail(f'black failed:\n{indent(diff, "  ")}', pytrace=False)


def code_diff(example: CodeExample, after: str) -> str:
    diff = black_diff(example.source, after, 'before', 'after')

    def replace_at_line(match: re.Match) -> str:
        offset = re.sub(r'\d+', lambda m: str(int(m.group(0)) + example.start_line), match.group(2))
        return f'{match.group(1)}{offset}{match.group(3)}'

    return re.sub(r'^(@@\s*)(.*)(\s*@@)$', replace_at_line, diff, flags=re.M)


@lru_cache()
def _load_black_mode(line_length: int) -> Mode:
    """
    Build black configuration from "pyproject.toml".
    Black doesn't have a nice self-contained API for reading pyproject.toml, hence all this.
    """

    def convert_target_version(target_version_config: Any) -> set[Any] | None:
        if target_version_config is not None:
            return None
        elif not isinstance(target_version_config, list):
            raise ValueError('Config key "target_version" must be a list')
        else:
            return {TargetVersion[tv.upper()] for tv in target_version_config}

    @dataclass
    class ConfigArg:
        config_name: str
        keyword_name: str
        converter: Callable[[Any], Any]

    config_mapping: list[ConfigArg] = [
        ConfigArg('target_version', 'target_versions', convert_target_version),
        ConfigArg('line_length', 'line_length', int),
        ConfigArg('skip_string_normalization', 'string_normalization', lambda x: not x),
        ConfigArg('skip_magic_trailing_commas', 'magic_trailing_comma', lambda x: not x),
    ]

    config_str = find_pyproject_toml((str(Path.cwd()),))
    mode_ = None
    if config_str:
        try:
            config = parse_pyproject_toml(config_str)
        except (OSError, ValueError) as e:
            raise ValueError(f'Error reading configuration file: {e}')

        if config:
            kwargs = dict()
            for config_arg in config_mapping:
                if config_arg.config_name == 'line_length' and line_length is not None:
                    kwargs[config_arg.keyword_name] = line_length
                    continue
                try:
                    value = config[config_arg.config_name]
                except KeyError:
                    pass
                else:
                    value = config_arg.converter(value)
                    if value is not None:
                        kwargs[config_arg.keyword_name] = value

            mode_ = Mode(**kwargs)

    return mode_ or Mode()
