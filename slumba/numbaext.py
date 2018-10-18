from numba import types, extending, cgutils
from numba.targets import imputils
from numba.typing import ctypes_utils

from slumba.sqlite import VALUE_EXTRACTORS, RESULT_SETTERS


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
            inst_struct.meminfo = cgutils.get_null_value(
                inst_struct.meminfo.type)

            # Set data from the given pointer
            inst_struct.data = builder.bitcast(ptr, alloc_type.as_pointer())
            return inst_struct._getvalue()
        return sig, codegen
    else:
        raise TypeError(
            f'Unable to cast pointer type {src} to class type {dst}'
        )


@extending.intrinsic
def make_arg_tuple(typingctx, func, argv):
    (func_type,), _ = func.get_call_signatures()
    first_arg, *_ = args = func_type.args

    # skip the first argument if `func` is a method call
    first_argument_position = int(
        isinstance(first_arg, types.ClassInstanceType))
    argtypes = args[first_argument_position:]
    tuple_type = types.Tuple(argtypes)
    sig = tuple_type(func, types.CPointer(types.voidptr))

    def codegen(context, builder, signature, args):
        _, argv = args
        converted_args = []
        for i, argtype in enumerate(argtypes):

            # get the appropriate ctypes extraction routine
            ctypes_function = VALUE_EXTRACTORS[argtype]

            # create a numba function type for the converter
            converter = ctypes_utils.make_function_type(ctypes_function)

            # get the function pointer instruction out
            fn = context.get_constant_generic(
                builder, converter, ctypes_function)

            # get a pointer to the ith argument
            element_pointer = cgutils.gep(builder, argv, i)

            # deref that pointer
            element = builder.load(element_pointer)

            # call the value extraction routine
            raw = builder.call(fn, [element])

            # if the argument is an optional type then pull out the underlying
            # type and make an optional value with it
            #
            # otherwise the raw value is the argument
            if isinstance(argtype, types.Optional):
                underlying_type = getattr(argtype, 'type', argtype)
                instr = context.make_optional_value(
                    builder, underlying_type, raw
                )
            else:
                instr = raw

            # collect the value into an argument list used to build the tuple
            converted_args.append(instr)

        # construct a tuple using LLVM
        res = context.make_tuple(builder, tuple_type, converted_args)
        return imputils.impl_ret_borrowed(context, builder, tuple_type, res)
    return sig, codegen


@extending.intrinsic
def get_sqlite3_result_function(typingctx, value_type):
    underlying_type = getattr(value_type, 'type', value_type)
    func_type = types.void(types.voidptr, underlying_type)

    external_function_pointer = types.ExternalFunctionPointer(
        func_type, ctypes_utils.get_pointer)
    sig = external_function_pointer(underlying_type)

    def codegen(context, builder, signature, args):
        # get the appropriate ctypes extraction routine
        ctypes_function = RESULT_SETTERS[value_type]

        # create a numba function type for the converter
        converter = ctypes_utils.make_function_type(ctypes_function)

        # get the function pointer instruction out
        fn = context.get_constant_generic(
            builder, converter, ctypes_function)
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
        raise TypeError('Cannot get sizeof non jitclass')


def generate_null_checker(func):
    def null_pointer_checker(typingctx, src):
        if isinstance(src, types.ClassInstanceType):
            sig = types.boolean(src)

            def codegen(context, builder, signature, args):
                instance, = args

                # TODO: probably a more general way to do this
                second_element = builder.extract_value(instance, [1])
                result = func(builder, second_element)
                return result
            return sig, codegen
        else:
            raise TypeError(
                'Cannot check null pointer status of a non-jitclass type')
    return null_pointer_checker


is_null_pointer = extending.intrinsic(generate_null_checker(cgutils.is_null))
is_not_null_pointer = extending.intrinsic(
    generate_null_checker(cgutils.is_not_null))
