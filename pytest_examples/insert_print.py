from __future__ import annotations as _annotations

import inspect
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from textwrap import indent
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from .lint import black_format, code_diff

if TYPE_CHECKING:
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
        else:
            self.code = str(v)

    def __str__(self) -> str:
        if self.string is not None:
            return self.string
        else:
            return self.code

    def format(self, black_length: int) -> str:
        if self.string is not None:
            r = repr(self.string)
        else:
            r = self.code
        return black_format(r, black_length)


@dataclass
class PrintStatement:
    line_no: int
    sep: str
    args: list[Arg]


class MockPrintFunction:
    def __init__(self, file: Path) -> None:
        self.file = file
        self.statements: list[PrintStatement] = []

    def __call__(self, *args: Any, sep: str = ' ', **kwargs: Any) -> None:
        frame = inspect.stack()[parent_frame_id]

        if self.file.samefile(frame.filename):
            # -1 to account for the line number being 1-indexed
            s = PrintStatement(frame.lineno - 1, sep, [Arg(arg) for arg in args])
            self.statements.append(s)


class InsertPrintStatements:
    def __init__(self, python_path: Path, line_length: int, enable: bool):
        self.file = python_path
        self.line_length = line_length
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

        for s in reversed(self.print_func.statements):
            remove_old_print(lines, s.line_no)
            indent = find_print_indent(lines, s.line_no)
            self._insert_print_args(lines, s, indent)

        return '\n'.join(lines) + '\n'

    def _insert_print_args(self, lines: list[str], statement: PrintStatement, indent_str: str) -> None:
        single_line = statement.sep.join(map(str, statement.args))
        if len(single_line) < self.line_length - len(indent_str) - len(comment_prefix):
            lines.insert(statement.line_no + 1, f'{indent_str}{comment_prefix}{single_line}')
        else:
            # if the statement is too long to go on one line, print each arg on its own line formatted with black
            sep = f'{statement.sep}\n'
            black_length = self.line_length - len(indent_str)
            output = sep.join(arg.format(black_length) for arg in statement.args)
            lines.insert(statement.line_no + 1, indent(f'"""\n{output}"""', indent_str))


comment_prefix = '#> '
comment_prefix_re = re.compile(f'^ *{re.escape(comment_prefix)}', re.MULTILINE)
triple_quotes_prefix = re.compile('^ *"""', re.MULTILINE)


def remove_old_print(lines: list[str], line_no: int) -> None:
    """
    Remove the old print statement.
    """
    try:
        next_line = lines[line_no + 1]
    except IndexError:
        # end of file
        return

    if triple_quotes_prefix.search(next_line):
        for i in range(2, 100):
            if triple_quotes_prefix.search(lines[line_no + i]):
                del lines[line_no + 1 : line_no + i + 1]
                return
        raise ValueError('Could not find end of triple quotes')
    else:
        try:
            while comment_prefix_re.search(lines[line_no + 1]):
                del lines[line_no + 1]
        except IndexError:
            # end of file
            pass


def find_print_indent(lines: list[str], line_no: int) -> str:
    """
    Look back through recent lines to find the "print(" function and return its indentation.
    """
    for back in range(100):
        m = re.search(r'^( *)print\(', lines[line_no - back])
        if m:
            return m.group(1)
    return ''
