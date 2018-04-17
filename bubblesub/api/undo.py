import contextlib
import gzip
import pickle
import typing as T

import bubblesub.ass.event
import bubblesub.ass.style
import bubblesub.util
from bubblesub.api.subs import SubtitlesApi


class UndoState:
    def __init__(
            self,
            lines: bubblesub.ass.event.EventList,
            styles: bubblesub.ass.style.StyleList,
            selected_indexes: T.List[int]
    ) -> None:
        self._lines = _pickle(lines)
        self._styles = _pickle(styles)
        self.selected_indexes = selected_indexes

    @property
    def lines(self) -> bubblesub.ass.event.EventList:
        return T.cast(bubblesub.ass.event.EventList, _unpickle(self._lines))

    @property
    def styles(self) -> bubblesub.ass.style.StyleList:
        return T.cast(bubblesub.ass.style.StyleList, _unpickle(self._styles))


def _pickle(data: T.Any) -> bytes:
    return gzip.compress(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))


def _unpickle(data: bytes) -> T.Any:
    return pickle.loads(gzip.decompress(data))


class UndoApi:
    def __init__(self, subs_api: SubtitlesApi) -> None:
        self._subs_api = subs_api
        self._stack: T.List[T.Tuple[UndoState, UndoState]] = []
        self._stack_pos = -1
        self._stack_pos_when_saved = -1
        self._subs_api.loaded.connect(self._on_subtitles_load)
        self._subs_api.saved.connect(self._on_subtitles_save)
        self._ignore = bubblesub.util.ScopedCounter()

    @property
    def needs_save(self) -> bool:
        return self._stack_pos_when_saved != self._stack_pos

    @property
    def has_undo(self) -> bool:
        return self._stack_pos - 1 >= 0

    @property
    def has_redo(self) -> bool:
        return self._stack_pos + 1 < len(self._stack)

    @contextlib.contextmanager
    def capture(self) -> T.Generator:
        old_state = self._make_state()
        with self._ignore:
            yield
        new_state = self._make_state()
        if not self._ignore.num:
            self._trim_stack_and_push(old_state, new_state)

    def undo(self) -> None:
        if not self.has_undo:
            raise RuntimeError('No more undo.')

        with self._ignore:
            old_state, _new_state = self._stack[self._stack_pos]
            self._stack_pos -= 1
            self._apply_state(old_state)

    def redo(self) -> None:
        if not self.has_redo:
            raise RuntimeError('No more redo.')

        with self._ignore:
            self._stack_pos += 1
            _old_state, new_state = self._stack[self._stack_pos]
            self._apply_state(new_state)

    def _trim_stack(self) -> None:
        self._stack = self._stack[:self._stack_pos + 1]
        self._stack_pos = len(self._stack) - 1

    def _trim_stack_and_push(
            self, old_state: UndoState, new_state: UndoState
    ) -> None:
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
            lines=self._subs_api.lines,
            styles=self._subs_api.styles,
            selected_indexes=self._subs_api.selected_indexes
        )

    def _apply_state(self, state: UndoState) -> None:
        self._subs_api.lines.replace(state.lines)
        self._subs_api.styles.replace(state.styles)
        self._subs_api.selected_indexes = state.selected_indexes
