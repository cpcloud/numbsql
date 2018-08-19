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
using stepfunc = void (*)(sqlite3_context *ctx, int narg, sqlite3_value **args);
using finalizefunc = void (*)(sqlite3_context *ctx);
using valuefunc = void (*)(sqlite3_context *ctx);
using inversefunc = void (*)(sqlite3_context *ctx, int narg,
                             sqlite3_value **args);

void register_scalar_function(sqlite3 *db, const char *name, int narg,
                              scalarfunc scalar) {
  if (sqlite3_create_function(db, name, narg, SQLITE_UTF8, nullptr, scalar,
                              nullptr, nullptr) != SQLITE_OK) {
    throw std::runtime_error(sqlite3_errmsg(db));
  }
}

void register_aggregate_function(sqlite3 *db, const char *name, int narg,
                                 stepfunc step, finalizefunc finalize) {
  if (sqlite3_create_function(db, name, narg, SQLITE_UTF8, nullptr, nullptr,
                              step, finalize) != SQLITE_OK) {
    throw std::runtime_error(sqlite3_errmsg(db));
  }
}

void register_window_function(sqlite3 *db, const char *name, int narg,
                              stepfunc step, finalizefunc finalize,
                              valuefunc value, inversefunc inverse) {
  if (sqlite3_create_window_function(db, name, narg, SQLITE_UTF8, nullptr, step,
                                     finalize, value, inverse,
                                     nullptr) != SQLITE_OK) {
    throw std::runtime_error(sqlite3_errmsg(db));
  }
}

PYBIND11_MODULE(cslumba, m) {
  m.doc() = "A module for registering numba functions with sqlite";
  m.attr("SQLITE_NULL") = SQLITE_NULL;
  m.def("register_scalar_function",
        [](py::object con, const std::string &name, int narg, intptr_t scalar) {
          register_scalar_function(
              reinterpret_cast<Connection *>(con.ptr())->db, name.c_str(), narg,
              reinterpret_cast<scalarfunc>(scalar));
        },
        "Register a numba generated SQLite user-defined function",
        py::arg("con"), py::arg("name"), py::arg("narg").noconvert(),
        py::arg("scalar").noconvert())
      .def("register_aggregate_function",
           [](py::object con, const std::string &name, int narg, intptr_t step,
              intptr_t finalize) {
             register_aggregate_function(
                 reinterpret_cast<Connection *>(con.ptr())->db, name.c_str(),
                 narg, reinterpret_cast<stepfunc>(step),
                 reinterpret_cast<finalizefunc>(finalize));
           },
           "Register a numba generated SQLite user-defined aggregate function",
           py::arg("con"), py::arg("name"), py::arg("narg").noconvert(),
           py::arg("step").noconvert(), py::arg("finalize").noconvert())
      .def("register_window_function",
           [](py::object con, const std::string &name, int narg, intptr_t step,
              intptr_t finalize, intptr_t value, intptr_t inverse) {
             register_window_function(
                 reinterpret_cast<Connection *>(con.ptr())->db, name.c_str(),
                 narg, reinterpret_cast<stepfunc>(step),
                 reinterpret_cast<finalizefunc>(finalize),
                 reinterpret_cast<valuefunc>(value),
                 reinterpret_cast<inversefunc>(inverse));
           },
           "Register a numba generated SQLite user-defined window function",
           py::arg("con"), py::arg("name"), py::arg("narg").noconvert(),
           py::arg("step").noconvert(), py::arg("finalize").noconvert(),
           py::arg("value").noconvert(), py::arg("inverse").noconvert());
}
