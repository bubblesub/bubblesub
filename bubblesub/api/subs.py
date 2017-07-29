from pathlib import Path
import bubblesub.util
import pysubs2
from PyQt5 import QtCore


class Subtitle(bubblesub.util.ObservableObject):
    start = bubblesub.util.ObservableProperty('start')
    end = bubblesub.util.ObservableProperty('end')
    style = bubblesub.util.ObservableProperty('style')
    actor = bubblesub.util.ObservableProperty('actor')
    text = bubblesub.util.ObservableProperty('text')
    effect = bubblesub.util.ObservableProperty('effect')
    layer = bubblesub.util.ObservableProperty('layer')
    margins = bubblesub.util.ObservableProperty('margins')
    is_comment = bubblesub.util.ObservableProperty('is_comment')

    def __init__(
            self, subtitles,
            start, end, style='Default', actor='', text='',
            layer=0, effect='', margins=(0, 0, 0), is_comment=False):
        super().__init__()
        self._subtitles = subtitles
        self.begin_update()
        self.start = start
        self.end = end
        self.style = style
        self.actor = actor
        self.text = text
        self.layer = layer
        self.effect = effect
        self.margins = margins
        self.is_comment = is_comment
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
        if self.number is not None:
            self._subtitles.item_changed.emit(self.number)


class SubtitleList(bubblesub.util.ListModel):
    def insert_one(self, idx, **kwargs):
        self.insert(idx, [Subtitle(self, **kwargs)])


class SubtitlesApi(QtCore.QObject):
    loaded = QtCore.pyqtSignal([])
    selection_changed = QtCore.pyqtSignal([list])

    def __init__(self, video_api):
        super().__init__()
        self._video_api = video_api
        self._loaded_video_path = None
        self._selected_lines = []
        self._ass_source = None
        self._path = None
        self.lines = bubblesub.api.subs.SubtitleList()

    @property
    def path(self):
        return self._path

    @property
    def has_selection(self):
        return len(self.selected_lines) > 0

    @property
    def selected_lines(self):
        return self._selected_lines

    @selected_lines.setter
    def selected_lines(self, new_selection):
        if new_selection != self._selected_lines:
            self._selected_lines = new_selection
            self.selection_changed.emit(new_selection)

    def load_ass(self, path):
        self._path = Path(path)
        self._ass_source = pysubs2.load(str(self._path))

        self.selected_lines = []

        with bubblesub.util.Benchmark('loading subs'):
            self.lines.remove(0, len(self.lines))
            self.lines.insert(
                0,
                [
                    bubblesub.api.subs.Subtitle(
                        self.lines,
                        start=line.start,
                        end=line.end,
                        style=line.style,
                        actor=line.name,
                        text=line.text,
                        effect=line.effect,
                        layer=line.layer,
                        margins=(line.marginl, line.marginv, line.marginr),
                        is_comment=line.is_comment)
                    for line in self._ass_source
                    if line.start and line.end
                ])

        self._loaded_video_path = None
        if self._ass_source and 'Video File' \
                in self._ass_source.aegisub_project:
            self._loaded_video_path = (
                self._path.parent /
                self._ass_source.aegisub_project['Video File'])
        self._video_api.load(self._loaded_video_path)

        self.loaded.emit()

    def save_ass(self, path):
        if not self._ass_source:
            raise RuntimeError('Subtitles not loaded')
        del self._ass_source[:]
        for subtitle in self.lines:
            self._ass_source.append(pysubs2.SSAEvent(
                start=subtitle.start,
                end=subtitle.end,
                style=subtitle.style,
                name=subtitle.actor,
                text=subtitle.text,
                effect=subtitle.effect,
                layer=subtitle.layer,
                marginl=subtitle.margins[0],
                marginv=subtitle.margins[1],
                marginr=subtitle.margins[2],
                type='Comment' if subtitle.is_comment else 'Dialogue'))
        if self._video_api.path != self._loaded_video_path:
            video_path = str(self._video_api.path)
            self._ass_source.aegisub_project['Video File'] = video_path
            self._ass_source.aegisub_project['Audio File'] = video_path
        self._ass_source.save(path)
