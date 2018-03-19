#include "Python.h"
#include "sqlite3.h"

/* We assume the pysqlite_Connection object's first non PyObject member is
 * the sqlite3* database */
typedef struct Connection {
    PyObject_HEAD
    sqlite3 *db;
} Connection;

typedef void (*scalarfunc)(sqlite3_context*, int, sqlite3_value**);
typedef scalarfunc stepfunc;
typedef void (*finalizefunc)(sqlite3_context*);

static PyObject *
register_scalar_function(PyObject *self, PyObject *args)
{
    PyObject* con = NULL;
    const char* name = NULL;
    int narg;
    Py_ssize_t address;

    if (!PyArg_ParseTuple(args, "Osin", &con, &name, &narg, &address)) {
        return NULL;
    }

    if (narg < -1) {
	PyErr_SetString(
	    PyExc_ValueError,
	    "narg < -1, must be between -1 and SQLITE_LIMIT_FUNCTION_ARG");
	return NULL;
    }

    if (narg > SQLITE_LIMIT_FUNCTION_ARG) {
	PyErr_SetString(PyExc_ValueError, "narg > SQLITE_LIMIT_FUNCTION_ARG");
	return NULL;
    }

    if (address <= 0) {
	PyErr_SetString(
		PyExc_ValueError,
		"scalar function pointer address must be greater than 0");
	return NULL;
    }

    sqlite3* db = ((Connection*) con)->db;

    int result = sqlite3_create_function(
        db,
        name,
        narg,
        SQLITE_UTF8,
        NULL,
        (scalarfunc) address,
        NULL,
        NULL
    );

    if (result != SQLITE_OK) {
	PyErr_SetString(PyExc_RuntimeError, sqlite3_errmsg(db));
	return NULL;
    }

    Py_RETURN_NONE;
}

static PyObject *
register_aggregate_function(PyObject *self, PyObject *args)
{
    PyObject* con = NULL;
    const char* name = NULL;
    int narg;

    /* step and finalize are function pointer addresses */
    Py_ssize_t step;
    Py_ssize_t finalize;

    if (!PyArg_ParseTuple(
	    args, "Osinn", &con, &name, &narg, &step, &finalize)) {
        return NULL;
    }

    if (narg < -1) {
	PyErr_SetString(
	    PyExc_ValueError,
	    "narg < -1, must be between -1 and SQLITE_LIMIT_FUNCTION_ARG");
	return NULL;
    }

    if (narg > SQLITE_LIMIT_FUNCTION_ARG) {
	PyErr_SetString(PyExc_ValueError, "narg > SQLITE_LIMIT_FUNCTION_ARG");
	return NULL;
    }

    if (step <= 0) {
	PyErr_SetString(
		PyExc_ValueError,
		"step function pointer address must be greater than 0");
	return NULL;
    }

    if (finalize <= 0) {
	PyErr_SetString(
		PyExc_ValueError,
		"step function pointer address must be greater than 0");
	return NULL;
    }

    sqlite3* db = ((Connection*) con)->db;

    int result = sqlite3_create_function(
        db,
        name,
        narg,
        SQLITE_UTF8,
        NULL,
        NULL,
	(stepfunc) step,
	(finalizefunc) finalize
    );

    if (result != SQLITE_OK) {
	PyErr_SetString(PyExc_RuntimeError, sqlite3_errmsg(db));
	return NULL;
    }

    Py_RETURN_NONE;
}

static PyMethodDef cslumba_methods[] = {
    {"register_scalar_function",
	(PyCFunction) register_scalar_function, METH_VARARGS,
     "Register a numba generated SQLite user-defined function"},
    {"register_aggregate_function",
	(PyCFunction) register_aggregate_function, METH_VARARGS,
     "Register a numba generated SQLite user-defined aggregate function"},
    {NULL, NULL, 0, NULL}   /* sentinel */
};

static struct PyModuleDef cslumbamodule = {
    PyModuleDef_HEAD_INIT,
    "cslumba",
    NULL,
    -1,
    cslumba_methods,
};

PyMODINIT_FUNC
PyInit_cslumba(void)
{
    PyObject* module = PyModule_Create(&cslumbamodule);
    if (PyModule_AddIntMacro(module, SQLITE_NULL) == -1) {
	PyErr_SetString(
	    PyExc_RuntimeError, "Unable to add SQLITE_NULL constant");
	return NULL;
    }
    return module;
}
