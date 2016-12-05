# Put some Numba in your SQLite

[![Circle CI](https://circleci.com/gh/cpcloud/slumba.svg?style=shield&circle-token=:circle-token)](https://github.com/cpcloud/slumba)

## Requirements

* `cython`
* `numba`

## Installation
* `python setup.py develop`

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
    return x + 1 if x is not None else None
```


### Aggregate Functions


These follow the API of the Python standard library's
`sqlite3.Connection.create_aggregate` method. The difference with slumba
aggregates is that they require two decorators: `numba.jitclass` and
`slumba.sqlite_udaf`. Let's define the `avg` (average) function for
floating point numbers.

```python
from numba import jitclass, int64, float64
from slumba import sqlite_udaf

@sqlite_udaf(float64(float64))
@jitclass([
  ('total', float64),
  ('count', int64)
])
class Avg(object):
    def __init__(self):
        self.total = 0.0
        self.count = 0.0

    def step(self, value):
        if value is not None:
            self.total += value
            self.count += 1

    def finalize(self):
        if self.count:
            return self.total / self.count
        else:
            return None
```
