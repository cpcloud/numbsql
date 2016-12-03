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
        func_name = func.__name__
        scope = {func_name: jitted}
        genmod = gen_scalar(jitted)
        mod = ast.fix_missing_locations(genmod)
        bytecode = compile(mod, __file__, 'exec')
        exec(bytecode, scope)
        return SQLiteUDF(scope['wrapper'], func)
    return wrapped
