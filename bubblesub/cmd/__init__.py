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

"""Command layer."""

import bubblesub.api
import bubblesub.cmd.file
import bubblesub.cmd.grid
import bubblesub.cmd.edit
import bubblesub.cmd.search
import bubblesub.cmd.audio
import bubblesub.cmd.video
import bubblesub.cmd.karaoke
import bubblesub.cmd.view
import bubblesub.cmd.spellcheck
import bubblesub.cmd.styles_manager
import bubblesub.cmd.misc


def register_core_commands(api: bubblesub.api.Api) -> None:
    """
    Register core commands in the API.

    :param api: API instance to register the commands in
    """
    for cls in bubblesub.api.cmd.CoreCommand.__subclasses__():
        api.cmd.register_core_command(cls)
