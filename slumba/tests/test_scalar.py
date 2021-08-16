import sqlite3
from typing import Any, List, Optional, Tuple

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


@sqlite_udf  # type: ignore[misc]
def string_identity_numba(s: str) -> str:
    return s


def string_identity_python(s: str) -> str:
    return s


@sqlite_udf
def string_upper_numba(s: Optional[str]) -> Optional[str]:
    return s.upper() if s is not None else None


def string_upper_python(s: Optional[str]) -> Optional[str]:
    return s.upper() if s is not None else None


def register_udfs(con: sqlite3.Connection) -> None:
    create_function(con, "string_len_numba", 1, string_len_numba)
    create_function(con, "string_len_numba_no_opt", 1, string_len_numba_no_opt)
    con.create_function("string_len_python", 1, string_len_python)

    create_function(con, "add_one_numba", 1, add_one_numba)
    con.create_function("add_one_python", 1, add_one_python)

    create_function(con, "add_one_optional_numba", 1, add_one_optional_numba)
    con.create_function("add_one_optional_python", 1, add_one_optional_python)

    create_function(con, "string_identity_numba", 1, string_identity_numba)
    con.create_function("string_identity_python", 1, string_identity_python)

    create_function(con, "string_upper_numba", 1, string_upper_numba)
    con.create_function("string_upper_python", 1, string_upper_python)


def test_string_len_same_as_builtin(large_con: sqlite3.Connection) -> None:
    test = large_con.execute(
        "SELECT string_len_numba(string_key) FROM large_t"
    ).fetchall()
    expected = large_con.execute("SELECT length(string_key) FROM large_t").fetchall()
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


@pytest.mark.parametrize(  # type: ignore[misc]
    "func",
    [
        "string_upper_numba(key)",
        "string_upper_python(key)",
    ],
)
def test_string_upper_scalar_bench(
    large_con: sqlite3.Connection, benchmark: BenchmarkFixture, func: str
) -> None:
    assert benchmark(run_scalar, large_con, func)
