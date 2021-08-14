import itertools
import random
import sqlite3

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


@pytest.fixture(
    params=[
        pytest.param((in_memory, index), id=f"{in_memory_name}-{index_name}")
        for (in_memory, in_memory_name), (index, index_name) in itertools.product(
            [(True, "in_memory"), (False, "on_disk")],
            [(True, "with_index"), (False, "no_index")],
        )
    ],
)
def large_con(request, tmp_path):
    in_memory, index = request.param
    path = ":memory:" if in_memory else str(tmp_path / "test.db")
    con = sqlite3.connect(path)
    con.execute(
        """
        CREATE TABLE large_t (
            id INTEGER PRIMARY KEY,
            value DOUBLE PRECISION
        )
        """
    )
    n = int(1e5)
    rows = ((random.normalvariate(0.0, 1.0),) for _ in range(n))
    con.executemany("INSERT INTO large_t (value) VALUES (?)", rows)
    create_function(con, "add_one_numba", 1, add_one_optional)
    con.create_function("add_one_python", 1, add_one_python)
    return con


def run_scalar(con, func):
    return con.execute(f"SELECT {func}(value) AS result FROM large_t").fetchall()


@pytest.mark.parametrize("func", ["add_one_numba", "add_one_python"])
def test_scalar_bench(large_con, benchmark, func):
    assert benchmark(run_scalar, large_con, func)
