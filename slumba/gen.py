from itertools import chain

import ast
import re
import textwrap

from slumba.miniast import (
    call, store, load, TRUE, NONE, arg, import_from, alias, attr, if_, def_,
    decorate, mod, ifelse, return_
)

from ctypes import CDLL, c_void_p, c_double, c_int, c_int64, c_ubyte, POINTER
from ctypes.util import find_library

from numba import float64, int64, int32, optional


libsqlite3 = CDLL(find_library('sqlite3'))


sqlite3_result_double = libsqlite3.sqlite3_result_double
sqlite3_result_int64 = libsqlite3.sqlite3_result_int64
sqlite3_result_int = libsqlite3.sqlite3_result_int
sqlite3_result_null = libsqlite3.sqlite3_result_null

sqlite3_result_double.argtypes = c_void_p, c_double
sqlite3_result_double.restype = None

sqlite3_result_int64.argtypes = c_void_p, c_int64
sqlite3_result_int64.restype = None

sqlite3_result_int.argtypes = c_void_p, c_int
sqlite3_result_int.restype = None

sqlite3_result_null.argtypes = c_void_p,
sqlite3_result_null.restype = None


RESULT_SETTERS = {
    optional(float64): sqlite3_result_double,
    optional(int64): sqlite3_result_int64,
    optional(int32): sqlite3_result_int,
    float64: sqlite3_result_double,
    int64: sqlite3_result_int64,
    int32: sqlite3_result_int,
}


value_methods = {
    'blob': c_void_p,
    'bytes': c_int,
    'double': c_double,
    'int': c_int,
    'int64': c_int64,
    'text': POINTER(c_ubyte),
    'type': c_int,
}


def add_value_method(typename, restype):
    method = getattr(libsqlite3, f'sqlite3_value_{typename}')
    method.argtypes = c_void_p,
    method.restype = restype
    return method


VALUE_EXTRACTORS = {
    optional(float64): add_value_method('double', c_double),
    optional(int64): add_value_method('int64', c_int64),
    optional(int32): add_value_method('int', c_int),
    float64: add_value_method('double', c_double),
    int64: add_value_method('int64', c_int64),
    int32: add_value_method('int', c_int),
}


CONVERTERS = {
    f'sqlite3_value_{typename}': add_value_method(typename, restype)
    for typename, restype in value_methods.items()
}


def unnullify(value, true_function, name):
    # condition = sqlite3_value_type(value) == SQLITE_NULL
    # name = true_function(value) if condition else None
    stored_var = store[name].assign(
        ifelse(
            call.sqlite3_value_type(value) != load.SQLITE_NULL,
            true_function(value),
            NONE
        )
    )
    return stored_var


def generate_function_body(func, *, skipna):
    sig, = func.nopython_signatures
    converters = ((arg, VALUE_EXTRACTORS[arg]) for arg in sig.args)
    resulter = RESULT_SETTERS[sig.return_type]

    args = []
    sequence = []

    for i, (argtype, converter) in enumerate(converters):
        argname = f'arg_{i:d}'

        if_statement = unnullify(
            load.argv[i], call[converter.__name__], argname
        )

        sequence.append(if_statement)

        if skipna:
            sequence.append(
                if_(
                    load[argname].is_(NONE),
                    [
                        call.sqlite3_result_null(load.ctx),
                        return_()
                    ]
                )
            )
        args.append(load[argname])

    result = call[func.__name__](*args)
    final_call = call[resulter.__name__](load.ctx, load.result_value)
    return sequence + [
        store.result_value.assign(result),
        if_(
            load.result_value.is_not(NONE),
            final_call,
            call.sqlite3_result_null(load.ctx)
        )
    ]


def gen_scalar(func, name, *, skipna):
    return mod(
        # from numba import cfunc
        import_from.numba[alias.cfunc],

        # from numba.types import void, voidptr, intc, CPointer
        import_from.numba.types[
            alias.void,
            alias.voidptr,
            alias.intc,
            alias.CPointer,
        ],

        # @cfunc(void(voidptr, intc, CPointer(voidptr)))
        decorate(
            call.cfunc(
                call.void(
                    load.voidptr,
                    load.intc,
                    call.CPointer(load.voidptr)
                ),
                nopython=TRUE
            )
        )(
            # def func(ctx, argc, argv):
            #     *body
            def_[name](arg.ctx, arg.argc, arg.argv)(
                *generate_function_body(func, skipna=skipna),
                returns=None
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

    body = [store[f'arg_{i:d}'].assign(load.argv[i]) for i in range(len(args))]

    step_args = []
    statements = []

    for i, a in enumerate(args):
        argname = f'value_{i:d}'
        if_statement = unnullify(
            load[f'arg_{i:d}'],
            call[VALUE_EXTRACTORS[a].__name__],
            argname,
        )
        statements.append(if_statement)
        if skipna:
            statements.append(
                if_(
                    load[argname].is_(NONE),
                    [
                        call.sqlite3_result_null(load.ctx),
                        return_()
                    ]
                )
            )
        step_args.append(load[argname])

    body.extend([
        store.agg_ctx.assign(
            call.unsafe_cast(
                call.sqlite3_aggregate_context(
                    load.ctx,
                    call.sizeof(load[class_name])
                ),
                load[class_name]
            )
        ),
        if_(
            call.not_null(load.agg_ctx),
            statements + [call(attr.agg_ctx.step, *step_args)]
        )
    ])
    module = mod(
        import_from.numba[alias.cfunc],
        import_from.numba.types[
            alias.void, alias.voidptr, alias.intc, alias.CPointer
        ],
        decorate(
            call.cfunc(
                call.void(
                    load.voidptr, load.intc, call.CPointer(load.voidptr)
                ),
                nopython=TRUE
            )
        )(
            def_[name](arg.ctx, arg.argc, arg.argv)(
                *body,
                returns=None
            )
        )
    )

    return module


def gen_finalize(cls, name):
    class_name = cls.__name__
    sig, = cls.class_type.jitmethods['finalize'].nopython_signatures
    output_call = call[RESULT_SETTERS[sig.return_type].__name__](
        load.ctx, load.final_value
    )
    final_result = if_(
        load.final_value.is_not(NONE),
        output_call,
        call.sqlite3_result_null(load.ctx)
    )
    return mod(
        # no imports because this is always defined with a step function,
        # which has the imports
        decorate(
            call.cfunc(call.void(load.voidptr), nopython=TRUE)
        )(
            def_[name](arg.ctx)(
                store.agg_ctx.assign(
                    call.unsafe_cast(
                        call.sqlite3_aggregate_context(load.ctx, 0),
                        load[class_name]
                    )
                ),
                if_(
                    call.not_null(load.agg_ctx),
                    [
                        store.final_value.assign(call(attr.agg_ctx.finalize)),
                        final_result,
                    ],
                ),
                returns=None
            )
        )
    )


class SourceVisitor(ast.NodeVisitor):
    """An AST visitor to show what our generated function looks like.
    """

    def visit(self, node):
        node_type = type(node)
        node_typename = node_type.__name__
        method = getattr(self, f'visit_{node_typename}', None)
        if method is None:
            raise TypeError(
                f'Node of type {node_typename} has no visit method'
            )
        return method(node)

    def visit_NoneType(self, node):
        return ''

    def visit_If(self, node):
        test = self.visit(node.test)
        spaces = ' ' * 4
        body = textwrap.indent('\n'.join(map(self.visit, node.body)), spaces)
        if node.orelse:
            orelse = textwrap.indent(
                '\n'.join(map(self.visit, node.orelse)),
                spaces
            )
            return f'if {test}:\n{body}\nelse:\n{orelse}'
        return f'if {test}:\n{body}'

    def visit_IfExp(self, node):
        body = self.visit(node.body)
        test = self.visit(node.test)
        orelse = self.visit(node.orelse)
        return f'{body} if {test} else {orelse}'

    def visit_And(self, node):
        return 'and'

    def visit_NotEq(self, node):
        return '!='

    def visit_Eq(self, node):
        return '=='

    def visit_Not(self, node):
        return 'not '

    def visit_Is(self, node):
        return 'is'

    def visit_IsNot(self, node):
        return 'is not'

    def visit_UnaryOp(self, node):
        return f'{self.visit(node.op)}{self.visit(node.operand)}'

    def visit_Compare(self, node):
        left = self.visit(node.left)
        return left + ' '.join(
            f' {self.visit(op)} {self.visit(comparator)}'
            for op, comparator in zip(node.ops, node.comparators)
        )

    def visit_BoolOp(self, node):
        left, op, right = node.left, node.op, node.right
        return f'{self.visit(left)} {self.visit(op)} {self.visit(right)}'

    def visit_Or(self, node):
        return 'or'

    def visit_Return(self, node):
        return f'return {self.visit(node.value)}'

    def visit_Attribute(self, node):
        return f'{self.visit(node.value)}.{node.attr}'

    def visit_ImportFrom(self, node):
        imports = ', '.join(
            ' as '.join(filter(None, (alias.name, alias.asname)))
            for alias in node.names
        )
        return f'from {node.module} import {imports}'

    def visit_Assign(self, node):
        target = ', '.join(map(self.visit, node.targets))
        return f'{target} = {self.visit(node.value)}'

    def visit_FunctionDef(self, node):
        decorator_list = '\n'.join(map(self.visit, node.decorator_list))
        decorators = f'@{decorator_list}\n' if decorator_list else ''
        args = ', '.join(map(self.visit, node.args.args))
        body = textwrap.indent(
            '\n'.join(map(self.visit, node.body)),
            ' ' * 4
        )
        return f'\n{decorators}def {node.name}({args}):\n{body}'

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            func = self.visit(node.func)
            args = ',\n'.join(chain(
                map(self.visit, node.args),
                (f'{kw.arg}={self.visit(kw.value)!r}' for kw in node.keywords)
            ))
            indented_args = textwrap.indent(args, ' ' * 4)
            template = (
                f'(\n{indented_args}\n)' if args else '({indented_args})'
            )
            return f'{func}{template}'
        else:
            args = ', '.join(chain(
                map(self.visit, node.args),
                (f'{kw.arg}={self.visit(kw.value)!r}' for kw in node.keywords)
            ))
            return f'{self.visit(node.func)}({args})'

    def visit_NameConstant(self, node):
        return node.value

    def visit_Expr(self, node):
        return self.visit(node.value)

    def visit_Name(self, node):
        return node.id

    visit_Variable = visit_Name

    def visit_Num(self, node):
        return str(node.n)

    def visit_Str(self, node):
        return repr(node.s)

    def visit_arg(self, node):
        return node.arg

    def visit_Raise(self, node):
        raise_string = f'raise {self.visit(node.exc)}'
        cause = getattr(node, 'cause', None)

        if cause is not None:
            return f'{raise_string} from {self.visit(cause)}'
        return raise_string

    def visit_Subscript(self, node):
        value = self.visit(node.value)
        slice = self.visit(node.slice)
        return f'{value}[{slice}]'

    def visit_Index(self, node):
        return self.visit(node.value)

    def visit_Module(self, node):
        return '\n'.join(map(self.visit, node.body))


def sourcify(mod):
    return SourceVisitor().visit(mod)


if __name__ == '__main__':
    from numba import jit

    @jit(float64(int64, int64), nopython=True)
    def g(x, y):
        return x + y * 1.0

    # this shows what the compiled function looks like
    module = gen_scalar(g, 'g_unit', skipna=True)
    print(sourcify(module))
