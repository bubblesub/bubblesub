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

import bubblesub.ass.event
import bubblesub.ass.style
import bubblesub.util
from bubblesub.api.subs import SubtitlesApi


class UndoState:
    """Simplified application state."""

    def __init__(
            self,
            events: bubblesub.ass.event.EventList,
            styles: bubblesub.ass.style.StyleList,
            selected_indexes: T.List[int]
    ) -> None:
        """
        Initialize self.

        :param events: list of events for the currently loaded ASS file
        :param styles: list of styles for the currently loaded ASS file
        :param selected_indexes: current selection on the subtitle grid
        """
        self._events = _pickle(events)
        self._styles = _pickle(styles)
        self.selected_indexes = selected_indexes

    @property
    def events(self) -> bubblesub.ass.event.EventList:
        """
        Return list of remembered events.

        :return: list of remembered events
        """
        return T.cast(bubblesub.ass.event.EventList, _unpickle(self._events))

    @property
    def styles(self) -> bubblesub.ass.style.StyleList:
        """
        Return list of remembered styles.

        :return: list of remembered styles
        """
        return T.cast(bubblesub.ass.style.StyleList, _unpickle(self._styles))

    def __eq__(self, other: T.Any) -> T.Any:
        """
        Whether two UndoStates are equivalent.

        Needed to tell if nothing has changed when deciding whether to push
        onto the undo stack.

        :param other: object to compare self with
        :return: bool or NotImplemented to fall back to default implementation
        """
        if isinstance(other, UndoState):
            # pylint: disable=protected-access
            return (
                self._events == other._events
                and self._styles == other._styles
            )
        return NotImplemented

    def __ne__(self, other: T.Any) -> T.Any:
        """
        Opposite of __eq__.

        :param other: object to compare self with
        :return: bool or NotImplemented to fall back to default implementation
        """
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result


def _pickle(data: T.Any) -> bytes:
    """
    Serialize data and use compression to save memory usage.

    :param data: object to serialize
    :return: serialized data
    """
    return zlib.compress(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))


def _unpickle(data: bytes) -> T.Any:
    """
    Deserialize data.

    :param data: serialized data
    :return: deserialized object
    """
    return pickle.loads(zlib.decompress(data))


class UndoApi:
    """The undo API."""

    def __init__(self, subs_api: SubtitlesApi) -> None:
        """
        Initialize self.

        :param subs_api: subtitles API
        """
        self._subs_api = subs_api
        self._stack: T.List[T.Tuple[UndoState, UndoState]] = []
        self._stack_pos = -1
        self._stack_pos_when_saved = -1
        self._subs_api.loaded.connect(self._on_subtitles_load)
        self._subs_api.saved.connect(self._on_subtitles_save)
        self._ignore = bubblesub.util.ScopedCounter()

    @property
    def needs_save(self) -> bool:
        """
        Return whether there are any unsaved changes.

        :return: whether there are any unsaved changes
        """
        return self._stack_pos_when_saved != self._stack_pos

    @property
    def has_undo(self) -> bool:
        """
        Return whether there's anything to undo.

        :return: whether there's anything to undo
        """
        return self._stack_pos - 1 >= 0

    @property
    def has_redo(self) -> bool:
        """
        Return whether there's anything to redo.

        :return: whether there's anything to redo
        """
        return self._stack_pos + 1 < len(self._stack)

    @contextlib.contextmanager
    def capture(self) -> T.Generator:
        """
        Record the application state before and after user operation.

        Doesn't push onto undo stack if nothing has changed.
        This function should wrap any operation that makes "undoable" changes
        (such as changes to the ASS events or styles), especially operations
        from within commands. Otherwise the undo may behave unpredictably.
        """
        old_state = self._make_state()
        with self._ignore:
            yield
        new_state = self._make_state()
        if not self._ignore.num and new_state != old_state:
            self._trim_stack_and_push(old_state, new_state)

    def undo(self) -> None:
        """Restore previous application state."""
        if not self.has_undo:
            raise RuntimeError('No more undo.')

        with self._ignore:
            old_state, _new_state = self._stack[self._stack_pos]
            self._stack_pos -= 1
            self._apply_state(old_state)

    def redo(self) -> None:
        """Reapply undone application state."""
        if not self.has_redo:
            raise RuntimeError('No more redo.')

        with self._ignore:
            self._stack_pos += 1
            _old_state, new_state = self._stack[self._stack_pos]
            self._apply_state(new_state)

    def _trim_stack(self) -> None:
        """Discard any redo information."""
        self._stack = self._stack[:self._stack_pos + 1]
        self._stack_pos = len(self._stack) - 1

    def _trim_stack_and_push(
            self, old_state: UndoState, new_state: UndoState
    ) -> None:
        """
        Discard any redo information and push given state.

        :param old_state: state before change
        :param new_state: state after change
        """
        self._trim_stack()
        self._stack.append((old_state, new_state))
        self._stack_pos = len(self._stack) - 1

    def _on_subtitles_load(self) -> None:
        state = self._make_state()
        self._stack = [(state, state)]
        self._stack_pos = 0
        self._stack_pos_when_saved = 0

    def _on_subtitles_save(self) -> None:
        self._stack_pos_when_saved = self._stack_pos

    def _make_state(self) -> UndoState:
        return UndoState(
            events=self._subs_api.events,
            styles=self._subs_api.styles,
            selected_indexes=self._subs_api.selected_indexes
        )

    def _apply_state(self, state: UndoState) -> None:
        self._subs_api.events.replace(list(state.events))
        self._subs_api.styles.replace(list(state.styles))
        self._subs_api.selected_indexes = state.selected_indexes
