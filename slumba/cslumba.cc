#include <stdexcept>

#include <pybind11/pybind11.h>

#include "sqlite3.h"

namespace py = pybind11;

/* Assume the pysqlite_Connection object's first non-PyObject member is the
 * sqlite3 database */
struct Connection {
  PyObject_HEAD sqlite3 *db;
};

using scalarfunc = void (*)(sqlite3_context *ctx, int narg,
                            sqlite3_value **args);
using stepfunc = scalarfunc;
using finalizefunc = void (*)(sqlite3_context *ctx);
using valuefunc = void (*)(sqlite3_context *ctx);
using inversefunc = void (*)(sqlite3_context *ctx, int narg,
                             sqlite3_value **args);

void register_scalar_function(py::object con, std::string name, int narg,
                              intptr_t scalar) {
  sqlite3 *db = reinterpret_cast<Connection *>(con.ptr())->db;

  if (sqlite3_create_function(db, name.c_str(), narg, SQLITE_UTF8, nullptr,
                              reinterpret_cast<scalarfunc>(scalar), nullptr,
                              nullptr) != SQLITE_OK) {
    throw std::runtime_error(sqlite3_errmsg(db));
  }
}

void register_aggregate_function(py::object con, std::string name, int narg,
                                 intptr_t step, intptr_t finalize) {
  sqlite3 *db = reinterpret_cast<Connection *>(con.ptr())->db;

  if (sqlite3_create_function(db, name.c_str(), narg, SQLITE_UTF8, nullptr,
                              reinterpret_cast<scalarfunc>(step),
                              reinterpret_cast<scalarfunc>(finalize),
                              nullptr) != SQLITE_OK) {
    throw std::runtime_error(sqlite3_errmsg(db));
  }
}

void register_window_function(py::object con, std::string name, int narg,
                              intptr_t step, intptr_t finalize, intptr_t value,
                              intptr_t inverse) {
  sqlite3 *db = reinterpret_cast<Connection *>(con.ptr())->db;

  //if (sqlite3_create_window_function(
          //db, name.c_str(), narg, SQLITE_UTF8, nullptr,
          //reinterpret_cast<scalarfunc>(step),
          //reinterpret_cast<finalizefunc>(finalize),
          //reinterpret_cast<valuefunc>(value),
          //reinterpret_cast<inversefunc>(inverse), nullptr) != SQLITE_OK) {
    //throw std::runtime_error(sqlite3_errmsg(db));
  //}
}

PYBIND11_MODULE(cslumba, m) {
  m.doc() = "A module for registering numba functions with sqlite";
  m.def("register_scalar_function", &register_scalar_function,
        "Register a numba generated SQLite user-defined function")
      .def("register_aggregate_function", &register_aggregate_function,
           "Register a numba generated SQLite user-defined aggregate function")
      .def("register_window_function", &register_window_function,
           "Register a numba generated SQLite user-defined window function");
}
