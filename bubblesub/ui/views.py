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

from PyQt5 import QtCore, QtWidgets

from bubblesub.api import Api


class View(enum.Enum):
    def __str__(self) -> str:
        return self.value

    Full = "full"
    Audio = "audio"
    Video = "video"
    Subs = "subs"


class TargetWidget(enum.Enum):
    def __str__(self) -> str:
        return self.value

    NoteEditor = "note-editor"
    VideoContainer = "video-container"
    VideoController = "video-controller"
    VideoVolume = "video-volume"
    Status = "status"
    StatusFrameLabel = "status-frame-label"
    StatusAudioLabel = "status-audio-label"
    TextEditor = "text-editor"
    StyleEditor = "style-editor"
    ActorEditor = "actor-editor"
    LayerEditor = "layer-editor"
    MarginLeftEditor = "margin-left-editor"
    MarginRightEditor = "margin-right-editor"
    MarginVerticalEditor = "margin-vertical-editor"
    StartTimeEditor = "start-time-editor"
    EndTimeEditor = "end-time-editor"
    DurationEditor = "duration-editor"
    CommentCheckbox = "comment-checkbox"
    SubtitlesGrid = "subtitles-grid"
    Spectrogram = "spectrogram"
    ConsoleContainer = "console-container"
    ConsoleWindow = "console-window"
    ConsoleInput = "console-input"


VIEW_WIDGET_VISIBILITY_MAP = {
    View.Full: {
        TargetWidget.Spectrogram: True,
        TargetWidget.VideoContainer: True,
        TargetWidget.StatusAudioLabel: True,
        TargetWidget.StatusFrameLabel: True,
    },
    View.Audio: {
        TargetWidget.Spectrogram: True,
        TargetWidget.VideoContainer: False,
        TargetWidget.StatusAudioLabel: True,
        TargetWidget.StatusFrameLabel: False,
    },
    View.Video: {
        TargetWidget.Spectrogram: False,
        TargetWidget.VideoContainer: True,
        TargetWidget.StatusAudioLabel: False,
        TargetWidget.StatusFrameLabel: True,
    },
    View.Subs: {
        TargetWidget.Spectrogram: False,
        TargetWidget.VideoContainer: False,
        TargetWidget.StatusAudioLabel: False,
        TargetWidget.StatusFrameLabel: False,
    },
}


class ViewManager(QtCore.QObject):
    def __init__(self, api: Api, main_window: QtWidgets.QMainWindow) -> None:
        super().__init__(main_window)
        self._api = api
        self._main_window = main_window
        self._view = View.Full

    @property
    def current_view(self) -> View:
        return self._view

    def set_view(self, view: View) -> None:
        if self._view != view:
            self._run_view(view)

    def restore_view_layout(self) -> None:
        view = View(self._api.cfg.opt["view"]["current"])
        self._run_view(view)

    def store_view_layout(self) -> None:
        view = {
            View.Full: "full",
            View.Audio: "audio",
            View.Video: "video",
            View.Subs: "subs",
        }.get(self._view)

        self._api.cfg.opt["view"]["current"] = view

    def restore_widgets_visibility(self) -> None:
        for (key, data) in self._api.cfg.opt["gui"]["visibility"].items():
            widget = self._main_window.findChild(QtWidgets.QWidget, key)
            widget.setVisible(data)

    def store_widgets_visibility(self) -> None:
        def _store_widget(widget_name: str) -> bool:
            widget = self._main_window.findChild(
                QtWidgets.QWidget, widget_name
            )
            return widget.isVisible()

        self._api.cfg.opt["gui"]["visibility"] = {
            "console": _store_widget("console-container"),
            "note-editor": _store_widget("note-editor"),
            "video-controller": _store_widget("video-controller"),
        }

    def _run_view(self, view: View) -> None:
        visibility_map = VIEW_WIDGET_VISIBILITY_MAP[view]

        self._view = view
        self._api.playback.is_paused = True

        for widget, visible in visibility_map.items():
            self._main_window.findChild(
                QtWidgets.QWidget, widget.value
            ).setVisible(visible)
