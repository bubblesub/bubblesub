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

"""Commands related to video and playback."""

import argparse
import typing as T
from pathlib import Path

from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ui.util
from bubblesub.api.cmd import BaseCommand
from bubblesub.api.cmd import CommandCanceled
from bubblesub.api.cmd import CommandUnavailable
from bubblesub.cmd.common import BooleanOperation
from bubblesub.cmd.common import EventSelection
from bubblesub.cmd.common import FancyPath
from bubblesub.cmd.common import RelativePts


class PlaySubtitleCommand(BaseCommand):
    names = ['play-sub', 'play-subtitle']
    help_text = 'Plays given subtitle.'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded and self.args.target.makes_sense

    async def run(self) -> None:
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable('nothing to play')

        start = min(sub.start for sub in subs)
        end = max(sub.end for sub in subs)
        self.api.media.play(start, end)

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitle to play',
            type=lambda value: EventSelection(api, value),
            default='selected'
        )


class PlayAudioSelectionCommand(BaseCommand):
    names = [
        'play-audio-sel',
        'play-audio-selection',
        'play-spectrogram-sel',
        'play-spectrogram-selection'
    ]
    help_text = 'Plays a region near the current spectrogram selection.'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded \
            and self.api.media.audio.has_selection

    async def run(self) -> None:
        start = self.api.media.audio.selection_start
        end = self.api.media.audio.selection_end

        if self.args.method == 'start':
            end = start
        elif self.args.method == 'end':
            start = end
        elif self.args.method != 'both':
            raise AssertionError

        if self.args.delta_start:
            start = await self.args.delta_start.apply(start)
        if self.args.delta_end:
            end = await self.args.delta_end.apply(end)

        self.api.media.play(start, end)

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-ds', '--delta-start',
            help='delta relative to the selection start',
            type=lambda value: RelativePts(api, value)
        )
        parser.add_argument(
            '-de', '--delta-end',
            help='delta relative to the selection end',
            type=lambda value: RelativePts(api, value)
        )

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '--start',
            action='store_const',
            dest='method',
            const='start',
            help='play around selection start',
            default='both'
        )
        group.add_argument(
            '--end',
            action='store_const',
            dest='method',
            const='end',
            help='play around selection end'
        )
        group.add_argument(
            '--both',
            action='store_const',
            dest='method',
            const='both',
            help='play around whole selection'
        )


class SeekCommand(BaseCommand):
    names = ['seek']
    help_text = 'Changes the video playback position to desired place.'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded

    async def run(self) -> None:
        pts = self.api.media.current_pts
        pts = await self.args.delta.apply(pts, align_to_near_frame=True)
        self.api.media.seek(pts, self.args.precise)
        self.api.media.is_paused = True

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-d', '--delta',
            help='amount to shift the selection',
            type=lambda value: RelativePts(api, value),
            required=True,
        )
        parser.add_argument(
            '-p', '--precise',
            help=(
                'whether to use precise seeking at the expense of performance'
            ),
            action='store_true'
        )


class SetPlaybackSpeedCommand(BaseCommand):
    names = ['set-playback-speed']
    help_text = 'Adjusts the video playback speed.'

    async def run(self) -> None:
        new_value = bubblesub.util.eval_expr(
            self.args.expression.format(self.api.media.playback_speed)
        )
        assert isinstance(new_value, type(self.api.media.playback_speed))
        self.api.media.playback_speed = new_value

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            'expression',
            help='expression to calculate new playback speed',
            type=str
        )


class SetVolumeCommand(BaseCommand):
    names = ['set-volume']
    help_text = 'Adjusts the video volume.'

    async def run(self) -> None:
        new_value = bubblesub.util.eval_expr(
            self.args.expression.format(self.api.media.volume)
        )
        assert isinstance(new_value, type(self.api.media.volume))
        self.api.media.volume = new_value

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            'expression',
            help='expression to calculate new volume',
            type=str
        )


class MuteCommand(BaseCommand):
    names = ['mute']
    help_text = 'Mutes or unmutes the video audio.'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded

    async def run(self) -> None:
        self.api.media.mute = self.args.operation.apply(self.api.media.mute)

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            'operation',
            help='whether to mute the audio',
            type=BooleanOperation
        )


class PauseCommand(BaseCommand):
    names = ['pause']
    help_text = 'Pauses or unpauses the video playback.'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded

    async def run(self) -> None:
        self.api.media.is_paused = (
            self.args.operation.apply(self.api.media.is_paused)
        )

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            'operation',
            help='whether to pause the video',
            type=BooleanOperation
        )


class SaveScreenshotCommand(BaseCommand):
    names = ['save-screenshot']
    help_text = 'Makes a screenshot of the current video frame.'

    @property
    def is_enabled(self) -> bool:
        return self.api.media.is_loaded

    async def run(self) -> None:
        assert self.api.media.path
        path = await self.args.path.get_save_path(
            file_filter='Portable Network Graphics (*.png)',
            default_file_name='shot-{}-{}.png'.format(
                self.api.media.path.name,
                bubblesub.util.ms_to_str(self.api.media.current_pts)
            )
        )

        self.api.media.video.screenshot(path, self.args.include_subs)
        self.api.log.info(f'saved screenshot to {path}')

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-p', '--path',
            help='path to save the screenshot to',
            type=lambda value: FancyPath(api, value),
            default='ask'
        )
        parser.add_argument(
            '-i', '--include-subs',
            help='whether to "burn" the subtitles into the screenshot',
            action='store_true'
        )


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    """
    Register commands in this file into the command API.

    :param cmd_api: command API
    """
    for cls in [
            PlaySubtitleCommand,
            PlayAudioSelectionCommand,
            SeekCommand,
            SetPlaybackSpeedCommand,
            SetVolumeCommand,
            MuteCommand,
            PauseCommand,
            SaveScreenshotCommand,
    ]:
        cmd_api.register_core_command(T.cast(T.Type[BaseCommand], cls))
