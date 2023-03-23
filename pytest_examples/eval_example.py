from __future__ import annotations as _annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import pytest
from _pytest.assertion.rewrite import AssertionRewritingHook

from .insert_print import InsertPrintStatements
from .lint import DEFAULT_LINE_LENGTH, black_check, black_format, ruff_check, ruff_format
from .traceback import create_example_traceback

if TYPE_CHECKING:
    from .find_examples import CodeExample

__all__ = ('EvalExample',)


class EvalExample:
    """
    Class to run and lint examples.
    """

    def __init__(self, *, tmp_path: Path, pytest_request: pytest.FixtureRequest):
        self.tmp_path = tmp_path
        self._pytest_config = pytest_request.config
        self._test_id = pytest_request.node.nodeid
        self.to_update: list[CodeExample] = []

    @property
    def update_examples(self) -> bool:
        return self._pytest_config.getoption('update_examples')

    def run(
        self,
        example: CodeExample,
        line_length: int = DEFAULT_LINE_LENGTH,
        rewrite_assertions: bool = True,
    ) -> None:
        """
        Run the example, print is not mocked and print statements are not checked.

        :param example: The example to run.
        :param line_length: The line length to use when wrapping print statements.
        :param rewrite_assertions: If True, rewrite assertions in the example using pytest's assertion rewriting.
        """
        __tracebackhide__ = True
        example.test_id = self._test_id
        self._run(example, None, line_length, rewrite_assertions)

    def run_print_check(
        self,
        example: CodeExample,
        line_length: int = DEFAULT_LINE_LENGTH,
        rewrite_assertions: bool = True,
    ) -> None:
        """
        Run the example and check print statements.

        :param example: The example to run.
        :param line_length: The line length to use when wrapping print statements.
        :param rewrite_assertions: If True, rewrite assertions in the example using pytest's assertion rewriting.
        """
        __tracebackhide__ = True
        example.test_id = self._test_id
        insert_print = self._run(example, 'check', line_length, rewrite_assertions)
        insert_print.check_print_statements(example)

    def run_print_update(
        self,
        example: CodeExample,
        line_length: int = DEFAULT_LINE_LENGTH,
        rewrite_assertions: bool = True,
    ) -> None:
        """
        Run the example and update print statements, requires `--update-examples`.

        :param example: The example to run.
        :param line_length: The line length to use when wrapping print statements.
        :param rewrite_assertions: If True, rewrite assertions in the example using pytest's assertion rewriting.
        """
        __tracebackhide__ = True
        self._check_update(example)
        insert_print = self._run(example, 'update', line_length, rewrite_assertions)

        new_code = insert_print.updated_print_statements(example)
        if new_code:
            example.source = new_code
            self._mark_for_update(example)

    def _run(
        self,
        example: CodeExample,
        insert_print_statements: Literal['check', 'update', None],
        line_length: int,
        rewrite_assertions: bool,
    ) -> InsertPrintStatements:
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
            enable_print_mock = True
        else:
            enable_print_mock = False

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

        return insert_print

    def lint(self, example: CodeExample, *, line_length: int = DEFAULT_LINE_LENGTH) -> None:
        """
        Lint the example with black and ruff.

        :param example: The example to lint.
        :param line_length: The line length to use when linting.
        """
        self.lint_black(example, line_length=line_length)
        self.lint_ruff(example, line_length=line_length)

    def lint_black(self, example: CodeExample, *, line_length: int = DEFAULT_LINE_LENGTH) -> None:
        """
        Lint the example using black.

        :param example: The example to lint.
        :param line_length: The line length to use when linting.
        """
        example.test_id = self._test_id
        black_check(example, line_length)

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
        example.test_id = self._test_id
        python_file = self._write_file(example)
        ruff_check(example, python_file, extra_ruff_args, line_length, config)

    def format(self, example: CodeExample, *, line_length: int = DEFAULT_LINE_LENGTH) -> None:
        """
        Format the example with black and ruff, requires `--update-examples`.

        :param example: The example to format.
        :param line_length: The line length to use when formatting.
        """
        self.format_black(example, line_length=line_length)
        self.format_ruff(example, line_length=line_length)

    def format_black(self, example: CodeExample, *, line_length: int = DEFAULT_LINE_LENGTH) -> None:
        """
        Format the example using black, requires `--update-examples`.

        :param example: The example to lint.
        :param line_length: The line length to use when linting.
        """
        self._check_update(example)

        new_content = black_format(example.source, line_length)
        if new_content != example.source:
            example.source = new_content
            self._mark_for_update(example)

    def format_ruff(
        self,
        example: CodeExample,
        *,
        extra_ruff_args: tuple[str, ...] = (),
        line_length: int = DEFAULT_LINE_LENGTH,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Format the example using ruff, requires `--update-examples`.

        :param example: The example to lint.
        :param extra_ruff_args: Extra arguments to pass to ruff.
        :param line_length: The line length to use when linting.
        :param config: key-value pairs to write to a .ruff.toml file in the directory of the example to configure ruff.
        """
        self._check_update(example)

        python_file = self._write_file(example)
        new_content = ruff_format(example, python_file, extra_ruff_args, line_length, config)
        if new_content != example.source:
            example.source = new_content
            self._mark_for_update(example)

    def _check_update(self, example: CodeExample) -> None:
        if not self.update_examples:
            raise RuntimeError('Cannot update examples without --update-examples')
        example.test_id = self._test_id

    def _mark_for_update(self, example: CodeExample) -> None:
        """
        Add the example to self.to_update IF it's not already there.
        """
        s = str(example)
        if not any(s == str(ex) for ex in self.to_update):
            self.to_update.append(example)

    def _write_file(self, example: CodeExample) -> Path:
        python_file = self.tmp_path / f'{example.module_name}.py'
        if self.update_examples:
            # if we're in update mode, we need to always rewrite the file
            python_file.write_text(example.source)
        elif not python_file.exists():
            # assume if it already exists, it's because it was previously written in this test
            python_file.write_text(example.source)
        return python_file
