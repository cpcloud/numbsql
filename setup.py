import os

from setuptools import setup, find_packages, Extension

from Cython.Build import cythonize


setup(
    name='cysqlite3',
    packages=find_packages(),
    ext_modules=cythonize([
        Extension(
            'cysqlite3.cysqlite3',
            sources=[os.path.join('cysqlite3', 'cysqlite3.pyx')],
            libraries=['sqlite3'],
            include_dirs=[os.path.join('cysqlite3')]
        )
    ]),
)
