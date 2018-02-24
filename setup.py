import os
import versioneer

from setuptools import setup, find_packages, Extension

from Cython.Build import cythonize


setup(
    name='slumba',
    url='https://github.com/cpcloud/slumba',
    packages=find_packages(),
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    ext_modules=cythonize([
        Extension(
            name='slumba.cyslumba',
            sources=[os.path.join('slumba', 'cyslumba.pyx')],
            libraries=['sqlite3'],
            include_dirs=[os.path.join('slumba')]
        )
    ]),
    author='Phillip Cloud',
    author_email='cpcloud@gmail.com',
)
