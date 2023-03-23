import re
from pathlib import Path

import pytest


def find_cases():
    root_dir = Path(__file__).parent / 'cases_update'
    for f in root_dir.iterdir():
        if not f.is_file():
            continue
        if f.suffix in {'.py', '.md'}:
            content = f.read_text()
            m = re.search(r'(.+?)^#{5,}', content, flags=re.M | re.I | re.S)
            assert m, f'No EXAMPLE match found for {f}'
            example = m.group(1).strip('\n')
            m = re.search(r'^#{5,}\s*output\s*#{5,}\n(.+?)^#{5,}', content, flags=re.M | re.I | re.S)
            assert m, f'No OUTPUT match found for {f}'
            output = m.group(1).strip('\n')
            m = re.search(r'^#{5,}\s*test\s*#{5,}\n(.+)', content, flags=re.M | re.I | re.S)
            assert m, f'No TEST match found for {f}'
            test = m.group(1).strip('\n')
            if f.suffix == '.md':
                m = re.search(r'^```.*?^(.+?)^```', test, flags=re.M | re.S)
                if m:
                    test = m.group(1)
            yield pytest.param(f, example, output, test, id=f.name)


@pytest.mark.parametrize('file_path,example,output,test_code', find_cases())
def test_cases_update(pytester: pytest.Pytester, file_path: Path, example: str, output: str, test_code: str):
    input_file = pytester.makefile(file_path.suffix, **{file_path.stem: example})
    pytester.makepyfile(test_code)
    result = pytester.runpytest('-p', 'no:pretty', '-v', '--update-examples', '--update-examples-disable-summary')
    result.assert_outcomes(passed=1)

    # debug(input_file.read_text(), output)
    assert input_file.read_text() == output
