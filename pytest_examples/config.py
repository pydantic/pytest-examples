from __future__ import annotations as _annotations

import hashlib
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypedDict, get_args, get_origin, get_type_hints

import pytest
from black.const import DEFAULT_LINE_LENGTH
from black.mode import Mode as BlackMode, TargetVersion as BlackTargetVersion

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


__all__ = 'DEFAULT_LINE_LENGTH', 'PYPROJECT_CONFIG_KEY', 'ConfigKwargs', 'ExamplesConfig', 'load_pyproject_config'


@dataclass
class ExamplesConfig:
    line_length: int = DEFAULT_LINE_LENGTH
    quotes: Literal['single', 'double', 'either'] = 'either'
    magic_trailing_comma: bool = True
    target_version: Literal['py37', 'py38', 'py39', 'py310', 'py311'] = 'py37'
    upgrade: bool = False
    isort: bool = False
    ruff_line_length: int | None = None
    ruff_select: list[str] | None = None
    ruff_ignore: list[str] | None = None
    white_space_dot: bool = False
    """If True, replace spaces with `·` in example diffs."""

    def black_mode(self) -> BlackMode:
        return BlackMode(
            line_length=self.line_length,
            target_versions={BlackTargetVersion[self.target_version.upper()]} if self.target_version else set(),
            string_normalization=self.quotes == 'double',
            magic_trailing_comma=self.magic_trailing_comma,
        )

    def hash(self) -> str:
        # str(self) should be a good identifier of a specific config
        return hashlib.md5(str(self).encode()).hexdigest()

    def ruff_config(self) -> tuple[str, ...]:
        config_lines: list[str] = []
        select: list[str] = []
        ignore: list[str] = []
        args: list[str] = []

        # line length is enforced by black
        if self.ruff_line_length is None:
            # if not ruff line length, ignore E501 which is line length errors
            # by default, ruff sets the line length to 88
            ignore.append('E501')
        else:
            args.append(f'--line-length={self.ruff_line_length}')

        if self.ruff_select:
            select.extend(self.ruff_select)

        if self.quotes == 'single':
            # enforce single quotes using ruff, black will enforce double quotes
            select.append('Q')
            config_lines.append("flake8-quotes = {inline-quotes = 'single', multiline-quotes = 'double'}")

        if self.target_version:
            args.append(f'--target-version={self.target_version}')

        if self.upgrade:
            select.append('UP')
        if self.isort:
            select.append('I')

        if self.ruff_ignore:
            ignore.extend(self.ruff_ignore)

        # ruff 0.16 changed its default rules: it enabled several hundred from other linters, and
        # dropped 18 pycodestyle and pyflakes ones (`E711` and `F403` among them). Select the pre-0.16
        # default explicitly so examples are linted with the same rules whatever ruff version is installed.
        args.append(f'--select={",".join(["E4", "E7", "E9", "F", *select])}')
        if ignore:
            args.append(f'--ignore={",".join(ignore)}')

        if config_lines:
            config_toml = '\n'.join(config_lines)
            config_file = Path(tempfile.gettempdir()) / 'pytest-examples-ruff-config' / self.hash() / 'ruff.toml'
            if not config_file.exists() or config_file.read_text() != config_toml:
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text(config_toml)

            args.append(f'--config={config_file}')

        return tuple(args)


class ConfigKwargs(TypedDict, total=False):
    """The `set_config` arguments, which are also the `[tool.pytest-examples]` keys in kebab-case."""

    # black and ruff
    quotes: Literal['single', 'double', 'either']
    target_version: Literal['py37', 'py38', 'py39', 'py310', 'py311']
    # black, and the wrapping of `#>` print output
    line_length: int
    magic_trailing_comma: bool
    # ruff
    upgrade: bool
    isort: bool
    ruff_line_length: int | None
    ruff_select: list[str] | None
    ruff_ignore: list[str] | None


PYPROJECT_CONFIG_KEY = pytest.StashKey[ExamplesConfig]()


def load_pyproject_config(rootdir: Path) -> ExamplesConfig:
    """Build the config from `[tool.pytest-examples]` in `pyproject.toml` in the pytest rootdir, if there is one."""
    path = rootdir / 'pyproject.toml'
    if not path.is_file():
        return ExamplesConfig()

    hints = get_type_hints(ConfigKwargs)

    kwargs: dict[str, Any] = {}
    for key, value in _read_table(path).items():
        # keys are kebab-case like the rest of `pyproject.toml`, and a snake-case key is rejected below
        # so every option has one spelling
        field = key.replace('-', '_')
        if '_' in key or field not in hints:
            keys = ', '.join(name.replace('_', '-') for name in hints)
            raise pytest.UsageError(f'{path}: unknown key {key!r} in [tool.pytest-examples], expected one of: {keys}')

        expected = _mismatch(value, hint=hints[field])
        if expected is not None:
            raise pytest.UsageError(f'{path}: {key!r} in [tool.pytest-examples] must be {expected}, got {value!r}')

        kwargs[field] = value

    return ExamplesConfig(**kwargs)


def _read_table(path: Path) -> dict[str, Any]:
    # pytest stops at a `pytest.ini` before it parses `pyproject.toml`, so a syntax error may reach here
    # https://github.com/pytest-dev/pytest/blob/b55ab2aabb68c0ce94c3903139b062d0c2790152/src/_pytest/config/findpaths.py#L91-L97
    try:
        pyproject = tomllib.loads(path.read_text(encoding='utf-8'))
    except tomllib.TOMLDecodeError as exc:
        raise pytest.UsageError(f'{path}: {exc}') from exc

    tool: dict[str, Any] = pyproject.get('tool', {})
    if not isinstance(tool, dict):
        raise pytest.UsageError(f'{path}: [tool] must be a table, got {tool!r}')

    table: dict[str, Any] = tool.get('pytest-examples', {})
    if not isinstance(table, dict):
        raise pytest.UsageError(f'{path}: [tool.pytest-examples] must be a table, got {table!r}')

    return table


def _mismatch(value: Any, *, hint: Any) -> str | None:
    """What `value` should have been to match `hint`, or `None` when it matches."""
    # TOML has no null, so an `X | None` field takes an `X`
    if type(None) in get_args(hint):
        (hint,) = (member for member in get_args(hint) if member is not type(None))

    if get_origin(hint) is Literal:
        choices = get_args(hint)
        return None if value in choices else f'one of: {", ".join(choices)}'

    if get_origin(hint) is list:
        if type(value) is not list:
            return 'a list of str'

        items: list[Any] = value
        return None if all(type(item) is str for item in items) else 'a list of str'

    # `bool` is a subclass of `int`, so `isinstance` would accept `line-length = true`
    return None if type(value) is hint else hint.__name__
