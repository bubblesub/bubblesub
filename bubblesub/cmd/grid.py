import wave
import bubblesub.ui.util
from bubblesub.cmd.registry import BaseCommand
from PyQt5 import QtCore
from PyQt5 import QtWidgets


class GridJumpToLineCommand(BaseCommand):
    name = 'grid/jump-to-line'

    def enabled(self, api):
        return len(api.subs.lines) > 0

    def run(self, api):
        dialog = QtWidgets.QInputDialog(api.gui.main_window)
        dialog.setLabelText('Line number to jump to:')
        dialog.setIntMinimum(1)
        dialog.setIntMaximum(len(api.subs.lines))
        if api.subs.has_selection:
            dialog.setIntValue(api.subs.selected_indexes[0] + 1)
        dialog.setInputMode(QtWidgets.QInputDialog.IntInput)
        if dialog.exec_():
            api.subs.selected_indexes = [dialog.intValue() - 1]


class GridJumpToTimeCommand(BaseCommand):
    name = 'grid/jump-to-time'

    def enabled(self, api):
        return len(api.subs.lines) > 0

    def run(self, api):
        dialog = self.JumpToTimeDialog()
        if api.subs.has_selection:
            dialog.setValue(api.subs.lines[api.subs.selected_indexes[0]].start)
        if dialog.exec_():
            target_pts = dialog.value()
            best_distance = None
            best_idx = None
            for i, sub in enumerate(api.subs.lines):
                center = (sub.start + sub.end) / 2
                distance = abs(target_pts - center)
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_idx = i
            if best_idx is not None:
                api.subs.selected_indexes = [best_idx]

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


class GridSelectPrevSubtitleCommand(BaseCommand):
    name = 'grid/select-prev-sub'

    def enabled(self, api):
        return len(api.subs.lines) > 0

    def run(self, api):
        api.subs.selected_indexes = (
            [max(0, api.subs.selected_indexes[0] - 1)]
            if api.subs.selected_indexes else
            [len(api.subs.lines) - 1, 0])


class GridSelectNextSubtitleCommand(BaseCommand):
    name = 'grid/select-next-sub'

    def enabled(self, api):
        return len(api.subs.lines) > 0

    def run(self, api):
        api.subs.selected_indexes = (
            [min(api.subs.selected_indexes[0] + 1, len(api.subs.lines) - 1)]
            if api.subs.selected_indexes else
            [0])


class GridSelectAllCommand(BaseCommand):
    name = 'grid/select-all'

    def enabled(self, api):
        return len(api.subs.lines) > 0

    def run(self, api):
        api.subs.selected_indexes = list(range(len(api.subs.lines)))


class GridSelectNothingCommand(BaseCommand):
    name = 'grid/select-nothing'

    def run(self, api):
        api.subs.selected_indexes = []


class GridCopyToClipboardCommand(BaseCommand):
    name = 'grid/copy-to-clipboard'

    def enabled(self, api):
        return api.subs.has_selection

    def run(self, api):
        QtWidgets.QApplication.clipboard().setText('\n'.join(
            line.text for line in api.subs.selected_lines))


class SaveAudioSampleCommand(BaseCommand):
    name = 'grid/create-audio-sample'

    def enabled(self, api):
        return api.subs.has_selection and api.audio.has_audio_source

    def run(self, api):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            api.gui.main_window,
            directory=QtCore.QDir.homePath(),
            initialFilter='*.wav')

        start_pts = api.subs.selected_lines[0].start
        end_pts = api.subs.selected_lines[-1].end

        start_frame = int(start_pts * api.audio.sample_rate / 1000)
        end_frame = int(end_pts * api.audio.sample_rate / 1000)
        frame_count = end_frame - start_frame

        samples = api.audio.get_samples(start_frame, frame_count)

        with wave.open(path, mode='wb') as handle:
            handle.setnchannels(api.audio.channel_count)
            handle.setsampwidth(api.audio.bits_per_sample // 8)
            handle.setframerate(api.audio.sample_rate)
            handle.setnframes(frame_count)
            handle.setcomptype('NONE', 'No compression')
            handle.writeframesraw(samples.tobytes())
