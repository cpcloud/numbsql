from typing import Any, Callable

from numba import njit, cfunc
from numba.core.ccallback import CFunc
from numba.types import void, voidptr, intc, CPointer
from numba.core.typing import Signature

from slumba.sqlite import sqlite3_result_null
from slumba.numbaext import get_sqlite3_result_function, make_arg_tuple


def sqlite_udf(
    signature: Signature, nogil: bool = True, **njit_kwargs: Any
) -> Callable[[Callable], CFunc]:
    """Define a custom scalar function.

    Parameters
    ----------
    signature
        A numba signature.
    nogil
        Whether to release the GIL.
    nijt_kwargs
        Any additional keyword arguments supported by numba's jit decorator.

    """

    def wrapper(func: Callable) -> CFunc:
        compiled_func = njit(signature, nogil=nogil, **njit_kwargs)(func)

        @cfunc(void(voidptr, intc, CPointer(voidptr)))
        def scalar(ctx, argc, argv):  # pragma: no cover
            args = make_arg_tuple(compiled_func, argv)
            result = compiled_func(*args)
            if result is None:
                sqlite3_result_null(ctx)
            else:
                result_setter = get_sqlite3_result_function(result)
                result_setter(ctx, result)

        return scalar

    return wrapper
