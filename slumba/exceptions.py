from typing import Type, TypeVar

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
