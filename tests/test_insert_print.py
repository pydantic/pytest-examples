from pathlib import Path

import pytest
from _pytest.outcomes import Failed

from pytest_examples import CodeExample


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
    print(['x' * i * 5 for i in range(3)])
    """
    [
        '',
        'xxxxx',
        'xxxxxxxxxx',
    ]
    """
''',
        id='multi-line-indent',
    ),
]


@pytest.mark.parametrize('python_code', unchanged_code)
def test_insert_print_check_unchanged(tmp_path, eval_example, python_code):
    # note this file is no written here as it's not required
    md_file = tmp_path / 'test.md'
    example = fake_example(md_file, python_code)
    eval_example.run(example, insert_print_statements='check', line_length=30)


def test_insert_print_check_change(tmp_path, eval_example):
    # language=Python
    python_code = 'print(1, 2, [3, 4, 5], "hello")\n'

    # note this file is no written here as it's not required
    md_file = tmp_path / 'test.md'
    example = fake_example(md_file, python_code, start_line=3)

    with pytest.raises(Failed) as exc_info:
        eval_example.run(example, insert_print_statements='check')
    assert str(exc_info.value) == (
        'Print output changed code:\n'
        '  --- before\n'
        '  +++ after\n'
        '  @@ -4 +4,5 @@\n'
        '   print(1, 2, [3, 4, 5], "hello")\n'
        '  +#> 1 2 [3, 4, 5] hello\n'
    )
