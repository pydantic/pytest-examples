from __future__ import annotations as _annotations

import difflib
import re
from subprocess import PIPE, Popen
from textwrap import indent
from typing import TYPE_CHECKING, Literal

from .config import ExamplesConfig

if TYPE_CHECKING:
    from .find_examples import CodeExample

__all__ = 'ruff_check', 'ruff_format', 'code_diff', 'FormatError'


class FormatError(ValueError):
    pass


def ruff_fix(example: CodeExample, config: ExamplesConfig, ignore_errors: bool = False) -> str:
    extra_args = ('--exit-zero',) if ignore_errors else ()
    try:
        return _invoke_ruff('check', example.source, config, extra_ruff_args=('--fix', *extra_args))
    except FormatError:
        # this is a workaround for https://github.com/charliermarsh/ruff/issues/3694#issuecomment-1483388856
        try:
            ruff_check(example, config)
        except FormatError as e2:
            raise e2 from None
        else:
            raise Exception('ruff failed in Fix mode but not in Check mode, please report this')


def ruff_format(source: str, config: ExamplesConfig, remove_double_blank: bool = False) -> str:
    return _invoke_ruff('format', source, config, remove_double_blank=remove_double_blank)


def ruff_check(example: CodeExample, config: ExamplesConfig, remove_double_blank: bool = False) -> None:
    try:
        _invoke_ruff('check', example.source, config)
    except FormatError as e:
        message = e.args[0]

        def replace_offset(m: re.Match):
            line_number = int(m.group(1))
            return f'  {example.path}:{line_number + example.start_line}'

        message = re.sub(r'^  -:(\d+)', replace_offset, message, flags=re.M)
        raise FormatError(message) from None

    try:
        _invoke_ruff(
            'format',
            example.source,
            config,
            extra_ruff_args=('--diff',),
            remove_double_blank=remove_double_blank,
        )
    except FormatError as e:
        # strip leading newlines
        message = e.args[0]
        # fixup start of the message to add before / after hints
        message = re.sub(r'(ruff failed:\n)(  @@[^\n]+\n)(   #\n){0,3}', r'\1  --- before\n  +++ after\n\2', message)

        def adjust_offset(m: re.match) -> str:
            (removed, added) = (m.group(1), m.group(2))
            removed = ','.join(str(int(x) + example.start_line) for x in removed.split(','))
            added = ','.join(str(int(x) + example.start_line) for x in added.split(','))
            return f'@@ -{removed} +{added} @@'

        message = re.sub(r'@@ -(\d+(?:,\d+)?) \+(\d+(?:,\d+)?) @@', adjust_offset, message)
        raise FormatError(message) from None


def _invoke_ruff(
    subcommand: Literal['check', 'format'],
    source: str,
    config: ExamplesConfig,
    *,
    remove_double_blank: bool = False,
    extra_ruff_args: tuple[str, ...] = (),
) -> str:
    args = 'ruff', subcommand, *config.ruff_config(), '-', *extra_ruff_args

    if subcommand == 'format':
        # hack to avoid ruff complaining about our print output format
        source = re.sub(r'^( *#)> ', r'\1 > ', source, flags=re.M)

    p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    stdout, stderr = p.communicate(source, timeout=2)

    if subcommand == 'format':
        # then revert it back
        stdout = re.sub(r'^( *#) > ', r'\1> ', stdout, flags=re.M)
        if remove_double_blank:
            stdout = re.sub(r'\n{3}', '\n\n', stdout)

        # remove trailing newline
        stdout = stdout.rstrip('\n')

    if p.returncode == 1 and stdout:
        raise FormatError(f'ruff failed:\n{indent(stdout, "  ")}')
    elif p.returncode != 0:
        raise RuntimeError(f'Error running ruff, return code {p.returncode}:\n{stderr or stdout}')
    else:
        return stdout


def code_diff(example: CodeExample, after: str) -> str:
    before = example.source.splitlines(keepends=True)
    after = after.splitlines(keepends=True)

    diff = ''.join(difflib.unified_diff(before, after, 'before', 'after'))

    def replace_at_line(match: re.Match) -> str:
        offset = re.sub(r'\d+', lambda m: str(int(m.group(0)) + example.start_line), match.group(2))
        return f'{match.group(1)}{offset}{match.group(3)}'

    return re.sub(r'^(@@\s*)(.*)(\s*@@)$', replace_at_line, diff, flags=re.M)
