import re
from pathlib import Path
import bubblesub.util
import pysubs2
from PyQt5 import QtCore


EMPTY_ASS = '''
[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResY: 288

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00202020,&H7F202020,-1,0,0,0,100,100,0,0,1,3,0,2,20,20,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''


def _extract_note(text):
    match = re.search('{NOTE:(?P<note>[^}]*)}', text)
    if match:
        text = text[:match.start()] + text[match.end():]
        note = bubblesub.util.unescape_ass_tag(match.group('note'))
    else:
        text = text
        note = ''
    return text, note


def _pack_note(text, note):
    text = text.replace('\n', '\\N')
    if note:
        text += '{NOTE:%s}' % (
            bubblesub.util.escape_ass_tag(note.replace('\n', '\\N')))
    return text


class Subtitle(bubblesub.util.ObservableObject):
    prop = {
        'start': bubblesub.util.ObservableObject.REQUIRED,
        'end': bubblesub.util.ObservableObject.REQUIRED,
        'style': 'Default',
        'actor': '',
        'text': '',
        'note': '',
        'effect': '',
        'layer': 0,
        'margins': (0, 0, 0),
        'is_comment': False,
    }

    def __init__(self, subtitles, **kwargs):
        super().__init__(**kwargs)
        self.ssa_event = pysubs2.SSAEvent()
        self._subtitles = subtitles
        self._sync_ssa_event()

    @property
    def duration(self):
        return self.end - self.start

    @property
    def number(self):
        for i, item in enumerate(self._subtitles):
            if item == self:
                return i
        return None

    def _before_change(self):
        num = self.number
        if num is not None:
            self._subtitles.item_about_to_change.emit(num)

    def _after_change(self):
        self._sync_ssa_event()
        num = self.number
        if num is not None:
            self._subtitles.item_changed.emit(num)

    def _sync_ssa_event(self):
        self.ssa_event.start = self.start
        self.ssa_event.end = self.end
        self.ssa_event.style = self.style
        self.ssa_event.name = self.actor
        self.ssa_event.text = _pack_note(self.text, self.note)
        self.ssa_event.effect = self.effect
        self.ssa_event.layer = self.layer
        self.ssa_event.marginl = self.margins[0]
        self.ssa_event.marginv = self.margins[1]
        self.ssa_event.marginr = self.margins[2]
        self.ssa_event.type = 'Comment' if self.is_comment else 'Dialogue'


class SubtitleList(bubblesub.util.ListModel):
    def insert_one(self, idx, **kwargs):
        self.insert(idx, [Subtitle(self, **kwargs)])


class SubtitlesApi(QtCore.QObject):
    loaded = QtCore.pyqtSignal()
    saved = QtCore.pyqtSignal()
    selection_changed = QtCore.pyqtSignal(list)

    def __init__(self, video_api):
        super().__init__()
        self._video_api = video_api
        self._loaded_video_path = None
        self._selected_lines = []
        self._ass_source = pysubs2.SSAFile.from_string(
            EMPTY_ASS, format_='ass')
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
        new_selection = list(sorted(new_selection))
        if new_selection != self._selected_lines:
            self._selected_lines = new_selection
            self.selection_changed.emit(new_selection)

    def unload(self):
        self._path = None
        self._ass_source = pysubs2.SSAFile.from_string(
            EMPTY_ASS, format_='ass')
        self.lines.remove(0, len(self.lines))
        self.selected_lines = []
        self._video_api.unload()
        self.loaded.emit()

    def load_ass(self, path):
        assert path
        try:
            ass_source = pysubs2.load(str(path))
        except Exception:
            raise

        self._path = Path(path)
        self._ass_source = ass_source

        self.selected_lines = []

        with bubblesub.util.Benchmark('loading subs'):
            collection = []
            for line in self._ass_source:
                text, note = _extract_note(line.text)
                collection.append(
                    bubblesub.api.subs.Subtitle(
                        self.lines,
                        start=line.start,
                        end=line.end,
                        style=line.style,
                        actor=line.name,
                        text=text,
                        note=note,
                        effect=line.effect,
                        layer=line.layer,
                        margins=(line.marginl, line.marginv, line.marginr),
                        is_comment=line.is_comment))

            self.lines.remove(0, len(self.lines))
            self.lines.insert(0, collection)

        self._loaded_video_path = None
        if self._ass_source and 'Video File' \
                in self._ass_source.aegisub_project:
            self._loaded_video_path = (
                self._path.parent /
                self._ass_source.aegisub_project['Video File'])
        if self._loaded_video_path:
            self._video_api.load(self._loaded_video_path)
        else:
            self._video_api.unload()

        self.loaded.emit()

    def save_ass(self, path, remember_path=False):
        with bubblesub.util.Benchmark('saving subs'):
            assert path
            path = Path(path)
            del self._ass_source[:]
            for subtitle in self.lines:
                self._ass_source.append(subtitle.ssa_event)
            if self._video_api.path != self._loaded_video_path:
                video_path = str(self._video_api.path)
                self._ass_source.aegisub_project['Video File'] = video_path
                self._ass_source.aegisub_project['Audio File'] = video_path
            if remember_path:
                self._path = path
            self._ass_source.save(path)

            if remember_path:
                self.saved.emit()
