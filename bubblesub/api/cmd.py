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
import asyncio
import importlib.util
import inspect
import sys
import time
import traceback
import typing as T
from pathlib import Path

import bubblesub.api.api
import bubblesub.event
import bubblesub.model


class BaseCommand(abc.ABC):
    """Base class for all commands."""

    def __init__(self, api: 'bubblesub.api.api.Api', *_args: T.Any) -> None:
        """
        Initialize self.

        :param api: core API
        :param _args: optional arguments to the command
        """
        self.api = api

    @bubblesub.model.classproperty
    @abc.abstractproperty
    def name(cls) -> str:  # pylint: disable=no-self-argument
        """
        Return command name.

        Must be globally unique and should be human readable.

        :param cls: type inheriting from BaseCommand
        :return: command name
        """
        raise NotImplementedError('Command has no name')

    @property
    @abc.abstractproperty
    def menu_name(self) -> str:
        """
        Return name shown in the GUI menus.

        :return: name shown in GUI menu
        """
        raise NotImplementedError('Command has no menu name')

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
        raise NotImplementedError('Command has no implementation')

    def debug(self, text: str) -> None:
        """
        Log a message with debug level.

        :param text: text to log
        """
        self.api.log.debug(f'cmd/{self.name}: {text}')

    def info(self, text: str) -> None:
        """
        Log a message with info level.

        :param text: text to log
        """
        self.api.log.info(f'cmd/{self.name}: {text}')

    def warn(self, text: str) -> None:
        """
        Log a message with warning level.

        :param text: text to log
        """
        self.api.log.warn(f'cmd/{self.name}: {text}')

    def error(self, text: str) -> None:
        """
        Log a message with error level.

        :param text: text to log
        """
        self.api.log.error(f'cmd/{self.name}: {text}')


class CommandApi:
    """The command API."""

    core_registry: T.Dict[str, T.Type] = {}
    plugin_registry: T.Dict[str, T.Type] = {}
    plugins_loaded = bubblesub.event.EventHandler()

    def __init__(self, api: 'bubblesub.api.Api') -> None:
        """
        Initialize self.

        :param api: core API
        """
        super().__init__()
        self._api = api
        self._thread = None

    def run(self, cmd: BaseCommand) -> None:
        """
        Execute given command.

        :param cmd: command to run
        """
        if not cmd.is_enabled:
            self._api.log.info(f'cmd/{cmd.name}: not available right now')
            return

        async def run() -> None:
            self._api.log.info('cmd/{}: running...'.format(cmd.name))
            start_time = time.time()
            try:
                await cmd.run()
            except Exception as ex:  # pylint: disable=broad-except
                self._api.log.error('cmd/{}: {}'.format(cmd.name, ex))
                traceback.print_exc()
            end_time = time.time()
            took = end_time - start_time
            self._api.log.info(f'cmd/{cmd.name}: ran in {took:.02f} s')

        asyncio.ensure_future(run())

    def get(self, name: str, args: T.Any) -> BaseCommand:
        """
        Retrieve command instance by its name and arguments.

        :param name: command name
        :param args: command arguments
        :return: BaseCommand instance
        """
        ret = self.plugin_registry.get(name)
        if not ret:
            ret = self.core_registry.get(name)
        if not ret:
            raise KeyError('No command named {}'.format(name))
        try:
            return T.cast(BaseCommand, ret(self._api, *args))
        except Exception:  # pylint: disable=broad-except
            print('Error creating command {}'.format(name), file=sys.stderr)
            raise

    def load_plugins(self, path: Path) -> None:
        """
        Reload all the plugin commands.

        :param path: dictionary containing plugin definitions
        """
        self.plugin_registry.clear()
        specs = []
        if path.exists():
            for subpath in path.glob('*.py'):
                spec = importlib.util.spec_from_file_location(
                    'bubblesub.plugin', str(subpath)
                )
                if spec is not None:
                    specs.append(spec)
        try:
            for spec in specs:
                spec.loader.exec_module(importlib.util.module_from_spec(spec))
        finally:
            self.plugins_loaded.emit()


class CoreCommand(BaseCommand):  # pylint: disable=abstract-method
    """Base class for internal bubblesub commands."""

    def __init_subclass__(cls) -> None:
        """
        Register core command.

        Ran on application startup for all declared core command classes.

        :param cls: type inheriting from CoreCommand
        """
        if not inspect.isabstract(cls):
            print('registering', cls, 'as', cls.name)
            CommandApi.core_registry[cls.name] = cls


class PluginCommand(BaseCommand):  # pylint: disable=abstract-method
    """
    Base class for external user commands.

    User commands can be accessed from the 'plugins' menu and reloaded at
    runtime.
    """

    def __init_subclass__(cls) -> None:
        """
        Register plugin command.

        Ran on application startup or plugin reload for all declared plugin
        command classes.

        :param cls: type inheriting from PluginCommand
        """
        if not inspect.isabstract(cls):
            print('registering', cls, 'as', cls.name)
            CommandApi.plugin_registry[cls.name] = cls
