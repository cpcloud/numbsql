import sqlite3
from ctypes import byref, c_bool, py_object, pythonapi
from typing import Any

from numba import cfunc
from numba.core.ccallback import CFunc
from numba.types import ClassType, void, voidptr

from .aggregate import sqlite_udaf
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
    aggregate_class: ClassType,
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
    namebytes = name.encode("utf8")
    sqlite_db = get_sqlite_db(con)
    flags = SQLITE_UTF8 | (SQLITE_DETERMINISTIC if deterministic else 0)

    # XXX: this is really really gross, maybe there's a better way
    # we use a boolean to track whether a constructor has been called, because
    # we only want to call it once for every invocation of the UDAF, on the first call
    #
    # unfortunately, python cannot magically know _not_ to decref this value,
    # and then subsequently call (likely, but not guaranteed) the object's
    # destructor and cause a segmentation fault
    #
    # We work around this by increasing the lifetime of the value by incref-ing
    # it, and then decref-ing it when the program exits
    init = byref(c_bool(False))
    _incref(init)

    if hasattr(aggregate_class, "value") and hasattr(aggregate_class, "inverse"):
        rc = sqlite3_create_window_function(
            sqlite_db,
            namebytes,
            num_params,
            flags,
            # XXX: byref is necessary here because byref returns a new reference
            # whereas ctypes.pointer doesn't, and is likely to be destroyed when
            # this function returns
            init,
            stepfunc(aggregate_class.step.address),
            finalizefunc(aggregate_class.finalize.address),
            valuefunc(aggregate_class.value.address),
            inversefunc(aggregate_class.inverse.address),
            destroyfunc(_safe_decref.address),
        )
    else:
        rc = sqlite3_create_function_v2(
            sqlite_db,
            namebytes,
            num_params,
            flags,
            init,
            scalarfunc(0),
            stepfunc(aggregate_class.step.address),
            finalizefunc(aggregate_class.finalize.address),
            destroyfunc(_safe_decref.address),
        )
    if rc != SQLITE_OK:
        raise sqlite3.OperationalError(sqlite3_errmsg(sqlite_db))
