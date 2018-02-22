import sqlite3
import random

import pytest

from slumba import create_function, sqlite_udf
from numba import int64, float64


@sqlite_udf(float64(float64))
def add_one(x):
    return x + 1.0


@sqlite_udf(float64(float64))
def add_one_optional(x):
    return x + 1.0 if x is not None else None


@sqlite_udf(int64(int64, float64))
def add_each_other(x, y):
    return x + int(y)


@sqlite_udf(int64(int64, float64), skipna=False)
def add_each_other_nulls(x, y):
    if x is not None and y is not None:
        return x + int(y)
    return None


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

    con.execute("""
        CREATE TABLE null_t (
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
    null_rows = [row for row in rows] + [('b', None), ('c', None)]
    random.shuffle(null_rows)
    con.executemany('INSERT INTO t (key, value) VALUES (?, ?)', rows)
    create_function(con, 'add_one', 1, add_one)
    create_function(con, 'add_one_optional', 1, add_one_optional)
    return con


def test_scalar(con):
    assert list(con.execute('SELECT add_one(value) AS c FROM t')) == [
        (2.0,),
        (3.0,),
        (4.0,),
        (5.0,),
        (6.0,),
    ]


def test_scalar_with_aggregate(con):
    assert list(
        con.execute('SELECT sum(add_one(value)) as c FROM t')
    ) == [(20.0,)]


def test_scalar_with_empty(con):
    result = list(con.execute('SELECT add_one(value) as c FROM s'))
    assert result == []


def test_optional(con):
    result = list(
        con.execute('SELECT add_one_optional(value) AS c FROM null_t')
    )
    assert result == list(con.execute('SELECT value + 1.0 AS c FROM null_t'))
