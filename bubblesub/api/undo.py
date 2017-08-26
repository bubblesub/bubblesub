import enum
import pickle
import bubblesub.api.subs
import bubblesub.util
from PyQt5 import QtCore


class UndoOperation(enum.Enum):
    Reset = 0
    SubtitleChange = 1
    SubtitlesInsertion = 2
    SubtitlesRemoval = 3
    # TODO: handle changes to styles once the style editor is in


class UndoBulk:
    def __init__(self, undo_api):
        self._undo_api = undo_api

    def __enter__(self):
        self._undo_api.start_bulk()

    def __exit__(self, _type, _value, _traceback):
        self._undo_api.end_bulk()


class UndoApi(QtCore.QObject):
    def __init__(self, subs_api):
        super().__init__()
        self._subs_api = subs_api
        self._connect_signals()
        self._undo_stack = []
        self._undo_stack_pos = -1
        self._undo_stack_pos_when_saved = -1
        self._subs_api.loaded.connect(self._subtitles_loaded)
        self._subs_api.saved.connect(self._subtitles_saved)
        self._tmp_state = None

    @property
    def needs_save(self):
        return self._undo_stack_pos_when_saved != self._undo_stack_pos

    @property
    def has_undo(self):
        return self._undo_stack_pos - 1 >= 0

    @property
    def has_redo(self):
        return self._undo_stack_pos + 1 < len(self._undo_stack)

    def bulk(self):
        return UndoBulk(self)

    def start_bulk(self):
        self._disconnect_signals()
        self._tmp_state = self._serialize_lines(0, len(self._subs_api.lines))

    def end_bulk(self):
        self._trim_undo_stack_and_append(
            UndoOperation.Reset,
            self._tmp_state,
            self._serialize_lines(0, len(self._subs_api.lines)))
        self._connect_signals()

    def undo(self):
        if not self.has_undo:
            raise RuntimeError('No more undo.')
        self._disconnect_signals()

        op_type, *op_args = self._undo_stack[self._undo_stack_pos]
        self._undo_stack_pos -= 1

        if op_type == UndoOperation.Reset:
            old_lines, _new_lines = op_args
            self._subs_api.lines[:] = self._deserialize_lines(old_lines)
        elif op_type == UndoOperation.SubtitleChange:
            idx, old_lines, _new_lines = op_args
            self._subs_api.lines[idx] = self._deserialize_lines(old_lines)[0]
        elif op_type == UndoOperation.SubtitlesInsertion:
            idx, count, lines = op_args
            self._subs_api.lines.remove(idx, count)
        elif op_type == UndoOperation.SubtitlesRemoval:
            idx, count, lines = op_args
            self._subs_api.lines.insert(idx, self._deserialize_lines(lines))

        self._connect_signals()

    def redo(self):
        if not self.has_redo:
            raise RuntimeError('No more redo.')
        self._disconnect_signals()

        self._undo_stack_pos += 1
        op_type, *op_args = self._undo_stack[self._undo_stack_pos]

        if op_type == UndoOperation.Reset:
            _old_lines, new_lines = op_args
            self._subs_api.lines[:] = self._deserialize_lines(new_lines)
        elif op_type == UndoOperation.SubtitleChange:
            idx, _old_lines, new_lines = op_args
            self._subs_api.lines[idx] = self._deserialize_lines(new_lines)[0]
        elif op_type == UndoOperation.SubtitlesInsertion:
            idx, count, lines = op_args
            self._subs_api.lines.insert(idx, self._deserialize_lines(lines))
        elif op_type == UndoOperation.SubtitlesRemoval:
            idx, count, lines = op_args
            self._subs_api.lines.remove(idx, count)

        self._connect_signals()

    def _trim_undo_stack(self):
        self._undo_stack = self._undo_stack[:self._undo_stack_pos + 1]
        self._undo_stack_pos = len(self._undo_stack) - 1

    def _trim_undo_stack_and_append(self, op_type, *op_args):
        self._trim_undo_stack()
        self._undo_stack.append((op_type, *op_args))
        self._undo_stack_pos = len(self._undo_stack) - 1

    def _connect_signals(self):
        self._subs_api.lines.items_inserted.connect(self._subtitles_inserted)
        self._subs_api.lines.item_changed.connect(self._subtitle_changed)
        self._subs_api.lines.item_about_to_change.connect(
            self._subtitle_about_to_change)
        self._subs_api.lines.items_about_to_be_removed.connect(
            self._subtitles_removed)

    def _disconnect_signals(self):
        self._subs_api.lines.items_inserted.disconnect(
            self._subtitles_inserted)
        self._subs_api.lines.item_changed.disconnect(self._subtitle_changed)
        self._subs_api.lines.item_about_to_change.disconnect(
            self._subtitle_about_to_change)
        self._subs_api.lines.items_about_to_be_removed.disconnect(
            self._subtitles_removed)

    def _subtitles_loaded(self):
        self._undo_stack = [(
            UndoOperation.Reset,
            self._serialize_lines(0, len(self._subs_api.lines)),
            [])]
        self._undo_stack_pos = 0
        self._undo_stack_pos_when_saved = 0

    def _subtitles_saved(self):
        self._undo_stack_pos_when_saved = self._undo_stack_pos

    def _subtitle_about_to_change(self, idx):
        self._tmp_state = self._serialize_lines(idx, 1)

    def _subtitle_changed(self, idx):
        self._trim_undo_stack_and_append(
            UndoOperation.SubtitleChange,
            idx,
            self._tmp_state,
            self._serialize_lines(idx, 1))

    def _subtitles_inserted(self, idx, count):
        self._trim_undo_stack_and_append(
            UndoOperation.SubtitlesInsertion,
            idx,
            count,
            self._serialize_lines(idx, count))

    def _subtitles_removed(self, idx, count):
        self._trim_undo_stack_and_append(
            UndoOperation.SubtitlesRemoval,
            idx,
            count,
            self._serialize_lines(idx, count))

    def _serialize_lines(self, idx, count):
        return pickle.dumps([
            {k: getattr(item, k) for k in item.prop.keys()}
            for item in self._subs_api.lines[idx:idx+count]
        ])

    def _deserialize_lines(self, lines):
        return [
            bubblesub.api.subs.Subtitle(self._subs_api.lines, **item)
            for item in pickle.loads(lines)
        ]
