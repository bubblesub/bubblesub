import abc
import pickle
import typing as T

from pathlib import Path

import xdg

CACHE_SUFFIX = '.dat'


def get_cache_dir() -> Path:
    return Path(xdg.XDG_CACHE_HOME) / 'bubblesub'


def get_cache_file_path(cache_name: str) -> Path:
    return get_cache_dir() / (cache_name + CACHE_SUFFIX)


def load_cache(cache_name: str) -> T.Any:
    cache_path = get_cache_file_path(cache_name)
    if cache_path.exists():
        with cache_path.open(mode='rb') as handle:
            return pickle.load(handle)
    return None


def save_cache(cache_name: str, data: T.Any) -> None:
    cache_path = get_cache_file_path(cache_name)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open(mode='wb') as handle:
        pickle.dump(data, handle)


def wipe_cache() -> None:
    for path in get_cache_dir().iterdir():
        if path.suffix == CACHE_SUFFIX:
            path.unlink()


class MemoryCache(abc.ABC):
    def __init__(self):
        self._cache = {}

    def __getitem__(self, index: T.Any) -> T.Any:
        ret = self._cache.get(index, None)
        if ret is None:
            ret = self._real_get(index)
            self._cache[index] = ret
        return ret

    def __delitem__(self, index: T.Any):
        if index in self._cache:
            del self._cache[index]

    def wipe(self) -> None:
        self._cache = {}

    @abc.abstractmethod
    def _real_get(self, index: T.Any) -> T.Any:
        raise NotImplementedError('Not implemented')
