from typing import Callable, Type

from numba import void, optional, cfunc
from numba.types import voidptr, intc, CPointer
from numba.typing import Signature

from slumba.sqlite import sqlite3_aggregate_context, sqlite3_result_null
from slumba.numbaext import (
    unsafe_cast,
    sizeof,
    is_not_null_pointer,
    make_arg_tuple,
    get_sqlite3_result_function,
)


def sqlite_udaf(signature: Signature) -> Callable[[Type], Type]:
    """Define a custom aggregate function.

    Parameters
    ----------
    signature
        A numba signature.

    """
    def cls_wrapper(cls: Type) -> Type:
        class_type = cls.class_type
        instance_type = class_type.instance_type

        step_func = class_type.jitmethods['step']
        step_signature = void(instance_type, *signature.args)
        step_func.compile(step_signature)

        @cfunc(void(voidptr, intc, CPointer(voidptr)))
        def step(ctx, argc, argv):  # pragma: no cover
            raw_pointer = sqlite3_aggregate_context(ctx, sizeof(cls))
            agg_ctx = unsafe_cast(raw_pointer, cls)
            if is_not_null_pointer(agg_ctx):
                args = make_arg_tuple(step_func, argv)
                agg_ctx.step(*args)

        finalize_func = class_type.jitmethods['finalize']
        finalize_signature: Signature = signature.return_type(instance_type)
        finalize_func.compile(finalize_signature)

        @cfunc(void(voidptr))
        def finalize(ctx):  # pragma: no cover
            raw_pointer = sqlite3_aggregate_context(ctx, sizeof(cls))
            agg_ctx = unsafe_cast(raw_pointer, cls)
            if is_not_null_pointer(agg_ctx):
                result = agg_ctx.finalize()
                if result is None:
                    sqlite3_result_null(ctx)
                else:
                    result_setter = get_sqlite3_result_function(result)
                    result_setter(ctx, result)

        try:
            value_func = class_type.jitmethods['value']
        except KeyError:
            has_value_func = False
        else:
            has_value_func = True

        try:
            inverse_func = class_type.jitmethods['inverse']
        except KeyError:
            has_inverse_func = False
        else:
            has_inverse_func = True

        is_window_function = has_value_func and has_inverse_func

        if is_window_function:
            # aggregates can always return a NULL value
            value_signature = optional(signature.return_type)(instance_type)
            value_func.compile(value_signature)

            @cfunc(void(voidptr))
            def value(ctx):  # pragma: no cover
                raw_pointer = sqlite3_aggregate_context(ctx, sizeof(cls))
                agg_ctx = unsafe_cast(raw_pointer, cls)
                if is_not_null_pointer(agg_ctx):
                    result = agg_ctx.value()
                    if result is None:
                        sqlite3_result_null(ctx)
                    else:
                        result_setter = get_sqlite3_result_function(result)
                        result_setter(ctx, result)

            inverse_signature: Signature = step_signature
            inverse_func.compile(inverse_signature)

            @cfunc(void(voidptr, intc, CPointer(voidptr)))
            def inverse(ctx, argc, argv):  # pragma: no cover
                raw_pointer = sqlite3_aggregate_context(ctx, sizeof(cls))
                agg_ctx = unsafe_cast(raw_pointer, cls)
                if is_not_null_pointer(agg_ctx):
                    agg_ctx.inverse(*make_arg_tuple(inverse_func, argv))

        cls.step.address = step.address
        cls.finalize.address = finalize.address

        if is_window_function:
            cls.value.address = value.address
            cls.inverse.address = inverse.address
        return cls
    return cls_wrapper
