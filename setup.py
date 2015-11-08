import os

from setuptools import setup, find_packages, Extension

from Cython.Distutils import build_ext


setup(
    name='cysqlite3',
    packages=find_packages(),
    ext_modules=[
        Extension(
            'cysqlite3.cysqlite3',
            sources=[os.path.join('cysqlite3', 'cysqlite3.pyx')],
            libraries=['sqlite3']
        )
    ],
    cmdclass={'build_ext': build_ext}
)
