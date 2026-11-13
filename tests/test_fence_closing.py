from pathlib import Path

import pytest

from pytest_examples import find_examples


@pytest.mark.parametrize('closing', ['```', '````` \t'])
@pytest.mark.parametrize(
    'source',
    ['value = "```"\nassert value == "```"\n', 'value = """\n```suffix\n"""\n', 'print("normal")\n'],
)
def test_only_a_fence_line_closes_an_example(tmp_path: Path, source: str, closing: str) -> None:
    path = tmp_path / 'example.md'
    text = f'```py\n{source}{closing}\n'
    path.write_text(text, encoding='utf-8')

    [example] = find_examples(path)

    assert example.source == source
    assert text[example.start_index : example.end_index] == source
    compile(example.source, str(path), 'exec')
