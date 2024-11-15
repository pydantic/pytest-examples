from __future__ import annotations as _annotations

import pytest
from _pytest.outcomes import Failed

from pytest_examples import CodeExample
from pytest_examples.run_code import find_print_location

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
    pytest.param(
        """\
try:
    raise ValueError('boom')
except ValueError as e:
    print(e)
    #> boom
""",
        4,
        (4, 4),
        id='try-except',
    ),
    pytest.param(
        """\
a.b.c(1, 2, 3)
print(4)
""",
        2,
        (2, 0),
        id='call-attribute',
    ),
    pytest.param(
        """\
@dataclass
class User:
    foobar: int

    def __post_init__(self):
        print(self.foobar)
        #> 123
""",
        6,
        (6, 8),
        id='class-method',
    ),
    pytest.param(
        """\
async with foobar():
    print(
        1
    )
""",
        2,
        (4, 4),
        id='async-function',
    ),
]


@pytest.mark.parametrize('python_code,print_line,expected_last_loc', print_last_lines)
def test_find_end_of_print(python_code: str, print_line: int, expected_last_loc: tuple[int, int]):
    last_loc = find_print_location(CodeExample.create(python_code), print_line)
    assert last_loc == expected_last_loc


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
    0: 'i value is 0',
    1: 'i value is 1',
    2: 'i value is 2',
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
    print(['x' * i * 8 for i in range(3)])
    """
    [
        '',
        'xxxxxxxx',
        'xxxxxxxxxxxxxxxx',
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
    'abcdefghij',
    'abcdefghijk',
    'abcdefghijkl',
    'abcdefghijklm',
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
    pytest.param(
        # language=Python
        '''\
if True:
    if True:
        if True:
            print([1, 2, 3, 4])
            #> [1, 2, 3, 4]
            print([1, 2, 3, 4, 5])
            """
            [1, 2, 3, 4, 5]
            """
            print([1_000_000, 2_000_000, 3_000_000])
            """
            [
                1000000,
                2000000,
                3000000,
            ]
            """
''',
        id='big-indent',
    ),
    pytest.param(
        '''\
print('this is not\\npython code')
"""
this is not
python code
"""
''',
        id='not-python-code',
    ),
    pytest.param(
        """\
print(ValueError('this is not python code'))
#> this is not python code
""",
        id='non-python-repr',
    ),
    pytest.param(
        '''\
print(ValueError('this is not\\npython code'))
"""
this is not
python code
"""
''',
        id='non-python-repr',
    ),
    pytest.param(
        """\
try:
    raise ValueError('boom')
except ValueError as e:
    print(e)
    #> boom
""",
        id='print-in-except',
    ),
    pytest.param(
        """\
print({1, 3, 2, 4})
#> {1, 2, 3, 4}
""",
        id='set-order',
    ),
    pytest.param(
        '''\
class Foo:
    pass

print(Foo())
"""
<__main__.Foo object at 0x0123456789ab>
"""
''',
        id='hex_id',
    ),
    pytest.param(
        """\
for i in range(3):
    print(i)
    #> 0
    #> 1
    #> 2
""",
        id='look',
    ),
    pytest.param(
        """print('foobar ')\n#> foobar \n""",
        id='trailing-spaces',
    ),
]


@pytest.mark.parametrize('python_code', unchanged_code)
def test_insert_print_check_unchanged(tmp_path, eval_example, python_code: str):
    # note this file is no written here as it's not required
    md_file = tmp_path / 'test.md'
    example = CodeExample.create(python_code, path=md_file)
    eval_example.set_config(line_length=30)
    eval_example.run_print_check(example)


def test_insert_print_check_change(tmp_path, eval_example):
    # language=Python
    python_code = 'print(1, 2, [3, 4, 5], "hello")\n'

    # note this file is no written here as it's not required
    md_file = tmp_path / 'test.md'
    example = CodeExample.create(python_code, path=md_file, start_line=3)

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


def test_run_main(tmp_path, eval_example):
    # note this file is no written here as it's not required
    md_file = tmp_path / 'test.md'
    python_code = """
def main():
    1 / 0
"""
    example = CodeExample.create(python_code, path=md_file)
    eval_example.set_config(line_length=30)
    eval_example.run_print_check(example)

    with pytest.raises(ZeroDivisionError):
        eval_example.run_print_check(example, call='main')


def test_run_main_print(tmp_path, eval_example):
    # note this file is no written here as it's not required
    md_file = tmp_path / 'test.md'
    python_code = """
main_called = False

def main():
    global main_called
    main_called = True
    print(1, 2, 3)
    #> 1 2 3
"""
    example = CodeExample.create(python_code, path=md_file)
    eval_example.set_config(line_length=30)

    module_dict = eval_example.run_print_check(example, call='main')
    assert module_dict['main_called']


def test_run_main_print_async(tmp_path, eval_example):
    # note this file is no written here as it's not required
    md_file = tmp_path / 'test.md'
    python_code = """
main_called = False

async def main():
    global main_called
    main_called = True
    print(1, 2, 3)
    #> 1 2 3
"""
    example = CodeExample.create(python_code, path=md_file)
    eval_example.set_config(line_length=30)

    module_dict = eval_example.run_print_check(example, call='main')
    assert module_dict['main_called']
