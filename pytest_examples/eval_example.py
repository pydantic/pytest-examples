from __future__ import annotations as _annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from _pytest.assertion.rewrite import AssertionRewritingHook

from .config import DEFAULT_LINE_LENGTH, ExamplesConfig
from .insert_print import InsertPrintStatements
from .lint import black_check, black_format, ruff_check, ruff_format
from .traceback import create_example_traceback

if TYPE_CHECKING:
    from typing import Literal

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
        self.config: ExamplesConfig = ExamplesConfig()

    def set_config(
        self,
        *,
        line_length: int = DEFAULT_LINE_LENGTH,
        quotes: Literal['single', 'double', 'either'] = 'either',
        magic_trailing_comma: bool = True,
        target_version: Literal['py37', 'py38', 'py39', 'py310', 'py310'] = 'py37',
        upgrade: bool = False,
        ruff_line_length: int | None = None,
        ruff_ignore: list[str] | None = None,
    ):
        """
        Set the config for lints

        :param line_length: The line length to use when wrapping print statements, defaults to 88.
        :param quotes: The quote to use, defaults to "either".
        :param magic_trailing_comma: If True, add a trailing comma to magic methods, defaults to True.
        :param target_version: The target version to use when upgrading code, defaults to "py37".
        :param upgrade: If True, upgrade the code to the target version, defaults to False.
        :param ruff_line_length: In general, we disable line-length checks in ruff, to let black take care of them.
        :param ruff_ignore: Ruff rule to ignore
        """
        self.config = ExamplesConfig(
            line_length=line_length,
            quotes=quotes,
            magic_trailing_comma=magic_trailing_comma,
            target_version=target_version,
            upgrade=upgrade,
            ruff_line_length=ruff_line_length,
            ruff_ignore=ruff_ignore,
        )

    @property
    def update_examples(self) -> bool:
        return self._pytest_config.getoption('update_examples')

    def run(
        self,
        example: CodeExample,
        *,
        module_globals: dict[str, Any] | None = None,
        rewrite_assertions: bool = True,
    ) -> dict[str, Any]:
        """
        Run the example, print is not mocked and print statements are not checked.

        :param example: The example to run.
        :param module_globals: The globals to use when running the example.
        :param rewrite_assertions: If True, rewrite assertions in the example using pytest's assertion rewriting.
        """
        __tracebackhide__ = True
        example.test_id = self._test_id
        _, module_dict = self._run(example, None, module_globals, rewrite_assertions)
        return module_dict

    def run_print_check(
        self,
        example: CodeExample,
        *,
        module_globals: dict[str, Any] | None = None,
        rewrite_assertions: bool = True,
    ) -> dict[str, Any]:
        """
        Run the example and check print statements.

        :param example: The example to run.
        :param module_globals: The globals to use when running the example.
        :param rewrite_assertions: If True, rewrite assertions in the example using pytest's assertion rewriting.
        """
        __tracebackhide__ = True
        example.test_id = self._test_id
        insert_print, module_dict = self._run(example, 'check', module_globals, rewrite_assertions)
        insert_print.check_print_statements(example)
        return module_dict

    def run_print_update(
        self,
        example: CodeExample,
        *,
        module_globals: dict[str, Any] | None = None,
        rewrite_assertions: bool = True,
    ) -> dict[str, Any]:
        """
        Run the example and update print statements, requires `--update-examples`.

        :param example: The example to run.
        :param module_globals: The globals to use when running the example.
        :param rewrite_assertions: If True, rewrite assertions in the example using pytest's assertion rewriting.
        """
        __tracebackhide__ = True
        self._check_update(example)
        insert_print, module_dict = self._run(example, 'update', module_globals, rewrite_assertions)

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
    ) -> tuple[InsertPrintStatements, dict[str, Any]]:
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
        insert_print = InsertPrintStatements(python_file, self.config, enable_print_mock)

        if module_globals:
            module.__dict__.update(module_globals)
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

        return insert_print, {k: v for k, v in module.__dict__.items() if not k.startswith(('__', '@'))}

    def lint(self, example: CodeExample) -> None:
        """
        Lint the example with black and ruff.

        :param example: The example to lint.
        :param line_length: The line length to use when linting.
        """
        self.lint_black(example)
        self.lint_ruff(example)

    def lint_black(self, example: CodeExample) -> None:
        """
        Lint the example using black.

        :param example: The example to lint.
        """
        example.test_id = self._test_id
        black_check(example, self.config)

    def lint_ruff(
        self,
        example: CodeExample,
    ) -> None:
        """
        Lint the example using ruff.

        :param example: The example to lint.
        """
        example.test_id = self._test_id
        ruff_check(example, self.config)

    def format(self, example: CodeExample) -> None:
        """
        Format the example with black and ruff, requires `--update-examples`.

        :param example: The example to format.
        """
        self.format_black(example)
        self.format_ruff(example)

    def format_black(self, example: CodeExample) -> None:
        """
        Format the example using black, requires `--update-examples`.

        :param example: The example to lint.
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
        """
        Format the example using ruff, requires `--update-examples`.

        :param example: The example to lint.
        """
        self._check_update(example)

        new_content = ruff_format(example, self.config)
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
        # python_file.parent.mkdir(exist_ok=True)
        if self.update_examples:
            # if we're in update mode, we need to always rewrite the file
            python_file.write_text(example.source)
        elif not python_file.exists():
            # assume if it already exists, it's because it was previously written in this test
            python_file.write_text(example.source)
        return python_file
