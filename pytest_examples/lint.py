from __future__ import annotations as _annotations

import re
from subprocess import PIPE, Popen
from textwrap import indent
from typing import TYPE_CHECKING

from black import format_str as black_format_str
from black.output import diff as black_diff
from ruff.__main__ import find_ruff_bin

from .config import ExamplesConfig

if TYPE_CHECKING:
    from .find_examples import CodeExample

__all__ = 'ruff_check', 'ruff_format', 'black_check', 'black_format', 'code_diff', 'FormatError'


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


def black_format(source: str, config: ExamplesConfig, *, remove_double_blank: bool = False) -> str:
    # hack to avoid black complaining about our print output format
    before_black = re.sub(r'^( *#)> ', r'\1 > ', source, flags=re.M)
    after_black = black_format_str(before_black, mode=config.black_mode())
    # then revert it back
    after_black = re.sub(r'^( *#) > ', r'\1> ', after_black, flags=re.M)
    if remove_double_blank:
        after_black = re.sub(r'\n{3}', '\n\n', after_black)
    return after_black


def black_check(example: CodeExample, config: ExamplesConfig) -> None:
    after_black = black_format(example.source, config, remove_double_blank=example.in_py_file())
    if example.source != after_black:
        diff = code_diff(example, after_black, config)
        raise FormatError(f'black failed:\n{indent(diff, "  ")}')


def code_diff(example: CodeExample, after: str, config: ExamplesConfig) -> str:
    diff = black_diff(sub_space(example.source, config), sub_space(after, config), 'before', 'after')

    def replace_at_line(match: re.Match) -> str:
        offset = re.sub(r'\d+', lambda m: str(int(m.group(0)) + example.start_line), match.group(2))
        return f'{match.group(1)}{offset}{match.group(3)}'

    return re.sub(r'^(@@\s*)(.*)(\s*@@)$', replace_at_line, diff, flags=re.M)


def sub_space(text: str, config: ExamplesConfig) -> str:
    if config.white_space_dot:
        return text.replace(' ', '·')
    else:
        return text
