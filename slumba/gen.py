from __future__ import division, print_function, absolute_import

from itertools import chain
import ast

from miniast import call, load, TRUE, arg, sub, idx, import_from, alias

from ctypes import CDLL, c_void_p, c_double, c_int, c_int64, c_ubyte, POINTER
from ctypes.util import find_library

from numba import float64, int64


libsqlite3 = CDLL(find_library('sqlite3'))


sqlite3_result_double = libsqlite3.sqlite3_result_double
sqlite3_result_int64 = libsqlite3.sqlite3_result_int64

sqlite3_result_double.argtypes = c_void_p, c_double
sqlite3_result_double.restype = None

sqlite3_result_int64.argtypes = c_void_p, c_int64
sqlite3_result_int64.restype = None


RESULT_SETTERS = {
    float64: sqlite3_result_double,
    int64: sqlite3_result_int64,
}


value_methods = {
    # 'blob': c_void_p,
    # 'bytes': c_int,
    'double': c_double,
    'int': c_int,
    'int64': c_int64,
    # 'text': POINTER(c_ubyte),
    'type': c_int,
}


def add_value_method(typename, restype):
    method = getattr(libsqlite3, 'sqlite3_value_{}'.format(typename))
    method.argtypes = c_void_p,
    method.restype = restype
    return method


locals().update({
    'sqlite3_value_{}'.format(typename): add_value_method(typename, restype)
    for typename, restype in value_methods.items()
})


# TODO: these are introduced by the locals() update above, find a better way
CONVERTERS = {
    float64: sqlite3_value_double,
    int64: sqlite3_value_int64,
}


def generate_function_body(func):
    sig, = func.nopython_signatures
    converters = [CONVERTERS[arg] for arg in sig.args]
    resulter = RESULT_SETTERS[sig.return_type]

    args = [
        call[converter.__name__](sub(load.argv, idx(i)))
        for i, converter in enumerate(converters)
    ]
    result = call[func.__name__](*args)
    return call[resulter.__name__](load.ctx, result)


def gen_def(func, wrapper_name='wrapper'):
    return ast.Module(
        body=[
            import_from.numba[alias.cfunc],
            import_from.numba.types[alias.void, alias.voidptr, alias.intc, alias.CPointer],
            ast.FunctionDef(
                name=wrapper_name,
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
                body=[ast.Expr(value=generate_function_body(func))],
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


class SourceVisitor(ast.NodeVisitor):
    """An AST visitor to show what our generated function looks like.
    """

    def visit_ImportFrom(self, node):
        return 'from {} import {}'.format(
            node.module,
            ', '.join(
                ' as '.join(filter(None, (alias.name, alias.asname)))
                for alias in node.names
            )
        )

    def visit_FunctionDef(self, node):
        template = '{}def {}({}):\n    {}'
        s = template.format(
            '@{}\n'.format('\n'.join(map(self.visit, node.decorator_list))) if node.decorator_list else '',
            node.name,
            ', '.join(map(self.visit, node.args.args)),
            '    \n'.join(map(self.visit, node.body))
        )
        return s

    def visit_Call(self, node):
        return '{}({})'.format(
            node.func.id,
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

    def visit_arg(self, node):
        return node.arg

    def visit_Subscript(self, node):
        return '{}[{}]'.format(self.visit(node.value), self.visit(node.slice))

    def visit_Index(self, node):
        return self.visit(node.value)

    def visit_Module(self, node):
        return '\n'.join(map(self.visit, node.body))


def sourcify(func):
    return SourceVisitor().visit(gen_def(func))


if __name__ == '__main__':
    from math import pi, sqrt, exp
    from numba import jit

    @jit(float64(int64, int64), nopython=True)
    def g(x, y):
        return x + y * 1.0

    # this shows what the compiled function looks like
    print(sourcify(g))
