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
import importlib
import io
import time
import traceback
import typing as T
from pathlib import Path

from pluginbase import PluginBase
from PyQt5 import QtCore

import bubblesub.api  # pylint: disable=unused-import
from bubblesub.cfg.menu import MenuItem
from bubblesub.model import classproperty


class CommandError(RuntimeError):
    """Base class for all command related errors."""


class CommandCanceled(CommandError):
    """The given command was canceled by the user."""

    def __init__(self) -> None:
        """Initialize self."""
        super().__init__("canceled")


class CommandUnavailable(CommandError):
    """The given command cannot be evaluated."""

    def __init__(self, text: T.Optional[str] = None) -> None:
        """
        Initialize self.

        :param text: optional text error
        """
        super().__init__(text or "command not available right now")


class CommandNotFound(CommandError):
    """The given command was not found."""


class BadInvocation(CommandError):
    """The given invocation was invalid."""


class CommandArgumentParser(argparse.ArgumentParser):
    """Overloaded ArgumentParser, suitable for commands."""

    def error(self, message):
        """
        Rather than exiting, raise an exception.

        :param message: error message about to be shown to the user
        """
        with io.StringIO() as handle:
            handle.write(f"{self.prog}: error: {message}\n")
            self.print_help(handle)
            handle.seek(0)
            message = handle.read()
        raise BadInvocation(message)


def split_invocation(invocation: str) -> T.List[T.List[str]]:
    """
    Split invocation into name and arguments array.

    :param invocation: command line to parse
    :return: tuple containing command name and arguments
    """
    cmds: T.List[T.List[str]] = []
    cmd: T.List[str] = []

    invocation = invocation.strip()
    while invocation:
        char = invocation[0]
        invocation = invocation[1:]

        if char in "'\"":
            while invocation:
                char2 = invocation[0]
                invocation = invocation[1:]
                if char2 == char:
                    break
                if cmd:
                    cmd[-1] += char2
                else:
                    cmd.append(char2)
            continue

        if char == ";":
            cmds.append(cmd)
            cmd = []
            continue

        if char in " \t":
            cmd.append("")
            continue

        if cmd:
            cmd[-1] += char
        else:
            cmd.append(char)

    if cmd:
        cmds.append(cmd)

    return cmds


class BaseCommand(abc.ABC):
    """Base class for all commands."""

    silent = False

    def __init__(
        self,
        api: "bubblesub.api.Api",
        args: argparse.Namespace,
        invocation: str,
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param args: command arguments
        :param invocation: cmdline how the comment was ran
        """
        self.api = api
        self.args = args
        self.invocation = invocation

    @classproperty
    @abc.abstractproperty
    def names(  # pylint: disable=no-self-argument
        cls: T.Type["BaseCommand"]
    ) -> T.List[str]:
        """
        Return command names.

        Must be globally unique and should be human readable.

        :param cls: type inheriting from BaseCommand
        :return: command names
        """
        raise NotImplementedError("command has no name")

    @classproperty
    @abc.abstractproperty
    def help_text(self) -> str:
        """
        Return command description shown in help.

        :return: description
        """
        raise NotImplementedError("command has no help text")

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
        raise NotImplementedError("command has no implementation")

    @staticmethod
    def decorate_parser(
        api: "bubblesub.api.Api", parser: argparse.ArgumentParser
    ) -> None:
        """
        Configure argument parser with custom command switches.

        :param api: core API
        :param parser: parser to configure
        """


class CommandApi(QtCore.QObject):
    """The command API."""

    commands_loaded = QtCore.pyqtSignal()

    def __init__(self, api: "bubblesub.api.Api") -> None:
        """
        Initialize self.

        :param api: core API
        """
        super().__init__()
        self._api = api
        self._cmd_registry: T.Dict[str, T.Type[BaseCommand]] = {}
        self._plugin_menu: T.List[MenuItem] = []
        self._plugin_base = PluginBase(package="bubblesub.api.cmd.plugins")
        self._plugin_sources: T.Dict[str, T.Any] = {}
        self._plugin_modules: T.List[T.Any] = []

    def run_cmdline(self, cmdline: T.Union[str, T.List[T.List[str]]]) -> None:
        """
        Run given cmdline.

        :param cmdline: either a list of command arguments, or a plain string
        """
        for cmd in self.parse_cmdline(cmdline):
            self.run(cmd)

    def parse_cmdline(
        self, cmdline: T.Union[str, T.List[T.List[str]]]
    ) -> T.List[BaseCommand]:
        """
        Create BaseCommand instances based on given invocation.

        :param cmdline: either a list of command arguments, or a plain string
        :return: list of command instances
        """
        ret: T.List[BaseCommand] = []
        if not isinstance(cmdline, list):
            cmdline = split_invocation(cmdline)

        for invocation in cmdline:
            cmd_name, *cmd_args = invocation
            cls = self._cmd_registry.get(cmd_name, None)
            if not cls:
                raise CommandNotFound(f'no command named "{cmd_name}"')

            parser = CommandArgumentParser(
                prog=cls.names[0], description=cls.help_text, add_help=False
            )
            cls.decorate_parser(self._api, parser)
            args = parser.parse_args(cmd_args)

            ret.append(cls(self._api, args, " ".join(invocation)))

        return ret

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
        if not cmd.silent:
            self._api.log.command_echo(cmd.invocation)

        try:
            if not cmd.is_enabled:
                raise CommandUnavailable
            await cmd.run()
        except (CommandCanceled, CommandUnavailable) as ex:
            if not cmd.silent:
                self._api.log.warn(str(ex))
            return False
        except CommandError as ex:  # pylint: disable=broad-except
            self._api.log.error(f"problem running {cmd.invocation}:")
            self._api.log.error(f"{ex}")
            return False
        except Exception as ex:  # pylint: disable=broad-except
            self._api.log.error(f"problem running {cmd.invocation}:")
            self._api.log.error(f"{ex}")
            self._api.log.error(traceback.format_exc())
            return False

        end_time = time.time()
        took = end_time - start_time
        if not cmd.silent:
            self._api.log.debug(f"{cmd.invocation}: took {took:.04f} s")
        return True

    def get(self, name: str) -> T.Optional[T.Type[BaseCommand]]:
        """
        Return class by command name.

        :param name: name to search for
        :return: type if command found, None otherwise
        """
        return self._cmd_registry.get(name, None)

    def get_all(self) -> T.List[T.Type[BaseCommand]]:
        """
        Return list of all registered command types.

        :return: list of types
        """
        return list(set(self._cmd_registry.values()))

    def reload_commands(self) -> None:
        """Rescans filesystem for commands."""
        self._unload_commands()
        self._load_commands(
            Path(__file__).parent.parent / "cmd",
            identifier="bubblesub.api.cmd.core",
        )
        if self._api.cfg.root_dir:
            self._load_commands(
                self._api.cfg.root_dir / "scripts",
                identifier="bubblesub.api.cmd.user",
            )
        self.commands_loaded.emit()

    def get_plugin_menu_items(self) -> T.List[MenuItem]:
        """
        Return plugin menu items.

        :return: plugins menu
        """
        return sorted(
            self._plugin_menu,
            key=lambda item: getattr(item, "name", "").replace("&", ""),
        )

    def _unload_commands(self) -> None:
        """Unloads registered commands."""
        for module in self._plugin_modules:
            with self._api.log.exception_guard():
                try:
                    module.on_unload(self._api)
                except AttributeError:
                    pass
        self._plugin_menu[:] = []
        for name, cls in self._cmd_registry.items():
            self._api.log.debug(f"unregistering {cls} as {name}")
        self._cmd_registry.clear()
        self._plugin_modules.clear()
        self._plugin_sources.clear()

    def _load_commands(self, path: Path, identifier: str) -> None:
        """
        Load commands from the specified path.

        Each file must have a `COMMANDS` global constant that contains
        a collection of commands inheriting from BaseCommand.

        Optionally, it can have a `MENU` global constant that contains
        menu item collection that get put in the plugin menu.

        :param path: directory to load the commands from
        :param identifier: unique identifier for this collection of commands
        """
        plugin_source = self._plugin_base.make_plugin_source(
            searchpath=[str(path)], identifier=identifier
        )
        for plugin in plugin_source.list_plugins():
            with self._api.log.exception_guard():
                mod = plugin_source.load_plugin(plugin)
                self._load_module(mod)
        self._plugin_sources[identifier] = plugin_source

    def _load_module(self, mod: importlib.types.ModuleType) -> None:
        # commands
        try:
            commands = mod.COMMANDS
        except AttributeError:
            pass
        else:
            for cls in commands:
                for name in cls.names:
                    self._api.log.debug(f"registering {cls} as {name}")
                    self._cmd_registry[name] = cls

        # menu
        try:
            menu = mod.MENU
        except AttributeError:
            pass
        else:
            self._plugin_menu += menu

        # load hook
        try:
            mod.on_load(self._api)
        except AttributeError:
            pass

        self._plugin_modules.append(mod)

    def unload(self) -> None:
        """Unloads registered commands."""
        self._unload_commands()
