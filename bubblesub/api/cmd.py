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

"""
Command API.

Commands use the API layer to manipulate the program state in
interesting, complex ways.
"""

import abc
import argparse
import asyncio
import importlib.util
import io
import shlex
import time
import traceback
import typing as T
from pathlib import Path

from PyQt5 import QtCore

import bubblesub.api.api
import bubblesub.model
from bubblesub.opt.menu import MenuItem


class CommandError(RuntimeError):
    """Base class for all command related errors."""

    pass


class CommandCanceled(CommandError):
    """The given command was canceled by the user."""

    def __init__(self):
        super().__init__('canceled')


class CommandNotFound(CommandError):
    """The given command was not found."""

    pass


class BadInvocation(CommandError):
    """The given invocation was invalid."""

    pass


class CommandArgumentParser(argparse.ArgumentParser):
    """Overloaded ArgumentParser, suitable for commands."""

    def error(self, message):
        """
        Rather than exiting, raise an exception.

        :param message: error message about to be shown to the user
        """
        with io.StringIO() as handle:
            handle.write(f'{self.prog}: error: {message}\n')
            self.print_help(handle)
            handle.seek(0)
            message = handle.read()
        raise BadInvocation(message)


def split_invocation(invocation: str) -> T.Tuple[str, T.List[str]]:
    """
    Split invocation into name and arguments array.

    :param invocation: command line to parse
    :return: tuple containing command name and arguments
    """
    if not invocation.startswith('/'):
        raise BadInvocation(
            f'Invocation should start with a slash ("{invocation}")'
        )
    name, *args = shlex.split(invocation.lstrip('/'))
    return (name, args)


class BaseCommand(abc.ABC):
    """Base class for all commands."""

    def __init__(self, api: 'bubblesub.api.api.Api', invocation: str) -> None:
        """
        Initialize self.

        :param api: core API
        :param invocation: command invocation
        """
        self.api = api
        self.invocation = invocation
        self.args = self.parse_args(api, split_invocation(invocation)[1])

    @bubblesub.model.classproperty
    @abc.abstractproperty
    def names(  # pylint: disable=no-self-argument
            cls: T.Any
    ) -> T.List[str]:
        """
        Return command names.

        Must be globally unique and should be human readable.

        :param cls: type inheriting from BaseCommand
        :return: command names
        """
        raise NotImplementedError('command has no name')

    @property
    @abc.abstractproperty
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        raise NotImplementedError('command has no menu name')

    @bubblesub.model.classproperty
    @abc.abstractproperty
    def help_text(self) -> str:
        """
        Return command description shown in help.

        :return: description
        """
        raise NotImplementedError('command has no help text')

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return True

    @abc.abstractmethod
    async def run(self) -> None:
        """Carry out the command."""
        raise NotImplementedError('command has no implementation')

    @classmethod
    def parse_args(
            cls,
            api: 'bubblesub.api.Api',
            invocation: str
    ) -> argparse.Namespace:
        """
        Convert command invocation.

        :param cls: type inheriting from BaseCommand
        :param api: core API
        :param invocation: command line
        :return: parsed arguments for command
        """
        parser = CommandArgumentParser(
            prog=cls.names[0],
            description=cls.help_text,
            add_help=False
        )
        cls._decorate_parser(api, parser)
        return parser.parse_args(invocation)

    @staticmethod
    def _decorate_parser(
            api: 'bubblesub.api.Api',
            parser: argparse.ArgumentParser
    ) -> None:
        pass


class CommandApi(QtCore.QObject):
    """The command API."""

    commands_loaded = QtCore.pyqtSignal()

    def __init__(self, api: 'bubblesub.api.Api') -> None:
        """
        Initialize self.

        :param api: core API
        """
        super().__init__()
        self._api = api
        self._thread = None
        self._command_registry: T.Dict[
            str,
            T.Tuple[T.Type[BaseCommand], bool]
        ] = {}
        self._plugin_menu: T.List[MenuItem] = []

    def execute(self, invocation: T.Union[T.List[str], str]) -> None:
        """
        Execute given invocation.

        :param invocation: invocation to run
        """
        if not invocation:
            return
        if isinstance(invocation, list):
            invocation = '/' + ' '.join(shlex.quote(arg) for arg in invocation)

        try:
            cmd = self.get(invocation)
        except Exception as ex:  # pylint: disable=broad-except
            self._api.log.error(str(ex))
        else:
            self.run(cmd)

    def run(self, cmd: BaseCommand) -> None:
        """
        Execute given command.

        :param cmd: command to run
        """
        asyncio.ensure_future(self.run_async(cmd))

    async def run_async(self, cmd: BaseCommand) -> bool:
        """
        Execute given command asynchronously.

        :param cmd: command to run
        :return: whether the command was executed without problems
        """
        start_time = time.time()

        self._api.log.info(cmd.invocation)

        if not cmd.is_enabled:
            self._api.log.info('command not available right now')
            return False

        try:
            await cmd.run()
        except CommandCanceled:
            self._api.log.warn(f'canceled')
            return False
        except Exception as ex:  # pylint: disable=broad-except
            self._api.log.error(f'problem running {cmd.invocation}:')
            self._api.log.error(f'{ex}')
            traceback.print_exc()
            return False
        end_time = time.time()
        took = end_time - start_time
        self._api.log.debug(f'{cmd.invocation}: took {took:.04f} s')
        return True

    def get(self, invocation: T.Union[T.List[str], str]) -> BaseCommand:
        """
        Retrieve command instance by its name and arguments.

        :param invocation: invocation
        :return: BaseCommand instance
        """
        if isinstance(invocation, list):
            invocation = '/' + ' '.join(shlex.quote(arg) for arg in invocation)

        name, _args = split_invocation(invocation)
        cls, _is_plugin = self._command_registry.get(name, (None, False))
        if not cls:
            raise CommandNotFound(f'no command named "{name}"')
        instance = cls(self._api, invocation)
        return T.cast(BaseCommand, instance)

    def get_all(self) -> T.List[T.Type[BaseCommand]]:
        """
        Return list of all registered command types.

        :return: list of types
        """
        return [cls for cls, _is_plugin in self._command_registry.values()]

    def load_commands(self, path: Path) -> None:
        """
        Load commands from the specified path.

        The file must have a `register` function that receives a reference to
        the `CommandApi`. This function should register all the commands
        within that file with the `CommandApi.register_plugin_command` or
        `CommandApi.register_core_command` method.

        :param path: dictionary containing plugin definitions
        """
        specs = []
        if path.exists():
            for subpath in path.glob('*.py'):
                if subpath.stem == '__init__':
                    continue
                subpath_rel = subpath.relative_to(path)
                spec = importlib.util.spec_from_file_location(
                    '.'.join(
                        ['bubblesub', 'cmd']
                        + list(subpath_rel.parent.parts)
                        + [subpath_rel.stem]
                    ), str(subpath)
                )
                if spec is not None:
                    specs.append(spec)

        for spec in specs:
            try:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.register(self)
            except Exception as ex:  # pylint: disable=broad-except
                self._api.log.error(str(ex))
                traceback.print_exc()
        self.commands_loaded.emit()

    def unload_plugin_commands(self) -> None:
        """Remove plugin commands from the registry and clear plugins menu."""
        self._plugin_menu[:] = []
        for key, value in list(self._command_registry.items()):
            cls, is_plugin = value
            if is_plugin:
                print(f'unregistering {cls} as {cls.name}')
                del self._command_registry[key]

    def register_core_command(self, cls: T.Type[BaseCommand]) -> None:
        """
        Register a core command to the registry.

        :param cls: type inheriting from BaseCommand
        """
        for name in cls.names:
            print(f'registering {cls} as {name}')
            self._command_registry[name] = (cls, False)

    def register_plugin_command(
            self, cls: T.Type[BaseCommand], menu_item: MenuItem
    ) -> None:
        """
        Register a plugin command to the registry.

        User commands can be accessed from the 'plugins' menu and reloaded at
        runtime. Unlike core commands, for which the menu is constructed via
        opt.menu.MenuConfig, the plugins build the menu by themselves.

        :param cls: type inheriting from BaseCommand
        :param menu_item: menu item to show in the plugins menu
        """
        for name in cls.names:
            print(f'registering {cls} as {name}')
            self._command_registry[name] = (cls, True)
        self._plugin_menu.append(menu_item)

    def get_plugin_menu_items(self) -> T.List[MenuItem]:
        """
        Return plugin menu items.

        :return: plugins menu
        """
        return self._plugin_menu
