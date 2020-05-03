#!/usr/bin/env python

# bubblesub - ASS subtitle editor
# Copyright (C) 2018 Marcin Kurczewski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import sys

from setuptools import Command, find_packages, setup


class PyTestCommand(Command):
    description = "run tests"
    user_options = [("pytest-args=", "a", "Arguments to pass to pytest")]

    def initialize_options(self):
        self.pytest_args = "-m 'not ci'"

    def finalize_options(self):
        pass

    def run(self):
        import shlex
        import pytest

        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


class FormatCommand(Command):
    description = "run formatters"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import subprocess

        commands = [
            ["isort", "-p", "bubblesub", "-o", "mpv", "-ns", "__init__.py"],
            ["black", "-l79", "."],
        ]
        for command in commands:
            status = subprocess.run(command)
            if status.returncode != 0:
                sys.exit(status.returncode)
        sys.exit(0)


class MypyCommand(Command):
    description = "run type checks"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import subprocess

        status = subprocess.run(
            [
                "mypy",
                "bubblesub",
                "--ignore-missing-imports",
                "--disallow-untyped-calls",
                "--disallow-untyped-defs",
                "--disallow-incomplete-defs",
            ]
        )
        sys.exit(status.returncode)


install_packages = [
    "ffms2",
    "numpy",
    "pyfftw",
    "PyQT5",
    "quamash",
    "regex",
    "pyqtcolordialog",
    "pympv",
    "ass_tag_parser",
    "Pillow",
    "pyyaml",
    "parsimonious",
    "pluginbase",
    "lazy_import",
    "sortedcontainers",
    "dataclasses;python_version<'3.7'",
]

if os.name == "nt":
    install_packages.append("pyspellchecker")
else:
    install_packages.append("pyenchant")

setup(
    author="Marcin Kurczewski",
    author_email="rr-@sakuya.pl",
    name="bubblesub",
    long_description="ASS subtitle editor",
    version="0.0",
    url="https://github.com/bubblesub/bubblesub",
    packages=find_packages(),
    entry_points={"console_scripts": ["bubblesub = bubblesub.__main__:main"]},
    package_dir={"bubblesub": "bubblesub"},
    package_data={
        "bubblesub": ["data/*", "data/**/*", "ui/assets/*", "ui/assets/**/*"]
    },
    install_requires=install_packages,
    extras_require={
        "develop": [
            "docstring_parser",
            "mypy",
            "pytest",
            "pytest-qt",
            "pyScss",
        ]
    },
    cmdclass={"test": PyTestCommand, "mypy": MypyCommand,},
    classifiers=[
        "Environment :: X11 Applications :: Qt",
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Text Editors",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Multimedia :: Video",
    ],
)
