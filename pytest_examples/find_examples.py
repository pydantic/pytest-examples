import dataclasses
import re
from pathlib import Path
from textwrap import dedent

import pytest

__all__ = 'CodeExample', 'find_examples'


@dataclasses.dataclass
class CodeExample:
    """
    Information about a Python code example.
    """

    path: Path
    """The path to the file containing the example."""
    start_line: int
    """The line number of the first line of the example."""
    prefix: str
    """The prefix of the code block, e.g. `py`, can also contain `test="skip"`."""
    source: str
    """The source code of the example."""

    @property
    def module_name(self) -> str:
        """
        A suitable Python module name for testing the example.
        """
        return f'{self.path.stem}_{self.start_line}_{self.end_line}'

    @property
    def end_line(self) -> int:
        """
        The line number of the last line of the example.
        """
        return self.start_line + self.source.count('\n') + 1

    def __str__(self):
        try:
            path = self.path.relative_to(Path.cwd())
        except ValueError:
            path = self.path
        return f'{path}:{self.start_line}-{self.end_line}'


def _extract_code_chunks(path: Path, text: str, offset: int):
    for m_code in re.finditer(r'^```(.*?)$\n(.*?)^```', text, flags=re.M | re.S):
        prefix = m_code.group(1).lower()
        if prefix.startswith(('py', '{.py')):
            start_line = offset + text[: m_code.start()].count('\n') + 1
            example = CodeExample(path, start_line, prefix, m_code.group(2))
            yield pytest.param(example, id=str(example))


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
            if path.suffix == '.py':
                code = path.read_text()
                for m_docstring in re.finditer(r'(^\s*)r?"""$(.*?)\1"""', code, flags=re.M | re.S):
                    start_line = code[: m_docstring.start()].count('\n')
                    docstring = dedent(m_docstring.group(2))
                    yield from _extract_code_chunks(path, docstring, start_line)
            elif path.suffix == '.md':
                code = path.read_text()
                yield from _extract_code_chunks(path, code, 0)
