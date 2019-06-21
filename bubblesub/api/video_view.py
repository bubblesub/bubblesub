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

"""API for video viewport."""

import fractions
import typing as T

from PyQt5 import QtCore

from bubblesub.api.subs import SubtitlesApi


class VideoViewApi(QtCore.QObject):
    zoom_changed = QtCore.pyqtSignal()

    def __init__(self, subs_api: SubtitlesApi) -> None:
        """Initialize self.

        :param subs_api: subtitles API
        """
        super().__init__()

        self._zoom = fractions.Fraction(0, 1)

        subs_api.loaded.connect(self.reset_view)

        self.reset_view()

    @property
    def zoom(self) -> fractions.Fraction:
        """Return zoom factor.

        :return: zoom factor
        """
        return self._zoom

    @zoom.setter
    def zoom(self, value: T.Union[fractions.Fraction, int, float]) -> None:
        """Sets new zoom factor.

        :param value: new zoom factor
        """
        if not isinstance(value, fractions.Fraction):
            value = fractions.Fraction(value)
        if value != self._zoom:
            self._zoom = value
            self.zoom_changed.emit()

    def reset_view(self) -> None:
        """Resets the view to the defaults."""
        self.zoom = 0
