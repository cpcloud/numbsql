from __future__ import division, print_function, absolute_import

from itertools import chain

import re
import ast
import textwrap

from slumba.miniast import (
    call, store, load, TRUE, NONE, arg, sub, idx, import_from, alias, attr
)

from ctypes import CDLL, c_void_p, c_double, c_int, c_int64, c_ubyte, POINTER
from ctypes.util import find_library

from numba import float64, int64, int32, optional
from numba import types


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
    method = getattr(libsqlite3, 'sqlite3_value_{}'.format(typename))
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
    'sqlite3_value_{}'.format(typename): add_value_method(typename, restype)
    for typename, restype in value_methods.items()
}


def unnullify(value, true_function, name, argtype):
    return ast.If(
        test=ast.Compare(
            left=call.sqlite3_value_type(value),
            ops=[ast.NotEq()],
            comparators=[load.SQLITE_NULL]
        ),
        body=[ast.Assign(targets=[store[name]], value=true_function(value))],
        orelse=[ast.Assign(targets=[store[name]], value=NONE)],
    ), None, load[name]


def fail_if_null(value, true_function, name, argtype):
    return ast.If(
        test=ast.Compare(
            left=call.sqlite3_value_type(value),
            ops=[ast.Eq()],
            comparators=[load.SQLITE_NULL]
        ),
        body=[
            ast.Raise(
                exc=call.TypeError(
                    ast.Str(
                        s=(
                            'Argument {0!r} is NULL but argument type was {1}.'
                            ' Please change the argument type to optional({1})'
                            ' to accept NULL values.'
                        ).format(SourceVisitor().visit(value), argtype)
                    )
                ),
                cause=None
            )
        ],
        orelse=[],
    ), ast.Assign(targets=[store[name]], value=true_function(value)), load[name]


def generate_function_body(func):
    sig, = func.nopython_signatures
    converters = [(arg, VALUE_EXTRACTORS[arg]) for arg in sig.args]
    resulter = RESULT_SETTERS[sig.return_type]

    args = []
    sequence = []

    for i, (argtype, converter) in enumerate(converters):
        arg = sub(load.argv, idx(i))
        converter_function = call[converter.__name__]
        argname = 'arg_{:d}'.format(i)
        if isinstance(argtype, types.Optional):
            if_statement, rest, arg = unnullify(arg, converter_function, argname, argtype)
        else:
            if_statement, rest, arg = fail_if_null(arg, converter_function, argname, argtype)

        sequence.append(if_statement)
        if rest is not None:
            sequence.append(rest)
        args.append(arg)

    result = call[func.__name__](*args)
    final_call = call[resulter.__name__](load.ctx, load.result_value)
    return sequence + [
        ast.Assign(targets=[store.result_value], value=result),
        ast.If(
            test=ast.Compare(
                left=load.result_value,
                ops=[ast.IsNot()],
                comparators=[NONE]
            ),
            body=[ast.Expr(value=final_call)],
            orelse=[ast.Expr(value=call.sqlite3_result_null(load.ctx))]
        ) if isinstance(sig.return_type, types.Optional) else (
            ast.Expr(value=final_call)
        )
    ]


def gen_scalar(func, name):
    return ast.Module(
        body=[
            import_from.numba[alias.cfunc],
            import_from.numba.types[
                alias.void,
                alias.voidptr,
                alias.intc,
                alias.CPointer,
            ],
            ast.FunctionDef(
                name=name,
                args=ast.arguments(
                    args=[
                        arg.ctx,
                        arg.argc,
                        arg.argv,
                    ],
                    vararg=None,
                    kwonlyargs=[],
                    kw_defaults=[],
                    kwargs=None,
                    defaults=[],
                ),
                body=generate_function_body(func),
                decorator_list=[
                    call.cfunc(
                        call.void(
                            load.voidptr,
                            load.intc,
                            call.CPointer(load.voidptr)
                        ),
                        nopython=TRUE
                    )
                ],
                returns=None
            )
        ]
    )


def camel_to_snake(name):
    result = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', result).lower()


def gen_step(cls, name):
    class_name = cls.__name__
    sig, = cls.class_type.jitmethods['step'].nopython_signatures
    args = sig.args[1:]

    body = [
        ast.Assign(
            targets=[store['arg_{:d}'.format(i)]],
            value=sub(load.argv, idx(i))
        )
        for i, arg in enumerate(args)
    ]

    step_args = []
    statements = []

    for i, a in enumerate(args):
        if isinstance(a, types.Optional):
            func = unnullify
        else:
            func = fail_if_null
        if_statement, rest, argument = func(
            load['arg_{:d}'.format(i)],
            call[VALUE_EXTRACTORS[a].__name__],
            'value_{:d}'.format(i),
            a
        )
        statements.append(if_statement)
        if rest is not None:
            statements.append(rest)
        step_args.append(argument)

    body.extend([
        ast.Assign(
            targets=[
                store.agg_ctx
            ],
            value=call.unsafe_cast(
                call.sqlite3_aggregate_context(
                    load.ctx,
                    call.sizeof(load[class_name])
                ),
                load[class_name]
            )
        ),
        ast.If(
            test=call.not_null(load.agg_ctx),
            body=statements + [
                ast.Expr(value=call(attr.agg_ctx.step, *step_args))
            ],
            orelse=[]
        )
    ])
    decorator_list = [
        call.cfunc(
            call.void(load.voidptr, load.intc, call.CPointer(load.voidptr)),
            nopython=TRUE
        )
    ]
    function_signature = ast.arguments(
        args=[arg.ctx, arg.argc, arg.argv],
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        kwargs=None,
        defaults=[],
    )
    mod = ast.Module(
        body=[
            import_from.numba[alias.cfunc],
            import_from.numba.types[
                alias.void, alias.voidptr, alias.intc, alias.CPointer
            ],
            ast.FunctionDef(
                name=name,
                args=function_signature,
                body=body,
                decorator_list=decorator_list,
                returns=None
            )
        ]
    )
    return mod


def gen_finalize(cls, name):
    class_name = cls.__name__
    sig, = cls.class_type.jitmethods['finalize'].nopython_signatures
    output_call = ast.Expr(
        value=call[
            RESULT_SETTERS[sig.return_type].__name__
        ](load.ctx, load.final_value)
    )
    final_result = ast.If(
        test=ast.Compare(
            left=load.final_value,
            ops=[ast.IsNot()],
            comparators=[NONE],
        ),
        body=[output_call],
        orelse=[ast.Expr(value=call.sqlite3_result_null(load.ctx))]
    ) if isinstance(sig.return_type, types.Optional) else output_call
    return ast.Module(
        body=[
            # no imports because this is always defined with a step function,
            # which has the imports
            ast.FunctionDef(
                name=name,
                args=ast.arguments(
                    args=[arg.ctx],
                    vararg=None,
                    kwonlyargs=[],
                    kw_defaults=[],
                    kwargs=None,
                    defaults=[],
                ),
                body=[
                    ast.Assign(
                        targets=[
                            store.agg_ctx
                        ],
                        value=call.unsafe_cast(
                            call.sqlite3_aggregate_context(
                                load.ctx,
                                ast.Num(n=0)
                            ),
                            load[class_name]
                        )
                    ),
                    ast.If(
                        test=call.not_null(load.agg_ctx),
                        body=[
                            ast.Assign(
                                targets=[
                                    store.final_value,
                                ],
                                value=call(attr.agg_ctx.finalize)
                            ),
                            final_result,
                        ],
                        orelse=[],
                    )
                ],
                decorator_list=[
                    call.cfunc(call.void(load.voidptr), nopython=TRUE)
                ],
                returns=None
            )
        ]
    )


class SourceVisitor(ast.NodeVisitor):
    """An AST visitor to show what our generated function looks like.
    """

    def visit(self, node):
        node_type = type(node)
        node_typename = node_type.__name__
        method = getattr(self, 'visit_{}'.format(node_typename), None)
        if method is None:
            raise TypeError(
                'Node of type {} has no visit method'.format(node_typename)
            )
        return method(node)

    def visit_If(self, node):
        test = self.visit(node.test)
        spaces = ' ' * 4
        body = textwrap.indent('\n'.join(map(self.visit, node.body)), spaces)
        if node.orelse:
            orelse = textwrap.indent(
                '\n'.join(map(self.visit, node.orelse)),
                spaces
            )
            return 'if {}:\n{}\nelse:\n{}'.format(test, body, orelse)
        return 'if {}:\n{}'.format(test, body)

    def visit_IfExp(self, node):
        return '{} if {} else {}'.format(
            self.visit(node.body),
            self.visit(node.test),
            self.visit(node.orelse),
        )

    def visit_And(self, node):
        return 'and'

    def visit_NotEq(self, node):
        return '!='

    def visit_Eq(self, node):
        return '=='

    def visit_Not(self, node):
        return 'not '

    def visit_IsNot(self, node):
        return 'is not'

    def visit_UnaryOp(self, node):
        return '{}{}'.format(self.visit(node.op), self.visit(node.operand))

    def visit_Compare(self, node):
        left = self.visit(node.left)
        return left + ' '.join(
            ' {} {}'.format(self.visit(op), self.visit(comparator))
            for op, comparator in zip(node.ops, node.comparators)
        )

    def visit_BoolOp(self, node):
        op = self.visit(node.op)
        return ' {} '.format(op).join(map(self.visit, node.values))

    def visit_Attribute(self, node):
        return '{}.{}'.format(self.visit(node.value), node.attr)

    def visit_ImportFrom(self, node):
        return 'from {} import {}'.format(
            node.module,
            ', '.join(
                ' as '.join(filter(None, (alias.name, alias.asname)))
                for alias in node.names
            )
        )

    def visit_Assign(self, node):
        return '{} = {}'.format(
            ', '.join(map(self.visit, node.targets)),
            self.visit(node.value)
        )

    def visit_FunctionDef(self, node):
        return '\n{}def {}({}):\n{}'.format(
            '@{}\n'.format(
                '\n'.join(map(self.visit, node.decorator_list))
            ) if node.decorator_list else '',
            node.name,
            ', '.join(map(self.visit, node.args.args)),
            textwrap.indent(
                '\n'.join(map(self.visit, node.body)),
                ' ' * 4
            )
        )

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            func = self.visit(node.func)
            args = ',\n'.join(chain(
                map(self.visit, node.args),
                (
                    '{}={!r}'.format(kw.arg, self.visit(kw.value))
                    for kw in node.keywords
                )
            ))
            template = '{}(\n{}\n)' if node.args else '{}({})'
            return template.format(func, textwrap.indent(args, ' ' * 4))
        else:
            return '{}({})'.format(
                self.visit(node.func),
                ', '.join(chain(
                    map(self.visit, node.args),
                    (
                        '{}={!r}'.format(kw.arg, self.visit(kw.value))
                        for kw in node.keywords
                    )
                ))
            )

    def visit_NameConstant(self, node):
        return node.value

    def visit_Expr(self, node):
        return self.visit(node.value)

    def visit_Name(self, node):
        return node.id

    def visit_Num(self, node):
        return str(node.n)

    def visit_Str(self, node):
        return repr(node.s)

    def visit_arg(self, node):
        return node.arg

    def visit_Raise(self, node):
        raise_string = 'raise {}'.format(self.visit(node.exc))
        cause = getattr(node, 'cause', None)

        if cause is not None:
            return '{} from {}'.format(raise_string, self.visit(cause))
        return raise_string

    def visit_Subscript(self, node):
        return '{}[{}]'.format(self.visit(node.value), self.visit(node.slice))

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
    print(SourceVisitor().visit(gen_scalar(g, 'g_unit')))
