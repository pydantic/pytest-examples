from __future__ import annotations as _annotations

import re
from subprocess import PIPE, Popen
from textwrap import indent
from typing import TYPE_CHECKING

from ruff.__main__ import find_ruff_bin

from .config import ExamplesConfig

if TYPE_CHECKING:
    from .find_examples import CodeExample

__all__ = 'ruff_check', 'ruff_format', 'code_diff', 'FormatError'


class FormatError(ValueError):
    pass


def ruff_format(
    example: CodeExample,
    config: ExamplesConfig,
    *,
    ignore_errors: bool = False,
) -> str:
    args = ('--fix',)
    if ignore_errors:
        args += ('--exit-zero',)
    try:
        return ruff_check(example, config, extra_ruff_args=args)
    except FormatError:
        # this is a workaround for https://github.com/charliermarsh/ruff/issues/3694#issuecomment-1483388856
        try:
            ruff_check(example, config)
        except FormatError as e2:
            raise e2 from None
        else:
            raise Exception('ruff failed in Fix mode but not in Check mode, please report this')


def ruff_check(
    example: CodeExample,
    config: ExamplesConfig,
    *,
    extra_ruff_args: tuple[str, ...] = (),
) -> str:
    ruff = find_ruff_bin()
    args = ruff, 'check', '-', *config.ruff_config(), *extra_ruff_args

    p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    stdout, stderr = p.communicate(example.source, timeout=10)
    if p.returncode == 1 and stdout:

        def replace_offset(m: re.Match):
            line_number = int(m.group(1))
            return f'{example.path}:{line_number + example.start_line}'

        output = re.sub(r'^-:(\d+)', replace_offset, stdout, flags=re.M)
        raise FormatError(f'ruff failed:\n{indent(output, "  ")}')
    elif p.returncode != 0:
        raise RuntimeError(f'Error running ruff, return code {p.returncode}:\n{stderr or stdout}')
    else:
        return stdout




def code_diff(example: CodeExample, after: str, config: ExamplesConfig) -> str:
    def replace_at_line(match: re.Match) -> str:
        offset = re.sub(r'\d+', lambda m: str(int(m.group(0)) + example.start_line), match.group(2))
        return f'{match.group(1)}{offset}{match.group(3)}'

    return re.sub(r'^(@@\s*)(.*)(\s*@@)$', replace_at_line, diff, flags=re.M)


def sub_space(text: str, config: ExamplesConfig) -> str:
    if config.white_space_dot:
        return text.replace(' ', '·')
    else:
        return text
