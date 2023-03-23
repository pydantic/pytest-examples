from __future__ import annotations as _annotations

from pathlib import Path

import pytest
from _pytest.outcomes import Failed

from pytest_examples import CodeExample
from pytest_examples.insert_print import find_print_location

# separate list to hopefully make it easier to read
print_last_lines = [
    pytest.param(
        """\
print(1, 2, [3, 4, 5], "hello")
""",
        1,
        (1, 0),
        id='simple case',
    ),
    pytest.param(
        """\
print(1, 2, [3, 4, 5], "hello")
x = 123
""",
        1,
        (1, 0),
        id='content after print output',
    ),
    pytest.param(
        """\
if True:
    print((1, 2, 3))
""",
        2,
        (2, 4),
        id='single-line-indent',
    ),
    pytest.param(
        """\
def foobar():
    a = 4
    if True:
        print(
            1,
            2,
            3
        )
x=4
foobar()
""",
        4,
        (8, 8),
        id='print-over-lines',
    ),
    pytest.param(
        """\
import string
print(
    [
        string.ascii_letters[
            : i + 10
        ]
        for i in range(4)
    ]
)
""",
        2,
        (9, 0),
        id='multiline-comprehension',
    ),
    pytest.param(
        """\
print(1, 2, 3
    )
""",
        1,
        (1, 0),
        id='ill-formed-print-1',
    ),
    pytest.param(
        """\
print(
    1, 2, 3)
""",
        1,
        (3, 0),
        id='ill-formed-print-2',
    ),
]


@pytest.mark.parametrize('python_code,print_line,expected_last_loc', print_last_lines)
def test_find_end_of_print(python_code: str, print_line: int, expected_last_loc: tuple[int, int]):
    last_loc = find_print_location(CodeExample.create(python_code), print_line)
    assert last_loc == expected_last_loc


def fake_example(path: Path, code: str, start_line: int = 0) -> CodeExample:
    return CodeExample(
        path, start_line=start_line, end_index=0, start_index=0, end_line=0, prefix='', source=code, indent=0
    )


# separate list to hopefully make it easier to read
unchanged_code: list = [
    pytest.param(
        # language=Python
        """\
print(1, 2, [3, 4, 5], "hello")
#> 1 2 [3, 4, 5] hello
""",
        id='simple case',
    ),
    pytest.param(
        # language=Python
        """\
print(1, 2, [3, 4, 5], "hello")
#> 1 2 [3, 4, 5] hello
x = 123
""",
        id='content after print output',
    ),
    pytest.param(
        # language=Python
        '''\
print({i: f'i value is {i}' for i in range(3)})
"""
{
    0: "i value is 0",
    1: "i value is 1",
    2: "i value is 2",
}
"""
''',
        id='multiline',
    ),
    pytest.param(
        # language=Python
        """\
if True:
    print((1, 2, 3))
    #> (1, 2, 3)
""",
        id='single-line-indent',
    ),
    pytest.param(
        # language=Python
        '''\
if True:
    print(['x' * i * 5 for i in range(3)])
    """
    [
        "",
        "xxxxx",
        "xxxxxxxxxx",
    ]
    """
''',
        id='multi-line-indent',
    ),
    pytest.param(
        # language=Python
        """\
def foobar():
    a = 4
    if True:
        print(
            1,
            2,
            3
        )
        #> 1 2 3
x=4
foobar()
""",
        id='print-over-lines',
    ),
    pytest.param(
        # language=Python
        '''\
import string
print(
    [
        string.ascii_letters[
            : i + 10
        ]
        for i in range(4)
    ]
)
"""
[
    "abcdefghij",
    "abcdefghijk",
    "abcdefghijkl",
    "abcdefghijklm",
]
"""
''',
        id='multiline-comprehension',
    ),
    pytest.param(
        # language=Python
        """\
print(1, 2, 3
#> 1 2 3
    )
""",
        id='ill-formed-print-1',
    ),
    pytest.param(
        # language=Python
        """\
print(
    1, 2, 3)
#> 1 2 3
#> 1 2 3
""",
        id='ill-formed-print-2',
    ),
]


@pytest.mark.parametrize('python_code', unchanged_code)
def test_insert_print_check_unchanged(tmp_path, eval_example, python_code: str):
    # note this file is no written here as it's not required
    md_file = tmp_path / 'test.md'
    example = fake_example(md_file, python_code)
    eval_example.run_print_check(example, line_length=30)


def test_insert_print_check_change(tmp_path, eval_example):
    # language=Python
    python_code = 'print(1, 2, [3, 4, 5], "hello")\n'

    # note this file is no written here as it's not required
    md_file = tmp_path / 'test.md'
    example = fake_example(md_file, python_code, start_line=3)

    with pytest.raises(Failed) as exc_info:
        eval_example.run_print_check(example)
    assert str(exc_info.value) == (
        'Print output changed code:\n'
        '  --- before\n'
        '  +++ after\n'
        '  @@ -4 +4,5 @@\n'
        '   print(1, 2, [3, 4, 5], "hello")\n'
        '  +#> 1 2 [3, 4, 5] hello\n'
    )
