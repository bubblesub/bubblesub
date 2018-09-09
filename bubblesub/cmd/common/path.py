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

import typing as T
from pathlib import Path

import bubblesub.api
import bubblesub.util
import bubblesub.ui.util
from bubblesub.api.cmd import CommandCanceled
from bubblesub.api.cmd import CommandUnavailable


class FancyPath:
    def __init__(self, api: bubblesub.api.Api, value: str) -> None:
        self.api = api
        self.value = value

    async def get_save_path(
            self,
            file_filter: T.Optional[str] = None,
            default_file_name: T.Optional[str] = None
    ) -> Path:
        if self.value == 'ask':
            self.value = await self.api.gui.exec(
                self._show_dialog,
                file_filter=file_filter,
                file_name=bubblesub.util.sanitize_file_name(default_file_name)
            )
            if self.value is None:
                raise CommandCanceled

        if not self.value:
            raise CommandUnavailable

        return Path(self.value).expanduser()

    async def _show_dialog(self, *args, **kwargs) -> T.Optional[Path]:
        return bubblesub.ui.util.save_dialog(*args, **kwargs)
