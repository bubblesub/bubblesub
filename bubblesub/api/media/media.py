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

"""Media API. Exposes audio/video player."""

import argparse
import fractions
import io
import locale
import typing as T
from pathlib import Path

import mpv  # pylint: disable=wrong-import-order
from PyQt5 import QtCore

import bubblesub.ass.writer
import bubblesub.event
import bubblesub.util
from bubblesub.api.log import LogApi
from bubblesub.api.media.audio import AudioApi
from bubblesub.api.media.video import VideoApi
from bubblesub.api.subs import SubtitlesApi
from bubblesub.opt import Options


class MediaApi:
    """The media API."""

    loaded = bubblesub.event.EventHandler()
    parsed = bubblesub.event.EventHandler()
    current_pts_changed = bubblesub.event.EventHandler()
    max_pts_changed = bubblesub.event.EventHandler()
    volume_changed = bubblesub.event.EventHandler()
    playback_speed_changed = bubblesub.event.EventHandler()

    def __init__(
            self,
            subs_api: SubtitlesApi,
            log_api: LogApi,
            opt_api: Options,
            args: argparse.Namespace
    ) -> None:
        """
        Initialize self.

        :param subs_api: subtitles API
        :param log_api: logging API
        :param opt_api: configuration API
        :param args: CLI arguments
        """
        super().__init__()

        self._log_api = log_api
        self._subs_api = subs_api
        self._opt_api = opt_api

        self._path: T.Optional[Path] = None
        self._playback_speed = fractions.Fraction(1.0)
        self._volume = fractions.Fraction(100.0)
        self._current_pts = 0
        self._max_pts = 0
        self._mpv_ready = False
        self._need_subs_refresh = False

        self._subs_api.loaded.connect(self._on_subs_load)
        self._subs_api.info_changed.connect(self._on_subs_change)
        self._subs_api.events.item_changed.connect(self._on_subs_change)
        self._subs_api.events.items_removed.connect(self._on_subs_change)
        self._subs_api.events.items_inserted.connect(self._on_subs_change)
        self._subs_api.styles.item_changed.connect(self._on_subs_change)
        self._subs_api.styles.items_removed.connect(self._on_subs_change)
        self._subs_api.styles.items_inserted.connect(self._on_subs_change)
        self._subs_api.selection_changed.connect(
            self._on_grid_selection_change
        )

        locale.setlocale(locale.LC_NUMERIC, 'C')
        self._mpv = mpv.Context()
        self._mpv.set_log_level('error')
        for key, value in {
                'config': False,
                'quiet': False,
                'msg-level': 'all=error',
                'osc': False,
                'osd-bar': False,
                'cursor-autohide': 'no',
                'input-cursor': False,
                'input-vo-keyboard': False,
                'input-default-bindings': False,
                'ytdl': False,
                'sub-auto': False,
                'audio-file-auto': False,
                'vo': 'null' if args.no_video else 'opengl-cb',
                'pause': True,
                'idle': True,
                'sid': False,
                'video-sync': 'display-vdrop',
                'keepaspect': True,
                'hwdec': 'auto',
                'stop-playback-on-init-failure': False,
                'keep-open': True,
        }.items():
            self._mpv.set_option(key, value)

        self._mpv.observe_property('time-pos')
        self._mpv.observe_property('duration')
        self._mpv.set_wakeup_callback(self._mpv_event_handler)
        self._mpv.initialize()

        self.video = VideoApi(self, log_api, self._mpv)
        self.audio = AudioApi(self, log_api)

        self._timer = QtCore.QTimer(parent=None)
        self._timer.setInterval(opt_api.general.video.subs_sync_interval)
        self._timer.timeout.connect(self._refresh_subs_if_needed)

    def start(self) -> None:
        """Start internal worker threads."""
        self.audio.start()
        self.video.start()
        self._timer.start()

    def stop(self) -> None:
        """Stop internal worker threads."""
        self.audio.stop()
        self.video.stop()
        self._timer.stop()

    def unload(self) -> None:
        """Unload currently loaded video."""
        self._playback_speed = fractions.Fraction(1.0)
        self._volume = fractions.Fraction(100.0)
        self._current_pts = 0
        self._max_pts = 0
        self._path = None
        self.loaded.emit()
        self._reload_video()

    def load(self, path: T.Union[str, Path]) -> None:
        """
        Load video.

        :param path: path where to load the video from
        """
        assert path is not None
        self._path = Path(path)
        if str(self._subs_api.remembered_video_path) != str(self._path):
            self._subs_api.remembered_video_path = self._path
        self._reload_video()
        self.loaded.emit()

    def seek(self, pts: int, precise: bool = True) -> None:
        """
        Seek to specified position in the video.

        :param pts: PTS to seek to
        :param precise: whether to be preciser at the expense of performance
        """
        if not self._mpv_ready:
            return
        self._set_end(None)  # mpv refuses to seek beyond --end
        pts = max(0, pts)
        pts = self.video.align_pts_to_next_frame(pts)
        if pts != self.current_pts:
            self._mpv.command(
                'seek',
                bubblesub.util.ms_to_str(pts),
                'absolute+exact' if precise else 'absolute'
            )

    def step_frame_forward(self) -> None:
        """Step one frame forward."""
        if not self._mpv_ready:
            return
        self._set_end(None)  # mpv refuses to seek beyond --end
        self._mpv.command('frame-step')

    def step_frame_backward(self) -> None:
        """Step one frame back."""
        if not self._mpv_ready:
            return
        self._set_end(None)  # mpv refuses to seek beyond --end
        self._mpv.command('frame-back-step')

    def play(self, start: int, end: int) -> None:
        """
        Play the currently loaded video at specified PTS range.

        :param start: start PTS
        :param end: end PTS
        """
        self._play(start, end)

    def unpause(self) -> None:
        """Unpause the currently loaded video."""
        self._play(None, None)

    def pause(self) -> None:
        """Pause the currently loaded video."""
        self._mpv.set_property('pause', True)

    @property
    def playback_speed(self) -> fractions.Fraction:
        """
        Return playback rate for the currently loaded video.

        :return: playback rate for the currently loaded video, 1.0 if no video
        """
        return self._playback_speed

    @playback_speed.setter
    def playback_speed(self, value: fractions.Fraction) -> None:
        """
        Set new playback rate for the currently loaded video.

        :param value: new playback rate
        """
        self._playback_speed = value
        self._mpv.set_property('speed', float(self._playback_speed))
        self.playback_speed_changed.emit()

    @property
    def volume(self) -> fractions.Fraction:
        """
        Return volume for the currently loaded video.

        :return: volume for the currently loaded video, 100.0 if no video
        """
        return self._volume

    @volume.setter
    def volume(self, value: fractions.Fraction) -> None:
        """
        Set new volume for the currently loaded video.

        :param value: new volume
        """
        self._volume = value
        self._mpv.set_property('volume', float(self._volume))
        self.volume_changed.emit()

    @property
    def current_pts(self) -> int:
        """
        Return current video position.

        :return: current video position, 0 if no video
        """
        return self._current_pts

    @property
    def max_pts(self) -> int:
        """
        Return maximum video position.

        :return: maximum video position, 0 if no video
        """
        return self._max_pts

    @property
    def is_paused(self) -> bool:
        """
        Return whether the currently loaded video is paused.

        :return: whether the currently loaded video is paused, True if no video
        """
        if not self._mpv_ready:
            return True
        return bool(self._mpv.get_property('pause'))

    @property
    def path(self) -> T.Optional[Path]:
        """
        Return path to the currently loaded video.

        :return: path to the currently loaded video, None if no video
        """
        return self._path

    @property
    def is_loaded(self) -> bool:
        """
        Return whether there's video loaded.

        :return: whether there's video loaded
        """
        return self._path is not None

    def _play(self, start: T.Optional[int], end: T.Optional[int]) -> None:
        if not self._mpv_ready:
            return
        if start is not None:
            self.seek(start)
        self._set_end(end)
        self._mpv.set_property('pause', False)

    def _set_end(self, end: T.Optional[int]) -> None:
        if end is None:
            # XXX: mpv doesn't accept None nor "" so we use max pts
            end = self._mpv.get_property('duration') * 1000
        assert end is not None
        end = max(0, end)
        self._mpv.set_option('end', bubblesub.util.ms_to_str(end))

    def _mpv_unloaded(self) -> None:
        self._mpv_ready = False
        self.parsed.emit()

    def _mpv_loaded(self) -> None:
        self._mpv_ready = True
        self._refresh_subs()
        self.parsed.emit()

    def _on_subs_load(self) -> None:
        if self._subs_api.remembered_video_path:
            self.load(self._subs_api.remembered_video_path)
        else:
            self.unload()
        self._on_subs_change()

    def _on_subs_change(self) -> None:
        self._need_subs_refresh = True

    def _reload_video(self) -> None:
        self._mpv_ready = False
        self._mpv.set_property('pause', True)
        if not self.path or not self.path.exists():
            self._mpv.command('loadfile', '')
        else:
            self._mpv.command('loadfile', str(self.path))

    def _refresh_subs_if_needed(self) -> None:
        if self._need_subs_refresh:
            self._refresh_subs()

    def _refresh_subs(self) -> None:
        if not self._mpv_ready:
            return
        if self._mpv.get_property('sub'):
            self._mpv.command('sub_remove')
        with io.StringIO() as handle:
            bubblesub.ass.writer.write_ass(self._subs_api.ass_file, handle)
            self._mpv.command('sub_add', 'memory://' + handle.getvalue())
        self._need_subs_refresh = False

    def _on_grid_selection_change(
            self,
            rows: T.List[int],
            _changed: bool
    ) -> None:
        if len(rows) == 1:
            self.pause()
            self.seek(self._subs_api.events[rows[0]].start)

    def _mpv_event_handler(self) -> None:
        while self._mpv:
            event = self._mpv.wait_event(.01)
            if event.id in {mpv.Events.none, mpv.Events.shutdown}:
                break
            elif event.id == mpv.Events.end_file:
                self._mpv_unloaded()
            elif event.id == mpv.Events.file_loaded:
                self._mpv_loaded()
            elif event.id == mpv.Events.log_message:
                event_log = event.data
                self._log_api.debug(
                    f'video/{event_log.prefix}: {event_log.text.strip()}'
                )
            elif event.id == mpv.Events.property_change:
                event_prop = event.data
                if event_prop.name == 'time-pos':
                    self._current_pts = event_prop.data * 1000
                    self.current_pts_changed.emit()
                elif event_prop.name == 'duration':
                    self._max_pts = event_prop.data * 1000
                    self.max_pts_changed.emit()
