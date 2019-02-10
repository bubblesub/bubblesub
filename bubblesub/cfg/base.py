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

from bubblesub.data import ROOT_DIR


class ConfigError(RuntimeError):
    pass


class SubConfig(abc.ABC):
    """Base config."""

    def __init__(self) -> None:
        """Initialize self."""
        self.reset()

    @property
    @abc.abstractmethod
    def file_name(self) -> str:
        """Config file name."""
        raise NotImplementedError("not implemented")

    def reset(self) -> None:
        """Reset to factory defaults."""
        self._clear()
        self.load(ROOT_DIR)

    def load(self, root_dir: Path) -> None:
        """
        Load internals of this config from the specified directory.

        :param root_dir: directory where to look for the matching config file
        """
        full_path = root_dir / self.file_name
        if full_path.exists():
            try:
                self._loads(full_path.read_text())
            except ConfigError as ex:
                raise ConfigError(f"error loading {full_path}: {ex}")

    def save(self, root_dir: Path) -> None:
        full_path = root_dir / self.file_name
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(self._dumps())

    @abc.abstractmethod
    def _clear(self) -> None:
        """Reset to blank state."""
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def _loads(self, text: str) -> None:
        """
        Load internals from a human readable representation.

        :param text: INI, JSON, etc.
        """
        raise NotImplementedError("not implemented")

    # doesn't have to be overridden
    def _dumps(self) -> str:
        """
        Save internals to a human readable representation.

        :return: INI, JSON, etc.
        """
        raise NotImplementedError("not implemented")
