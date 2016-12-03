import sqlite3
import inspect
import ast
import time
import random

from ctypes import CDLL, c_void_p, c_double, c_int, c_int64, c_ubyte
from ctypes.util import find_library

from math import sqrt, exp, pi

from numba import cfunc, int64, float64, jit, i1, f8, i8, void, int32
from numba import jitclass, float64, int64
from numba.types import voidptr, CPointer, intc

from slumba.gen import (
    RESULT_SETTERS, CONVERTERS, libsqlite3, gen_finalize, gen_step,
    camel_to_snake
)
from casting import unsafe_cast, sizeof

from slumba.cyslumba import (
    register_scalar_function,
    register_aggregate_function,
    _SQLITE_NULL as SQLITE_NULL
)


sqlite3_aggregate_context = libsqlite3.sqlite3_aggregate_context
sqlite3_aggregate_context.argtypes = c_void_p, c_int
sqlite3_aggregate_context.restype = c_void_p


class SQLiteUDAF(object):
    def __init__(self, numba_class, step, finalize):
        self.numba_class = numba_class
        self.step = step
        self.finalize = finalize


def sqlite_udaf(signature):
    def cls_wrapper(cls):
        class_type = cls.class_type
        instance_type = class_type.instance_type
        jitmethods = class_type.jitmethods

        jitmethods['step'].compile(void(instance_type, *signature.args))
        jitmethods['finalize'].compile(signature.return_type(instance_type))

        step_mod = gen_step(cls)
        finalize_mod = gen_finalize(cls)

        genmod = ast.Module(body=step_mod.body + finalize_mod.body)

        mod = ast.fix_missing_locations(genmod)
        code = compile(mod, __file__, 'exec')
        scope = {
            cls.__name__: cls,
            'sqlite3_aggregate_context': sqlite3_aggregate_context,
            'unsafe_cast': unsafe_cast,
            'sizeof': sizeof,
        }
        scope.update(CONVERTERS)
        scope.update((func.__name__, func) for func in RESULT_SETTERS.values())
        exec(code, scope)

        func_name = camel_to_snake(cls.__name__)
        return SQLiteUDAF(
            cls,
            scope['{}_step'.format(func_name)],
            scope['{}_finalize'.format(func_name)],
        )

    return cls_wrapper
