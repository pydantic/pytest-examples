import pytest

from pytest_examples import CodeExample, EvalExample, find_examples


@pytest.mark.xfail(reason='This is an expected failure due to errors in the code')
@pytest.mark.parametrize('example', find_examples('example/error.md'))
def test_will_error(example: CodeExample, eval_example: EvalExample):
    eval_example.lint(example)
    eval_example.run(example)


@pytest.mark.parametrize('example', find_examples('example/README.md'))
def test_insert_print(example: CodeExample, eval_example: EvalExample):
    if eval_example.update_examples:
        eval_example.format_black(example, line_length=30)
        eval_example.run_print_update(example, line_length=30)
    else:
        eval_example.lint(example, line_length=30)
        eval_example.run_print_check(example, line_length=30)


@pytest.mark.parametrize('example', find_examples('example/test_example.py'))
def test_python_self(example: CodeExample, eval_example: EvalExample):
    """
    Test this code.
    ```py
    print('this is introspection!')
    #> this is introspection!
    ```
    """
    eval_example.lint(example)
    eval_example.run_print_check(example)
