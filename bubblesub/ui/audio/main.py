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

import enum

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QSplitter, QVBoxLayout, QWidget

from bubblesub.api import Api
from bubblesub.ui.audio.audio_preview import AudioPreview
from bubblesub.ui.audio.audio_slider import AudioSlider
from bubblesub.ui.audio.audio_timeline import AudioTimeline
from bubblesub.ui.audio.video_preview import VideoPreview
from bubblesub.ui.themes import ThemeManager


class AutoSelectionStyle(enum.Enum):
    def __str__(self) -> str:
        return self.value

    DISABLED = "none"
    DYNAMIC = "dynamic"
    CONSTANT = "constant"


class Audio(QSplitter):
    def __init__(
        self, api: Api, theme_mgr: ThemeManager, parent: QWidget
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._audio_timeline = AudioTimeline(self._api, theme_mgr, self)
        self._audio_preview = AudioPreview(self._api, theme_mgr, self)
        self._video_preview = VideoPreview(self._api, self)
        self._slider = AudioSlider(self._api, theme_mgr, self)

        self.setObjectName("spectrogram")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        top_part = QWidget(self)
        top_part_layout = QVBoxLayout(top_part)
        top_part_layout.setSpacing(0)
        top_part_layout.setContentsMargins(0, 0, 0, 0)
        top_part_layout.addWidget(self._audio_timeline)
        top_part_layout.addWidget(self._audio_preview)

        bottom_part = QWidget(self)
        bottom_part_layout = QVBoxLayout(bottom_part)
        bottom_part_layout.setSpacing(0)
        bottom_part_layout.setContentsMargins(0, 0, 0, 0)
        bottom_part_layout.addWidget(self._video_preview)
        bottom_part_layout.addWidget(self._slider)

        self.addWidget(top_part)
        self.addWidget(bottom_part)
        self.setStretchFactor(0, 3)
        self.setStretchFactor(1, 1)
        self.setHandleWidth(0)
        self.setOrientation(Qt.Orientation.Vertical)

        api.subs.loaded.connect(self._on_subs_load)

    def _on_subs_load(self) -> None:
        self._api.subs.events.items_removed.subscribe(
            lambda _event: self._sync_selection()
        )
        self._api.subs.events.items_inserted.subscribe(
            lambda _event: self._sync_selection()
        )
        self._api.subs.selection_changed.connect(
            lambda _rows, _changed: self._sync_selection()
        )

    def _sync_selection(self) -> None:
        if not self._api.subs.selected_indexes:
            self._api.audio.view.unselect()
            return

        auto_view_style = self._api.cfg.opt["audio"]["auto_view_style"]
        auto_view_lead_in = self._api.cfg.opt["audio"]["auto_view_lead_in"]
        auto_view_lead_out = self._api.cfg.opt["audio"]["auto_view_lead_out"]
        auto_view_min = self._api.cfg.opt["audio"]["auto_view_max"]
        auto_view_max = self._api.cfg.opt["audio"]["auto_view_max"]
        auto_sel_subtitle = self._api.cfg.opt["audio"]["auto_sel_subtitle"]

        if auto_view_style == AutoSelectionStyle.DYNAMIC.value:
            first_sub = self._api.subs.selected_events[0]
            last_sub = self._api.subs.selected_events[-1]
            view_start = first_sub.start - auto_view_lead_in
            view_end = last_sub.end + auto_view_lead_out

            if view_end - view_start > auto_view_max:
                center = (view_start + view_end) / 2
                view_start = center - auto_view_max / 2
                view_end = center + auto_view_max / 2

            if view_end - view_start < auto_view_min:
                center = (view_start + view_end) / 2
                view_start = center - auto_view_min / 2
                view_end = center + auto_view_min / 2

            self._api.audio.view.view(view_start, view_end)

        elif auto_view_style == AutoSelectionStyle.CONSTANT.value:
            first_sub = self._api.subs.selected_events[0]
            last_sub = self._api.subs.selected_events[-1]
            center = (first_sub.start + last_sub.end) / 2
            view_start = center - auto_view_max / 2
            view_end = center + auto_view_max / 2
            self._api.audio.view.view(view_start, view_end)

        if auto_sel_subtitle:
            self._api.audio.view.select(first_sub.start, last_sub.end)
