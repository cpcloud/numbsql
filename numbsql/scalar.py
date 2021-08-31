import functools
import inspect
from typing import Any, Callable, Optional

from numba import cfunc, njit
from numba.core.ccallback import CFunc
from numba.extending import as_numba_type
from numba.types import CPointer, intc, void, voidptr

from .numbaext import make_arg_tuple, sqlite3_result
from .sqlite import sqlite3_result_null


def sqlite_udf(
    func: Optional[Callable[..., Any]] = None,
    nogil: bool = True,
    **njit_kwargs: Any,
) -> Callable[[Callable[..., Any]], CFunc]:
    """Define a custom scalar function.

    Parameters
    ----------
    func
        A user-defined function.
    nogil
        Whether to release the GIL.
    njit_kwargs
        Any additional keyword arguments supported by numba's `njit` decorator.

    Examples
    --------
    >>> import sqlite3
    >>> from numbsql import sqlite_udf
    >>> from typing import Optional
    >>> @sqlite_udf
    ... def add_one(value: Optional[int]) -> Optional[int]:
    ...     return value + 1 if value is not None else None
    ...
    >>> add_one(1)
    2
    >>> add_one(None) is None
    True

    """
    if func is None:
        return functools.partial(sqlite_udf, nogil=nogil, **njit_kwargs)

    python_signature = inspect.signature(func)
    return_type = as_numba_type(python_signature.return_annotation)
    argument_types = (
        as_numba_type(param.annotation)
        for param in python_signature.parameters.values()
    )
    numba_signature = return_type(*argument_types)
    compiled_func = njit(numba_signature, nogil=nogil, **njit_kwargs)(func)

    @cfunc(void(voidptr, intc, CPointer(voidptr)))  # type: ignore[misc]
    def scalar(  # type: ignore[no-untyped-def]
        ctx, argc: int, argv
    ):  # pragma: no cover
        args = make_arg_tuple(compiled_func, argv)
        result = compiled_func(*args)
        if result is None:
            sqlite3_result_null(ctx)
        else:
            sqlite3_result(ctx, result)

    setattr(func, "scalar", scalar)

    return func
