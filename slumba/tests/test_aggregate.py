import itertools
import random
import sqlite3
from typing import Generator, List, Optional, Tuple

import pytest
from _pytest.fixtures import SubRequest
from _pytest.tmpdir import TempPathFactory
from numba import float64, int64, optional
from numba.experimental import jitclass
from pkg_resources import parse_version
from pytest_benchmark.fixture import BenchmarkFixture

from slumba import create_aggregate, sqlite_udaf
from slumba.sqlite import SQLITE_VERSION


@sqlite_udaf(optional(float64)(optional(float64)))
@jitclass(dict(total=float64, count=int64))
class Avg:  # pragma: no cover
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


@sqlite_udaf(int64())
@jitclass(dict(count=int64))
class BogusCount:  # pragma: no cover
    def __init__(self) -> None:
        self.count = 1

    def step(self) -> None:
        self.count += 1

    def finalize(self) -> int:
        return self.count


class AvgPython:
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


@sqlite_udaf(optional(float64)(optional(float64)))
@jitclass(dict(total=float64, count=int64))
class WinAvg:  # pragma: no cover
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
        CREATE TABLE s (
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
        ("c", None),
    ]
    con.executemany("INSERT INTO t (key, value) VALUES (?, ?)", rows)
    create_aggregate(con, "avg_numba", 1, Avg)
    create_aggregate(con, "bogus_count", 0, BogusCount)
    create_aggregate(con, "winavg_numba", 1, WinAvg)
    con.create_aggregate("winavg_python", 1, WinAvgPython)
    return con


def test_constructor(con: sqlite3.Connection) -> None:
    ((count,),) = con.execute("SELECT count(1) FROM t").fetchall()
    ((bogus_count,),) = con.execute("SELECT bogus_count() FROM t").fetchall()
    assert bogus_count == count + 1

    ((count,),) = con.execute("SELECT count(1) FROM t").fetchall()
    ((bogus_count,),) = con.execute("SELECT bogus_count() FROM t").fetchall()
    assert bogus_count == count + 1


def test_aggregate(con: sqlite3.Connection) -> None:
    result = list(con.execute("SELECT avg_numba(value) as c FROM t"))
    assert result == list(con.execute("SELECT avg(value) FROM t"))


def test_aggregate_with_empty(con: sqlite3.Connection) -> None:
    result = list(con.execute("SELECT avg_numba(value) as c FROM s"))
    assert result == [(None,)]


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


@pytest.fixture(  # type: ignore[misc]
    params=[
        pytest.param((in_memory, index), id=f"{in_memory_name}-{index_name}")
        for (in_memory, in_memory_name), (index, index_name) in itertools.product(
            [(True, "in_memory"), (False, "on_disk")],
            [(True, "with_index"), (False, "no_index")],
        )
    ],
    scope="module",
)
def large_con(
    request: SubRequest, tmp_path_factory: TempPathFactory
) -> Generator[sqlite3.Connection, None, None]:
    in_memory, index = request.param
    path = ":memory:" if in_memory else str(tmp_path_factory.mktemp("test") / "test.db")
    con = sqlite3.connect(path)
    con.execute(
        """
        CREATE TABLE large_t (
            key INTEGER,
            value DOUBLE PRECISION
        )
        """
    )
    n = int(1e5)
    rows = zip(
        (random.randrange(0, int(0.01 * n)) for _ in range(n)),
        (random.normalvariate(0.0, 1.0) for _ in range(n)),
    )

    if index:
        con.execute('CREATE INDEX "large_t_key_index" ON large_t (key)')

    con.executemany("INSERT INTO large_t (key, value) VALUES (?, ?)", rows)
    create_aggregate(con, "avg_numba", 1, Avg)
    create_aggregate(con, "winavg_numba", 1, WinAvg)
    con.create_aggregate("avg_python", 1, AvgPython)
    con.create_aggregate("winavg_python", 1, WinAvgPython)
    try:
        yield con
    finally:
        if index:
            con.execute("DROP INDEX large_t_key_index")
        con.execute("DROP TABLE large_t")


def run_agg_group_by(
    con: sqlite3.Connection, func: str
) -> List[Tuple[str, Optional[float]]]:
    return con.execute(
        f"SELECT key, {func}(value) AS result FROM large_t GROUP BY key"
    ).fetchall()


@pytest.mark.parametrize(  # type: ignore[misc]
    "func", ["avg", "avg_numba", "avg_python"]
)
def test_aggregate_group_by_bench(
    large_con: sqlite3.Connection, benchmark: BenchmarkFixture, func: str
) -> None:
    assert benchmark(run_agg_group_by, large_con, func)


def run_agg(con: sqlite3.Connection, func: str) -> List[Tuple[str, Optional[float]]]:
    return con.execute(f"SELECT key, {func}(value) AS result FROM large_t").fetchall()


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
        f"SELECT key, {func}(value) OVER (PARTITION BY key) AS result FROM large_t"
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


@sqlite_udaf(float64(float64))
@jitclass(
    [
        ("mean", float64),
        ("sum_of_squares_of_differences", float64),
        ("count", int64),
    ]
)
class Var:  # pragma: no cover
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


@sqlite_udaf(optional(float64)(optional(float64), optional(float64)))
@jitclass(
    [("mean1", float64), ("mean2", float64), ("mean12", float64), ("count", int64)]
)
class Cov:  # pragma: no cover
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


@sqlite_udaf(optional(float64)(float64))
@jitclass([("total", float64), ("count", int64)])
class Sum:  # pragma: no cover
    def __init__(self) -> None:
        self.total = 0.0
        self.count = 0

    def step(self, value: float) -> None:
        self.total += value
        self.count += 1

    def finalize(self) -> Optional[float]:
        return self.total if self.count > 0 else None
