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
