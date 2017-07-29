import copy
import enum
import bubblesub.api.subs
import bubblesub.util
from PyQt5 import QtCore


class UndoOperation:
    Reset = 0
    SubtitleChange = 1
    SubtitlesInsertion = 2
    SubtitlesRemoval = 3
    # TODO: handle changes to styles once the style editor is in


class UndoApi(QtCore.QObject):
    def __init__(self, subs_api):
        super().__init__()
        self._subs_api = subs_api
        self._connect_signals()
        self._undo_stack = []
        self._undo_stack_pos = -1
        self._subs_api.loaded.connect(self._reset)

    @property
    def has_undo(self):
        return self._undo_stack_pos - 1 >= 0

    @property
    def has_redo(self):
        return self._undo_stack_pos + 1 < len(self._undo_stack)

    def undo(self):
        if not self.has_undo:
            raise RuntimeError('No more undo.')
        self._disconnect_signals()

        self._undo_stack_pos -= 1
        op, *op_args = self._undo_stack[self._undo_stack_pos]

        if op == UndoOperation.Reset:
            lines, = op_args
            self._subs_api.lines[:] = self._deserialize_lines(lines)
        elif op == UndoOperation.SubtitleChange:
            idx, lines = op_args
            self._subs_api.lines[idx] = self._deserialize_lines(lines)[0]
        elif op == UndoOperation.SubtitlesInsertion:
            idx, count, lines = op_args
            self._subs_api.lines.remove(idx, count)
        elif op == UndoOperation.SubtitlesRemoval:
            idx, count, lines = op_args
            self._subs_api.lines.insert(idx, self._deserialize_lines(lines))

        self._connect_signals()

    def redo(self):
        if not self.has_redo:
            raise RuntimeError('No more redo.')
        self._disconnect_signals()

        self._undo_stack_pos += 1
        op, *op_args = self._undo_stack[self._undo_stack_pos]

        if op == UndoOperation.Reset:
            lines, = op_args
            self._subs_api.lines = lines
        elif op == UndoOperation.SubtitleChange:
            idx, lines = op_args
            self._subs_api.lines[idx] = self._deserialize_lines(lines)[0]
        elif op == UndoOperation.SubtitlesInsertion:
            idx, count, lines = op_args
            self._subs_api.lines.insert(idx, self._deserialize_lines(lines))
        elif op == UndoOperation.SubtitlesRemoval:
            idx, count, lines = op_args
            self._subs_api.lines.remove(idx, count)

        self._connect_signals()

    def _trim_undo_stack(self):
        self._undo_stack = self._undo_stack[:self._undo_stack_pos + 1]
        self._undo_stack_pos = len(self._undo_stack) - 1

    def _trim_undo_stack_and_append(self, op):
        self._trim_undo_stack()
        self._undo_stack.append(op)
        self._undo_stack_pos = len(self._undo_stack) - 1
        print('Size of undo stack:', bubblesub.util.getsize(self._undo_stack))

    def _reset(self):
        self._undo_stack = [(
            UndoOperation.Reset,
            self._serialize_lines(0, len(self._subs_api.lines)))]
        self._undo_stack_pos = 0

    def _connect_signals(self):
        self._subs_api.lines.item_changed.connect(self._subtitle_changed)
        self._subs_api.lines.items_inserted.connect(self._subtitles_inserted)
        self._subs_api.lines.items_removed.connect(self._subtitles_removed)

    def _disconnect_signals(self):
        self._subs_api.lines.item_changed.disconnect(self._subtitle_changed)
        self._subs_api.lines.items_inserted.disconnect(self._subtitles_inserted)
        self._subs_api.lines.items_removed.disconnect(self._subtitles_removed)

    def _subtitle_changed(self, idx):
        # XXX: merge with previous operation if it concerns the same subtitle
        # and only one field has changed (difficult)
        self._trim_undo_stack_and_append((
            UndoOperation.SubtitleChange,
            idx,
            self._serialize_lines(idx, 1)))

    def _subtitles_inserted(self, idx, count):
        self._trim_undo_stack_and_append((
            UndoOperation.SubtitlesInsertion,
            idx,
            count,
            self._serialize_lines(idx, count)))

    def _subtitles_removed(self, idx, count):
        self._trim_undo_stack_and_append((
            UndoOperation.SubtitlesRemoval,
            idx,
            count,
            self._serialize_lines(idx, count)))

    # TODO: handle margins etc. once they appear
    def _serialize_lines(self, idx, count):
        ret = []
        for line in self._subs_api.lines[idx:idx+count]:
            ret.append((
                line.start, line.end, line.style, line.actor, line.text))
        return ret

    def _deserialize_lines(self, lines):
        ret = []
        for line in lines:
            ret.append((
                bubblesub.api.subs.Subtitle(
                    self._subs_api.lines,
                    start=line[0],
                    end=line[1],
                    style=line[2],
                    actor=line[3],
                    text=line[4])))
        return ret
