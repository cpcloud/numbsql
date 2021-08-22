"""Welcome to hell, or heaven, depending.

This module is a collection of numba extensions that perform operations
of varying levels of danger and complexity needed to make this monstrosity
work correctly.
"""
from typing import Callable, Tuple, Union

import numba
from llvmlite.ir.instructions import (
    CallInstr,
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

from .sqlite import (
    RESULT_SETTERS,
    SQLITE_NULL,
    VALUE_EXTRACTORS,
    sqlite3_value_type,
    strlen,
)


def _add_linking_libs(context: BaseContext, call: CallInstr) -> None:
    """Add the required libs for the callable to allow inlining."""
    try:
        libs = call.libs
    except AttributeError:
        pass
    else:
        context.add_linking_libs(libs)


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

            # get the llvm type of the thing that would be allocated
            alloc_type = context.get_data_type(inst_typ.get_data_type())

            # TODO: understand what this does exactly
            inst_struct = context.make_helper(builder, inst_typ)

            # Set meminfo to correctly typed NULL value
            #
            # If you don't set this attribute to a NULL value, then numba
            # thinks it owns the memory, when in fact SQLite is the owner.
            inst_struct.meminfo = cgutils.get_null_value(inst_struct.meminfo.type)

            # Set data from the given pointer
            #
            # This is effectively a reinterpret cast, fun.
            inst_struct.data = builder.bitcast(ptr, alloc_type.as_pointer())

            # don't track this structure with NRT because the memory is owned
            # by SQLite
            return imputils.impl_ret_untracked(
                context, builder, inst_typ, inst_struct._getvalue()
            )

        return sig, codegen

    raise TypeError(f"Unable to cast pointer type {src} to class type {dst}")


@extending.intrinsic  # type: ignore[misc]
def init(
    typingctx: Context,
    inst_typ: types.ClassInstanceType,
    user_data: types.Integer,
) -> Tuple[
    Signature, Callable[[BaseContext, Builder, Signature, Tuple[Value, ...]], None]
]:
    """Initialize a jitclass by calling its constructor.

    Parameters
    ----------
    typingctx
    """
    if isinstance(inst_typ, types.ClassInstanceType) and isinstance(
        user_data, types.Integer
    ):
        sig = types.void(inst_typ, types.voidptr)

        def codegen(
            context: BaseContext,
            builder: Builder,
            signature: Signature,
            args: Tuple[Value, ...],
        ) -> None:
            instance, user_data = args

            # cast the user-defined void* payload to bool*
            raw = builder.bitcast(user_data, cgutils.bool_t.as_pointer())

            # generate a basic block to check if the constructor has been
            # called
            #
            # it's only ever called once, so set likely=False for better cache
            # locality
            with builder.if_then(builder.not_(builder.load(raw)), likely=False):
                # pull out the function pointer
                dist_typ = types.Dispatcher(inst_typ.jit_methods["__init__"])
                fnty = types.void(inst_typ)
                fn = context.get_function(dist_typ, fnty)

                _add_linking_libs(context, fn)

                # set the blob to True to indicate that the constructor has
                # been called
                builder.store(context.get_constant(types.boolean, True), raw)

                # call the constructor on the instance
                fn(builder, [instance])

        return sig, codegen
    raise TypeError(f"Unable to initialize type {inst_typ}")


@extending.intrinsic  # type: ignore[misc]
def reset_init(
    typingctx: Context,
    user_data_type: types.Integer,
) -> Tuple[
    Signature, Callable[[BaseContext, Builder, Signature, Tuple[Value, ...]], None]
]:
    """Reset the init when finalize is called to ensure the constructor is called again.

    Parameters
    ----------
    typingctx
    user_data_type
    """
    if isinstance(user_data_type, types.Integer):
        sig = types.void(types.voidptr)

        def codegen(
            context: BaseContext,
            builder: Builder,
            signature: Signature,
            args: Tuple[Value, ...],
        ) -> None:
            (user_data,) = args
            # cast the user defined data structure, (which is current a pointer
            # to a boolean indicating whether the constructor has been called)
            # to a pointer to bool
            #
            # we pass around voidptrs because that's really the only way to
            # customize end-user data structures in C
            raw = builder.bitcast(user_data, cgutils.bool_t.as_pointer())
            builder.store(context.get_constant(types.boolean, False), raw)

        return sig, codegen
    raise TypeError(f"Unable to uninitialize type {user_data_type}")


@extending.intrinsic  # type: ignore[misc]
def safe_decref(
    typingctx: Context, pyobject: types.RawPointer
) -> Tuple[
    Signature, Callable[[BaseContext, Builder, Signature, Tuple[Value, ...]], None]
]:
    """Safely decrement the reference count of a PyObject*.

    Parameters
    ----------
    typingctx
    user_data_type
    """
    if isinstance(pyobject, types.RawPointer):
        sig = types.void(types.voidptr)

        def codegen(
            context: BaseContext,
            builder: Builder,
            signature: Signature,
            args: Tuple[Value, ...],
        ) -> None:
            (user_data,) = args
            pyapi = context.get_python_api(builder)
            # check whether the pyobject is null, (likely not)
            with builder.if_then(cgutils.is_not_null(builder, user_data), likely=True):
                # we can't call decref safely without holding the GIL
                gil = pyapi.gil_ensure()
                pyapi.decref(user_data)
                pyapi.gil_release(gil)

        return sig, codegen
    raise TypeError(f"Unable to decref type {pyobject}")


@extending.intrinsic  # type: ignore[misc]
def make_arg_tuple(
    typingctx: Context, func: types.Callable, argv: types.CPointer
) -> Tuple[
    Signature,
    Callable[[BaseContext, Builder, Signature, Tuple[Value, ...]], InsertValue],
]:
    """Construct a typed argument tuple to pass to a UD(A)F."""
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

        # make the SQLITE_NULL value type constant available
        sqlite_null = context.get_constant(types.int32, SQLITE_NULL)

        for i, argtype in enumerate(argtypes):
            # get a pointer to the sqlite3_value_type C function
            sqlite3_value_type_numba = context.get_constant_generic(
                builder,
                ctypes_utils.make_function_type(sqlite3_value_type),
                sqlite3_value_type,
            )

            # get a pointer to the ith argument
            element_pointer = cgutils.gep(builder, argv, i, inbounds=True)

            # deref that pointer
            element = builder.load(element_pointer)

            # get the value type
            value_type = builder.call(sqlite3_value_type_numba, [element])

            # check whether the value is equal to SQLITE_NULL
            is_not_sqlite_null = cgutils.is_true(
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
            out_type = context.get_value_type(argtype)
            instr = cgutils.alloca_once(builder, out_type)
            underlying_type = getattr(argtype, "type", argtype)

            if isinstance(argtype, types.Optional):

                with builder.if_else(is_not_sqlite_null) as (then, otherwise):
                    with then:
                        # you _must_ put code that only executes in this block,
                        # in the part of the context manager that will execute
                        # it, otherwise the code outside of the block can be
                        # executed unconditionally, leading to sadness
                        #
                        # in this case, we put string wrapping here so that
                        # strlen isn't called on invalid data
                        value = context.make_optional_value(
                            builder,
                            underlying_type,
                            (
                                raw
                                if not isinstance(underlying_type, types.UnicodeType)
                                else map_sqlite_string_to_numba_uni_str(
                                    context,
                                    builder,
                                    data=builder.inttoptr(raw, element.type),
                                )
                            ),
                        )
                        builder.store(value, instr)

                    with otherwise:
                        # create a none value, because we encounted a NULL
                        none = context.make_optional_none(builder, underlying_type)
                        builder.store(none, instr)
            else:
                # check for NULLs, and raise an exception if the value is NULL,
                # because the input doesn't have an option type
                #
                # favor the branch where the value isn't null, since it's
                # an error condition to accept null values without an option type
                with builder.if_else(is_not_sqlite_null, likely=True) as (
                    then,
                    otherwise,
                ):
                    with then:
                        value = (
                            raw
                            if not isinstance(underlying_type, types.UnicodeType)
                            else map_sqlite_string_to_numba_uni_str(
                                context,
                                builder,
                                data=builder.inttoptr(raw, element.type),
                            )
                        )

                        builder.store(value, instr)

                    with otherwise:
                        # without the GIL here we're deep in undefined behavior
                        # land
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

            # instr is a pointer, so we need to dereference it to use it later
            # in the argument tuple
            converted_args.append(builder.load(instr))

        # construct a tuple of arguments (fixed length and known types)
        res = context.make_tuple(builder, tuple_type, converted_args)
        return imputils.impl_ret_new_ref(context, builder, tuple_type, res)

    return sig, codegen


def map_sqlite_string_to_numba_uni_str(
    context: BaseContext,
    builder: Builder,
    *,
    data: Value,
) -> LoadInstr:
    """Construct a Numba string from a raw C string coming from SQLite.

    There's no way this implementation is correct.

    Notes
    -----
    This implementation is probably FULL of undefined behavior

    We tell numba to treat a const unsigned char* coming from SQLite as a
    numba-unmanaged unicode string.
    """
    # construct a numba-aware struct wrapper for a string
    uni_str = cgutils.create_struct_proxy(types.string)(context, builder)

    # point it at the SQLite string data
    uni_str.data = data

    # compute the length of the string
    uni_str.length = builder.call(
        context.get_constant_generic(
            builder,
            ctypes_utils.make_function_type(strlen),
            strlen,
        ),
        [data],
    )

    # This is the Python string kind, which numba will use in various string
    # algorithms.
    #
    # TODO: figure out how this maps to the different SQLite text types.
    uni_str.kind = uni_str.kind.type(numba.cpython.unicode.PY_UNICODE_1BYTE_KIND)

    # SQLite strings are never guaranteed to be anything really, and most
    # certainly not ASCII.
    uni_str.is_ascii = builder.zext(
        context.get_constant(types.boolean, False), uni_str.is_ascii.type
    )

    # Tell numba to forget about owning the data, because SQLite owns it.
    uni_str.meminfo = cgutils.get_null_value(uni_str.meminfo.type)

    # Cribbed from numba string construction code
    #
    # Set hash to -1 to indicate that it should be computed.
    #
    # We cannot bake in the hash value because of hashseed
    # randomization.
    uni_str.hash = uni_str.hash.type(-1)
    return uni_str._getvalue()


@extending.intrinsic  # type: ignore[misc]
def get_sqlite3_result_function(
    typingctx: Context, value_type: types.Type
) -> Tuple[
    Signature,
    Callable[[BaseContext, Builder, Signature, Tuple[Value, ...]], CastInstr],
]:
    """Return the correct result setting function for the given type."""
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
        # get the appropriate setter function
        result_setter = RESULT_SETTERS[value_type]

        # create a numba function type for the converter
        converter = ctypes_utils.make_function_type(result_setter)

        # get the function pointer instruction out
        return context.get_constant_generic(builder, converter, result_setter)

    return sig, codegen


@extending.intrinsic  # type: ignore[misc]
def sizeof(
    typingctx: Context, src: types.ClassType
) -> Tuple[
    Signature,
    Callable[[BaseContext, Builder, Signature, Tuple[Value, ...]], Constant],
]:
    """Return the size in bytes of a type."""
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


@extending.intrinsic  # type: ignore[misc]
def is_not_null_pointer(
    typingctx: Context, raw_pointer_type: types.Integer
) -> Tuple[
    Signature,
    Callable[[BaseContext, Builder, Signature, Tuple[Value]], ICMPInstr],
]:
    if isinstance(raw_pointer_type, types.Integer):
        sig = types.boolean(raw_pointer_type)

        def codegen(
            context: BaseContext,
            builder: Builder,
            signature: Signature,
            args: Tuple[Value],
        ) -> ICMPInstr:
            return cgutils.is_not_null(builder, *args)

        return sig, codegen

    raise TypeError(f"Cannot check whether a {raw_pointer_type} is not a null pointer")
