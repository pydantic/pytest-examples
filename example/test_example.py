import pytest

from pytest_examples import CodeExample, EvalExample, find_examples


@pytest.mark.parametrize('example', find_examples('example/README.md'))
def test_docstrings(example: CodeExample, eval_example: EvalExample):
    eval_example.lint(example)
    eval_example.run(example)
