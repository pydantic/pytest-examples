import pytest

from pytest_examples import CodeExample, EvalExample, find_examples


@pytest.mark.parametrize('example', find_examples('example/error.md'))
def test_will_error(example: CodeExample, eval_example: EvalExample):
    eval_example.lint(example)
    eval_example.run(example)


@pytest.mark.parametrize('example', find_examples('example/README.md'))
def test_mock_print(example: CodeExample, eval_example: EvalExample):
    eval_example.lint(example)
    eval_example.run(example, insert_print_statements=True)
