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

"""Main program options."""

import collections
import typing as T
from pathlib import Path

import yaml
from PyQt5 import QtCore

from bubblesub.cfg.base import SubConfig
from bubblesub.data import ROOT_DIR


def _get_user_path(root_dir: Path) -> Path:
    return root_dir / "options.yaml"


class _OptionsConfigSignals(QtCore.QObject):
    # QObject doesn't play nice with multiple inheritance, hence composition
    changed = QtCore.pyqtSignal()


class OptionsConfig(SubConfig):
    """Main program options."""

    changed = property(lambda self: self._signals.changed)

    def __init__(self) -> None:
        """Initialize self."""
        super().__init__()
        self._storage: T.Dict[str, T.Any] = {}
        self._signals = _OptionsConfigSignals()
        self.load(None)

    def load(self, root_dir: T.Optional[Path]) -> None:
        """
        Load internals of this config from the specified directory.

        :param root_dir: directory where to look for the matching config file
        """
        self._storage = {}
        self._loads((ROOT_DIR / "options.yaml").read_text())
        if root_dir:
            user_path = _get_user_path(root_dir)
            if user_path.exists():
                try:
                    self._loads(user_path.read_text())
                except ConfigError as ex:
                    raise ConfigError(f"error loading {user_path}: {ex}")
        self.changed.emit()

    def save(self, root_dir: Path) -> None:
        """
        Save internals of this config to the specified directory.

        :param root_dir: directory where to save the matching config file
        """
        user_path = _get_user_path(root_dir)
        user_path.parent.mkdir(parents=True, exist_ok=True)
        user_path.write_text(self._dumps())

    def _loads(self, text: str) -> None:
        self._merge(self._storage, yaml.load(text, Loader=yaml.SafeLoader))

    def _merge(self, target: T.Any, source: T.Any) -> T.Any:
        for key, value in source.items():
            if isinstance(value, collections.abc.Mapping):
                target[key] = self._merge(target.get(key, {}), value)
            else:
                target[key] = value
        return target

    def _dumps(self) -> str:
        return yaml.dump(self._storage, indent=4, default_flow_style=False)

    def __getitem__(self, key: T.Any) -> T.Any:
        return self._storage[key]

    def __setitem__(self, key: T.Any, value: T.Any) -> None:
        self._storage[key] = value
