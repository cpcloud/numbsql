import random
import sqlite3

import numpy as np
import pytest
from numba import float64, int64, optional

from slumba import create_function, sqlite_udf


@sqlite_udf(float64(float64))
def add_one(x):  # pragma: no cover
    return x + 1.0


@sqlite_udf(optional(float64)(optional(float64)))
def add_one_optional(x):  # pragma: no cover
    return x + 1.0 if x is not None else None


@sqlite_udf(optional(int64)(optional(int64), optional(float64)))
def add_each_other_nulls(x, y):  # pragma: no cover
    if x is not None and y is not None:
        return x + int(y)
    return None


@pytest.fixture
def con():
    con = sqlite3.connect(":memory:")
    con.execute(
        """
        CREATE TABLE t (
            id INTEGER PRIMARY KEY,
            key VARCHAR(1),
            value DOUBLE PRECISION
        )
        """
    )
    con.execute(
        """
        CREATE TABLE s (
            id INTEGER PRIMARY KEY,
            key VARCHAR(1),
            value DOUBLE PRECISION
        )
        """
    )

    con.execute(
        """
        CREATE TABLE null_t (
            id INTEGER PRIMARY KEY,
            key VARCHAR(1),
            value DOUBLE PRECISION
        )
        """
    )

    rows = [
        ("a", 1.0),
        ("a", 2.0),
        ("b", 3.0),
        ("c", 4.0),
        ("c", 5.0),
    ]
    null_rows = [row for row in rows] + [("b", None), ("c", None)]
    random.shuffle(null_rows)
    con.executemany("INSERT INTO t (key, value) VALUES (?, ?)", rows)
    create_function(con, "add_one_optional", 1, add_one_optional)
    return con


def test_scalar(con):
    assert list(con.execute("SELECT add_one_optional(value) AS c FROM t")) == [
        (2.0,),
        (3.0,),
        (4.0,),
        (5.0,),
        (6.0,),
    ]


def test_scalar_with_aggregate(con):
    assert list(con.execute("SELECT sum(add_one_optional(value)) as c FROM t")) == [
        (20.0,)
    ]


def test_optional(con):
    result = list(con.execute("SELECT add_one_optional(value) AS c FROM null_t"))
    assert result == list(con.execute("SELECT value + 1.0 AS c FROM null_t"))


def add_one_python(x):
    return 1.0 if x is not None else None


@pytest.fixture
def large_con():
    con = sqlite3.connect(":memory:")
    con.execute(
        """
        CREATE TABLE large_t (
            id INTEGER PRIMARY KEY,
            key VARCHAR(1),
            value DOUBLE PRECISION
        )
        """
    )
    n = int(1e5)
    rows = [
        (key, value.item())
        for key, value in zip(
            np.random.choice(list("abcde"), size=n),
            np.random.randn(n),
        )
    ]
    con.executemany("INSERT INTO large_t (key, value) VALUES (?, ?)", rows)
    create_function(con, "add_one_numba", 1, add_one_optional)
    con.create_function("add_one_python", 1, add_one_python)
    return con


def run_scalar_numba(con):
    query = "SELECT add_one_numba(value) AS result FROM large_t"
    result = con.execute(query)
    return result


def run_scalar_python(con):
    query = "SELECT add_one_python(value) AS result FROM large_t"
    result = con.execute(query)
    return result


def test_scalar_bench_numba(large_con, benchmark):
    result = benchmark(run_scalar_numba, large_con)
    assert result


def test_scalar_bench_python(large_con, benchmark):
    result = benchmark(run_scalar_python, large_con)
    assert result
