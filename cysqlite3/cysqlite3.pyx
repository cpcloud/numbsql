cdef extern from "math.h":
    double sin(double) nogil


from libc.stdio cimport printf


cdef extern from "sqlite3.h":
    int SQLITE_INTEGER
    int SQLITE_FLOAT
    int SQLITE_TEXT
    int SQLITE_BLOB

    int WORD_SIZE
    int SQLITE_UTF8
    int SQLITE_DETERMINISTIC

    ctypedef long long int sqlite3_int64

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

    int sqlite3_open(char *connection_string, sqlite3**) nogil
    int sqlite3_close(sqlite3 *db) nogil
    int sqlite3_create_function(
        sqlite3 *db,
        const char *zFunctionName,
        int nArg,
        int eTextRep,
        void *pApp,
        scalarfunc,
        stepfunc,
        finalfunc
    ) nogil
    int sqlite3_value_type(sqlite3_value*) nogil
    sqlite3_int64 sqlite3_value_int64(sqlite3_value*) nogil
    int sqlite3_value_int(sqlite3_value*) nogil
    double sqlite3_value_double(sqlite3_value*) nogil
    const unsigned char *sqlite3_value_text(sqlite3_value*) nogil
    const void *sqlite3_value_blob(sqlite3_value*) nogil
    void sqlite3_result_double(sqlite3_context*, double) nogil
    void sqlite3_free(void *) nogil
    int sqlite3_exec(
        sqlite3*,
        const char*,
        int (*)(void*, int, char**, char**),
        void *,
        char **
    ) nogil


cdef int print_result(void *value, int ncols, char **results, char **names):
    cdef:
        int i
        char *result
        char *name

    for i in range(ncols):
        result = results[i]
        if result == NULL:
            printf(b"NULL,")
        else:
            printf(b'%.3f,', result)
    printf(b'\n')
    return 0


cdef class sqlite3_connection:
    cdef sqlite3 *db

    def __cinit__(self, const char *connection_string):
        cdef int status = sqlite3_open(connection_string, &self.db)

    def __dealloc__(self):
        cdef int status = sqlite3_close(self.db)

    cpdef int execute(self, const char *sql):
        cdef:
            char *errmsg = NULL
            int value = 1

        return sqlite3_exec(self.db, sql, print_result, &value, &errmsg)


#cdef sqlvalue(sqlite3_value **values, Py_ssize_t i):
#    cdef:
#        sqlite3_value *value = values[i]
#        int typ = sqlite3_value_type(value)
#
#    if typ == SQLITE_INTEGER:
#        if WORD_SIZE == 64:
#            return sqlite3_value_int64(value)
#        else:
#            return sqlite3_value_int(value)
#    elif typ == SQLITE_FLOAT:
#        return sqlite3_value_double(value)
#    elif typ == SQLITE_TEXT:
#        return sqlite3_value_text(value)
#    elif typ == SQLITE_BLOB:
#        return bytes(<char *>sqlite3_value_blob(value))
#    else:
#        return None


cdef void mysin(sqlite3_context* context, int nargs, sqlite3_value **args):
    cdef:
        double value = sqlite3_value_double(args[0])
        double result = sin(value)
    print(result)
    sqlite3_result_double(context, result)
    return



cpdef int register(
    sqlite3_connection con,
    Py_ssize_t addr,
    const char *name,
    int nargs
):
    return sqlite3_create_function(
        con.db,
        name,
        nargs,
        SQLITE_UTF8 | SQLITE_DETERMINISTIC,
        NULL,
        mysin,
        NULL,
        NULL
    )
