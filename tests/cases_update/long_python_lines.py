def foobar():
    """
    ```py
    print({very_long_variable_name: 'x' * (25 * very_long_variable_name) for very_long_variable_name in range(3)})
    ```
    """
    pass
################### OUTPUT ###################
def foobar():
    """
    ```py
    print({
        very_long_variable_name: 'x' * (25 * very_long_variable_name)
        for very_long_variable_name in range(3)
    })
    '''
    {
        0: '',
        1: 'xxxxxxxxxxxxxxxxxxxxxxxxx',
        2: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    }
    '''
    ```
    """
    pass
################### TEST #####################
import pytest
from pytest_examples import CodeExample, EvalExample, find_examples


@pytest.mark.parametrize('example', find_examples('.'), ids=str)
def test_find_examples(example: CodeExample, eval_example: EvalExample):
    eval_example.set_config(line_length=30)
    if eval_example.update_examples:
        eval_example.format(example)
        eval_example.run_print_update(example)
