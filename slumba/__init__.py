import sqlite3
from ctypes import byref, c_bool, py_object, pythonapi
from typing import Any

from numba import cfunc
from numba.core.ccallback import CFunc
from numba.types import ClassType, void, voidptr

from .aggregate import sqlite_udaf
from .exceptions import MissingAggregateMethod
from .numbaext import safe_decref
from .scalar import sqlite_udf
from .sqlite import (
    SQLITE_DETERMINISTIC,
    SQLITE_OK,
    SQLITE_UTF8,
    destroyfunc,
    finalizefunc,
    get_sqlite_db,
    inversefunc,
    scalarfunc,
    sqlite3_create_function,
    sqlite3_create_function_v2,
    sqlite3_create_window_function,
    sqlite3_errmsg,
    stepfunc,
    valuefunc,
)

_incref = pythonapi.Py_IncRef
_incref.argtypes = (py_object,)
_incref.restype = None


@cfunc(void(voidptr))  # type: ignore[misc]
def _safe_decref(obj: Any) -> None:
    safe_decref(obj)


__all__ = (
    "create_function",
    "create_aggregate",
    "sqlite_udf",
    "sqlite_udaf",
)

try:
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata  # type: ignore

__version__ = importlib_metadata.version(__name__)

del importlib_metadata


def create_function(
    con: sqlite3.Connection,
    name: str,
    num_params: int,
    func: CFunc,
    deterministic: bool = False,
) -> None:
    """Register a UDF with name `name` with the SQLite connection `con`.

    Parameters
    ----------
    con : sqlite3.Connection
        A connection to a SQLite database
    name : str
        The name of this function in the database, given as a UTF-8 encoded
        string
    num_params : int
        The number of arguments this function takes
    func : cfunc
        The sqlite_udf-decorated function to register
    deterministic : bool
        True if this function returns the same output given the same input.
        Most functions are deterministic.

    """
    sqlite_db = get_sqlite_db(con)
    if (
        sqlite3_create_function(
            sqlite_db,
            name.encode("utf8"),
            num_params,
            SQLITE_UTF8 | (SQLITE_DETERMINISTIC if deterministic else 0),
            None,
            scalarfunc(func.address),
            stepfunc(0),
            finalizefunc(0),
        )
        != SQLITE_OK
    ):
        raise sqlite3.OperationalError(sqlite3_errmsg(sqlite_db))


def create_aggregate(
    con: sqlite3.Connection,
    name: str,
    num_params: int,
    agg_class: ClassType,
    deterministic: bool = False,
) -> None:
    """Register an aggregate named `name` with the SQLite connection `con`.

    Parameters
    ----------
    con : sqlite3.Connection
        A connection to a SQLite database
    name : str
        The name of this function in the database, given as a UTF-8 encoded
        string
    num_params : int
        The number of arguments this function takes
    aggregate_class : JitClass
       This class must be decorated with @sqlite_udaf for this function to
       work. If this class has `value` and `inverse` attributes, it will be
       registered as a window function. Window functions can also be used as
       standard aggregate functions.
    deterministic : bool
        True if this function returns the same output given the same input.
        Most functions are deterministic. `RANDOM()` is a notable exception.

    """
    try:
        step_method = agg_class.step
    except AttributeError as e:
        raise MissingAggregateMethod(agg_class, "step") from e
    else:
        step_address = step_method.address

    try:
        finalize_method = agg_class.finalize
    except AttributeError as e:
        raise MissingAggregateMethod(agg_class, "finalize") from e
    else:
        finalize_address = finalize_method.address

    value_address = getattr(getattr(agg_class, "value", None), "address", None)
    inverse_address = getattr(getattr(agg_class, "inverse", None), "address", None)

    safe_decref_address = _safe_decref.address

    namebytes = name.encode("utf8")
    sqlite_db = get_sqlite_db(con)
    flags = SQLITE_UTF8 | (SQLITE_DETERMINISTIC if deterministic else 0)

    # XXX: is_initialized is how we track whether an aggregate's constructor
    # has been called
    #
    # we only want to call the constructor once for every invocation of the
    # UDAF, on the first call to step
    #
    # when finalize is called, we set `is_initialized` to false
    #
    # a lifetime problem arises: we creating `is_initialized` in this function
    # which _registers_ the UDAF, but the variable itself needs to live for the
    # lifetime of the database connection
    #
    # unfortunately, python cannot magically know _not_ to decref this value
    # when the function exits, which will (likely, but guaranteed to) cause the
    # destructor for `is_initialized` to called.
    #
    # This leeds to a segmentation fault.
    #
    # We solve this problem by increasing the lifetime of the value by incrementing
    # the reference count of `is_initialized` here, and then using SQLite UDAFs'
    # destructor-callback-on-database-close mechanism to decrement the
    # reference count
    #
    # That way, there's no memory leak _and_ the lifetime of the value lives as
    # long as the database connection is valid
    is_initialized = byref(c_bool(False))
    _incref(is_initialized)

    try:
        if value_address is not None and inverse_address is not None:
            rc = sqlite3_create_window_function(
                sqlite_db,
                namebytes,
                num_params,
                flags,
                is_initialized,
                stepfunc(step_address),
                finalizefunc(finalize_address),
                valuefunc(value_address),
                inversefunc(inverse_address),
                destroyfunc(safe_decref_address),
            )
        else:
            rc = sqlite3_create_function_v2(
                sqlite_db,
                namebytes,
                num_params,
                flags,
                is_initialized,
                scalarfunc(0),
                stepfunc(step_address),
                finalizefunc(finalize_address),
                destroyfunc(safe_decref_address),
            )
        if rc != SQLITE_OK:
            raise sqlite3.OperationalError(sqlite3_errmsg(sqlite_db))
    except Exception:
        # catch every exception so that we can decrement the reference count
        # of `is_initialized`, and prevent a memory leak
        _safe_decref(is_initialized)
        raise
