import pytest


def test_find_md_example(pytester: pytest.Pytester):
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
c = 3
d = 4
assert c + d == 7
```
        """,
    )
    pytester.makepyfile(
        # language=Python
        """
from pytest_examples import find_examples
import pytest

@pytest.mark.parametrize('example', find_examples('.'))
def test_find_examples(example):
    pass
        """
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(passed=2)

    output = '\n'.join(result.outlines)
    assert 'test_find_examples[my_file.md:3-7] PASSED' in output
    assert 'test_find_examples[my_file.md:9-13] PASSED' in output


def test_find_py_example(pytester: pytest.Pytester):
    pytester.makefile(
        '.py',
        # language=Python
        my_file='''
def func_a():
    """
    ```py
    a = 1
    b = 2
    assert a + b == 3
    ```
    """
    pass


def func_b():
    """
    ```py
    c = 3
    d = 4
    assert c + d == 7
    ```

    ```py
    e = 5
    f = 6
    assert e + f == 11
    ```
    """
    pass
        ''',
    )
    pytester.makepyfile(
        # language=Python
        """
from pytest_examples import find_examples
import pytest

@pytest.mark.parametrize('example', find_examples('.'))
def test_find_examples(example):
    pass
        """
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(passed=3)

    output = '\n'.join(result.outlines)
    assert 'test_find_examples[my_file.py:3-7] PASSED' in output
    assert 'test_find_examples[my_file.py:14-18] PASSED' in output
    assert 'test_find_examples[my_file.py:20-24] PASSED' in output


def test_find_file_example(pytester: pytest.Pytester):
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
        """,
    )
    pytester.makepyfile(
        # language=Python
        """
from pytest_examples import find_examples
import pytest

@pytest.mark.parametrize('example', find_examples('my_file.md'))
def test_find_examples(example):
    pass
        """
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v', '-s')
    result.assert_outcomes(passed=1)

    output = '\n'.join(result.outlines)
    assert 'test_find_examples[my_file.md:3-7] PASSED' in output


def test_find_missing(pytester: pytest.Pytester):
    pytester.makepyfile(
        # language=Python
        """
from pytest_examples import find_examples
import pytest

@pytest.mark.parametrize('example', find_examples('missing.md'))
def test_find_examples(example):
    pass
        """
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v', '-s')
    result.assert_outcomes(errors=1)

    assert "Not a file or directory: 'missing.md'" in '\n'.join(result.outlines)
