import ast

from numba import void, optional

from miniast import mod

from slumba.gen import gen_finalize, gen_step, camel_to_snake
from slumba.sqlite import (
    RESULT_SETTERS, CONVERTERS, sqlite3_result_null, sqlite3_aggregate_context)
from slumba.casting import unsafe_cast, sizeof, not_null

from slumba.cslumba import SQLITE_NULL


def sqlite_udaf(signature, *, skipna=True):
    def cls_wrapper(cls):
        class_type = cls.class_type
        instance_type = class_type.instance_type
        jitmethods = class_type.jitmethods

        step_signature = void(instance_type, *map(optional, signature.args))
        jitmethods['step'].compile(step_signature)

        # aggregates can always return a NULL value
        finalize_signature = optional(signature.return_type)(instance_type)
        jitmethods['finalize'].compile(finalize_signature)

        # aggregates can always return a NULL value
        value_signature = finalize_signature
        try:
            jitmethods['value'].compile(value_signature)
        except KeyError:
            is_window_function = False
        else:
            is_window_function = True

        inverse_signature = step_signature
        try:
            jitmethods['inverse'].compile(inverse_signature)
        except KeyError:
            is_window_function = False

        func_name = camel_to_snake(cls.__name__)

        step_name = '{}_step'.format(func_name)
        finalize_name = '{}_finalize'.format(func_name)

        if is_window_function:
            value_name = '{}_value'.format(func_name)
            inverse_name = '{}_inverse'.format(func_name)

        step_mod = gen_step(cls, step_signature, step_name, skipna=skipna)
        finalize_mod = gen_finalize(cls, finalize_signature, finalize_name)

        if is_window_function:
            value_mod = gen_finalize(cls, value_signature, value_name)
            inverse_mod = gen_step(
                cls, inverse_signature, inverse_name, skipna=skipna)

        module_body = step_mod.body + finalize_mod.body

        if is_window_function:
            module_body.extend(value_mod.body)
            module_body.extend(inverse_mod.body)

        genmod = mod(*module_body)

        module = ast.fix_missing_locations(genmod)

        code = compile(module, __file__, 'exec')
        scope = {
            cls.__name__: cls,
            'sqlite3_aggregate_context': sqlite3_aggregate_context,
            'sqlite3_result_null': sqlite3_result_null,
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

        if is_window_function:
            value = scope[value_name]
            inverse = scope[inverse_name]

        cls.step.address = step.address
        cls.finalize.address = finalize.address

        if is_window_function:
            cls.value.address = value.address
            cls.inverse.address = inverse.address

        return cls

    return cls_wrapper
