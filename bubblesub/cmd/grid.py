import bubblesub.ui.util
from bubblesub.api.cmd import CoreCommand
from PyQt5 import QtCore
from PyQt5 import QtWidgets


class GridJumpToLineCommand(CoreCommand):
    name = 'grid/jump-to-line'

    def enabled(self):
        return len(self.api.subs.lines) > 0

    def run(self):
        dialog = QtWidgets.QInputDialog(self.api.gui.main_window)
        dialog.setLabelText('Line number to jump to:')
        dialog.setIntMinimum(1)
        dialog.setIntMaximum(len(self.api.subs.lines))
        if self.api.subs.has_selection:
            dialog.setIntValue(self.api.subs.selected_indexes[0] + 1)
        dialog.setInputMode(QtWidgets.QInputDialog.IntInput)
        if dialog.exec_():
            self.api.subs.selected_indexes = [dialog.intValue() - 1]


class GridJumpToTimeCommand(CoreCommand):
    name = 'grid/jump-to-time'

    def enabled(self):
        return len(self.api.subs.lines) > 0

    def run(self):
        dialog = self.JumpToTimeDialog()
        if self.api.subs.has_selection:
            dialog.setValue(self.api.subs.selected_lines[0].start)
        if dialog.exec_():
            target_pts = dialog.value()
            best_distance = None
            best_idx = None
            for i, sub in enumerate(self.api.subs.lines):
                center = (sub.start + sub.end) / 2
                distance = abs(target_pts - center)
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_idx = i
            if best_idx is not None:
                self.api.subs.selected_indexes = [best_idx]

    class JumpToTimeDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.time_widget = bubblesub.ui.util.TimeEdit(
                self, allow_negative=False)

            label = QtWidgets.QLabel('Time to jump to:')
            strip = QtWidgets.QDialogButtonBox(self)
            strip.addButton(strip.Ok)
            strip.addButton(strip.Cancel)
            strip.accepted.connect(self.accept)
            strip.rejected.connect(self.reject)

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(label)
            layout.addWidget(self.time_widget)
            layout.addWidget(strip)
            self.setLayout(layout)

        def setValue(self, value):
            self.time_widget.setText(bubblesub.util.ms_to_str(value))
            self.time_widget.setCursorPosition(0)

        def value(self):
            return bubblesub.util.str_to_ms(self.time_widget.text())


class GridSelectPrevSubtitleCommand(CoreCommand):
    name = 'grid/select-prev-sub'

    def enabled(self):
        return len(self.api.subs.lines) > 0

    def run(self):
        if not self.api.subs.selected_indexes:
            self.api.subs.selected_indexes = [len(self.api.subs.lines) - 1, 0]
        else:
            self.api.subs.selected_indexes = [
                max(0, self.api.subs.selected_indexes[0] - 1)]


class GridSelectNextSubtitleCommand(CoreCommand):
    name = 'grid/select-next-sub'

    def enabled(self):
        return len(self.api.subs.lines) > 0

    def run(self):
        if not self.api.subs.selected_indexes:
            self.api.subs.selected_indexes = [0]
        else:
            self.api.subs.selected_indexes = [
                min(
                    self.api.subs.selected_indexes[0] + 1,
                    len(self.api.subs.lines) - 1)]


class GridSelectAllCommand(CoreCommand):
    name = 'grid/select-all'

    def enabled(self):
        return len(self.api.subs.lines) > 0

    def run(self):
        self.api.subs.selected_indexes = list(range(len(self.api.subs.lines)))


class GridSelectNothingCommand(CoreCommand):
    name = 'grid/select-nothing'

    def run(self):
        self.api.subs.selected_indexes = []


class GridCopyToClipboardCommand(CoreCommand):
    name = 'grid/copy-to-clipboard'

    def enabled(self):
        return self.api.subs.has_selection

    def run(self):
        QtWidgets.QApplication.clipboard().setText('\n'.join(
            line.text for line in self.api.subs.selected_lines))


class SaveAudioSampleCommand(CoreCommand):
    name = 'grid/create-audio-sample'

    def enabled(self):
        return self.api.subs.has_selection and self.api.audio.has_audio_source

    def run(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.api.gui.main_window,
            directory=QtCore.QDir.homePath(),
            initialFilter='*.wav')

        if path:
            start_pts = self.api.subs.selected_lines[0].start
            end_pts = self.api.subs.selected_lines[-1].end
            self.api.audio.save_wav(path, start_pts, end_pts)