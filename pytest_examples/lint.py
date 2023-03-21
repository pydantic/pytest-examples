from __future__ import annotations as _annotations

import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import pytest

if TYPE_CHECKING:
    from .find_examples import CodeExample

__all__ = 'ruff_check', 'black_check'


def ruff_check(
    module_path: Path,
    tmp_path: Path,
    extra_ruff_args: tuple[str, ...],
    line_length: int | None,
    ruff_config: dict[str, Any] | None,
) -> None:
    __tracebackhide__ = True
    args = 'ruff', 'check', str(module_path), *extra_ruff_args

    config_content = ''
    if line_length is not None:
        config_content = f'line-length = {line_length}\n'
    if ruff_config is not None:
        config_content += '\n'.join(f'{k} = {v}' for k, v in ruff_config.items())

    if config_content:
        if '--config' in args:
            raise RuntimeError("Custom `--config` can't be combined with `line_length` or `ruff_config` arguments")
        config_file = tmp_path / 'ruff.toml'
        config_file.write_text(config_content)
        args += '--config', str(config_file)

    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode == 1:
        output = p.stdout.replace(str(tmp_path), '<path>') or p.stderr
        pytest.fail(f'ruff failed:\n{output}')
    elif p.returncode != 0:
        raise RuntimeError(f'Error running ruff, return code {p.returncode}:\n{p.stderr or p.stdout}')


def black_check(example: CodeExample, line_length: int | None = None) -> None:
    __tracebackhide__ = True
    format_code = load_black(line_length)
    diff, _ = format_code(example.source, True)
    if diff:

        def replace_at_line(match: re.Match) -> str:
            offset = re.sub(r'\d+', lambda m: str(int(m.group(0)) + example.start_line), match.group(2))
            return f'{match.group(1)}{offset}{match.group(3)}'

        diff = re.sub(r'^(@@\s*)(.*)(\s*@@)$', replace_at_line, diff, flags=re.M)
        pytest.fail(f'black failed:\n{diff}')


@lru_cache()
def load_black(line_length: int | None) -> Callable[[str, bool], tuple[str | None, str]]:  # noqa: C901
    """
    Build black configuration from "pyproject.toml".
    Black doesn't have a nice self-contained API for reading pyproject.toml, hence all this.
    """
    try:
        from black import format_str
        from black.files import find_pyproject_toml, parse_pyproject_toml
        from black.mode import Mode, TargetVersion
        from black.output import diff
    except ImportError:
        pytest.fail('black is not installed, cannot run black tests')

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

    mode = mode_ or Mode()

    def format_code(code: str, check: bool) -> tuple[str | None, str]:
        dst = format_str(code, mode=mode)
        if check and dst != code:
            return diff(code, dst, 'before', 'after'), dst
        return None, dst

    return format_code
