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

"""Paths to program data and user data."""

import os
from pathlib import Path


def _path_from_env(variable: str, default: Path) -> Path:
    value = os.environ.get(variable)
    if value:
        return Path(value)
    return default


ROOT_DIR = Path(__file__).parent / "data"
USER_HOME = Path(os.path.expandvars("$HOME"))
USER_CONFIG_DIR = _path_from_env("XDG_CONFIG_HOME", USER_HOME / ".config")
USER_CACHE_DIR = _path_from_env("XDG_CACHE_HOME", USER_HOME / ".cache")
