import bubblesub.util
import ffms
import pysubs2
import numpy as np
from pathlib import Path
from PyQt5 import QtCore


# TODO: do this somewhere else asynchronously
def _get_timecodes(video_path):
    cache_key = str(video_path)
    timecodes = bubblesub.util.load_cache('index', cache_key)
    if not timecodes:
        print('Reading video time codes, please wait.')
        video = ffms.VideoSource(str(video_path))
        timecodes = video.track.timecodes
        bubblesub.util.save_cache('index', cache_key, timecodes)
    return timecodes


class Subtitle(bubblesub.util.ObservableObject):
    start = bubblesub.util.ObservableProperty('start')
    end = bubblesub.util.ObservableProperty('end')
    style = bubblesub.util.ObservableProperty('style')
    actor = bubblesub.util.ObservableProperty('actor')
    text = bubblesub.util.ObservableProperty('text')

    def __init__(self, subtitles, start, end, style, actor='', text=''):
        super().__init__()
        self._subtitles = subtitles
        self.begin_update()
        self.start = start
        self.end = end
        self.style = style
        self.actor = actor
        self.text = text
        self.end_update()

    @property
    def duration(self):
        return self.end - self.start

    @property
    def number(self):
        for i, item in enumerate(self._subtitles):
            if item == self:
                return i
        return None

    def _changed(self):
        self._subtitles.item_changed.emit(self.number)


class SubtitleList(bubblesub.util.ListModel):
    def insert_one(self, idx, **kwargs):
        self.insert(idx, [Subtitle(self, **kwargs)])


class GuiApi(QtCore.QObject):
    quit_requested = QtCore.pyqtSignal([])

    def quit(self):
        self.quit_requested.emit()


class AudioApi(QtCore.QObject):
    view_changed = QtCore.pyqtSignal([])
    selection_changed = QtCore.pyqtSignal([])

    def __init__(self, api):
        super().__init__()
        self._min = 0
        self._max = 0
        self._view_start = 0
        self._view_end = 0
        self._selection_start = None
        self._selection_size = None
        self._api = api

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    @property
    def size(self):
        return self._max - self._min

    @property
    def view_start(self):
        return self._view_start

    @property
    def view_end(self):
        return self._view_end

    @property
    def view_size(self):
        return self._view_end - self._view_start

    @property
    def selection_start(self):
        return self._selection_start

    @property
    def selection_end(self):
        return self._selection_end

    @property
    def selection_size(self):
        if self._selection_start is None or self._selection_end is None:
            return 0
        return self._selection_end - self._selection_start

    def unselect(self):
        self._selection_start = None
        self._selection_end = None
        self.selection_changed.emit()

    def select(self, start_pts, end_pts):
        self._selection_start = self._clip(start_pts)
        self._selection_end = self._clip(end_pts)
        self.selection_changed.emit()

    def view(self, start_pts, end_pts):
        self._view_start = self._clip(start_pts)
        self._view_end = self._clip(end_pts)
        self.view_changed.emit()

    def zoom(self, factor):
        factor = max(0.001, min(1, factor))
        old_origin = self.view_start - self._min
        old_view_size = self.view_size / 2
        self._view_start = self.min
        self._view_end = self._clip(self.min + self.size * factor)
        new_view_size = self.view_size / 2
        distance = old_origin - new_view_size + old_view_size
        self.move(distance)  # emits view_changed

    def move(self, distance):
        view_size = self.view_size
        if self._view_start + distance < self.min:
            self.view(self.min, self.min + view_size)
        elif self._view_end + distance > self.max:
            self.view(self.max - view_size, self.max)
        else:
            self.view(self._view_start + distance, self._view_end + distance)

    def _set_max_pts(self, max_pts):
        self._min = 0
        self._max = max_pts
        self.zoom(1)  # emits selection changed

    def _clip(self, value):
        return max(min(self._max, value), self._min)


class VideoApi(QtCore.QObject):
    loaded = QtCore.pyqtSignal([])
    seek_requested = QtCore.pyqtSignal([int])
    playback_requested = QtCore.pyqtSignal([object, object])
    pause_requested = QtCore.pyqtSignal([])

    def __init__(self):
        super().__init__()
        self._timecodes = []
        self._path = None
        self._is_paused = False
        self._current_pts = None

    def seek(self, pts):
        self.seek_requested.emit(pts)

    def play(self, start, end):
        self.playback_requested.emit(start, end)

    def unpause(self):
        self.playback_requested.emit(None, None)

    def pause(self):
        self.pause_requested.emit()

    @property
    def current_pts(self):
        return self._current_pts

    @current_pts.setter
    def current_pts(self, new_pts):
        self._current_pts = new_pts

    @property
    def is_paused(self):
        return self._is_paused

    @is_paused.setter
    def is_paused(self, paused):
        self._is_paused = paused

    @property
    def path(self):
        return self._path

    @property
    def timecodes(self):
        return self._timecodes


class Api(QtCore.QObject):
    ass_loaded = QtCore.pyqtSignal([])
    grid_selection_changed = QtCore.pyqtSignal([list])

    def __init__(self):
        super().__init__()
        self._ass_source = None
        self._ass_path = None
        self._selected_lines = []
        self.subtitles = SubtitleList()
        self.video = VideoApi()
        self.audio = AudioApi(self)
        self.gui = GuiApi()

    @property
    def ass_path(self):
        return self._ass_path

    def load_ass(self, ass_path):
        self._ass_path = Path(ass_path)
        self._ass_source = pysubs2.load(str(self._ass_path))

        self.selected_lines = []

        with bubblesub.util.Benchmark('loading subs') as b:
            self.subtitles.remove(0, len(self.subtitles))
            self.subtitles.insert(
                0,
                [
                    Subtitle(
                        self.subtitles,
                        line.start,
                        line.end,
                        line.style,
                        line.name,
                        line.text)
                    for line in self._ass_source
                    if line.start and line.end
                ])

        if not self._ass_source \
                or 'Video File' not in self._ass_source.aegisub_project:
            self.load_video(None)
        else:
            self.load_video(
                self._ass_path.parent /
                self._ass_source.aegisub_project['Video File'])

        self.ass_loaded.emit()

    def load_video(self, video_path, update=False):
        self.video._path = video_path

        if video_path and video_path.exists():
            # TODO: refactor this
            timecodes = _get_timecodes(video_path)
            self.video._timecodes = timecodes
            self.audio._set_max_pts(timecodes[-1])
        else:
            self.video._timecodes = []
            self.audio._set_max_pts(0)

        if update:
            self._ass_source.aegisub_project['Video File'] = str(video_path)
            self._ass_source.aegisub_project['Audio File'] = str(video_path)

        self.video.loaded.emit()

    @property
    def selected_lines(self):
        return self._selected_lines

    @selected_lines.setter
    def selected_lines(self, new_selection):
        if new_selection != self._selected_lines:
            self._selected_lines = new_selection
            self.grid_selection_changed.emit(new_selection)

    def save_ass(self, path):
        if not self._ass_source:
            raise RuntimeError('Subtitles not loaded')
        del self._ass_source[:]
        for subtitle in self.subtitles:
            self._ass_source.append(pysubs2.SSAEvent(
                start=subtitle.start,
                end=subtitle.end,
                style=subtitle.style,
                name=subtitle.actor,
                text=subtitle.text))
        self._ass_source.save(path)

    def log(self, text):
        print(text)  # TODO: log to GUI console via events
