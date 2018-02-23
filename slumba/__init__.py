from .cyslumba import register_scalar_function, register_aggregate_function
from . import gen  # noqa: F401
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


def create_function(con, name, num_params, func):
    """Register a UDF with name `name` with the SQLite connection `con`.

    Parameters
    ----------
    con : sqlite3.Connection
    name : str
    num_params : int
    func : cfunc
    """
    register_scalar_function(
        con, name.encode('utf8'), num_params, func.address
    )


def create_aggregate(con, name, num_params, aggregate_class):
    """Register an aggregate named `name` with the SQLite connection `con`.

    Parameters
    ----------
    con : sqlite3.Connection
    name : str
    num_params : int
    aggregate_class : JitClass
       This class must be decorated with @sqlite_udaf for this function to work
    """
    register_aggregate_function(
        con,
        name.encode('utf8'),
        num_params,
        aggregate_class.step.address,
        aggregate_class.finalize.address,
    )
