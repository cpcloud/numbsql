import sqlite3
import tempfile

from pkg_resources import parse_version

import numpy as np

import pytest

from numba import float64, int64, jitclass, optional
from slumba import sqlite_udaf, create_aggregate
from slumba.cslumba import SQLITE_VERSION


xfail_if_no_window_functions = pytest.mark.xfail(
    parse_version(SQLITE_VERSION) < parse_version('3.25.0'),
    reason='Window functions are not supported in SQLite < 3.25.0',
    raises=RuntimeError
)


@sqlite_udaf(optional(float64)(optional(float64)))
@jitclass(dict(total=float64, count=int64))
class Avg:  # pragma: no cover
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


class AvgPython:
    def __init__(self):
        self.total = 0.0
        self.count = 0

    def step(self, value):
        self.total += value
        self.count += 1

    def finalize(self):
        return self.total / self.count


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
            self.total += value
            self.count += 1


class WinAvgPython:  # pragma: no cover
    def __init__(self):
        self.total = 0.0
        self.count = 0

    def step(self, value):
        self.total += value
        self.count += 1

    def finalize(self):
        return self.total / self.count

    def value(self):
        return self.finalize()

    def inverse(self, value):
        self.total -= value
        self.count -= 1


@sqlite_udaf(optional(float64)(optional(float64)))
@jitclass(dict(total=float64, count=int64))
class AvgWithNulls:  # pragma: no cover
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


@pytest.fixture
def con():
    con = sqlite3.connect(':memory:')
    con.execute("""
        CREATE TABLE t (
            id INTEGER PRIMARY KEY,
            key VARCHAR(1),
            value DOUBLE PRECISION
        )
    """)
    con.execute("""
        CREATE TABLE s (
            id INTEGER PRIMARY KEY,
            key VARCHAR(1),
            value DOUBLE PRECISION
        )
    """)

    rows = [
        ('a', 1.0),
        ('a', 2.0),
        ('b', 3.0),
        ('c', 4.0),
        ('c', 5.0),
        ('c', None),
    ]
    con.executemany('INSERT INTO t (key, value) VALUES (?, ?)', rows)
    create_aggregate(con, 'avg_numba', 1, Avg)
    create_aggregate(con, 'winavg_numba', 1, WinAvg)
    con.create_aggregate('winavg_python', 1, WinAvgPython)
    return con


def test_aggregate(con):
    result = list(con.execute('SELECT avg_numba(value) as c FROM t'))
    assert result == list(con.execute('SELECT avg(value) FROM t'))


def test_aggregate_with_empty(con):
    result = list(con.execute('SELECT avg_numba(value) as c FROM s'))
    assert result == [(None,)]


@xfail_if_no_window_functions
@pytest.mark.parametrize(
    'func',
    ['winavg_numba',
     pytest.mark.xfail('winavg_python', raises=sqlite3.OperationalError)])
def test_aggregate_window_numba(con, func):
    result = list(
        con.execute(
            f'SELECT {func}(value) OVER (PARTITION BY key) as c FROM t'))
    assert result == list(
        con.execute('SELECT avg(value) OVER (PARTITION BY key) as c FROM t'))


@pytest.fixture(scope='module')
def large_con():
    with tempfile.NamedTemporaryFile(suffix='.db') as f:
        con = sqlite3.connect(f.name)
        con.execute("""
            CREATE TABLE large_t (
                key INTEGER,
                value DOUBLE PRECISION
            )
        """)
        n = int(1e4)
        rows = [
            (key, value.item()) for key, value in zip(
                np.random.randint(0, int(0.01 * n), size=n),
                np.random.randn(n),
            )
        ]
        con.executemany('INSERT INTO large_t (key, value) VALUES (?, ?)', rows)
        con.execute('CREATE INDEX "large_t_key_index" ON large_t (key)')
        create_aggregate(con, 'avg_numba', 1, Avg)
        create_aggregate(con, 'winavg_numba', 1, WinAvg)
        con.create_aggregate('avg_python', 1, AvgPython)
        con.create_aggregate('winavg_python', 1, WinAvgPython)
        yield con


def run_agg_group_by_numba(con):
    query = 'SELECT key, avg_numba(value) AS result FROM large_t GROUP BY key'
    result = con.execute(query)
    return result.fetchall()


def run_agg_group_by_builtin(con):
    query = 'SELECT key, avg(value) AS result FROM large_t GROUP BY key'
    result = con.execute(query)
    return result.fetchall()


def run_agg_group_by_python(con):
    query = 'SELECT key, avg_python(value) AS result FROM large_t GROUP BY key'
    result = con.execute(query)
    return result.fetchall()


def test_aggregate_group_by_bench_numba(large_con, benchmark):
    result = benchmark(run_agg_group_by_numba, large_con)
    assert result


def test_aggregate_group_by_bench_builtin(large_con, benchmark):
    result = benchmark(run_agg_group_by_builtin, large_con)
    assert result


def test_aggregate_group_by_bench_python(large_con, benchmark):
    result = benchmark(run_agg_group_by_python, large_con)
    assert result


def run_agg_numba(con):
    query = 'SELECT key, avg_numba(value) AS result FROM large_t'
    result = con.execute(query)
    return result


def run_agg_builtin(con):
    query = 'SELECT key, avg(value) AS result FROM large_t'
    result = con.execute(query)
    return result


def run_agg_python(con):
    query = 'SELECT key, avg_python(value) AS result FROM large_t'
    result = con.execute(query)
    return result


def test_aggregate_bench_numba(large_con, benchmark):
    result = benchmark(run_agg_numba, large_con)
    assert result


def test_aggregate_bench_builtin(large_con, benchmark):
    result = benchmark(run_agg_builtin, large_con)
    assert result


def test_aggregate_bench_python(large_con, benchmark):
    result = benchmark(run_agg_python, large_con)
    assert result


def run_agg_partition_by_numba(con):
    query = """
SELECT key, winavg_numba(value) OVER (PARTITION BY key) AS result FROM large_t
"""
    result = con.execute(query)
    return result.fetchall()


def run_agg_partition_by_builtin(con):
    query = """
SELECT key, avg(value) OVER (PARTITION BY key) AS result FROM large_t"""
    result = con.execute(query)
    return result.fetchall()


def run_agg_partition_by_python(con):
    query = """
SELECT key, winavg_python(value) OVER (PARTITION BY key) AS result FROM large_t
"""
    result = con.execute(query)
    return result.fetchall()


@xfail_if_no_window_functions
def test_window_bench_numba(large_con, benchmark):
    result = benchmark(run_agg_partition_by_numba, large_con)
    assert result


@xfail_if_no_window_functions
def test_window_bench_builtin(large_con, benchmark):
    result = benchmark(run_agg_partition_by_builtin, large_con)
    assert result


@xfail_if_no_window_functions
@pytest.mark.xfail(raises=sqlite3.OperationalError)
def test_window_bench_python(large_con, benchmark):
    result = benchmark(run_agg_partition_by_python, large_con)
    assert result


@sqlite_udaf(float64(float64))
@jitclass([
    ('mean', float64),
    ('sum_of_squares_of_differences', float64),
    ('count', int64),
])
class Var:  # pragma: no cover
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
class Cov:  # pragma: no cover
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
        if not n:
            return None
        return n / (n - 1) * self.mean12


@sqlite_udaf(optional(float64)(float64))
@jitclass([('total', float64), ('count', int64)])
class Sum:  # pragma: no cover
    def __init__(self):
        self.total = 0.0
        self.count = 0

    def step(self, value):
        if value is not None:
            self.total += value
            self.count += 1

    def finalize(self):
        return self.total if self.count > 0 else None
