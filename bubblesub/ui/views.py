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


class ViewLayout(enum.Enum):
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


class ViewLayoutManager(QtCore.QObject):
    def __init__(self, api: Api, main_window: QtWidgets.QMainWindow) -> None:
        super().__init__(main_window)

        self._api = api
        self._main_window = main_window
        self._view_layout = ViewLayout.Full

    @property
    def view_layout(self) -> ViewLayout:
        return self._view_layout

    @view_layout.setter
    def view_layout(self, view_layout: ViewLayout) -> None:
        if self._view_layout == view_layout:
            return

        self._run_view(view_layout)

    def restore_view_layout(self) -> None:
        view_layout = ViewLayout(self._api.cfg.opt["view"]["current"])
        self._run_view(view_layout)

    def store_view_layout(self) -> None:
        view = {
            ViewLayout.Full: "full",
            ViewLayout.Audio: "audio",
            ViewLayout.Video: "video",
            ViewLayout.Subs: "subs",
        }.get(self._view_layout)

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

    def _run_view(self, view_layout: ViewLayout) -> None:
        func = {
            ViewLayout.Full: self._full_view_layout,
            ViewLayout.Audio: self._audio_view_layout,
            ViewLayout.Video: self._video_view_layout,
            ViewLayout.Subs: self._subs_view_layout,
        }.get(view_layout)

        if func is not None:
            func()
        else:
            self._api.log.error(f"Error setting the view")

    def _audio_view_layout(self) -> None:
        self._view_layout = ViewLayout.Audio

        self._api.playback.is_paused = True

        self._widgets_visibility(
            spectrogram="show",
            audio_label="show",
            video="hide",
            frame_label="hide",
        )

    def _video_view_layout(self) -> None:
        self._view_layout = ViewLayout.Video

        self._api.playback.is_paused = True

        self._widgets_visibility(
            spectrogram="hide",
            audio_label="hide",
            video="show",
            frame_label="show",
        )

        self._api.cmd.run_cmdline("show-widget video-volume -m hide")

    def _subs_view_layout(self) -> None:
        self._view_layout = ViewLayout.Subs

        self._api.playback.is_paused = True
        self._widgets_visibility(
            spectrogram="hide",
            audio_label="hide",
            video="hide",
            frame_label="hide",
        )

    def _full_view_layout(self) -> None:
        self._view_layout = ViewLayout.Full

        self._api.playback.is_paused = True

        self._widgets_visibility(
            spectrogram="show",
            audio_label="show",
            video="show",
            frame_label="show",
        )
        self._api.cmd.run_cmdline("show-widget video-volume -m show")

    def _widgets_visibility(
        self, spectrogram: str, audio_label: str, video: str, frame_label: str
    ) -> None:
        self._api.cmd.run_cmdline("show-widget spectrogram -m " + spectrogram)
        self._api.cmd.run_cmdline(
            "show-widget status-audio-label -m " + audio_label
        )
        self._api.cmd.run_cmdline("show-widget video-container -m " + video)
        self._api.cmd.run_cmdline(
            "show-widget status-frame-label -m " + frame_label
        )
