import sqlite3
from typing import Callable, List, Optional, Tuple, TypeVar

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from numbsql import create_function, sqlite_udf


def add_one_python(x: float) -> float:
    return x + 1.0


add_one_numba = sqlite_udf(add_one_python)


def add_one_optional_python(x: Optional[float]) -> Optional[float]:
    return x + 1.0 if x is not None else None


add_one_optional_numba = sqlite_udf(add_one_optional_python)


def binary_add_optional_python(
    x: Optional[int],
    y: Optional[int],
) -> Optional[int]:  # pragma: no cover
    if x is not None and y is not None:
        return x + int(y)
    return x if x is not None else y


binary_add_optional_numba = sqlite_udf(binary_add_optional_python)


def string_len_python(s: Optional[str]) -> Optional[int]:
    return len(s) if s is not None else None


string_len_numba = sqlite_udf(string_len_python)


def string_len_python_no_opt(s: str) -> int:
    return len(s)


string_len_numba_no_opt = sqlite_udf(string_len_python_no_opt)


def string_identity_python(s: str) -> str:
    return s


string_identity_numba = sqlite_udf(string_identity_python)


def string_upper_python(s: Optional[str]) -> Optional[str]:
    return s.upper() if s is not None else None


string_upper_numba = sqlite_udf(string_upper_python)


def string_single_upper_python(s: str) -> str:
    s += ""
    result = []
    for c in s:
        result.append(c.upper())
    s = "".join(result)
    return s


string_single_upper_numba = sqlite_udf(string_single_upper_python)


def register_udfs(con: sqlite3.Connection) -> None:
    create_function(con, "string_len_numba", 1, string_len_numba)
    create_function(con, "string_len_numba_no_opt", 1, string_len_numba_no_opt)
    con.create_function("string_len_python", 1, string_len_python)
    con.create_function("string_len_python_no_opt", 1, string_len_python_no_opt)

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

    create_function(con, "binary_add_optional_numba", 2, binary_add_optional_numba)
    con.create_function("binary_add_optional_python", 2, binary_add_optional_python)


@pytest.fixture(scope="session")  # type: ignore[misc]
def con(con: sqlite3.Connection) -> sqlite3.Connection:
    register_udfs(con)
    return con


@pytest.fixture(scope="session")  # type: ignore[misc]
def large_con(large_con: sqlite3.Connection) -> sqlite3.Connection:
    register_udfs(large_con)
    return large_con


Arg = TypeVar("Arg", str, float, Optional[float])


@pytest.mark.parametrize(  # type: ignore[misc]
    ("func", "args", "expected"),
    [
        pytest.param(
            sqlite_udf(string_len_python), ("abcd",), 4, id="string_len_numba"
        ),
        pytest.param(sqlite_udf(add_one_python), (1.0,), 2.0, id="add_one_numba"),
        pytest.param(
            sqlite_udf(add_one_optional_python),
            (None,),
            None,
            id="add_one_optional_numba",
        ),
        pytest.param(
            sqlite_udf(binary_add_optional_python),
            (1.0, 2.0),
            3.0,
            id="binary_add_optional_numba_without_none",
        ),
        pytest.param(
            sqlite_udf(binary_add_optional_python),
            (1.0, None),
            1.0,
            id="binary_add_optional_numba_with_none",
        ),
    ],
)
def test_function_can_be_called_from_python(
    func: Callable[..., Optional[int]],
    args: Tuple[Arg, ...],
    expected: Optional[int],
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
    [pytest.param("add_one_numba(value)", id="add_one_numba")],
)
def test_scalar_with_invalid_nulls(con: sqlite3.Connection, expr: str) -> None:
    query = f"SELECT {expr} FROM null_t"
    with pytest.raises(ValueError):
        con.execute(query).fetchall()


def test_string(con: sqlite3.Connection) -> None:
    result = con.execute("SELECT string_len_numba(key) FROM t").fetchall()
    assert result == con.execute("SELECT length(key) FROM t").fetchall()


def test_string_scalar(con: sqlite3.Connection) -> None:
    result = con.execute("SELECT string_len_numba('abcd')").fetchall()
    assert result == [(4,)]


def test_string_null_scalar(con: sqlite3.Connection) -> None:
    result = con.execute("SELECT string_len_numba(NULL)").fetchall()
    assert result == [(None,)]


def test_string_null_scalar_no_opt_null(con: sqlite3.Connection) -> None:
    query = "SELECT string_len_numba_no_opt(NULL)"
    with pytest.raises(ValueError):
        con.execute(query)


def test_string_null_scalar_no_opt_value(con: sqlite3.Connection) -> None:
    result = con.execute("SELECT string_len_numba_no_opt('test')").fetchall()
    assert result == [(4,)]


def test_string_len_same_as_builtin(con: sqlite3.Connection) -> None:
    test = con.execute("SELECT string_len_numba(key) FROM t").fetchall()
    expected = con.execute("SELECT length(key) FROM t").fetchall()
    assert test == expected


def test_string_single_upper(con: sqlite3.Connection) -> None:
    test = con.execute("SELECT string_single_upper_numba(key) FROM t").fetchall()
    expected = con.execute("SELECT string_single_upper_python(key) FROM t").fetchall()
    assert test == expected


def run_scalar(con: sqlite3.Connection, expr: str) -> List[Tuple[Optional[float]]]:
    return con.execute(f"SELECT {expr} FROM large_t").fetchall()


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
