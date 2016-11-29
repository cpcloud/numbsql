import sqlite3
import inspect
import ast
import time

from ctypes import CDLL, c_void_p, c_double, c_int, c_int64, c_ubyte
from ctypes.util import find_library

from math import sqrt, exp, pi

from numba import cfunc, int64, float64, jit, i1, f8, i8, void, int32
from numba import jitclass, float64, int64
from numba.types import voidptr, CPointer, intc


from gen import *  # we can probably do better than a star import here

from slumba import register_scalar_function



sqlite3_aggregate_context = libsqlite3.sqlite3_aggregate_context
sqlite3_aggregate_context.argtypes = c_void_p, c_int
sqlite3_aggregate_context.restype = c_void_p


@jitclass([
    ('mean', float64),
    ('sum_of_squares_of_differences', float64),
    ('count', int64),
])
class VarContext(object):
    def __init__(self):
        self.mean = 0.0
        self.sum_of_squares_of_differences = 0.0
        self.count = 0

@jitclass([
    ('context', VarContext),
])
class Variance(object):
    def __init__(self, context):
        self.context = sqlite3_aggregate_context(context, 24)

    @property

    def step(self, value):
        context = self.context
        context.count += 1
        delta = value - context.mean
        context.mean += delta / context.count
        context.sum_of_squares_of_differences += delta * (value - context.mean)

    def finalize(self):
        return self.context.sum_of_squares_of_differences / (self.context.count - 1)

@cfunc(void(voidptr, intc, CPointer(voidptr)))
def my_var(ctx, argc, argv):
    v = Variance()
    v.step(sqlite3_value_double(argv[0]))

# con = sqlite3.connect(':memory:')
# con.execute('CREATE TABLE t (random_numbers DOUBLE PRECISION)')

# random_numbers = [(random.random(),) for _ in range(50000)]
# con.executemany('INSERT INTO t VALUES (?)', random_numbers)

# # new way of registering C functions
# register_cfunc(con, normal)

# query1 = 'select myavg(random_numbers) as myavg from t'
# query2 = 'select avg(random_numbers) as oldavg from t'


# start1 = time.time()
# exe1 = con.execute(query1)
# result1 = list(exe1)
# t1 = time.time() - start1

# start2 = time.time()
# exe2 = con.execute(query2)
# result2 = list(exe2)
# t2 = time.time() - start2

# print(result1 == result2)
# print('t1 == {:.2f}'.format(t1))
# print('t2 == {:.2f}'.format(t2))
