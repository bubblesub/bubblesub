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

"""Caching utilities."""

import pickle
import typing as T
from pathlib import Path

import xdg

CACHE_SUFFIX = ".dat"


def get_cache_dir() -> Path:
    """
    Return path to cache files.

    :return: path to cache files
    """
    return Path(xdg.XDG_CACHE_HOME) / "bubblesub"


def get_cache_file_path(cache_name: str) -> Path:
    """
    Translate cache file name into full path.

    :param cache_name: name of cache file
    :return: full cache file path
    """
    return get_cache_dir() / (cache_name + CACHE_SUFFIX)


def load_cache(cache_name: str) -> T.Any:
    """
    Load cached object from disk.

    :param cache_name: name of cache file
    :return: persisted object
    """
    cache_path = get_cache_file_path(cache_name)
    if cache_path.exists():
        with cache_path.open(mode="rb") as handle:
            try:
                return pickle.load(handle)
            except EOFError:
                return None
    return None


def save_cache(cache_name: str, data: T.Any) -> None:
    """
    Save object to disk cache.

    :param cache_name: name of cache file
    :param data: object to persist
    """
    cache_path = get_cache_file_path(cache_name)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open(mode="wb") as handle:
        pickle.dump(data, handle)


def wipe_cache() -> None:
    """Delete disk cache."""
    for path in get_cache_dir().iterdir():
        if path.suffix == CACHE_SUFFIX:
            path.unlink()
