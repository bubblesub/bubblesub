# bubblesub - ASS subtitle editor
# Copyright (C) 2018 Marcin Kurczewski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Commands related to the subtitle grid."""

import base64
import pickle
import typing as T
import zlib

from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ui.util
from bubblesub.api.cmd import BaseCommand
from bubblesub.ass.event import Event


def _pickle(data: T.Any) -> str:
    return (
        base64.b64encode(
            zlib.compress(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))
        ).decode()
    )


def _unpickle(text: str) -> T.Any:
    return pickle.loads(zlib.decompress(base64.b64decode(text.encode())))


class JumpToSubtitleByLineCommand(BaseCommand):
    """
    Jumps to the specified line.

    Prompts user for the line number with a GUI dialog.
    """

    name = 'grid/jump-to-line'
    menu_name = 'Jump to line by number...'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return len(self.api.subs.events) > 0

    async def run(self) -> None:
        """Carry out the command."""
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        value = self._show_dialog(main_window)
        if value is not None:
            self.api.subs.selected_indexes = [value - 1]

    def _show_dialog(
            self,
            main_window: QtWidgets.QMainWindow
    ) -> T.Optional[int]:
        dialog = QtWidgets.QInputDialog(main_window)
        dialog.setLabelText('Line number to jump to:')
        dialog.setIntMinimum(1)
        dialog.setIntMaximum(len(self.api.subs.events))
        if self.api.subs.has_selection:
            dialog.setIntValue(self.api.subs.selected_indexes[0] + 1)
        dialog.setInputMode(QtWidgets.QInputDialog.IntInput)
        if dialog.exec_():
            return T.cast(int, dialog.intValue())
        return None


class JumpToSubtitleByTimeCommand(BaseCommand):
    """
    Jumps to the subtitle at specified time.

    Prompts user for details with a GUI dialog.
    """

    name = 'grid/jump-to-time'
    menu_name = 'Jump to line by time...'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return len(self.api.subs.events) > 0

    async def run(self) -> None:
        """Carry out the command."""
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        ret = bubblesub.ui.util.time_jump_dialog(
            main_window,
            value=(
                self.api.subs.selected_events[0].start
                if self.api.subs.has_selection else
                0
            ),
            absolute_label='Time to jump to:',
            relative_checked=False,
            show_radio=False
        )
        if ret is None:
            return

        target_pts, _is_relative = ret
        best_distance = None
        best_idx = None
        for i, sub in enumerate(self.api.subs.events):
            center = (sub.start + sub.end) / 2
            distance = abs(target_pts - center)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_idx = i
        if best_idx is not None:
            self.api.subs.selected_indexes = [best_idx]


class SelectPreviousSubtitleCommand(BaseCommand):
    """Selects the subtitle above the first currently selected subtitle."""

    name = 'grid/select-prev-sub'
    menu_name = 'Select previous subtitle'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return len(self.api.subs.events) > 0

    async def run(self) -> None:
        """Carry out the command."""
        if not self.api.subs.selected_indexes:
            self.api.subs.selected_indexes = [len(self.api.subs.events) - 1, 0]
        else:
            self.api.subs.selected_indexes = [
                max(0, self.api.subs.selected_indexes[0] - 1)]


class SelectNextSubtitleCommand(BaseCommand):
    """Selects the subtitle below the last currently selected subtitle."""

    name = 'grid/select-next-sub'
    menu_name = 'Select next subtitle'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return len(self.api.subs.events) > 0

    async def run(self) -> None:
        """Carry out the command."""
        if not self.api.subs.selected_indexes:
            self.api.subs.selected_indexes = [0]
        else:
            self.api.subs.selected_indexes = [
                min(
                    self.api.subs.selected_indexes[-1] + 1,
                    len(self.api.subs.events) - 1
                )
            ]


class SelectAllSubtitlesCommand(BaseCommand):
    """Selects all subtitles."""

    name = 'grid/select-all'
    menu_name = 'Select all subtitles'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return len(self.api.subs.events) > 0

    async def run(self) -> None:
        """Carry out the command."""
        self.api.subs.selected_indexes = list(range(len(self.api.subs.events)))


class ClearSubtitleSelectionCommand(BaseCommand):
    """Clears subtitle selection."""

    name = 'grid/select-nothing'
    menu_name = 'Clear subtitle selection'

    async def run(self) -> None:
        """Carry out the command."""
        self.api.subs.selected_indexes = []


class CopySubtitlesTextToClipboardCommand(BaseCommand):
    """Copies text from the subtitle selection."""

    name = 'grid/copy-text-to-clipboard'
    menu_name = 'Copy selected subtitles text to clipboard'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        QtWidgets.QApplication.clipboard().setText('\n'.join(
            line.text for line in self.api.subs.selected_events
        ))


class CopySubtitlesTimesToClipboardCommand(BaseCommand):
    """Copies time boundaries from the subtitle selection."""

    name = 'grid/copy-times-to-clipboard'
    menu_name = 'Copy selected subtitles times to clipboard'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        QtWidgets.QApplication.clipboard().setText('\n'.join(
            '{} - {}'.format(
                bubblesub.util.ms_to_str(line.start),
                bubblesub.util.ms_to_str(line.end)
            )
            for line in self.api.subs.selected_events
        ))


class PasteSubtitlesTimesFromClipboardCommand(BaseCommand):
    """Pastes time boundaries into the subtitle selection."""

    name = 'grid/paste-times-from-clipboard'
    menu_name = 'Paste times to selected subtitles from clipboard'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            self.error('Clipboard is empty, aborting.')
            return

        lines = text.split('\n')
        if len(lines) != len(self.api.subs.selected_events):
            self.error(
                'Size mismatch (selected {} lines, got {} lines in clipboard.'
                .format(len(self.api.subs.selected_events), len(lines))
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
            for i, sub in enumerate(self.api.subs.selected_events):
                sub.start = times[i][0]
                sub.end = times[i][1]


class CopySubtitlesToClipboardCommand(BaseCommand):
    """Copies the selected subtitles."""

    name = 'grid/copy-to-clipboard'
    menu_name = 'Copy selected subtitles to clipboard'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.subs.has_selection

    async def run(self) -> None:
        """Carry out the command."""
        QtWidgets.QApplication.clipboard().setText(
            _pickle(self.api.subs.selected_events)
        )


def _paste_from_clipboard(cmd: BaseCommand, idx: int) -> None:
    text = QtWidgets.QApplication.clipboard().text()
    if not text:
        cmd.error('Clipboard is empty, aborting.')
        return
    items = T.cast(T.List[Event], _unpickle(text))
    with cmd.api.undo.capture():
        cmd.api.subs.events.insert(idx, items)
        cmd.api.subs.selected_indexes = list(range(idx, idx + len(items)))


class PasteSubtitlesFromClipboardBelowCommand(BaseCommand):
    """Pastes subtitles below the selection."""

    name = 'grid/paste-from-clipboard-below'
    menu_name = 'Paste subtitles from clipboard (below)'

    async def run(self) -> None:
        """Carry out the command."""
        _paste_from_clipboard(self, (
            self.api.subs.selected_indexes[-1] + 1
            if self.api.subs.has_selection else 0
        ))


class PasteSubtitlesFromClipboardAboveCommand(BaseCommand):
    """Pastes subtitles above the selection."""

    name = 'grid/paste-from-clipboard-above'
    menu_name = 'Paste subtitles from clipboard (above)'

    async def run(self) -> None:
        """Carry out the command."""
        _paste_from_clipboard(self, (
            self.api.subs.selected_indexes[0]
            if self.api.subs.has_selection else 0
        ))


class SaveSubtitlesAsAudioSampleCommand(BaseCommand):
    """
    Saves current subtitle selection to a WAV file.

    The audio starts at the first selected subtitle start and ends at the last
    selected subtitle end.
    """

    name = 'grid/create-audio-sample'
    menu_name = 'Create audio sample'

    @property
    def is_enabled(self) -> bool:
        """
        Return whether the command can be executed.

        :return: whether the command can be executed
        """
        return self.api.subs.has_selection \
            and self.api.media.audio.has_audio_source

    async def run(self) -> None:
        """Carry out the command."""
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        path = bubblesub.ui.util.save_dialog(
            main_window, 'Waveform Audio File (*.wav)'
        )
        if path is None:
            self.info('cancelled')
        else:
            start_pts = self.api.subs.selected_events[0].start
            end_pts = self.api.subs.selected_events[-1].end
            self.api.media.audio.save_wav(path, start_pts, end_pts)
            self.info(f'saved audio sample to {path}')


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    """
    Register commands in this file into the command API.

    :param cmd_api: command API
    """
    for cls in [
            JumpToSubtitleByLineCommand,
            JumpToSubtitleByTimeCommand,
            SelectPreviousSubtitleCommand,
            SelectNextSubtitleCommand,
            SelectAllSubtitlesCommand,
            ClearSubtitleSelectionCommand,
            CopySubtitlesTextToClipboardCommand,
            CopySubtitlesTimesToClipboardCommand,
            PasteSubtitlesTimesFromClipboardCommand,
            CopySubtitlesToClipboardCommand,
            PasteSubtitlesFromClipboardBelowCommand,
            PasteSubtitlesFromClipboardAboveCommand,
            SaveSubtitlesAsAudioSampleCommand,
    ]:
        cmd_api.register_core_command(T.cast(T.Type[BaseCommand], cls))
