import ast


class Load(object):
    __slots__ = ()

    def __getitem__(self, key):
        return ast.Name(id=key, ctx=ast.Load())

    __getattr__ = __getitem__


load = Load()


class Store(object):
    __slots__ = ()

    def __getitem__(self, key):
        return ast.Name(id=key, ctx=ast.Store())

    __getattr__ = __getitem__


store = Store()


class Arg(object):
    __slots__ = ()

    def __getitem__(self, key):
        return ast.arg(arg=key, annotation=None)

    __getattr__ = __getitem__


arg = Arg()


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
        )

    __getattr__ = __getitem__


### API
# load.foo == ast.Name('foo', ctx=ast.Load())

call = Call()

### API
# call.func(load.foo, nopython=TRUE)


class Index(object):
    __slots__ = ()

    def __call__(self, index):
        if not isinstance(index, int):
            raise TypeError('index must be an integer')
        return ast.Index(value=ast.Num(n=index), ctx=ast.Load())


idx = Index()


class Subscript(object):
    __slots__ = ()

    def __call__(self, value, index):
        return ast.Subscript(
            value=value,
            slice=index,
            ctx=ast.Load(),
        )


sub = Subscript()


TRUE = ast.NameConstant(value=True)
FALSE = ast.NameConstant(value=False)


## API
# alias.foo
# alias.foo


class Alias(object):
    __slots__ = ()

    def __getattr__(self, name):
        return ast.alias(name=name, asname=None)


alias = Alias()


class ImportFrom(object):
    __slots__ = ()

    def __getattr__(self, name):
        return DottedModule(name)


import_from = ImportFrom()


class DottedModule(object):

    __slots__ = 'name',

    def __init__(self, name):
        self.name = name

    def __getitem__(self, key):
        names = [key] if isinstance(key, ast.alias) else list(key)
        return ast.ImportFrom(module=self.name, names=names)

    def __getattr__(self, name):
        return DottedModule('{}.{}'.format(self.name, name))
