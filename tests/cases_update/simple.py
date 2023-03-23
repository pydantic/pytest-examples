def foobar():
    """
    ```py
    print(123)
    ```
    """
    pass

################### OUTPUT ###################
def foobar():
    """
    ```py
    print(123)
    #> 123
    ```
    """
    pass

################### TEST #####################
import pytest
from pytest_examples import CodeExample, EvalExample, find_examples


@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_examples(example: CodeExample, eval_example: EvalExample):
    if eval_example.update_examples:
        eval_example.lint(example)
        eval_example.run_print_update(example)
