cdef extern from "sqlite3.h":
    int SQLITE_UTF8

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
        const char *function_name,
        int number_of_arguments,
        int test_representation,
        void *application_data,
        scalarfunc scalar_function,
        stepfunc step_function,
        finalfunc final_function
    ) nogil


cdef extern from "pysqlite/connection.h":
    ctypedef class sqlite3.Connection [object pysqlite_Connection]:
        cdef sqlite3 *db


cpdef int register_function_pointer(
    Connection con,
    const char *name,
    int narg,
    Py_ssize_t address
) nogil except -1:
    with nogil:
        return sqlite3_create_function(
            con.db,
            name,
            narg,
            SQLITE_UTF8,
            NULL,
            <void (*)(sqlite3_context*, int, sqlite3_value**)> address,
            NULL,
            NULL,
        )
