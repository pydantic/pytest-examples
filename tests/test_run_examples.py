import pytest

# language=Python
python_code = """
from pytest_examples import find_examples, CodeExample, ExampleRunner
import pytest

@pytest.mark.parametrize('example', find_examples('.'))
def test_find_run_examples(example: CodeExample, run_example: ExampleRunner):
    run_example.run(example)
"""


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
    pytester.makepyfile(python_code)

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(passed=1, failed=1)

    assert 'my_file_9_13.py:12: AssertionError' in '\n'.join(result.outlines)


def test_run_example_skip(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        # language=Markdown
        my_file="""
# My file

```py test="skip"
a = 1
b = 2
assert a + b == 3
```
        """,
    )
    pytester.makepyfile(python_code)

    result = pytester.runpytest('-p', 'no:pretty')
    result.assert_outcomes(skipped=1)


def test_ruff_ok(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        my_file='```py\nimport sys\nprint(sys.platform)\n```',
    )
    # language=Python
    pytester.makepyfile(
        """
from pytest_examples import find_examples, CodeExample, ExampleRunner
import pytest

@pytest.mark.parametrize('example', find_examples('.'))
def test_find_run_examples(example: CodeExample, run_example: ExampleRunner):
    run_example.ruff(example)
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
from pytest_examples import find_examples, CodeExample, ExampleRunner
import pytest

@pytest.mark.parametrize('example', find_examples('.'))
def test_find_run_examples(example: CodeExample, run_example: ExampleRunner):
    run_example.ruff(example)
"""
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(failed=1)

    output = '\n'.join(result.outlines)
    assert '<path>/my_file_1_4.py:2:8: F401 [*] `sys` imported but unused' in output
    assert '<path>/my_file_1_4.py:3:7: F821 Undefined name `missing`' in output


def test_black_ok(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        my_file='```py\nx = [1, 2, 3]\n```',
    )
    # language=Python
    pytester.makepyfile(
        """
from pytest_examples import find_examples, CodeExample, ExampleRunner
import pytest

@pytest.mark.parametrize('example', find_examples('.'))
def test_find_run_examples(example: CodeExample, run_example: ExampleRunner):
    run_example.black(example)
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
from pytest_examples import find_examples, CodeExample, ExampleRunner
import pytest

@pytest.mark.parametrize('example', find_examples('.'))
def test_find_run_examples(example: CodeExample, run_example: ExampleRunner):
    run_example.black(example)
"""
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(failed=1)

    e_lines = [line for line in result.outlines if line.startswith('E')]
    assert e_lines == [
        'E       Failed: black failed:',
        'E       --- before',
        'E       +++ after',
        'E       @@ -4 +4 @@',
        'E       -x =[1,2, 3]',
        'E       +x = [1, 2, 3]',
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
from pytest_examples import find_examples, CodeExample, ExampleRunner
import pytest

@pytest.mark.parametrize('example', find_examples('.'))
def test_find_run_examples(example: CodeExample, run_example: ExampleRunner):
    run_example.black(example)
"""
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(failed=1)

    e_lines = [line for line in result.outlines if line.startswith('E')]
    assert e_lines == [
        'E       Failed: black failed:',
        'E       --- before',
        'E       +++ after',
        'E       @@ -4,8 +4 @@',
        'E       -x =[',
        'E       -    1,',
        'E       -    2, ',
        'E       -    3',
        'E       -]',
        'E       +x = [1, 2, 3]',
    ]
