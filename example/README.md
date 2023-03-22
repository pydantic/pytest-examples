# Example of `pytest-examples` Usage

```py
x = 123
print('this is an example of how pytest-examples is used', x, [1, 2, 3])
#> this is an example of how pytest-examples is used 123 [1, 2, 3])

# something more complex
if True:
    print({i: f'this is {i}' for i in range(10)})
    """
    {
        0: 'this is 0',
        1: 'this is 1',
        2: 'this is 2',
        3: 'this is 3',
        4: 'this is 4',
        5: 'this is 5',
        6: 'this is 6',
        7: 'this is 7',
        8: 'this is 8',
        9: 'this is 9',
    }
    """
```
