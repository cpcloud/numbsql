import sqlite3

import pytest

from numba import float64, int64, jitclass
from slumba import sqlite_udaf, create_aggregate


@sqlite_udaf(float64(float64))
@jitclass(dict(
    total=float64,
    count=int64,
))
class Avg(object):
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


@sqlite_udaf(float64(float64), skipna=False)
@jitclass(dict(
    total=float64,
    count=int64,
))
class AvgWithNulls(object):
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
    ]
    con.executemany('INSERT INTO t (key, value) VALUES (?, ?)', rows)
    create_aggregate(con, 'myavg', 1, Avg)
    return con


def test_aggregate(con):
    result = list(con.execute('SELECT myavg(value) as c FROM t'))
    assert result == list(con.execute('SELECT avg(value) FROM t'))


def test_aggregate_with_empty(con):
    result = list(con.execute('SELECT myavg(value) as c FROM s'))
    assert result == [(None,)]
