import random
import sqlite3
import string
import time
from operator import attrgetter
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple

from numba.experimental import jitclass
from numba.types import ClassType

from numbsql import create_aggregate, sqlite_udaf


@sqlite_udaf
@jitclass
class Var:
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
class Cov:
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
class Avg:
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
        if not self.count:
            return None
        return self.total / self.count


@sqlite_udaf
@jitclass
class Sum:
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
        return self.total if self.count > 0 else None


def main() -> None:
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
    con.execute("CREATE INDEX key_index ON t (key)")

    random_numbers: List[Tuple[str, float]] = [
        (random.choice(string.ascii_lowercase[:2]), random.random())
        for _ in range(500000)
    ]

    placeholders = ", ".join("?" * len(random_numbers[0]))
    query = f"INSERT INTO t (key, value) VALUES ({placeholders})"
    con.executemany(query, random_numbers)

    cls: ClassType = Avg

    builtin = cls.__name__.lower()
    cfunc_defined = f"my{builtin}"
    python_defined = f"my{builtin}2"

    # new way of registering UDAFs using cfuncs
    create_aggregate(con, cfunc_defined, 1, cls)

    con.create_aggregate(python_defined, 1, cls.class_type.class_def)

    query1 = f"select key, {builtin}(value) as builtin_{builtin} from t " f"group by 1"
    query2 = (
        f"select key, {cfunc_defined}(value) as cfunc_{cfunc_defined} "
        f"from t group by 1"
    )
    query3 = (
        f"select key, {python_defined}(value) as python_{python_defined}"
        f" from t group by 1"
    )

    queries: Dict[str, str] = {
        f"{builtin}_builtin": query1,
        f"{cfunc_defined}_cfunc": query2,
        f"{python_defined}_python": query3,
    }

    class Result(NamedTuple):
        name: str
        result: List[Tuple[str, float]]
        duration: float

    results: List[Result] = []

    execute: Callable = con.execute
    for name, query in queries.items():
        start = time.time()
        exe = execute(query)
        stop = time.time()
        duration = stop - start
        result = list(exe)
        results.append(Result(name=name, result=result, duration=duration))

    builtin_result: List = results[0].result

    results.sort(key=attrgetter("duration"))

    strings: List[str] = [
        (
            f"{name} duration == {duration:.2f}s | "
            f"{round(results[-1].duration / duration):d}x faster | "
            f"values equal? {'yes' if builtin_result == result else 'no'}"
        )
        for name, result, duration in results
    ]

    width = max(map(len, strings))
    print("\n".join(string.rjust(width, " ")) for string in strings)


if __name__ == "__main__":
    main()
