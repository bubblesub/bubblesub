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
from bubblesub.api.audio import AudioApi
from bubblesub.api.audio_view import AudioViewApi
from bubblesub.api.gui import GuiApi
from bubblesub.api.log import LogApi
from bubblesub.api.playback import PlaybackApi
from bubblesub.api.subs import SubtitlesApi
from bubblesub.api.undo import UndoApi
from bubblesub.api.video import VideoApi
from bubblesub.cfg import Config


class Api:
    """Core class grouping all descendant APIs."""

    def __init__(self, args: argparse.Namespace) -> None:
        """
        Initialize self.

        :param args: CLI arguments
        """
        self.args = args

        self.cfg = Config()
        self.log = LogApi(self.cfg)
        self.subs = SubtitlesApi()
        self.undo = UndoApi(self.cfg, self.subs)

        self.video = VideoApi(self.log, self.subs)
        self.audio = AudioApi(self.log, self.subs)
        self.playback = PlaybackApi(
            self.log, self.subs, self.video, self.audio
        )

        self.audio.view = AudioViewApi(self.subs, self.audio, self.video)

        self.gui = GuiApi(self)
        self.cmd = bubblesub.api.cmd.CommandApi(self)

        self.gui.terminated.connect(self.audio.unload)
        self.gui.terminated.connect(self.video.unload)
        self.gui.terminated.connect(self.cmd.unload)
        self.subs.loaded.connect(self._on_subs_load)

    def _on_subs_load(self) -> None:
        if self.subs.remembered_video_path:
            self.video.load(self.subs.remembered_video_path)
        else:
            self.video.unload()

        if self.subs.remembered_audio_path:
            self.audio.load(self.subs.remembered_audio_path)
        else:
            self.audio.unload()

    def shutdown(self) -> None:
        """Stop internal worker threads."""
        self.audio.shutdown()
        self.video.shutdown()
