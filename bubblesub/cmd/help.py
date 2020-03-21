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

from bubblesub.api.cmd import BaseCommand


def transform_help(text: str) -> str:
    return text[0].lower() + text[1:].rstrip(".")


class HelpCommand(BaseCommand):
    names = ["help"]
    help_text = "Lists available commands."

    async def run(self) -> None:
        self.api.log.info("available core commands:")
        self._list(self.api.cmd.CORE_COMMAND)

        if self.api.cmd.get_all(self.api.cmd.USER_COMMAND):
            self.api.log.info("")
            self.api.log.info("available user commands:")
            self._list(self.api.cmd.USER_COMMAND)

    def _list(self, identifier: str) -> None:
        for cls in sorted(
            self.api.cmd.get_all(identifier), key=lambda cls: cls.names[0],
        ):
            self.api.log.info(
                f"- {cls.names[0]}: {transform_help(cls.help_text)}"
            )


COMMANDS = [HelpCommand]
