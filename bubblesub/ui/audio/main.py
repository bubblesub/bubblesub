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

from PyQt5 import QtCore, QtWidgets

from bubblesub.api import Api
from bubblesub.api.audio import AudioState
from bubblesub.ui.audio.audio_preview import AudioPreview
from bubblesub.ui.audio.audio_slider import AudioSlider
from bubblesub.ui.audio.audio_timeline import AudioTimeline
from bubblesub.ui.audio.video_preview import VideoPreview


class Audio(QtWidgets.QWidget):
    def __init__(self, api: Api, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self._api = api
        self._audio_timeline = AudioTimeline(self._api, self)
        self._audio_preview = AudioPreview(self._api, self)
        self._video_preview = VideoPreview(self._api, self)
        self._slider = AudioSlider(self._api, self)

        self.setObjectName("spectrogram")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._audio_timeline)
        layout.addWidget(self._audio_preview)
        layout.addWidget(self._video_preview)
        layout.addWidget(self._slider)

        api.audio.state_changed.connect(self._on_audio_state_change)

        api.subs.events.items_inserted.connect(self._sync_selection)
        api.subs.events.items_removed.connect(self._sync_selection)
        api.subs.events.items_moved.connect(self._sync_selection)
        api.subs.selection_changed.connect(
            lambda _rows, _changed: self._sync_selection()
        )

    def shutdown(self) -> None:
        self._video_preview.shutdown()

    def _on_audio_state_change(self, state: AudioState) -> None:
        if state == AudioState.Loaded:
            self._api.audio.view.reset_view()

    def _sync_selection(self) -> None:
        if len(self._api.subs.selected_indexes) >= 1:
            first_sub = self._api.subs.selected_events[0]
            last_sub = self._api.subs.selected_events[-1]
            self._api.audio.view.view(
                first_sub.start - 10000, last_sub.end + 10000
            )
            self._api.audio.view.select(first_sub.start, last_sub.end)
        else:
            self._api.audio.view.unselect()
