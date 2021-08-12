#include "Python.h"
#include "sqlite3.h"
#include <cstdint>
#include <pybind11/pybind11.h>

namespace py = pybind11;

// Assume the pysqlite_Connection object's first non-PyObject member is the
// sqlite3 database
struct Connection {
  PyObject_HEAD sqlite3 *db;
};

PYBIND11_MODULE(cslumba, m) {
  m.attr("SQLITE_NULL") = SQLITE_NULL;
  m.attr("SQLITE_OK") = SQLITE_OK;
  m.attr("SQLITE_DETERMINISTIC") = SQLITE_DETERMINISTIC;
  m.attr("SQLITE_UTF8") = SQLITE_UTF8;
  m.attr("SQLITE_VERSION") = SQLITE_VERSION;

  m.def(
      "get_sqlite_db",
      [](py::object connection) {
        return reinterpret_cast<std::uintptr_t>(
            reinterpret_cast<Connection *>(connection.ptr())->db);
      },
      "Get the address of the sqlite3* db instance", py::arg("connection"));
}
