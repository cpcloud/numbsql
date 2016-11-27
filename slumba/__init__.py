from .slumba import register_function_pointer

__all__ = [
    'register_scalar_function',
    'register_aggregate_function',
]

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
