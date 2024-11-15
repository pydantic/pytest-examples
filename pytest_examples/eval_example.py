from __future__ import annotations as _annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import pytest
from _pytest.assertion.rewrite import AssertionRewritingHook
from _pytest.outcomes import Failed as PytestFailed

from .config import DEFAULT_LINE_LENGTH, ExamplesConfig
from .lint import FormatError, black_check, black_format, ruff_check, ruff_format
from .run_code import InsertPrintStatements, run_code

if TYPE_CHECKING:
    from typing import Literal

    from .find_examples import CodeExample

__all__ = ('EvalExample',)


class EvalExample:
    """Class to run and lint examples."""

    def __init__(self, *, tmp_path: Path, pytest_request: pytest.FixtureRequest):
        self.tmp_path = tmp_path
        self._pytest_config = pytest_request.config
        self._test_id = pytest_request.node.nodeid
        self.to_update: list[CodeExample] = []
        self.config: ExamplesConfig = ExamplesConfig()
        self.print_callback: Callable[[str], str] | None = None

    def set_config(
        self,
        *,
        line_length: int = DEFAULT_LINE_LENGTH,
        quotes: Literal['single', 'double', 'either'] = 'either',
        magic_trailing_comma: bool = True,
        target_version: Literal['py37', 'py38', 'py39', 'py310', 'py310'] = 'py37',
        upgrade: bool = False,
        isort: bool = False,
        ruff_line_length: int | None = None,
        ruff_select: list[str] | None = None,
        ruff_ignore: list[str] | None = None,
    ):
        """Set the config for lints.

        Args:
            line_length: The line length to use when wrapping print statements, defaults to 88.
            quotes: The quote to use, defaults to "either".
            magic_trailing_comma: If True, add a trailing comma to magic methods, defaults to True.
            target_version: The target version to use when upgrading code, defaults to "py37".
            upgrade: If True, upgrade the code to the target version, defaults to False.
            isort: If True, run ruff's isort extension on the code, defaults to False.
            ruff_line_length: In general, we disable line-length checks in ruff, to let black take care of them.
            ruff_select: Ruff rules to select
            ruff_ignore: Ruff rules to ignore
        """
        self.config = ExamplesConfig(
            line_length=line_length,
            quotes=quotes,
            magic_trailing_comma=magic_trailing_comma,
            target_version=target_version,
            upgrade=upgrade,
            isort=isort,
            ruff_line_length=ruff_line_length,
            ruff_select=ruff_select,
            ruff_ignore=ruff_ignore,
        )

    @property
    def update_examples(self) -> bool:
        return bool(self._pytest_config.getoption('update_examples'))

    def run(
        self,
        example: CodeExample,
        *,
        module_globals: dict[str, Any] | None = None,
        rewrite_assertions: bool = True,
        call: str | None = None,
    ) -> dict[str, Any]:
        """Run the example, print is not mocked and print statements are not checked.

        Args:
            example: The example to run.
            module_globals: The globals to use when running the example.
            rewrite_assertions: If True, rewrite assertions in the example using pytest's assertion rewriting.
            call: If not None, method to check for and call if it exists.
        """
        __tracebackhide__ = True
        example.test_id = self._test_id
        _, module_dict = self._run(example, None, module_globals, rewrite_assertions, call)
        return module_dict

    def run_print_check(
        self,
        example: CodeExample,
        *,
        module_globals: dict[str, Any] | None = None,
        rewrite_assertions: bool = True,
        call: str | None = None,
    ) -> dict[str, Any]:
        """Run the example and check print statements.

        Args:
            example: The example to run.
            module_globals: The globals to use when running the example.
            rewrite_assertions: If True, rewrite assertions in the example using pytest's assertion rewriting.
            call: If not None, method to check for and call if it exists.
        """
        __tracebackhide__ = True
        example.test_id = self._test_id
        insert_print, module_dict = self._run(example, 'check', module_globals, rewrite_assertions, call)
        insert_print.check_print_statements(example)
        return module_dict

    def run_print_update(
        self,
        example: CodeExample,
        *,
        module_globals: dict[str, Any] | None = None,
        rewrite_assertions: bool = True,
        call: str | None = None,
    ) -> dict[str, Any]:
        """Run the example and update print statements, requires `--update-examples`.

        Args:
            example: The example to run.
            module_globals: The globals to use when running the example.
            rewrite_assertions: If True, rewrite assertions in the example using pytest's assertion rewriting.
            call: If not None, method to check for and call if it exists.
        """
        __tracebackhide__ = True
        self._check_update(example)
        insert_print, module_dict = self._run(example, 'update', module_globals, rewrite_assertions, call)

        new_code = insert_print.updated_print_statements(example)
        if new_code:
            example.source = new_code
            self._mark_for_update(example)
        return module_dict

    def _run(
        self,
        example: CodeExample,
        insert_print_statements: Literal['check', 'update', None],
        module_globals: dict[str, Any] | None,
        rewrite_assertions: bool,
        call: str | None,
    ) -> tuple[InsertPrintStatements, dict[str, Any]]:
        __tracebackhide__ = True

        if rewrite_assertions:
            loader = AssertionRewritingHook(config=self._pytest_config)
            loader.mark_rewrite(example.module_name)
        else:
            loader = None

        if insert_print_statements == 'check':
            enable_print_mock = True
        elif insert_print_statements == 'update':
            enable_print_mock = True
        else:
            enable_print_mock = False

        python_file = self._write_file(example)
        return run_code(
            example=example,
            python_file=python_file,
            loader=loader,
            config=self.config,
            enable_print_mock=enable_print_mock,
            print_callback=self.print_callback,
            module_globals=module_globals,
            call=call,
        )

    def lint(self, example: CodeExample) -> None:
        """Lint the example with black and ruff.

        Args:
            example: The example to lint.
        """
        self.lint_black(example)
        self.lint_ruff(example)

    def lint_black(self, example: CodeExample) -> None:
        """Lint the example using black.

        Args:
            example: The example to lint.
        """
        example.test_id = self._test_id
        try:
            black_check(example, self.config)
        except FormatError as exc:
            raise PytestFailed(str(exc), pytrace=False) from None

    def lint_ruff(
        self,
        example: CodeExample,
    ) -> None:
        """Lint the example using ruff.

        Args:
            example: The example to lint.
        """
        example.test_id = self._test_id
        try:
            ruff_check(example, self.config)
        except FormatError as exc:
            raise PytestFailed(str(exc), pytrace=False) from None

    def format(self, example: CodeExample) -> None:
        """Format the example with black and ruff, requires `--update-examples`.

        Args:
            example: The example to format.
        """
        self.format_ruff(example)
        self.format_black(example)

    def format_black(self, example: CodeExample) -> None:
        """Format the example using black, requires `--update-examples`.

        Args:
            example: The example to lint.
        """
        self._check_update(example)

        new_content = black_format(example.source, self.config, remove_double_blank=example.in_py_file())
        if new_content != example.source:
            example.source = new_content
            self._mark_for_update(example)

    def format_ruff(
        self,
        example: CodeExample,
    ) -> None:
        """Format the example using ruff, requires `--update-examples`.

        Args:
            example: The example to lint.
        """
        self._check_update(example)

        try:
            new_content = ruff_format(example, self.config)
        except FormatError as exc:
            raise PytestFailed(str(exc), pytrace=False) from None
        else:
            if new_content != example.source:
                example.source = new_content
                self._mark_for_update(example)

    def _check_update(self, example: CodeExample) -> None:
        if not self.update_examples:
            raise RuntimeError('Cannot update examples without --update-examples')
        example.test_id = self._test_id

    def _mark_for_update(self, example: CodeExample) -> None:
        """Add the example to self.to_update IF it's not already there."""
        s = str(example)
        if not any(s == str(ex) for ex in self.to_update):
            self.to_update.append(example)

    def _write_file(self, example: CodeExample) -> Path:
        python_file = self.tmp_path / f'{example.module_name}.py'
        python_file.write_text(example.source)
        return python_file
