import pytest

from numba import boolean, njit, int64, TypingError
from slumba.numbaext import is_not_null_pointer, sizeof, unsafe_cast


def test_sizeof_invalid():
    dec = njit(int64(int64))

    with pytest.raises(TypingError):

        @dec
        def bad_sizeof(x):  # pragma: no cover
            return sizeof(x)


def test_not_null_invalid():
    dec = njit(boolean(int64))

    with pytest.raises(TypingError):

        @dec
        def bad_not_null(x):  # pragma: no cover
            return is_not_null_pointer(x)


def test_unsafe_case_invalid():
    dec = njit(int64(int64))

    with pytest.raises(TypingError):

        @dec
        def bad_unsafe_cast(x):  # pragma: no cover
            return unsafe_cast(x, int64)
