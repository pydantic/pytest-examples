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
