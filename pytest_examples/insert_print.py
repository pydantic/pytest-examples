from __future__ import annotations as _annotations

import ast
import dataclasses
import inspect
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from textwrap import indent
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from black import InvalidInput

from .lint import black_format, code_diff

if TYPE_CHECKING:
    from .config import ExamplesConfig
    from .find_examples import CodeExample

__all__ = ('InsertPrintStatements',)

parent_frame_id = 4 if sys.version_info >= (3, 8) else 3


@dataclass(init=False)
class Arg:
    string: str | None = None
    code: str | None = None

    def __init__(self, v: Any):
        if isinstance(v, str):
            self.string = v
        elif isinstance(v, set):
            # NOTE! this is not recursive
            ordered = ', '.join(repr(x) for x in sorted(v))
            self.string = f'{{{ordered}}}'
        else:
            self.code = re.sub('0x[a-f0-9]{8,12}>', '0x0123456789ab>', str(v))

    def __str__(self) -> str:
        if self.string is not None:
            return self.string
        else:
            return self.code

    def format(self, config: ExamplesConfig) -> str:
        if self.string is not None:
            return self.string
        else:
            try:
                return black_format(self.code, config)
            except InvalidInput:
                return self.code


@dataclass
class PrintStatement:
    line_no: int
    sep: str
    args: list[Arg]


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
    def __init__(self, python_path: Path, config: ExamplesConfig, enable: bool):
        self.file = python_path
        self.config = config
        self.print_func = MockPrintFunction(python_path) if enable else None
        self.patch = None

    def __enter__(self) -> None:
        if self.print_func:
            self.patch = patch('builtins.print', side_effect=self.print_func)
            self.patch.start()

    def __exit__(self, *args) -> None:
        if self.patch is not None:
            self.patch.stop()

    def check_print_statements(self, example: CodeExample) -> None:
        with_prints = self._insert_print_statements(example)
        if example.source != with_prints:
            diff = code_diff(example, with_prints)
            pytest.fail(f'Print output changed code:\n{indent(diff, "  ")}', pytrace=False)

    def updated_print_statements(self, example: CodeExample) -> str | None:
        with_prints = self._insert_print_statements(example)
        if example.source != with_prints:
            return with_prints

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
        indent_str = ' ' * col
        max_single_length = self.config.line_length - len(indent_str)
        if '\n' not in single_line and len(single_line) + len(comment_prefix) < max_single_length:
            lines.insert(line_index + 1, f'{indent_str}{comment_prefix}{single_line}')
        else:
            # if the statement is too long to go on one line, print each arg on its own line formatted with black
            sep = f'{statement.sep}\n'
            indent_config = dataclasses.replace(self.config, line_length=max_single_length)
            output = sep.join(arg.format(indent_config).strip('\n') for arg in statement.args)
            # remove trailing whitespace
            output = re.sub(r' +$', '', output, flags=re.MULTILINE)
            # have to use triple single quotes in python since we're already in a double quotes docstring
            quote = "'''" if in_python else '"""'
            lines.insert(line_index + 1, indent(f'{quote}\n{output}\n{quote}', indent_str))


comment_prefix = '#> '
comment_prefix_re = re.compile(f'^ *{re.escape(comment_prefix)}', re.MULTILINE)
triple_quotes_prefix_re = re.compile('^ *(?:"{3}|\'{3})', re.MULTILINE)


def find_print_line(lines: list[str], line_no: int) -> int:
    """
    For 3.7 we have to reverse through lines to find the print statement lint
    """
    if sys.version_info >= (3, 8):
        return line_no

    for back in range(100):
        new_line_no = line_no - back
        m = re.search(r'^ *print\(', lines[new_line_no - 1])
        if m:
            return new_line_no
    return line_no


def remove_old_print(lines: list[str], line_index: int) -> None:
    """
    Remove the old print statement.
    """
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
    """
    Find the line and column of the print statement.

    :param example: the `CodeExample`
    :param line_no: The line number on which the print statement starts (or approx on 3.7)
    :return: tuple if `(line, column)` of the print statement
    """
    # For 3.7 we have to reverse through lines to find the print statement lint
    if sys.version_info < (3, 8):
        # find the last print statement before the line
        lines = example.source.splitlines()
        for back in range(100):
            new_line_no = line_no - back
            m = re.match(r' *print\(', lines[new_line_no - 1])
            if m:
                line_no = new_line_no
                break

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
