import locale
import tempfile
import bubblesub.mpv
import bubblesub.util
from PyQt5 import QtWidgets


def mpv_log_handler(log_level, component, message):
    print('[{}] {}: {}'.format(log_level, component, message))


class Video(QtWidgets.QFrame):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self._api = api
        _, self._subs_path = tempfile.mkstemp(suffix='.ass')

        self._ready = False

        locale.setlocale(locale.LC_NUMERIC, 'C')
        self._mpv = bubblesub.mpv.MPV(
            # osd_bar=True,
            # osc=True,
            # input_cursor=True,
            # input_vo_keyboard=True,
            # input_default_bindings=True,
            keep_open=True,  # end stops the playback, whereas we want it to pause
            wid=str(int(self.winId())),
            log_handler=mpv_log_handler)
        self._mpv.pause = True
        self._api.video.is_paused = True

        @self._mpv.event_callback('file_loaded')
        def init_handler(*args):
            self._video_ready()

        # TODO: handle tick, update api.video.current_pts

        # TODO: buttons for play/pause like aegisub

        api.grid_selection_changed.connect(self._grid_selection_changed)
        api.subtitles.item_changed.connect(self._refresh_subs)
        api.video.loaded.connect(self._reload_video)
        api.video.pause_requested.connect(self._pause)
        api.video.playback_requested.connect(self._play)
        api.video.seek_requested.connect(self._seek)

    def _play(self, start, end):
        if end:
            self._mpv['end'] = bubblesub.util.ms_to_str(end)
        else:
            self._mpv['end'] = bubblesub.util.ms_to_str(self._mpv.duration * 1000)
        if start:
            self._seek(start)
        self._mpv.pause = False
        self._api.video.is_paused = False

    def _pause(self):
        self._mpv.pause = True
        self._api.video.is_paused = True

    def _seek(self, pts):
        if not self._ready:
            return
        pts = self._align_pts_to_next_frame(pts)
        self._mpv.seek(bubblesub.util.ms_to_str(pts), 'absolute+exact')

    def _reload_video(self, *args, **kwargs):
        self._api.save_ass(self._subs_path)
        if not self._api.video.path or not self._api.video.path.exists():
            self._mpv.loadfile('')
            self._ready = False
        else:
            self._mpv.loadfile(str(self._api.video.path))

    def _video_ready(self):
        self._ready = True
        self._mpv.sub_add(self._subs_path)
        self._refresh_subs()

    def _refresh_subs(self, *args, **kwargs):
        if not self._ready:
            return
        self._api.save_ass(self._subs_path)
        if self._mpv.sub:
            self._mpv.sub_reload()

    def _grid_selection_changed(self, rows):
        if len(rows) == 1:
            self._api.video.pause()
            self._api.video.seek(self._api.subtitles[rows[0]].start)

    def _align_pts_to_next_frame(self, pts):
        if self._api.video.timecodes:
            for timecode in self._api.video.timecodes:
                if timecode >= pts:
                    return timecode
        return pts
