from numba import types, extending, cgutils
from numba.targets import imputils
from numba.typing import ctypes_utils

from slumba.sqlite import VALUE_EXTRACTORS, RESULT_SETTERS


def _unsafe_cast_ptr_to_class(int_type, class_type):
    inst_typ = class_type.instance_type
    sig = inst_typ(types.voidptr, class_type)

    def codegen(context, builder, signature, args):
        ptr, _ = args
        alloc_type = context.get_data_type(inst_typ.get_data_type())

        inst_struct = context.make_helper(builder, inst_typ)

        # Set meminfo to NULL
        inst_struct.meminfo = cgutils.get_null_value(inst_struct.meminfo.type)

        # Set data from the given pointer
        inst_struct.data = builder.bitcast(ptr, alloc_type.as_pointer())
        return inst_struct._getvalue()

    return sig, codegen


@extending.intrinsic
def unsafe_cast(typingctx, src, dst):
    """Cast a voidptr to a jitclass
    """
    if isinstance(src, (types.RawPointer, types.Integer)) and isinstance(
        dst, types.ClassType
    ):
        return _unsafe_cast_ptr_to_class(src, dst)
    raise TypeError(
        'Unable to cast pointer type {} to class type {}'.format(src, dst)
    )


@extending.intrinsic
def make_arg_tuple(typingctx, func, argv):
    (func_type,), _ = func.get_call_signatures()
    args = func_type.args

    # skip the first argument if `func` is a method call
    argtypes = args[isinstance(args[0], types.ClassInstanceType):]
    tuple_type = types.Tuple(argtypes)
    sig = tuple_type(func, types.CPointer(types.voidptr))

    def codegen(context, builder, signature, args):
        _, argv = args
        converted_args = []
        for i, argtype in enumerate(argtypes):
            # get the appropriate ctypes extraction routine
            ctypes_function = VALUE_EXTRACTORS[argtype.type]

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
            instr = context.make_optional_value(builder, argtype.type, raw)

            # put the value into a list used to build a tuple
            converted_args.append(instr)

        res = context.make_tuple(builder, tuple_type, converted_args)
        return imputils.impl_ret_borrowed(context, builder, tuple_type, res)
    return sig, codegen


@extending.intrinsic
def get_sqlite3_result_function(typingctx, value_type):
    func_type = types.void(
        types.voidptr, getattr(value_type, 'type', value_type))

    efp = types.ExternalFunctionPointer(
        func_type, ctypes_utils.get_pointer)
    sig = efp(result)

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
    sig = types.int64(src)

    def codegen(context, builder, signature, args):
        return context.get_constant(
            sig.return_type,
            context.get_abi_sizeof(context.get_data_type(src.instance_type))
        )
    if isinstance(src, types.ClassType):
        return sig, codegen
    raise TypeError()


@extending.intrinsic
def not_null(typingctx, src):
    sig = types.boolean(src)

    def codegen(context, builder, signature, args):
        instance, = args

        # TODO: probably a more general way to do this
        second_element = builder.extract_value(instance, [1])
        result = cgutils.is_not_null(builder, second_element)
        return result

    if isinstance(src, types.ClassInstanceType):
        return sig, codegen

    raise TypeError()
