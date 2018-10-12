#include "Python.h"
#include "sqlite3.h"

/* Assume the pysqlite_Connection object's first non-PyObject member is the
 * sqlite3 database */
typedef struct
{
  PyObject_HEAD
  sqlite3* db;
} Connection;

static PyObject*
get_sqlite_db(PyObject* self, PyObject* args)
{
  (void)self;
  PyObject* con = NULL;
  if (!PyArg_ParseTuple(args, "O", &con)) {
    return NULL;
  }
  Py_INCREF(con);
  Py_ssize_t address = (Py_ssize_t)((Connection*)con)->db;
  Py_DECREF(con);
  return PyLong_FromLong(address);
}

static PyMethodDef cslumba_methods[] = {
  { "get_sqlite_db",
    (PyCFunction)get_sqlite_db,
    METH_VARARGS,
    "Get the address of the sqlite3* db instance" },
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

  if (PyModule_AddIntMacro(module, SQLITE_DETERMINISTIC) == -1) {
    return PyErr_Format(
      PyExc_RuntimeError,
      "Unable to add SQLITE_DETERMINISTIC int constant with value %d",
      SQLITE_DETERMINISTIC);
  }

  if (PyModule_AddIntMacro(module, SQLITE_UTF8) == -1) {
    return PyErr_Format(
      PyExc_RuntimeError,
      "Unable to add SQLITE_UTF8 int constant with value %d",
      SQLITE_UTF8);
  }

  if (PyModule_AddStringMacro(module, SQLITE_VERSION) == -1) {
    return PyErr_Format(
      PyExc_RuntimeError,
      "Unable to add SQLITE_VERSION string constant with value %s",
      SQLITE_VERSION);
  }
  return module;
}
