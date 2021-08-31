from typing import Type, TypeVar

from numba import types

T = TypeVar("T")


class MissingAggregateMethod(Exception):
    def __init__(self, cls: Type[T], method: str) -> None:
        self.clsname = cls.__name__
        self.method = method
        super().__init__(self.clsname, self.method)

    def __str__(self) -> str:
        return (
            f"Missing aggregate method `{self.method}` on UDAF class `{self.clsname}`"
        )


class MissingLibrary(Exception):
    def __init__(self, library: str) -> None:
        self.library = library
        super().__init__(self.library)

    def __str__(self) -> str:
        return f"Library `{self.library}` not found"


class UnsupportedAggregateTypeError(NotImplementedError):
    def __init__(self, typ: types.Type) -> None:
        self.typ = typ
        super().__init__(self.typ)

    def __str__(self) -> str:
        return f"Aggregates with field type `{self.typ}` are not yet implemented"
