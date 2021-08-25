import sqlite3
from typing import Any, Callable, List, Optional, Tuple

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from slumba import create_function, sqlite_udf


@sqlite_udf  # type: ignore[misc]
def add_one_numba(x: float) -> float:  # pragma: no cover
    return x + 1.0


def add_one_python(x: float) -> float:
    return x + 1.0


@sqlite_udf  # type: ignore[misc]
def add_one_optional_numba(x: Optional[float]) -> Optional[float]:  # pragma: no cover
    return x + 1.0 if x is not None else None


def add_one_optional_python(x: Optional[float]) -> Optional[float]:
    return x + 1.0 if x is not None else None


@sqlite_udf  # type: ignore[misc]
def binary_add_optional(
    x: Optional[int], y: Optional[int]
) -> Optional[float]:  # pragma: no cover
    if x is not None and y is not None:
        return x + int(y)
    return x if x is not None else y


@sqlite_udf  # type: ignore[misc]
def string_len_numba(s: Optional[str]) -> Optional[int]:
    return len(s) if s is not None else None


@sqlite_udf  # type: ignore[misc]
def string_len_numba_no_opt(s: str) -> int:
    return len(s)


def string_len_python(s: Optional[str]) -> Optional[int]:
    return len(s) if s is not None else None


def register_udfs(con: sqlite3.Connection) -> None:
    create_function(con, "string_len_numba", 1, string_len_numba)
    create_function(con, "string_len_numba_no_opt", 1, string_len_numba_no_opt)
    con.create_function("string_len_python", 1, string_len_python)

    create_function(con, "add_one_numba", 1, add_one_numba)
    con.create_function("add_one_python", 1, add_one_python)

    create_function(con, "add_one_optional_numba", 1, add_one_optional_numba)
    con.create_function("add_one_optional_python", 1, add_one_optional_python)


@pytest.fixture(scope="session")  # type: ignore[misc]
def con(con: sqlite3.Connection) -> sqlite3.Connection:
    register_udfs(con)
    return con


@pytest.fixture(scope="session")  # type: ignore[misc]
def large_con(large_con: sqlite3.Connection) -> sqlite3.Connection:
    register_udfs(large_con)
    return large_con


@pytest.mark.parametrize(  # type: ignore[misc]
    ("func", "args", "expected"),
    [
        pytest.param(string_len_numba, ("abcd",), 4, id="string_len_numba"),
        pytest.param(add_one_numba, (1,), 2, id="add_one_numba"),
        pytest.param(
            add_one_optional_numba, (None,), None, id="add_one_optional_numba"
        ),
    ],
)
def test_function_can_be_called_from_python(
    func: Callable[..., Any], args: Tuple[Any, ...], expected: Any
) -> None:
    assert func(*args) == expected


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
    [pytest.param("add_one_numba(value)", id="scalar_add_one")],
)
def test_scalar_with_invalid_nulls(con: sqlite3.Connection, expr: str) -> None:
    query = f"SELECT {expr} AS result FROM null_t"
    with pytest.raises(ValueError):
        con.execute(query).fetchall()


def test_string(con: sqlite3.Connection) -> None:
    result = list(con.execute("SELECT string_len_numba(key) AS n FROM t"))
    assert result == list(con.execute("SELECT length(key) AS n FROM t"))


def test_string_scalar(con: sqlite3.Connection) -> None:
    result = list(con.execute("SELECT string_len_numba('abcd')").fetchall())
    assert result == [(4,)]


def test_string_null_scalar(con: sqlite3.Connection) -> None:
    result = list(con.execute("SELECT string_len_numba(NULL)").fetchall())
    assert result == [(None,)]


def test_string_null_scalar_no_opt_null(con: sqlite3.Connection) -> None:
    with pytest.raises(ValueError):
        con.execute("SELECT string_len_numba_no_opt(NULL)")


def test_string_null_scalar_no_opt_value(con: sqlite3.Connection) -> None:
    result = list(con.execute("SELECT string_len_numba_no_opt('test')").fetchall())
    assert result == [(4,)]


def test_string_len_same_as_builtin(large_con: sqlite3.Connection) -> None:
    test = large_con.execute("SELECT string_len_numba(key) FROM large_t").fetchall()
    expected = large_con.execute("SELECT length(key) FROM large_t").fetchall()
    assert test == expected


def run_scalar(con: sqlite3.Connection, expr: str) -> List[Tuple[Optional[float]]]:
    return con.execute(f"SELECT {expr} AS result FROM large_t").fetchall()


@pytest.mark.parametrize(  # type: ignore[misc]
    "expr",
    [
        pytest.param("add_one_optional_numba(value)", id="add_one_optional_numba"),
        pytest.param("add_one_optional_python(value)", id="add_one_optional_python"),
        pytest.param("value + 1.0", id="add_one_builtin"),
    ],
)
def test_add_one_bench(
    large_con: sqlite3.Connection, benchmark: BenchmarkFixture, expr: str
) -> None:
    assert benchmark(run_scalar, large_con, expr)


@pytest.mark.parametrize(  # type: ignore[misc]
    "func",
    [
        "string_len_numba(string_key)",
        "string_len_python(string_key)",
        "length(string_key)",
    ],
)
def test_string_len_scalar_bench(
    large_con: sqlite3.Connection, benchmark: BenchmarkFixture, func: str
) -> None:
    assert benchmark(run_scalar, large_con, func)
