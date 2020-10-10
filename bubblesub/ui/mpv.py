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

# pylint: disable=no-member

import io
import locale
import typing as T

import mpv
from PyQt5 import QtCore, QtOpenGL, QtWidgets

from bubblesub.api import Api
from bubblesub.api.audio_stream import AudioStream
from bubblesub.api.playback import PlaybackFrontendState
from bubblesub.api.video_stream import VideoStream
from bubblesub.fmt.ass.writer import write_ass
from bubblesub.util import ms_to_str


def get_proc_address(proc: T.Any) -> T.Optional[int]:
    glctx = QtOpenGL.QGLContext.currentContext()
    if glctx is None:
        return None
    addr = glctx.getProcAddress(str(proc, "utf-8"))
    return T.cast(int, addr.__int__())


class MpvWidget(QtWidgets.QOpenGLWidget):
    _schedule_update = QtCore.pyqtSignal()

    def __init__(
        self, api: Api, parent: T.Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._api = api

        locale.setlocale(locale.LC_NUMERIC, "C")

        self._destroyed = False
        self._need_subs_refresh = False
        self._mpv = mpv.Context()

        self._mpv.set_log_level("error")
        for key, value in {
            "config": False,
            "quiet": False,
            "msg-level": "all=error",
            "osc": False,
            "osd-bar": False,
            "input-cursor": False,
            "input-vo-keyboard": False,
            "input-default-bindings": False,
            "ytdl": False,
            "sub-auto": False,
            "audio-file-auto": False,
            "vo": "null" if api.args.no_video else "libmpv",
            "pause": True,
            "idle": True,
            "blend-subtitles": "video",
            "video-sync": "display-vdrop",
            "keepaspect": True,
            "stop-playback-on-init-failure": False,
            "keep-open": True,
            "track-auto-selection": False,
        }.items():
            self._mpv.set_option(key, value)

        self._mpv.observe_property("time-pos")
        self._mpv.observe_property("track-list")
        self._mpv.observe_property("pause")
        self._mpv.set_wakeup_callback(self._mpv_event_handler)
        self._mpv.initialize()

        self._opengl = None

        self._timer = QtCore.QTimer(parent=None)
        self._timer.setInterval(api.cfg.opt["video"]["subs_sync_interval"])
        self._timer.timeout.connect(self._refresh_subs_if_needed)

        api.subs.meta_changed.connect(self._on_subs_change)
        api.subs.events.item_modified.connect(self._on_subs_change)
        api.subs.events.items_inserted.connect(self._on_subs_change)
        api.subs.events.items_removed.connect(self._on_subs_change)
        api.subs.events.items_moved.connect(self._on_subs_change)
        api.subs.styles.item_modified.connect(self._on_subs_change)
        api.subs.styles.items_inserted.connect(self._on_subs_change)
        api.subs.styles.items_removed.connect(self._on_subs_change)
        api.subs.styles.items_moved.connect(self._on_subs_change)

        api.video.stream_created.connect(self._on_video_state_change)
        api.video.stream_unloaded.connect(self._on_video_state_change)
        api.video.current_stream_switched.connect(self._on_video_state_change)
        api.audio.stream_created.connect(self._on_audio_state_change)
        api.audio.stream_unloaded.connect(self._on_audio_state_change)
        api.audio.current_stream_switched.connect(self._on_audio_state_change)
        api.playback.request_seek.connect(
            self._on_request_seek, QtCore.Qt.DirectConnection
        )
        api.playback.request_playback.connect(self._on_request_playback)
        api.playback.playback_speed_changed.connect(
            self._on_playback_speed_change
        )
        api.playback.volume_changed.connect(self._on_volume_change)
        api.playback.mute_changed.connect(self._on_mute_change)
        api.playback.pause_changed.connect(self._on_pause_change)
        api.video.view.zoom_changed.connect(self._on_video_zoom_change)
        api.video.view.pan_changed.connect(self._on_video_pan_change)
        self.frameSwapped.connect(self.swapped, QtCore.Qt.DirectConnection)
        api.gui.terminated.connect(self.shutdown)
        self._schedule_update.connect(self.update)

        self._timer.start()

    def _on_video_state_change(self, stream: VideoStream) -> None:
        self._sync_media()
        self._need_subs_refresh = True

    def _on_audio_state_change(self, stream: AudioStream) -> None:
        self._sync_media()

    def _sync_media(self) -> None:
        self._mpv.set_property("pause", True)
        self._mpv.command("loadfile", "null://")
        external_files: T.Set[str] = set()
        for stream in self._api.video.streams:
            external_files.add(str(stream.path))
        for stream in self._api.audio.streams:
            external_files.add(str(stream.path))
        self._mpv.set_property("external-files", list(external_files))
        if not external_files:
            self._api.playback.state = PlaybackFrontendState.NotReady
        else:
            self._api.playback.state = PlaybackFrontendState.Loading

    def shutdown(self) -> None:
        self._destroyed = True
        self.makeCurrent()
        if self._opengl:
            self._opengl.set_update_callback(lambda: None)
            self._opengl.close()
        self.deleteLater()
        self._timer.stop()

    def initializeGL(self) -> None:
        self._opengl = mpv.RenderContext(
            self._mpv, "opengl", {"get_proc_address": get_proc_address}
        )
        self._opengl.set_update_callback(self.maybe_update)

    def paintGL(self) -> None:
        if self._opengl:
            self._opengl.render(
                {
                    "fbo": self.defaultFramebufferObject(),
                    "w": round(self.width() * self.devicePixelRatioF()),
                    "h": round(self.height() * self.devicePixelRatioF()),
                },
                flip_y=True,
            )

    @QtCore.pyqtSlot()
    def swapped(self) -> None:
        if self._opengl:
            self._opengl.report_swap()

    def maybe_update(self) -> None:
        if self._destroyed:
            return
        self._schedule_update.emit()

    def _refresh_subs_if_needed(self) -> None:
        if self._need_subs_refresh:
            self._refresh_subs()

    def _refresh_subs(self) -> None:
        if not self._api.playback.is_ready:
            return
        if self._mpv.get_property("sub"):
            try:
                self._mpv.command("sub_remove")
            except mpv.MPVError:
                pass
        with io.StringIO() as handle:
            write_ass(self._api.subs.ass_file, handle)
            self._mpv.command("sub_add", "memory://" + handle.getvalue())
        self._need_subs_refresh = False

    def _set_end(self, end: T.Optional[int]) -> None:
        if not self._api.playback.is_ready:
            return
        if end is None:
            self._mpv.set_option("end", "none")
        else:
            end = max(0, end - 1)
            self._mpv.set_option("end", ms_to_str(end))

    def _on_request_seek(self, pts: int, precise: bool) -> None:
        self._set_end(None)  # mpv refuses to seek beyond --end
        self._mpv.command(
            "seek", ms_to_str(pts), "absolute+exact" if precise else "absolute"
        )

    def _on_request_playback(
        self, start: T.Optional[int], end: T.Optional[int]
    ) -> None:
        if start is not None:
            self._mpv.command("seek", ms_to_str(start), "absolute")
        self._set_end(end)
        self._mpv.set_property("pause", False)

    def _on_playback_speed_change(self) -> None:
        self._mpv.set_property(
            "speed", float(self._api.playback.playback_speed)
        )

    def _on_volume_change(self) -> None:
        self._mpv.set_property("volume", float(self._api.playback.volume))

    def _on_mute_change(self) -> None:
        self._mpv.set_property("mute", self._api.playback.is_muted)

    def _on_pause_change(self, is_paused: bool) -> None:
        self._set_end(None)
        self._mpv.set_property("pause", is_paused)

    def _on_video_zoom_change(self) -> None:
        # ignore errors coming from setting extreme values
        try:
            self._mpv.set_property(
                "video-zoom", float(self._api.video.view.zoom)
            )
        except mpv.MPVError:
            pass

    def _on_video_pan_change(self) -> None:
        # ignore errors coming from setting extreme values
        try:
            self._mpv.set_property(
                "video-pan-x", float(self._api.video.view.pan_x)
            )
            self._mpv.set_property(
                "video-pan-y", float(self._api.video.view.pan_y)
            )
        except mpv.MPVError:
            pass

    def _on_subs_change(self) -> None:
        self._need_subs_refresh = True

    def _on_mpv_unload(self) -> None:
        self._api.playback.state = PlaybackFrontendState.NotReady

    def _on_mpv_load(self) -> None:
        self._api.playback.state = PlaybackFrontendState.Ready
        self._need_subs_refresh = True

    def _mpv_event_handler(self) -> None:
        while self._mpv:
            with self._api.log.exception_guard():
                event = self._mpv.wait_event(0.01)
                if self._handle_event(event):
                    break

    def _on_track_list_ready(self, track_list: T.Any) -> None:
        # self._api.log.debug(json.dumps(track_list, indent=4))
        vid: T.Optional[int] = None
        aid: T.Optional[int] = None

        for track in track_list:
            track_type = track["type"]
            track_path = track.get("external-filename")

            if (
                track_type == "video"
                and self._api.video.current_stream
                and self._api.video.current_stream.path.samefile(track_path)
            ):
                vid = track["id"]

            if (
                track_type == "audio"
                and self._api.audio.current_stream
                and self._api.audio.current_stream.path.samefile(track_path)
            ):
                aid = track["id"]

        if self._mpv.get_property("vid") != vid:
            self._mpv.set_property("vid", vid if vid is not None else "no")
            self._api.log.debug(f"playback: changing vid to {vid}")

        if self._mpv.get_property("aid") != aid:
            self._mpv.set_property("aid", aid if aid is not None else "no")
            self._api.log.debug(f"playback: changing aid to {aid}")

        delay = (
            self._api.audio.current_stream.delay
            if self._api.audio.current_stream
            else 0
        ) / 1000.0
        if self._mpv.get_property("audio-delay") != delay:
            self._mpv.set_property("audio-delay", delay)

        if vid is not None or aid is not None:
            self._api.playback.state = PlaybackFrontendState.Ready
        else:
            self._api.playback.state = PlaybackFrontendState.NotReady

    def _handle_event(self, event: mpv.Event) -> bool:
        if self._destroyed:
            return False

        if event.id in {mpv.Events.none, mpv.Events.shutdown}:
            return True

        if event.id == mpv.Events.end_file:
            self._on_mpv_unload()
        elif event.id == mpv.Events.file_loaded:
            self._on_mpv_load()
        elif event.id == mpv.Events.log_message:
            event_log = event.data
            self._api.log.debug(
                f"video/{event_log.prefix}: {event_log.text.strip()}"
            )
        elif event.id == mpv.Events.property_change:
            event_prop = event.data
            if event_prop.name == "time-pos":
                pts = round((event_prop.data or 0) * 1000)
                self._api.playback.receive_current_pts_change.emit(pts)
            elif event_prop.name == "pause":
                self._api.playback.pause_changed.disconnect(
                    self._on_pause_change
                )
                self._api.playback.is_paused = event_prop.data
                self._api.playback.pause_changed.connect(self._on_pause_change)
            elif event_prop.name == "track-list":
                self._on_track_list_ready(event_prop.data)
        return False
