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

import typing as T

from PyQt5 import QtWidgets

from bubblesub.ui.themes.base import BaseTheme


class SystemTheme(BaseTheme):
    name = "system"

    def apply(self) -> None:
        QtWidgets.QApplication.setStyle("")
        QtWidgets.QApplication.instance().setStyleSheet("")

    @property
    def palette(self) -> T.Dict[str, str]:
        return {
            "spectrogram/mouse-marker": "#40C04080",
            "spectrogram/video-marker": "#00A000",
            "spectrogram/keyframe": "#FF800078",
            "spectrogram/selected-sub-text": "#FFFFFF",
            "spectrogram/selected-sub-line": "#2A82DADC",
            "spectrogram/selected-sub-fill": "#2A82DA32",
            "spectrogram/unselected-sub-text": "#000000",
            "spectrogram/unselected-sub-line": "#2A82DA78",
            "spectrogram/unselected-sub-fill": "#2A82DA1E",
            "spectrogram/focused-sel-line": "#90A000DC",
            "spectrogram/focused-sel-fill": "#A0FF003C",
            "spectrogram/unfocused-sel-line": "#90A0006E",
            "spectrogram/unfocused-sel-fill": "#A0FF001E",
            "grid/ass-mark": "#E60000",
            "grid/comment": "#EFEBE7",
            "console/error": "#FF0000",
            "console/warning": "#C86400",
            "console/info": "#000000",
            "console/debug": "#0064C8",
            "console/timestamp": "#787878",
            "console/command": "#008000",
        }
