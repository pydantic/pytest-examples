from __future__ import annotations as _annotations

import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Iterable
from uuid import UUID, uuid4

__all__ = 'CodeExample', 'find_examples'


@dataclass
class CodeExample:
    """
    Information about a Python code example.
    """

    source: str
    """The source code of the example, this is has any indent removed."""
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
    """The prefix of the code block, e.g. `py`, can also contain rules for skipping some tests."""
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
        start_line: int = 0,
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
        return cls(
            source=source,
            path=path,
            start_line=start_line,
            end_line=end_line,
            start_index=start_index,
            end_index=end_index,
            prefix=prefix,
            indent=indent,
        )

    @property
    def module_name(self) -> str:
        """
        A suitable Python module name for testing the example.
        """
        return f'{self.path.stem}_{self.start_line}_{self.end_line}'

    def prefix_settings(self) -> dict[str, str]:
        """
        Key/value pairs from the prefix line
        """
        settings = {}
        for m in re.finditer(r'(\S+?)=([\'"])(.+?)\2', self.prefix):
            settings[m.group(1)] = m.group(3)
        return settings

    def in_py_file(self) -> bool:
        """
        Whether the example is in a Python file.
        """
        return self.path.suffix == '.py'

    def __str__(self):
        try:
            path = self.path.relative_to(Path.cwd())
        except ValueError:
            path = self.path
        return f'{path}:{self.start_line}-{self.end_line}'


def find_examples(*paths: str, skip: bool = False) -> Iterable[CodeExample]:
    """
    Find Python code examples in markdown files and python file docstrings.

    :param paths: Directories or files to search for examples in.
    :param skip: Whether to exit early and not search for examples, useful when running on windows where search fails.
    :return: A generator of `CodeExample` objects.
    """
    if skip:
        return

    for s in paths:
        path = Path(s)
        if path.is_file():
            sub_paths = [path]
        elif path.is_dir():
            sub_paths = path.glob('**/*')
        else:
            raise ValueError(f'Not a file or directory: {s!r}')

        for path in sub_paths:
            group = uuid4()
            if path.suffix == '.py':
                code = path.read_text('utf-8')
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


def _extract_code_chunks(
    path: Path, text: str, group: UUID, *, line_offset: int = 0, index_offset: int = 0
) -> Iterable[CodeExample]:
    for m_code in re.finditer(r'(^ *)```(.*?)$\n(.+?)\1```', text, flags=re.M | re.S):
        prefix = m_code.group(2).lower()
        if prefix.startswith(('py', '{.py')):
            start_line = line_offset + text[: m_code.start()].count('\n') + 1
            source = m_code.group(3)
            source_dedent, indent = remove_indent(source)
            # 3 for the ``` and 1 for the newline
            start_index = index_offset + m_code.start() + len(m_code.group(1)) + 3 + len(prefix) + 1
            yield CodeExample(
                source=source_dedent,
                path=path,
                start_line=start_line,
                end_line=start_line + source.count('\n') + 1,
                start_index=start_index,
                end_index=start_index + len(source),
                prefix=prefix,
                indent=indent,
                group=group,
            )


def remove_indent(text: str) -> tuple[str, int]:
    """
    Remove the given indent from each line of text, return the dedented text and the indent.
    """
    first_line_before = text[: text.strip('\n').find('\n')]
    text = dedent(text)
    first_line_after = text[: text.strip('\n').find('\n')]
    return text, len(first_line_before) - len(first_line_after)
