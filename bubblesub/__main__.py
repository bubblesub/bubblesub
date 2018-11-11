#!/usr/bin/env python3

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

"""CLI endpoint."""

import argparse

import bubblesub.cache
import bubblesub.opt
import bubblesub.ui


def parse_args() -> argparse.Namespace:
    """
    Parse user arguments from CLI.

    :return: parsed args
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='?')
    parser.add_argument('--no-config', action='store_true')
    parser.add_argument('--no-video', action='store_true')
    parser.add_argument('--wipe-cache', action='store_true')
    return parser.parse_args()


def main() -> None:
    """CLI endpoint."""
    args = parse_args()

    opt = bubblesub.opt.Options()
    if not args.no_config:
        opt.load(opt.DEFAULT_PATH)

    if args.wipe_cache:
        bubblesub.cache.wipe_cache()

    from bubblesub.api import Api

    api = Api(opt, args)

    bubblesub.ui.run(api, args)

    if not args.no_config:
        assert opt.root_dir is not None
        opt.save(opt.root_dir)


if __name__ == '__main__':
    main()
