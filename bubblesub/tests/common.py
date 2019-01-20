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

import argparse
import typing as T
from pathlib import Path

import pytest

from bubblesub.api import Api

APP_ROOT_DIR = Path(__file__).parent.parent
TESTS_ROOT_DIR = APP_ROOT_DIR / "tests"


def collect_source_files(root: Path = APP_ROOT_DIR) -> T.Iterable[Path]:
    for path in root.iterdir():
        if path.is_dir():
            yield from collect_source_files(path)
        elif path.is_file() and path.suffix == ".py":
            yield path


@pytest.fixture
def api() -> Api:
    args = argparse.Namespace()
    setattr(args, "no_video", True)
    return Api(args)
