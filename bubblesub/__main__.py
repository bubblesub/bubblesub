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
import logging
import sys

from bubblesub.api import Api
from bubblesub.cache import wipe_cache
from bubblesub.ui import ui


def setup_logging() -> None:
    """Add console logging handler; configure loggin levels."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)


def parse_args() -> argparse.Namespace:
    """Parse user arguments from CLI.

    :return: parsed args
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?")
    parser.add_argument("--no-config", action="store_true")
    parser.add_argument("--no-video", action="store_true")
    parser.add_argument("--wipe-cache", action="store_true")
    return parser.parse_args()


def main() -> None:
    """CLI endpoint."""
    setup_logging()
    args = parse_args()

    if args.wipe_cache:
        wipe_cache()

    app = ui.Application(args)
    app.splash_screen()

    api = Api(args)
    app.run(api)


if __name__ == "__main__":
    main()
