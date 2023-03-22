from __future__ import annotations as _annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from _pytest.assertion.rewrite import AssertionRewritingHook

from .lint import black_check, ruff_check
from .traceback import create_example_traceback

if TYPE_CHECKING:
    from .find_examples import CodeExample

__all__ = ('EvalExample',)


class EvalExample:
    def __init__(self, *, tmp_path: Path, pytest_config: pytest.Config):
        self.tmp_path = tmp_path
        self._pytest_config = pytest_config

    def run(self, example: CodeExample, *, rewrite_assertions: bool = True):
        __tracebackhide__ = True
        if 'test="skip"' in example.prefix:
            pytest.skip('test="skip" on code snippet, skipping')

        if rewrite_assertions:
            loader = AssertionRewritingHook(config=self._pytest_config)
            loader.mark_rewrite(example.module_name)
        else:
            loader = None

        module_path = self._write_file(example)
        spec = importlib.util.spec_from_file_location('__main__', str(module_path), loader=loader)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except KeyboardInterrupt:
            print(f'KeyboardInterrupt in example {self}')
        except Exception as exc:
            example_tb = create_example_traceback(exc, str(module_path), example)
            if example_tb:
                raise exc.with_traceback(example_tb)
            else:
                raise exc

    def lint(
        self, example: CodeExample, *, ruff: bool = True, black: bool = True, line_length: int | None = None
    ) -> None:
        if ruff:
            self.lint_ruff(example, line_length=line_length)
        if black:
            self.lint_black(example, line_length=line_length)

    def lint_ruff(
        self,
        example: CodeExample,
        *,
        extra_ruff_args: tuple[str, ...] = (),
        line_length: int | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        __tracebackhide__ = True
        module_path = self._write_file(example)
        ruff_check(example, module_path, extra_ruff_args, line_length, config)

    def lint_black(self, example: CodeExample, *, line_length: int | None = None) -> None:
        __tracebackhide__ = True
        black_check(example, line_length)

    def _write_file(self, example: CodeExample) -> Path:
        module_path = self.tmp_path / f'{example.module_name}.py'
        if not module_path.exists():
            # assume if it already exists, it's because it was previously written in this test
            module_path.write_text(example.source)
        return module_path
