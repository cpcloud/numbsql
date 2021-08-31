# Put some Numba in your SQLite

## Fair Warning

This library does unsafe things like pass around function pointer addresses
as integers.  **Use at your own risk**.

If you're unfamiliar with why passing function pointers' addresses around as
integers might be unsafe, then you shouldn't use this library.

## Requirements

* Python `>=3.7`
* `numba`

Use `nix-shell` from the repository to avoid dependency hell.

## Installation

* `poetry install`

## Examples

### Scalar Functions

These are almost the same as decorating a Python function with `numba.jit`.

```python
from typing import Optional

from numbsql import sqlite_udf


@sqlite_udf
def add_one(x: Optional[int]) -> Optional[int]:
    """Add one to `x` if `x` is not NULL."""

    if x is not None:
        return x + 1
    return None
```


### Aggregate Functions

These follow the API of the Python standard library's
`sqlite3.Connection.create_aggregate` method. The difference with numbsql
aggregates is that they require two decorators: `numba.experimental.jit_class` and
`numbsql.sqlite_udaf`. Let's define the `avg` (arithmetic mean) function for
64-bit floating point numbers.

```python
from typing import Optional

from numba.experimental import jitclass

from numbsql import sqlite_udaf


@sqlite_udaf
@jitclass
class Avg:
    total: float
    count: int

    def __init__(self):
        self.total = 0.0
        self.count = 0

    def step(self, value: Optional[float]) -> None:
        if value is not None:
            self.total += value
            self.count += 1

    def finalize(self) -> Optional[float]:
        if not self.count:
            return None
        return self.total / self.count
```

### Window Functions

You can also define window functions for use with SQLite's `OVER` construct:

```python
from typing import Optional

from numba.experimental import jitclass

from numbsql import sqlite_udaf


@sqlite_udaf
@jitclass
class WinAvg:  # pragma: no cover
    total: float
    count: int

    def __init__(self) -> None:
        self.total = 0.0
        self.count = 0

    def step(self, value: Optional[float]) -> None:
        if value is not None:
            self.total += value
            self.count += 1

    def finalize(self) -> Optional[float]:
        count = self.count
        if count:
            return self.total / count
        return None

    def value(self) -> Optional[float]:
        return self.finalize()

    def inverse(self, value: Optional[float]) -> None:
        if value is not None:
            self.total -= value
            self.count -= 1
```

#### Calling your aggregate function

Similar to scalar functions, we register the function with a `sqlite3.Connection` object:

```python
>>> import sqlite3
>>> from numbsql import create_aggregate, create_function
>>> con = sqlite3.connect(":memory:")
>>> create_function(con, "add_one", 1, add_one)
>>> con.execute("SELECT add_one(1)").fetchall()
[(2,)]
```
