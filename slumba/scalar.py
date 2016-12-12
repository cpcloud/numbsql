import ast

from numba import njit, optional

from slumba.gen import (
    CONVERTERS, RESULT_SETTERS, gen_scalar, sqlite3_result_null
)
from slumba.cyslumba import _SQLITE_NULL as SQLITE_NULL


def sqlite_udf(signature):
    """Generate a SQLite compatible cfunc wrapper for a numba compiled function

    Parameters
    ----------
    signature : numba.Signature
    """

    def wrapped(func):
        jitted_func = njit(signature)(func)
        func_name = func.__name__
        scope = {
            func_name: jitted_func,
            'SQLITE_NULL': SQLITE_NULL,
            'sqlite3_result_null': sqlite3_result_null,
        }
        scope.update(CONVERTERS)
        scope.update((f.__name__, f) for f in RESULT_SETTERS.values())
        final_func_name = '{}_scalar'.format(func_name)
        genmod = gen_scalar(jitted_func, final_func_name)
        mod = ast.fix_missing_locations(genmod)
        bytecode = compile(mod, __file__, 'exec')
        exec(bytecode, scope)
        return scope[final_func_name]
    return wrapped
