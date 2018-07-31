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

"""Commands related to files."""

import argparse
import typing as T
from pathlib import Path

from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ui.util
from bubblesub.api.cmd import BaseCommand

VIDEO_FILE_FILTER = 'Video filters (*.avi *.mkv *.webm *.mp4);;All files (*.*)'
SUBS_FILE_FILTER = 'Advanced Substation Alpha (*.ass)'


def _get_dialog_dir(api: bubblesub.api.Api) -> T.Optional[Path]:
    if api.subs.path:
        return api.subs.path.parent
    return None


def _ask_about_unsaved_changes(api: bubblesub.api.Api) -> bool:
    if not api.undo.needs_save:
        return True
    return bubblesub.ui.util.ask(
        'There are unsaved changes. '
        'Are you sure you want to close the current file?'
    )


class NewCommand(BaseCommand):
    names = ['new']
    menu_name = '&New'
    help_text = (
        'Opens a new file. '
        'Prompts user to save the current file if there are unsaved changes.'
    )

    async def run(self) -> None:
        if _ask_about_unsaved_changes(self.api):
            self.api.subs.unload()


class OpenCommand(BaseCommand):
    names = ['open']
    menu_name = '&Open'
    help_text = (
        'Opens an existing subtitles file. '
        'Prompts user to save the current file if there are unsaved changes. '
        'Prompts user to choose where to load the file from if the path '
        'wasn\'t specified in the command arguments.'
    )

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        if _ask_about_unsaved_changes(self.api):
            if self.args.path:
                path = self.args.path
            else:
                path = bubblesub.ui.util.load_dialog(
                    main_window,
                    SUBS_FILE_FILTER,
                    directory=_get_dialog_dir(self.api)
                )
            if not path:
                self.api.log.info('cancelled')
            else:
                self.api.subs.load_ass(path)
                self.api.log.info(f'opened {path}')

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            'path',
            help='path to load the subtitles from',
            type=Path,
            nargs='?'
        )


class LoadVideoCommand(BaseCommand):
    names = ['load-video']
    menu_name = '&Load video'
    help_text = (
        'Loads a video file for the audio/video playback. '
        'Prompts user to choose where to load the file from if the path '
        'wasn\'t specified in the command arguments.'
    )

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        if self.args.path:
            path = self.args.path
        else:
            path = bubblesub.ui.util.load_dialog(
                main_window,
                VIDEO_FILE_FILTER,
                directory=_get_dialog_dir(self.api)
            )
        if not path:
            self.api.log.info('cancelled')
        else:
            self.api.media.load(path)
            self.api.log.info(f'loading {path}')

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            'path',
            help='optional path to load the video from',
            type=Path,
            nargs='?'
        )


class SaveCommand(BaseCommand):
    names = ['save']
    menu_name = '&Save'
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
                SUBS_FILE_FILTER,
                directory=_get_dialog_dir(self.api)
            )
        if not path:
            self.api.log.info('cancelled')
            return
        self.api.subs.save_ass(path, remember_path=True)
        self.api.log.info(f'saved subtitles to {path}')


class SaveAsCommand(BaseCommand):
    names = ['save-as']
    menu_name = '&Save as'
    help_text = (
        'Saves the current subtitles to an ASS file. '
        'Prompts user to choose where to save the file to if the path wasn\'t '
        'specified in the command arguments.'
    )

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QtWidgets.QMainWindow) -> None:
        if self.args.path:
            path = self.args.path
        else:
            path = bubblesub.ui.util.save_dialog(
                main_window,
                SUBS_FILE_FILTER,
                directory=_get_dialog_dir(self.api)
            )
        if not path:
            self.api.log.info('cancelled')
        else:
            self.api.subs.save_ass(path, remember_path=True)
            self.api.log.info(f'saved subtitles to {path}')

    @staticmethod
    def _decorate_parser(
            api: bubblesub.api.Api,
            parser: argparse.ArgumentParser
    ) -> None:
        parser.add_argument(
            'path',
            help='optional path to save the subtitles to',
            type=Path,
            nargs='?'
        )


class QuitCommand(BaseCommand):
    names = ['quit']
    menu_name = '&Quit'
    help_text = (
        'Quits the application. '
        'Prompts user to save the current file if there are unsaved changes.'
    )

    async def run(self) -> None:
        self.api.gui.quit()


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    """
    Register commands in this file into the command API.

    :param cmd_api: command API
    """
    for cls in [
            NewCommand,
            OpenCommand,
            LoadVideoCommand,
            SaveCommand,
            SaveAsCommand,
            QuitCommand,
    ]:
        cmd_api.register_core_command(T.cast(T.Type[BaseCommand], cls))
