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

from bubblesub.api.subs import SubtitlesApi
from bubblesub.ass.event import AssEventList
from bubblesub.ass.meta import AssMeta
from bubblesub.ass.style import AssStyleList
from bubblesub.cfg import Config


class UndoState:
    """Simplified application state."""

    def __init__(
        self,
        events: AssEventList,
        styles: AssStyleList,
        meta: AssMeta,
        selected_indexes: T.List[int],
    ) -> None:
        """Initialize self.

        :param events: list of events for the currently loaded ASS file
        :param styles: list of styles for the currently loaded ASS file
        :param meta: meta dict for the currently loaded ASS file
        :param selected_indexes: current selection on the subtitle grid
        """
        self._events = _pickle(events)
        self._styles = _pickle(styles)
        self._meta = _pickle(dict(meta.items()))
        self.selected_indexes = selected_indexes

    @property
    def events(self) -> AssEventList:
        """Return list of remembered events.

        :return: list of remembered events
        """
        return T.cast(AssEventList, _unpickle(self._events))

    @property
    def styles(self) -> AssStyleList:
        """Return list of remembered styles.

        :return: list of remembered styles
        """
        return T.cast(AssStyleList, _unpickle(self._styles))

    @property
    def meta(self) -> T.Dict[str, str]:
        """Return remembered meta dict.

        :return: meta dict
        """
        return T.cast(T.Dict[str, str], _unpickle(self._meta))

    def __eq__(self, other: T.Any) -> T.Any:
        """Whether two UndoStates are equivalent.

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
                and self._meta == other._meta
            )
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
    """The undo API."""

    def __init__(self, cfg: Config, subs_api: SubtitlesApi) -> None:
        """Initialize self.

        :param cfg: program configuration
        :param subs_api: subtitles API
        """
        self._cfg = cfg
        self._subs_api = subs_api
        self._stack: T.List[T.Tuple[T.Optional[UndoState], UndoState]] = []
        self._stack_pos = -1
        self._dirty = False
        self._prev_state: T.Optional[UndoState] = None
        self._capture_nesting = 0
        self._ignore = False

        self._subs_api.loaded.connect(self._on_subtitles_load)
        self._subs_api.saved.connect(self._on_subtitles_save)

    @property
    def needs_save(self) -> bool:
        """Return whether there are any unsaved changes.

        :return: whether there are any unsaved changes
        """
        return self._dirty

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
        """Record the application state before and after user operation.

        Shorthand for begin_capture() and end_capture().

        Doesn't push onto undo stack if nothing has changed.
        This function should wrap any operation that makes "undoable" changes
        (such as changes to the ASS events or styles), especially operations
        from within commands. Otherwise the undo may behave unpredictably.
        """
        self.begin_capture()
        try:
            yield
        finally:
            self.end_capture()

    def begin_capture(self) -> None:
        """Begin undo capture."""
        if self._ignore:
            return

        # if called recursively, split recorded changes into separate
        # undo point at the entrance point
        cur_state = self._make_state()
        if self._capture_nesting > 0:
            self._push(self._prev_state, cur_state)
        self._prev_state = cur_state
        self._capture_nesting += 1

    def end_capture(self) -> None:
        """End undo capture."""
        cur_state = self._make_state()
        self._push(self._prev_state, cur_state)
        self._capture_nesting -= 1
        self._prev_state = cur_state if self._capture_nesting else None

    def undo(self) -> None:
        """Restore previous application state."""
        if not self.has_undo:
            raise RuntimeError("no more undo")

        self._ignore = True
        old_state, _new_state = self._stack[self._stack_pos]
        self._stack_pos -= 1
        self._dirty = True
        assert old_state
        self._apply_state(old_state)
        self._ignore = False

    def redo(self) -> None:
        """Reapply undone application state."""
        if not self.has_redo:
            raise RuntimeError("no more redo")

        self._ignore = True
        self._stack_pos += 1
        self._dirty = True
        _old_state, new_state = self._stack[self._stack_pos]
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

    def _push(
        self, old_state: T.Optional[UndoState], new_state: UndoState
    ) -> None:
        """Discard any redo information and push given state.

        :param old_state: state before change
        :param new_state: state after change
        """
        if old_state == new_state:
            return
        self._discard_redo()
        self._stack.append((old_state, new_state))
        self._stack_pos = len(self._stack) - 1
        self._dirty = True
        self._discard_old_undo()

    def _on_subtitles_load(self) -> None:
        state = self._make_state()
        self._stack = [(state, state)]
        self._stack_pos = 0
        self._dirty = False

    def _on_subtitles_save(self) -> None:
        self._dirty = False

    def _make_state(self) -> UndoState:
        return UndoState(
            events=self._subs_api.events,
            styles=self._subs_api.styles,
            meta=self._subs_api.meta,
            selected_indexes=self._subs_api.selected_indexes,
        )

    def _apply_state(self, state: UndoState) -> None:
        self._subs_api.events.replace(list(state.events))
        self._subs_api.styles.replace(list(state.styles))
        self._subs_api.meta.clear()
        self._subs_api.meta.update(state.meta)
        self._subs_api.selected_indexes = state.selected_indexes
