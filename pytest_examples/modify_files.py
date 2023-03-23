from __future__ import annotations as _annotations

from itertools import groupby
from pathlib import Path
from textwrap import indent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .find_examples import CodeExample


def _modify_files(examples: list[CodeExample]) -> str:
    """
    Internal use only, update examples in place.
    """
    # The same example shouldn't appear more than once
    unique_examples: set[str] = set()
    for ex in examples:
        s = str(ex)
        if s in unique_examples:
            examples = '\n'.join(f'  {ex} (test: {ex.test_id})' for ex in examples)
            raise RuntimeError(f'Cannot update the same example in separate tests!\nexamples:\n{examples}')
        unique_examples.add(s)

    # same file should not appear in more than one group
    files: set[Path] = set()
    # order by line number descending so the earlier change doesn't mess up line numbers for later changes
    examples.sort(key=lambda x: (x.group, x.start_line), reverse=True)

    for _, g in groupby(examples, key=lambda x: x.group):
        new_files = {ex.path for ex in g}
        if new_files & files:
            raise RuntimeError('Cannot update the same file in separate groups!')
        files |= new_files

    msg = [f'pytest-examples: {len(examples)} examples to update in {len(files)} file(s)...']

    for path, g in groupby(examples, key=lambda ex: ex.path):
        content = path.read_text()
        count = 0
        for ex in g:
            example: CodeExample = ex
            new_source = example.source
            if example.indent:
                new_source = indent(new_source, ' ' * example.indent)
            content = content[: example.start_index] + new_source + content[example.end_index :]
            count += 1

        msg.append(f'  {path} {count} examples updated')
        path.write_text(content)

    return '\n'.join(msg)
