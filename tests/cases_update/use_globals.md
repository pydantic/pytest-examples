```py
x = 1
y = 2
```
```py
print(x, y)
```
################### OUTPUT ###################
```py
x = 1
y = 2
```
```py
print(x, y)
#> 1 2
```
################### TEST #####################
```py
test_count = 2
from pytest_examples import find_examples, CodeExample, EvalExample
import pytest

examples_globals = {}

@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_examples(example: CodeExample, eval_example: EvalExample):
    if eval_example.update_examples:
        m_dict = eval_example.run_print_update(example, module_globals=examples_globals)
        examples_globals.update(m_dict)
```
