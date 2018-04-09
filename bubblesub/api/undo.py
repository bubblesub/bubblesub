import gzip
import pickle


class UndoState:
    def __init__(self, lines=None, styles=None, selected_indexes=None):
        self.lines = lines or []
        self.styles = styles or []
        self.selected_indexes = selected_indexes or []


def _pickle(data):
    return gzip.compress(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))


def _unpickle(data):
    return pickle.loads(gzip.decompress(data))


class UndoApi:
    def __init__(self, subs_api):
        super().__init__()
        self._subs_api = subs_api
        self._undo_stack = []
        self._undo_stack_pos = -1
        self._undo_stack_pos_when_saved = -1
        self._subs_api.loaded.connect(self._on_subtitles_load)
        self._subs_api.saved.connect(self._on_subtitles_save)
        self._ignore = False
        self._tmp_state = self._make_state()

    @property
    def needs_save(self) -> bool:
        return self._undo_stack_pos_when_saved != self._undo_stack_pos

    @property
    def has_undo(self) -> bool:
        return self._undo_stack_pos - 1 >= 0

    @property
    def has_redo(self) -> bool:
        return self._undo_stack_pos + 1 < len(self._undo_stack)

    def mark_undo(self) -> None:
        if self._ignore:
            return
        self._trim_undo_stack_and_append(self._tmp_state, self._make_state())
        self._tmp_state = self._make_state()

    def undo(self) -> None:
        if not self.has_undo:
            raise RuntimeError('No more undo.')

        self._ignore = True
        old_state, _new_state = self._undo_stack[self._undo_stack_pos]
        self._undo_stack_pos -= 1
        self._apply_state(old_state)
        self._ignore = False

    def redo(self) -> None:
        if not self.has_redo:
            raise RuntimeError('No more redo.')

        self._ignore = True
        self._undo_stack_pos += 1
        _old_state, new_state = self._undo_stack[self._undo_stack_pos]
        self._apply_state(new_state)
        self._ignore = False

    def _trim_undo_stack(self) -> None:
        self._undo_stack = self._undo_stack[:self._undo_stack_pos + 1]
        self._undo_stack_pos = len(self._undo_stack) - 1

    def _trim_undo_stack_and_append(
            self, old_state: UndoState, new_state: UndoState) -> None:
        self._trim_undo_stack()
        self._undo_stack.append((old_state, new_state))
        self._undo_stack_pos = len(self._undo_stack) - 1

    def _on_subtitles_load(self) -> None:
        self._undo_stack = [(None, None)]
        self._undo_stack_pos = 0
        self._undo_stack_pos_when_saved = 0
        self._tmp_state = self._make_state()

    def _on_subtitles_save(self) -> None:
        self._undo_stack_pos_when_saved = self._undo_stack_pos

    def _make_state(self) -> UndoState:
        return UndoState(
            lines=_pickle(self._subs_api.lines),
            styles=_pickle(self._subs_api.styles),
            selected_indexes=self._subs_api.selected_indexes)

    def _apply_state(self, state: UndoState) -> None:
        self._subs_api.lines.replace(_unpickle(state.lines))
        self._subs_api.styles.replace(_unpickle(state.styles))
        self._subs_api.selected_indexes = state.selected_indexes
        self._tmp_state = state
