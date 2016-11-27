import os
import versioneer

from setuptools import setup, find_packages, Extension

from Cython.Build import cythonize


setup(
    name='slumba',
    packages=find_packages(),
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    ext_modules=cythonize([
        Extension(
            'slumba.slumba',
            sources=[os.path.join('slumba', 'slumba.pyx')],
            libraries=['sqlite3'],
            include_dirs=[os.path.join('slumba')]
        )
    ]),
)
