from numba import jit


class VarContext(object):
    def __init__(self):
        self.mean = 0.0
        self.sum_of_squares_of_differences = 0.0
        self.count = 0


from numba import types


class VarContextType(types.Type):
    def __init__(self):
        super(VarContextType, self).__init__(name='VarContext')


var_context_type = VarContextType()


from numba.extending import typeof_impl

@typeof_impl.register(VarContext)
def typeof_index(val, c):
    return var_context_type


from numba.extending import type_callable

@type_callable(VarContext)
def type_var_context(context):
    def typer(mean, sum_of_squares_of_differences, count):
        assert isinstance(mean, types.Float)
        assert isinstance(sum_of_squares_of_differences, types.Float)
        assert isinstance(count, types.Integer)
        return var_context_type
    return typer

from numba.extending import models, register_model


@register_model(VarContextType)
class VarContextModel(models.StructModel):
    def __init__(self, dmm, fe_type):
        members = [
            ('mean', types.float64),
            ('sum_of_squares_of_differences', types.float64),
            ('count', types.int64),
        ]
        super(VarContextModel, self).__init__(dmm, fe_type, members)


from numba.extending import make_attribute_wrapper

make_attribute_wrapper(VarContextType, 'mean', 'mean')
make_attribute_wrapper(VarContextType, 'sum_of_squares_of_differences', 'sum_of_squares_of_differences')
make_attribute_wrapper(VarContextType, 'count', 'count')


from numba.extending import lower_builtin, lower_setattr_generic, lower_setattr
from numba import cgutils


@lower_builtin(VarContext)
def impl_var_context(context, builder, sig, args):
    import pdb
    pdb.set_trace()
    var_context = cgutils.create_struct_proxy(sig.return_type)(context, builder)
    var_context.mean = 0.0
    var_context.sum_of_squares_of_differences = 0.0
    var_context.count = 0
    return var_context._getvalue()


@lower_setattr_generic(VarContext)
def impl_var_context_setattr(context, builder, sig, args):
    import pdb
    pdb.set_trace()
    var_context = cgutils.create_struct_proxy(sig.return_type)(context, builder)
    var_context.mean = 0.0
    var_context.sum_of_squares_of_differences = 0.0
    var_context.count = 0
    return var_context._getvalue()


from numba.extending import box, unbox, NativeValue


@unbox(VarContextType)
def unbox_var_context_type(typ, obj, c):
    mean_obj = c.pyapi.object_getattr_string(obj, 'mean')
    sum_of_squares_of_differences_obj = c.pyapi.object_getattr_string(obj, 'sum_of_squares_of_differences')
    count_obj = c.pyapi.object_getattr_string(obj, 'count')
    var_context = cgutils.create_struct_proxy(typ)(c.context, c.builder)
    var_context.mean = c.pyapi.float_as_double(mean_obj)
    var_context.sum_of_squares_of_differences = c.pyapi.float_as_double(sum_of_squares_of_differences_obj)
    var_context.count = c.pyapi.long_as_longlong(count_obj)
    c.pyapi.decref(mean_obj)
    c.pyapi.decref(sum_of_squares_of_differences_obj)
    c.pyapi.decref(count_obj)
    is_error = cgutils.is_not_null(c.builder, c.pyapi.err_occurred())
    return NativeValue(var_context._getvalue(), is_error=is_error)


@jit(nopython=True)
def foo(v):
    v.count += 1
    # v.mean += 23.034
    # v.sum_of_squares_of_differences -= 234.021
    # return v


v = VarContext()
foo(v)
