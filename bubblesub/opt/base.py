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

"""Base config."""

import abc
from pathlib import Path


class BaseConfig(abc.ABC):
    """Base config."""

    @property
    @abc.abstractmethod
    def file_name(self) -> str:
        """Config file name."""
        raise NotImplementedError('Not implemented')

    @abc.abstractmethod
    def loads(self, text: str) -> None:
        """
        Load internals from a human readable representation.

        :param text: INI, JSON, etc.
        """
        raise NotImplementedError('Not implemented')

    @abc.abstractmethod
    def dumps(self) -> str:
        """
        Serialize internals to a human readable representation.

        :return: INI, JSON etc.
        """
        raise NotImplementedError('Not implemented')

    def load(self, root_dir: Path) -> None:
        """
        Load internals of this config from the specified directory.

        :param root_dir: directory where to look for the matching config file
        """
        full_path = root_dir / self.file_name
        if full_path.exists():
            self.loads(full_path.read_text())

    def save(self, root_dir: Path) -> None:
        """
        Save internals of this config to a specified directory.

        :param root_dir: directory where to look for the matching config file
        """
        full_path = root_dir / self.file_name
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(self.dumps())
