cdef extern from "sqlite3.h":
    int SQLITE_UTF8
    int SQLITE_DETERMINISTIC
    int SQLITE_LIMIT_FUNCTION_ARG
    int SQLITE_OK
    int SQLITE_INTEGER
    int SQLITE_FLOAT
    int SQLITE_TEXT
    int SQLITE_BLOB
    int SQLITE_NULL

    ctypedef struct sqlite3:
        pass

    ctypedef struct sqlite3_context:
        pass

    ctypedef struct sqlite3_value:
        pass

    int sqlite3_create_function(
        sqlite3 *db,
        const char *function_name,
        int number_of_arguments,
        int text_representation,
        void *application_data,
        void (*scalar_function)(sqlite3_context*, int, sqlite3_value**),
        void (*step_function)(sqlite3_context*, int, sqlite3_value**),
        void (*final_function)(sqlite3_context*)
    )

    const char *sqlite3_errmsg(sqlite3 *db)


cdef extern from "pysqlite/connection.h":
    ctypedef class sqlite3.Connection [object pysqlite_Connection]:
        cdef sqlite3 *db


cpdef object register_scalar_function(
    Connection con,
    const char *name,
    int narg,
    Py_ssize_t address
):
    assert -1 <= narg <= SQLITE_LIMIT_FUNCTION_ARG, \
        'Number of arguments must be between -1 and {:d}'.format(
            SQLITE_LIMIT_FUNCTION_ARG
        )
    assert address > 0, 'Invalid value for address, must be greater than 0'

    cdef int result = sqlite3_create_function(
        con.db,
        name,
        narg,
        SQLITE_UTF8,
        NULL,
        # for some reason Cython fails when using the `scalarfunc` type
        <void (*)(sqlite3_context*, int, sqlite3_value**)> address,
        NULL,
        NULL,
    )

    if result != SQLITE_OK:
        raise RuntimeError(sqlite3_errmsg(con.db))


cpdef object register_aggregate_function(
    Connection con,
    const char *name,
    int narg,
    Py_ssize_t step_address,
    Py_ssize_t finalize_address
):
    assert -1 <= narg <= SQLITE_LIMIT_FUNCTION_ARG, \
        'Number of arguments must be between -1 and {:d}'.format(
            SQLITE_LIMIT_FUNCTION_ARG
        )
    assert step_address > 0, \
        'Invalid value for step_address, must be greater than 0'
    assert finalize_address > 0, \
        'Invalid value for finalize_address, must be greater than 0'

    cdef int result = sqlite3_create_function(
        con.db,
        name,
        narg,
        SQLITE_UTF8,
        NULL,
        NULL,
        <void (*)(sqlite3_context*, int, sqlite3_value**)> step_address,
        <void (*)(sqlite3_context*)> finalize_address,
    )

    if result != SQLITE_OK:
        raise RuntimeError(sqlite3_errmsg(con.db))


_SQLITE_INTEGER = SQLITE_INTEGER
_SQLITE_FLOAT = SQLITE_FLOAT
_SQLITE_TEXT = SQLITE_TEXT
_SQLITE_BLOB = SQLITE_BLOB
_SQLITE_NULL = SQLITE_NULL
