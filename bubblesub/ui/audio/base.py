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

from PyQt5 import QtCore, QtGui, QtWidgets

import bubblesub.api
import bubblesub.api.media.audio

SLIDER_SIZE = 20


class BaseAudioWidget(QtWidgets.QWidget):
    def __init__(
        self, api: bubblesub.api.Api, parent: QtWidgets.QWidget = None
    ) -> None:
        super().__init__(parent)
        self._api = api

        def update(*_: T.Any) -> None:
            self.update()

        api.media.audio.selection_changed.connect(update)
        api.media.audio.view_changed.connect(update)
        api.subs.events.items_inserted.connect(update)
        api.subs.events.items_removed.connect(update)
        api.subs.events.item_changed.connect(update)

    @property
    def _audio(self) -> bubblesub.api.media.audio.AudioApi:
        return self._api.media.audio

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.modifiers() & QtCore.Qt.ControlModifier:
            self._zoomed(
                event.angleDelta().y(), event.pos().x() / self.width()
            )
        else:
            self._scrolled(event.angleDelta().y())

    def _zoomed(self, delta: int, mouse_x: int) -> None:
        cur_factor = self._audio.view_size / self._audio.size
        new_factor = cur_factor * (1.1 if delta < 0 else 0.9)
        self._audio.zoom_view(new_factor, mouse_x)

    def _scrolled(self, delta: int) -> None:
        distance = self._audio.view_size * 0.05
        distance *= 1 if delta < 0 else -1
        self._audio.move_view(int(distance))
