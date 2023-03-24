```py
def foobar(x):
    print(f'x={x}')

foobar(1)
foobar(2)
```
################### OUTPUT ###################
```py
def foobar(x):
    print(f'x={x}')
    #> x=1
    #> x=2


foobar(1)
foobar(2)
```
################### TEST #####################
```py
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest


@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_examples(example: CodeExample, eval_example: EvalExample):
    if eval_example.update_examples:
        eval_example.format(example)
        eval_example.run_print_update(example)
```
