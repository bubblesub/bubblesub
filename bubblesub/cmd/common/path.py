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

"""Path object that's capable of prompting user with load/save dialogs."""

from pathlib import Path
from typing import Any, Optional

from bubblesub.api import Api
from bubblesub.api.cmd import CommandCanceled, CommandUnavailable
from bubblesub.ui.util import load_dialog, save_dialog
from bubblesub.util import sanitize_file_name


class FancyPath:
    def __init__(self, api: Api, value: str) -> None:
        self.api = api
        self.value = value

    async def get_load_path(
        self,
        file_filter: Optional[str] = None,
    ) -> Path:
        if self.value:
            path = Path(self.value).expanduser()
            if not path.exists():
                raise CommandUnavailable(f'file "{path}" does not exist')
            return path

        path = await self.api.gui.exec(
            self._show_load_dialog,
            file_filter=file_filter,
            directory=self.api.gui.get_dialog_dir(),
        )
        if path:
            self.api.gui.last_directory = path.parent
            return path

        raise CommandCanceled

    async def get_save_path(
        self,
        file_filter: Optional[str] = None,
        directory: Optional[Path] = None,
        default_file_name: Optional[str] = None,
    ) -> Path:
        if self.value:
            return Path(self.value).expanduser()

        path = await self.api.gui.exec(
            self._show_save_dialog,
            file_filter=file_filter,
            directory=directory,
            file_name=(
                None
                if default_file_name is None
                else sanitize_file_name(default_file_name)
            ),
        )
        if path:
            return path

        raise CommandCanceled

    async def _show_load_dialog(
        self, *args: Any, **kwargs: Any
    ) -> Optional[Path]:
        return await load_dialog(*args, **kwargs)

    async def _show_save_dialog(
        self, *args: Any, **kwargs: Any
    ) -> Optional[Path]:
        return await save_dialog(*args, **kwargs)
