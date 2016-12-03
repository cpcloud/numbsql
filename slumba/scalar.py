import ast

from numba import njit

from slumba.cyslumba import _SQLITE_NULL as SQLITE_NULL

from slumba.gen import CONVERTERS, RESULT_SETTERS, gen_scalar


def sqlite_udf(signature):
    new_signature = optional(signature.return_type)(*signature.args) 

    def wrapped(func):
        jitted_func = njit(new_signature)(func)
        func_name = func.__name__
        scope = {func_name: jitted_func}
        scope.update(CONVERTERS)
        scope.update((f.__name__, f) for f in RESULT_SETTERS.values())
        final_func_name = '{}_scalar'.format(func_name)
        genmod = gen_scalar(jitted, final_func_name)
        mod = ast.fix_missing_locations(genmod)
        bytecode = compile(mod, __file__, 'exec')
        exec(bytecode, scope)
        return scope[final_func_name]
    return wrapped
