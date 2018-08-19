import glob
import os
import tempfile

import versioneer

import setuptools
from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext


class get_pybind_include:
    """Helper class to determine the pybind11 include path

    The purpose of this class is to postpone importing pybind11
    until it is actually installed, so that the ``get_include()``
    method can be invoked.
    """

    def __init__(self, user=False):
        self.user = user

    def __str__(self):
        import pybind11
        return pybind11.get_include(self.user)


# As of Python 3.6, CCompiler has a `has_flag` method.
# cf http://bugs.python.org/issue26689
def has_flag(compiler, flagname):
    """Return a boolean indicating whether a flag name is supported on
    the specified compiler.
    """
    source = 'int main (int argc, const char *argv[]) { return 0; }'
    with tempfile.NamedTemporaryFile('w', suffix='.cc') as f:
        f.write(source)
        try:
            compiler.compile(
                [f.name],
                extra_postargs=[flagname],
                output_dir=os.path.dirname(f.name),
            )
        except setuptools.distutils.errors.CompileError:
            return False
    return True


def cpp_flag(compiler):
    """Return the -std=c++[11/14] compiler flag.
    The c++14 is prefered over c++11 (when it is available).
    """
    if has_flag(compiler, '-std=c++14'):
        return '-std=c++14'
    elif has_flag(compiler, '-std=c++11'):
        return '-std=c++11'
    else:
        raise RuntimeError('Unsupported compiler -- at least C++11 support '
                           'is needed!')


class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""
    c_opts = {
        'unix': ['-fvisibility=hidden'],
    }

    def build_extensions(self):
        ct = self.compiler.compiler_type
        opts = self.c_opts.get(ct, [])

        for flag in opts:
            if not has_flag(self.compiler, flag):
                opts.remove(flag)

        opts.append(cpp_flag(self.compiler))
        for ext in self.extensions:
            ext.extra_compile_args = opts
        super().build_extensions()


cmdclass = versioneer.get_cmdclass()
cmdclass['build_ext'] = BuildExt

setup(
    name='slumba',
    url='https://github.com/cpcloud/slumba',
    packages=find_packages(),
    python_requires='>=3.5',
    install_requires=['pybind11>=2.2'],
    version=versioneer.get_version(),
    cmdclass=cmdclass,
    description='JITted SQLite user-defined functions and aggregates',
    ext_modules=[
        Extension(
            name='slumba.cslumba',
            sources=glob.glob(os.path.join('slumba', '*.cc')),
            include_dirs=[
                # Path to pybind11 headers
                get_pybind_include(),
                get_pybind_include(user=True),
                os.path.join(os.environ['HOME'], 'code', 'c', 'sqlite'),
            ],
            libraries=['sqlite3'],
            language='c++',
        ),

    ],
    license='Apache License, Version 2.0',
    author='Phillip Cloud',
    author_email='cpcloud@gmail.com',
    zip_safe=False,
)
