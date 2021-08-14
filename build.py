import os
import sys
from typing import Any, MutableMapping

from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        name="slumba.cslumba",
        sources=["slumba/cslumba.cc"],
        libraries=["sqlite3"],
        library_dirs=(
            [
                os.path.join(os.environ["CONDA_PREFIX"], "Library", part)
                for part in ("lib", "bin")
            ]
            if sys.platform == "win32"
            else []
        ),
        include_dirs=(
            [os.path.join(os.environ["CONDA_PREFIX"], "Library", "include")]
            if sys.platform == "win32"
            else []
        ),
    )
]


def build(setup_kwargs: MutableMapping[str, Any]) -> None:
    """This function is mandatory in order to build the extensions."""

    setup_kwargs.update(
        {"ext_modules": ext_modules, "cmdclass": {"build_ext": build_ext}}
    )
