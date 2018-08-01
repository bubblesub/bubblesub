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
from bubblesub.cmd.common import EventSelection


def _pickle(data: T.Any) -> str:
    return (
        base64.b64encode(
            zlib.compress(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))
        ).decode()
    )


def _unpickle(text: str) -> T.Any:
    return pickle.loads(zlib.decompress(base64.b64decode(text.encode())))


class SelectSubtitlesCommand(BaseCommand):
    names = ['select-subs']
    help_text = 'Selects given subtitles.'

    @property
    def menu_name(self) -> str:
        return 'Select ' + self.args.target.description

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        self.api.subs.selected_indexes = await self.args.target.get_indexes()

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            'target',
            help='subtitles to select',
            type=lambda value: EventSelection(api, value)
        )


class CopySubtitlesCommand(BaseCommand):
    names = ['copy-subs']
    help_text = 'Copies given subtitles to clipboard.'

    @property
    def menu_name(self):
        target_desc = self.args.target.description
        if self.args.subject == 'text':
            return f'Copy {target_desc} text to clipboard'
        if self.args.subject == 'times':
            return f'Copy {target_desc} times to clipboard'
        if self.args.subject == 'all':
            return f'Copy {target_desc} to clipboard'
        raise AssertionError

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        if self.args.subject == 'text':
            QtWidgets.QApplication.clipboard().setText('\n'.join(
                event.text for event in await self.args.target.get_subtitles()
            ))
        elif self.args.subject == 'times':
            QtWidgets.QApplication.clipboard().setText('\n'.join(
                '{} - {}'.format(
                    bubblesub.util.ms_to_str(event.start),
                    bubblesub.util.ms_to_str(event.end)
                )
                for event in await self.args.target.get_subtitles()
            ))
        elif self.args.subject == 'all':
            QtWidgets.QApplication.clipboard().setText(
                _pickle(await self.args.target.get_subtitles())
            )
        else:
            raise AssertionError

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to select',
            type=lambda value: EventSelection(api, value),
            default='selected'
        )
        parser.add_argument(
            '-s', '--subject',
            help='subject to copy',
            choices=('text', 'times', 'all'),
            default='all'
        )


class PasteSubtitlesCommand(BaseCommand):
    names = ['paste-subs']
    help_text = 'Pastes subtitles from clipboard.'

    @property
    def menu_name(self) -> str:
        direction = 'before' if self.args.before else 'after'
        return f'Paste subtitles from clipboard ({direction})'

    async def run(self) -> None:
        indexes = await self.args.target.get_indexes()

        if self.args.before:
            self._paste_from_clipboard(indexes[0] if indexes else 0)
        else:
            self._paste_from_clipboard(indexes[-1] + 1 if indexes else 0)

    def _paste_from_clipboard(self, idx: int) -> None:
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            self.api.log.error('Clipboard is empty, aborting.')
            return
        items = T.cast(T.List[Event], _unpickle(text))
        with self.api.undo.capture():
            self.api.subs.events.insert(idx, items)
            self.api.subs.selected_indexes = list(range(idx, idx + len(items)))

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='where to paste the subtitles',
            type=lambda value: EventSelection(api, value)
        )

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '--before',
            action='store_true',
            help='paste before target'
        )
        group.add_argument(
            '--after',
            action='store_false', dest='before',
            help='paste after target'
        )


class PasteIntoSubtitlesCommand(BaseCommand):
    names = ['paste-into-subs']
    help_text = 'Pastes text or times into the given subtitles.'

    @property
    def menu_name(self) -> str:
        target_desc = self.args.target.description
        return f'Paste {self.args.subject} to {target_desc} from clipboard'

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            self.api.log.error('Clipboard is empty, aborting.')
            return

        lines = text.split('\n')
        events = await self.args.target.get_subtitles()
        if len(lines) != len(events):
            self.api.log.error(
                'Size mismatch (selected {} lines, got {} lines in clipboard.'
                .format(len(events), len(lines))
            )
            return

        with self.api.undo.capture():
            if self.args.subject == 'text':
                for i, event in enumerate(events):
                    event.text = lines[i]

            elif self.args.subject == 'times':
                times: T.List[T.Tuple[int, int]] = []
                for line in lines:
                    try:
                        start, end = line.split('-', 1)
                        times.append((
                            bubblesub.util.str_to_ms(start.strip()),
                            bubblesub.util.str_to_ms(end.strip())
                        ))
                    except ValueError:
                        raise ValueError(f'Invalid time format: {line}')

                for i, event in enumerate(events):
                    event.start = times[i][0]
                    event.end = times[i][1]

            else:
                raise AssertionError

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to paste the subject into',
            type=lambda value: EventSelection(api, value),
            default='selected'
        )
        parser.add_argument(
            '-s', '--subject',
            help='subject to copy',
            choices=('text', 'times'),
            required=True,
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
            SelectSubtitlesCommand,
            CopySubtitlesCommand,
            PasteSubtitlesCommand,
            PasteIntoSubtitlesCommand,
            CreateAudioSampleCommand,
    ]:
        cmd_api.register_core_command(T.cast(T.Type[BaseCommand], cls))
