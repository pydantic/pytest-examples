import pytest


def test_run_example_ok(pytester: pytest.Pytester):
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
    pytester.makepyfile(
        # language=Python
        """
from pytest_examples import find_examples, CodeExample, ExampleRunner
import pytest

@pytest.mark.parametrize('example', find_examples('.'))
def test_find_examples(example: CodeExample, run_example: ExampleRunner):
    run_example.run(example)
        """
    )

    result = pytester.runpytest('-p', 'no:pretty', '-v')
    result.assert_outcomes(passed=1, failed=1)

    output = '\n'.join(result.outlines)
    assert 'my_file_9_13.py:12: AssertionError' in output
