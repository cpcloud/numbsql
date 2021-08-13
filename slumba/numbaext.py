from numba import extending, types
from numba.core import cgutils, imputils
from numba.core.typing import ctypes_utils

from slumba.cslumba import SQLITE_NULL
from slumba.sqlite import RESULT_SETTERS, VALUE_EXTRACTORS, sqlite3_value_type


@extending.intrinsic
def unsafe_cast(typingctx, src, dst):
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

    Returns
    -------
    """
    if isinstance(src, (types.RawPointer, types.Integer)) and isinstance(
        dst, types.ClassType
    ):
        inst_typ = dst.instance_type
        sig = inst_typ(types.voidptr, dst)

        def codegen(context, builder, signature, args):
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


@extending.intrinsic
def make_arg_tuple(typingctx, func, argv):
    (func_type,), _ = func.get_call_signatures()
    first_arg, *_ = args = func_type.args

    # skip the first argument if `func` is a method call
    first_argument_position = int(isinstance(first_arg, types.ClassInstanceType))
    argtypes = args[first_argument_position:]
    tuple_type = types.Tuple(argtypes)
    sig = tuple_type(func, types.CPointer(types.voidptr))

    def codegen(context, builder, signature, args):
        _, argv = args
        converted_args = []
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
            is_null = cgutils.is_true(
                builder, builder.icmp_signed("==", value_type, sqlite_null)
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

                # make an optional none if the value is null, otherwise
                # make an optional value from the raw
                instr = builder.select(
                    is_null,
                    context.make_optional_none(builder, underlying_type),
                    context.make_optional_value(builder, underlying_type, raw),
                )
            else:
                # TODO: should check if a value is null and raise an error if
                # it is
                instr = raw

            # collect the value into an argument list used to build the tuple
            converted_args.append(instr)

        # construct a tuple (fixed length and known types) similar to tuples in
        # statically typed languages
        res = context.make_tuple(builder, tuple_type, converted_args)
        return imputils.impl_ret_borrowed(context, builder, tuple_type, res)

    return sig, codegen


@extending.intrinsic
def get_sqlite3_result_function(typingctx, value_type):
    underlying_type = getattr(value_type, "type", value_type)
    func_type = types.void(types.voidptr, underlying_type)

    external_function_pointer = types.ExternalFunctionPointer(
        func_type, ctypes_utils.get_pointer
    )
    sig = external_function_pointer(underlying_type)

    def codegen(context, builder, signature, args):
        # get the appropriate ctypes extraction routine
        ctypes_function = RESULT_SETTERS[value_type]

        # create a numba function type for the converter
        converter = ctypes_utils.make_function_type(ctypes_function)

        # get the function pointer instruction out
        fn = context.get_constant_generic(builder, converter, ctypes_function)
        return fn

    return sig, codegen


@extending.intrinsic
def sizeof(typingctx, src):
    if isinstance(src, types.ClassType):
        sig = types.int64(src)

        def codegen(context, builder, signature, args):
            data_type = context.get_data_type(src.instance_type)
            size_of_data_type = context.get_abi_sizeof(data_type)
            return context.get_constant(sig.return_type, size_of_data_type)

        return sig, codegen
    else:
        raise TypeError("Cannot get sizeof non jitclass")


def generate_null_checker(func):
    def null_pointer_checker(typingctx, src):
        if isinstance(src, types.ClassInstanceType):
            sig = types.boolean(src)

            def codegen(context, builder, signature, args):
                (instance,) = args

                # TODO: probably a more general way to do this
                second_element = builder.extract_value(instance, [1])
                result = func(builder, second_element)
                return result

            return sig, codegen
        else:
            raise TypeError("Cannot check null pointer status of a non-jitclass type")

    return null_pointer_checker


is_null_pointer = extending.intrinsic(generate_null_checker(cgutils.is_null))
is_not_null_pointer = extending.intrinsic(generate_null_checker(cgutils.is_not_null))
