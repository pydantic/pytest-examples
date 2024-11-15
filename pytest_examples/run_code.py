from __future__ import annotations as _annotations

import ast
import asyncio
import dataclasses
import importlib.util
import inspect
import re
import sys
from dataclasses import dataclass
from importlib.abc import Loader
from pathlib import Path
from textwrap import indent
from typing import TYPE_CHECKING, Any, Callable
from unittest.mock import patch

import pytest
from black.parsing import InvalidInput

from .lint import black_format, code_diff
from .traceback import create_example_traceback

if TYPE_CHECKING:
    from .config import ExamplesConfig
    from .find_examples import CodeExample

__all__ = 'run_code', 'InsertPrintStatements'

parent_frame_id = 4 if sys.version_info >= (3, 8) else 3


def run_code(
    *,
    example: CodeExample,
    python_file: Path,
    loader: Loader | None,
    config: ExamplesConfig,
    enable_print_mock: bool,
    print_callback: Callable[[str], str] | None,
    module_globals: dict[str, Any] | None,
    call: str | None,
) -> tuple[InsertPrintStatements, dict[str, Any]]:
    """Run the code example.

    Args:
        example: The `CodeExample` to run.
        python_file: The path to the python file.
        loader: optional loader to use to load the module.
        config: The `ExamplesConfig` to use.
        enable_print_mock: If True, mock the `print` function.
        print_callback: If not None, a callback to call on `print`.
        module_globals: The extra globals to add before calling the module.
        call: If not None, a (coroutine) function to call in the module.

    Returns:
        A tuple of the `InsertPrintStatements` instance and the module's globals.
    """
    __tracebackhide__ = True

    spec = importlib.util.spec_from_file_location('__main__', str(python_file), loader=loader)
    assert spec is not None, f'Could not load {python_file}'
    assert spec.loader is not None, f'Loader is None for {python_file}'
    module = importlib.util.module_from_spec(spec)

    # does nothing if insert_print_statements is False
    insert_print = InsertPrintStatements(python_file, config, enable_print_mock, print_callback)

    if module_globals:
        module.__dict__.update(module_globals)

    try:
        with insert_print:
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            if call:
                to_call = getattr(module, call, None)
                if to_call is not None:
                    if inspect.iscoroutinefunction(to_call):
                        asyncio.run(to_call())
                    else:
                        to_call()
    except KeyboardInterrupt:
        print('KeyboardInterrupt in example')
    except Exception as exc:
        example_tb = create_example_traceback(exc, str(python_file), example)
        if example_tb:
            raise exc.with_traceback(example_tb)
        else:
            raise exc

    return insert_print, {k: v for k, v in module.__dict__.items() if not k.startswith(('__', '@'))}


@dataclass(init=False)
class Arg:
    """A single argument to a print statement."""

    data: str
    is_str: bool = False

    def __init__(self, v: Any):
        if isinstance(v, str):
            self.data = v
            self.is_str = True
        elif isinstance(v, set):
            # NOTE! this is not recursive
            ordered = ', '.join(repr(x) for x in sorted(v))
            self.data = f'{{{ordered}}}'
        else:
            self.data = re.sub('0x[a-f0-9]{8,12}>', '0x0123456789ab>', str(v))

    def __str__(self) -> str:
        return self.data

    def format(self, config: ExamplesConfig) -> str:
        if self.is_str:
            return self.data
        else:
            try:
                return black_format(self.data, config)
            except InvalidInput:
                return self.data


@dataclass
class PrintStatement:
    """A single print statement."""

    line_no: int
    sep: str
    args: list[Arg]

    def __str__(self):
        return self.sep.join(map(str, self.args))


def not_print(*args):
    import sys

    sys.stdout.write(' '.join(map(str, args)) + '\n')


class MockPrintFunction:
    def __init__(self, file: Path) -> None:
        self.file = file
        self.statements: list[PrintStatement] = []

    def __call__(self, *args: Any, sep: str = ' ', **kwargs: Any) -> None:
        frame = inspect.stack()[parent_frame_id]

        if self.file.samefile(frame.filename):
            # -1 to account for the line number being 1-indexed
            s = PrintStatement(frame.lineno, sep, [Arg(arg) for arg in args])
            self.statements.append(s)


class InsertPrintStatements:
    def __init__(
        self, python_path: Path, config: ExamplesConfig, enable: bool, print_callback: Callable[[str], str] | None
    ):
        self.file = python_path
        self.config = config
        self.print_func = MockPrintFunction(python_path) if enable else None
        self.print_callback = print_callback
        self.patch = None

    def __enter__(self) -> None:
        if self.print_func:
            self.patch = patch('builtins.print', side_effect=self.print_func)
            self.patch.start()

    def __exit__(self, *args) -> None:
        if self.patch is not None:
            self.patch.stop()

    def check_print_statements(self, example: CodeExample) -> None:
        new_code = self.updated_print_statements(example)
        if new_code is not None:
            diff = code_diff(example, new_code, self.config)
            pytest.fail(f'Print output changed code:\n{indent(diff, "  ")}', pytrace=False)

    def updated_print_statements(self, example: CodeExample) -> str | None:
        with_prints = self._insert_print_statements(example)
        # we check against the raw `with_prints` and `with_prints` with trailing whitespace removed
        # since trailing white space will have already been stripped by pre-commit in `example.source`
        if example.source not in (with_prints, re.sub(r'[ \t]+\n', '\n', with_prints)):
            return with_prints

    def print_statements(self) -> list[PrintStatement]:
        return self.print_func.statements if self.print_func else []

    def _insert_print_statements(self, example: CodeExample) -> str:
        assert self.print_func is not None, 'print statements not being inserted'

        lines = example.source.splitlines()

        old_line_no = -1

        for s in reversed(self.print_func.statements):
            line_no, col = find_print_location(example, s.line_no)

            # switch from 1-indexed line number to 0-indexed indexes into lines
            line_index = line_no - 1

            if s.line_no != old_line_no:
                remove_old_print(lines, line_index)
            self._insert_print_args(lines, s, example.in_py_file(), line_index, col)
            old_line_no = s.line_no

        return '\n'.join(lines) + '\n'

    def _insert_print_args(
        self, lines: list[str], statement: PrintStatement, in_python: bool, line_index: int, col: int
    ) -> None:
        single_line = statement.sep.join(map(str, statement.args))
        if self.print_callback:
            single_line = self.print_callback(single_line)
        indent_str = ' ' * col
        max_single_length = self.config.line_length - len(indent_str)
        if '\n' not in single_line and len(single_line) + len(comment_prefix) < max_single_length:
            lines.insert(line_index + 1, f'{indent_str}{comment_prefix}{single_line}')
        else:
            # if the statement is too long to go on one line, print each arg on its own line formatted with black
            sep = f'{statement.sep}\n'
            indent_config = dataclasses.replace(self.config, line_length=max_single_length)
            output = sep.join(arg.format(indent_config).strip('\n') for arg in statement.args)
            if self.print_callback:
                output = self.print_callback(output)
            # remove trailing whitespace
            output = re.sub(r' +$', '', output, flags=re.MULTILINE)
            # have to use triple single quotes in python since we're already in a double quotes docstring
            quote = "'''" if in_python else '"""'
            lines.insert(line_index + 1, indent(f'{quote}\n{output}\n{quote}', indent_str))


comment_prefix = '#> '
comment_prefix_re = re.compile(f'^ *{re.escape(comment_prefix)}', re.MULTILINE)
triple_quotes_prefix_re = re.compile('^ *(?:"{3}|\'{3})', re.MULTILINE)


def find_print_line(lines: list[str], line_no: int) -> int:
    """For 3.7 we have to reverse through lines to find the print statement lint."""
    return line_no

    for back in range(100):
        new_line_no = line_no - back
        m = re.search(r'^ *print\(', lines[new_line_no - 1])
        if m:
            return new_line_no
    return line_no


def remove_old_print(lines: list[str], line_index: int) -> None:
    """Remove the old print statement."""
    try:
        next_line = lines[line_index + 1]
    except IndexError:
        # end of file
        return

    if triple_quotes_prefix_re.search(next_line):
        for i in range(2, 100):
            if triple_quotes_prefix_re.search(lines[line_index + i]):
                del lines[line_index + 1 : line_index + i + 1]
                return
        raise ValueError('Could not find end of triple quotes')
    else:
        try:
            while comment_prefix_re.search(lines[line_index + 1]):
                del lines[line_index + 1]
        except IndexError:
            # end of file
            pass


def find_print_location(example: CodeExample, line_no: int) -> tuple[int, int]:
    """Find the line and column of the print statement.

    :param example: the `CodeExample`
    :param line_no: The line number on which the print statement starts (or approx on 3.7)
    :return: tuple if `(line, column)` of the print statement
    """
    # For 3.7 we have to reverse through lines to find the print statement lint

    m = ast.parse(example.source, filename=example.path.name)
    return find_print(m, line_no) or (line_no, 0)


# ast nodes that have a body
with_body = (
    ast.Module,
    ast.FunctionDef,
    ast.If,
    ast.Try,
    ast.ExceptHandler,
    ast.With,
    ast.For,
    ast.AsyncFor,
    ast.AsyncFunctionDef,
    ast.AsyncWith,
    ast.While,
    ast.ClassDef,
)


def find_print(node: Any, line: int) -> tuple[int, int] | None:
    if isinstance(node, with_body):
        found_loc = find_print_in_body(node.body, line)
        if found_loc is not None:
            return found_loc
        if isinstance(node, ast.If):
            found_loc = find_print_in_body(node.orelse, line)
            if found_loc is not None:
                return found_loc
        elif isinstance(node, ast.Try):
            for node in node.handlers:
                found_loc = find_print(node, line)
                if found_loc is not None:
                    return found_loc
    elif isinstance(node, ast.Expr):
        return find_print(node.value, line)
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == 'print' and node.lineno == line:
            return expr_last_line(node), node.col_offset
        return find_print(node.func, line)


def find_print_in_body(body: list[ast.stmt], line: int) -> tuple[int, int] | None:
    for node in body:
        found_loc = find_print(node, line)
        if found_loc is not None:
            return found_loc


def expr_last_line(c: ast.expr) -> int:
    if isinstance(c, ast.Constant):
        return c.lineno
    if isinstance(c, ast.Call):
        if c.keywords:
            return maybe_plus_1(c, expr_last_line(c.keywords[-1].value))
        elif c.args:
            return maybe_plus_1(c, expr_last_line(c.args[-1]))
        else:
            return c.lineno
    elif isinstance(c, (ast.List, ast.Tuple, ast.Set)):
        if c.elts:
            return maybe_plus_1(c, expr_last_line(c.elts[-1]))
        else:
            return c.lineno
    elif isinstance(c, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        gen = c.generators[-1]
        if gen.ifs:
            return maybe_plus_1(c, expr_last_line(gen.ifs[-1]))
        else:
            return maybe_plus_1(c, expr_last_line(gen.iter))
    else:
        return c.lineno


def maybe_plus_1(c: ast.expr, last_arg_line: int) -> int:
    if c.lineno == last_arg_line:
        # all args are on the same line, assume the basic `print(x, y)` case
        return c.lineno
    else:
        # args are on multiple lines, assume the following format an extra line with `)`
        return last_arg_line + 1
