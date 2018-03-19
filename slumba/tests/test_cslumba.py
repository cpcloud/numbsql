"""Smoke tests to make sure that we can register pointers without raising an
exception.
"""

import pytest
import sqlite3


from slumba.cslumba import (
    register_scalar_function,
    register_aggregate_function,
)
from numba import cfunc
from numba.types import void, voidptr, CPointer, intc


@pytest.fixture
def con():
    return sqlite3.connect(':memory:')


@cfunc(void(voidptr, intc, CPointer(voidptr)))
def add_one(ctx, argc, argv):
    pass


def test_register_scalar_function(con):
    assert add_one.address > 0

    register_scalar_function(
        con,
        b'add_one',
        1,
        add_one.address
    )


@cfunc(void(voidptr, intc, CPointer(voidptr)))
def my_count_step(ctx, argc, argv):
    pass


@cfunc(void(voidptr))
def my_count_finalize(ctx):
    pass


def test_register_aggregate_function(con):
    assert my_count_step.address > 0
    assert my_count_finalize.address > 0
    register_aggregate_function(
        con,
        b'my_count',
        1,
        my_count_step.address,
        my_count_finalize.address
    )
