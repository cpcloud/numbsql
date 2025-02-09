import numpy as np
from numba import njit
from typing import Optional
import sqlite3
from numba.experimental import jitclass
from numba.types import float64, int64
from numbsql import create_aggregate, sqlite_udaf

import pytest


class BaseSum:
    def __init__(self) -> None:
        self.total = 0.0
        self.count = 0

    def step(self, value: Optional[float64]) -> None:
        if value is not None and not np.isnan(value):
            self.total += value
            self.count += 1

    def finalize(self) -> Optional[float64]:
        return self.total if self.count else np.nan


Sum = jitclass([("total", float64), ("count", int64)])(BaseSum)
SQLiteSum = sqlite_udaf(Sum)


def total_python(values):  # type: ignore[no-untyped-def]
    agg = BaseSum()
    for value in values:
        agg.step(value)
    return agg.finalize()


@njit(float64(float64[:]))
def total_jitclass(values):  # type: ignore[no-untyped-def]
    agg = Sum()
    for value in values:
        agg.step(value)
    return agg.finalize()


@njit(float64(float64[:]))
def total_jitclass_method_cached(values):  # type: ignore[no-untyped-def]
    agg = Sum()
    step = agg.step
    for value in values:
        step(value)
    return agg.finalize()


@njit(float64(float64[:]))
def total_no_jitclass(values):  # type: ignore[no-untyped-def]
    total = 0.0
    count = 0
    for value in values:
        if not np.isnan(value):
            total += value
            count += 1
    return total if count else np.nan


N = 1_000_000


@pytest.fixture(scope="session", params=[True, False], ids=["nans", "no_nans"])
def data(request):  # type: ignore[no-untyped-def]
    values = np.random.randn(N)
    if request.param:
        values[values > 0.5] = np.nan
    return values


@pytest.mark.parametrize(
    "total",
    [total_jitclass, total_jitclass_method_cached, total_no_jitclass, total_python],
    ids=["jitclass", "jitclass_method_cached", "no_jitclass", "pure_python"],
)
def test_ref_count_perf(total, data, benchmark):  # type: ignore[no-untyped-def]
    benchmark(total, data)


@pytest.fixture(scope="session")
def db(tmp_path_factory, data):  # type: ignore[no-untyped-def]
    tmp_path = tmp_path_factory.mktemp("test")
    db_path = tmp_path / "test.db"
    con = sqlite3.connect(str(db_path))

    con.execute("CREATE TABLE t (x REAL)")
    con.executemany("INSERT INTO t VALUES (?)", [(value,) for value in data.tolist()])
    create_aggregate(con, "jitclass_total", 1, SQLiteSum, deterministic=True)
    con.create_aggregate("class_total", 1, BaseSum)
    yield con
    con.close()


@pytest.mark.parametrize("total", ["jitclass_total", "class_total"])
def test_ref_count_perf_database(total, benchmark, db):  # type: ignore[no-untyped-def]
    benchmark(db.execute, f"SELECT {total}(x) FROM t")
