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

"""Miscellaneous commands."""

from bubblesub.api.cmd import CoreCommand


class ResetPluginsCommand(CoreCommand):
    """Reloads the user plugins."""

    name = 'misc/reload-plugins'
    menu_name = 'Reload plugins'

    async def run(self) -> None:
        """Carry out the command."""
        if self.api.opt.root_dir:
            self.api.cmd.load_plugins(self.api.opt.root_dir / 'scripts')
