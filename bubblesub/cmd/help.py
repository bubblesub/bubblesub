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

# pylint: disable=protected-access

import argparse

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand


def transform_help(text: str) -> str:
    return text[0].lower() + text[1:].rstrip(".")


def format_action(action: argparse.Action) -> str:
    ret = ""
    if not action.required:
        ret += "["
    ret += "|".join(action.option_strings) or f"{action.dest}" or ""
    if action.option_strings and action.nargs != 0:
        ret += f'={action.default or "…"}'
    if not action.required:
        ret += "]"
    return ret


def add_backticks(text: str, backticks: bool) -> str:
    if backticks:
        return f"`{text}`"
    return text


def get_usage(
    cmd_name: str, parser: argparse.ArgumentParser, backticks: bool
) -> str:
    desc = " ".join(
        [cmd_name] + [format_action(action) for action in parser._actions]
    )
    return "Usage: {}".format(add_backticks(desc, backticks=backticks))


def get_params_help(
    cmd_name: str, parser: argparse.ArgumentParser, backticks: bool
) -> str:
    desc = ""
    for action in parser._actions:
        if not action.help:
            raise ValueError(
                f"Command {cmd_name} has no help text "
                f"for one of its arguments"
            )

        desc += "* "
        desc += (
            ", ".join(
                add_backticks(opt, backticks=backticks)
                for opt in action.option_strings
            )
            or add_backticks(f"{action.dest}", backticks=backticks)
            or ""
        )
        desc += ": "
        desc += action.help
        if action.choices:
            desc += " (can be {})".format(
                ", ".join(
                    add_backticks(f"{choice!s}", backticks=backticks)
                    for choice in action.choices
                )
            )
        desc += "\n"
    return desc.rstrip()


class HelpCommand(BaseCommand):
    names = ["help"]
    help_text = "Lists available commands."

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "cmd", help="command name to get help for", type=str, nargs="?"
        )

    async def run(self) -> None:
        if self.args.cmd:
            self._show_help_for_command(self.args.cmd)
        else:
            self._show_help_for_all_commands()

    def _show_help_for_command(self, cmd_name: str) -> None:
        cls = self.api.cmd.get(cmd_name)
        if not cls:
            self.api.log.error(f'no command named "{cmd_name}"')
            return

        parser = argparse.ArgumentParser(
            add_help=False,
            prog=cls.names[0],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        cls.decorate_parser(self.api, parser)

        self.api.log.info(cls.names[0])

        if len(cls.names) > 1:
            self.api.log.info(
                "(aliases: {})\n".format(
                    ", ".join(f"{alias}" for alias in cls.names[1:])
                )
            )

        self.api.log.info(cls.help_text)
        if cls.help_text_extra:
            self.api.log.info(cls.help_text_extra)
        if parser._actions:
            self.api.log.info("")
            self.api.log.info(get_usage(cmd_name, parser, backticks=False))
            self.api.log.info(
                get_params_help(cmd_name, parser, backticks=False)
            )

    def _show_help_for_all_commands(self) -> None:
        self.api.log.info("available core commands:")
        self._list_commands(self.api.cmd.CORE_COMMAND)

        if self.api.cmd.get_all(self.api.cmd.USER_COMMAND):
            self.api.log.info("")
            self.api.log.info("available user commands:")
            self._list_commands(self.api.cmd.USER_COMMAND)

    def _list_commands(self, identifier: str) -> None:
        for cls in sorted(
            self.api.cmd.get_all(identifier), key=lambda cls: cls.names[0],
        ):
            self.api.log.info(
                f"- {cls.names[0]}: {transform_help(cls.help_text)}"
            )


COMMANDS = [HelpCommand]
