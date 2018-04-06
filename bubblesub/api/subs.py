from pathlib import Path

from PyQt5 import QtCore

import bubblesub.ass.file
import bubblesub.model
import bubblesub.util


class SubtitlesApi(QtCore.QObject):
    loaded = QtCore.pyqtSignal()
    saved = QtCore.pyqtSignal()
    selection_changed = QtCore.pyqtSignal(list, bool)

    def __init__(self):
        super().__init__()
        self._loaded_video_path = None
        self._selected_indexes = []
        self._path = None
        self.ass_file = bubblesub.ass.file.AssFile()
        self.lines.items_about_to_be_removed.connect(
            self._on_items_about_to_be_removed)

    @property
    def lines(self):
        return self.ass_file.events

    @property
    def styles(self):
        return self.ass_file.styles

    @property
    def info(self):
        return self.ass_file.info

    @property
    def meta(self):
        return self.ass_file.meta

    @property
    def remembered_video_path(self):
        path = self.meta.get('Video File', None)
        if not path:
            return None
        if not self._path:
            return None
        return self._path.parent / path

    @remembered_video_path.setter
    def remembered_video_path(self, path):
        self.meta['Video File'] = str(path)
        self.meta['Audio File'] = str(path)

    @property
    def path(self):
        return self._path

    @property
    def has_selection(self):
        return len(self.selected_indexes) > 0

    @property
    def selected_indexes(self):
        return self._selected_indexes

    @property
    def selected_lines(self):
        return [self.lines[idx] for idx in self.selected_indexes]

    @selected_indexes.setter
    def selected_indexes(self, new_selection):
        new_selection = list(sorted(new_selection))
        changed = new_selection != self._selected_indexes
        self._selected_indexes = new_selection
        self.selection_changed.emit(new_selection, changed)

    def unload(self):
        self._path = None
        self.ass_file = bubblesub.ass.file.AssFile()
        self.selected_indexes = []
        self.loaded.emit()

    def load_ass(self, path):
        assert path
        path = Path(path)
        try:
            with path.open('r') as handle:
                self.ass_file.load_ass(handle)
        except Exception:
            raise

        self.selected_indexes = []
        self._path = path
        self.loaded.emit()

    def save_ass(self, path, remember_path=False):
        assert path
        path = Path(path)
        if remember_path:
            self._path = path
        with path.open('w') as handle:
            self.ass_file.write_ass(handle)
        if remember_path:
            self.saved.emit()

    def _on_items_about_to_be_removed(self, idx, count):
        new_indexes = list(sorted(self.selected_indexes))
        for i in reversed(range(idx, idx + count)):
            new_indexes = [
                j - 1 if j > i else j
                for j in new_indexes
                if j != i]
        self.selected_indexes = new_indexes
