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


class UndoCommand(BaseCommand):
    names = ["undo"]
    help_text = "Undoes last edit operation."

    @property
    def is_enabled(self) -> bool:
        return self.api.undo.has_undo

    async def run(self) -> None:
        self.api.undo.undo()


class RedoCommand(BaseCommand):
    names = ["redo"]
    help_text = "Redoes last edit operation."

    @property
    def is_enabled(self) -> bool:
        return self.api.undo.has_redo

    async def run(self) -> None:
        self.api.undo.redo()


COMMANDS = [UndoCommand, RedoCommand]
