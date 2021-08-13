import sqlite3
import time
from typing import List, Tuple

from numba import float64

from slumba import create_function, sqlite_udf

if __name__ == "__main__":
    import random
    from math import exp, pi, sqrt

    from numba import optional

    @sqlite_udf(optional(float64)(float64, float64, float64))
    def normal(x: float, mu: float, sigma: float) -> float:
        c = 1.0 / (sigma * sqrt(2.0 * pi))
        return c * exp(-0.5 * ((x - mu) / sigma) ** 2.0)

    def oldnormal(x: float, mu: float, sigma: float) -> float:
        c = 1.0 / (sigma * sqrt(2.0 * pi))
        return c * exp(-0.5 * ((x - mu) / sigma) ** 2.0)

    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE t (random_numbers DOUBLE PRECISION)")

    random_numbers: List[Tuple[float]] = [(random.random(),) for _ in range(50000)]
    con.executemany("INSERT INTO t VALUES (?)", random_numbers)

    # new way of registering C functions
    create_function(con, "normal", 3, normal, deterministic=True)

    # old way
    con.create_function("oldnormal", 3, oldnormal)
    query1 = "select normal(random_numbers, 0.0, 1.0) from t"
    query2 = "select oldnormal(random_numbers, 0.0, 1.0) from t"

    start1 = time.time()
    exe1 = con.execute(query1)
    result1 = list(exe1)
    t1 = time.time() - start1

    start2 = time.time()
    exe2 = con.execute(query2)
    result2 = list(exe2)
    t2 = time.time() - start2

    print(result1 == result2)
    print(f"t1 == {t1:.2f}")
    print(f"t2 == {t1:.2f}")
