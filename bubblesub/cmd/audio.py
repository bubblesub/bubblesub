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

"""Commands related to audio and audio selection."""

import argparse
import typing as T

import bubblesub.api
from bubblesub.api.cmd import BaseCommand
from bubblesub.cmd.common import EventSelection
from bubblesub.cmd.common import RelativePts


class SpectrogramScrollCommand(BaseCommand):
    names = ['spectrogram-scroll']
    help_text = (
        'Scrolls the spectrogram horizontally by its width\'s percentage.'
    )

    @property
    def menu_name(self) -> str:
        direction = 'forward' if self.args.delta > 0 else 'backward'
        return f'&Scroll spectrogram {direction} by {self.args.delta*100}%'

    async def run(self) -> None:
        distance = int(self.args.delta * self.api.media.audio.view_size)
        self.api.media.audio.move_view(distance)

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-d', '--delta',
            help='factor to shift the view by',
            type=float,
            required=True
        )


class SpectrogramZoomCommand(BaseCommand):
    names = ['spectrogram-zoom']
    help_text = 'Zooms the spectrogram in or out by the specified factor.'

    @property
    def menu_name(self) -> str:
        return '&Zoom spectrogram %s' % ['in', 'out'][self.args.delta > 1]

    async def run(self) -> None:
        mouse_x = 0.5
        cur_factor = self.api.media.audio.view_size / self.api.media.audio.size
        new_factor = cur_factor * self.args.delta
        self.api.media.audio.zoom_view(new_factor, mouse_x)

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-d', '--delta',
            help='factor to zoom the view by',
            type=float,
            required=True
        )


class PlaceSpectrogramSelectionAtCurrentVideoFrameCommand(BaseCommand):
    names = ['audio/place-sel-at-current-video-frame']
    menu_name = '&Place selection at current video frame'
    help_text = (
        'Realigns the selection to the current video frame. '
        'The selection start is placed at the current video frame '
        'and the selection size is set to the default subtitle duration.'
    )

    @property
    def is_enabled(self) -> bool:
        return self.api.media.audio.has_selection \
            and self.api.subs.has_selection

    async def run(self) -> None:
        self.api.media.audio.select(
            self.api.media.video.align_pts_to_near_frame(
                self.api.media.current_pts
            ),
            self.api.media.video.align_pts_to_near_frame(
                self.api.media.current_pts
                + self.api.opt.general.subs.default_duration
            )
        )


class SpectrogramShiftSelectionCommand(BaseCommand):
    names = ['spectrogram-shift-sel', 'spectrogram-shift-selection']
    help_text = 'Shfits the spectrogram selection.'

    @property
    def menu_name(self) -> str:
        if self.args.method == 'start':
            target = 'selection start'
        elif self.args.method == 'end':
            target = 'selection end'
        else:
            target = 'selection'
        return f'&Shift {target} to {self.args.delta.description}'

    async def run(self) -> None:
        with self.api.undo.capture():
            start = self.api.media.audio.selection_start
            end = self.api.media.audio.selection_end

            if self.args.method in {'start', 'both'}:
                start = await self.args.delta.apply(start)

            if self.args.method in {'end', 'both'}:
                end = await self.args.delta.apply(end)

            self.api.media.audio.select(start, end)

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-d', '--delta',
            help='amount to shift the selection',
            type=lambda value: RelativePts(api, value),
            default='selected'
        )

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '--start',
            action='store_const',
            dest='method',
            const='start',
            help='shift selection start'
        )
        group.add_argument(
            '--end',
            action='store_const',
            dest='method',
            const='end',
            help='shift selection end'
        )
        group.add_argument(
            '--both',
            action='store_const',
            dest='method',
            const='both',
            help='shift whole selection'
        )


class SpectrogramCommitSelectionCommand(BaseCommand):
    names = ['spectrogram-commit-sel', 'spectrogram-commit-selection']
    help_text = (
        'Commits the spectrogram selection into given subtitles. '
        'The subtitles start and end times are synced to the '
        'current spectrogram selection boundaries.'
    )

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    @property
    def menu_name(self) -> str:
        return '&Commit selection to ' + self.args.target.description

    async def run(self) -> None:
        with self.api.undo.capture():
            target_subtitles = await self.args.target.get_subtitles()
            for sub in target_subtitles:
                sub.begin_update()
                sub.start = self.api.media.audio.selection_start
                sub.end = self.api.media.audio.selection_end
                sub.end_update()

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to commit selection into',
            type=lambda value: EventSelection(api, value),
            default='selected'
        )


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    """
    Register commands in this file into the command API.

    :param cmd_api: command API
    """
    for cls in [
            SpectrogramScrollCommand,
            SpectrogramZoomCommand,
            PlaceSpectrogramSelectionAtCurrentVideoFrameCommand,
            SpectrogramShiftSelectionCommand,
            SpectrogramCommitSelectionCommand,
    ]:
        cmd_api.register_core_command(T.cast(T.Type[BaseCommand], cls))
