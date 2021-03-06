#! /usr/bin/python3
# -*- coding: utf-8 -*-

from distutils.core import setup
from setuptools import find_packages

import os
import sys
from setuptools.command.test import test as TestCommand

class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        _test_args = [
            '--verbose',
            '--ignore=build',
            '--cov=domainics',
            '--cov-report=term-missing',
            # '--pep8',
        ]
        extra_args = os.environ.get('PYTEST_EXTRA_ARGS')
        if extra_args is not None:
            _test_args.extend(extra_args.split())
        self.test_args = _test_args
        self.test_suite = True

    def run_tests(self):
        import pytest
        from pkg_resources import normalize_path, _namespace_packages

        errno = pytest.main(self.test_args)
        sys.exit(errno)

setup(
    name='alipayrequest',
    version='0.5.0',
    license="BSD",
    description="A request client for Alipay gateway",
    author='Chenggong Lyu',
    author_email='lcgong@gmail.com',
    url='https://github.com/lcgong/alipayrequest',
    packages=find_packages("."),
    # package_dir = {"": "."},
    zip_safe = False,
    install_requires = [],
    classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Utilities",
        ],
    test_suite='domainics.test',
    tests_require=[
        'pytest',
        'pytest-pep8',
        'pytest-cov',
        ],
    cmdclass={'test': PyTest},
    )
