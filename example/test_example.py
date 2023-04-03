import pytest

from pytest_examples import CodeExample, EvalExample, find_examples


@pytest.mark.xfail(reason='This is an expected failure due to errors in the code', strict=True)
@pytest.mark.parametrize('example', find_examples('example/error.md'), ids=str)
def test_will_error(example: CodeExample, eval_example: EvalExample):
    eval_example.lint(example)
    eval_example.run(example)


@pytest.mark.parametrize('example', find_examples('example/README.md'), ids=str)
def test_insert_print(example: CodeExample, eval_example: EvalExample):
    eval_example.set_config(line_length=50)
    if eval_example.update_examples:
        eval_example.format(example)
        eval_example.run_print_update(example)
    else:
        eval_example.lint(example)
        eval_example.run_print_check(example)


@pytest.mark.parametrize('example', find_examples('example/test_example.py'), ids=str)
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


@pytest.mark.parametrize('example', find_examples('example/test_example.py'), ids=str)
def test_python_self_change_docstyle(example: CodeExample, eval_example: EvalExample):
    """Test this code (no line break at beginning of docstring).
    ```py
    print('this is introspection!')
    #> this is introspection!
    ```
    """
    eval_example.lint(example)
    eval_example.run_print_check(example)
