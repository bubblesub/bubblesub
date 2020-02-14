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

import bubblesub.api
import bubblesub.util


class StatusBar(QtWidgets.QStatusBar):
    def __init__(
        self, api: bubblesub.api.Api, parent: QtWidgets.QWidget
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._subs_label = QtWidgets.QLabel(self)
        self._video_frame_label = QtWidgets.QLabel(self)
        self._audio_selection_label = QtWidgets.QLabel(self)
        self.setSizeGripEnabled(False)

        self.setObjectName("status")
        self._audio_selection_label.setObjectName("status-audio-label")
        self._video_frame_label.setObjectName("status-frame-label")

        for label in [
            self._subs_label,
            self._video_frame_label,
            self._audio_selection_label,
        ]:
            label.setFrameStyle(
                QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken
            )
            label.setLineWidth(1)

        self.addPermanentWidget(self._subs_label)
        self.addPermanentWidget(self._video_frame_label)
        self.addPermanentWidget(self._audio_selection_label)

        api.subs.selection_changed.connect(self._on_subs_selection_change)
        api.playback.current_pts_changed.connect(self._on_current_pts_change)
        api.audio.view.selection_changed.connect(
            self._on_audio_selection_change
        )

    def _on_subs_selection_change(self) -> None:
        count = len(self._api.subs.selected_indexes)
        total = len(self._api.subs.events)

        if count == 0:
            self._subs_label.setText(f"Subtitles: -/{total} (-%)")
        elif count == 1:
            idx = self._api.subs.selected_indexes[0]
            self._subs_label.setText(
                f"Subtitles: {idx + 1}/{total} ({idx / total:.1%})"
            )
        else:

            def format_range(low: int, high: int) -> str:
                return f"{low}..{high}" if low != high else str(low)

            ranges: T.List[T.Tuple[int, int]] = []
            for idx in self._api.subs.selected_indexes:
                if ranges and ranges[-1][1] == idx - 1:
                    ranges[-1] = (ranges[-1][0], idx)
                else:
                    ranges.append((idx, idx))

            self._subs_label.setText(
                "Subtitles: {}/{} ({}, {:.1%})".format(
                    ",".join(
                        format_range(low + 1, high + 1) for low, high in ranges
                    ),
                    total,
                    count,
                    count / total,
                )
            )

    def _on_current_pts_change(self) -> None:
        self._video_frame_label.setText(
            "Video frame: {} ({:.1%})".format(
                bubblesub.util.ms_to_str(self._api.playback.current_pts),
                self._api.playback.current_pts
                / max(1, self._api.playback.max_pts),
            )
        )

    def _on_audio_selection_change(self) -> None:
        def format_ms_delta(delta: int) -> str:
            ret = bubblesub.util.ms_to_str(abs(delta))
            ret = ("\u2212", "+")[delta >= 0] + ret
            return ret

        if len(self._api.subs.selected_events) != 1:
            return
        sub = self._api.subs.selected_events[0]
        start_delta = self._api.audio.view.selection_start - sub.start
        end_delta = self._api.audio.view.selection_end - sub.end

        self._audio_selection_label.setText(
            "Audio selection: {} / {} (duration: {})".format(
                format_ms_delta(start_delta),
                format_ms_delta(end_delta),
                bubblesub.util.ms_to_str(self._api.audio.view.selection_size),
            )
        )
