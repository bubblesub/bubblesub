import bubblesub.util
from PyQt5 import QtCore
from PyQt5 import QtWidgets


class TimeEdit(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resetText()
        self.setInputMask('9:99:99.999')

    def resetText(self):
        self.setText('0:00:00.000')

    def keyPressEvent(self, event):
        super().keyPressEvent(event)

        delta = 10
        if event.key() == QtCore.Qt.Key_Up:
            self.setText(
                bubblesub.util.ms_to_str(
                    bubblesub.util.str_to_ms(self.text()) + delta))
            self.textEdited.emit(self.text())
        elif event.key() == QtCore.Qt.Key_Down:
            self.setText(
                bubblesub.util.ms_to_str(
                    bubblesub.util.str_to_ms(self.text()) - delta))
            self.textEdited.emit(self.text())


class Editor(QtWidgets.QWidget):
    # TODO: allow editing layer, margins and comment
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.setEnabled(False)

        api.grid_selection_changed.connect(self._grid_selection_changed)

        self._index = None
        self._model = api
        self.setLayout(QtWidgets.QVBoxLayout())

        self.start_time_edit = TimeEdit(self)
        self.end_time_edit = TimeEdit(self)
        self.duration_edit = TimeEdit(self)
        self.actor_edit = QtWidgets.QLineEdit(self)
        self.style_edit = QtWidgets.QLineEdit(self)
        self.text_edit = QtWidgets.QPlainTextEdit(self)
        self.text_edit.setTabChangesFocus(True)

        def end_edited(*args):
            start = bubblesub.util.str_to_ms(self.start_time_edit.text())
            end = bubblesub.util.str_to_ms(self.end_time_edit.text())
            duration = end - start
            self.duration_edit.setText(bubblesub.util.ms_to_str(duration))
            self._put_into_model()

        def duration_edited(*args):
            start = bubblesub.util.str_to_ms(self.start_time_edit.text())
            duration = bubblesub.util.str_to_ms(self.duration_edit.text())
            end = start + duration
            self.end_time_edit.setText(bubblesub.util.ms_to_str(end))
            self._put_into_model()

        def text_edited(*args):
            self._put_into_model()

        self.start_time_edit.textEdited.connect(text_edited)
        self.end_time_edit.textEdited.connect(end_edited)
        self.duration_edit.textEdited.connect(duration_edited)
        self.actor_edit.textEdited.connect(text_edited)
        self.style_edit.textEdited.connect(text_edited)
        self.text_edit.textChanged.connect(text_edited)

        top_bar = QtWidgets.QWidget()
        top_bar.setLayout(QtWidgets.QHBoxLayout())
        top_bar.layout().setContentsMargins(0, 0, 0, 0)
        top_bar.layout().addWidget(QtWidgets.QLabel('Start time:'))
        top_bar.layout().addWidget(self.start_time_edit)
        top_bar.layout().addWidget(QtWidgets.QLabel('End time:'))
        top_bar.layout().addWidget(self.end_time_edit)
        top_bar.layout().addWidget(QtWidgets.QLabel('Duration:'))
        top_bar.layout().addWidget(self.duration_edit)
        top_bar.layout().addWidget(QtWidgets.QLabel('Style:'))
        top_bar.layout().addWidget(self.style_edit)
        top_bar.layout().addWidget(QtWidgets.QLabel('Actor:'))
        top_bar.layout().addWidget(self.actor_edit)

        self.layout().addWidget(top_bar)
        self.layout().addWidget(self.text_edit)
        self.text_edit.setFocus()

    def _load_from_model(self, index):
        self._index = index
        subtitle = self._model.subtitles[index]
        self.start_time_edit.setText(bubblesub.util.ms_to_str(subtitle.start))
        self.end_time_edit.setText(bubblesub.util.ms_to_str(subtitle.end))
        self.duration_edit.setText(bubblesub.util.ms_to_str(subtitle.duration))
        self.style_edit.setText(subtitle.style)
        self.actor_edit.setText(subtitle.actor)
        self.text_edit.document().setPlainText(subtitle.text)

    def _put_into_model(self):
        if not self.isEnabled():
            return

        new_start = bubblesub.util.str_to_ms(self.start_time_edit.text())
        new_end = bubblesub.util.str_to_ms(self.end_time_edit.text())
        new_style = self.style_edit.text()
        new_actor = self.actor_edit.text()
        new_text = self.text_edit.toPlainText()

        subtitle = self._model.subtitles[self._index]
        changed = (
            new_start != subtitle.start or
            new_end != subtitle.end or
            new_style != subtitle.style or
            new_actor != subtitle.actor or
            new_text != subtitle.text)

        subtitle.start = bubblesub.util.str_to_ms(self.start_time_edit.text())
        subtitle.end = bubblesub.util.str_to_ms(self.end_time_edit.text())
        subtitle.style = self.style_edit.text()
        subtitle.actor = self.actor_edit.text()
        subtitle.text = self.text_edit.toPlainText()

        if changed:
            self._model.subtitles.item_changed.emit(self._index)

    def _grid_selection_changed(self, rows):
        if len(rows) == 1:
            self._load_from_model(rows[0])
            self.setEnabled(True)
        else:
            self.setEnabled(False)
            self.start_time_edit.resetText()
            self.end_time_edit.resetText()
            self.duration_edit.resetText()
            self.style_edit.setText('')
            self.actor_edit.setText('')
            self.text_edit.document().setPlainText('')
