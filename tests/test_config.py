from pathlib import Path
from typing import get_type_hints

import pytest

from pytest_examples import EvalExample
from pytest_examples.config import ConfigKwargs, ExamplesConfig, load_pyproject_config


def test_no_pyproject(tmp_path: Path):
    assert load_pyproject_config(tmp_path) == ExamplesConfig()


def test_pyproject_without_table(tmp_path: Path):
    (tmp_path / 'pyproject.toml').write_text('[tool.ruff]\nline-length = 120\n')

    assert load_pyproject_config(tmp_path) == ExamplesConfig()


def test_table_sets_every_key(tmp_path: Path):
    (tmp_path / 'pyproject.toml').write_text(
        # language=TOML
        """
[tool.pytest-examples]
line-length = 30
quotes = 'single'
magic-trailing-comma = false
target-version = 'py310'
upgrade = true
isort = true
ruff-line-length = 100
ruff-select = ['B']
ruff-ignore = ['D', 'T201']
"""
    )

    assert load_pyproject_config(tmp_path) == ExamplesConfig(
        line_length=30,
        quotes='single',
        magic_trailing_comma=False,
        target_version='py310',
        upgrade=True,
        isort=True,
        ruff_line_length=100,
        ruff_select=['B'],
        ruff_ignore=['D', 'T201'],
    )


@pytest.mark.parametrize(
    'key',
    [
        pytest.param('line_length', id='snake-case'),
        pytest.param('white-space-dot', id='not-a-set-config-argument'),
    ],
)
def test_unknown_key(tmp_path: Path, key: str):
    (tmp_path / 'pyproject.toml').write_text(f'[tool.pytest-examples]\n{key} = 30\n')

    with pytest.raises(pytest.UsageError, match=rf"unknown key '{key}' in \[tool\.pytest-examples\]"):
        load_pyproject_config(tmp_path)


@pytest.mark.parametrize(
    'line',
    [
        pytest.param('line-length = true', id='bool-for-int'),
        pytest.param("line-length = '30'", id='str-for-int'),
        pytest.param("ruff-line-length = '30'", id='str-for-optional-int'),
        pytest.param("ruff-ignore = 'D'", id='str-for-list'),
        pytest.param('ruff-ignore = [1]', id='int-in-list'),
        pytest.param('target-version = 311', id='int-for-target'),
    ],
)
def test_wrong_type(tmp_path: Path, line: str):
    (tmp_path / 'pyproject.toml').write_text(f'[tool.pytest-examples]\n{line}\n')

    with pytest.raises(pytest.UsageError, match=r'in \[tool\.pytest-examples\] must be'):
        load_pyproject_config(tmp_path)


@pytest.mark.parametrize(
    'line',
    [
        pytest.param("quotes = 'bogus'", id='quotes'),
    ],
)
def test_value_not_allowed(tmp_path: Path, line: str):
    (tmp_path / 'pyproject.toml').write_text(f'[tool.pytest-examples]\n{line}\n')

    with pytest.raises(pytest.UsageError, match=r'in \[tool\.pytest-examples\] must be one of: '):
        load_pyproject_config(tmp_path)


def test_target_version_reaches_the_tools(tmp_path: Path):
    (tmp_path / 'pyproject.toml').write_text("[tool.pytest-examples]\ntarget-version = 'py399'\n")

    assert load_pyproject_config(tmp_path).target_version == 'py399'


@pytest.mark.parametrize(
    'content,message',
    [
        pytest.param('tool = 1', r'\[tool\] must be a table, got 1', id='tool-scalar'),
        pytest.param('tool = [1]', r'\[tool\] must be a table, got \[1\]', id='tool-array'),
        pytest.param('[tool]\npytest-examples = 1', r'\[tool\.pytest-examples\] must be a table, got 1', id='child'),
    ],
)
def test_table_is_not_a_table(tmp_path: Path, content: str, message: str):
    (tmp_path / 'pyproject.toml').write_text(f'{content}\n')

    with pytest.raises(pytest.UsageError, match=message):
        load_pyproject_config(tmp_path)


def test_broken_toml_when_pytest_reads_another_file(pytester: pytest.Pytester):
    pytester.makefile('.ini', pytest='[pytest]\n')
    pytester.makefile('.toml', pyproject='[tool.pytest-examples\n')
    pytester.makepyfile('def test_never_runs(): pass')

    result = pytester.runpytest('-p', 'no:pretty')
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(["ERROR: *pyproject.toml: Expected ']' at the end of a table declaration*"])


def test_set_config_starts_from_table(pytester: pytest.Pytester):
    pytester.makepyprojecttoml(
        # language=TOML
        """
[tool.pytest-examples]
line-length = 30
ruff-ignore = ['D']
"""
    )
    # language=Python
    pytester.makepyfile(
        """
from pytest_examples import EvalExample
from pytest_examples.config import ExamplesConfig

def test_table(eval_example: EvalExample):
    assert eval_example.config == ExamplesConfig(line_length=30, ruff_ignore=['D'])
    eval_example.config.ruff_ignore.append('E501')

def test_table_not_mutated_by_previous_test(eval_example: EvalExample):
    assert eval_example.config == ExamplesConfig(line_length=30, ruff_ignore=['D'])

def test_set_config_overrides_only_what_it_is_passed(eval_example: EvalExample):
    eval_example.set_config(quotes='double', line_length=40)
    assert eval_example.config == ExamplesConfig(line_length=40, quotes='double', ruff_ignore=['D'])

    eval_example.set_config(isort=True)
    assert eval_example.config == ExamplesConfig(line_length=30, isort=True, ruff_ignore=['D'])
"""
    )

    result = pytester.runpytest('-p', 'no:pretty')
    result.assert_outcomes(passed=3)


def test_bad_table_stops_the_run(pytester: pytest.Pytester):
    pytester.makepyprojecttoml('[tool.pytest-examples]\nline-lenght = 30\n')
    pytester.makepyfile('def test_never_runs(): pass')

    result = pytester.runpytest('-p', 'no:pretty')
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(["ERROR: *unknown key 'line-lenght' in [[]tool.pytest-examples]*"])


def test_eval_example_without_the_plugin(pytester: pytest.Pytester):
    pytester.makepyprojecttoml('[tool.pytest-examples]\nline-length = 30\n')
    # language=Python
    pytester.makepyfile(
        """
import pytest
from pytest_examples import EvalExample
from pytest_examples.config import ExamplesConfig

@pytest.fixture
def eval_example(tmp_path, request):
    return EvalExample(tmp_path=tmp_path, pytest_request=request)

def test_defaults(eval_example: EvalExample):
    assert eval_example.config == ExamplesConfig()
"""
    )

    result = pytester.runpytest('-p', 'no:pretty', '-p', 'no:examples')
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    'key',
    [
        pytest.param('white_space_dot', id='not-a-set-config-argument'),
        pytest.param('line_lenght', id='misspelled'),
    ],
)
def test_set_config_unknown_argument(eval_example: EvalExample, key: str):
    with pytest.raises(TypeError, match=rf"^EvalExample\.set_config\(\) got an unexpected keyword argument '{key}'$"):
        eval_example.set_config(**{key: True})


def test_config_kwargs_are_the_config_fields():
    # every option but `white_space_dot`, which only changes how diffs are printed
    fields = get_type_hints(ExamplesConfig)
    del fields['white_space_dot']

    assert get_type_hints(ConfigKwargs) == fields
