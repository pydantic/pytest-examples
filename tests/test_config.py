from dataclasses import dataclass
from typing import Any

import pytest

from pytest_examples.config import ExamplesConfig


@dataclass
class TargetVersionTestCase:
    id: str
    target_version: Any


@pytest.mark.parametrize(
    'case',
    [
        # Valid target versions
        TargetVersionTestCase('py37', 'py37'),
        TargetVersionTestCase('py38', 'py38'),
        TargetVersionTestCase('py39', 'py39'),
        TargetVersionTestCase('py310', 'py310'),
        TargetVersionTestCase('py311', 'py311'),
        TargetVersionTestCase('py312', 'py312'),
        TargetVersionTestCase('py313', 'py313'),
        TargetVersionTestCase('py314', 'py314'),
        TargetVersionTestCase('py3100', 'py3100'),
    ],
    ids=lambda case: case.id,
)
def test_examples_config_valid_target_version(case: TargetVersionTestCase):
    """Test that ExamplesConfig validates target_version correctly during initialization."""
    config = ExamplesConfig(target_version=case.target_version)
    assert config.target_version == case.target_version


@pytest.mark.parametrize(
    'case',
    [
        TargetVersionTestCase('missing_py', '37'),
        TargetVersionTestCase('python_word', 'python37'),
        TargetVersionTestCase('single_digit', 'py3'),
        TargetVersionTestCase('dots', 'py3.7'),
        TargetVersionTestCase('spaces', 'py 37'),
        TargetVersionTestCase('uppercase', 'PY37'),
        TargetVersionTestCase('mixed_case', 'Py37'),
        TargetVersionTestCase('letters_before_digits', 'py3a7'),
        TargetVersionTestCase('hyphen', 'py-37'),
        TargetVersionTestCase('underscore', 'py_37'),
        TargetVersionTestCase('suffix', 'py37!'),
        TargetVersionTestCase('text_suffix', 'py37abc'),
    ],
    ids=lambda case: case.id,
)
def test_examples_config_invalid_target_version(case: TargetVersionTestCase):
    """Test that ExamplesConfig validates target_version correctly during initialization."""
    with pytest.raises(ValueError, match=f'Invalid target version: {case.target_version!r}'):
        ExamplesConfig(target_version=case.target_version)


def test_examples_config_empty_string_target_version():
    """Test that empty string target_version is accepted without validation."""
    # Based on the validation logic, empty string should not raise an error
    # because the check is 'if self.target_version' which is falsy for empty string
    config = ExamplesConfig(target_version='')
    assert config.target_version == ''


def test_examples_config_target_version_error_message():
    """Test that the error message includes the expected format."""
    with pytest.raises(ValueError, match='must be like "py37"'):
        ExamplesConfig(target_version='invalid')
