from .cslumba import get_sqlite_db, SQLITE_DETERMINISTIC, SQLITE_UTF8
from .sqlite import (
    sqlite3_create_function,
    scalarfunc, stepfunc, finalizefunc, valuefunc, inversefunc)
try:
    from .sqlite import sqlite3_create_window_function
except ImportError:
    pass
from .scalar import sqlite_udf
from .aggregate import sqlite_udaf
from ._version import get_versions

__all__ = [
    'register_scalar_function',
    'register_aggregate_function',
    'sqlite_udf',
    'sqlite_udaf',
]

__version__ = get_versions()['version']
del get_versions


def create_function(con, name, num_params, func, deterministic=False):
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
    """
    sqlite3_create_function(
        get_sqlite_db(con),
        name.encode('utf8'),
        num_params,
        SQLITE_UTF8 | (SQLITE_DETERMINISTIC if deterministic else 0),
        None,
        scalarfunc(func.address),
        stepfunc(0),
        finalizefunc(0),
    )


def create_aggregate(
    con, name, num_params, aggregate_class, deterministic=False
):
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
        True if this function returns the same output given the same input
    """
    namebytes = name.encode('utf8')
    if hasattr(aggregate_class, 'value') and hasattr(
        aggregate_class, 'inverse'
    ):
        sqlite3_create_window_function(
            get_sqlite_db(con),
            namebytes,
            num_params,
            SQLITE_UTF8 | (SQLITE_DETERMINISTIC if deterministic else 0),
            None,
            stepfunc(aggregate_class.step.address),
            finalizefunc(aggregate_class.finalize.address),
            valuefunc(aggregate_class.value.address),
            inversefunc(aggregate_class.inverse.address),
        )
    else:
        sqlite3_create_function(
            get_sqlite_db(con),
            namebytes,
            num_params,
            SQLITE_UTF8 | (SQLITE_DETERMINISTIC if deterministic else 0),
            None,
            scalarfunc(0),
            stepfunc(aggregate_class.step.address),
            finalizefunc(aggregate_class.finalize.address),
        )
