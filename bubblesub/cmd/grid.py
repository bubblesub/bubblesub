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

import argparse
import base64
import pickle
import typing as T
import zlib

from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ui.util
from bubblesub.api.cmd import BaseCommand
from bubblesub.ass.event import Event
from bubblesub.util import VerticalDirection


def _pickle(data: T.Any) -> str:
    return (
        base64.b64encode(
            zlib.compress(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))
        ).decode()
    )


def _unpickle(text: str) -> T.Any:
    return pickle.loads(zlib.decompress(base64.b64decode(text.encode())))


class JumpToSubtitleByNumberCommand(BaseCommand):
    names = ['grid/jump-to-sub-by-number']
    menu_name = 'Jump to subtitle by number...'
    help_text = (
        'Jumps to the specified number. '
        'Prompts user for the line number with a GUI dialog.'
    )

    @property
    def is_enabled(self) -> bool:
        return len(self.api.subs.events) > 0

    async def run(self) -> None:
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
    names = ['grid/jump-to-sub-by-time']
    menu_name = 'Jump to subtitle by time...'
    help_text = (
        'Jumps to the subtitle at specified time. '
        'Prompts user for details with a GUI dialog.'
    )

    @property
    def is_enabled(self) -> bool:
        return len(self.api.subs.events) > 0

    async def run(self) -> None:
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


class SelectNearSubtitleCommand(BaseCommand):
    names = ['grid/select-near-sub']
    help_text = (
        'Selects nearest subtitle in given direction to the current selection.'
    )

    @property
    def menu_name(self) -> str:
        return f'Select {self.args.direction.name.lower()} subtitle'

    @property
    def is_enabled(self) -> bool:
        return len(self.api.subs.events) > 0

    async def run(self) -> None:
        max_idx = len(self.api.subs.events) - 1
        if self.args.direction == VerticalDirection.Above:
            if not self.api.subs.selected_indexes:
                self.api.subs.selected_indexes = [max_idx]
            else:
                self.api.subs.selected_indexes = [
                    max(0, self.api.subs.selected_indexes[0] - 1)
                ]
        elif self.args.direction == VerticalDirection.Below:
            if not self.api.subs.selected_indexes:
                self.api.subs.selected_indexes = [0]
            else:
                self.api.subs.selected_indexes = [
                    min(self.api.subs.selected_indexes[-1] + 1, max_idx)
                ]
        else:
            raise AssertionError

    @staticmethod
    def _decorate_parser(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-d', '--direction',
            help='direction to look in',
            type=VerticalDirection.from_string,
            choices=list(VerticalDirection),
            required=True
        )


class SelectAllSubtitlesCommand(BaseCommand):
    names = ['grid/select-all-subs']
    menu_name = 'Select all subtitles'
    help_text = 'Selects all subtitles.'

    @property
    def is_enabled(self) -> bool:
        return len(self.api.subs.events) > 0

    async def run(self) -> None:
        self.api.subs.selected_indexes = list(range(len(self.api.subs.events)))


class ClearSubtitleSelectionCommand(BaseCommand):
    names = ['grid/clear-sub-sel']
    menu_name = 'Clear subtitle selection'
    help_text = 'Clears subtitle selection.'

    async def run(self) -> None:
        self.api.subs.selected_indexes = []


class CopySubtitlesTextCommand(BaseCommand):
    names = ['grid/copy-subs/text']
    menu_name = 'Copy selected subtitles text to clipboard'
    help_text = 'Copies text from the subtitle selection.'

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection

    async def run(self) -> None:
        QtWidgets.QApplication.clipboard().setText('\n'.join(
            line.text for line in self.api.subs.selected_events
        ))


class PasteSubtitlesTextCommand(BaseCommand):
    names = ['grid/paste-subs/text']
    menu_name = 'Paste text to selected subtitles from clipboard'
    help_text = 'Pastes teext into the subtitle selection.'

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection

    async def run(self) -> None:
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            self.api.log.error('Clipboard is empty, aborting.')
            return

        lines = text.split('\n')
        if len(lines) != len(self.api.subs.selected_events):
            self.api.log.error(
                'Size mismatch (selected {} lines, got {} lines in clipboard.'
                .format(len(self.api.subs.selected_events), len(lines))
            )
            return

        with self.api.undo.capture():
            for i, sub in enumerate(self.api.subs.selected_events):
                sub.text = lines[i]


class CopySubtitlesTimesCommand(BaseCommand):
    names = ['grid/copy-subs/times']
    menu_name = 'Copy selected subtitles times to clipboard'
    help_text = 'Copies time boundaries from the subtitle selection.'

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection

    async def run(self) -> None:
        QtWidgets.QApplication.clipboard().setText('\n'.join(
            '{} - {}'.format(
                bubblesub.util.ms_to_str(line.start),
                bubblesub.util.ms_to_str(line.end)
            )
            for line in self.api.subs.selected_events
        ))


class PasteSubtitlesTimesCommand(BaseCommand):
    names = ['grid/paste-subs/times']
    menu_name = 'Paste times to selected subtitles from clipboard'
    help_text = 'Pastes time boundaries into the subtitle selection.'

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection

    async def run(self) -> None:
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            self.api.log.error('Clipboard is empty, aborting.')
            return

        lines = text.split('\n')
        if len(lines) != len(self.api.subs.selected_events):
            self.api.log.error(
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
                self.api.log.error('Invalid time format: {}'.format(line))
                return

        with self.api.undo.capture():
            for i, sub in enumerate(self.api.subs.selected_events):
                sub.start = times[i][0]
                sub.end = times[i][1]


class CopySubtitlesCommand(BaseCommand):
    names = ['grid/copy-subs']
    menu_name = 'Copy selected subtitles to clipboard'
    help_text = 'Copies the selected subtitles.'

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection

    async def run(self) -> None:
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


class PasteSubtitlesCommand(BaseCommand):
    names = ['grid/paste-subs']
    help_text = 'Pastes subtitles near the selection.'

    @property
    def menu_name(self) -> str:
        return (
            f'Paste subtitles from clipboard '
            f'({self.args.direction.name.lower()})'
        )

    async def run(self) -> None:
        if self.args.direction == VerticalDirection.Below:
            _paste_from_clipboard(self, (
                self.api.subs.selected_indexes[-1] + 1
                if self.api.subs.has_selection else 0
            ))
        elif self.args.direction == VerticalDirection.Above:
            _paste_from_clipboard(self, (
                self.api.subs.selected_indexes[0]
                if self.api.subs.has_selection else 0
            ))
        else:
            raise AssertionError

    @staticmethod
    def _decorate_parser(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-d', '--direction',
            help='direction to paste into',
            type=VerticalDirection.from_string,
            choices=list(VerticalDirection),
            default=VerticalDirection.Below
        )


class CreateAudioSampleCommand(BaseCommand):
    names = ['grid/create-audio-sample']
    menu_name = 'Create audio sample'
    help_text = (
        'Saves current subtitle selection to a WAV file. '
        'The audio starts at the first selected subtitle start and ends at '
        'the last selected subtitle end.'
    )

    @property
    def is_enabled(self) -> bool:
        return self.api.subs.has_selection \
            and self.api.media.audio.has_audio_source

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        start_pts = self.api.subs.selected_events[0].start
        end_pts = self.api.subs.selected_events[-1].end

        file_name = bubblesub.util.sanitize_file_name(
            'audio-{}-{}..{}.wav'.format(
                self.api.media.path.name,
                bubblesub.util.ms_to_str(start_pts),
                bubblesub.util.ms_to_str(end_pts)
            )
        )

        path = bubblesub.ui.util.save_dialog(
            main_window, 'Waveform Audio File (*.wav)', file_name=file_name
        )
        if path is None:
            self.api.log.info('cancelled')
        else:
            self.api.media.audio.save_wav(path, start_pts, end_pts)
            self.api.log.info(f'saved audio sample to {path}')


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    """
    Register commands in this file into the command API.

    :param cmd_api: command API
    """
    for cls in [
            JumpToSubtitleByNumberCommand,
            JumpToSubtitleByTimeCommand,
            SelectNearSubtitleCommand,
            SelectAllSubtitlesCommand,
            ClearSubtitleSelectionCommand,
            CopySubtitlesTextCommand,
            PasteSubtitlesTextCommand,
            CopySubtitlesTimesCommand,
            PasteSubtitlesTimesCommand,
            CopySubtitlesCommand,
            PasteSubtitlesCommand,
            CreateAudioSampleCommand,
    ]:
        cmd_api.register_core_command(T.cast(T.Type[BaseCommand], cls))
