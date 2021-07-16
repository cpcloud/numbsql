from ctypes import (
    CDLL,
    CFUNCTYPE,
    POINTER,
    c_char_p,
    c_double,
    c_int,
    c_int64,
    c_void_p,
)
from ctypes.util import find_library
from typing import Optional

from numba import float64, int32, int64, optional

from .cslumba import SQLITE_DETERMINISTIC, SQLITE_OK, SQLITE_UTF8  # noqa: F401

sqlite3_path: Optional[str] = find_library("sqlite3")
if sqlite3_path is None:  # pragma: no cover
    raise RuntimeError("Unable to find sqlite3 library")

libsqlite3 = CDLL(sqlite3_path)

sqlite3_aggregate_context = libsqlite3.sqlite3_aggregate_context
sqlite3_aggregate_context.argtypes = c_void_p, c_int
sqlite3_aggregate_context.restype = c_void_p

sqlite3_result_double = libsqlite3.sqlite3_result_double
sqlite3_result_int64 = libsqlite3.sqlite3_result_int64
sqlite3_result_int = libsqlite3.sqlite3_result_int
sqlite3_result_null = libsqlite3.sqlite3_result_null

sqlite3_result_double.argtypes = c_void_p, c_double
sqlite3_result_double.restype = None

sqlite3_result_int64.argtypes = c_void_p, c_int64
sqlite3_result_int64.restype = None

sqlite3_result_int.argtypes = c_void_p, c_int
sqlite3_result_int.restype = None

sqlite3_result_null.argtypes = (c_void_p,)
sqlite3_result_null.restype = None

scalarfunc = CFUNCTYPE(None, c_void_p, c_int, POINTER(c_void_p))
stepfunc = CFUNCTYPE(None, c_void_p, c_int, POINTER(c_void_p))
finalizefunc = CFUNCTYPE(None, c_void_p)
valuefunc = CFUNCTYPE(None, c_void_p)
inversefunc = CFUNCTYPE(None, c_void_p, c_int, POINTER(c_void_p))

destroyfunc = CFUNCTYPE(None, c_void_p)

sqlite3_create_function = libsqlite3.sqlite3_create_function
sqlite3_create_function.restype = c_int
sqlite3_create_function.argtypes = (
    c_void_p,
    c_char_p,
    c_int,
    c_int,
    c_void_p,
    scalarfunc,
    stepfunc,
    finalizefunc,
)

try:
    sqlite3_create_window_function = libsqlite3.sqlite3_create_window_function
except AttributeError:  # pragma: no cover
    pass
else:
    sqlite3_create_window_function.restype = c_int
    sqlite3_create_window_function.argtypes = (
        c_void_p,
        c_char_p,
        c_int,
        c_int,
        c_void_p,
        stepfunc,
        finalizefunc,
        valuefunc,
        inversefunc,
        destroyfunc,
    )


RESULT_SETTERS = {
    optional(float64): sqlite3_result_double,
    optional(int64): sqlite3_result_int64,
    optional(int32): sqlite3_result_int,
    float64: sqlite3_result_double,
    int64: sqlite3_result_int64,
    int32: sqlite3_result_int,
}


value_methods = {
    "double": c_double,
    "int": c_int,
    "int64": c_int64,
    "type": c_int,
}


def add_value_method(typename: str, restype):
    method = getattr(libsqlite3, f"sqlite3_value_{typename}")
    method.argtypes = (c_void_p,)
    method.restype = restype
    return method


VALUE_EXTRACTORS = {
    optional(float64): add_value_method("double", c_double),
    optional(int64): add_value_method("int64", c_int64),
    optional(int32): add_value_method("int", c_int),
    float64: add_value_method("double", c_double),
    int64: add_value_method("int64", c_int64),
    int32: add_value_method("int", c_int),
}

sqlite3_value_type = libsqlite3.sqlite3_value_type
sqlite3_value_type.argtypes = (c_void_p,)
sqlite3_restype = c_int

_sqlite3_errmsg = libsqlite3.sqlite3_errmsg
_sqlite3_errmsg.argtypes = (c_void_p,)
_sqlite3_errmsg.restype = c_char_p


def sqlite3_errmsg(db):
    return _sqlite3_errmsg(db).decode("utf8")
