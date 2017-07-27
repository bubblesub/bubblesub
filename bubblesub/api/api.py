from pathlib import Path
import ffms
import pysubs2
import bubblesub.util
import bubblesub.api.gui
import bubblesub.api.audio
import bubblesub.api.video
import bubblesub.api.subs
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


class Api(QtCore.QObject):
    ass_loaded = QtCore.pyqtSignal([])
    grid_selection_changed = QtCore.pyqtSignal([list])

    def __init__(self):
        super().__init__()
        self._ass_source = None
        self._ass_path = None
        self._selected_lines = []
        self.subtitles = bubblesub.api.subs.SubtitleList()
        self.video = bubblesub.api.video.VideoApi()
        self.audio = bubblesub.api.audio.AudioApi(self)
        self.gui = bubblesub.api.gui.GuiApi()

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
                    bubblesub.api.subs.Subtitle(
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
