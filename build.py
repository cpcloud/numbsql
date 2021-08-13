from typing import Any, MutableMapping

from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        name="slumba.cslumba",
        sources=["slumba/cslumba.cc"],
        libraries=["sqlite3"],
    )
]


def build(setup_kwargs: MutableMapping[str, Any]) -> None:
    """This function is mandatory in order to build the extensions."""

    setup_kwargs.update(
        {"ext_modules": ext_modules, "cmdclass": {"build_ext": build_ext}}
    )
