from .slumba import register_function_pointer

__all__ = [
    'register_function_pointer',
]

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
