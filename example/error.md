# Example of `pytest-examples` Usage

```py
description = 'this is an example of how pytest-examples is used'
a = 1
b = 2
# assert a + b == 4
# c = 1 / 0


def foo():
    """
    This will fail
    """
    x = 1
    return x / 0


foo()
```
