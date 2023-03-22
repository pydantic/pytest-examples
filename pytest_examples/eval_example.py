from __future__ import annotations as _annotations

import importlib.util
from operator import itemgetter
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import pytest
from _pytest.assertion.rewrite import AssertionRewritingHook

from .insert_print import InsertPrintStatements
from .lint import DEFAULT_LINE_LENGTH, black_check, ruff_check
from .traceback import create_example_traceback

if TYPE_CHECKING:
    from .find_examples import CodeExample

__all__ = ('EvalExample',)


class EvalExample:
    """
    Class to run and lint examples.
    """

    def __init__(self, *, tmp_path: Path, pytest_config: pytest.Config):
        self.tmp_path = tmp_path
        self._pytest_config = pytest_config
        self.to_update: list[CodeExample] = []

    @property
    def update_examples(self) -> bool:
        return self._pytest_config.getoption('update_examples')

    def run(
        self,
        example: CodeExample,
        insert_print_statements: Literal['check', 'update', None] = None,
        line_length: int = DEFAULT_LINE_LENGTH,
        rewrite_assertions: bool = True,
    ) -> None:
        """
        Run the example.

        :param example: The example to run.
        :param insert_print_statements: `'check'` means check print statement comments match expected format,
            `'update'` means update print statement comments to match expected format,
            `None` means don't mock `print()`.
        :param line_length: The line length to use when wrapping print statements.
        :param rewrite_assertions: If True, rewrite assertions in the example using pytest's assertion rewriting.
        """
        __tracebackhide__ = True
        if 'test="skip"' in example.prefix:
            pytest.skip('test="skip" on code snippet, skipping')

        if rewrite_assertions:
            loader = AssertionRewritingHook(config=self._pytest_config)
            loader.mark_rewrite(example.module_name)
        else:
            loader = None

        python_file = self._write_file(example)
        spec = importlib.util.spec_from_file_location('__main__', str(python_file), loader=loader)
        module = importlib.util.module_from_spec(spec)

        if insert_print_statements == 'check':
            enable_print_mock = True
        elif insert_print_statements == 'update':
            if not self.update_examples:
                raise RuntimeError('Cannot update examples without --update-examples')
            enable_print_mock = True
        elif insert_print_statements is None:
            enable_print_mock = False
        else:
            raise ValueError(f'Invalid value for insert_print_statements: {insert_print_statements}')

        # does nothing if insert_print_statements is False
        insert_print = InsertPrintStatements(python_file, line_length, enable_print_mock)

        try:
            with insert_print:
                spec.loader.exec_module(module)
        except KeyboardInterrupt:
            print(f'KeyboardInterrupt in example {self}')
        except Exception as exc:
            example_tb = create_example_traceback(exc, str(python_file), example)
            if example_tb:
                raise exc.with_traceback(example_tb)
            else:
                raise exc

        if insert_print_statements == 'check':
            insert_print.check_print_statements(example)
        elif insert_print_statements == 'update':
            new_code = insert_print.updated_print_statements(example)
            if new_code:
                example.source = new_code
                self.to_update.append(example)

    def lint(
        self, example: CodeExample, *, ruff: bool = True, black: bool = True, line_length: int = DEFAULT_LINE_LENGTH
    ) -> None:
        """
        Lint the example.

        :param example: The example to lint.
        :param ruff: If True, lint the example using ruff.
        :param black: If True, lint the example using black.
        :param line_length: The line length to use when linting.
        """
        if ruff:
            self.lint_ruff(example, line_length=line_length)
        if black:
            self.lint_black(example, line_length=line_length)

    def lint_ruff(
        self,
        example: CodeExample,
        *,
        extra_ruff_args: tuple[str, ...] = (),
        line_length: int = DEFAULT_LINE_LENGTH,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Lint the example using ruff.

        :param example: The example to lint.
        :param extra_ruff_args: Extra arguments to pass to ruff.
        :param line_length: The line length to use when linting.
        :param config: key-value pairs to write to a .ruff.toml file in the directory of the example to configure ruff.
        """
        python_file = self._write_file(example)
        ruff_check(example, python_file, extra_ruff_args, line_length, config)

    def lint_black(self, example: CodeExample, *, line_length: int = DEFAULT_LINE_LENGTH) -> None:
        """
        Lint the example using black.

        :param example: The example to lint.
        :param line_length: The line length to use when linting.
        """
        black_check(example, line_length)

    def _write_file(self, example: CodeExample) -> Path:
        python_file = self.tmp_path / f'{example.module_name}.py'
        if not python_file.exists():
            # assume if it already exists, it's because it was previously written in this test
            python_file.write_text(example.source)
        return python_file


def _update_examples(example_groups: list[list[CodeExample]]):
    """
    Internal use only, update examples in place.
    """
    # The same example shouldn't appear more than once
    examples: set[str] = set()
    for example_group in example_groups:
        new_changes = {str(ex) for ex in example_group}
        if new_changes & examples:
            raise RuntimeError('Cannot update the same example in separate tests!')
        examples |= new_changes

    for example_group in example_groups:
        # order by line number descending so the earlier change doesn't mess up line numbers for later changes
        example_groups.sort(key=itemgetter('start_line'), reverse=True)
        for example in example_group:
            _apply_example_update(example)


def _apply_example_update(example: CodeExample):
    pass
