def foobar():
    """
    ```py
    print({i: 'x' * (5 * i) for i in range(3)})
    ```
    """
    pass
################### OUTPUT ###################
def foobar():
    """
    ```py
    print(
        {
            i: 'x' * (5 * i)
            for i in range(3)
        }
    )
    '''
    {
        0: '',
        1: 'xxxxx',
        2: 'xxxxxxxxxx',
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
