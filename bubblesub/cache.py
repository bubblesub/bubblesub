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

import functools
import pickle
import typing as T

from pathlib import Path

import xdg

CACHE_SUFFIX = '.dat'


def get_cache_dir() -> Path:
    """
    Return path to cache files.

    :return: path to cache files
    """
    return Path(xdg.XDG_CACHE_HOME) / 'bubblesub'


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
        with cache_path.open(mode='rb') as handle:
            return pickle.load(handle)
    return None


def save_cache(cache_name: str, data: T.Any) -> None:
    """
    Save object to disk cache.

    :param cache_name: name of cache file
    :param data: object to persist
    """
    cache_path = get_cache_file_path(cache_name)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open(mode='wb') as handle:
        pickle.dump(data, handle)


def wipe_cache() -> None:
    """Delete disk cache."""
    for path in get_cache_dir().iterdir():
        if path.suffix == CACHE_SUFFIX:
            path.unlink()


class Memoize:
    """
    Simple function memoization.

    Its advantage over functools.lru_cache boils down to the ability
    of removing single items from the cache.
    """

    def __init__(self, func: T.Callable[..., T.Any]) -> None:
        """
        Initialize self.

        :param func: function to cache the results for
        """
        self._func = func
        self._cache: T.Dict = {}

    def __get__(self, obj: T.Any, objtype: T.Any = None) -> T.Callable:
        """
        Support instance methods.

        :param obj: object instance
        :param objtype: object type
        :return: instance-bound callback or free function
        """
        func = functools.partial(self.__call__, obj)
        setattr(func, 'wipe_cache', self._wipe_cache)
        setattr(func, 'wipe_cache_at', self._wipe_cache_at)
        return func

    def __call__(self, *args: T.Any, **kwargs: T.Any) -> T.Any:
        """
        Try to get the result from cache; call underlying function if failed.

        :param args: arguments for the underlying function
        :param kwargs: keyword arguments for the underlying function
        :return: function result
        """
        cache_key = self._get_cache_key(*args[1:], **kwargs)
        if cache_key not in self._cache:
            self._cache[cache_key] = self._func(*args, **kwargs)
        return self._cache[cache_key]

    def _wipe_cache(self) -> None:
        """Wipe entire cache."""
        self._cache = {}

    def _wipe_cache_at(self, *args: T.Any, **kwargs: T.Any) -> None:
        """
        Delete key from cache.

        :param args: cached function arguments
        :param kwargs: cached function keyword arguments
        """
        cache_key = self._get_cache_key(*args, **kwargs)
        self._cache.pop(cache_key, None)

    def _get_cache_key(self, *args: T.Any, **kwargs: T.Any) -> T.Any:
        return (self._func, args, frozenset(kwargs.items()))
