from numba import njit, cfunc
from numba.types import void, voidptr, intc, CPointer

from slumba.sqlite import sqlite3_result_null, CONVERTERS
from slumba.numbaext import get_sqlite3_result_function, make_arg_tuple


sqlite3_value_type = CONVERTERS['sqlite3_value_type']


def sqlite_udf(signature):
    """Generate a SQLite compatible cfunc wrapper for a numba compiled function

    Parameters
    ----------
    signature : numba.Signature
    """
    def wrapper(func):
        compiled_func = njit(signature.return_type(
            *signature.args), nogil=True)(func)

        @cfunc(void(voidptr, intc, CPointer(voidptr)))
        def scalar(ctx, argc, argv):
            result = compiled_func(*make_arg_tuple(compiled_func, argv))
            if result is None:
                sqlite3_result_null(ctx)
            else:
                result_setter = get_sqlite3_result_function(result)
                result_setter(ctx, result)
        return scalar
    return wrapper
