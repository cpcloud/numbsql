import os
import versioneer

from setuptools import setup, find_packages, Extension


setup(
    name='slumba',
    url='https://github.com/cpcloud/slumba',
    packages=find_packages(),
    python_requires='>=3.6',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='JITted SQLite user-defined functions and aggregates',
    ext_modules=[
        Extension(
            name='slumba.cslumba',
            sources=[os.path.join('slumba', 'cslumba.c')],
            libraries=['sqlite3'],
        )
    ],
    license='Apache License, Version 2.0',
    author='Phillip Cloud',
    author_email='cpcloud@gmail.com',
)
