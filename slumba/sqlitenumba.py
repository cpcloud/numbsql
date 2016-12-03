import sqlite3
import inspect
import ast
import time

from ctypes import CDLL, c_void_p, c_double, c_int, c_int64, c_ubyte
from ctypes.util import find_library

from math import sqrt, exp, pi

from numba import cfunc, int64, float64, jit, i1, f8, i8, void, int32

from gen import *  # we can probably do better than a star import here

from slumba import (
    register_scalar_function,
    _SQLITE_INTEGER as SQLITE_INTEGER,
    _SQLITE_FLOAT as SQLITE_FLOAT,
    _SQLITE_TEXT as SQLITE_TEXT,
    _SQLITE_BLOB as SQLITE_BLOB,
    _SQLITE_NULL as SQLITE_NULL,
)


class SQLiteUDF(object):
    __slots__ = 'wrapper', 'pyfunc'

    def __init__(self, wrapper, pyfunc):
        self.wrapper = wrapper
        self.pyfunc = pyfunc

    @property
    def address(self):
        return self.wrapper.address

    def __call__(self, *args, **kwargs):
        return self.wrapper(*args, **kwargs)


def sqlite_udf(signature):
    def wrapped(func):
        jitted = jit(signature, nopython=True)(func)
        assert func.__name__ not in globals(), \
            'found previously defined function {} in globals()'.format(
                func.__name__
            )
        globals()[func.__name__] = jitted
        genmod = gen_scalar(jitted)
        mod = ast.fix_missing_locations(genmod)
        bytecode = compile(mod, __file__, 'exec')
        exec(bytecode)
        w = locals()['wrapper']
        return SQLiteUDF(w, func)
    return wrapped


def register_scalar_cfunc(con, func):
    pyfunc = func.pyfunc
    narg = len(inspect.getargspec(pyfunc).args)
    register_scalar_function(
        con, pyfunc.__name__.encode('utf8'), narg, func.address
    )


if __name__ == '__main__':
    import random

    @sqlite_udf(float64(float64, float64, float64))
    def normal(x, mu, sigma):
        c = 1.0 / (sigma * sqrt(2.0 * pi))
        return c * exp(-0.5 * ((x - mu) / sigma) ** 2.0)


    def oldnormal(x, mu, sigma):
        c = 1.0 / (sigma * sqrt(2.0 * pi))
        return c * exp(-0.5 * ((x - mu) / sigma) ** 2.0)

    con = sqlite3.connect(':memory:')
    con.execute('CREATE TABLE t (random_numbers DOUBLE PRECISION, random_strings VARCHAR)')

    random_numbers = [
        (random.random(), str(random.random())) for _ in range(50000)
    ]
    con.executemany('INSERT INTO t VALUES (?, ?)', random_numbers)

    # new way of registering C functions
    register_scalar_cfunc(con, normal)

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
