```py
from dataclasses import dataclass


@dataclass
class User:
    foobar: int

    def __post_init__(self):
        print(self.foobar)


User(foobar=123)
```
################### OUTPUT ###################
```py
from dataclasses import dataclass


@dataclass
class User:
    foobar: int

    def __post_init__(self):
        print(self.foobar)
        #> 123


User(foobar=123)
```
################### TEST #####################
```py
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest


@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_examples(example: CodeExample, eval_example: EvalExample):
    eval_example.set_config(quotes='double')
    if eval_example.update_examples:
        eval_example.format(example)
        eval_example.run_print_update(example)
```
