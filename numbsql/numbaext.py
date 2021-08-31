"""Welcome to hell, or heaven, depending.

This module is a collection of numba extensions that perform operations
of varying levels of danger and complexity needed to make this monstrosity
work correctly.
"""

import contextlib
import inspect
from typing import Any, Callable, Generator, Optional, Tuple

import numba
from llvmlite import ir
from llvmlite.ir.instructions import (
    CallInstr,
    Constant,
    ICMPInstr,
    InsertValue,
    LoadInstr,
    Value,
)
from llvmlite.llvmpy.core import Builder
from numba import extending, types
from numba.core import cgutils, imputils, pythonapi
from numba.core.base import BaseContext
from numba.core.typing import ctypes_utils
from numba.core.typing.context import Context
from numba.core.typing.templates import Signature

from .sqlite import (
    SQLITE3_RESULT_SETTERS,
    SQLITE3_VALUE_EXTRACTORS,
    SQLITE_NULL,
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


@contextlib.contextmanager
def gil(pyapi: pythonapi.PythonAPI) -> Generator[ir.AllocaInstr, None, None]:
    """Generate instructions to hold the GIL."""
    locked_gil = pyapi.gil_ensure()
    try:
        yield locked_gil
    finally:
        pyapi.gil_release(locked_gil)


@extending.intrinsic  # type: ignore[misc]
def unsafe_cast(
    typingctx: Context,
    src: types.Integer,
    dst: types.ClassType,
) -> Tuple[
    Signature,
    Callable[[BaseContext, Builder, Signature, Tuple[Value, Value]], LoadInstr],
]:
    """Cast a void pointer to a `jitclass` type.

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
    if isinstance(src, types.Integer) and isinstance(dst, types.ClassType):
        inst_typ = dst.instance_type
        sig = inst_typ(types.voidptr, dst)

        def codegen(
            context: BaseContext,
            builder: Builder,
            signature: Signature,
            args: Tuple[Value, Value],
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
    Signature,
    Callable[[BaseContext, Builder, Signature, Tuple[Value, Value]], None],
]:
    """Initialize a `jitclass` by calling its constructor."""
    if isinstance(inst_typ, types.ClassInstanceType) and isinstance(
        user_data, types.Integer
    ):
        sig = types.void(inst_typ, types.voidptr)

        def codegen(
            context: BaseContext,
            builder: Builder,
            signature: Signature,
            args: Tuple[Value, Value],
        ) -> None:
            instance, user_data = args

            # cast the user-defined void* payload to bool*
            raw = builder.bitcast(user_data, cgutils.bool_t.as_pointer())

            # generate an if statement to check whether the constructor has
            # been called
            #
            # it's only ever called once, so use `if_unlikely` for better
            # locality
            with cgutils.if_unlikely(builder, builder.not_(builder.load(raw))):
                # pull out the function pointer
                dist_typ = types.Dispatcher(inst_typ.jit_methods["__init__"])
                fn = context.get_function(dist_typ, types.void(inst_typ))

                _add_linking_libs(context, fn)

                # set the blob to True to indicate that the constructor has
                # been called
                builder.store(context.get_constant(types.boolean, True), raw)

                # call the constructor on the instance
                fn(builder, [instance])

        return sig, codegen
    raise TypeError(f"Unable to initialize type {inst_typ}")


def python_signature_to_numba_signature(
    signature: inspect.Signature,
    *,
    self_type: Optional[types.ClassInstanceType] = None,
) -> Signature:
    """Convert a Python `inspect.Signature` object into a numba `Signature`."""
    input_types = []
    parameters = iter(signature.parameters.items())

    try:
        first_name, first_type = next(parameters)
    except StopIteration:
        pass
    else:
        input_types.append(
            extending.as_numba_type(self_type if first_name == "self" else first_type)
        )

    return_ann = signature.return_annotation
    return_type = extending.as_numba_type(
        return_ann if return_ann is not None else types.void
    )

    input_types.extend(
        extending.as_numba_type(param.annotation) for _, param in parameters
    )
    return return_type(*input_types)


@extending.intrinsic  # type: ignore[misc]
def reset_init(
    typingctx: Context,
    user_data: types.Integer,
) -> Tuple[Signature, Callable[[BaseContext, Builder, Signature, Tuple[Value]], None]]:
    """Reset the user data when `finalize` is called.

    This call ensures that the constructor is called the next time the `step`
    method is invoked.

    """
    if isinstance(user_data, types.Integer):
        sig = types.void(types.voidptr)

        def codegen(
            context: BaseContext,
            builder: Builder,
            signature: Signature,
            args: Tuple[Value],
        ) -> None:
            (user_data,) = args
            # cast the user defined data structure, (which is current a pointer
            # to a boolean indicating whether the constructor has been called)
            # to a pointer to bool
            #
            # void pointer is the typical way to customize end-user data
            # structures in C
            raw = builder.bitcast(user_data, cgutils.bool_t.as_pointer())
            builder.store(context.get_constant(types.boolean, False), raw)

        return sig, codegen

    raise TypeError(f"Unable to uninitialize flag of type `{user_data}`")


@extending.intrinsic  # type: ignore[misc]
def safe_decref(
    typingctx: Context,
    pyobject_type: types.RawPointer,
) -> Tuple[Signature, Callable[[BaseContext, Builder, Signature, Tuple[Value]], None]]:
    """Safely decrement the reference count of a Python object.

    Notes
    -----
    This function holds the GIL.

    There is no cause for concerns about performance here: this function is
    only called when the SQLite user data blob is destroyed, which happens when
    a database connection is closed.

    Additionally the GIL is only held if the user data is not a null pointer.
    """
    if isinstance(pyobject_type, types.RawPointer):
        sig = types.void(types.voidptr)

        def codegen(
            context: BaseContext,
            builder: Builder,
            signature: Signature,
            args: Tuple[Value],
        ) -> None:
            (user_data,) = args
            pyapi = context.get_python_api(builder)
            # check whether the pyobject is null, (likely not)
            with cgutils.if_likely(builder, cgutils.is_not_null(builder, user_data)):
                # we can't call decref safely without holding the GIL
                with gil(pyapi):
                    pyapi.decref(user_data)

        return sig, codegen

    raise TypeError(
        f"Unable to decrement the reference count of type `{pyobject_type}`"
    )


@extending.intrinsic  # type: ignore[misc]
def make_arg_tuple(
    typingctx: Context, func: types.Callable, argv: types.CPointer
) -> Tuple[
    Signature,
    Callable[
        [BaseContext, Builder, Signature, Tuple[Value, Value]],
        InsertValue,
    ],
]:
    """Construct a typed argument tuple to pass to a user-defined function."""
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
        args: Tuple[Value, Value],
    ) -> InsertValue:
        # first argument is the instance, and we don't need it here
        _, argv = args

        # initialize a list to hold the converted function arguments
        converted_args = []

        # grab the python API object, which we use in the case of encountering
        # asn unexpected null value
        pyapi = context.get_python_api(builder)

        # make the SQLITE_NULL value type constant available
        sqlite_null = context.get_constant(types.int32, SQLITE_NULL)

        # get a pointer to the sqlite3_value_type C function
        sqlite3_value_type_numba = context.get_constant_generic(
            builder,
            ctypes_utils.make_function_type(sqlite3_value_type),
            sqlite3_value_type,
        )

        for i, argtype in enumerate(argtypes):
            # get a pointer to the ith argument
            sqlite3_value_pointer = cgutils.gep(builder, argv, i, inbounds=True)

            # deref that pointer
            sqlite3_value = builder.load(sqlite3_value_pointer)

            # the previous two instructions are equivalent to the following C code:
            #
            # sqlite3_value** args; // this is passed in
            # args[i] // or *(args + i)

            # call the SQLite C API to get the value type
            value_type = builder.call(sqlite3_value_type_numba, [sqlite3_value])

            # check whether the value is equal to SQLITE_NULL
            is_not_sqlite_null = builder.icmp_signed("!=", value_type, sqlite_null)

            # get the appropriate ctypes extraction routine
            ctypes_function = SQLITE3_VALUE_EXTRACTORS[argtype]

            # create a numba function type for the converter
            converter = ctypes_utils.make_function_type(ctypes_function)

            # get the function pointer instruction out
            fn = context.get_constant_generic(builder, converter, ctypes_function)

            # if the argument is an optional type then pull out the underlying
            # type and make an optional value with it
            #
            # otherwise the raw value is the argument
            raw = builder.call(fn, [sqlite3_value])
            out_type = context.get_value_type(argtype)
            instr = cgutils.alloca_once(builder, out_type)
            underlying_type = getattr(argtype, "type", argtype)

            if isinstance(argtype, types.Optional):
                # branch to handle null values
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
                                    data=builder.inttoptr(raw, sqlite3_value.type),
                                )
                            ),
                        )
                        builder.store(value, instr)

                    with otherwise:
                        # create a none value, because we encounted a NULL
                        none = context.make_optional_none(builder, underlying_type)
                        builder.store(none, instr)
            else:
                # raise an exception if the value is NULL, because the input
                # type is not optional and therefore cannot handle NULLs
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
                                data=builder.inttoptr(raw, sqlite3_value.type),
                            )
                        )

                        builder.store(value, instr)

                    with otherwise:
                        # without the GIL here we're deep in undefined behavior
                        # land
                        with gil(pyapi):
                            pyapi.err_set_string(
                                "PyExc_ValueError",
                                (
                                    "encountered unexpected NULL in call to "
                                    "user-defined numba function "
                                    f"{func.dispatcher.py_func.__name__!r}"
                                ),
                            )

            # instr is a pointer, so we need to dereference it to use it later
            # in the argument tuple
            converted_args.append(builder.load(instr))

        # construct a tuple of arguments (fixed length and known types)
        arg_tuple = context.make_tuple(builder, tuple_type, converted_args)
        return imputils.impl_ret_untracked(context, builder, tuple_type, arg_tuple)

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
    # XXX: Is this actually alway valid?
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


@numba.generated_jit(nopython=True, nogil=True)  # type: ignore[misc]
def sqlite3_result(ctx: types.Integer, value: Any) -> Callable[[Any, Any], Any]:
    func = SQLITE3_RESULT_SETTERS[value]
    return lambda ctx, value: func(ctx, value)


@extending.intrinsic  # type: ignore[misc]
def sizeof(
    typingctx: Context, src: types.ClassType
) -> Tuple[
    Signature,
    Callable[[BaseContext, Builder, Signature, Tuple[Value]], Constant],
]:
    """Return the size in bytes of a type."""
    if isinstance(src, types.ClassType):
        sig = types.int64(src)

        def codegen(
            context: BaseContext,
            builder: Builder,
            signature: Signature,
            args: Tuple[Value],
        ) -> Constant:
            data_type = context.get_data_type(src.instance_type)
            size_of_data_type = context.get_abi_sizeof(data_type)
            return context.get_constant(sig.return_type, size_of_data_type)

        return sig, codegen

    raise TypeError(f"Cannot get ABI size of `{src}`")


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

    raise TypeError(
        f"Cannot check whether a value of type `{raw_pointer_type}` "
        "is not a null pointer"
    )
