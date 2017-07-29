import locale
import tempfile
import bubblesub.mpv
import bubblesub.util
from PyQt5 import QtCore
from PyQt5 import QtWidgets


def mpv_log_handler(log_level, component, message):
    print('[{}] {}: {}'.format(log_level, component, message))


class Video(QtWidgets.QFrame):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self._api = api
        _, self._subs_path = tempfile.mkstemp(suffix='.ass')

        self._need_subs_refresh = False
        self._mpv_ready = False

        locale.setlocale(locale.LC_NUMERIC, 'C')
        self._mpv = bubblesub.mpv.MPV(
            osd_bar=False,
            osc=False,
            input_cursor=False,
            input_vo_keyboard=False,
            input_default_bindings=False,
            keep_open=True,  # without this reaching mpv['end'] borks playback
            wid=str(int(self.winId())),
            log_handler=mpv_log_handler)
        self._mpv.pause = True
        self._api.video.is_paused = True

        @self._mpv.event_callback('file_loaded')
        def init_handler(*args):
            self._video_ready()

        @self._mpv.event_callback('pause')
        def pause_handler(*args):
            self._api.video.is_paused = True

        def time_pos_handler(prop_name, time_pos):
            self._api.video.current_pts = time_pos * 1000

        self._mpv.observe_property('time-pos', time_pos_handler)

        # TODO: buttons for play/pause like aegisub

        api.subs.selection_changed.connect(self._grid_selection_changed)
        api.subs.loaded.connect(self._subs_changed)
        api.subs.lines.item_changed.connect(self._subs_changed)
        api.subs.lines.items_removed.connect(self._subs_changed)
        api.subs.lines.items_inserted.connect(self._subs_changed)
        api.video.loaded.connect(self._reload_video)
        api.video.pause_requested.connect(self._pause)
        api.video.playback_requested.connect(self._play)
        api.video.seek_requested.connect(self._seek)

        timer = QtCore.QTimer(
            self,
            interval=api.opt.general['video']['subs_sync_interval'])
        timer.timeout.connect(self._refresh_subs_if_needed)
        timer.start()

    def _subs_changed(self):
        self._need_subs_refresh = True

    def _play(self, start, end):
        if start:
            self._seek(start)
        self._set_end(end)
        self._mpv.pause = False
        self._api.video.is_paused = False

    def _pause(self):
        self._mpv.pause = True
        self._api.video.is_paused = True

    def _seek(self, pts):
        if not self._mpv_ready:
            return
        self._set_end(None)  # mpv refuses to seek beyond --end
        pts = self._align_pts_to_next_frame(pts)
        self._mpv.seek(bubblesub.util.ms_to_str(pts), 'absolute+exact')

    def _reload_video(self, *args, **kwargs):
        self._api.subs.save_ass(self._subs_path)
        if not self._api.video.path or not self._api.video.path.exists():
            self._mpv.loadfile('')
            self._mpv_ready = False
        else:
            self._mpv.loadfile(str(self._api.video.path))

    def _video_ready(self):
        self._mpv_ready = True
        self._mpv.sub_add(self._subs_path)
        self._refresh_subs()

    def _refresh_subs_if_needed(self):
        if self._need_subs_refresh:
            self._refresh_subs()

    def _refresh_subs(self, *args, **kwargs):
        if not self._mpv_ready:
            return
        self._api.subs.save_ass(self._subs_path)
        if self._mpv.sub:
            self._mpv.sub_reload()
            self._need_subs_refresh = False

    def _set_end(self, end):
        if not end:
            # XXX: mpv doesn't accept None nor "" so we use max pts
            end = self._mpv.duration * 1000
        self._mpv['end'] = bubblesub.util.ms_to_str(end)

    def _grid_selection_changed(self, rows):
        if len(rows) == 1:
            self._api.video.pause()
            self._api.video.seek(self._api.subs.lines[rows[0]].start)

    def _align_pts_to_next_frame(self, pts):
        if self._api.video.timecodes:
            for timecode in self._api.video.timecodes:
                if timecode >= pts:
                    return timecode
        return pts
