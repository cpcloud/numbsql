#include <pybind11/pybind11.h>

#include "sqlite3.h"

namespace py = pybind11;

/* Assume the pysqlite_Connection object's first non-PyObject member is the
 * sqlite3 database */
using Connection = struct {
    PyObject_HEAD
    sqlite3 *db;
};

using scalarfunc = void (*)(sqlite3_context* ctx, int narg, sqlite3_value** args);
using stepfunc = scalarfunc;
using finalizefunc = void (*)(sqlite3_context* ctx);
using valuefunc = void (*)(sqlite3_context* ctx);
using inversefunc = void (*)(sqlite3_context* ctx, int narg, sqlite3_value** args);

void register_scalar_function(py::object con, std::string name, int narg, Py_ssize_t scalar) {
    if (nargs < -1) {
	throw py::value_error("narg < -1, must be between -1 and SQLITE_LIMIT_FUNCTION_ARG");
    }

    if (narg > SQLITE_LIMIT_FUNCTION_ARG) {
	throw py::value_error("narg > SQLITE_LIMIT_FUNCTION_ARG");
    }

    if (address <= 0) {
	throw py::value_error("scalar function pointer address must be greater than 0");
    }

    sqlite3* db = reinterpret_cast<Connection*>(con.ptr())->db;

    int result = sqlite3_create_function(
        db,
        name,
        narg,
        SQLITE_UTF8,
        nullptr,
	reinterpret_cast<scalarfunc>(scalar);
        nullptr,
        nullptr
    );

    if (result != SQLITE_OK) {
	throw py::runtime_error(sqlite3_errmsg(db));
    }
}

void register_aggregate_function(
    py::object con, std::string name, int narg, Py_ssize_t step, Py_ssize_t finalize) {
    if (nargs < -1) {
	throw py::value_error("narg < -1, must be between -1 and SQLITE_LIMIT_FUNCTION_ARG");
    }

    if (narg > SQLITE_LIMIT_FUNCTION_ARG) {
	throw py::value_error("narg > SQLITE_LIMIT_FUNCTION_ARG");
    }

    if (step <= 0) {
	throw py::value_error("step function pointer address must be greater than 0");
    }

    if (finalize <= 0) {
	throw py::value_error("finalize function pointer address must be greater than 0");
    }

    sqlite3* db = reinterpret_cast<Connection*>(con.ptr())->db;

    int result = sqlite3_create_function(
        db,
        name,
        narg,
        SQLITE_UTF8,
        nullptr,
        nullptr,
	reinterpret_cast<scalarfunc>(step),
	reinterpret_cast<scalarfunc>(finalize)
    );

    if (result != SQLITE_OK) {
	throw py::runtime_error(sqlite3_errmsg(db));
    }
}

void register_window_function(
    py::object con, std::string name, int narg, Py_ssize_t step, Py_ssize_t finalize) {
    if (nargs < -1) {
	throw py::value_error("narg < -1, must be between -1 and SQLITE_LIMIT_FUNCTION_ARG");
    }

    if (narg > SQLITE_LIMIT_FUNCTION_ARG) {
	throw py::value_error("narg > SQLITE_LIMIT_FUNCTION_ARG");
    }

    if (step <= 0) {
	throw py::value_error("step function pointer address must be greater than 0");
    }

    if (finalize <= 0) {
	throw py::value_error("finalize function pointer address must be greater than 0");
    }

    sqlite3* db = reinterpret_cast<Connection*>(con.ptr())->db;

    int result = sqlite3_create_window_function(
        db,
        name,
        narg,
        SQLITE_UTF8,
	nullptr,
	reinterpret_cast<scalarfunc>(step),
	reinterpret_cast<finalizefunc>(finalize),
        reinterpret_cast<valuefunc>(value),
        reinterpret_cast<inversefunc>(value),
        nullptr
    );

    if (result != SQLITE_OK) {
	throw py::runtime_error(sqlite3_errmsg(db));
    }
}

PYBIND11_MODULE(cslumba, m) {
    m.doc() = "A module for registering numba functions with sqlite";
    m.def("register_scalar_function", &register_scalar_function, "Register a numba generated SQLite user-defined function")
     .def("register_aggregate_function", &register_aggregate_function, "Register a numba generated SQLite user-defined aggregate function")
     .def("register_window_function", &register_window_function, "Register a numba generated SQLite user-defined window function");
}
