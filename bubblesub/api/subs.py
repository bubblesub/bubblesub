"""Subtitles API."""
import typing as T
from pathlib import Path

from PyQt5 import QtCore

import bubblesub.ass.reader
import bubblesub.ass.writer
from bubblesub.ass.file import AssFile
from bubblesub.ass.event import EventList
from bubblesub.ass.style import StyleList


class SubtitlesApi(QtCore.QObject):
    """
    The subtitles API.

    Encapsulates ASS styles, subtitles and subtitle selection.
    """

    loaded = QtCore.pyqtSignal()
    saved = QtCore.pyqtSignal()
    selection_changed = QtCore.pyqtSignal(list, bool)

    def __init__(self) -> None:
        """Initialize self."""
        super().__init__()
        self._loaded_video_path: T.Optional[Path] = None
        self._selected_indexes: T.List[int] = []
        self._path: T.Optional[Path] = None
        self.ass_file = AssFile()
        self.lines.items_removed.connect(self._on_items_removed)

    @property
    def lines(self) -> EventList:
        """
        Return list of ASS lines.

        :return: list of lines
        """
        return self.ass_file.events

    @property
    def styles(self) -> StyleList:
        """
        Return list of ASS styles.

        :return: list of styles
        """
        return self.ass_file.styles

    @property
    def info(self) -> T.Dict[str, str]:
        """
        Return info dict.

        This holds basic information about ASS version, video resolution etc.

        :return: info dict
        """
        return self.ass_file.info

    @property
    def meta(self) -> T.Dict[str, str]:
        """
        Return meta dict.

        This holds extra user information not part of the usual ASS spec.

        :return: meta dict
        """
        return self.ass_file.meta

    @property
    def remembered_video_path(self) -> T.Optional[Path]:
        """
        Return path of the associated video file.

        :return: path of the associated video file or None if no video
        """
        path: str = self.meta.get('Video File', '')
        if not path:
            return None
        if not self._path:
            return None
        return self._path.parent / path

    @remembered_video_path.setter
    def remembered_video_path(self, path: Path) -> None:
        """
        Set path of the associated video file, updating meta dict.

        :param path: path to the video file
        """
        self.meta['Video File'] = str(path)
        self.meta['Audio File'] = str(path)

    @property
    def path(self) -> T.Optional[Path]:
        """
        Return path of the currently loaded ASS file.

        :return: path of the currently loaded ASS file or None if no file
        """
        return self._path

    @property
    def has_selection(self) -> bool:
        """
        Return whether there are any selected lines.

        :return: whether there are any selected lines
        """
        return len(self.selected_indexes) > 0

    @property
    def selected_indexes(self) -> T.List[int]:
        """
        Return indexes of the selected lines.

        :return: indexes of the selected lines
        """
        return self._selected_indexes

    @selected_indexes.setter
    def selected_indexes(self, new_selection: T.List[int]) -> None:
        """
        Update line selection.

        :param new_selection: new list of selected indexes
        """
        new_selection = list(sorted(new_selection))
        changed = new_selection != self._selected_indexes
        self._selected_indexes = new_selection
        self.selection_changed.emit(new_selection, changed)

    @property
    def selected_lines(self) -> T.List[bubblesub.ass.event.Event]:
        """
        Return list of selected lines.

        :return: list of selected lines
        """
        return [self.lines[idx] for idx in self.selected_indexes]

    def unload(self) -> None:
        """Load empty ASS file."""
        self._path = None
        self.ass_file = AssFile()
        self.selected_indexes = []
        self.loaded.emit()

    def load_ass(self, path: T.Union[str, Path]) -> None:
        """
        Load specified ASS file.

        :param path: path to load the file from
        """
        assert path
        path = Path(path)
        try:
            with path.open('r') as handle:
                bubblesub.ass.reader.load_ass(handle, self.ass_file)
        except (FileNotFoundError, ValueError):
            raise

        self.selected_indexes = []
        self._path = path
        self.loaded.emit()

    def save_ass(
            self,
            path: T.Union[str, Path],
            remember_path: bool = False
    ) -> None:
        """
        Save current state to the specified file.

        :param path: path to save the state to
        :param remember_path:
            whether to update `self.path` with the specified `path`
        """
        assert path
        path = Path(path)
        if remember_path:
            self._path = path
        with path.open('w') as handle:
            bubblesub.ass.writer.write_ass(self.ass_file, handle)
        if remember_path:
            self.saved.emit()

    def _on_items_removed(self, idx: int, count: int) -> None:
        new_indexes = list(sorted(self.selected_indexes))
        for i in reversed(range(idx, idx + count)):
            new_indexes = [
                j - 1 if j > i else j
                for j in new_indexes
                if j != i
            ]
        self.selected_indexes = new_indexes
