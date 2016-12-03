import sqlite3
import inspect
import ast
import time

# from ctypes import CDLL, c_void_p, c_double, c_int, c_int64, c_ubyte
# from ctypes.util import find_library

from numba import jit

from slumba.cyslumba import _SQLITE_NULL as SQLITE_NULL

from slumba.gen import CONVERTERS, RESULT_SETTERS, gen_scalar


def sqlite_udf(signature):
    def wrapped(func):
        jitted = jit(
            optional(signature.return_type)(*signature.args),
            nopython=True
        )(func)
        func_name = func.__name__
        scope = {func_name: jitted}
        scope.update(CONVERTERS)
        scope.update((f.__name__, f) for f in RESULT_SETTERS.values())
        final_func_name = '{}_scalar'.format(func_name)
        genmod = gen_scalar(jitted, final_func_name)
        mod = ast.fix_missing_locations(genmod)
        bytecode = compile(mod, __file__, 'exec')
        exec(bytecode, scope)
        return scope[final_func_name]
    return wrapped
