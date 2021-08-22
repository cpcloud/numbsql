from typing import Callable, Type

from numba import cfunc, void
from numba.core.typing import Signature
from numba.types import CPointer, intc, voidptr

from .numbaext import (
    get_sqlite3_result_function,
    init,
    is_not_null_pointer,
    make_arg_tuple,
    reset_init,
    sizeof,
    unsafe_cast,
)
from .sqlite import sqlite3_aggregate_context, sqlite3_result_null, sqlite3_user_data


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

        init_func = class_type.jit_methods["__init__"]
        init_signature = void(instance_type)
        init_func.compile(init_signature)

        step_func = class_type.jit_methods["step"]
        step_signature = void(instance_type, *signature.args)
        step_func.compile(step_signature)

        @cfunc(void(voidptr, intc, CPointer(voidptr)))  # type: ignore[misc]
        def step(  # type: ignore[no-untyped-def]
            ctx, argc: int, argv
        ) -> None:  # pragma: no cover
            raw_pointer = sqlite3_aggregate_context(ctx, sizeof(cls))

            if is_not_null_pointer(raw_pointer):
                agg_ctx = unsafe_cast(raw_pointer, cls)
                is_initialized = sqlite3_user_data(ctx)
                init(agg_ctx, is_initialized)
                args = make_arg_tuple(step_func, argv)
                agg_ctx.step(*args)

        finalize_func = class_type.jit_methods["finalize"]
        finalize_signature: Signature = signature.return_type(instance_type)
        finalize_func.compile(finalize_signature)

        @cfunc(void(voidptr))  # type: ignore[misc]
        def finalize(ctx) -> None:  # type: ignore[no-untyped-def]  # pragma: no cover
            raw_pointer = sqlite3_aggregate_context(ctx, sizeof(cls))
            if is_not_null_pointer(raw_pointer):
                agg_ctx = unsafe_cast(raw_pointer, cls)
                result = agg_ctx.finalize()

                if result is None:
                    sqlite3_result_null(ctx)
                else:
                    result_setter = get_sqlite3_result_function(result)
                    result_setter(ctx, result)

                is_initialized = sqlite3_user_data(ctx)
                reset_init(is_initialized)

        try:
            value_func = class_type.jit_methods["value"]
        except KeyError:
            has_value_func = False
        else:
            has_value_func = True

        try:
            inverse_func = class_type.jit_methods["inverse"]
        except KeyError:
            has_inverse_func = False
        else:
            has_inverse_func = True

        is_window_function = has_value_func and has_inverse_func

        if is_window_function:
            # aggregates can always return a NULL value
            value_signature = finalize_signature
            value_func.compile(value_signature)

            @cfunc(void(voidptr))  # type: ignore[misc]
            def value(ctx) -> None:  # type: ignore[no-untyped-def]  # pragma: no cover
                raw_pointer = sqlite3_aggregate_context(ctx, sizeof(cls))
                if is_not_null_pointer(raw_pointer):
                    agg_ctx = unsafe_cast(raw_pointer, cls)
                    result = agg_ctx.value()
                    if result is None:
                        sqlite3_result_null(ctx)
                    else:
                        result_setter = get_sqlite3_result_function(result)
                        result_setter(ctx, result)

            inverse_signature = step_signature
            inverse_func.compile(inverse_signature)

            @cfunc(void(voidptr, intc, CPointer(voidptr)))  # type: ignore[misc,]
            def inverse(  # type: ignore[no-untyped-def]
                ctx, argc: int, argv
            ) -> None:  # pragma: no cover
                raw_pointer = sqlite3_aggregate_context(ctx, sizeof(cls))
                if is_not_null_pointer(raw_pointer):
                    agg_ctx = unsafe_cast(raw_pointer, cls)
                    args = make_arg_tuple(inverse_func, argv)
                    agg_ctx.inverse(*args)

        cls.step.address = step.address
        cls.finalize.address = finalize.address

        if is_window_function:
            cls.value.address = value.address
            cls.inverse.address = inverse.address
        return cls

    return cls_wrapper
