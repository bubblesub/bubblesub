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
import bubblesub.util
from bubblesub.api.cmd import BaseCommand
from bubblesub.api.cmd import CommandError
from bubblesub.api.cmd import CommandUnavailable
from bubblesub.ass.event import Event
from bubblesub.cmd.common import EventSelection
from bubblesub.cmd.common import FancyPath


def _pickle(data: T.Any) -> str:
    return (
        base64.b64encode(
            zlib.compress(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))
        ).decode()
    )


def _unpickle(text: str) -> T.Any:
    return pickle.loads(zlib.decompress(base64.b64decode(text.encode())))


class SubtitlesSelectCommand(BaseCommand):
    names = ['sub-select']
    help_text = 'Selects given subtitles.'

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


class SubtitlesCopyCommand(BaseCommand):
    names = ['sub-copy']
    help_text = 'Copies given subtitles to clipboard.'

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable('nothing to copy')

        if self.args.subject == 'text':
            QtWidgets.QApplication.clipboard().setText(
                '\n'.join(sub.text for sub in subs)
            )
        elif self.args.subject == 'times':
            QtWidgets.QApplication.clipboard().setText(
                '\n'.join(
                    '{} - {}'.format(
                        bubblesub.util.ms_to_str(sub.start),
                        bubblesub.util.ms_to_str(sub.end)
                    )
                    for sub in subs
                )
            )
        elif self.args.subject == 'all':
            QtWidgets.QApplication.clipboard().setText(_pickle(subs))
        else:
            raise AssertionError

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to paste into',
            type=lambda value: EventSelection(api, value),
            default='selected'
        )
        parser.add_argument(
            '-s', '--subject',
            help='subject to copy',
            choices=('text', 'times', 'all'),
            default='all'
        )


class SubtitlesPasteCommand(BaseCommand):
    names = ['sub-paste']
    help_text = 'Pastes subtitles from clipboard.'

    @property
    def is_enabled(self) -> bool:
        return self.args.origin.makes_sense

    async def run(self) -> None:
        indexes = await self.args.origin.get_indexes()

        if self.args.dir == 'before':
            self._paste_from_clipboard(indexes[0] if indexes else 0)
        elif self.args.dir == 'after':
            self._paste_from_clipboard(indexes[-1] + 1 if indexes else 0)
        else:
            raise AssertionError

    def _paste_from_clipboard(self, idx: int) -> None:
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            raise CommandUnavailable('clipboard is empty, aborting')

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
            '-o', '--origin',
            help='where to paste the subtitles',
            type=lambda value: EventSelection(api, value),
            default='selected',
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--before',
            dest='dir',
            action='store_const',
            const='before',
            help='paste before origin'
        )
        group.add_argument(
            '--after',
            dest='dir',
            action='store_const',
            const='after',
            help='paste after origin'
        )


class SubtitlesPasteIntoCommand(BaseCommand):
    names = ['sub-paste-into']
    help_text = 'Pastes text or times into the given subtitles.'

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            self.api.log.error('clipboard is empty, aborting')
            return

        lines = text.split('\n')
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable('nothing to paste into')

        if len(lines) != len(subs):
            raise CommandError(
                f'size mismatch ('
                f'selected {len(subs)} lines, '
                f'got {len(lines)} lines in clipboard)'
                .format(len(subs), len(lines))
            )

        with self.api.undo.capture():
            if self.args.subject == 'text':
                for line, sub in zip(lines, subs):
                    sub.text = line

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
                        raise ValueError(f'invalid time format: {line}')

                for time, sub in zip(times, subs):
                    sub.start = time[0]
                    sub.end = time[1]

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


class SaveAudioSampleCommand(BaseCommand):
    names = ['save-audio-sample']
    help_text = (
        'Saves given subtitles to a WAV file. '
        'Prompts user to choose where to save the file to if the path wasn\'t '
        'specified in the command arguments.'
    )

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense \
            and self.api.media.audio.has_audio_source

    async def run(self) -> None:
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable('nothing to sample')

        assert self.api.media.path
        path = await self.args.path.get_save_path(
            file_filter='Waveform Audio File (*.wav)',
            default_file_name='audio-{}-{}..{}.wav'.format(
                self.api.media.path.name,
                bubblesub.util.ms_to_str(subs[0].start),
                bubblesub.util.ms_to_str(subs[-1].end)
            )
        )

        pts_ranges = [(sub.start, sub.end) for sub in subs]
        self.api.media.audio.save_wav(path, pts_ranges)
        self.api.log.info(f'saved audio sample to {path}')

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to save audio from',
            type=lambda value: EventSelection(api, value),
            default='selected'
        )
        parser.add_argument(
            '-p', '--path',
            help='path to save the sample to',
            type=lambda value: FancyPath(api, value),
            default=''
        )


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    """
    Register commands in this file into the command API.

    :param cmd_api: command API
    """
    for cls in [
            SubtitlesSelectCommand,
            SubtitlesCopyCommand,
            SubtitlesPasteCommand,
            SubtitlesPasteIntoCommand,
            SaveAudioSampleCommand,
    ]:
        cmd_api.register_core_command(T.cast(T.Type[BaseCommand], cls))
