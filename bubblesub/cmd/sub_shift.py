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

import argparse
import typing as T

from PyQt5 import QtWidgets

import bubblesub.ui.util
from bubblesub.api.cmd import BaseCommand
from bubblesub.api.cmd import CommandCanceled
from bubblesub.api.cmd import CommandUnavailable
from bubblesub.ass.event import Event
from bubblesub.cmd.common import EventSelection
from bubblesub.cmd.common import RelativePts


class SubtitlesShiftCommand(BaseCommand):
    names = ['sub-shift']
    help_text = 'Shifts given subtitles.'

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable('nothing to update')

        delta = await self._get_delta(subs, main_window)

        with self.api.undo.capture():
            for sub in subs:
                start = sub.start
                end = sub.end

                if self.args.method in {'start', 'both'}:
                    start = await delta.apply(
                        start, align_to_near_frame=not self.args.no_align
                    )

                if self.args.method in {'end', 'both'}:
                    end = await delta.apply(
                        end, align_to_near_frame=not self.args.no_align
                    )

                sub.begin_update()
                sub.start = start
                sub.end = end
                sub.end_update()

    async def _get_delta(
            self,
            subs: T.List[Event],
            main_window: QtWidgets.QMainWindow
    ) -> RelativePts:
        if self.args.delta:
            return self.args.delta
        if self.args.gui:
            ret = bubblesub.ui.util.time_jump_dialog(
                main_window,
                absolute_label='Time to move to:',
                relative_label='Time to add:',
                relative_checked=True
            )
            if ret is None:
                raise CommandCanceled

            delta, is_relative = ret
            if not is_relative and subs:
                delta -= subs[0].start

            return RelativePts(self.api, str(delta) + 'ms')
        raise AssertionError

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            '-t', '--target',
            help='subtitles to shift',
            type=lambda value: EventSelection(api, value),
            default='selected'
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '-g', '--gui',
            action='store_true',
            help='prompt user for shift amount with a GUI dialog'
        )
        group.add_argument(
            '-d', '--delta',
            help='amount to shift the subtitles by',
            type=lambda value: RelativePts(api, value),
        )

        parser.add_argument(
            '--no-align',
            help='don\'t realign subtitles to video frames',
            action='store_true'
        )

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '--start',
            action='store_const',
            dest='method',
            const='start',
            help='shift subtitles start',
            default='both'
        )
        group.add_argument(
            '--end',
            action='store_const',
            dest='method',
            const='end',
            help='shift subtitles end'
        )
        group.add_argument(
            '--both',
            action='store_const',
            dest='method',
            const='both',
            help='shift whole subtitles'
        )


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    cmd_api.register_core_command(SubtitlesShiftCommand)
