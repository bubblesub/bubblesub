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

"""Undo API."""

import contextlib
import pickle
import typing as T
import zlib
from copy import copy

from ass_parser import AssFile

from bubblesub.api.subs import SubtitlesApi
from bubblesub.cfg import Config


class UndoState:
    """Simplified application state."""

    def __init__(
        self,
        ass_file: AssFile,
        selected_indexes: T.List[int],
    ) -> None:
        """Initialize self.

        :param ass_file: currently loaded ASS file
        :param selected_indexes: current selection on the subtitle grid
        """
        self._ass_file = _pickle(ass_file)
        self.selected_indexes = selected_indexes

    @property
    def ass_file(self) -> AssFile:
        """Return remembered ASS file.

        :return: remembered ASS file
        """
        return T.cast(AssFile, _unpickle(self._ass_file))

    def __eq__(self, other: T.Any) -> T.Any:
        """Whether two UndoStates are equivalent.

        Needed to tell if nothing has changed when deciding whether to push
        onto the undo stack.

        :param other: object to compare self with
        :return: bool or NotImplemented to fall back to default implementation
        """
        if isinstance(other, UndoState):
            return self.ass_file == other.ass_file
        return NotImplemented

    def __ne__(self, other: T.Any) -> T.Any:
        """Opposite of __eq__.

        :param other: object to compare self with
        :return: bool or NotImplemented to fall back to default implementation
        """
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result


def _pickle(data: T.Any) -> bytes:
    """Serialize data and use compression to save memory usage.

    :param data: object to serialize
    :return: serialized data
    """
    return zlib.compress(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))


def _unpickle(data: bytes) -> T.Any:
    """Deserialize data.

    :param data: serialized data
    :return: deserialized object
    """
    return pickle.loads(zlib.decompress(data))


class UndoApi:
    """API for manipulation of undo and redo data for subtitles styles, events
    and metadata.
    """

    def __init__(self, cfg: Config, subs_api: SubtitlesApi) -> None:
        """Initialize self.

        :param cfg: program configuration
        :param subs_api: subtitles API
        """
        self._cfg = cfg
        self._subs_api = subs_api
        self._stack: T.List[UndoState] = []
        self._stack_pos = -1
        self._saved_state: T.Optional[UndoState] = None
        self._ignore = False

        self._subs_api.loaded.connect(self._on_subtitles_load)
        self._subs_api.saved.connect(self._on_subtitles_save)

    @property
    def needs_save(self) -> bool:
        """Return whether there are any unsaved changes.

        :return: whether there are any unsaved changes
        """
        return self._make_state() != self._saved_state

    @property
    def has_undo(self) -> bool:
        """Return whether there's anything to undo.

        :return: whether there's anything to undo
        """
        return self._stack_pos - 1 >= 0

    @property
    def has_redo(self) -> bool:
        """Return whether there's anything to redo.

        :return: whether there's anything to redo
        """
        return self._stack_pos + 1 < len(self._stack)

    @contextlib.contextmanager
    def capture(self) -> T.Iterator[None]:
        """Execute user operation and record the application state after it.

        Doesn't push onto undo stack if nothing has changed.
        This function should wrap any operation that makes "undoable" changes
        (such as changes to the ASS events or styles), especially operations
        from within commands. Otherwise undoing may do too many changes, and
        the program might exit without asking for confirmation.
        """
        try:
            yield
        finally:
            self.push()

    def undo(self) -> None:
        """Restore previous application state."""
        if not self.has_undo:
            raise RuntimeError("no more undo")
        self._ignore = True
        self._stack_pos -= 1
        old_state = self._stack[self._stack_pos]
        assert old_state
        self._apply_state(old_state)
        self._ignore = False

    def redo(self) -> None:
        """Reapply undone application state."""
        if not self.has_redo:
            raise RuntimeError("no more redo")

        self._ignore = True
        self._stack_pos += 1
        new_state = self._stack[self._stack_pos]
        self._apply_state(new_state)
        self._ignore = False

    def _discard_redo(self) -> None:
        self._stack = self._stack[: self._stack_pos + 1]
        self._stack_pos = len(self._stack) - 1

    def _discard_old_undo(self) -> None:
        max_undo = self._cfg.opt["basic"]["max_undo"]
        if len(self._stack) < max_undo or max_undo <= 0:
            return
        assert self._stack_pos == len(self._stack) - 1
        self._stack = self._stack[-max_undo + 1 :]
        self._stack_pos = len(self._stack) - 1

    def push(self) -> bool:
        """Discard any redo information and push current state onto stack.

        :return: whether there was a change
        """
        if self._ignore:
            return False
        old_state = self._stack[self._stack_pos]
        cur_state = self._make_state()
        if old_state == cur_state:
            return False
        self._discard_redo()
        self._stack.append(cur_state)
        self._stack_pos = len(self._stack) - 1
        self._discard_old_undo()
        return True

    def _on_subtitles_load(self) -> None:
        state = self._make_state()
        self._stack = [state]
        self._stack_pos = 0
        self._saved_state = state

    def _on_subtitles_save(self) -> None:
        self._saved_state = self._make_state()

    def _make_state(self) -> UndoState:
        return UndoState(
            ass_file=self._subs_api.ass_file,
            selected_indexes=self._subs_api.selected_indexes,
        )

    def _apply_state(self, state: UndoState) -> None:
        self._subs_api.ass_file.events[:] = list(
            map(copy, state.ass_file.events)
        )
        self._subs_api.ass_file.styles[:] = list(
            map(copy, state.ass_file.styles)
        )
        self._subs_api.ass_file.script_info.clear()
        self._subs_api.ass_file.script_info.update(state.ass_file.script_info)
        self._subs_api.selected_indexes = state.selected_indexes
