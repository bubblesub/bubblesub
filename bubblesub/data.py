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

"""Static assets management."""

import typing as T
from pathlib import Path

import bubblesub.opt


ROOT_DIR = Path(__file__).parent / 'data'


def get_all(
        opt: bubblesub.opt.Options,
        directory_name: str
) -> T.Iterable[Path]:
    """
    Get path to all static assets under given directory name.

    :param opt: program options
    :param directory_name: directory that contains relevant assets
    :return: list of paths found in the user and built-in asset directories
    """
    for path in [ROOT_DIR, opt.root_dir]:
        if path is None:
            continue

        path /= directory_name
        if path.exists():
            yield from path.iterdir()
