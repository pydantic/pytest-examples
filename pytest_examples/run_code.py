from __future__ import annotations as _annotations

import ast
import asyncio
import dataclasses
import importlib.util
import inspect
import io
import re
import sys
import tokenize
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from importlib.abc import Loader
from pathlib import Path
from textwrap import indent
from typing import TYPE_CHECKING, Any, TypeAlias
from unittest.mock import patch

import pytest
from black.parsing import InvalidInput

from .lint import black_format, code_diff
from .traceback import create_example_traceback

if TYPE_CHECKING:
    from .config import ExamplesConfig
    from .find_examples import CodeExample

__all__ = 'IncludePrint', 'InsertPrintStatements', 'run_code'

parent_frame_id = 4
IncludePrint: TypeAlias = Callable[[Path, inspect.FrameInfo, Sequence[Any]], bool]


def run_code(
    *,
    example: CodeExample,
    python_file: Path,
    loader: Loader | None,
    config: ExamplesConfig,
    enable_print_mock: bool,
    print_callback: Callable[[str], str] | None,
    include_print: IncludePrint | None,
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
        include_print: If not None, a function to call to determine if the print statement should be included.
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
    insert_print = InsertPrintStatements(python_file, config, enable_print_mock, print_callback, include_print)

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
            raise

    return insert_print, {k: v for k, v in module.__dict__.items() if not k.startswith(('__', '@'))}


@dataclass(init=False)
class Arg:
    """A single argument to a print statement."""

    data: str
    is_str: bool = False

    def __init__(self, v: Any) -> None:
        if isinstance(v, str):
            self.data = v
            self.is_str = True
        elif isinstance(v, set):
            # NOTE! this is not recursive
            items: set[Any] = v
            ordered = ', '.join(repr(x) for x in sorted(items))
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

    def __str__(self) -> str:
        return self.sep.join(map(str, self.args))


class MockPrintFunction:
    __slots__ = 'file', 'include_print', 'statements'

    def __init__(self, file: Path, include_print: IncludePrint | None) -> None:
        self.file = file
        self.statements: list[PrintStatement] = []
        self.include_print = include_print

    def __call__(self, *args: Any, sep: str = ' ', **kwargs: Any) -> None:
        frame = inspect.stack()[parent_frame_id]

        if self._include_file(frame, args):
            lineno = self._find_line_number(frame)
            s = PrintStatement(lineno, sep, [Arg(arg) for arg in args])
            self.statements.append(s)

    def _include_file(self, frame: inspect.FrameInfo, args: Sequence[Any]) -> bool:
        if self.include_print:
            return self.include_print(self.file, frame, args)
        else:
            return self.file.samefile(frame.filename)

    def _find_line_number(self, inspect_frame: inspect.FrameInfo) -> int:
        """Find the line number of the print statement in the file that is being executed."""
        frame = inspect_frame.frame
        while True:
            if self.file.samefile(frame.f_code.co_filename):
                return frame.f_lineno
            elif frame.f_back:
                frame = frame.f_back
            else:
                raise RuntimeError(f'Could not find line number of print statement at {inspect_frame}')


class InsertPrintStatements:
    def __init__(
        self,
        python_path: Path,
        config: ExamplesConfig,
        enable: bool,
        print_callback: Callable[[str], str] | None,
        include_print: IncludePrint | None,
    ) -> None:
        self.file = python_path
        self.config = config
        self.print_func = MockPrintFunction(python_path, include_print) if enable else None
        self.print_callback = print_callback
        self.patch = None

    def __enter__(self) -> None:
        if self.print_func:
            self.patch = patch('builtins.print', side_effect=self.print_func)
            self.patch.start()

    def __exit__(self, *args: object) -> None:
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
        tree = ast.parse(example.source, filename=example.path.name)
        print_locations = _find_print_locations(tree)

        executed_by_loc: dict[tuple[int, int], list[PrintStatement]] = {}
        executed_lines: set[int] = set()
        covered_comment_lines: set[int] = set()

        for s in self.print_func.statements:
            executed_lines.add(s.line_no)
            loc = print_locations.get(s.line_no) or (s.line_no, 0)
            line_no, _ = loc
            covered_comment_lines.update(range(s.line_no, line_no + 1))
            covered_comment_lines.update(_trailing_comment_lines(lines, line_no - 1))
            executed_by_loc.setdefault(loc, []).append(s)

        # Each action is (start_idx, delete_end_idx_or_None, col, executed_stmts_or_None)
        actions: list[tuple[int, int | None, int, list[PrintStatement] | None]] = [
            (line_no - 1, None, col, stmts) for (line_no, col), stmts in executed_by_loc.items()
        ]
        for start_idx, end_idx in _find_unexecuted_triple_quote_blocks(lines, print_locations, executed_lines):
            actions.append((start_idx, end_idx, 0, None))
        for comment_line in _find_comment_output_lines(example.source, lines):
            if comment_line not in covered_comment_lines:
                actions.append((comment_line - 1, comment_line, 0, None))

        # Apply edits from bottom to top so deleting or inserting lines does not shift earlier indices
        actions.sort(key=lambda a: a[0], reverse=True)
        for start_idx, end_idx, col, stmts in actions:
            if stmts is None:
                assert end_idx is not None
                del lines[start_idx:end_idx]
            else:
                remove_old_print(lines, start_idx)
                for s in reversed(stmts):
                    self._insert_print_args(lines, s, example.in_py_file(), start_idx, col)

        return '\n'.join(lines) + '\n'

    def _insert_print_args(
        self, lines: list[str], statement: PrintStatement, in_python: bool, line_index: int, col: int
    ) -> None:
        formatted_args = [self.print_callback(str(arg)) if self.print_callback else str(arg) for arg in statement.args]
        single_line = statement.sep.join(formatted_args)
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
comment_prefix_re = re.compile(rf'^ *{re.escape(comment_prefix.rstrip())}(?: |$)', re.MULTILINE)
triple_quotes_prefix_re = re.compile('^ *(?:"{3}|\'{3})', re.MULTILINE)


def remove_old_print(lines: list[str], line_index: int) -> None:
    """Remove the old print statement."""
    try:
        next_line = lines[line_index + 1]
    except IndexError:
        # end of file
        return

    if triple_quotes_prefix_re.search(next_line):
        for i in range(2, 10_000):
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

    Args:
        example: the `CodeExample`
        line_no: The line number on which the print statement starts or approx

    Return: tuple if `(line, column)` of the print statement
    """
    m = ast.parse(example.source, filename=example.path.name)
    return find_print(m, line_no) or (line_no, 0)


def _is_print_call(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Name) and call.func.id == 'print'


def _iter_statement_calls(node: ast.AST) -> Iterator[ast.Call]:
    if isinstance(node, ast.Call):
        cur: ast.expr = node
        while isinstance(cur, ast.Call):
            yield cur
            cur = cur.func
    elif isinstance(node, ast.Expr):
        yield from _iter_statement_calls(node.value)
    elif isinstance(node, (ast.Module, ast.stmt, ast.ExceptHandler, ast.match_case)):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.stmt, ast.ExceptHandler, ast.match_case)):
                yield from _iter_statement_calls(child)


def _find_print_locations(tree: ast.AST) -> dict[int, tuple[int, int]]:
    locations: dict[int, tuple[int, int]] = {}
    for call in _iter_statement_calls(tree):
        if _is_print_call(call):
            locations.setdefault(call.lineno, (expr_last_line(call), call.col_offset))
    return locations


def _trailing_comment_lines(lines: list[str], line_index: int) -> Iterator[int]:
    idx = line_index + 1
    while idx < len(lines) and comment_prefix_re.search(lines[idx]):
        yield idx + 1
        idx += 1


def _find_comment_output_lines(source: str, lines: list[str]) -> list[int]:
    comment_lines: list[int] = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            line_no = tok.start[0]
            if comment_prefix_re.match(lines[line_no - 1]):
                comment_lines.append(line_no)
    return comment_lines


def _find_unexecuted_triple_quote_blocks(
    lines: list[str],
    print_locations: dict[int, tuple[int, int]],
    executed_lines: set[int],
) -> list[tuple[int, int]]:
    removals: list[tuple[int, int]] = []
    for call_line, (line_no, col) in print_locations.items():
        if call_line in executed_lines or line_no >= len(lines):
            continue
        opening = lines[line_no].rstrip()
        if opening not in (' ' * col + '"""', ' ' * col + "'''"):
            continue
        end_idx = next((i for i in range(line_no + 1, len(lines)) if lines[i].rstrip() == opening), None)
        if end_idx is not None:
            removals.append((line_no, end_idx + 1))
    return removals


def find_print(node: ast.AST, line: int) -> tuple[int, int] | None:
    for call in _iter_statement_calls(node):
        if _is_print_call(call) and call.lineno == line:
            return expr_last_line(call), call.col_offset
    return None


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
    elif isinstance(c, ast.List | ast.Tuple | ast.Set):
        if c.elts:
            return maybe_plus_1(c, expr_last_line(c.elts[-1]))
        else:
            return c.lineno
    elif isinstance(c, ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp):
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
