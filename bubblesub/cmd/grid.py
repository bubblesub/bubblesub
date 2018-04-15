import base64
import gzip
import pickle
import typing as T
from pathlib import Path

from PyQt5 import QtWidgets

import bubblesub.ui.util
from bubblesub.api.cmd import CoreCommand
from bubblesub.ass.event import Event


def _pickle(data: T.Any) -> str:
    return (
        base64.b64encode(
            gzip.compress(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))
        ).decode()
    )


def _unpickle(text: str) -> T.Any:
    return pickle.loads(gzip.decompress(base64.b64decode(text.encode())))


class GridJumpToLineCommand(CoreCommand):
    name = 'grid/jump-to-line'
    menu_name = 'Jump to line by number...'

    @property
    def is_enabled(self) -> bool:
        return len(self.api.subs.lines) > 0

    async def run(self) -> None:
        async def run_dialog(
                api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow
        ) -> T.Optional[int]:
            dialog = QtWidgets.QInputDialog(main_window)
            dialog.setLabelText('Line number to jump to:')
            dialog.setIntMinimum(1)
            dialog.setIntMaximum(len(api.subs.lines))
            if api.subs.has_selection:
                dialog.setIntValue(api.subs.selected_indexes[0] + 1)
            dialog.setInputMode(QtWidgets.QInputDialog.IntInput)
            if dialog.exec_():
                return T.cast(int, dialog.intValue())
            return None

        value = await self.api.gui.exec(run_dialog)
        if value is not None:
            self.api.subs.selected_indexes = [value - 1]


class GridJumpToTimeCommand(CoreCommand):
    name = 'grid/jump-to-time'
    menu_name = 'Jump to line by time...'

    @property
    def is_enabled(self) -> bool:
        return len(self.api.subs.lines) > 0

    async def run(self) -> None:
        async def _run_dialog(
                _api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow,
                **kwargs: T.Any
        ) -> T.Optional[T.Tuple[int, bool]]:
            return bubblesub.ui.util.time_jump_dialog(main_window, **kwargs)

        ret = await self.api.gui.exec(
            _run_dialog,
            value=(
                self.api.subs.selected_lines[0].start
                if self.api.subs.has_selection else
                0
            ),
            absolute_label='Time to jump to:',
            relative_checked=False,
            show_radio=False
        )

        if ret is not None:
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

    @property
    def is_enabled(self) -> bool:
        return len(self.api.subs.lines) > 0

    async def run(self) -> None:
        if not self.api.subs.selected_indexes:
            self.api.subs.selected_indexes = [len(self.api.subs.lines) - 1, 0]
        else:
            self.api.subs.selected_indexes = [
                max(0, self.api.subs.selected_indexes[0] - 1)]


class GridSelectNextSubtitleCommand(CoreCommand):
    name = 'grid/select-next-sub'
    menu_name = 'Select next subtitle'

    @property
    def is_enabled(self) -> bool:
        return len(self.api.subs.lines) > 0

    async def run(self) -> None:
        if not self.api.subs.selected_indexes:
            self.api.subs.selected_indexes = [0]
        else:
            self.api.subs.selected_indexes = [
                min(
                    self.api.subs.selected_indexes[-1] + 1,
                    len(self.api.subs.lines) - 1
                )
            ]


class GridSelectAllCommand(CoreCommand):
    name = 'grid/select-all'
    menu_name = 'Select all subtitles'

    @property
    def is_enabled(self) -> bool:
        return len(self.api.subs.lines) > 0

    async def run(self) -> None:
        self.api.subs.selected_indexes = list(range(len(self.api.subs.lines)))


class GridSelectNothingCommand(CoreCommand):
    name = 'grid/select-nothing'
    menu_name = 'Clear subtitle selection'

    async def run(self) -> None:
        self.api.subs.selected_indexes = []


class GridCopyTextToClipboardCommand(CoreCommand):
    name = 'grid/copy-text-to-clipboard'
    menu_name = 'Copy selected subtitles text to clipboard'

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection

    async def run(self) -> None:
        QtWidgets.QApplication.clipboard().setText('\n'.join(
            line.text for line in self.api.subs.selected_lines
        ))


class GridCopyTimesToClipboardCommand(CoreCommand):
    name = 'grid/copy-times-to-clipboard'
    menu_name = 'Copy selected subtitles times to clipboard'

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection

    async def run(self) -> None:
        QtWidgets.QApplication.clipboard().setText('\n'.join(
            '{} - {}'.format(
                bubblesub.util.ms_to_str(line.start),
                bubblesub.util.ms_to_str(line.end)
            )
            for line in self.api.subs.selected_lines
        ))


class GridPasteTimesFromClipboardCommand(CoreCommand):
    name = 'grid/paste-times-from-clipboard'
    menu_name = 'Paste times to selected subtitles from clipboard'

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection

    async def run(self) -> None:
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            self.error('Clipboard is empty, aborting.')
            return

        lines = text.split('\n')
        if len(lines) != len(self.api.subs.selected_lines):
            self.error(
                'Size mismatch (selected {} lines, got {} lines in clipboard.'
                .format(len(self.api.subs.selected_lines), len(lines))
            )
            return

        times: T.List[T.Tuple[int, int]] = []
        for line in lines:
            try:
                start, end = line.strip().split(' - ')
                times.append((
                    bubblesub.util.str_to_ms(start),
                    bubblesub.util.str_to_ms(end)
                ))
            except ValueError:
                self.error('Invalid time format: {}'.format(line))
                return

        with self.api.undo.capture():
            for i, sub in enumerate(self.api.subs.selected_lines):
                sub.start = times[i][0]
                sub.end = times[i][1]


class GridCopyToClipboardCommand(CoreCommand):
    name = 'grid/copy-to-clipboard'
    menu_name = 'Copy selected subtitles to clipboard'

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection

    async def run(self) -> None:
        QtWidgets.QApplication.clipboard().setText(
            _pickle(self.api.subs.selected_lines)
        )


class PasteFromClipboardBelowCommand(CoreCommand):
    name = 'grid/paste-from-clipboard-below'
    menu_name = 'Paste subtitles from clipboard (below)'

    async def run(self) -> None:
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            self.error('Clipboard is empty, aborting.')
            return
        idx = self.api.subs.selected_indexes[-1] + 1
        items = T.cast(T.List[Event], _unpickle(text))
        with self.api.undo.capture():
            self.api.subs.lines.insert(idx, items)
            self.api.subs.selected_indexes = list(range(idx, idx + len(items)))


class PasteFromClipboardAboveCommand(CoreCommand):
    name = 'grid/paste-from-clipboard-above'
    menu_name = 'Paste subtitles from clipboard (above)'

    async def run(self) -> None:
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            self.error('Clipboard is empty, aborting.')
            return
        idx = self.api.subs.selected_indexes[0]
        items = T.cast(T.List[Event], _unpickle(text))
        with self.api.undo.capture():
            self.api.subs.lines.insert(idx, items)
            self.api.subs.selected_indexes = list(range(idx, idx + len(items)))


class SaveAudioSampleCommand(CoreCommand):
    name = 'grid/create-audio-sample'
    menu_name = 'Create audio sample...'

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection \
            and self.api.media.audio.has_audio_source

    async def run(self) -> None:
        async def run_dialog(
                _api: bubblesub.api.Api,
                main_window: QtWidgets.QMainWindow
        ) -> T.Optional[Path]:
            return bubblesub.ui.util.save_dialog(
                main_window, 'Waveform Audio File (*.wav)'
            )

        path = await self.api.gui.exec(run_dialog)
        if path is not None:
            start_pts = self.api.subs.selected_lines[0].start
            end_pts = self.api.subs.selected_lines[-1].end
            self.api.media.audio.save_wav(path, start_pts, end_pts)
