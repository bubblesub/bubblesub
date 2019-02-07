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
from bubblesub.api.gui import GuiApi
from bubblesub.api.log import LogApi
from bubblesub.api.media import MediaApi
from bubblesub.api.subs import SubtitlesApi
from bubblesub.api.undo import UndoApi
from bubblesub.cfg import Config


class Api:
    """Core class grouping all descendant APIs."""

    def __init__(self, args: argparse.Namespace) -> None:
        """
        Initialize self.

        :param args: CLI arguments
        """
        self.cfg = Config()
        self.log = LogApi(self.cfg)
        self.subs = SubtitlesApi()
        self.media = MediaApi(self.subs, self.log, self.cfg, args)
        self.undo = UndoApi(self.cfg, self.subs)

        self.gui = GuiApi(self)
        self.cmd = bubblesub.api.cmd.CommandApi(self)

        self.gui.quit_confirmed.connect(self.media.unload)
