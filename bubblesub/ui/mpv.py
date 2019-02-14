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

import io
import locale
import typing as T

import mpv  # pylint: disable=wrong-import-order
from PyQt5 import QtCore, QtOpenGL, QtWidgets

from bubblesub.api import Api
from bubblesub.api.audio import AudioState
from bubblesub.api.playback import PlaybackFrontendState
from bubblesub.api.video import VideoState
from bubblesub.ass.writer import write_ass
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

        self._opengl = self._mpv.opengl_cb_api()
        self._opengl.set_update_callback(self.maybe_update)

        self._timer = QtCore.QTimer(parent=None)
        self._timer.setInterval(api.cfg.opt["video"]["subs_sync_interval"])
        self._timer.timeout.connect(self._refresh_subs_if_needed)

        api.subs.meta_changed.connect(self._on_subs_change)
        api.subs.events.item_changed.connect(self._on_subs_change)
        api.subs.events.items_inserted.connect(self._on_subs_change)
        api.subs.events.items_removed.connect(self._on_subs_change)
        api.subs.events.items_moved.connect(self._on_subs_change)
        api.subs.styles.item_changed.connect(self._on_subs_change)
        api.subs.styles.items_inserted.connect(self._on_subs_change)
        api.subs.styles.items_removed.connect(self._on_subs_change)
        api.subs.styles.items_moved.connect(self._on_subs_change)

        api.video.state_changed.connect(self._on_video_state_change)
        api.audio.state_changed.connect(self._on_audio_state_change)
        api.playback.request_seek.connect(self._on_request_seek)
        api.playback.request_playback.connect(self._on_request_playback)
        api.playback.playback_speed_changed.connect(
            self._on_playback_speed_change
        )
        api.playback.volume_changed.connect(self._on_volume_change)
        api.playback.mute_changed.connect(self._on_mute_change)
        api.playback.pause_changed.connect(self._on_pause_change)
        self.frameSwapped.connect(self.swapped, QtCore.Qt.DirectConnection)
        self._schedule_update.connect(self.update)

        self._timer.start()

    def _on_video_state_change(self, state: VideoState) -> None:
        if state == VideoState.NotLoaded:
            self._sync_media()
        elif state == VideoState.Loading:
            self._sync_media()
        self._need_subs_refresh = True

    def _on_audio_state_change(self, state: AudioState) -> None:
        if state == AudioState.NotLoaded:
            self._sync_media()
        elif state == AudioState.Loading:
            self._sync_media()

    def _sync_media(self) -> None:
        self._mpv.set_property("pause", True)
        self._mpv.command("loadfile", "null://")
        external_files: T.Set[str] = set()
        if self._api.video.path:
            external_files.add(str(self._api.video.path))
        if self._api.audio.path:
            external_files.add(str(self._api.audio.path))
        self._mpv.set_property("external-files", list(external_files))
        if not external_files:
            self._api.playback.state = PlaybackFrontendState.NotReady
        else:
            self._api.playback.state = PlaybackFrontendState.Loading

    def shutdown(self) -> None:
        self.makeCurrent()
        if self._opengl:
            self._opengl.set_update_callback(lambda: None)
            self._opengl.uninit_gl()
        self.deleteLater()
        self._timer.stop()

    def initializeGL(self) -> None:
        if self._opengl:
            self._opengl.init_gl(None, get_proc_address)

    def paintGL(self) -> None:
        if self._opengl:
            self._opengl.draw(
                self.defaultFramebufferObject(),
                round(self.width() * self.devicePixelRatioF()),
                round(-self.height() * self.devicePixelRatioF()),
            )

    @QtCore.pyqtSlot()
    def swapped(self) -> None:
        if self._opengl:
            self._opengl.report_flip(0)

    def maybe_update(self) -> None:
        self._schedule_update.emit()

    def _refresh_subs_if_needed(self) -> None:
        if self._need_subs_refresh:
            self._refresh_subs()

    def _refresh_subs(self) -> None:
        if not self._api.playback.is_ready:
            return
        if self._mpv.get_property("sub"):
            self._mpv.command("sub_remove")
        with io.StringIO() as handle:
            write_ass(self._api.subs.ass_file, handle)
            self._mpv.command("sub_add", "memory://" + handle.getvalue())
        self._need_subs_refresh = False

    def _set_end(self, end: T.Optional[int]) -> None:
        if not self._api.playback.is_ready:
            return
        if end is None:
            # XXX: mpv doesn't accept None nor "" so we use max pts
            end = self._api.playback.max_pts
        else:
            end -= 1
        assert end is not None
        end = max(0, end)
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

    def _on_pause_change(self) -> None:
        self._set_end(None)
        self._mpv.set_property("pause", self._api.playback.is_paused)

    def _on_subs_change(self) -> None:
        self._need_subs_refresh = True

    def _on_mpv_unload(self) -> None:
        self._api.playback.state = PlaybackFrontendState.NotReady

    def _on_mpv_load(self) -> None:
        self._api.playback.state = PlaybackFrontendState.Ready
        self._refresh_subs()

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
                and self._api.video.path
                and self._api.video.path.samefile(track_path)
            ):
                vid = track["id"]

            if (
                track_type == "audio"
                and self._api.audio.path
                and self._api.audio.path.samefile(track_path)
            ):
                aid = track["id"]

        if self._mpv.get_property("vid") != vid:
            self._mpv.set_property("vid", vid if vid is not None else "no")
            self._api.log.debug(f"playback: changing vid to {vid}")

        if self._mpv.get_property("aid") != aid:
            self._mpv.set_property("aid", aid if aid is not None else "no")
            self._api.log.debug(f"playback: changing aid to {aid}")

        if vid is not None or aid is not None:
            self._api.playback.state = PlaybackFrontendState.Ready
        else:
            self._api.playback.state = PlaybackFrontendState.NotReady

    def _handle_event(self, event: mpv.Event) -> bool:
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
