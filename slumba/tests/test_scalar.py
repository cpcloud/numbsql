import sqlite3
from typing import List, Optional, Tuple

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


def string_single_upper_python(s: str) -> str:
    result = []
    for c in s:
        result.append(c.upper())
    return "".join(result)


@sqlite_udf
def string_single_upper_numba(s: str) -> str:
    s += ""
    result = []
    for c in s:
        result.append(c.upper())
    s = "".join(result)
    return s


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

    create_function(con, "string_single_upper_numba", 1, string_single_upper_numba)
    con.create_function("string_single_upper_python", 1, string_single_upper_python)


@pytest.fixture(scope="session")  # type: ignore[misc]
def con(con: sqlite3.Connection) -> sqlite3.Connection:
    register_udfs(con)
    return con


@pytest.fixture(scope="session")  # type: ignore[misc]
def large_con(large_con: sqlite3.Connection) -> sqlite3.Connection:
    register_udfs(large_con)
    return large_con


def test_string_len_same_as_builtin(con: sqlite3.Connection) -> None:
    test = con.execute("SELECT string_len_numba(key) FROM t").fetchall()
    expected = con.execute("SELECT length(key) FROM t").fetchall()
    assert test == expected


def test_string_single_upper(con: sqlite3.Connection) -> None:
    test = con.execute("SELECT string_single_upper_numba(key) FROM t").fetchall()
    expected = con.execute("SELECT string_single_upper_python(key) FROM t").fetchall()
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
    "expr",
    [
        pytest.param("string_len_numba(string_key)", id="string_len_numba"),
        pytest.param("string_len_python(string_key)", id="string_len_python"),
        pytest.param("length(string_key)", id="string_len_builtin"),
    ],
)
def test_string_len_scalar_bench(
    large_con: sqlite3.Connection, benchmark: BenchmarkFixture, expr: str
) -> None:
    assert benchmark(run_scalar, large_con, expr)


@pytest.mark.parametrize(  # type: ignore[misc]
    "expr",
    [
        pytest.param("string_upper_numba(string_key)", id="string_upper_numba"),
        pytest.param("string_upper_python(string_key)", id="string_upper_python"),
    ],
)
def test_string_upper_scalar_bench(
    large_con: sqlite3.Connection, benchmark: BenchmarkFixture, expr: str
) -> None:
    assert benchmark(run_scalar, large_con, expr)
