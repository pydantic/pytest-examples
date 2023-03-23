from __future__ import annotations as _annotations

import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from uuid import UUID, uuid4

import pytest

__all__ = 'CodeExample', 'find_examples'


@dataclass
class CodeExample:
    """
    Information about a Python code example.
    """

    path: Path
    """The path to the file containing the example."""
    start_line: int
    """The line number of the first line of the example."""
    end_line: int
    """The line number of the last line of the example."""
    start_index: int
    """Index of the start of the example."""
    end_index: int
    """Index of the end of the example."""
    prefix: str
    """The prefix of the code block, e.g. `py`, can also contain `test="skip"`."""
    source: str
    """The source code of the example, this is has any indent removed."""
    indent: int
    """The indentation of the example, number of spaces."""
    group: UUID | None = None
    """A unique identifier for the example group."""
    test_id: str | None = None
    """ID of the test this example was generated for."""

    @classmethod
    def create(
        cls,
        source: str,
        *,
        path: Path = Path('testing.md'),
        start_line: int = 1,
        end_line: int | None = None,
        start_index: int = 0,
        end_index: int | None = None,
        prefix: str = '',
        indent: int = 0,
    ):
        """
        Create a `CodeExample`, mostly for testing.
        """
        if end_line is None:
            end_line = start_line + source.count('\n')
        if end_index is None:
            end_index = start_index + len(source)
        return cls(path, start_line, end_line, start_index, end_index, prefix, source, indent)

    @property
    def module_name(self) -> str:
        """
        A suitable Python module name for testing the example.
        """
        return f'{self.path.stem}_{self.start_line}_{self.end_line}'

    def __str__(self):
        try:
            path = self.path.relative_to(Path.cwd())
        except ValueError:
            path = self.path
        return f'{path}:{self.start_line}-{self.end_line}'


def find_examples(*directories: str):
    """
    Find Python code examples in markdown files and python file docstrings.

    Yields `CodeExample` objects wrapped in a `pytest.param` object.
    """
    for d in directories:
        dir_path = Path(d)
        if dir_path.is_file():
            paths = [dir_path]
        elif dir_path.is_dir():
            paths = dir_path.glob('**/*')
        else:
            raise ValueError(f'Not a file or directory: {d!r}')

        for path in paths:
            group = uuid4()
            if path.suffix == '.py':
                code = path.read_text()
                for m_docstring in re.finditer(r'(^ *)(r?"""\n)(.+?)\1"""', code, flags=re.M | re.S):
                    start_line = code[: m_docstring.start()].count('\n') + 1
                    docstring = m_docstring.group(3)
                    index_offset = m_docstring.start() + len(m_docstring.group(1)) + len(m_docstring.group(2))
                    yield from _extract_code_chunks(
                        path, docstring, group, line_offset=start_line, index_offset=index_offset
                    )
            elif path.suffix == '.md':
                code = path.read_text()
                yield from _extract_code_chunks(path, code, group)


def _extract_code_chunks(path: Path, text: str, group: UUID, *, line_offset: int = 0, index_offset: int = 0):
    for m_code in re.finditer(r'(^ *)```(.*?)$\n(.+?)\1```', text, flags=re.M | re.S):
        prefix = m_code.group(2).lower()
        if prefix.startswith(('py', '{.py')):
            start_line = line_offset + text[: m_code.start()].count('\n') + 1
            source = m_code.group(3)
            source_dedent, indent = remove_indent(source)
            # 3 for the ``` and 1 for the newline
            start_index = index_offset + m_code.start() + len(m_code.group(1)) + 3 + len(prefix) + 1
            example = CodeExample(
                path,
                start_line,
                start_line + source.count('\n') + 1,
                start_index,
                start_index + len(source),
                prefix,
                source_dedent,
                indent,
                group,
            )
            yield pytest.param(example, id=str(example))


def remove_indent(text: str) -> tuple[str, int]:
    """
    Remove the given indent from each line of text, return the dedented text and the indent.
    """
    first_line_before = text[: text.strip('\n').find('\n')]
    text = dedent(text)
    first_line_after = text[: text.strip('\n').find('\n')]
    return text, len(first_line_before) - len(first_line_after)
