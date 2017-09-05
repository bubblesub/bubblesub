import bubblesub.util
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets


class TextEdit(QtWidgets.QPlainTextEdit):
    def __init__(self, api, name, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._name = name
        self._api = api
        try:
            font_def = self._api.opt.general['fonts'][name]
            if font_def:
                font = QtGui.QFont()
                font.fromString(font_def)
                self.setFont(font)
        except KeyError:
            pass

    def wheelEvent(self, event):
        if event.modifiers() & QtCore.Qt.ControlModifier:
            distance = 1 if event.angleDelta().y() > 0 else -1
            new_size = self.font().pointSize() + distance
            if new_size < 5:
                return
            font = self.font()
            font.setPointSize(new_size)
            self.setFont(font)
            self._api.opt.general['fonts'][self._name] = (
                self.font().toString())


class Editor(QtWidgets.QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)

        self._index = None
        self._api = api

        self.start_time_edit = bubblesub.ui.util.TimeEdit(self)
        self.end_time_edit = bubblesub.ui.util.TimeEdit(self)
        self.duration_edit = bubblesub.ui.util.TimeEdit(self)

        self.margins_widget = QtWidgets.QWidget(self)
        self.margin_l_edit = QtWidgets.QSpinBox(self.margins_widget, minimum=0)
        self.margin_v_edit = QtWidgets.QSpinBox(self.margins_widget, minimum=0)
        self.margin_r_edit = QtWidgets.QSpinBox(self.margins_widget, minimum=0)
        layout = QtWidgets.QHBoxLayout(self.margins_widget, spacing=0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.margin_l_edit)
        layout.addWidget(self.margin_v_edit)
        layout.addWidget(self.margin_r_edit)

        self.layer_edit = QtWidgets.QSpinBox(self, minimum=0)

        self.text_edit = TextEdit(api, 'editor', self, tabChangesFocus=True)
        self.note_edit = TextEdit(
            api, 'notes', self, tabChangesFocus=True, placeholderText='Notes')

        self.style_edit = QtWidgets.QComboBox(
            self,
            editable=True,
            sizePolicy=QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Preferred),
            insertPolicy=QtWidgets.QComboBox.NoInsert)
        self.actor_edit = QtWidgets.QComboBox(
            self,
            editable=True,
            sizePolicy=QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Preferred),
            insertPolicy=QtWidgets.QComboBox.NoInsert)
        self.effect_edit = QtWidgets.QLineEdit(self)
        self.comment_checkbox = QtWidgets.QCheckBox('Comment', self)

        self.top_bar = QtWidgets.QWidget(self)
        layout = QtWidgets.QHBoxLayout(self.top_bar)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtWidgets.QLabel('Start time:', self))
        layout.addWidget(self.start_time_edit)
        layout.addWidget(QtWidgets.QLabel('End time:', self))
        layout.addWidget(self.end_time_edit)
        layout.addWidget(QtWidgets.QLabel('Duration:', self))
        layout.addWidget(self.duration_edit)
        layout.addStretch()
        layout.addWidget(QtWidgets.QLabel('Margins:', self))
        layout.addWidget(self.margins_widget)
        layout.addWidget(QtWidgets.QLabel('Layer:', self))
        layout.addWidget(self.layer_edit)

        self.bottom_bar = QtWidgets.QWidget(self)
        layout = QtWidgets.QHBoxLayout(self.bottom_bar)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtWidgets.QLabel('Style:', self))
        layout.addWidget(self.style_edit)
        layout.addWidget(QtWidgets.QLabel('Actor:', self))
        layout.addWidget(self.actor_edit)
        layout.addStretch()
        layout.addWidget(QtWidgets.QLabel('Effect:', self))
        layout.addWidget(self.effect_edit)
        layout.addWidget(self.comment_checkbox)

        self.center = QtWidgets.QWidget(self)
        layout = QtWidgets.QHBoxLayout(self.center)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.note_edit)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.top_bar)
        layout.addWidget(self.center)
        layout.addWidget(self.bottom_bar)
        self.setEnabled(False)

        self._connect_api_signals()
        self._connect_ui_signals()

    def _fetch_selection(self, index):
        self._index = index
        subtitle = self._api.subs.lines[index]
        self.start_time_edit.set_value(subtitle.start)
        self.end_time_edit.set_value(subtitle.end)
        self.duration_edit.set_value(subtitle.duration)
        self.effect_edit.setText(subtitle.effect)
        self.layer_edit.setValue(subtitle.layer)
        self.comment_checkbox.setChecked(subtitle.is_comment)
        self.margin_l_edit.setValue(subtitle.margins[0])
        self.margin_v_edit.setValue(subtitle.margins[1])
        self.margin_r_edit.setValue(subtitle.margins[2])

        self.actor_edit.clear()
        self.actor_edit.addItems(
            sorted(list(set(sub.actor for sub in self._api.subs.lines))))
        self.actor_edit.lineEdit().setText(subtitle.actor)

        self.style_edit.clear()
        self.style_edit.addItems(
            sorted(list(set(sub.style for sub in self._api.subs.lines))))
        self.style_edit.lineEdit().setText(subtitle.style)

        self.text_edit.document().setPlainText(
            self._convert_newlines(subtitle.text))
        self.note_edit.document().setPlainText(
            self._convert_newlines(subtitle.note))
        self.setEnabled(True)

    def _convert_newlines(self, text):
        if self._api.opt.general['convert_newlines']:
            return text.replace('\\N', '\n')
        return text

    def _clear_selection(self):
        self._index = None
        self.start_time_edit.reset_text()
        self.end_time_edit.reset_text()
        self.duration_edit.reset_text()
        self.style_edit.lineEdit().setText('')
        self.actor_edit.lineEdit().setText('')
        self.effect_edit.setText('')
        self.layer_edit.setValue(0)
        self.comment_checkbox.setChecked(False)
        self.margin_l_edit.setValue(0)
        self.margin_v_edit.setValue(0)
        self.margin_r_edit.setValue(0)
        self.text_edit.document().setPlainText('')
        self.note_edit.document().setPlainText('')
        self.setEnabled(False)

    def _push_selection(self):
        if not self.isEnabled():
            return

        self._disconnect_api_signals()
        subtitle = self._api.subs.lines[self._index]
        subtitle.begin_update()
        subtitle.start = self.start_time_edit.get_value()
        subtitle.end = self.end_time_edit.get_value()
        subtitle.style = self.style_edit.lineEdit().text()
        subtitle.actor = self.actor_edit.lineEdit().text()
        subtitle.text = self.text_edit.toPlainText()
        subtitle.note = self.note_edit.toPlainText()
        subtitle.effect = self.effect_edit.text()
        subtitle.layer = self.layer_edit.value()
        subtitle.margins = (
            self.margin_l_edit.value(),
            self.margin_v_edit.value(),
            self.margin_r_edit.value())
        subtitle.is_comment = self.comment_checkbox.isChecked()
        subtitle.end_update()
        self._connect_api_signals()

    def _grid_selection_changed(self, rows):
        self._disconnect_ui_signals()
        if len(rows) == 1:
            self._fetch_selection(rows[0])
        else:
            self._clear_selection()
        self._connect_ui_signals()

    def _item_changed(self, idx):
        if idx == self._index or idx is None:
            self._disconnect_ui_signals()
            self._fetch_selection(self._index)
            self._connect_ui_signals()

    def _time_end_edited(self):
        self._disconnect_ui_signals()
        start = self.start_time_edit.get_value()
        end = self.end_time_edit.get_value()
        duration = end - start
        self.duration_edit.set_value(duration)
        self._push_selection()
        self._connect_ui_signals()

    def _duration_edited(self):
        self._disconnect_ui_signals()
        start = self.start_time_edit.get_value()
        duration = self.duration_edit.get_value()
        end = start + duration
        self.end_time_edit.set_value(end)
        self._push_selection()
        self._connect_ui_signals()

    def _generic_edited(self):
        self._push_selection()

    def _connect_api_signals(self):
        self._api.subs.lines.item_changed.connect(self._item_changed)
        self._api.subs.selection_changed.connect(self._grid_selection_changed)

    def _disconnect_api_signals(self):
        self._api.subs.lines.item_changed.disconnect(self._item_changed)
        self._api.subs.selection_changed.disconnect(
            self._grid_selection_changed)

    def _connect_ui_signals(self):
        self.start_time_edit.textEdited.connect(self._generic_edited)
        self.end_time_edit.textEdited.connect(self._time_end_edited)
        self.duration_edit.textEdited.connect(self._duration_edited)
        self.actor_edit.editTextChanged.connect(self._generic_edited)
        self.style_edit.editTextChanged.connect(self._generic_edited)
        self.text_edit.textChanged.connect(self._generic_edited)
        self.note_edit.textChanged.connect(self._generic_edited)
        self.effect_edit.textChanged.connect(self._generic_edited)
        self.layer_edit.valueChanged.connect(self._generic_edited)
        self.margin_l_edit.valueChanged.connect(self._generic_edited)
        self.margin_v_edit.valueChanged.connect(self._generic_edited)
        self.margin_r_edit.valueChanged.connect(self._generic_edited)
        self.comment_checkbox.stateChanged.connect(self._generic_edited)

    def _disconnect_ui_signals(self):
        self.start_time_edit.textEdited.disconnect(self._generic_edited)
        self.end_time_edit.textEdited.disconnect(self._time_end_edited)
        self.duration_edit.textEdited.disconnect(self._duration_edited)
        self.actor_edit.editTextChanged.disconnect(self._generic_edited)
        self.style_edit.editTextChanged.disconnect(self._generic_edited)
        self.text_edit.textChanged.disconnect(self._generic_edited)
        self.note_edit.textChanged.disconnect(self._generic_edited)
        self.effect_edit.textChanged.disconnect(self._generic_edited)
        self.layer_edit.valueChanged.disconnect(self._generic_edited)
        self.margin_l_edit.valueChanged.disconnect(self._generic_edited)
        self.margin_v_edit.valueChanged.disconnect(self._generic_edited)
        self.margin_r_edit.valueChanged.disconnect(self._generic_edited)
        self.comment_checkbox.stateChanged.disconnect(self._generic_edited)
