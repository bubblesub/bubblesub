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

import sys
import typing as T
from pathlib import Path
from setuptools import setup, find_packages, Command


class GenerateDocumentationCommand(Command):
    description = 'generate documentation'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    @property
    def _docs_dir(self) -> Path:
        return Path(__file__).parent / 'docs'

    def run(self):
        with (self._docs_dir / 'doc.md').open('w') as handle:
            self._generate_hotkeys_documentation(handle=handle)
            self._generate_commands_documentation(handle=handle)

    def _generate_hotkeys_documentation(self, handle):
        import bubblesub.opt

        opt = bubblesub.opt.Options()

        table = []
        for context, hotkeys in opt.hotkeys:
            for hotkey in hotkeys:
                cmd_name = hotkey.command_name
                cmd_anchor = self._get_anchor_name('cmd', cmd_name)
                row = [
                    f'<kbd>{hotkey.shortcut}</kbd>',
                    context,
                    f'<a href="#user-content-{cmd_anchor}">`{cmd_name}`</a>',
                    ', '.join(f'`{arg}`' for arg in hotkey.command_args)
                ]
                table.append(row)

        print('# Default hotkeys', file=handle)
        print('', file=handle)
        print('Context refers to the currently focused widget.', file=handle)
        print('', file=handle)
        print(
            self._make_table(
                ['Shortcut', 'Context', 'Command name', 'Command parameters'],
                table
            ),
            file=handle
        )

    def _generate_commands_documentation(self, handle):
        import bubblesub.api.cmd
        import bubblesub.cmd
        import inspect
        import docstring_parser

        table = []

        for cmd in bubblesub.api.cmd.CommandApi.core_registry.values():
            signature = inspect.signature(cmd.__init__)
            cls_docstring = docstring_parser.parse(cmd.__doc__)
            init_docstring = docstring_parser.parse(cmd.__init__.__doc__)
            parameters = {
                name: param
                for name, param in signature.parameters.items()
                if name not in {'self', 'api'}
            }

            row = []
            cmd_anchor = self._get_anchor_name('cmd', cmd.name)
            cmd_name = cmd.name.replace('-', '\N{NON-BREAKING HYPHEN}')
            row.append(f'`{cmd_name}`')

            desc = f'<a name="{cmd_anchor}"></a>'
            desc += cls_docstring.short_description
            if cls_docstring.long_description:
                desc += '\n'
                desc += cls_docstring.long_description.replace('\n', ' ')
            desc += '\n'

            if parameters:
                desc += 'Parameters:\n<ol>'
                for num, item in enumerate(parameters.items()):
                    name, param = item
                    param_type = self._repr_type(param.annotation)
                    param_desc = next(
                        p for p in init_docstring.params if p.arg_name == name
                    ).description.replace('\n', '')
                    desc += f'<li>{name} ({param_type}): {param_desc}</li>'
                desc += '</ol>'

            row.append(desc.strip())

            table.append(row)

        print('# Default commands', file=handle)
        print(
            self._make_table(['Command name', 'Description'], table),
            file=handle
        )

    @staticmethod
    def _get_anchor_name(prefix: str, name: str) -> str:
        return prefix + '-' + name.replace('/', '-')

    @staticmethod
    def _make_table(
            header_names: T.List[str],
            rows: T.List[T.List[str]]
    ) -> str:
        ret = '| ' + ' | '.join(header_names) + ' |\n'
        ret += '|' + '|'.join([':--' for _ in header_names]) + '|\n'
        for row in rows:
            ret += (
                '|'
                + ' | '.join(
                    str(cell).replace('\n', '<br>')
                    for cell in row
                )
                + ' |\n'
            )
        return ret

    @staticmethod
    def _repr_type(type_: type) -> str:
        for comp, name in {
                str: 'string',
                int: 'integer',
                float: 'real number',
                bool: 'boolean',
                Path: 'path',
        }.items():
            if type_ == comp:
                return name
            if type_ == T.Optional[comp]:
                return name + ', optional'
        raise RuntimeError(f'Don\'t know how to describe "{type_}"')


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
                'bubblesub/cmd',
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
            'mypy',
            'bubblesub',
            '--ignore-missing-imports',
            '--disallow-untyped-calls',
            '--disallow-untyped-defs',
            '--disallow-incomplete-defs',
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

    package_dir={'bubblesub': 'bubblesub'},
    package_data={'bubblesub': ['data/**/*']},

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
        'ass_tag_parser',
        'Pillow',
    ],

    extras_require={
        'develop': [
            'pytest',
            'pylint',
            'pycodestyle',
            'pydocstyle',
            'mypy',
            'docstring_parser'
        ]
    },

    cmdclass={
        'doc': GenerateDocumentationCommand,
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
