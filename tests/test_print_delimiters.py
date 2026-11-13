import pytest

from pytest_examples import CodeExample


@pytest.mark.parametrize('suffix,delimiter', [('.md', '"""'), ('.py', "'''")])
def test_updated_output_with_quote_delimiter_is_valid_python(
    eval_example, monkeypatch, pytestconfig, tmp_path, suffix, delimiter
):
    output = f'first line\n{delimiter}\nlast line'
    path = tmp_path / f'example{suffix}'
    source = f'print({output!r})\n'
    path.write_text(source)
    example = CodeExample.create(source, path=path)
    monkeypatch.setattr(pytestconfig.option, 'update_examples', True)

    eval_example.run_print_update(example, rewrite_assertions=False)

    compile(example.source, str(path), 'exec')
    eval_example.run_print_check(example, rewrite_assertions=False)
