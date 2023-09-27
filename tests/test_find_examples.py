import pytest

from pytest_examples import CodeExample, find_examples


def test_find_md_example(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        # language=Markdown
        my_file="""
# My file

```py
a = 1
```

``` py
b = 2
```

```{.py .test="skip"}
c = 3
```

``` {.py}
d = 4
```
        """,
    )
    pytester.makepyfile(
        # language=Python
        """
from pathlib import Path

from pytest_examples import find_examples
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_examples_str(example):
    assert example.indent == 0
    assert example.end_line == example.start_line + 2

@pytest.mark.parametrize('example', find_examples(Path('.')), ids=str)
def test_find_examples_path(example):
    assert example.indent == 0
    assert example.end_line == example.start_line + 2
        """
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    output = '\n'.join(result.outlines)
    result.assert_outcomes(passed=8)

    assert 'test_find_examples_str[my_file.md:3-5] PASSED' in output
    assert 'test_find_examples_str[my_file.md:7-9] PASSED' in output
    assert 'test_find_examples_str[my_file.md:11-13] PASSED' in output
    assert 'test_find_examples_str[my_file.md:15-17] PASSED' in output
    assert 'test_find_examples_path[my_file.md:3-5] PASSED' in output
    assert 'test_find_examples_path[my_file.md:7-9] PASSED' in output
    assert 'test_find_examples_path[my_file.md:11-13] PASSED' in output
    assert 'test_find_examples_path[my_file.md:15-17] PASSED' in output


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

def func_c():
    """Does cool things.
    ```py
    g = 7
    h = 8
    assert g + h == 15
    ```
    """
        ''',
    )
    pytester.makepyfile(
        # language=Python
        """
from pytest_examples import find_examples
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_examples(example):
    assert example.indent == 4
        """
    )

    result = pytester.runpytest('-p', 'no:pretty', '-vs')
    result.assert_outcomes(passed=4)

    output = '\n'.join(result.outlines)
    assert 'test_find_examples[my_file.py:3-7] PASSED' in output
    assert 'test_find_examples[my_file.py:14-18] PASSED' in output
    assert 'test_find_examples[my_file.py:20-24] PASSED' in output
    assert 'test_find_examples[my_file.py:30-34] PASSED' in output


def test_find_py_example_with_module_docstring(pytester: pytest.Pytester):
    pytester.makefile(
        '.py',
        # language=Python
        my_file='''
"""Module docstring."""
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

def func_c():
    """Does cool things.
    ```py
    g = 7
    h = 8
    assert g + h == 15
    ```
    """
        ''',
    )
    pytester.makepyfile(
        # language=Python
        """
from pytest_examples import find_examples
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_examples(example):
    assert example.indent == 4
        """
    )

    result = pytester.runpytest('-p', 'no:pretty', '-vs')
    result.assert_outcomes(passed=4)

    output = '\n'.join(result.outlines)
    assert 'test_find_examples[my_file.py:4-8] PASSED' in output
    assert 'test_find_examples[my_file.py:15-19] PASSED' in output
    assert 'test_find_examples[my_file.py:21-25] PASSED' in output
    assert 'test_find_examples[my_file.py:31-35] PASSED' in output


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

@pytest.mark.parametrize('example', find_examples('my_file.md'), ids=str)
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

@pytest.mark.parametrize('example', find_examples('missing.md'), ids=str)
def test_find_examples(example):
    pass
        """
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v', '-s')
    result.assert_outcomes(errors=1)

    assert "Not a file or directory: 'missing.md'" in '\n'.join(result.outlines)


def test_find_index_markdown(tmp_path):
    # language=Markdown
    code = """
foobar

```py title="a.py"
a = 1
b = 2
assert a + b == 3
```
"""
    (tmp_path / 'a.md').write_text(code)
    examples = list(find_examples(str(tmp_path)))
    assert len(examples) == 1
    example: CodeExample = examples[0]
    assert code[example.start_index : example.end_index] == 'a = 1\nb = 2\nassert a + b == 3\n'
    assert example.source == 'a = 1\nb = 2\nassert a + b == 3\n'


def test_find_index_python(tmp_path):
    # language=Python
    code = '''
def foo():
    """Single line docstring"""
    pass


def func_a():
    """
    prefix.
    ```py
    a = 1
    b = 2
    assert a + b == 3
    ```
    """
    pass
'''
    (tmp_path / 'a.py').write_text(code)
    examples = list(find_examples(str(tmp_path)))
    assert len(examples) == 1
    example: CodeExample = examples[0]
    assert code[example.start_index : example.end_index] == '    a = 1\n    b = 2\n    assert a + b == 3\n'
    assert example.source == 'a = 1\nb = 2\nassert a + b == 3\n'


@pytest.mark.parametrize(
    'prefix,prefix_settings',
    [
        ('py test="skip"', {'test': 'skip'}),
        ('py test="skip" foo="B ar"', {'test': 'skip', 'foo': 'B ar'}),
        ("py test='require-3.8'", {'test': 'require-3.8'}),
    ],
)
def test_prefix_settings(prefix, prefix_settings):
    ex = CodeExample.create('foobar', prefix=prefix)
    assert ex.prefix_settings() == prefix_settings


@pytest.mark.parametrize(
    'prefix,prefix_tags',
    [
        ('{.py .foobar}', {'foobar'}),
        ("{.py 'foo bar'", {'foo bar'}),
        ('py mytag', {'mytag'}),
        ('py test="skip" foo="B ar"', {'test=skip', 'foo=B ar'}),
    ],
)
def test_prefix_tags(prefix, prefix_tags):
    ex = CodeExample.create('foobar', prefix=prefix)
    assert ex.prefix_tags() == prefix_tags
