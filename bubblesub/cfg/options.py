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

from bubblesub.cfg.base import ConfigError, SubConfig


class OptionsConfig(SubConfig):
    """Main program options."""

    file_name = "options.yaml"

    def __init__(self) -> None:
        """Initialize self."""
        self._storage: T.Dict[str, T.Any] = {}
        super().__init__()

    def _clear(self) -> None:
        self._storage = {}

    def _loads(self, text: str) -> None:
        self._merge(self._storage, yaml.load(text))

    def _merge(self, target: T.Any, source: T.Any) -> T.Any:
        for k, v in source.items():
            if isinstance(v, collections.Mapping):
                target[k] = self._merge(target.get(k, {}), v)
            else:
                target[k] = v
        return target

    def _dumps(self) -> str:
        return yaml.dump(self._storage, indent=4, default_flow_style=False)

    def __getitem__(self, key: T.Any) -> T.Any:
        return self._storage[key]

    def __setitem__(self, key: T.Any, value: T.Any) -> None:
        self._storage[key] = value
