from pprint import pprint
import sqlite3
import functools

import ast

from ctypes import CDLL, c_void_p, c_double, c_int, c_int64, c_ubyte
from ctypes.util import find_library

from math import sqrt, exp, pi
from pprint import pprint

from numba import cfunc, int64, float64, jit, i1, f8, i8, void, int32

import pandas as pd

from gen import *


# TODO: think about how to handle commented out types below

class SQLiteUDF(object):
    __slots__ = 'wrapper',

    def __init__(self, wrapper):
        self.wrapper = wrapper

    @property
    def address(self):
        return self.wrapper.address


def sqlite_udf(signature):
    def wrapped(func):
        jitted = functools.wraps(func)(jit(signature)(func))
        assert func.__name__ not in globals(), \
            'found previously defined function {} in globals()'.format(
                func.__name__
            )
        globals()[func.__name__] = jitted
        genmod = gen_def(jitted)
        mod = ast.fix_missing_locations(genmod)
        bytecode = compile(mod, __file__, 'exec')
        exec(bytecode)
        return SQLiteUDF(locals()['wrapper'])
    return wrapped


@sqlite_udf(float64(float64, float64, float64))
def normal2(x, mu, sigma):
    c = 1.0 / (sigma * sqrt(2.0 * pi))
    return c * exp(-0.5 * ((x - mu) / sigma) ** 2.0)


def oldnormal(x, mu, sigma):
    c = 1.0 / (sigma * sqrt(2.0 * pi))
    return c * exp(-0.5 * ((x - mu) / sigma) ** 2.0)


if __name__ == '__main__':
    from slumba import register_function_pointer
    con = sqlite3.connect('/home/phillip/data/ibis-testing-data/ibis_testing.db')

    # new way of registering C functions
    register_function_pointer(con, 'normal'.encode('utf8'), 3, normal2.address)

    # old way
    con.create_function('oldnormal', 3, oldnormal)
    query1 = 'select normal(double_col, 0.0, 1.0) as sine from functional_alltypes'
    query2 = 'select oldnormal(double_col, 0.0, 1.0) as oldsine from functional_alltypes'
    result1 = pd.DataFrame(list(con.execute(query1))).loc[:, 0]
    result2 = pd.DataFrame(list(con.execute(query2))).loc[:, 0]
    print(result1.eq(result2).all())
