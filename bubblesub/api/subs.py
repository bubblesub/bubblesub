# bubblesub - ASS subtitle editor
# Copyright (C) 2018 Marcin Kurczewski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Subtitles API."""

from collections.abc import Iterable
from pathlib import Path
from typing import Optional, Union, cast

from ass_parser import (
    AssEvent,
    AssEventList,
    AssFile,
    AssScriptInfo,
    AssStyle,
    AssStyleList,
    ObservableSequenceItemRemovalEvent,
    read_ass,
    write_ass,
)
from PyQt5 import QtCore

from bubblesub.cfg import Config
from bubblesub.util import first


class SubtitlesApi(QtCore.QObject):
    """The subtitles API.

    Encapsulates ASS styles, subtitles and subtitle selection.
    """

    loaded = QtCore.pyqtSignal()
    saved = QtCore.pyqtSignal()
    selection_changed = QtCore.pyqtSignal(list, bool)

    def __init__(self, cfg: Config) -> None:
        """Initialize self.

        :param cfg: program configuration
        """
        super().__init__()
        self._cfg = cfg
        self._selected_indexes: list[int] = []
        self._selection_to_commit: list[AssEvent] = []
        self._path: Optional[Path] = None
        self.ass_file = AssFile()

        self.loaded.connect(self._on_subs_load)

    @property
    def events(self) -> AssEventList:
        """Return list of ASS events.

        :return: list of events
        """
        return self.ass_file.events

    @property
    def styles(self) -> AssStyleList:
        """Return list of ASS styles.

        :return: list of styles
        """
        return self.ass_file.styles

    @property
    def script_info(self) -> AssScriptInfo:
        """Return additional information associated with the ASS file.

        This holds basic information about ASS version, video resolution etc.

        :return: additional information
        """
        return self.ass_file.script_info

    @property
    def remembered_video_paths(self) -> Iterable[Path]:
        """Return path of the associated video files.

        :return: paths of the associated video files or empty list if none
        """
        for segment in (self.script_info.get("Video File") or "").split("|"):
            if segment:
                path = Path(segment)
                yield self._path.parent / path if self._path else path

    @property
    def remembered_audio_paths(self) -> Iterable[Path]:
        """Return path of the associated audio files.

        :return: paths of the associated audio files or empty list if none
        """
        for segment in (self.script_info.get("Audio File") or "").split("|"):
            if segment:
                path = Path(segment)
                yield self._path.parent / path if self._path else path

    def remember_video_path_if_needed(self, path: Path) -> None:
        """Add given path to associated video files if it's not there yet.

        :param path: path to remember
        """
        paths = list(self.remembered_video_paths)
        if not paths or not any(
            remembered_path.samefile(path) for remembered_path in paths
        ):
            paths.append(path)
            self.script_info.update({"Video File": "|".join(map(str, paths))})

    def remember_audio_path_if_needed(self, path: Path) -> None:
        """Add given path to associated audio files if it's not there yet.

        :param path: path to remember
        """
        paths = list(self.remembered_audio_paths)
        if not paths or not any(
            remembered_path.samefile(path) for remembered_path in paths
        ):
            paths.append(path)
            self.script_info.update({"Audio File": "|".join(map(str, paths))})

    @property
    def language(self) -> Optional[str]:
        """Return the language of the subtitles, in ISO 639-1 form.

        :return: language
        """
        return cast(str, self.script_info.get("Language") or "") or None

    @language.setter
    def language(self, language: Optional[str]) -> None:
        """Set the language of the subtitles, in ISO 639-1 form.

        :param language: language
        """
        if language:
            self.script_info["Language"] = language
        else:
            self.script_info.pop("Language", None)

    @property
    def path(self) -> Optional[Path]:
        """Return path of the currently loaded ASS file.

        :return: path of the currently loaded ASS file or None if no file
        """
        return self._path

    @property
    def has_selection(self) -> bool:
        """Return whether there are any selected events.

        :return: whether there are any selected events
        """
        return len(self.selected_indexes) > 0

    @property
    def selected_indexes(self) -> list[int]:
        """Return indexes of the selected events.

        :return: indexes of the selected events
        """
        return self._selected_indexes

    @selected_indexes.setter
    def selected_indexes(self, new_selection: list[int]) -> None:
        """Update event selection.

        :param new_selection: new list of selected indexes
        """
        new_selection = list(sorted(new_selection))
        changed = new_selection != self._selected_indexes
        self._selected_indexes = new_selection
        self.selection_changed.emit(new_selection, changed)

    @property
    def selected_events(self) -> list[AssEvent]:
        """Return list of selected events.

        :return: list of selected events
        """
        return [self.events[idx] for idx in self.selected_indexes]

    @property
    def default_style_name(self) -> str:
        """Return default style name.

        :return: first style name if it exists, otherwise "Default"
        """
        style = first(self.styles)
        if style and style.name:
            return style.name
        return "Default"

    def unload(self) -> None:
        """Load empty ASS file."""
        self._path = None
        self.selected_indexes = []
        self.ass_file = AssFile()
        self.ass_file.styles.append(AssStyle(name=self.default_style_name))
        self.ass_file.script_info.update(
            {"Language": self._cfg.opt["gui"]["spell_check"]}
        )
        self.loaded.emit()

    def load_ass(self, path: Union[str, Path]) -> None:
        """Load specified ASS file.

        :param path: path to load the file from
        """
        assert path
        path = Path(path)
        with path.open("r") as handle:
            self.ass_file = read_ass(handle)

        self._cfg.opt.add_recent_file(path)

        self.selected_indexes = []
        self._path = path
        self.loaded.emit()

    def save_ass(
        self, path: Union[str, Path], remember_path: bool = False
    ) -> None:
        """Save current state to the specified file.

        :param path: path to save the state to
        :param remember_path:
            whether to update `self.path` with the specified `path`
        """
        assert path
        path = Path(path)
        if remember_path:
            self._path = path
        with path.open("w") as handle:
            write_ass(self.ass_file, handle)
        if remember_path:
            self.saved.emit()
            self._cfg.opt.add_recent_file(path)

    def _on_subs_load(self) -> None:
        self.events.items_about_to_be_removed.subscribe(
            self._on_items_about_to_be_removed
        )
        self.events.items_removed.subscribe(self._on_items_removed)

    def _on_items_about_to_be_removed(
        self, event: ObservableSequenceItemRemovalEvent
    ) -> None:
        # remember events to re-select before reindexing
        indexes_about_to_be_removed = [item.index for item in event.items]
        self._selection_to_commit = [
            event
            for event in self.selected_events
            if event.index not in indexes_about_to_be_removed
        ]

    def _on_items_removed(
        self, event: ObservableSequenceItemRemovalEvent
    ) -> None:
        # fix selection after reindexing
        self.selected_indexes = [
            event.index for event in self._selection_to_commit
        ]
