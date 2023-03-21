import pytest

from pytest_examples import CodeExample, EvalExample, find_examples


@pytest.mark.parametrize('example', find_examples('example/README.md'))
def test_docstrings(example: CodeExample, run_example: EvalExample):
    run_example.lint(example)
    run_example.run(example)
