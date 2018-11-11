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
from pathlib import Path

from PyQt5 import QtWidgets

import bubblesub.ui.util
from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand, CommandCanceled
from bubblesub.cmd.common import FancyPath

VIDEO_FILE_FILTER = 'Video filters (*.avi *.mkv *.webm *.mp4);;All files (*.*)'
SUBS_FILE_FILTER = 'Advanced Substation Alpha (*.ass)'


def _get_dialog_dir(api: Api) -> T.Optional[Path]:
    if api.subs.path:
        return api.subs.path.parent
    return None


def _ask_about_unsaved_changes(api: Api) -> bool:
    if not api.undo.needs_save:
        return True
    return bubblesub.ui.util.ask(
        'There are unsaved changes. '
        'Are you sure you want to close the current file?'
    )


class NewCommand(BaseCommand):
    names = ['new']
    help_text = (
        'Opens a new file. '
        'Prompts user to save the current file if there are unsaved changes.'
    )

    async def run(self) -> None:
        if _ask_about_unsaved_changes(self.api):
            self.api.subs.unload()


class OpenCommand(BaseCommand):
    names = ['open']
    help_text = (
        'Opens an existing subtitles file. '
        'Prompts user to save the current file if there are unsaved changes. '
        'Prompts user to choose where to load the file from if the path '
        'wasn\'t specified in the command arguments.'
    )

    async def run(self) -> None:
        if not _ask_about_unsaved_changes(self.api):
            return

        path = await self.args.path.get_load_path(
            file_filter=SUBS_FILE_FILTER, directory=_get_dialog_dir(self.api)
        )

        self.api.subs.load_ass(path)
        self.api.log.info(f'opened {path}')

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-p',
            '--path',
            help='path to load the subtitles from',
            type=lambda value: FancyPath(api, value),
            default='',
        )


class LoadVideoCommand(BaseCommand):
    names = ['load-video']
    help_text = (
        'Loads a video file for audio/video playback. '
        'Prompts user to choose where to load the file from if the path '
        'wasn\'t specified in the command arguments.'
    )

    async def run(self) -> None:
        path = await self.args.path.get_load_path(
            file_filter=VIDEO_FILE_FILTER, directory=_get_dialog_dir(self.api)
        )

        self.api.media.load(path)
        self.api.log.info(f'loading {path}')

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-p',
            '--path',
            help='path to load the video from',
            type=lambda value: FancyPath(api, value),
            default='',
        )


class SaveCommand(BaseCommand):
    names = ['save']
    help_text = (
        'Saves the current subtitles to an ASS file. '
        'If the currently loaded subtitles weren\'t ever saved, prompts user '
        'to choose where to save the file to.'
    )

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        path = self.api.subs.path
        if not path:
            path = bubblesub.ui.util.save_dialog(
                main_window,
                file_filter=SUBS_FILE_FILTER,
                directory=_get_dialog_dir(self.api),
            )
            if not path:
                raise CommandCanceled

        self.api.subs.save_ass(path, remember_path=True)
        self.api.log.info(f'saved subtitles to {path}')


class SaveAsCommand(BaseCommand):
    names = ['save-as']
    help_text = (
        'Saves the current subtitles to an ASS file. '
        'Prompts user to choose where to save the file to if the path wasn\'t '
        'specified in the command arguments.'
    )

    async def run(self) -> None:
        path = await self.args.path.get_save_path(
            file_filter=SUBS_FILE_FILTER,
            directory=_get_dialog_dir(self.api),
            default_file_name=(
                self.api.subs.path.name if self.api.subs.path else None
            ),
        )

        self.api.subs.save_ass(path, remember_path=True)
        self.api.log.info(f'saved subtitles to {path}')

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '-p',
            '--path',
            help='optional path to save the subtitles to',
            type=lambda value: FancyPath(api, value),
            default='',
        )


COMMANDS = [
    NewCommand,
    OpenCommand,
    LoadVideoCommand,
    SaveCommand,
    SaveAsCommand,
]
