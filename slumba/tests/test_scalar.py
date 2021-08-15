import itertools
import random
import sqlite3
import string as strings
from typing import Generator, List, Optional, Tuple

import pytest
from _pytest.fixtures import SubRequest
from _pytest.tmpdir import TempPathFactory
from numba import float64, int64, optional
from numba.types import string
from pytest_benchmark.fixture import BenchmarkFixture

from slumba import create_function, sqlite_udf


@sqlite_udf(float64(float64))  # type: ignore[misc]
def add_one_numba(x: float) -> float:  # pragma: no cover
    return x + 1.0


def add_one_python(x: float) -> float:
    return x + 1.0


@sqlite_udf(optional(float64)(optional(float64)))  # type: ignore[misc]
def add_one_optional_numba(x: Optional[float]) -> Optional[float]:  # pragma: no cover
    return x + 1.0 if x is not None else None


def add_one_optional_python(x: Optional[float]) -> Optional[float]:
    return x + 1.0 if x is not None else None


@sqlite_udf(optional(int64)(optional(int64), optional(float64)))  # type: ignore[misc]
def binary_add_optional(
    x: Optional[int], y: Optional[int]
) -> Optional[float]:  # pragma: no cover
    if x is not None and y is not None:
        return x + int(y)
    return x if x is not None else y


@sqlite_udf(optional(int64)(optional(string)))  # type: ignore[misc]
def string_len_numba(s: Optional[str]) -> Optional[int]:
    return len(s) if s is not None else None


@sqlite_udf(int64(string))  # type: ignore[misc]
def string_len_numba_no_opt(s: str) -> int:
    return len(s)


def string_len_python(s: Optional[str]) -> Optional[int]:
    return len(s) if s is not None else None


@pytest.fixture(scope="module")  # type: ignore[misc]
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

    create_function(con, "string_len_numba", 1, string_len_numba)
    create_function(con, "string_len_numba_no_opt", 1, string_len_numba_no_opt)
    con.create_function("string_len_python", 1, string_len_python)

    create_function(con, "add_one_numba", 1, add_one_numba)
    con.create_function("add_one_python", 1, add_one_python)

    create_function(con, "add_one_optional_numba", 1, add_one_optional_numba)
    con.create_function("add_one_optional_python", 1, add_one_optional_python)

    create_function(con, "string_len_numba", 1, string_len_numba)
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


@pytest.fixture(  # type: ignore[misc]
    params=[
        pytest.param(
            (in_memory, index, null_perc),
            id=f"{in_memory_name}-{index_name}-{null_perc_name}",
        )
        for (in_memory, in_memory_name), (index, index_name), (
            null_perc,
            null_perc_name,
        ) in itertools.product(
            [(True, "in_memory"), (False, "on_disk")],
            [(True, "with_index"), (False, "no_index")],
            [(0.0, "no_nulls"), (0.5, "50_perc_nulls"), (1.0, "all_nulls")],
        )
    ],
    scope="module",
)
def large_con(
    request: SubRequest, tmp_path_factory: TempPathFactory
) -> Generator[sqlite3.Connection, None, None]:
    key_n = 10
    in_memory, index, null_perc = request.param
    path = ":memory:" if in_memory else str(tmp_path_factory.mktemp("test") / "test.db")
    con = sqlite3.connect(path)

    create_function(con, "add_one_numba", 1, add_one_numba)
    con.create_function("add_one_python", 1, add_one_python)

    create_function(con, "add_one_optional_numba", 1, add_one_optional_numba)
    con.create_function("add_one_optional_python", 1, add_one_optional_python)

    create_function(con, "string_len_numba", 1, string_len_numba)
    con.create_function("string_len_python", 1, string_len_python)

    con.execute(
        f"""
        CREATE TABLE large_t (
            id INTEGER PRIMARY KEY,
            key VARCHAR({key_n:d}),
            value DOUBLE PRECISION
        )
        """
    )
    n = int(1e5)
    rows = [
        (
            (
                "".join(
                    random.choices(
                        strings.ascii_letters, k=random.randrange(0, key_n + 1)
                    )
                )
                if random.random() < (1.0 - null_perc)
                else None
            ),
            random.normalvariate(0.0, 1.0) if random.random() < null_perc else None,
        )
        for _ in range(n)
    ]

    if index:
        con.execute('CREATE INDEX "large_t_key_index" ON large_t (key)')

    con.executemany("INSERT INTO large_t (key, value) VALUES (?, ?)", rows)

    try:
        yield con
    finally:
        if index:
            con.execute("DROP INDEX large_t_key_index")
        con.execute("DROP TABLE large_t")


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
    "func", ["string_len_numba(key)", "string_len_python(key)", "length(key)"]
)
def test_string_len_scalar_bench(
    large_con: sqlite3.Connection, benchmark: BenchmarkFixture, func: str
) -> None:
    assert benchmark(run_scalar, large_con, func)
