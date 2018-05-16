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
import time
import traceback
import typing as T
from pathlib import Path

import bubblesub.api.api
import bubblesub.event
import bubblesub.model
from bubblesub.opt.menu import MenuItem


class BaseCommand(abc.ABC):
    """Base class for all commands."""

    def __init__(self, api: 'bubblesub.api.api.Api') -> None:
        """
        Initialize self.

        :param api: core API
        """
        self.api = api

    @bubblesub.model.classproperty
    @abc.abstractproperty
    def name(  # pylint: disable=no-self-argument
            cls: T.Any
    ) -> str:
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

    commands_loaded = bubblesub.event.EventHandler()

    def __init__(self, api: 'bubblesub.api.Api') -> None:
        """
        Initialize self.

        :param api: core API
        """
        super().__init__()
        self._api = api
        self._thread = None
        self._command_registry: T.Dict[str, T.Type[BaseCommand]] = {}
        self._plugin_menu: T.List[MenuItem] = []

    def run(self, cmd: BaseCommand) -> None:
        """
        Execute given command.

        :param cmd: command to run
        """
        if not cmd.is_enabled:
            self._api.log.info(f'cmd/{cmd.name}: not available right now')
            return

        async def run() -> None:
            self._api.log.info(f'cmd/{cmd.name}: running...')
            start_time = time.time()
            try:
                await cmd.run()
            except Exception as ex:  # pylint: disable=broad-except
                self._api.log.error(f'cmd/{cmd.name}: {ex}')
                traceback.print_exc()
            end_time = time.time()
            took = end_time - start_time
            self._api.log.info(f'cmd/{cmd.name}: ran in {took:.04f} s')

        asyncio.ensure_future(run())

    def get(self, name: str, args: T.List[T.Any]) -> BaseCommand:
        """
        Retrieve command instance by its name and arguments.

        :param name: command name
        :param args: command arguments
        :return: BaseCommand instance
        """
        cls = self._command_registry.get(name)
        if not cls:
            raise KeyError(f'No command named "{name}"')
        try:
            instance = cls(self._api, *args)
            return T.cast(BaseCommand, instance)
        except Exception:  # pylint: disable=broad-except
            self._api.log.error(f'Error creating command "{name}"')
            raise

    def get_all(self) -> T.List[BaseCommand]:
        """
        Return list of all registered command types.

        :return: list of types
        """
        return self._command_registry.values()

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
        for key in list(self._command_registry.keys()):
            if key.startswith('plugin/'):
                del self._command_registry[key]

    def register_core_command(self, cls: T.Type[BaseCommand]) -> None:
        """
        Register a core command to the registry.

        :param cls: type inheriting from BaseCommand
        """
        print(f'registering {cls} as {cls.name}')
        self._command_registry[cls.name] = cls

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
        print(f'registering {cls} as {cls.name}')
        if not cls.name.startswith('plugin/'):
            raise ValueError(
                'Plugin commands must start with "plugin/" prefix'
            )

        self._command_registry[cls.name] = cls
        self._plugin_menu.append(menu_item)

    def get_plugin_menu_items(self) -> T.List[MenuItem]:
        """
        Return plugin menu items.

        :return: plugins menu
        """
        return self._plugin_menu
