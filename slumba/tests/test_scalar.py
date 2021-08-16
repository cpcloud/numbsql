import itertools
import pathlib
import random
import sqlite3
from typing import List, Optional, Tuple

import pytest
from _pytest.fixtures import SubRequest
from numba import float64, int64, optional
from pytest_benchmark.fixture import BenchmarkFixture

from slumba import create_function, sqlite_udf


@sqlite_udf(float64(float64))  # type: ignore[misc]
def add_one_numba(x: float) -> float:  # pragma: no cover
    return x + 1.0


@sqlite_udf(optional(float64)(optional(float64)))  # type: ignore[misc]
def add_one_numba_optional(x: Optional[float]) -> Optional[float]:  # pragma: no cover
    return x + 1.0 if x is not None else None


@sqlite_udf(optional(int64)(optional(int64), optional(float64)))  # type: ignore[misc]
def binary_add_optional(
    x: Optional[int], y: Optional[int]
) -> Optional[float]:  # pragma: no cover
    if x is not None and y is not None:
        return x + int(y)
    return x if x is not None else y


def add_one_python_optional(x: Optional[float]) -> Optional[float]:
    return 1.0 if x is not None else None


@pytest.fixture  # type: ignore[misc]
def con() -> sqlite3.Connection:
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
    con.executemany("INSERT INTO t (key, value) VALUES (?, ?)", rows)

    null_rows = list(
        itertools.chain(
            rows,
            [
                ("b", None),
                ("c", None),
            ],
        )
    )
    random.shuffle(null_rows)
    con.executemany("INSERT INTO null_t (key, value) VALUES (?, ?)", null_rows)

    create_function(con, "add_one_optional_numba", 1, add_one_numba_optional)
    create_function(con, "add_one_numba", 1, add_one_numba)
    return con


@pytest.mark.parametrize(  # type: ignore[misc]
    ("test_expr", "validation_expr"),
    [
        pytest.param(
            "sum(add_one_optional_numba(value))",
            "sum(value + 1.0)",
            id="sum_add_one_optional",
        ),
        pytest.param(
            "add_one_optional_numba(value)",
            "value + 1.0",
            id="scalar_add_one_optional",
        ),
    ],
)
@pytest.mark.parametrize("source_table", ["t", "null_t"])  # type: ignore[misc]
def test_scalar_with_valid_nulls(
    con: sqlite3.Connection,
    test_expr: str,
    validation_expr: str,
    source_table: str,
) -> None:
    test_query = f"select {test_expr} as result from {source_table}"
    validation_query = f"select {validation_expr} as result from {source_table}"
    assert (
        con.execute(test_query).fetchall() == con.execute(validation_query).fetchall()
    )


@pytest.mark.parametrize(  # type: ignore[misc]
    "expr",
    [
        pytest.param(
            "add_one_numba(value)",
            id="scalar_add_one",
            marks=[
                pytest.mark.xfail(
                    reason="error handling for invalid nulls is not yet implemented"
                )
            ],
        )
    ],
)
def test_scalar_with_invalid_nulls(con: sqlite3.Connection, expr: str) -> None:
    query = f"SELECT {expr} AS result FROM null_t"
    with pytest.raises(ValueError):
        con.execute(query)


@pytest.fixture(  # type: ignore[misc]
    params=[
        pytest.param(in_memory, id=in_memory_name)
        for in_memory, in_memory_name in [(True, "in_memory"), (False, "on_disk")]
    ],
)
def large_con(request: SubRequest, tmp_path: pathlib.Path) -> sqlite3.Connection:
    in_memory = request.param
    path = ":memory:" if in_memory else str(tmp_path.joinpath("test.db"))
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
    create_function(con, "add_one_numba_optional", 1, add_one_numba_optional)
    con.create_function("add_one_python_optional", 1, add_one_python_optional)
    return con


def run_scalar(con: sqlite3.Connection, expr: str) -> List[Tuple[Optional[float]]]:
    return con.execute(f"SELECT {expr} AS result FROM large_t").fetchall()


@pytest.mark.parametrize(  # type: ignore[misc]
    "expr",
    [
        pytest.param("add_one_numba_optional(value)", id="add_one_numba_optional"),
        pytest.param("add_one_python_optional(value)", id="add_one_python_optional"),
        pytest.param("value + 1.0", id="add_one_builtin"),
    ],
)
def test_scalar_bench(
    large_con: sqlite3.Connection, benchmark: BenchmarkFixture, expr: str
) -> None:
    assert benchmark(run_scalar, large_con, expr)
