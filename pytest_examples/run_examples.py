from __future__ import annotations as _annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from _pytest.assertion.rewrite import AssertionRewritingHook

if TYPE_CHECKING:
    from .find_examples import CodeExample


class ExampleRunner:
    def __init__(self, *, tmp_path: Path, pytest_config: pytest.Config):
        self._tmp_path = tmp_path
        self._pytest_config = pytest_config

    def run(self, example: CodeExample, *, rewrite_assertions: bool = False):
        if 'test="skip"' in example.prefix:
            pytest.skip('test="skip" on code snippet, skipping')

        if rewrite_assertions:
            loader = AssertionRewritingHook(config=self._pytest_config)
            loader.mark_rewrite(example.module_name)
        else:
            loader = None

        module_path = self._tmp_path / f'{example.module_name}.py'
        module_path.write_text('\n' * example.start_line + example.source)
        spec = importlib.util.spec_from_file_location('__main__', str(module_path), loader=loader)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except KeyboardInterrupt:
            print(f'KeyboardInterrupt in example {self}')
