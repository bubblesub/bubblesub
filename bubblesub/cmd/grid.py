import json
import bubblesub.ui.util
from bubblesub.api.cmd import CoreCommand
from PyQt5 import QtWidgets


class GridJumpToLineCommand(CoreCommand):
    name = 'grid/jump-to-line'
    menu_name = 'Jump to line by number...'

    def enabled(self):
        return len(self.api.subs.lines) > 0

    async def run(self):
        async def run_dialog(api, main_window):
            dialog = QtWidgets.QInputDialog(main_window)
            dialog.setLabelText('Line number to jump to:')
            dialog.setIntMinimum(1)
            dialog.setIntMaximum(len(api.subs.lines))
            if api.subs.has_selection:
                dialog.setIntValue(api.subs.selected_indexes[0] + 1)
            dialog.setInputMode(QtWidgets.QInputDialog.IntInput)
            if dialog.exec_():
                return dialog.intValue()
            return None

        value = await self.api.gui.exec(run_dialog)
        if value is not None:
            self.api.subs.selected_indexes = [value - 1]


class GridJumpToTimeCommand(CoreCommand):
    name = 'grid/jump-to-time'
    menu_name = 'Jump to line by time...'

    def enabled(self):
        return len(self.api.subs.lines) > 0

    async def run(self):
        async def _run_dialog(_api, main_window, **kwargs):
            return bubblesub.ui.util.time_jump_dialog(main_window, **kwargs)

        ret = await self.api.gui.exec(
            _run_dialog,
            value=(
                self.api.subs.selected_lines[0].start
                if self.api.subs.has_selection
                else 0),
            absolute_label='Time to jump to:',
            relative_checked=False,
            show_radio=False)

        if ret:
            target_pts, _is_relative = ret
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


class GridSelectPrevSubtitleCommand(CoreCommand):
    name = 'grid/select-prev-sub'
    menu_name = 'Select previous subtitle'

    def enabled(self):
        return len(self.api.subs.lines) > 0

    async def run(self):
        if not self.api.subs.selected_indexes:
            self.api.subs.selected_indexes = [len(self.api.subs.lines) - 1, 0]
        else:
            self.api.subs.selected_indexes = [
                max(0, self.api.subs.selected_indexes[0] - 1)]


class GridSelectNextSubtitleCommand(CoreCommand):
    name = 'grid/select-next-sub'
    menu_name = 'Select next subtitle'

    def enabled(self):
        return len(self.api.subs.lines) > 0

    async def run(self):
        if not self.api.subs.selected_indexes:
            self.api.subs.selected_indexes = [0]
        else:
            self.api.subs.selected_indexes = [
                min(
                    self.api.subs.selected_indexes[-1] + 1,
                    len(self.api.subs.lines) - 1)]


class GridSelectAllCommand(CoreCommand):
    name = 'grid/select-all'
    menu_name = 'Select all subtitles'

    def enabled(self):
        return len(self.api.subs.lines) > 0

    async def run(self):
        self.api.subs.selected_indexes = list(range(len(self.api.subs.lines)))


class GridSelectNothingCommand(CoreCommand):
    name = 'grid/select-nothing'
    menu_name = 'Clear subtitle selection'

    async def run(self):
        self.api.subs.selected_indexes = []


class GridCopyTextToClipboardCommand(CoreCommand):
    name = 'grid/copy-text-to-clipboard'
    menu_name = 'Copy selected subtitles text to clipboard'

    def enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        QtWidgets.QApplication.clipboard().setText('\n'.join(
            line.text for line in self.api.subs.selected_lines))


class GridCopyTimesToClipboardCommand(CoreCommand):
    name = 'grid/copy-times-to-clipboard'
    menu_name = 'Copy selected subtitles times to clipboard'

    def enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        QtWidgets.QApplication.clipboard().setText('\n'.join(
            '{} - {}'.format(
                bubblesub.util.ms_to_str(line.start),
                bubblesub.util.ms_to_str(line.end))
            for line in self.api.subs.selected_lines))


class GridPasteTimesFromClipboardCommand(CoreCommand):
    name = 'grid/paste-times-from-clipboard'
    menu_name = 'Paste times to selected subtitles from clipboard'

    def enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            self.error('Clipboard is empty, aborting.')
            return

        lines = text.split('\n')
        if len(lines) != len(self.api.subs.selected_lines):
            self.error(
                'Size mismatch (selected {} lines, got {} lines in clipboard.'
                .format(len(self.api.subs.selected_lines), len(lines)))
            return

        times = []
        for line in lines:
            try:
                start, end = line.strip().split(' - ')
                start = bubblesub.util.str_to_ms(start)
                end = bubblesub.util.str_to_ms(end)
                times.append((start, end))
            except Exception:
                self.error('Invalid time format: {}'.format(line))
                return

        with self.api.undo.bulk():
            for i, line in enumerate(self.api.subs.selected_lines):
                line.start = times[i][0]
                line.end = times[i][1]


class GridCopyToClipboardCommand(CoreCommand):
    name = 'grid/copy-to-clipboard'
    menu_name = 'Copy selected subtitles to clipboard'

    def enabled(self):
        return self.api.subs.has_selection

    async def run(self):
        QtWidgets.QApplication.clipboard().setText(json.dumps([
            {k: getattr(item, k) for k in item.prop.keys()}
            for item in self.api.subs.selected_lines
        ]))


class PasteFromClipboardBelowCommand(CoreCommand):
    name = 'grid/paste-from-clipboard-below'
    menu_name = 'Paste subtitles from clipboard (below)'

    async def run(self):
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            self.error('Clipboard is empty, aborting.')
            return
        idx = self.api.subs.selected_indexes[-1] + 1
        with self.api.undo.bulk():
            items = json.loads(text)
            for i, item in enumerate(items):
                self.api.subs.lines.insert_one(idx + i, **item)
        self.api.subs.selected_indexes = list(range(idx, idx + len(items)))


class PasteFromClipboardAboveCommand(CoreCommand):
    name = 'grid/paste-from-clipboard-above'
    menu_name = 'Paste subtitles from clipboard (above)'

    async def run(self):
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            self.error('Clipboard is empty, aborting.')
            return
        idx = self.api.subs.selected_indexes[0]
        with self.api.undo.bulk():
            items = json.loads(text)
            for item in reversed(items):
                self.api.subs.lines.insert_one(idx, **item)
        self.api.subs.selected_indexes = list(range(idx, idx + len(items)))


class SaveAudioSampleCommand(CoreCommand):
    name = 'grid/create-audio-sample'
    menu_name = 'Create audio sample...'

    def enabled(self):
        return self.api.subs.has_selection and self.api.audio.has_audio_source

    async def run(self):
        async def run_dialog(_api, main_window):
            return bubblesub.ui.util.save_dialog(
                main_window, 'Waveform Audio File (*.wav)')

        path = await self.api.gui.exec(run_dialog)
        if path:
            start_pts = self.api.subs.selected_lines[0].start
            end_pts = self.api.subs.selected_lines[-1].end
            self.api.audio.save_wav(path, start_pts, end_pts)
