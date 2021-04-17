# Put some Numba in your SQLite

## Fair Warning

This library does unsafe things like pass around function pointer addresses
as integers.  **Use at your own risk**.

If you're unfamiliar with why passing function pointers' addresses around as
integers might be unsafe, then you shouldn't use this library.

## Requirements

* Python >=3.7
* `numba`

Use `nix-shell` from the repository to avoid dependency hell.

## Installation
* `poetry install`

## Examples

### Scalar Functions

These are almost the same as decorating a Python function with
`numba.jit`. In the case of `sqlite_udf` a signature is required.

```python
from slumba import sqlite_udf
from numba import int64


@sqlite_udf(int64(int64))
def add_one(x):
    """Add one to `x` if `x` is not NULL
    """
    if x is not None:
        return x + 1
    return None
```


### Aggregate Functions


These follow the API of the Python standard library's
`sqlite3.Connection.create_aggregate` method. The difference with slumba
aggregates is that they require two decorators: `numba.jitclass` and
`slumba.sqlite_udaf`. Let's define the `avg` (average) function for
floating point numbers.

```python
from numba import int64, float64, jitclass
from slumba import sqlite_udaf


@sqlite_udaf(float64(float64))
@jitclass(dict(total=float64, count=int64))
class Avg:
    def __init__(self):
        self.total = 0.0
        self.count = 0

    def step(self, value):
        if value is not None:
            self.total += value
            self.count += 1

    def finalize(self):
        if not self.count:
            return None
        return self.total / self.count
```
