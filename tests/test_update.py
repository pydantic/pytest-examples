import pytest


def test_update_files(pytester: pytest.Pytester):
    md_file = pytester.makefile(
        '.md',
        # language=Markdown
        my_file="""
# My file

```py
print("this is the first example")
```

```py
async def main():
    print(["first things", "second things", "third things"])
```
        """,
    )

    py_file = pytester.makefile(
        '.py',
        # language=Python
        my_file='''
################################# start of demo code #################################
def func_a():
    """
    Func A docstring.
    ```py
    print(1)
    ```
    """
    pass
################################# end of demo code #################################
            ''',
    )
    pytester.makepyfile(
        # language=Python
        """
################################# start of test code #################################
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_examples(example: CodeExample, eval_example: EvalExample):
    if eval_example.update_examples:
        eval_example.lint(example)
        eval_example.run_print_update(example, call='main')
    else:
        eval_example.lint(example)
        # insert_print_statements='check' would fail here
        eval_example.run(example)
################################# end of test code #################################
        """
    )

    result = pytester.runpytest('-p', 'no:pretty')
    result.assert_outcomes(passed=3)

    result = pytester.runpytest('-p', 'no:pretty', '--update-examples', '--update-examples-disable-summary')
    result.assert_outcomes(passed=3)

    assert md_file.read_text() == (
        """\
# My file

```py
print("this is the first example")
#> this is the first example
```

```py
async def main():
    print(["first things", "second things", "third things"])
    #> ['first things', 'second things', 'third things']
```"""
    )
    assert (
        py_file.read_text()
        == '''\
################################# start of demo code #################################
def func_a():
    """
    Func A docstring.
    ```py
    print(1)
    #> 1
    ```
    """
    pass
################################# end of demo code #################################'''
    )


def test_update_repeat_example(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        # language=Markdown
        my_file="""
# My file

```py
print("this is the first example")
```
        """,
    )

    pytester.makepyfile(
        # language=Python
        """
################################# start of test code #################################
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_a(example: CodeExample, eval_example: EvalExample):
    if eval_example.update_examples:
        eval_example.run_print_update(example)

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_b(example: CodeExample, eval_example: EvalExample):
    if eval_example.update_examples:
        eval_example.run_print_update(example)
################################# end of test code #################################
        """
    )

    result = pytester.runpytest('-p', 'no:pretty', '--update-examples')
    result.assert_outcomes(errors=1, passed=2)
    assert 'RuntimeError: Cannot update the same example in separate tests!' in '\n'.join(result.outlines)


def test_update_repeat_file(pytester: pytest.Pytester):
    pytester.makefile(
        '.md',
        # language=Markdown
        my_file="""
```py
print("example 1")
```

```py
print("example 2")
```
        """,
    )

    pytester.makepyfile(
        # language=Python
        """
################################# start of test code #################################
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_a(example: CodeExample, eval_example: EvalExample):
    if 'example 1' in example.source:
        eval_example.run_print_update(example)

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_b(example: CodeExample, eval_example: EvalExample):
    if 'example 2' in example.source:
        eval_example.run_print_update(example)
################################# end of test code #################################
        """
    )

    result = pytester.runpytest('-p', 'no:pretty', '--update-examples')
    result.assert_outcomes(errors=1, passed=4)
    assert 'RuntimeError: Cannot update the same file in separate groups!' in '\n'.join(result.outlines)
