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
from fractions import Fraction

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.util import eval_expr


class SetVolumeCommand(BaseCommand):
    names = ["set-volume"]
    help_text = "Adjusts the video volume."

    async def run(self) -> None:
        new_value = eval_expr(
            self.args.expression.format(self.api.playback.volume)
        )
        assert isinstance(new_value, Fraction)
        self.api.playback.volume = new_value

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "expression", help="expression to calculate new volume", type=str
        )


COMMANDS = [SetVolumeCommand]
