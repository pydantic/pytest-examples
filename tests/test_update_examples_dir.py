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
            m_test_count = re.search(r'^test_count *= *(\d+)', test, flags=re.M)
            if m_test_count:
                test_count = int(m_test_count.group(1))
            else:
                test_count = 1

            if f.suffix == '.md':
                m = re.search(r'^```.*?^(.+?)^```', test, flags=re.M | re.S)
                if m:
                    test = m.group(1)
            yield pytest.param(f, example, output, test, test_count, id=f.name)


@pytest.mark.parametrize('file_path,example,output,test_code,test_count', find_cases())
def test_cases_update(
    pytester: pytest.Pytester, file_path: Path, example: str, output: str, test_code: str, test_count: int
):
    input_file = pytester.makefile(file_path.suffix, **{f'case_{file_path.stem}': example})
    pytester.makepyfile(test_code)
    result = pytester.runpytest('-p', 'no:pretty', '-vs', '--update-examples', '--update-examples-disable-summary')
    result.assert_outcomes(passed=test_count)

    # debug(input_file.read_text(), output)
    # print(input_file.read_text())
    assert input_file.read_text() == output
