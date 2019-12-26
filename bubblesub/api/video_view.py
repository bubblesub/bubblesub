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
    """API for video preview."""

    zoom_changed = QtCore.pyqtSignal()
    pan_changed = QtCore.pyqtSignal()

    def __init__(self, subs_api: SubtitlesApi) -> None:
        """Initialize self.

        :param subs_api: subtitles API
        """
        super().__init__()

        self._zoom = fractions.Fraction(0, 1)
        self._pan = (fractions.Fraction(0, 1), fractions.Fraction(0, 1))

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
        """Set new zoom factor.

        :param value: new zoom factor
        """
        if not isinstance(value, fractions.Fraction):
            value = fractions.Fraction(value)
        if value != self._zoom:
            self._zoom = value
            self.zoom_changed.emit()

    @property
    def pan(self) -> T.Tuple[fractions.Fraction, fractions.Fraction]:
        """Return pan.

        :return: pan
        """
        return self._pan

    @pan.setter
    def pan(
        self, value: T.Tuple[fractions.Fraction, fractions.Fraction]
    ) -> None:
        """Set new pan.

        :param value: new pan
        """
        if value != self._pan:
            self._pan = value
            self.pan_changed.emit()

    @property
    def pan_x(self) -> fractions.Fraction:
        """Return x pan position.

        :return: x pan position
        """
        return self._pan[0]

    @pan_x.setter
    def pan_x(self, value: fractions.Fraction) -> None:
        """Set new x pan position.

        :param value: new x pan position
        """
        self.pan = (value, self.pan[1])

    @property
    def pan_y(self) -> fractions.Fraction:
        """Return y pan position.

        :return: y pan position
        """
        return self._pan[1]

    @pan_y.setter
    def pan_y(self, value: fractions.Fraction) -> None:
        """Set new y pan position.

        :param value: new y pan position
        """
        self.pan = (self.pan[0], value)

    def reset_view(self) -> None:
        """Resets the view to the defaults."""
        self.zoom = fractions.Fraction(0, 1)
        self.pan = (fractions.Fraction(0, 1), fractions.Fraction(0, 1))
