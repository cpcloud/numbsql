import ctypes
import ctypes.util
import sqlite3
import sys
from ctypes import (
    CFUNCTYPE,
    POINTER,
    c_char_p,
    c_double,
    c_int,
    c_int64,
    c_size_t,
    c_ssize_t,
    c_ubyte,
    c_void_p,
)
from typing import Any, Callable, Optional, Tuple

from llvmlite.ir.instructions import ExtractValue, Value
from llvmlite.llvmpy.core import Builder
from numba import cfunc, extending, float64, int32, int64, optional, types
from numba.core.base import BaseContext
from numba.core.typing.context import Context
from numba.core.typing.templates import Signature
from numba.types import string, void, voidptr

from .exceptions import MissingLibrary

SQLITE_OK = sqlite3.SQLITE_OK
SQLITE_VERSION = sqlite3.sqlite_version
SQLITE_UTF8 = 1
SQLITE_UTF16LE = 2
SQLITE_UTF16BE = 3
SQLITE_UTF16 = 4
SQLITE_NULL = 5
SQLITE_DETERMINISTIC = 0x000000800

sqlite3_path: Optional[str] = ctypes.util.find_library("sqlite3")
if sqlite3_path is None:  # pragma: no cover
    raise MissingLibrary("libsqlite3")

libsqlite3 = ctypes.cdll[sqlite3_path]

if sys.platform != "win32":
    libc_path: Optional[str] = ctypes.util.find_library("c")
    if libc_path is None:  # pragma: no cover
        raise MissingLibrary("libc")
    libc = ctypes.cdll[libc_path]
else:
    libc = ctypes.cdll.msvcrt

sqlite3_aggregate_context = libsqlite3.sqlite3_aggregate_context
sqlite3_aggregate_context.argtypes = c_void_p, c_int
sqlite3_aggregate_context.restype = c_void_p

sqlite3_user_data = libsqlite3.sqlite3_user_data
sqlite3_user_data.argtypes = (c_void_p,)
sqlite3_user_data.restype = c_void_p

sqlite3_libversion = libsqlite3.sqlite3_libversion
sqlite3_libversion.argtypes = ()
sqlite3_libversion.restype = c_char_p

sqlite3_result_double = libsqlite3.sqlite3_result_double
sqlite3_result_double.argtypes = c_void_p, c_double
sqlite3_result_double.restype = None

sqlite3_result_int64 = libsqlite3.sqlite3_result_int64
sqlite3_result_int64.argtypes = c_void_p, c_int64
sqlite3_result_int64.restype = None

sqlite3_result_int = libsqlite3.sqlite3_result_int
sqlite3_result_int.argtypes = c_void_p, c_int
sqlite3_result_int.restype = None

sqlite3_result_text64 = libsqlite3.sqlite3_result_text64
sqlite3_result_text64.argtypes = (
    # sqlite3_context
    c_void_p,
    # result string
    c_void_p,
    # the number of characters to consume from the result string, not including
    # the null byte
    c_size_t,
    # function pointer destructor for the string, always -1 for now, to tell
    # SQLite to make a copy
    #
    # this is c_ssize_t for now because numba cannot handle typing function
    # pointers as arguments
    c_ssize_t,
    # encoding
    c_ubyte,
)
sqlite3_result_text64.restype = None

sqlite3_result_null = libsqlite3.sqlite3_result_null
sqlite3_result_null.argtypes = (c_void_p,)
sqlite3_result_null.restype = None


@extending.intrinsic  # type: ignore[misc]
def extract_raw_unicode_data(
    typingctx: Context,
    raw_chars_type: types.UnicodeType,
) -> Tuple[
    Signature,
    Callable[[BaseContext, Builder, Signature, Tuple[Value]], ExtractValue],
]:
    """Pull out the data and length from a Numba unicode string."""
    if isinstance(raw_chars_type, types.UnicodeType):
        sig = types.Tuple((voidptr, int64))(raw_chars_type)

        def codegen(
            context: BaseContext,
            builder: Builder,
            signature: Signature,
            args: Tuple[Value],
        ) -> ExtractValue:
            # get the first and only argument
            (arg,) = args

            # access the data and length fields of the unicode type struct
            mgr = context.data_model_manager[raw_chars_type]
            data = mgr.get(builder, arg, "data")
            length = mgr.get(builder, arg, "length")

            return context.make_tuple(builder, signature.return_type, [data, length])

        return sig, codegen

    raise TypeError(f"Unable to extract raw data from type `{raw_chars_type}`")


@cfunc(void(voidptr, types.string))  # type: ignore[misc]
def sqlite3_result_text64_numba(ctx: c_void_p, chars: str) -> None:
    """Set the result of a UDF call to a string value.

    Notes
    -----
    SQLITE_TRANSIENT is used to ensure program correctness, but it's
    probably not very efficient as it tells SQLite to make copy of the
    input string.

    `sqlite3_result_text64` accepts a destructor, but unfortunately it takes
    only the string/blob data as its argument and not a custom structure. It's
    not totally clear how to get around this.

    Ideally we could incref the string when extracting the data, and decref it
    """
    (data, length) = extract_raw_unicode_data(chars)
    sqlite3_result_text64(
        ctx,
        data,
        # use the entire string, up to but not including the null byte
        length,
        # SQLITE_TRANSIENT, indicating that SQLite should copy
        # TODO: can we avoid a copy?
        -1,
        # encoding
        SQLITE_UTF8,
    )


@cfunc(void(voidptr, types.float64))  # type: ignore[misc]
def sqlite3_result_double_numba(ctx: c_void_p, value: float) -> None:
    sqlite3_result_double(ctx, value)


@cfunc(void(voidptr, types.int64))  # type: ignore[misc]
def sqlite3_result_int64_numba(ctx: c_void_p, value: int) -> None:
    sqlite3_result_int64(ctx, value)


@cfunc(void(voidptr, types.int32))  # type: ignore[misc]
def sqlite3_result_int_numba(ctx: c_void_p, value: int) -> None:
    sqlite3_result_int(ctx, value)


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

sqlite3_create_function_v2 = libsqlite3.sqlite3_create_function_v2
sqlite3_create_function_v2.restype = c_int
sqlite3_create_function_v2.argtypes = (
    c_void_p,
    c_char_p,
    c_int,
    c_int,
    c_void_p,
    scalarfunc,
    stepfunc,
    finalizefunc,
    destroyfunc,
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


SQLITE3_RESULT_SETTERS = {
    optional(float64): sqlite3_result_double_numba,
    optional(int64): sqlite3_result_int64_numba,
    optional(int32): sqlite3_result_int_numba,
    optional(string): sqlite3_result_text64_numba,
    float64: sqlite3_result_double_numba,
    int64: sqlite3_result_int64_numba,
    int32: sqlite3_result_int_numba,
    string: sqlite3_result_text64_numba,
}


c_ubyte_p = POINTER(c_ubyte)


def _get_value_method(
    typename: str,
    restype: Any,
) -> Any:
    method = getattr(libsqlite3, f"sqlite3_value_{typename}")
    method.argtypes = (c_void_p,)
    method.restype = restype
    return method


SQLITE3_VALUE_EXTRACTORS = {
    optional(float64): _get_value_method("double", c_double),
    optional(int64): _get_value_method("int64", c_int64),
    optional(int32): _get_value_method("int", c_int),
    optional(string): _get_value_method("text", c_ubyte_p),
    float64: _get_value_method("double", c_double),
    int64: _get_value_method("int64", c_int64),
    int32: _get_value_method("int", c_int),
    string: _get_value_method("text", c_ubyte_p),
}

sqlite3_value_type = libsqlite3.sqlite3_value_type
sqlite3_value_type.argtypes = (c_void_p,)
sqlite3_restype = c_int

_sqlite3_errmsg = libsqlite3.sqlite3_errmsg
_sqlite3_errmsg.argtypes = (c_void_p,)
_sqlite3_errmsg.restype = c_char_p

strlen = libc.strlen
strlen.argtypes = (c_ubyte_p,)
strlen.restype = c_size_t


class _RawConnection(ctypes.Structure):
    """Model a sqlite3.Connection object's first few fields.

    The purpose of this class is to expose a minimal interface
    for accessing the `db` field of `sqlite3.Connection` structures.

    These structures are technically private in the CPython API.
    """

    _fields_ = [
        # ob_refcnt and ob_type are what current make up PyObject_HEAD, the
        # structure that every Python object shares
        #
        # we list them here because they are necessary to inform ctypes of the
        # offset to the `db` field
        ("ob_refcnt", c_ssize_t),
        ("ob_type", c_void_p),
        ("db", c_void_p),
    ]


def get_sqlite_db(connection: sqlite3.Connection) -> c_void_p:
    """Get the address of the sqlite3* db instance in `connection`."""
    return _RawConnection.from_address(id(connection)).db


def sqlite3_errmsg(db: c_void_p) -> str:
    """Get the most recent error message from the SQLite database."""
    return _sqlite3_errmsg(db).decode("utf8")
