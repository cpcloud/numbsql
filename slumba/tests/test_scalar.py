import sqlite3

import pytest

from slumba import create_function, sqlite_udf
from numba import float64


@sqlite_udf(float64(float64))
def add_one(x):
    return x + 1.0 if x is not None else None


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
    create_function(con, 'add_one', 1, add_one)
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
