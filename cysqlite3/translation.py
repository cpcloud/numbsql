import os
from math import sin as math_sin

# from ctypes import c_double, CFUNCTYPE as cfunctype

import llvmlite.llvmpy.ee as ee
from toolz import first
from cysqlite3 import register, sqlite3_connection

from numba import jit, float64


def udf(func):
    llvm_module = first(func._compileinfos.values()).library._final_module
    engine = ee.EngineBuilder.new(llvm_module).create()
    functions = [
        func for func in llvm_module.functions
        if not func.name.startswith('_') and not func.is_declaration
    ]
    addr = engine.get_function_address(functions[1].name)
    assert addr > 0, 'addr == %d' % addr

    # Declare the ctypes function prototype
    # functype = cfunctype(c_double, c_double)

    path = os.path.expanduser(
        os.path.join('~', 'ibis-data', 'ibis-testing-data', 'ibis-testing.db')
    )
    con = sqlite3_connection(path.encode('utf8'))
    result = register(
        con,
        addr,
        func.__name__.encode('utf8'),
        len(func.nopython_signatures[0].args)
    )
    import ipdb; ipdb.set_trace()
    con.execute("select mysin(1.0230923)".encode('utf8'))


@jit(float64(float64))
def mysin(x):
    return math_sin(x)


sin = udf(mysin)

