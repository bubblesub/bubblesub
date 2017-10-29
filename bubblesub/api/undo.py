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
    StyleChange = 4
    StylesInsertion = 5
    StylesRemoval = 6


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
        self._subs_api.loaded.connect(self._on_subtitles_load)
        self._subs_api.saved.connect(self._on_subtitles_save)
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
        self._tmp_state = (
            self._serialize_lines(0, len(self._subs_api.lines)),
            self._serialize_styles(0, len(self._subs_api.styles)))

    def end_bulk(self):
        self._trim_undo_stack_and_append(
            UndoOperation.Reset,
            self._tmp_state[0],
            self._serialize_lines(0, len(self._subs_api.lines)),
            self._tmp_state[1],
            self._serialize_styles(0, len(self._subs_api.styles)))
        self._connect_signals()

    def undo(self):
        if not self.has_undo:
            raise RuntimeError('No more undo.')
        self._disconnect_signals()

        op_type, *op_args = self._undo_stack[self._undo_stack_pos]
        self._undo_stack_pos -= 1

        if op_type == UndoOperation.Reset:
            old_lines, _new_lines, old_styles, _new_styles = op_args
            self._subs_api.lines.replace(self._deserialize_lines(old_lines))
            self._subs_api.styles.replace(self._deserialize_styles(old_styles))
        elif op_type == UndoOperation.SubtitleChange:
            idx, old_lines, _new_lines = op_args
            self._subs_api.lines[idx] = self._deserialize_lines(old_lines)[0]
        elif op_type == UndoOperation.SubtitlesInsertion:
            idx, count, lines = op_args
            self._subs_api.lines.remove(idx, count)
        elif op_type == UndoOperation.SubtitlesRemoval:
            idx, count, lines = op_args
            self._subs_api.lines.insert(idx, self._deserialize_lines(lines))
        elif op_type == UndoOperation.StyleChange:
            idx, old_styles, _new_styles = op_args
            self._subs_api.styles[idx] = (
                self._deserialize_styles(old_styles)[0])
        elif op_type == UndoOperation.StylesInsertion:
            idx, count, styles = op_args
            self._subs_api.styles.remove(idx, count)
        elif op_type == UndoOperation.StylesRemoval:
            idx, count, styles = op_args
            self._subs_api.styles.insert(idx, self._deserialize_styles(styles))

        self._connect_signals()

    def redo(self):
        if not self.has_redo:
            raise RuntimeError('No more redo.')
        self._disconnect_signals()

        self._undo_stack_pos += 1
        op_type, *op_args = self._undo_stack[self._undo_stack_pos]

        if op_type == UndoOperation.Reset:
            _old_lines, new_lines, _old_styles, new_styles = op_args
            self._subs_api.lines.replace(self._deserialize_lines(new_lines))
            self._subs_api.styles.replace(self._deserialize_styles(new_styles))
        elif op_type == UndoOperation.SubtitleChange:
            idx, _old_lines, new_lines = op_args
            self._subs_api.lines[idx] = self._deserialize_lines(new_lines)[0]
        elif op_type == UndoOperation.SubtitlesInsertion:
            idx, count, lines = op_args
            self._subs_api.lines.insert(idx, self._deserialize_lines(lines))
        elif op_type == UndoOperation.SubtitlesRemoval:
            idx, count, lines = op_args
            self._subs_api.lines.remove(idx, count)
        elif op_type == UndoOperation.StyleChange:
            idx, _old_styles, new_styles = op_args
            self._subs_api.styles[idx] = (
                self._deserialize_styles(new_styles)[0])
        elif op_type == UndoOperation.StylesInsertion:
            idx, count, styles = op_args
            self._subs_api.styles.insert(idx, self._deserialize_styles(styles))
        elif op_type == UndoOperation.StylesRemoval:
            idx, count, styles = op_args
            self._subs_api.styles.remove(idx, count)

        self._connect_signals()

    def _trim_undo_stack(self):
        self._undo_stack = self._undo_stack[:self._undo_stack_pos + 1]
        self._undo_stack_pos = len(self._undo_stack) - 1

    def _trim_undo_stack_and_append(self, op_type, *op_args):
        self._trim_undo_stack()
        self._undo_stack.append((op_type, *op_args))
        self._undo_stack_pos = len(self._undo_stack) - 1

    def _connect_signals(self):
        self._subs_api.lines.items_inserted.connect(self._on_subtitles_insert)
        self._subs_api.lines.item_changed.connect(self._on_subtitle_change)
        self._subs_api.lines.item_about_to_change.connect(
            self._on_subtitle_about_to_change)
        self._subs_api.lines.items_about_to_be_removed.connect(
            self._on_subtitles_remove)
        self._subs_api.styles.items_inserted.connect(self._on_styles_insert)
        self._subs_api.styles.item_changed.connect(self._on_style_change)
        self._subs_api.styles.item_about_to_change.connect(
            self._on_style_about_to_change)
        self._subs_api.styles.items_about_to_be_removed.connect(
            self._on_styles_remove)

    def _disconnect_signals(self):
        self._subs_api.lines.items_inserted.disconnect(
            self._on_subtitles_insert)
        self._subs_api.lines.item_changed.disconnect(self._on_subtitle_change)
        self._subs_api.lines.item_about_to_change.disconnect(
            self._on_subtitle_about_to_change)
        self._subs_api.lines.items_about_to_be_removed.disconnect(
            self._on_subtitles_remove)
        self._subs_api.styles.items_inserted.disconnect(self._on_styles_insert)
        self._subs_api.styles.item_changed.disconnect(self._on_style_change)
        self._subs_api.styles.item_about_to_change.disconnect(
            self._on_style_about_to_change)
        self._subs_api.styles.items_about_to_be_removed.disconnect(
            self._on_styles_remove)

    def _on_subtitles_load(self):
        self._undo_stack = [(
            UndoOperation.Reset,
            self._serialize_lines(0, len(self._subs_api.lines)),
            [],
            self._serialize_styles(0, len(self._subs_api.styles)),
            [])]
        self._undo_stack_pos = 0
        self._undo_stack_pos_when_saved = 0

    def _on_subtitles_save(self):
        self._undo_stack_pos_when_saved = self._undo_stack_pos

    def _on_subtitle_about_to_change(self, idx):
        self._tmp_state = self._serialize_lines(idx, 1)

    def _on_subtitle_change(self, idx):
        self._trim_undo_stack_and_append(
            UndoOperation.SubtitleChange,
            idx,
            self._tmp_state,
            self._serialize_lines(idx, 1))

    def _on_subtitles_insert(self, idx, count):
        self._trim_undo_stack_and_append(
            UndoOperation.SubtitlesInsertion,
            idx,
            count,
            self._serialize_lines(idx, count))

    def _on_subtitles_remove(self, idx, count):
        self._trim_undo_stack_and_append(
            UndoOperation.SubtitlesRemoval,
            idx,
            count,
            self._serialize_lines(idx, count))

    def _on_style_about_to_change(self, idx):
        self._tmp_state = self._serialize_styles(idx, 1)

    def _on_style_change(self, idx):
        self._trim_undo_stack_and_append(
            UndoOperation.StyleChange,
            idx,
            self._tmp_state,
            self._serialize_styles(idx, 1))

    def _on_styles_insert(self, idx, count):
        self._trim_undo_stack_and_append(
            UndoOperation.StylesInsertion,
            idx,
            count,
            self._serialize_styles(idx, count))

    def _on_styles_remove(self, idx, count):
        self._trim_undo_stack_and_append(
            UndoOperation.StylesRemoval,
            idx,
            count,
            self._serialize_styles(idx, count))

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

    def _serialize_styles(self, idx, count):
        return pickle.dumps([
            {k: getattr(item, k) for k in item.prop.keys()}
            for item in self._subs_api.styles[idx:idx+count]
        ])

    def _deserialize_styles(self, styles):
        return [
            bubblesub.api.subs.Style(self._subs_api.styles, **item)
            for item in pickle.loads(styles)
        ]
