#include "Python.h"
#include "sqlite3.h"

/* Assume the pysqlite_Connection object's first non-PyObject member is the
 * sqlite3 database */
typedef struct
{
  PyObject_HEAD sqlite3* db;
} Connection;

typedef void (*scalarfunc)(sqlite3_context* ctx,
                           int narg,
                           sqlite3_value** arguments);
typedef void (*stepfunc)(sqlite3_context* ctx,
                         int narg,
                         sqlite3_value** arguments);
typedef void (*finalizefunc)(sqlite3_context* ctx);
typedef void (*valuefunc)(sqlite3_context* ctx);
typedef void (*inversefunc)(sqlite3_context* ctx,
                            int narg,
                            sqlite3_value** arguments);

static int
check_function_pointer_address(Py_ssize_t address, const char* name)
{
  if (address <= 0) {
    (void)PyErr_Format(PyExc_ValueError,
                       "%s function pointer address must be greater than 0",
                       name);
    return 0;
  }
  return 1;
}

static PyObject*
register_scalar_function(PyObject* self, PyObject* args)
{
  PyObject* con = NULL;
  const char* name = NULL;
  int narg;
  Py_ssize_t address;

  if (!PyArg_ParseTuple(args, "Oyin", &con, &name, &narg, &address)) {
    return NULL;
  }

  Py_XINCREF(con);

  if (narg < -1) {
    PyErr_SetString(
      PyExc_ValueError,
      "narg < -1, must be between -1 and SQLITE_LIMIT_FUNCTION_ARG");
    goto error;
  }

  if (narg > SQLITE_LIMIT_FUNCTION_ARG) {
    PyErr_SetString(PyExc_ValueError, "narg > SQLITE_LIMIT_FUNCTION_ARG");
    goto error;
  }

  if (!check_function_pointer_address(address, "scalar")) {
    goto error;
  }

  sqlite3* db = ((Connection*)con)->db;

  int result = sqlite3_create_function(
    db, name, narg, SQLITE_UTF8, NULL, (scalarfunc)address, NULL, NULL);

  if (result != SQLITE_OK) {
    PyErr_SetString(PyExc_RuntimeError, sqlite3_errmsg(db));
    goto error;
  }

  Py_XDECREF(con);
  Py_RETURN_NONE;

error:
  Py_XDECREF(con);
  return NULL;
}

static PyObject*
register_aggregate_function(PyObject* self, PyObject* args)
{
  PyObject* con = NULL;
  const char* name = NULL;
  int narg;

  /* step and finalize are function pointer addresses */
  Py_ssize_t step;
  Py_ssize_t finalize;

  if (!PyArg_ParseTuple(args, "Oyinn", &con, &name, &narg, &step, &finalize)) {
    return NULL;
  }

  Py_XINCREF(con);

  if (narg < -1) {
    PyErr_SetString(
      PyExc_ValueError,
      "narg < -1, must be between -1 and SQLITE_LIMIT_FUNCTION_ARG");
    goto error;
  }

  if (narg > SQLITE_LIMIT_FUNCTION_ARG) {
    PyErr_SetString(PyExc_ValueError, "narg > SQLITE_LIMIT_FUNCTION_ARG");
    goto error;
  }

  if (!check_function_pointer_address(step, "step")) {
    goto error;
  }

  if (!check_function_pointer_address(finalize, "finalize")) {
    goto error;
  }

  sqlite3* db = ((Connection*)con)->db;

  int result = sqlite3_create_function(db,
                                       name,
                                       narg,
                                       SQLITE_UTF8,
                                       NULL,
                                       NULL,
                                       (stepfunc)step,
                                       (finalizefunc)finalize);

  if (result != SQLITE_OK) {
    PyErr_SetString(PyExc_RuntimeError, sqlite3_errmsg(db));
    goto error;
  }

  Py_XDECREF(con);
  Py_RETURN_NONE;

error:
  Py_XDECREF(con);
  return NULL;
}

#if SQLITE_VERSION_NUMBER >= 3025000
static PyObject*
register_window_function(PyObject* self, PyObject* args)
{
  PyObject* con = NULL;
  const char* name = NULL;
  int narg;

  /* step, finalize, value and inverse are function pointer addresses */
  Py_ssize_t step;
  Py_ssize_t finalize;
  Py_ssize_t value;
  Py_ssize_t inverse;

  if (!PyArg_ParseTuple(args,
                        "Oyinnnn",
                        &con,
                        &name,
                        &narg,
                        &step,
                        &finalize,
                        &value,
                        &inverse)) {
    return NULL;
  }

  Py_XINCREF(con);

  if (narg < -1) {
    PyErr_SetString(
      PyExc_ValueError,
      "narg < -1, must be between -1 and SQLITE_LIMIT_FUNCTION_ARG");
    goto error;
  }

  if (narg > SQLITE_LIMIT_FUNCTION_ARG) {
    PyErr_SetString(PyExc_ValueError, "narg > SQLITE_LIMIT_FUNCTION_ARG");
    goto error;
  }

  if (!check_function_pointer_address(step, "step")) {
    goto error;
  }

  if (!check_function_pointer_address(finalize, "finalize")) {
    goto error;
  }

  if (!check_function_pointer_address(value, "value")) {
    goto error;
  }

  if (!check_function_pointer_address(inverse, "inverse")) {
    goto error;
  }

  sqlite3* db = ((Connection*)con)->db;

  int result = sqlite3_create_window_function(db,
                                              name,
                                              narg,
                                              SQLITE_UTF8,
                                              NULL,
                                              (stepfunc)step,
                                              (finalizefunc)finalize,
                                              (valuefunc)value,
                                              (inversefunc)inverse,
                                              NULL);

  if (result != SQLITE_OK) {
    PyErr_SetString(PyExc_RuntimeError, sqlite3_errmsg(db));
    goto error;
  }

  Py_XDECREF(con);
  Py_RETURN_NONE;

error:
  Py_XDECREF(con);
  return NULL;
}
#else
static PyObject*
register_window_function(PyObject* self, PyObject* args)
{
  return PyErr_Format(PyExc_RuntimeError,
                      "SQLite version %s does not support window functions. "
                      "Window functions were added in 3.25.0",
                      SQLITE_VERSION);
}
#endif

static PyMethodDef cslumba_methods[] = {
  { "register_scalar_function",
    (PyCFunction)register_scalar_function,
    METH_VARARGS,
    "Register a numba generated SQLite user-defined function" },
  { "register_aggregate_function",
    (PyCFunction)register_aggregate_function,
    METH_VARARGS,
    "Register a numba generated SQLite user-defined aggregate function" },
  { "register_window_function",
    (PyCFunction)register_window_function,
    METH_VARARGS,
    "Register a numba generated SQLite user-defined window function" },
  { NULL, NULL, 0, NULL } /* sentinel */
};

static struct PyModuleDef cslumbamodule = {
  PyModuleDef_HEAD_INIT, "cslumba", NULL, -1, cslumba_methods,
};

PyMODINIT_FUNC
PyInit_cslumba(void)
{
  PyObject* module = PyModule_Create(&cslumbamodule);
  if (module == NULL) {
    return NULL;
  }

  if (PyModule_AddIntMacro(module, SQLITE_NULL) == -1) {
    return PyErr_Format(PyExc_RuntimeError,
                        "Unable to add SQLITE_NULL int constant with value %i",
                        SQLITE_NULL);
  }

  if (PyModule_AddIntMacro(module, SQLITE_FLOAT) == -1) {
    return PyErr_Format(
      PyExc_RuntimeError,
      "Unable to add SQLITE_FLOAT int constant with value %i",
      SQLITE_FLOAT);
  }

  if (PyModule_AddIntMacro(module, SQLITE_INTEGER) == -1) {
    return PyErr_Format(
      PyExc_RuntimeError,
      "Unable to add SQLITE_INTEGER int constant with value %i",
      SQLITE_INTEGER);
  }

  if (PyModule_AddStringMacro(module, SQLITE_VERSION) == -1) {
    return PyErr_Format(
      PyExc_RuntimeError,
      "Unable to add SQLITE_VERSION string constant with value %s",
      SQLITE_VERSION);
  }
  return module;
}
