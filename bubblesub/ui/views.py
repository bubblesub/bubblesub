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

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QMainWindow, QWidget

from bubblesub.api import Api


class View(enum.Enum):
    def __str__(self) -> str:
        return self.value

    FULL = "full"
    AUDIO = "audio"
    VIDEO = "video"
    SUBS = "subs"


class TargetWidget(enum.Enum):
    def __str__(self) -> str:
        return self.value

    NOTE_EDITOR = "note-editor"
    VIDEO_CONTAINER = "video-container"
    VIDEO_CONTROLLER = "video-controller"
    VIDEO_VOLUME = "video-volume"
    STATUS = "status"
    STATUS_FRAME_LABEL = "status-frame-label"
    STATUS_AUDIO_LABEL = "status-audio-label"
    TEXT_EDITOR = "text-editor"
    STYLE_EDITOR = "style-editor"
    ACTOR_EDITOR = "actor-editor"
    LAYER_EDITOR = "layer-editor"
    MARGIN_LEFT_EDITOR = "margin-left-editor"
    MARGIN_RIGHT_EDITOR = "margin-right-editor"
    MARGIN_VERTICAL_EDITOR = "margin-vertical-editor"
    START_TIME_EDITOR = "start-time-editor"
    END_TIME_EDITOR = "end-time-editor"
    DURATION_EDITOR = "duration-editor"
    COMMENT_CHECKBOX = "comment-checkbox"
    SUBTITLES_GRID = "subtitles-grid"
    SPECTROGRAM = "spectrogram"
    CONSOLE_CONTAINER = "console-container"
    CONSOLE_WINDOW = "console-window"
    CONSOLE_INPUT = "console-input"


VIEW_WIDGET_VISIBILITY_MAP = {
    View.FULL: {
        TargetWidget.SPECTROGRAM: True,
        TargetWidget.VIDEO_CONTAINER: True,
        TargetWidget.STATUS_AUDIO_LABEL: True,
        TargetWidget.STATUS_FRAME_LABEL: True,
    },
    View.AUDIO: {
        TargetWidget.SPECTROGRAM: True,
        TargetWidget.VIDEO_CONTAINER: False,
        TargetWidget.STATUS_AUDIO_LABEL: True,
        TargetWidget.STATUS_FRAME_LABEL: False,
    },
    View.VIDEO: {
        TargetWidget.SPECTROGRAM: False,
        TargetWidget.VIDEO_CONTAINER: True,
        TargetWidget.STATUS_AUDIO_LABEL: False,
        TargetWidget.STATUS_FRAME_LABEL: True,
    },
    View.SUBS: {
        TargetWidget.SPECTROGRAM: False,
        TargetWidget.VIDEO_CONTAINER: False,
        TargetWidget.STATUS_AUDIO_LABEL: False,
        TargetWidget.STATUS_FRAME_LABEL: False,
    },
}


class ViewManager(QObject):
    def __init__(self, api: Api, main_window: QMainWindow) -> None:
        super().__init__(main_window)
        self._api = api
        self._main_window = main_window
        self._view = View.FULL

    @property
    def current_view(self) -> View:
        return self._view

    def set_view(self, view: View) -> None:
        if self._view != view:
            self._run_view(view)

    def restore_view(self) -> None:
        self._view = View(self._api.cfg.opt["view"]["current"])
        for widget in TargetWidget:
            visibility = self._api.cfg.opt["gui"]["visibility"].get(
                widget.value
            )
            if visibility is not None:
                self._main_window.findChild(QWidget, widget.value).setVisible(
                    visibility
                )

    def store_view(self) -> None:
        visibility_map = {}
        for target_widget in TargetWidget:
            widget = self._main_window.findChild(QWidget, target_widget.value)

            parent = widget.parent()
            parents_visible = parent.isVisible()
            while parent:
                parents_visible &= parent.isVisible()
                parent = parent.parent()

            if parents_visible:
                visibility_map[target_widget.value] = widget.isVisible()

        self._api.cfg.opt["gui"]["visibility"] = visibility_map
        self._api.cfg.opt["view"]["current"] = self._view.value

    def _run_view(self, view: View) -> None:
        visibility_map = VIEW_WIDGET_VISIBILITY_MAP[view]

        self._view = view
        self._api.playback.is_paused = True

        for widget, visible in visibility_map.items():
            self._main_window.findChild(QWidget, widget.value).setVisible(
                visible
            )
