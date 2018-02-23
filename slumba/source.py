import ast
import itertools
import textwrap


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

    def visit_BinOp(self, node):
        left, op, right = node.left, node.op, node.right
        return f'{self.visit(left)} {self.visit(op)} {self.visit(right)}'

    def visit_Add(self, node):
        return '+'

    def visit_Sub(self, node):
        return '-'

    def visit_Mult(self, node):
        return '*'

    def visit_Div(self, node):
        return '/'

    def visit_FloorDiv(self, node):
        return '//'

    def visit_Pow(self, node):
        return '**'

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

    def visit_Or(self, node):
        return 'or'

    def visit_Lt(self, node):
        return '<'

    def visit_LtE(self, node):
        return '<='

    def visit_Gt(self, node):
        return '>'

    def visit_GtE(self, node):
        return '>='

    def visit_In(self, node):
        return 'in'

    def visit_NotIn(self, node):
        return 'not in'

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
            args = ',\n'.join(itertools.chain(
                map(self.visit, node.args),
                (f'{kw.arg}={self.visit(kw.value)!r}' for kw in node.keywords)
            ))
            indented_args = textwrap.indent(args, ' ' * 4)
            template = (
                f'(\n{indented_args}\n)' if args else f'({indented_args})'
            )
            return f'{func}{template}'
        else:
            args = ', '.join(itertools.chain(
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

    def visit_ClassDef(self, node):

        bases = list(map(self.visit, node.bases))
        keywords = node.keywords
        string = f'class {node.name}'

        if bases:
            string += f"({', '.join(bases)}"

        import pdb; pdb.set_trace()  # noqa
        if keywords:
            kwargs = ', '.join(
                f'{k.arg}={self.visit(k.value)}' for k in keywords
            )
            string += f", {kwargs}"

        if bases or keywords:
            string += ')'

        body = textwrap.indent('\n'.join(map(self.visit, node.body)), ' ' * 4)
        return string + f':{body}'


def sourcify(mod):
    return SourceVisitor().visit(mod)
