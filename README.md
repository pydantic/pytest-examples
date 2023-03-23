# pytest-examples

[![CI](https://github.com/pydantic/pytest-examples/workflows/CI/badge.svg?event=push)](https://github.com/pydantic/pytest-examples/actions?query=event%3Apush+branch%3Amain+workflow%3ACI)
[![pypi](https://img.shields.io/pypi/v/pytest-examples.svg)](https://pypi.python.org/pypi/pytest-examples)
[![versions](https://img.shields.io/pypi/pyversions/pytest-examples.svg)](https://github.com/pydantic/pytest-examples)
[![license](https://img.shields.io/github/license/pydantic/pytest-examples.svg)](https://github.com/pydantic/pytest-examples/blob/main/LICENSE)

Pytest plugin for testing Python code examples in docstrings and markdown files.

`pytest-examples` can:
* lint code examples using `ruff` and `black`
* run code examples
* run code examples and check print statements are inlined correctly in the code

It can also update code examples in place to format them and insert or update print statements.

## Installation

```bash
pip install -U pytest-examples
```

## Usage

### Basic usage

Here's an example basic usage - lint then run examples in the `foo_dir` directory and the `bar_file.py` file.

```py
import pytest
from pytest_examples import find_examples, CodeExample, EvalExample


@pytest.mark.parametrize('example', find_examples('foo_dir', 'bar_file.py'), ids=str)
def test_docstrings(example: CodeExample, eval_example: EvalExample):
    eval_example.lint(example)
    eval_example.run(example)
```

### Check print statements

`pytest-examples` can also check print statements are inserted correctly.

There's the expected format of prints statemints in docstrings:

```py
def add_two_things(a, b):
    """
    ```py
    from my_lib import add_two_things

    print(add_two_things(1, 2))
    #> 3
    ```
    """
    return a + b
```

And here's an example of a markdown file, again documenting `add_two_things`:

````markdown
# How `add_two_things` works

```py
from my_lib import add_two_things

print(add_two_things(1, 2))
#> 3
```
````

`pytest-examples` can then run the code and check the print statements are correct:

```py
import pytest
from pytest_examples import find_examples, CodeExample, EvalExample


@pytest.mark.parametrize('example', find_examples('foo_dir'), ids=str)
def test_docstrings(example: CodeExample, eval_example: EvalExample):
    eval_example.run_print_check(example)
```

### Updating files

As well as checking linting and print statements, are correct, we can also update files.

This requires the `--update-examples` flags **AND** use of the `format()` and `run_print_update()` methods.

Here's a full example of a unit test that checks code when called normally, but can update it
when the flag is set:

```py
import pytest
from pytest_examples import find_examples, CodeExample, EvalExample


@pytest.mark.parametrize('example', find_examples('README.md'), ids=str)
def test_readme(example: CodeExample, eval_example: EvalExample):
    if eval_example.update_examples:
        eval_example.format(example)
        eval_example.run_print_update(example)
    else:
        eval_example.lint(example)
        eval_example.run_print_check(example)
```
