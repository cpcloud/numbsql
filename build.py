import subprocess
from typing import Any, List, MutableMapping, Sequence

from pybind11.setup_helpers import Pybind11Extension, build_ext


def pkg_config(pkg: str, *flags: str) -> List[str]:
    """Return the result of running `pkg-config` with flags `flags`."""
    return (
        subprocess.check_output(["pkg-config", *flags, pkg], encoding="utf8")
        .strip()
        .split()
    )


def strip_prefixes(results: Sequence[str], *, prefix: str) -> List[str]:
    """Strip prefix `prefix` from every element of `results`."""
    return [result[len(prefix) :] for result in results]


ext_modules = [
    Pybind11Extension(
        name="slumba.cslumba",
        include_dirs=strip_prefixes(
            pkg_config("sqlite3", "--cflags-only-I"), prefix="-I"
        ),
        libraries=strip_prefixes(pkg_config("sqlite3", "--libs-only-l"), prefix="-l"),
        library_dirs=strip_prefixes(
            pkg_config("sqlite3", "--libs-only-L"), prefix="-L"
        ),
        sources=["slumba/cslumba.cc"],
    )
]


def build(setup_kwargs: MutableMapping[str, Any]) -> None:
    """Build extension modules."""

    setup_kwargs.update(
        {"ext_modules": ext_modules, "cmdclass": {"build_ext": build_ext}}
    )
