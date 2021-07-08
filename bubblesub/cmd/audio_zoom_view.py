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

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.ui.views import TargetWidget


class AudioZoomViewCommand(BaseCommand):
    names = ["audio-zoom-view", "spectrogram-zoom-view"]
    help_text = "Zooms the spectrogram in or out by the specified factor."

    @property
    def is_enabled(self) -> bool:
        return self.api.gui.is_widget_visible(TargetWidget.SPECTROGRAM.value)

    async def run(self) -> None:
        mouse_x = 0.5
        cur_factor = self.api.audio.view.view_size / max(
            1, self.api.audio.view.size
        )
        new_factor = cur_factor * self.args.delta
        self.api.audio.view.zoom_view(new_factor, mouse_x)

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-d",
            "--delta",
            help="factor to zoom the viewport by",
            type=float,
            required=True,
        )


COMMANDS = [AudioZoomViewCommand]
