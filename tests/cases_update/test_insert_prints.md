# this is an example

```py
import string
print([string.ascii_letters[: i + 10] for i in range(4)])
"""
[
    'abcdefghij',
    'abcdefghijk',
    'abcdefghijkl',
    'abcdefghijklm',
]
"""
```
################### OUTPUT ###################
# this is an example

```py
import string

print([string.ascii_letters[: i + 10] for i in range(4)])
```
################### TEST #####################
```py
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest


@pytest.mark.parametrize('example', find_examples('.'))
def test_find_examples(example: CodeExample, eval_example: EvalExample):
    if eval_example.update_examples:
        eval_example.format(example, line_length=30)
        eval_example.run_print_update(example, line_length=30)
```
