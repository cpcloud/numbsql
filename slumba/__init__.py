import sqlite3
from typing import Callable

from numba.types import ClassType

from .aggregate import sqlite_udaf
from .cslumba import get_sqlite_db
from .scalar import sqlite_udf
from .sqlite import (
    SQLITE_DETERMINISTIC,
    SQLITE_OK,
    SQLITE_UTF8,
    destroyfunc,
    finalizefunc,
    inversefunc,
    scalarfunc,
    sqlite3_create_function,
    sqlite3_create_window_function,
    sqlite3_errmsg,
    stepfunc,
    valuefunc,
)

__all__ = (
    "create_function",
    "create_aggregate",
    "sqlite_udf",
    "sqlite_udaf",
)


def create_function(
    con: sqlite3.Connection,
    name: str,
    num_params: int,
    func: Callable,
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
            scalarfunc(getattr(func, "address")),
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
        Most functions are deterministic.

    """
    namebytes = name.encode("utf8")
    sqlite_db = get_sqlite_db(con)
    if hasattr(aggregate_class, "value") and hasattr(aggregate_class, "inverse"):
        rc = sqlite3_create_window_function(
            sqlite_db,
            namebytes,
            num_params,
            SQLITE_UTF8 | (SQLITE_DETERMINISTIC if deterministic else 0),
            None,
            stepfunc(aggregate_class.step.address),
            finalizefunc(aggregate_class.finalize.address),
            valuefunc(aggregate_class.value.address),
            inversefunc(aggregate_class.inverse.address),
            destroyfunc(0),
        )
    else:
        rc = sqlite3_create_function(
            sqlite_db,
            namebytes,
            num_params,
            SQLITE_UTF8 | (SQLITE_DETERMINISTIC if deterministic else 0),
            None,
            scalarfunc(0),
            stepfunc(aggregate_class.step.address),
            finalizefunc(aggregate_class.finalize.address),
        )
    if rc != SQLITE_OK:
        raise sqlite3.OperationalError(sqlite3_errmsg(sqlite_db))
