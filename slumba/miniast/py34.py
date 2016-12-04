"""
Constructing Python ASTs in Python is quite verbose, let's clean it up a bit.
"""

from .base import *


class Call(object):
    __slots__ = ()

    def __getitem__(self, key):
        return lambda *args, **kwargs: ast.Call(
            func=load[key],
            args=list(args),
            keywords=[
                ast.keyword(arg=arg, value=value)
                for arg, value in kwargs.items()
            ],
            starargs=None,
            kwargs=None,
        )

    __getattr__ = __getitem__

    def __call__(self, callable, *args, **kwargs):
        return lambda *args, **kwargs: ast.Call(
            func=callable,
            args=list(args),
            keywords=[
                ast.keyword(arg=arg, value=value)
                for arg, value in kwargs.items()
            ],
            starargs=None,
            kwargs=None,
        )


call = Call()
