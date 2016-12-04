import sys


_mm = '{:d}{:d}'.format(
    sys.version_info.major,
    sys.version_info.minor
)

if _mm == '34':
    from .py34 import *
elif _mm == '35':
    from .py35 import *
