import re

from miniast import (
    TRUE, NONE, arg, from_, if_, def_, var, alias, decorate, mod, ifelse,
    return_, sourcify
)

from slumba.sqlite import VALUE_EXTRACTORS, RESULT_SETTERS


def unnullify(value, true_function, name):
    # condition = sqlite3_value_type(value) == SQLITE_NULL
    # name = true_function(value) if condition else None
    return var[name].store(
        ifelse(
            var.sqlite3_value_type(value) != var.SQLITE_NULL,
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
            var.argv[i], var[converter.__name__], argname
        )

        sequence.append(if_statement)

        if skipna:
            sequence.append(
                if_(var[argname].is_(NONE))[
                    var.sqlite3_result_null(var.ctx),
                    return_()
                ]
            )
        args.append(var[argname])

    result = var[func.__name__](*args)
    final_call = var[resulter.__name__](var.ctx, var.result_value)
    return sequence + [
        var.result_value.store(result),
        if_(var.result_value.is_not(NONE))[
            final_call,
        ].else_[
            var.sqlite3_result_null(var.ctx)
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
            var.cfunc(
                var.void(var.voidptr, var.intc, var.CPointer(var.voidptr)),
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
            var[VALUE_EXTRACTORS[a].__name__],
            argname,
        )
        statements.append(if_statement)
        argvar = var[argname]
        if skipna:
            statements.append(
                if_(argvar.is_(NONE))[
                    var.sqlite3_result_null(var.ctx),
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
            var.cfunc(
                var.void(var.voidptr, var.intc, var.CPointer(var.voidptr)),
                nopython=TRUE
            )
        )(
            def_[name](arg.ctx, arg.argc, arg.argv)(
                *body,
                var.agg_ctx.store(
                    var.unsafe_cast(
                        var.sqlite3_aggregate_context(
                            var.ctx,
                            var.sizeof(var[class_name])
                        ),
                        var[class_name]
                    )
                ),
                if_(var.not_null(var.agg_ctx))(
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
    output_call = var[RESULT_SETTERS[sig.return_type].__name__](
        var.ctx, var.final_value
    )
    final_result = if_(var.final_value.is_not(NONE))[
        output_call,
    ].else_[
        var.sqlite3_result_null(var.ctx)
    ]
    return mod(
        # no imports because this is always defined with a step function,
        # which has the imports
        decorate(
            var.cfunc(var.void(var.voidptr), nopython=TRUE)
        )(
            def_[name](arg.ctx)(
                var.agg_ctx.store(
                    var.unsafe_cast(
                        var.sqlite3_aggregate_context(var.ctx, 0),
                        var[class_name]
                    )
                ),
                if_(var.not_null(var.agg_ctx))(
                    var.final_value.store(var.agg_ctx.finalize()),
                    final_result,
                ),
            )
        )
    )


if __name__ == '__main__':
    from numba import jit, jitclass, float64, int64
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
