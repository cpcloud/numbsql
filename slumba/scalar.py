import ast

from numba import njit, optional

from slumba.gen import CONVERTERS, RESULT_SETTERS, gen_scalar


def sqlite_udf(signature):
    # SQL functions can always return and accept None
    new_signature = optional(signature.return_type)(
        *map(optional, signature.args)
    )

    def wrapped(func):
        jitted_func = njit(new_signature)(func)
        func_name = func.__name__
        scope = {func_name: jitted_func}
        scope.update(CONVERTERS)
        scope.update((f.__name__, f) for f in RESULT_SETTERS.values())
        final_func_name = '{}_scalar'.format(func_name)
        genmod = gen_scalar(jitted_func, final_func_name)
        mod = ast.fix_missing_locations(genmod)
        bytecode = compile(mod, __file__, 'exec')
        exec(bytecode, scope)
        return scope[final_func_name]
    return wrapped
