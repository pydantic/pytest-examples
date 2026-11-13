import pytest

from pytest_examples import CodeExample


def test_print_check_preserves_explicit_stream(eval_example):
    example = CodeExample.create(
        'from io import StringIO\n'
        'buffer = StringIO()\n'
        "print('hello', 'world', sep=':', end='!', file=buffer, flush=True)\n"
        "assert buffer.getvalue() == 'hello:world!'\n"
        'print(buffer.getvalue())\n'
        '#> HELLO:WORLD!\n'
    )
    eval_example.print_callback = str.upper

    eval_example.run_print_check(example)


@pytest.mark.parametrize('file_expression', ['None', 'sys.stdout'])
def test_print_check_keeps_stdout_capture(eval_example, file_expression):
    example = CodeExample.create(f"import sys\nprint('hello', file={file_expression})\n#> hello\n")

    eval_example.run_print_check(example)
