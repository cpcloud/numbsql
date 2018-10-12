import sqlite3
import time
import string

from operator import attrgetter
from collections import namedtuple

from numba import float64, int64, jitclass, optional

from slumba import sqlite_udaf, create_aggregate


@sqlite_udaf(float64(float64))
@jitclass([
    ('mean', float64),
    ('sum_of_squares_of_differences', float64),
    ('count', int64),
])
class Var:
    def __init__(self):
        self.mean = 0.0
        self.sum_of_squares_of_differences = 0.0
        self.count = 0

    def step(self, value):
        self.count += 1
        delta = value - self.mean
        self.mean += delta
        self.sum_of_squares_of_differences += delta * (value - self.mean)

    def finalize(self):
        return self.sum_of_squares_of_differences / (self.count - 1)


@sqlite_udaf(optional(float64)(optional(float64), optional(float64)))
@jitclass([
    ('mean1', float64),
    ('mean2', float64),
    ('mean12', float64),
    ('count', int64)
])
class Cov:
    def __init__(self):
        self.mean1 = 0.0
        self.mean2 = 0.0
        self.mean12 = 0.0
        self.count = 0

    def step(self, x, y):
        if x is not None and y is not None:
            self.count += 1
            n = self.count
            delta1 = (x - self.mean1) / n
            self.mean1 += delta1
            delta2 = (y - self.mean2) / n
            self.mean2 += delta2
            self.mean12 += (n - 1) * delta1 * delta2 - self.mean12 / n

    def finalize(self):
        n = self.count
        return n / (n - 1) * self.mean12


@sqlite_udaf(optional(float64)(optional(float64)))
@jitclass([('total', float64), ('count', int64)])
class Avg:
    def __init__(self):
        self.total = 0.0
        self.count = 0

    def step(self, value):
        self.total += value
        self.count += 1

    def finalize(self):
        if not self.count:
            return None
        return self.total / self.count


@sqlite_udaf(optional(float64)(float64))
@jitclass([('total', float64), ('count', int64)])
class Sum:
    def __init__(self):
        self.total = 0.0
        self.count = 0

    def step(self, value):
        if value is not None:
            self.total += value
            self.count += 1

    def finalize(self):
        return self.total if self.count > 0 else None


def main():
    import random

    con = sqlite3.connect(':memory:')
    con.execute("""
        CREATE TABLE t (
          id INTEGER PRIMARY KEY,
          key VARCHAR(1),
          value DOUBLE PRECISION
        )
    """)
    # con.execute('CREATE INDEX key_index ON t (key)')

    random_numbers = [
        (
            random.choice(string.ascii_lowercase[:2]),
            random.random()
        ) for _ in range(500000)
    ]

    query = (
        f'INSERT INTO t (key, value) '
        f'VALUES ({", ".join("?" * len(random_numbers[0]))})'
    ),
    con.executemany(query, random_numbers)

    cls = Avg

    builtin = cls.__name__.lower()
    cfunc_defined = f'my{builtin}'
    python_defined = f'my{builtin}2'

    # new way of registering UDAFs using cfuncs
    create_aggregate(
        con,
        cfunc_defined,
        1,
        cls,
    )

    con.create_aggregate(python_defined, 1, cls.class_type.class_def)

    query1 = (f'select key, {builtin}(value) as builtin_{builtin} from t '
              f'group by 1')
    query2 = (f'select key, {cfunc_defined}(value) as cfunc_{cfunc_defined} '
              f'from t group by 1')
    query3 = (f'select key, {python_defined}(value) as python_{python_defined}'
              f' from t group by 1')

    queries = {
        builtin + '_builtin': query1,
        cfunc_defined + '_cfunc': query2,
        python_defined + '_python': query3,
    }

    results = []

    Result = namedtuple('Result', 'name result duration')

    for name, query in queries.items():
        start = time.time()
        exe = con.execute(query)
        duration = time.time() - start
        result = list(exe)
        results.append(Result(name=name, result=result, duration=duration))

    builtin_value = results[0].result

    results.sort(key=attrgetter('duration'))

    strings = [
        (
            f"{name} duration == {duration:.2f}s | "
            f"{round(results[-1].duration / duration):d}x faster | "
            f"values equal? {'yes' if builtin_value == result else 'no'}"
        ) for name, result, duration in results
    ]

    width = max(map(len, strings))

    for s in strings:
        print(s.rjust(width, ' '))


if __name__ == '__main__':
    main()
