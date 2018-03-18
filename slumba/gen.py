import re

from miniast import (
    call, TRUE, NONE, arg, from_, if_, def_, var, alias, decorate, mod, ifelse,
    return_, sourcify
)

from ctypes import CDLL, c_void_p, c_double, c_int, c_int64, c_ubyte, POINTER
from ctypes.util import find_library

from numba import float64, int64, int32, optional


libsqlite3 = CDLL(find_library('sqlite3'))


sqlite3_result_double = libsqlite3.sqlite3_result_double
sqlite3_result_int64 = libsqlite3.sqlite3_result_int64
sqlite3_result_int = libsqlite3.sqlite3_result_int
sqlite3_result_null = libsqlite3.sqlite3_result_null

sqlite3_result_double.argtypes = c_void_p, c_double
sqlite3_result_double.restype = None

sqlite3_result_int64.argtypes = c_void_p, c_int64
sqlite3_result_int64.restype = None

sqlite3_result_int.argtypes = c_void_p, c_int
sqlite3_result_int.restype = None

sqlite3_result_null.argtypes = c_void_p,
sqlite3_result_null.restype = None


RESULT_SETTERS = {
    optional(float64): sqlite3_result_double,
    optional(int64): sqlite3_result_int64,
    optional(int32): sqlite3_result_int,
    float64: sqlite3_result_double,
    int64: sqlite3_result_int64,
    int32: sqlite3_result_int,
}


value_methods = {
    'blob': c_void_p,
    'bytes': c_int,
    'double': c_double,
    'int': c_int,
    'int64': c_int64,
    'text': POINTER(c_ubyte),
    'type': c_int,
}


def add_value_method(typename, restype):
    method = getattr(libsqlite3, 'sqlite3_value_{}'.format(typename))
    method.argtypes = c_void_p,
    method.restype = restype
    return method


VALUE_EXTRACTORS = {
    optional(float64): add_value_method('double', c_double),
    optional(int64): add_value_method('int64', c_int64),
    optional(int32): add_value_method('int', c_int),
    float64: add_value_method('double', c_double),
    int64: add_value_method('int64', c_int64),
    int32: add_value_method('int', c_int),
}


CONVERTERS = {
    'sqlite3_value_{}'.format(typename): add_value_method(typename, restype)
    for typename, restype in value_methods.items()
}


def unnullify(value, true_function, name):
    # condition = sqlite3_value_type(value) == SQLITE_NULL
    # name = true_function(value) if condition else None
    return var[name].store(
        ifelse(
            call.sqlite3_value_type(value) != var.SQLITE_NULL,
            true_function(value),
            NONE
        )
    )


def generate_function_body(func, *, skipna):
    sig, = func.nopython_signatures
    converters = ((arg, VALUE_EXTRACTORS[arg]) for arg in sig.args)
    resulter = RESULT_SETTERS[sig.return_type]

    args = []
    sequence = []

    for i, (argtype, converter) in enumerate(converters):
        argname = 'arg_{:d}'.format(i)

        if_statement = unnullify(
            var.argv[i], call[converter.__name__], argname
        )

        sequence.append(if_statement)

        if skipna:
            sequence.append(
                if_(var[argname].is_(NONE))[
                    call.sqlite3_result_null(var.ctx),
                    return_()
                ]
            )
        args.append(var[argname])

    result = call[func.__name__](*args)
    final_call = call[resulter.__name__](var.ctx, var.result_value)
    return sequence + [
        var.result_value.store(result),
        if_(var.result_value.is_not(NONE))[
            final_call,
        ].else_[
            call.sqlite3_result_null(var.ctx)
        ]
    ]


def gen_scalar(func, name, *, skipna):
    return mod(
        # from numba import cfunc
        from_.numba.import_(alias.cfunc),

        # from numba.types import void, voidptr, intc, CPointer
        from_.numba.types.import_(
            alias.void,
            alias.voidptr,
            alias.intc,
            alias.CPointer,
        ),

        # @cfunc(void(voidptr, intc, CPointer(voidptr)))
        decorate(
            call.cfunc(
                call.void(var.voidptr, var.intc, call.CPointer(var.voidptr)),
                nopython=TRUE
            )
        )(
            # def func(ctx, argc, argv):
            #     *body
            def_[name](arg.ctx, arg.argc, arg.argv)(
                *generate_function_body(func, skipna=skipna),
            )
        )
    )


def camel_to_snake(name):
    result = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', result).lower()


def gen_step(cls, name, *, skipna):
    class_name = cls.__name__
    sig, = cls.class_type.jitmethods['step'].nopython_signatures
    args = sig.args[1:]

    body = [
        var['arg_{:d}'.format(i)].store(var.argv[i]) for i in range(len(args))
    ]

    step_args = []
    statements = []

    for i, a in enumerate(args):
        argname = 'value_{:d}'.format(i)
        if_statement = unnullify(
            var['arg_{:d}'.format(i)],
            call[VALUE_EXTRACTORS[a].__name__],
            argname,
        )
        statements.append(if_statement)
        argvar = var[argname]
        if skipna:
            statements.append(
                if_(argvar.is_(NONE))[
                    call.sqlite3_result_null(var.ctx),
                    return_()
                ]
            )
        step_args.append(argvar)

    module = mod(
        from_.numba.import_(alias.cfunc),
        from_.numba.types.import_(
            alias.void, alias.voidptr, alias.intc, alias.CPointer
        ),
        decorate(
            call.cfunc(
                call.void(var.voidptr, var.intc, call.CPointer(var.voidptr)),
                nopython=TRUE
            )
        )(
            def_[name](arg.ctx, arg.argc, arg.argv)(
                *body,
                var.agg_ctx.store(
                    call.unsafe_cast(
                        call.sqlite3_aggregate_context(
                            var.ctx,
                            call.sizeof(var[class_name])
                        ),
                        var[class_name]
                    )
                ),
                if_(call.not_null(var.agg_ctx))(
                    *statements,
                    var.agg_ctx.step(*step_args)
                ),
            )
        )
    )

    return module


def gen_finalize(cls, name):
    class_name = cls.__name__
    sig, = cls.class_type.jitmethods['finalize'].nopython_signatures
    output_call = call[RESULT_SETTERS[sig.return_type].__name__](
        var.ctx, var.final_value
    )
    final_result = if_(var.final_value.is_not(NONE))[
        output_call,
    ].else_[
        call.sqlite3_result_null(var.ctx)
    ]
    return mod(
        # no imports because this is always defined with a step function,
        # which has the imports
        decorate(
            call.cfunc(call.void(var.voidptr), nopython=TRUE)
        )(
            def_[name](arg.ctx)(
                var.agg_ctx.store(
                    call.unsafe_cast(
                        call.sqlite3_aggregate_context(var.ctx, 0),
                        var[class_name]
                    )
                ),
                if_(call.not_null(var.agg_ctx))(
                    var.final_value.store(call(var.agg_ctx.finalize)),
                    final_result,
                ),
            )
        )
    )


if __name__ == '__main__':
    from numba import jit, jitclass
    from slumba import sqlite_udaf

    @jit(float64(int64, int64), nopython=True)
    def g(x, y):
        return x + y * 1.0

    # this shows what the compiled function looks like
    module = gen_scalar(g, 'g_unit', skipna=True)

    @sqlite_udaf(float64(float64))
    @jitclass([
        ('total', float64),
        ('count', int64),
    ])
    class Avg(object):
        def __init__(self):
            self.total = 0.0
            self.count = 0

        def step(self, value):
            self.total += value
            self.count += 1

        def finalize(self):
            if not self.count:
                return None
            return self.total / self.count
    print(sourcify(gen_step(Avg, 'avg_step', skipna=True)))
    print(sourcify(gen_finalize(Avg, 'avg_finalize')))
