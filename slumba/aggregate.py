import ast

from ctypes import c_void_p, c_int

from numba import void, optional

from slumba.gen import (
    RESULT_SETTERS, CONVERTERS, libsqlite3, gen_finalize, gen_step,
    camel_to_snake
)
from slumba.casting import unsafe_cast, sizeof, not_null

from slumba.cyslumba import _SQLITE_NULL as SQLITE_NULL


sqlite3_aggregate_context = libsqlite3.sqlite3_aggregate_context
sqlite3_aggregate_context.argtypes = c_void_p, c_int
sqlite3_aggregate_context.restype = c_void_p


def sqlite_udaf(signature):
    def cls_wrapper(cls):
        class_type = cls.class_type
        instance_type = class_type.instance_type
        jitmethods = class_type.jitmethods

        # don't make decisions about what to do with NULL values for users
        step_signature = void(instance_type, *map(optional, signature.args))
        jitmethods['step'].compile(step_signature)

        # aggregates can always return a NULL value
        finalize_signature = optional(signature.return_type)(instance_type)
        jitmethods['finalize'].compile(finalize_signature)

        func_name = camel_to_snake(cls.__name__)
        step_name = '{}_step'.format(func_name)
        finalize_name = '{}_finalize'.format(func_name)

        step_mod = gen_step(cls, step_name)
        finalize_mod = gen_finalize(cls, finalize_name)

        genmod = ast.Module(body=step_mod.body + finalize_mod.body)

        mod = ast.fix_missing_locations(genmod)

        code = compile(mod, __file__, 'exec')
        scope = {
            cls.__name__: cls,
            'sqlite3_aggregate_context': sqlite3_aggregate_context,
            'unsafe_cast': unsafe_cast,
            'sizeof': sizeof,
            'not_null': not_null,
            'SQLITE_NULL': SQLITE_NULL,
        }
        scope.update(CONVERTERS)
        scope.update((func.__name__, func) for func in RESULT_SETTERS.values())
        exec(code, scope)

        step = scope[step_name]
        finalize = scope[finalize_name]

        cls.step.address = step.address
        cls.finalize.address = finalize.address
        return cls

    return cls_wrapper
