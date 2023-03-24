from __future__ import annotations as _annotations

import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from black.mode import DEFAULT_LINE_LENGTH
from black.mode import Mode as BlackMode
from black.mode import TargetVersion as BlackTargetVersion

if TYPE_CHECKING:
    from typing import Literal


__all__ = 'ExamplesConfig', 'DEFAULT_LINE_LENGTH'


@dataclass
class ExamplesConfig:
    line_length: int = DEFAULT_LINE_LENGTH
    quotes: Literal['single', 'double', 'either'] = 'either'
    magic_trailing_comma: bool = True
    target_version: Literal['py37', 'py38', 'py39', 'py310', 'py311'] = 'py37'
    upgrade: bool = False
    isort: bool = False

    def black_mode(self):
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
        ruff_toml = self._to_ruff_toml()

        if ruff_toml is None:
            return ()

        config_file = Path(tempfile.gettempdir()) / 'pytest-examples-ruff-config' / self.hash() / 'ruff.toml'
        if not config_file.exists():
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(ruff_toml)

        return '--config', str(config_file)

    def _to_ruff_toml(self) -> str | None:
        config_lines = []
        # line length is enforced by black

        select = []
        if self.quotes == 'single':
            # enforce single quotes using ruff, black will enforce double quotes
            select.append('Q')
            config_lines.append("flake8-quotes = {inline-quotes = 'single', multiline-quotes = 'double'}")

        if self.target_version:
            config_lines.append(f'target-version = "{self.target_version}"')

        if self.upgrade:
            select.append('UP')
        if self.isort:
            select.append('I')

        if select:
            config_lines.append(f'select = {select}')

        if config_lines:
            return '\n'.join(config_lines)
