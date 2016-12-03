import time
import sqlite3
import inspect

from numba import float64
from slumba import register_scalar_function, sqlite_udf


def register_scalar_cfunc(con, func):
    pyfunc = func.pyfunc
    narg = len(inspect.getargspec(pyfunc).args)
    register_scalar_function(
        con, pyfunc.__name__.encode('utf8'), narg, func.address
    )


if __name__ == '__main__':
    import random
    from math import sqrt, pi, exp

    @sqlite_udf(float64(float64, float64, float64))
    def normal(x, mu, sigma):
        c = 1.0 / (sigma * sqrt(2.0 * pi))
        return c * exp(-0.5 * ((x - mu) / sigma) ** 2.0)

    def oldnormal(x, mu, sigma):
        c = 1.0 / (sigma * sqrt(2.0 * pi))
        return c * exp(-0.5 * ((x - mu) / sigma) ** 2.0)

    con = sqlite3.connect(':memory:')
    con.execute('CREATE TABLE t (random_numbers DOUBLE PRECISION)')

    random_numbers = [
        (random.random(),) for _ in range(50000)
    ]
    con.executemany('INSERT INTO t VALUES (?)', random_numbers)

    # new way of registering C functions
    register_scalar_function(con, b'normal', 3, normal.address)

    # old way
    con.create_function('oldnormal', 3, oldnormal)
    query1 = 'select normal(random_numbers, 0.0, 1.0) as sine from t'
    query2 = 'select oldnormal(random_numbers, 0.0, 1.0) as oldsine from t'

    start1 = time.time()
    exe1 = con.execute(query1)
    result1 = list(exe1)
    t1 = time.time() - start1

    start2 = time.time()
    exe2 = con.execute(query2)
    result2 = list(exe2)
    t2 = time.time() - start2

    print(result1 == result2)
    print('t1 == {:.2f}'.format(t1))
    print('t2 == {:.2f}'.format(t2))
