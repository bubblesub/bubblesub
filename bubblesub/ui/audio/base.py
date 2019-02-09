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

import bisect
import math
import typing as T

from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.api import Api
from bubblesub.api.media.audio import AudioApi

SLIDER_SIZE = 20


class BaseAudioWidget(QtWidgets.QWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self._api = api

        def update(*_: T.Any) -> None:
            self.update()

        api.media.audio.selection_changed.connect(update)
        api.media.audio.view_changed.connect(update)
        api.subs.events.item_changed.connect(update)
        api.subs.events.items_inserted.connect(update)
        api.subs.events.items_removed.connect(update)
        api.subs.events.items_moved.connect(update)

    @property
    def _audio(self) -> AudioApi:
        return self._api.media.audio

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.modifiers() & QtCore.Qt.ControlModifier:
            self._zoomed(
                event.angleDelta().y(), event.pos().x() / self.width()
            )
        else:
            self._scrolled(event.angleDelta().y())

    def _zoomed(self, delta: int, mouse_x: int) -> None:
        if not self._audio.size:
            return
        cur_factor = self._audio.view_size / self._audio.size
        new_factor = cur_factor * (1.1 if delta < 0 else 0.9)
        self._audio.zoom_view(new_factor, mouse_x)

    def _scrolled(self, delta: int) -> None:
        if not self._audio.size:
            return
        distance = self._audio.view_size * 0.05
        distance *= 1 if delta < 0 else -1
        self._audio.move_view(int(distance))


class BaseLocalAudioWidget(BaseAudioWidget):
    def pts_to_x(self, pts: int) -> float:
        scale = self.width() / max(1, self._audio.view_size)
        return math.floor((pts - self._audio.view_start) * scale)

    def pts_from_x(self, x: float) -> int:
        scale = self._audio.view_size / self.width()
        return int(x * scale + self._audio.view_start)

    def frame_idx_from_x(self, x: int) -> int:
        pts = self.pts_from_x(x)
        return max(
            0, bisect.bisect_left(self._api.media.video.timecodes, pts) - 1
        )


class BaseGlobalAudioWidget(BaseAudioWidget):
    def pts_to_x(self, pts: int) -> float:
        scale = T.cast(int, self.width()) / max(1, self._audio.size)
        return (pts - self._audio.min) * scale

    def pts_from_x(self, x: float) -> int:
        scale = self._audio.size / self.width()
        return int(x * scale + self._audio.min)
