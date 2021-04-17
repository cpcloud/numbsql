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


@sqlite_udf(optional(int64)(optional(int64)))
def add_one(x):
    """Add one to `x` if `x` is not NULL."""

    if x is not None:
        return x + 1
    return None
```


### Aggregate Functions

These follow the API of the Python standard library's
`sqlite3.Connection.create_aggregate` method. The difference with slumba
aggregates is that they require two decorators: `numba.experimental.jit_class` and
`slumba.sqlite_udaf`. Let's define the `avg` (arithmetic mean) function for
64-bit floating point numbers.

```python
from numba import int64, float64
from numba.experimental import jit_class
from slumba import sqlite_udaf


@sqlite_udaf(optional(float64)(optional(float64)))
@jit_class(dict(total=float64, count=int64))
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

### Window Functions

You can also define window functions for use with SQLite's `OVER` construct:

```python
@sqlite_udaf(optional(float64)(optional(float64)))
@jitclass(dict(total=float64, count=int64))
class WinAvg:  # pragma: no cover
    def __init__(self):
        self.total = 0.0
        self.count = 0

    def step(self, value):
        if value is not None:
            self.total += value
            self.count += 1

    def finalize(self):
        count = self.count
        if count:
            return self.total / count
        return None

    def value(self):
        return self.finalize()

    def inverse(self, value):
        if value is not None:
            self.total -= value
            self.count -= 1
```
