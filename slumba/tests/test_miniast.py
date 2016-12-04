import ast

import pytest

from slumba.miniast import (
    load,
    store,
    arg,
    call,
    attr,
    idx,
    sub,
    alias,
    import_from,
    NONE,
    TRUE,
    FALSE
)


def eq(a, b):
    """Test equality of AST nodes, because Python doesn't define __eq__ for
    them :(
    """
    if isinstance(a, (ast.Load, ast.Store)):
        return isinstance(b, type(a))
    if isinstance(a, list):
        return isinstance(b, list) and all(map(eq, a, b))
    return a == b or (
        isinstance(a, type(b)) and
        isinstance(b, type(a)) and
        hasattr(a, '_fields') and
        hasattr(b, '_fields') and
        a._fields == b._fields and
        all(eq(getattr(a, field), getattr(b, field)) for field in a._fields)
    )


def test_eq():
    assert not eq(1, 0)
    assert eq('a', 'a')

    assert not eq('a', 1)

    assert not eq(
        ast.Name(id='x', ctx=ast.Load()),
        ast.Name(id='x', ctx=ast.Store())
    )
    assert eq(
        ast.Name(id='x', ctx=ast.Load()),
        ast.Name(id='x', ctx=ast.Load())
    )



def test_load():
    assert eq(load.foo, ast.Name(id='foo', ctx=ast.Load()))
    assert eq(load['bar'], ast.Name(id='bar', ctx=ast.Load()))


def test_store():
    assert eq(store.foo, ast.Name(id='foo', ctx=ast.Store()))
    assert eq(store['bar'], ast.Name(id='bar', ctx=ast.Store()))


def test_arg():
    assert eq(arg.fizzbuzz, ast.arg(arg='fizzbuzz', annotation=None))


def test_call():
    assert eq(
        call.func(),
        ast.Call(
            func=ast.Name(id='func', ctx=ast.Load()), args=[], keywords=[]
        )
    )
    assert eq(
        call.func(load.a, b=load.b),
        ast.Call(
            func=ast.Name(id='func', ctx=ast.Load()),
            args=[ast.Name(id='a', ctx=ast.Load())],
            keywords=[
                ast.keyword(arg='b', value=ast.Name(id='b', ctx=ast.Load()))
            ]
        )
    )


def test_attr():
    assert eq(
        attr.foo.get_a_thing,
        ast.Attribute(
            value=ast.Name(id='foo', ctx=ast.Load()),
            attr='get_a_thing',
            ctx=ast.Load(),
        )
    )


@pytest.mark.parametrize('i', range(5))
def test_idx(i):
    assert eq(idx(i), ast.Index(value=ast.Num(n=i)))


@pytest.mark.parametrize('i', range(5))
def test_sub(i):
    assert eq(
        sub(load.a, idx(i)),
        ast.Subscript(
            value=ast.Name(id='a', ctx=ast.Load()),
            slice=ast.Index(value=ast.Num(n=i)),
            ctx=ast.Load()
        )
    )


def test_alias():
    assert eq(
        alias.foo,
        ast.alias(name='foo', asname=None)
    )
    assert eq(
        alias['foo', 'bar'],
        ast.alias(name='foo', asname='bar')
    )


def test_import_from():
    assert eq(
        import_from.bar[alias.foo, alias['foo', 'baz']],
        ast.ImportFrom(
            module='bar',
            names=[
                ast.alias(name='foo', asname=None),
                ast.alias(name='foo', asname='baz')
            ],
            level=0
        )
    )


def test_constants():
    assert eq(NONE, ast.NameConstant(value=None))
    assert eq(TRUE, ast.NameConstant(value=True))
    assert eq(FALSE, ast.NameConstant(value=False))
