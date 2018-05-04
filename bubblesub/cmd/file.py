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


async def _get_save_file_name(
        api: bubblesub.api.Api,
        main_window: QtWidgets.QMainWindow,
        file_filter: str
) -> T.Optional[Path]:
    return bubblesub.ui.util.save_dialog(
        main_window, file_filter, directory=_get_dialog_dir(api)
    )


async def _get_load_file_name(
        api: bubblesub.api.Api,
        main_window: QtWidgets.QMainWindow,
        file_filter: str
) -> T.Optional[Path]:
    return bubblesub.ui.util.load_dialog(
        main_window, file_filter, directory=_get_dialog_dir(api)
    )


def _ask_about_unsaved_changes(api: bubblesub.api.Api) -> bool:
    if not api.undo.needs_save:
        return True
    return bubblesub.ui.util.ask(
        'There are unsaved changes. '
        'Are you sure you want to close the current file?'
    )


class NewFileCommand(BaseCommand):
    """
    Opens a new file.

    Prompts user to save the current file if there are unsaved changes.
    """

    name = 'file/new'
    menu_name = '&New'

    async def run(self) -> None:
        """Carry out the command."""
        if _ask_about_unsaved_changes(self.api):
            self.api.subs.unload()


class OpenFileCommand(BaseCommand):
    """
    Opens an existing subtitles file.

    Prompts user to save the current file if there are unsaved changes.
    Prompts user to choose where to load the file from if the path wasn't
    specified in the command arguments.
    """

    name = 'file/open'
    menu_name = '&Open'

    def __init__(
            self,
            api: bubblesub.api.Api,
            path: T.Optional[Path] = None
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param path: optional path to load the subtitles from
        """
        super().__init__(api)
        self._path = path

    async def run(self) -> None:
        """Carry out the command."""
        if _ask_about_unsaved_changes(self.api):
            if self._path:
                path = self._path
            else:
                path = await self.api.gui.exec(
                    _get_load_file_name, SUBS_FILE_FILTER
                )
            if not path:
                self.info('opening cancelled.')
            else:
                self.api.subs.load_ass(path)
                self.info('opened {}'.format(path))


class LoadVideoCommand(BaseCommand):
    """
    Loads a video file for the audio/video playback.

    Prompts user to choose where to load the file from if the path wasn't
    specified in the command arguments.
    """

    name = 'file/load-video'
    menu_name = '&Load video'

    def __init__(
            self,
            api: bubblesub.api.Api,
            path: T.Optional[Path] = None
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param path: optional path to load the video from
        """
        super().__init__(api)
        self._path = path

    async def run(self) -> None:
        """Carry out the command."""
        if self._path:
            path = self._path
        else:
            path = await self.api.gui.exec(
                _get_load_file_name, VIDEO_FILE_FILTER
            )
        if not path:
            self.info('loading video cancelled.')
        else:
            self.api.media.load(path)
            self.info('loading {}'.format(path))


class SaveFileCommand(BaseCommand):
    """
    Saves the current subtitles to an ASS file.

    If the currently loaded subtitles weren't ever saved, prompts user to
    choose where to save the file to.
    """

    name = 'file/save'
    menu_name = '&Save'

    async def run(self) -> None:
        """Carry out the command."""
        path = self.api.subs.path
        if not path:
            path = await self.api.gui.exec(
                _get_save_file_name, SUBS_FILE_FILTER
            )
        if not path:
            self.info('saving cancelled.')
            return
        self.api.subs.save_ass(path, remember_path=True)
        self.info('saved subtitles to {}'.format(path))


class SaveFileAsCommand(BaseCommand):
    """
    Saves the current subtitles to an ASS file.

    Prompts user to choose where to save the file to if the path wasn't
    specified in the command arguments.
    """

    name = 'file/save-as'
    menu_name = '&Save as'

    def __init__(
            self,
            api: bubblesub.api.Api,
            path: T.Optional[Path] = None
    ) -> None:
        """
        Initialize self.

        :param api: core API
        :param path: optional path to save the subtitles to
        """
        super().__init__(api)
        self._path = path

    async def run(self) -> None:
        """Carry out the command."""
        if self._path:
            path = self._path
        else:
            path = await self.api.gui.exec(
                _get_save_file_name, SUBS_FILE_FILTER
            )
        if not path:
            self.info('saving cancelled.')
        else:
            self.api.subs.save_ass(path, remember_path=True)
            self.info('saved subtitles to {}'.format(path))


class QuitCommand(BaseCommand):
    """
    Quits the application.

    Prompts user to save the current file if there are unsaved changes.
    """

    name = 'file/quit'
    menu_name = '&Quit'

    async def run(self) -> None:
        """Carry out the command."""
        self.api.gui.quit()


def register(cmd_api: bubblesub.api.cmd.CommandApi) -> None:
    """
    Register commands in this file into the command API.

    :param cmd_api: command API
    """
    for cls in [
            NewFileCommand,
            OpenFileCommand,
            LoadVideoCommand,
            SaveFileCommand,
            SaveFileAsCommand,
            QuitCommand,
    ]:
        cmd_api.register_core_command(cls)
