from numba import types
from numba import extending
from numba import cgutils


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
    if isinstance(src, types.RawPointer) and isinstance(dst, types.ClassType):
        return _unsafe_cast_ptr_to_class(src, dst)
    raise TypeError(
        'Unable to cast pointer type {} to class type {}'.format(src, dst)
    )


@extending.intrinsic
def sizeof(typingctx, src):
    sig = types.int64(src)

    def codegen(context, builder, signature, args):
        return context.get_constant(
            sig.return_type,
            context.get_abi_sizeof(
                context.get_data_type(src.instance_type)
            )
        )
    return sig, codegen
