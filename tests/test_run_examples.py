import re
import sys

import pytest

from pytest_examples import CodeExample

# language=Python
python_code = """
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_run_examples(example: CodeExample, eval_example: EvalExample):
    eval_example.run(example)
"""


@pytest.mark.skipif(sys.version_info < (3, 8), reason='traceback different on 3.7')
def test_run_example_ok_fail(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        # language=Markdown
        my_file="""
# My file

```py
a = 1
b = 2
assert a + b == 3
```

```py
a = 1
b = 2
assert a + b == 4
```
        """,
    )
    # language=Python
    pytester.makepyfile(
        """
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_run_examples(example: CodeExample, eval_example: EvalExample):
    eval_example.run(example, rewrite_assertions=False)
"""
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(passed=1, failed=1)

    assert result.outlines[-11].startswith('_ _ _ _ ')
    assert result.outlines[-10:-3] == [
        '',
        '    a = 1',
        '    b = 2',
        '>   assert a + b == 4',
        'E   AssertionError',
        '',
        'my_file.md:12: AssertionError',
    ]


def test_ruff_ok(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        my_file='```py\nimport sys\nprint(sys.platform)\n```',
    )
    # language=Python
    pytester.makepyfile(
        """
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_run_examples(example: CodeExample, eval_example: EvalExample):
    eval_example.lint_ruff(example)
"""
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(passed=1)


def test_ruff_error(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        my_file='```py\nimport sys\nprint(missing)\n```',
    )
    # language=Python
    pytester.makepyfile(
        """
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_run_examples(example: CodeExample, eval_example: EvalExample):
    eval_example.lint_ruff(example)
"""
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(failed=1)

    output = '\n'.join(result.outlines)
    output = re.sub(r'(=|_){3,}', r'\1\1\1', output)
    for phrase in [
        '=== FAILURES ===\n',
        '___ test_find_run_examples[my_file.md:1-4] ___\n',
        'ruff failed:\n',
        '  my_file.md:2:8: F401 [*] `sys` imported but unused\n',
        '  my_file.md:3:7: F821 Undefined name `missing`\n',
        '  Found 2 errors.\n',
        '  [*] 1 fixable with the `--fix` option.\n',
        '=== short test summary info ===\n',
    ]:
        assert phrase in output


def test_black_ok(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        my_file='```py\nx = [1, 2, 3]\n```',
    )
    # language=Python
    pytester.makepyfile(
        """
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_run_examples(example: CodeExample, eval_example: EvalExample):
    eval_example.lint_black(example)
"""
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(passed=1)


def test_black_error(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        my_file='line 1\nline 2\n```py\nx =[1,2, 3]\n```',
    )
    # language=Python
    pytester.makepyfile(
        """
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_run_examples(example: CodeExample, eval_example: EvalExample):
    eval_example.lint_black(example)
"""
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(failed=1)

    failures_start = next(index for index, line in enumerate(result.outlines) if 'FAILURES' in line)
    failures_end = next(index for index, line in enumerate(result.outlines) if 'short test summary' in line)
    e_lines = [line.strip() for line in result.outlines[failures_start + 2 : failures_end]]
    assert e_lines == [
        'black failed:',
        '--- before',
        '+++ after',
        '@@ -4 +4 @@',
        '-x =[1,2, 3]',
        '+x = [1, 2, 3]',
    ]


def test_black_error_dot_space(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        my_file='line 1\nline 2\n```py\nx =[1,2, 3]\n```',
    )
    # language=Python
    pytester.makepyfile(
        """
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_run_examples(example: CodeExample, eval_example: EvalExample):
    eval_example.config.white_space_dot = True
    eval_example.lint_black(example)
"""
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(failed=1)

    failures_start = next(index for index, line in enumerate(result.outlines) if 'FAILURES' in line)
    failures_end = next(index for index, line in enumerate(result.outlines) if 'short test summary' in line)
    e_lines = [line.strip() for line in result.outlines[failures_start + 2 : failures_end]]
    assert e_lines == [
        'black failed:',
        '--- before',
        '+++ after',
        '@@ -4 +4 @@',
        '-x·=[1,2,·3]',
        '+x·=·[1,·2,·3]',
    ]


def test_black_error_multiline(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        my_file="""
line 1
line 2
```py
x =[
    1,
    2,
    3
]
```""",
    )
    # language=Python
    pytester.makepyfile(
        """
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_run_examples(example: CodeExample, eval_example: EvalExample):
    eval_example.lint_black(example)
"""
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(failed=1)

    failures_start = next(index for index, line in enumerate(result.outlines) if 'FAILURES' in line)
    failures_end = next(index for index, line in enumerate(result.outlines) if 'short test summary' in line)
    e_lines = [line.strip() for line in result.outlines[failures_start + 2 : failures_end]]
    assert e_lines == [
        'black failed:',
        '--- before',
        '+++ after',
        '@@ -4,8 +4 @@',
        '-x =[',
        '-    1,',
        '-    2,',
        '-    3',
        '-]',
        '+x = [1, 2, 3]',
    ]


@pytest.mark.skipif(sys.version_info < (3, 8), reason='traceback different on 3.7')
def test_run_directly(tmp_path, eval_example):
    # language=Python
    python_code = """\
x = 4

def div(y):
    try:
        return x / y
    finally:
        str(y)

div(2)
div(0)"""
    # language=Markdown
    markdown = f"""\
# this is markdown

```py
{python_code}
```
"""
    md_file = tmp_path / 'test.md'
    md_file.write_text(markdown)
    example = CodeExample.create(python_code, path=md_file, start_line=3, end_line=6)
    with pytest.raises(ZeroDivisionError) as exc_info:
        eval_example.run(example)

    # debug(exc_info.traceback)
    assert exc_info.traceback[-1].frame.code.path == md_file
    assert exc_info.traceback[-1].lineno == 7

    assert exc_info.traceback[-2].frame.code.path == md_file
    assert exc_info.traceback[-2].lineno == 12


def test_print_sub(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        # language=Markdown
        my_file='''
# My file

```py
print('hello')
#> hello
print('1/2/3')
#> X/X/X
print({f'{i} key': i for i in range(8)})
"""
{
    'X key': X,
    'X key': X,
    'X key': X,
    'X key': X,
    'X key': X,
    'X key': X,
    'X key': X,
    'X key': X,
}
"""
```
        ''',
    )
    # language=Python
    pytester.makepyfile(
        r"""
import re
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest

def print_sub(print_statement):
    return re.sub(r'[0-9]+', 'X', print_statement)

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_run_examples(example: CodeExample, eval_example: EvalExample):
    eval_example.print_callback = print_sub
    eval_example.run_print_check(example, rewrite_assertions=False)
"""
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(passed=1)


def test_print_check_spaces(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        # language=Markdown
        my_file="""
# My file

```py
# note trailing space

print('hello ')
#> hello
```""",
    )
    # language=Python
    pytester.makepyfile(
        r"""
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_run_examples(example: CodeExample, eval_example: EvalExample):
    eval_example.run_print_check(example, rewrite_assertions=False)
"""
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(passed=1)
