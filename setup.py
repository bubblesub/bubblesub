#!/usr/bin/env python
import sys
from setuptools import setup, find_packages, Command


class PyTestCommand(Command):
    description = 'run tests'
    user_options = [('pytest-args=', 'a', 'Arguments to pass to pytest')]

    def initialize_options(self):
        self.pytest_args = ''

    def finalize_options(self):
        pass

    def run(self):
        import shlex
        import pytest
        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


class LintCommand(Command):
    description = 'run linters'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import subprocess
        import glob

        commands = [
            ['pycodestyle', 'bubblesub'],
            [
                'pydocstyle',
                'bubblesub/api',
                'bubblesub/opt',
                'bubblesub/ass',
            ] + glob.glob('bubblesub/*.py'),
            ['pylint', 'bubblesub']
        ]

        for command in commands:
            status = subprocess.run(command)
            if status.returncode != 0:
                sys.exit(status.returncode)
        sys.exit(0)


class MypyCommand(Command):
    description = 'run type checks'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import subprocess

        status = subprocess.run([
            'mypy', 'bubblesub', '--ignore-missing-imports'
        ])
        sys.exit(status.returncode)


setup(
    author='Marcin Kurczewski',
    author_email='rr-@sakuya.pl',
    name='bubblesub',
    long_description='ASS subtitle editor',
    version='0.0',
    url='https://github.com/rr-/bubblesub',
    packages=find_packages(),

    entry_points={
        'console_scripts': [
            'bubblesub = bubblesub.__main__:main'
        ]
    },

    install_requires=[
        'ffms',
        'numpy',
        'scipy',
        'pyfftw',
        'PyQT5',
        'quamash',
        'regex',
        'pyenchant',
        'pympv',
        'xdg',
        'ass_tag_parser'
    ],

    extras_require={
        'develop': [
            'pytest',
            'pylint',
            'pycodestyle',
            'pydocstyle',
            'mypy'
        ]
    },

    cmdclass={
        'test': PyTestCommand,
        'lint': LintCommand,
        'mypy': MypyCommand
    },

    classifiers=[
        'Environment :: X11 Applications :: Qt',
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Text Editors',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Video'
    ]
)
