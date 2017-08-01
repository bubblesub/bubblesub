import os
import locale
import atexit
import tempfile
from pathlib import Path
import ffms
import bubblesub.mpv
import bubblesub.util
from PyQt5 import QtCore


class TimecodesProviderContext(bubblesub.util.ProviderContext):
    def __init__(self, log_api):
        super().__init__()
        self._log_api = log_api

    def work(self, task):
        path = task
        self._log_api.info('video/timecodes: loading... ({})'.format(path))
        cache_key = str(path)
        timecodes = bubblesub.util.load_cache('index', cache_key)
        if not timecodes:
            video = ffms.VideoSource(str(path))
            timecodes = video.track.timecodes
            bubblesub.util.save_cache('index', cache_key, timecodes)
        self._log_api.info('video/timecodes: loaded')
        return path, timecodes


class TimecodesProvider(bubblesub.util.Provider):
    def __init__(self, parent, log_api):
        super().__init__(parent, TimecodesProviderContext(log_api))


class VideoApi(QtCore.QObject):
    loaded = QtCore.pyqtSignal()
    timecodes_updated = QtCore.pyqtSignal()
    current_pts_changed = QtCore.pyqtSignal()

    def __init__(self, subs_api, log_api, opt_api):
        super().__init__()
        self._log_api = log_api
        self._subs_api = subs_api
        self._opt_api = opt_api

        _, self._tmp_subs_path = tempfile.mkstemp(suffix='.ass')
        atexit.register(lambda: os.unlink(self._tmp_subs_path))

        self._timecodes = []
        self._path = None
        self._current_pts = None
        self._mpv = None
        self._mpv_ready = False
        self._need_subs_refresh = False

        self._timecodes_provider = TimecodesProvider(self, log_api)
        self._timecodes_provider.finished.connect(self._got_timecodes)

        self._subs_api.loaded.connect(self._subs_loaded)
        self._subs_api.selection_changed.connect(self._grid_selection_changed)
        self._subs_api.lines.item_changed.connect(self._subs_changed)
        self._subs_api.lines.items_removed.connect(self._subs_changed)
        self._subs_api.lines.items_inserted.connect(self._subs_changed)

    def unload(self):
        self._path = None
        self._timecodes = []
        self.timecodes_updated.emit()
        self.loaded.emit()
        self._reload_video()

    def load(self, path):
        assert path
        self._path = Path(path)
        if str(self._subs_api.remembered_video_path) != str(self._path):
            self._subs_api.remembered_video_path = self._path
        self._timecodes = []
        self.timecodes_updated.emit()
        self._timecodes_provider.schedule(self._path)
        self._reload_video()
        self.loaded.emit()

    def connect_presenter(self, window_id):
        if self._mpv:
            raise RuntimeError('Already connected!')
        locale.setlocale(locale.LC_NUMERIC, 'C')

        def _mpv_log_handler(log_level, component, message):
            self._log_api.info(
                'video/{}[{}]: {}'.format(component, log_level, message))

        self._mpv = bubblesub.mpv.MPV(
            osd_bar=False,
            osc=False,
            cursor_autohide='no',
            input_cursor=False,
            input_vo_keyboard=False,
            input_default_bindings=False,
            wid=str(window_id),
            keep_open=True,  # without this reaching mpv['end'] borks playback
            log_handler=_mpv_log_handler)

        @self._mpv.event_callback('file_loaded')
        def _init_handler(*_):
            self._mpv_loaded()

        @self._mpv.property_observer('time-pos')
        def _time_pos_handler(_prop_name, time_pos):
            self.current_pts = time_pos * 1000

        timer = QtCore.QTimer(
            self,
            interval=self._opt_api.general['video']['subs_sync_interval'])
        timer.timeout.connect(self._refresh_subs_if_needed)
        timer.start()

    def seek(self, pts):
        if not self._mpv_ready:
            return
        self._set_end(None)  # mpv refuses to seek beyond --end
        pts = self._align_pts_to_next_frame(pts)
        self._mpv.seek(bubblesub.util.ms_to_str(pts), 'absolute+exact')

    def play(self, start, end):
        self._play(start, end)

    def unpause(self):
        self._play(None, None)

    def pause(self):
        self._mpv.pause = True

    @property
    def playback_speed(self):
        return self._mpv.speed

    @playback_speed.setter
    def playback_speed(self, speed):
        self._mpv.speed = speed

    @property
    def current_pts(self):
        return self._current_pts

    @current_pts.setter
    def current_pts(self, new_pts):
        self._current_pts = new_pts
        self.current_pts_changed.emit()

    @property
    def max_pts(self):
        if not self._mpv:
            return 0
        return self._mpv.duration * 1000

    @property
    def is_paused(self):
        if not self._mpv_ready:
            return True
        return self._mpv.pause

    @property
    def path(self):
        return self._path

    @property
    def timecodes(self):
        return self._timecodes

    def _got_timecodes(self, result):
        path, timecodes = result
        if path == self.path:
            self._timecodes = timecodes
            self.timecodes_updated.emit()

    def _play(self, start, end):
        if not self._mpv_ready:
            return
        if start:
            self.seek(start)
        self._set_end(end)
        self._mpv.pause = False

    def _set_end(self, end):
        if not end:
            # XXX: mpv doesn't accept None nor "" so we use max pts
            end = self._mpv.duration * 1000
        self._mpv['end'] = bubblesub.util.ms_to_str(end)

    def _mpv_loaded(self):
        self._mpv_ready = True
        self._mpv.sub_add(self._tmp_subs_path)
        self._refresh_subs()

    def _subs_loaded(self):
        if self._subs_api.remembered_video_path:
            self.load(self._subs_api.remembered_video_path)
        else:
            self.unload()
        self._subs_changed()

    def _subs_changed(self):
        self._need_subs_refresh = True

    def _reload_video(self):
        self._subs_api.save_ass(self._tmp_subs_path)
        if not self.path or not self.path.exists():
            self._mpv.loadfile('')
            self._mpv_ready = False
        else:
            self._mpv.loadfile(str(self.path))

    def _refresh_subs_if_needed(self):
        if self._need_subs_refresh:
            self._refresh_subs()

    def _refresh_subs(self):
        if not self._mpv_ready:
            return
        self._subs_api.save_ass(self._tmp_subs_path)
        if self._mpv.sub:
            self._mpv.sub_reload()
            self._need_subs_refresh = False

    def _grid_selection_changed(self, rows):
        if len(rows) == 1:
            self.pause()
            self.seek(self._subs_api.lines[rows[0]].start)

    def _align_pts_to_next_frame(self, pts):
        if self.timecodes:
            for timecode in self.timecodes:
                if timecode >= pts:
                    return timecode
        return pts
