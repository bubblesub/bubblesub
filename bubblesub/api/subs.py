import typing as T
from pathlib import Path

from PyQt5 import QtCore

import bubblesub.ass.event
import bubblesub.ass.style
import bubblesub.ass.file
import bubblesub.model
import bubblesub.util


class SubtitlesApi(QtCore.QObject):
    loaded = QtCore.pyqtSignal()
    saved = QtCore.pyqtSignal()
    selection_changed = QtCore.pyqtSignal(list, bool)

    def __init__(self) -> None:
        super().__init__()
        self._loaded_video_path: T.Optional[Path] = None
        self._selected_indexes: T.List[int] = []
        self._path: T.Optional[Path] = None
        self.ass_file = bubblesub.ass.file.AssFile()
        self.lines.items_about_to_be_removed.connect(
            self._on_items_about_to_be_removed)

    @property
    def lines(self) -> bubblesub.ass.event.EventList:
        return self.ass_file.events

    @property
    def styles(self) -> bubblesub.ass.style.StyleList:
        return self.ass_file.styles

    @property
    def info(self) -> T.Dict[str, str]:
        return self.ass_file.info

    @property
    def meta(self) -> T.Dict[str, str]:
        return self.ass_file.meta

    @property
    def remembered_video_path(self) -> T.Optional[Path]:
        path: str = self.meta.get('Video File', '')
        if not path:
            return None
        if not self._path:
            return None
        return self._path.parent / path

    @remembered_video_path.setter
    def remembered_video_path(self, path: Path) -> None:
        self.meta['Video File'] = str(path)
        self.meta['Audio File'] = str(path)

    @property
    def path(self) -> T.Optional[Path]:
        return self._path

    @property
    def has_selection(self) -> bool:
        return len(self.selected_indexes) > 0

    @property
    def selected_indexes(self) -> T.List[int]:
        return self._selected_indexes

    @selected_indexes.setter
    def selected_indexes(self, new_selection: T.List[int]) -> None:
        new_selection = list(sorted(new_selection))
        changed = new_selection != self._selected_indexes
        self._selected_indexes = new_selection
        self.selection_changed.emit(new_selection, changed)

    @property
    def selected_lines(self) -> T.List[bubblesub.ass.event.Event]:
        return [self.lines[idx] for idx in self.selected_indexes]

    def unload(self) -> None:
        self._path = None
        self.ass_file = bubblesub.ass.file.AssFile()
        self.selected_indexes = []
        self.loaded.emit()

    def load_ass(self, path: T.Union[str, Path]) -> None:
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

    def save_ass(
            self,
            path: T.Union[str, Path],
            remember_path: bool = False) -> None:
        assert path
        path = Path(path)
        if remember_path:
            self._path = path
        with path.open('w') as handle:
            self.ass_file.write_ass(handle)
        if remember_path:
            self.saved.emit()

    def _on_items_about_to_be_removed(self, idx: int, count: int) -> None:
        new_indexes = list(sorted(self.selected_indexes))
        for i in reversed(range(idx, idx + count)):
            new_indexes = [
                j - 1 if j > i else j
                for j in new_indexes
                if j != i]
        self.selected_indexes = new_indexes
