from libc.stdio cimport printf
from libc.stdint cimport int32_t, int64_t


cdef extern from "sqlite3.h":
    struct sqlite3:
        pass

    struct sqlite3_context:
        pass

    struct Mem:
        pass

    ctypedef Mem sqlite3_value

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


# cdef extern from "connection.h":
    # struct pysqlite_Connection:
        # pass


cpdef int register_function_pointer(pysqlite_Connection *con) except -1:
    return sqlite3_create_function(
        con.db,
        "foo",
        1,
        1,
        NULL,
        NULL,
        NULL,
        NULL,
    )
