from libc.stdio cimport printf
from libc.stdint cimport int32_t, int64_t


cdef extern from "sqlite3.h":
    ctypedef struct sqlite3:
        pass

    ctypedef struct sqlite3_context:
        pass

    ctypedef struct sqlite3_value:
        pass

    ctypedef void (*scalarfunc)(sqlite3_context*, int, sqlite3_value**)
    ctypedef void (*stepfunc)(sqlite3_context*, int, sqlite3_value**)
    ctypedef void (*finalfunc)(sqlite3_context*)

    int sqlite3_create_function(
        sqlite3 *db,
        const char *zFunctionName,
        int nArg,
        int eTextRep,
        void *pApp,
        scalarfunc,
        stepfunc,
        finalfunc
    )


cdef extern from "connection.h":
    ctypedef class sqlite3.Connection [object pysqlite_Connection]:
        cdef sqlite3 *db


cpdef int register_function_pointer(
    Connection con,
    const char *name,
    int narg,
    Py_ssize_t address
) except -1:
    return sqlite3_create_function(
        con.db,
        name,
        narg,
        1, # SQLITE_UTF8,
        NULL,
        <void (*)(sqlite3_context*, int, sqlite3_value**)> address,
        NULL,
        NULL,
    )
