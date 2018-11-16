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
Core API.

Encapsulates most of the program state and offers simple interfaces
to manipulate it.
"""

import argparse

import bubblesub.api.cmd
import bubblesub.api.gui
import bubblesub.api.log
import bubblesub.api.media
import bubblesub.api.subs
import bubblesub.api.undo
import bubblesub.opt


class Api:
    """Core class grouping all descendant APIs."""

    def __init__(self, args: argparse.Namespace) -> None:
        """
        Initialize self.

        :param args: CLI arguments
        """
        self.opt = bubblesub.opt.Options()
        self.log = bubblesub.api.log.LogApi()
        self.gui = bubblesub.api.gui.GuiApi(self)
        self.subs = bubblesub.api.subs.SubtitlesApi()
        self.media = bubblesub.api.media.MediaApi(
            self.subs, self.log, self.opt, args
        )
        self.undo = bubblesub.api.undo.UndoApi(self.opt, self.subs)
        self.cmd = bubblesub.api.cmd.CommandApi(self)

        self.gui.quit_confirmed.connect(self.media.unload)
