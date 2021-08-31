import pathlib
import sqlite3
import sys
from typing import List, Optional, Tuple

import pytest
from numba.experimental import jitclass
from pkg_resources import parse_version
from pytest_benchmark.fixture import BenchmarkFixture
from testbook import testbook
from testbook.client import TestbookNotebookClient

from numbsql import create_aggregate, sqlite_udaf
from numbsql.exceptions import UnsupportedAggregateTypeError
from numbsql.sqlite import SQLITE_VERSION


@sqlite_udaf
@jitclass
class Avg:  # pragma: no cover
    total: float
    count: int

    def __init__(self) -> None:
        self.total = 0.0
        self.count = 0

    def step(self, value: Optional[float]) -> None:
        if value is not None:
            self.total += value
            self.count += 1

    def finalize(self) -> Optional[float]:
        count = self.count
        return self.total / count if count else None


@sqlite_udaf
@jitclass
class BogusCount:  # pragma: no cover
    count: int

    def __init__(self) -> None:
        self.count = 1

    def step(self) -> None:
        self.count += 1

    def finalize(self) -> int:
        return self.count


class AvgPython:
    total: float
    count: int

    def __init__(self) -> None:
        self.total = 0.0
        self.count = 0

    def step(self, value: Optional[float]) -> None:
        if value is not None:
            self.total += value
            self.count += 1

    def finalize(self) -> Optional[float]:
        count = self.count
        return self.total / count if count else None


@sqlite_udaf
@jitclass
class WinAvg:  # pragma: no cover
    total: float
    count: int

    def __init__(self) -> None:
        self.total = 0.0
        self.count = 0

    def step(self, value: Optional[float]) -> None:
        if value is not None:
            self.total += value
            self.count += 1

    def finalize(self) -> Optional[float]:
        count = self.count
        return self.total / count if count else None

    def value(self) -> Optional[float]:
        return self.finalize()

    def inverse(self, value: Optional[float]) -> None:
        if value is not None:
            self.total -= value
            self.count -= 1


class WinAvgPython:  # pragma: no cover
    total: float
    count: int

    def __init__(self) -> None:
        self.total = 0.0
        self.count = 0

    def step(self, value: Optional[float]) -> None:
        if value is not None:
            self.total += value
            self.count += 1

    def finalize(self) -> Optional[float]:
        count = self.count
        return self.total / count if count else None

    def value(self) -> Optional[float]:
        return self.finalize()

    def inverse(self, value: Optional[float]) -> None:
        if value is not None:
            self.total -= value
            self.count -= 1


@sqlite_udaf
@jitclass
class Var:  # pragma: no cover
    mean: float
    sum_of_squares_of_differences: float
    count: int

    def __init__(self) -> None:
        self.mean = 0.0
        self.sum_of_squares_of_differences = 0.0
        self.count = 0

    def step(self, value: float) -> None:
        self.count += 1
        delta = value - self.mean
        self.mean += delta
        self.sum_of_squares_of_differences += delta * (value - self.mean)

    def finalize(self) -> float:
        return self.sum_of_squares_of_differences / (self.count - 1)


@sqlite_udaf
@jitclass
class Cov:  # pragma: no cover
    mean1: float
    mean2: float
    mean12: float
    count: int

    def __init__(self) -> None:
        self.mean1 = 0.0
        self.mean2 = 0.0
        self.mean12 = 0.0
        self.count = 0

    def step(self, x: Optional[float], y: Optional[float]) -> None:
        if x is not None and y is not None:
            self.count += 1
            n = self.count
            delta1 = (x - self.mean1) / n
            self.mean1 += delta1
            delta2 = (y - self.mean2) / n
            self.mean2 += delta2
            self.mean12 += (n - 1) * delta1 * delta2 - self.mean12 / n

    def finalize(self) -> Optional[float]:
        n = self.count
        if not n:
            return None
        return n / (n - 1) * self.mean12


@sqlite_udaf
@jitclass
class Sum:  # pragma: no cover
    total: float
    count: int

    def __init__(self) -> None:
        self.total = 0.0
        self.count = 0

    def step(self, value: float) -> None:
        self.total += value
        self.count += 1

    def finalize(self) -> Optional[float]:
        return self.total if self.count > 0 else None


@pytest.fixture(scope="session")  # type: ignore[misc]
def con(con: sqlite3.Connection) -> sqlite3.Connection:
    create_aggregate(con, "avg_numba", 1, Avg)
    create_aggregate(con, "bogus_count", 0, BogusCount)
    create_aggregate(con, "winavg_numba", 1, WinAvg)
    con.create_aggregate("winavg_python", 1, WinAvgPython)
    return con


def test_aggregates_with_string_fields_fail() -> None:
    with pytest.raises(
        UnsupportedAggregateTypeError,
        match=r"Aggregates with field type `unicode_type` are not yet implemented",
    ):

        @sqlite_udaf
        @jitclass
        class StringJoin:
            joined: str
            count: int

            def __init__(self) -> None:
                self.joined = ""
                self.count = 0

            def step(self, value: Optional[str], sep: Optional[str]) -> None:
                if value is not None and sep is not None:
                    if not self.count:
                        self.joined = value
                    else:
                        self.joined += sep + value
                    self.count += 1

            def finalize(self) -> Optional[str]:
                return self.joined if self.count else None


def test_constructor(con: sqlite3.Connection) -> None:
    ((count,),) = con.execute("SELECT count(1) FROM t").fetchall()
    ((bogus_count,),) = con.execute("SELECT bogus_count() FROM t").fetchall()
    assert bogus_count == count + 1

    ((count,),) = con.execute("SELECT count(1) FROM t").fetchall()
    ((bogus_count,),) = con.execute("SELECT bogus_count() FROM t").fetchall()
    assert bogus_count == count + 1


def test_aggregate(con: sqlite3.Connection) -> None:
    assert (
        con.execute("SELECT avg_numba(value) FROM t").fetchall()
        == con.execute("SELECT avg(value) FROM t").fetchall()
    )


def test_aggregate_with_empty(con: sqlite3.Connection) -> None:
    assert (
        con.execute("SELECT avg_numba(value) FROM s").fetchall()
        == con.execute("SELECT avg(value) FROM s").fetchall()
    )


xfail_missing_python_api = pytest.mark.xfail(
    reason="Python has no API for defining window functions for SQLite",
    raises=sqlite3.OperationalError,
)


@pytest.mark.parametrize(  # type: ignore[misc]
    "func",
    [
        "winavg_numba",
        pytest.param("winavg_python", marks=[xfail_missing_python_api]),
    ],
)
def test_aggregate_window_numba(con: sqlite3.Connection, func: str) -> None:
    query = f"SELECT {func}(value) OVER (PARTITION BY key) as c FROM t"
    result = list(con.execute(query))
    assert (
        result
        == con.execute(
            "SELECT avg(value) OVER (PARTITION BY key) as c FROM t"
        ).fetchall()
    )


@pytest.fixture(scope="session")  # type: ignore[misc]
def large_con(large_con: sqlite3.Connection) -> sqlite3.Connection:
    create_aggregate(large_con, "avg_numba", 1, Avg)
    create_aggregate(large_con, "winavg_numba", 1, WinAvg)
    large_con.create_aggregate("avg_python", 1, AvgPython)
    large_con.create_aggregate("winavg_python", 1, WinAvgPython)
    return large_con


def run_agg_low_card_group_by(
    con: sqlite3.Connection, func: str
) -> List[Tuple[str, Optional[float]]]:
    return con.execute(
        f"SELECT key, {func}(value) FROM large_t GROUP BY key"
    ).fetchall()


@pytest.mark.parametrize(  # type: ignore[misc]
    "func", ["avg", "avg_numba", "avg_python"]
)
def test_aggregate_low_card_group_by_bench(
    large_con: sqlite3.Connection, benchmark: BenchmarkFixture, func: str
) -> None:
    assert benchmark(run_agg_low_card_group_by, large_con, func)


def run_agg_high_card_group_by(
    con: sqlite3.Connection, func: str
) -> List[Tuple[str, Optional[float]]]:
    return con.execute(
        f"SELECT dense_key, {func}(value) FROM large_t GROUP BY dense_key"
    ).fetchall()


@pytest.mark.parametrize(  # type: ignore[misc]
    "func", ["avg", "avg_numba", "avg_python"]
)
def test_aggregate_high_card_group_by_bench(
    large_con: sqlite3.Connection, benchmark: BenchmarkFixture, func: str
) -> None:
    assert benchmark(run_agg_high_card_group_by, large_con, func)


def run_agg(con: sqlite3.Connection, func: str) -> List[Tuple[str, Optional[float]]]:
    return con.execute(f"SELECT {func}(value) FROM large_t").fetchall()


@pytest.mark.parametrize(  # type: ignore[misc]
    "func", ["avg", "avg_numba", "avg_python"]
)
def test_aggregate_bench(
    large_con: sqlite3.Connection, benchmark: BenchmarkFixture, func: str
) -> None:
    assert benchmark(run_agg, large_con, func)


def run_agg_partition_by(
    con: sqlite3.Connection, func: str
) -> List[Tuple[str, Optional[float]]]:
    return con.execute(
        f"SELECT key, {func}(value) OVER (PARTITION BY key) FROM large_t"
    ).fetchall()


@pytest.mark.parametrize(  # type: ignore[misc]
    "func",
    [
        "avg",
        "winavg_numba",
        pytest.param(
            "winavg_python",
            marks=[
                xfail_missing_python_api,
                pytest.mark.xfail(
                    parse_version(SQLITE_VERSION) < parse_version("3.25.0"),
                    reason="Window functions are not supported in SQLite < 3.25.0",
                    raises=RuntimeError,
                ),
            ],
        ),
    ],
)
def test_window_bench(
    large_con: sqlite3.Connection, benchmark: BenchmarkFixture, func: str
) -> None:
    assert benchmark(run_agg_partition_by, large_con, func)


@pytest.mark.skipif(  # type: ignore[misc]
    sys.platform == "win32",
    reason="Installation of dependencies is problematic on windows",
)
@testbook(  # type: ignore[misc]
    pathlib.Path(__file__).parent.parent.parent / "notebooks" / "sqlite-window.ipynb",
    execute=True,
)
def test_sqlite_window_notebook(tb: TestbookNotebookClient) -> None:
    pass
