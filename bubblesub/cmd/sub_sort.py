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

import argparse
from copy import copy

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand, CommandUnavailable
from bubblesub.cmd.common import Pts, SubtitlesSelection


class SubtitlesSortCommand(BaseCommand):
    names = ["sub-sort"]
    help_text = "Sorts all subtitles by their start time."

    @property
    def is_enabled(self) -> bool:
        return len(self.api.subs.events) > 0

    async def run(self) -> None:
        with self.api.undo.capture(), self.api.gui.throttle_updates():
            events = sorted(
                self.api.subs.events, key=lambda event: event.start
            )
            self.api.subs.events[:] = events


COMMANDS = [SubtitlesSortCommand]
