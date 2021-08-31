import pytest
from numba import TypingError, boolean, int64, njit

from numbsql.numbaext import is_not_null_pointer, sizeof, unsafe_cast


def test_sizeof_invalid() -> None:
    with pytest.raises(TypingError):

        @njit(int64(int64))  # type: ignore[misc]
        def bad_sizeof(x: int) -> int:  # pragma: no cover
            return sizeof(x)


@pytest.mark.xfail(  # type: ignore[misc]
    reason="Numba converts c_void_p from ctypes into an integer"
)
def test_is_null_invalid() -> None:
    with pytest.raises(TypingError):

        @njit(boolean(int64))  # type: ignore[misc]
        def bad_is_null_pointer(x: int) -> bool:  # pragma: no cover
            return is_not_null_pointer(x)


def test_unsafe_case_invalid() -> None:
    with pytest.raises(TypingError):

        @njit(int64(int64))  # type: ignore[misc]
        def bad_unsafe_cast(x: int) -> int:  # pragma: no cover
            return unsafe_cast(x, int64)
