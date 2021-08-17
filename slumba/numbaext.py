from typing import Callable, Tuple, Union

from llvmlite.ir.instructions import (
    CastInstr,
    Constant,
    ICMPInstr,
    InsertValue,
    LoadInstr,
    Value,
)
from llvmlite.llvmpy.core import Builder
from numba import extending, types
from numba.core import cgutils, imputils
from numba.core.base import BaseContext
from numba.core.typing import ctypes_utils
from numba.core.typing.context import Context
from numba.core.typing.templates import Signature

from .sqlite import RESULT_SETTERS, SQLITE_NULL, VALUE_EXTRACTORS, sqlite3_value_type


@extending.intrinsic  # type: ignore[misc]
def unsafe_cast(
    typingctx: Context,
    src: Union[types.RawPointer, types.Integer],
    dst: types.ClassType,
) -> Tuple[
    Signature, Callable[[BaseContext, Builder, Signature, Tuple[Value, ...]], LoadInstr]
]:
    """Cast a void pointer to a jitclass.

    Parameters
    ----------
    typingctx
    src
        A pointer to cast to type `dst`.
    dst
        A type to cast from `src` to.

    Raises
    ------
    TypeError
        If `src` is not a raw pointer or integer or `dst` is not a jitclass
        type.
    """
    if isinstance(src, (types.RawPointer, types.Integer)) and isinstance(
        dst, types.ClassType
    ):
        inst_typ = dst.instance_type
        sig = inst_typ(types.voidptr, dst)

        def codegen(
            context: BaseContext,
            builder: Builder,
            signature: Signature,
            args: Tuple[Value, ...],
        ) -> LoadInstr:
            ptr, _ = args
            alloc_type = context.get_data_type(inst_typ.get_data_type())

            inst_struct = context.make_helper(builder, inst_typ)

            # Set meminfo to correctly typed NULL value
            #
            # If you don't set this attribute to a NULL value, then numba
            # thinks it owns the memory, when in fact SQLite is the owner.
            inst_struct.meminfo = cgutils.get_null_value(inst_struct.meminfo.type)

            # Set data from the given pointer
            inst_struct.data = builder.bitcast(ptr, alloc_type.as_pointer())
            return inst_struct._getvalue()

        return sig, codegen
    else:
        raise TypeError(f"Unable to cast pointer type {src} to class type {dst}")


@extending.intrinsic  # type: ignore[misc]
def make_arg_tuple(
    typingctx: Context, func: types.Callable, argv: types.CPointer
) -> Tuple[
    Signature,
    Callable[[BaseContext, Builder, Signature, Tuple[Value, ...]], InsertValue],
]:
    (func_type,), _ = func.get_call_signatures()
    first_arg, *_ = args = func_type.args

    # skip the first argument if `func` is a method call
    first_argument_position = int(isinstance(first_arg, types.ClassInstanceType))
    argtypes = args[first_argument_position:]
    tuple_type = types.Tuple(argtypes)
    sig = tuple_type(func, types.CPointer(types.voidptr))

    def codegen(
        context: BaseContext,
        builder: Builder,
        signature: Signature,
        args: Tuple[Value, ...],
    ) -> InsertValue:
        # first argument is the instance, and we don't need it here
        _, argv = args
        converted_args = []
        pyapi = context.get_python_api(builder)

        for i, argtype in enumerate(argtypes):
            # get a pointer to the ith argument
            element_pointer = cgutils.gep(builder, argv, i, inbounds=True)

            # deref that pointer
            element = builder.load(element_pointer)

            # check for null values #
            # get a pointer to the sqlite3_value_type C function
            sqlite3_value_type_numba = context.get_constant_generic(
                builder,
                ctypes_utils.make_function_type(sqlite3_value_type),
                sqlite3_value_type,
            )
            value_type = builder.call(sqlite3_value_type_numba, [element])

            # make the SQLITE_NULL value type constant available
            sqlite_null = context.get_constant(types.int32, SQLITE_NULL)

            # check whether the value is equal to SQLITE_NULL
            is_not_null = cgutils.is_true(
                builder, builder.icmp_signed("!=", value_type, sqlite_null)
            )

            # setup value extraction #
            # get the appropriate ctypes extraction routine
            ctypes_function = VALUE_EXTRACTORS[argtype]

            # create a numba function type for the converter
            converter = ctypes_utils.make_function_type(ctypes_function)

            # get the function pointer instruction out
            fn = context.get_constant_generic(builder, converter, ctypes_function)

            # if the argument is an optional type then pull out the underlying
            # type and make an optional value with it
            #
            # otherwise the raw value is the argument
            raw = builder.call(fn, [element])
            if isinstance(argtype, types.Optional):
                underlying_type = getattr(argtype, "type", argtype)

                # make a optional value if the value is not null, otherwise
                # make an none value
                instr = builder.select(
                    is_not_null,
                    context.make_optional_value(builder, underlying_type, raw),
                    context.make_optional_none(builder, underlying_type),
                )
            else:
                with builder.if_else(is_not_null, likely=True) as (then, otherwise):
                    # TODO: should check if a value is null and raise an error if
                    # it is
                    with then:
                        instr = raw
                    with otherwise:
                        gil = pyapi.gil_ensure()
                        pyapi.err_set_string(
                            "PyExc_ValueError",
                            (
                                "encountered unexpected NULL in call to "
                                "user-defined numba function "
                                f"{func.dispatcher.py_func.__name__!r}"
                            ),
                        )
                        pyapi.gil_release(gil)

            # collect the value into an argument list used to build the tuple
            converted_args.append(instr)

        # construct a tuple of arguments (fixed length and known types)
        res = context.make_tuple(builder, tuple_type, converted_args)
        return imputils.impl_ret_borrowed(context, builder, tuple_type, res)

    return sig, codegen


@extending.intrinsic  # type: ignore[misc]
def get_sqlite3_result_function(
    typingctx: Context, value_type: types.Type
) -> Tuple[
    Signature,
    Callable[[BaseContext, Builder, Signature, Tuple[Value, ...]], CastInstr],
]:
    underlying_type = getattr(value_type, "type", value_type)
    func_type = types.void(types.voidptr, underlying_type)

    external_function_pointer = types.ExternalFunctionPointer(
        func_type, ctypes_utils.get_pointer
    )
    sig = external_function_pointer(underlying_type)

    def codegen(
        context: BaseContext,
        builder: Builder,
        signature: Signature,
        args: Tuple[Value, ...],
    ) -> CastInstr:
        # get the appropriate ctypes extraction routine
        ctypes_function = RESULT_SETTERS[value_type]

        # create a numba function type for the converter
        converter = ctypes_utils.make_function_type(ctypes_function)

        # get the function pointer instruction out
        return context.get_constant_generic(builder, converter, ctypes_function)

    return sig, codegen


@extending.intrinsic  # type: ignore[misc]
def sizeof(
    typingctx: Context, src: types.ClassType
) -> Tuple[
    Signature,
    Callable[[BaseContext, Builder, Signature, Tuple[Value, ...]], Constant],
]:
    if isinstance(src, types.ClassType):
        sig = types.int64(src)

        def codegen(
            context: BaseContext,
            builder: Builder,
            signature: Signature,
            args: Tuple[Value, ...],
        ) -> Constant:
            data_type = context.get_data_type(src.instance_type)
            size_of_data_type = context.get_abi_sizeof(data_type)
            return context.get_constant(sig.return_type, size_of_data_type)

        return sig, codegen
    else:
        raise TypeError("Cannot get sizeof non jitclass")


def generate_null_checker(
    func: Callable[[Builder, Value], Value]
) -> Callable[
    [Context, types.ClassInstanceType],
    Tuple[
        Signature,
        Callable[[BaseContext, Builder, Signature, Tuple[Value, ...]], ICMPInstr],
    ],
]:
    def null_pointer_checker(
        typingctx: Context, src: types.ClassInstanceType
    ) -> Tuple[
        Signature,
        Callable[[BaseContext, Builder, Signature, Tuple[Value, ...]], ICMPInstr],
    ]:
        if isinstance(src, types.ClassInstanceType):
            sig = types.boolean(src)

            def codegen(
                context: BaseContext,
                builder: Builder,
                signature: Signature,
                args: Tuple[Value, ...],
            ) -> ICMPInstr:
                (instance,) = args

                # TODO: probably a more general way to do this
                second_element = builder.extract_value(instance, [1])
                return func(builder, second_element)

            return sig, codegen
        else:
            raise TypeError("Cannot check null pointer status of a non-jitclass type")

    return null_pointer_checker


is_null_pointer = extending.intrinsic(generate_null_checker(cgutils.is_null))
is_not_null_pointer = extending.intrinsic(generate_null_checker(cgutils.is_not_null))
