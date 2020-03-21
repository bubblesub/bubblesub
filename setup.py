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

import io
import os
import sys
import typing as T
from pathlib import Path

from setuptools import Command, find_packages, setup


class GenerateDocumentationCommand(Command):
    description = "generate documentation"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    @property
    def _docs_dir(self) -> Path:
        return Path(__file__).parent / "docs"

    def run(self):
        with io.StringIO() as handle:
            self._generate_hotkeys_documentation(handle=handle)
            self._generate_commands_documentation(handle=handle)
            handle.seek(0)
            text = handle.read()
        (self._docs_dir / "doc.md").write_text(text.strip() + "\n")

    def _generate_hotkeys_documentation(self, handle):
        import re
        import shlex
        import bubblesub.cfg
        from bubblesub.api.cmd import split_invocation

        cfg = bubblesub.cfg.Config()

        table = []
        for hotkey in cfg.hotkeys:
            last_cell = []
            for invocation in split_invocation(hotkey.cmdline):
                cmd_name, *cmd_args = invocation
                anchor = self._get_anchor_name("cmd", cmd_name)
                last_cell.append(
                    f'<a href="#user-content-{anchor}">{cmd_name}</a> '
                    + " ".join(shlex.quote(arg) for arg in cmd_args)
                )
            row = [
                f"<kbd>{hotkey.shortcut}</kbd>",
                re.sub("([A-Z])", r" \1", hotkey.context.name).strip().lower(),
                "<code>" + "; ".join(last_cell) + "</code>",
            ]
            table.append(row)

        print("# Default hotkeys", file=handle)
        print("", file=handle)
        print("Context refers to the currently focused widget.", file=handle)
        print("", file=handle)
        print(
            self._make_table(["Shortcut", "Context", "Command"], table),
            file=handle,
        )

    def _generate_commands_documentation(self, handle):
        import argparse

        import bubblesub.cfg
        import bubblesub.api.cmd

        args = argparse.Namespace()
        setattr(args, "no_video", True)

        api = bubblesub.api.Api(args)
        api.cmd.reload_commands()

        print("# Default commands", file=handle)
        for cls in sorted(api.cmd.get_all(), key=lambda cls: cls.names[0]):
            parser = argparse.ArgumentParser(
                add_help=False,
                prog=cls.names[0],
                formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )
            cls.decorate_parser(api, parser)

            cmd_anchor = self._get_anchor_name("cmd", cls.names[0])
            cmd_name = cls.names[0].replace("-", "\N{NON-BREAKING HYPHEN}")
            print(f'### <a name="{cmd_anchor}"></a>`{cmd_name}`', file=handle)

            if len(cls.names) > 1:
                print(
                    "Aliases: "
                    + ", ".join(f"`{alias}`" for alias in cls.names[1:])
                    + "\n",
                    file=handle,
                )

            print(
                (cls.help_text + " " + cls.help_text_extra).strip(),
                file=handle,
            )
            if parser._actions:
                print(file=handle)
                print(self._get_usage(cmd_name, parser), file=handle)
                print(self._get_params_help(cmd_name, parser), file=handle)
            print(file=handle)

    @staticmethod
    def _get_usage(cmd_name, parser):
        def format_action(action):
            ret = ""
            if not action.required:
                ret += "["
            ret += "|".join(action.option_strings) or f"{action.dest}" or ""
            if action.option_strings and action.nargs != 0:
                ret += f'={action.default or "…"}'
            if not action.required:
                ret += "]"
            return ret

        desc = "Usage: `"
        desc += " ".join(
            [cmd_name] + [format_action(action) for action in parser._actions]
        )
        desc += "`"
        return desc

    @staticmethod
    def _get_params_help(cmd_name, parser):
        desc = ""
        for action in parser._actions:
            if not action.help:
                raise ValueError(
                    f"Command {cmd_name} has no help text "
                    f"for one of its arguments"
                )

            desc += "* "
            desc += (
                ", ".join(f"`{opt}`" for opt in action.option_strings)
                or f"`{action.dest}`"
                or ""
            )
            desc += ": "
            desc += action.help
            if action.choices:
                desc += (
                    " (can be "
                    + ", ".join(f"`{choice!s}`" for choice in action.choices)
                    + ")"
                )
            desc += "\n"
        return desc.rstrip()

    @staticmethod
    def _get_anchor_name(prefix: str, name: str) -> str:
        return prefix + "-" + name.replace("/", "-")

    @staticmethod
    def _make_table(
        header_names: T.List[str], rows: T.List[T.List[str]]
    ) -> str:
        ret = "| " + " | ".join(header_names) + " |\n"
        ret += "|" + "|".join([":--" for _ in header_names]) + "|\n"
        for row in rows:
            ret += (
                "|"
                + " | ".join(str(cell).replace("\n", "<br>") for cell in row)
                + " |\n"
            )
        return ret

    @staticmethod
    def _repr_type(type_: type) -> str:
        for comp, name in {
            str: "string",
            int: "integer",
            float: "real number",
            bool: "boolean",
            Path: "path",
        }.items():
            if type_ == comp:
                return name
            if type_ == T.Optional[comp]:
                return name + ", optional"
        raise RuntimeError(f'don\'t know how to describe "{type_}"')


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
    package_data={"bubblesub": ["data/*", "data/**/*"]},
    install_requires=install_packages,
    extras_require={"develop": ["docstring_parser", "mypy", "pytest"]},
    cmdclass={
        "doc": GenerateDocumentationCommand,
        "test": PyTestCommand,
        "mypy": MypyCommand,
    },
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
