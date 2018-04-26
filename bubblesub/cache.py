"""Caching utilities."""
import abc
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


class MemoryCache(abc.ABC):
    """Class providing functionality similar to functools.lru_cache."""

    def __init__(self):
        """Initialize self."""
        self._cache = {}

    def __getitem__(self, key: T.Any) -> T.Any:
        """
        Retrieve object with given key.

        If object is unavailable, calls _real_get and caches its result under
        given key.

        :param key: cache key
        :return: cached object
        """
        ret = self._cache.get(key, None)
        if ret is None:
            ret = self._real_get(key)
            self._cache[key] = ret
        return ret

    def __delitem__(self, key: T.Any):
        """
        Delete object with given key from cache.

        :param key: cache key to delete
        """
        if key in self._cache:
            del self._cache[key]

    def wipe(self) -> None:
        """Wipe cache."""
        self._cache = {}

    @abc.abstractmethod
    def _real_get(self, key: T.Any) -> T.Any:
        """
        Create the object (without cache lookups).

        :param key: cache key the object was looked up with
        :return: created object
        """
        raise NotImplementedError('Not implemented')
