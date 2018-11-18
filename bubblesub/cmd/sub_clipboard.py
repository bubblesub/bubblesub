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
import base64
import pickle
import typing as T
import zlib

from PyQt5 import QtWidgets

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand, CommandError, CommandUnavailable
from bubblesub.ass.event import Event
from bubblesub.cmd.common import SubtitlesSelection
from bubblesub.util import ms_to_str, str_to_ms


def _pickle(data: T.Any) -> str:
    return base64.b64encode(
        zlib.compress(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))
    ).decode()


def _unpickle(text: str) -> T.Any:
    return pickle.loads(zlib.decompress(base64.b64decode(text.encode())))


class SubtitlesCopyCommand(BaseCommand):
    names = ["sub-copy"]
    help_text = "Copies given subtitles to clipboard."

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable("nothing to copy")

        if self.args.subject == "text":
            QtWidgets.QApplication.clipboard().setText(
                "\n".join(sub.text for sub in subs)
            )
        elif self.args.subject == "times":
            QtWidgets.QApplication.clipboard().setText(
                "\n".join(
                    "{} - {}".format(ms_to_str(sub.start), ms_to_str(sub.end))
                    for sub in subs
                )
            )
        elif self.args.subject == "all":
            QtWidgets.QApplication.clipboard().setText(_pickle(subs))
        else:
            raise AssertionError

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-t",
            "--target",
            help="subtitles to paste into",
            type=lambda value: SubtitlesSelection(api, value),
            default="selected",
        )
        parser.add_argument(
            "-s",
            "--subject",
            help="subject to copy",
            choices=("text", "times", "all"),
            default="all",
        )


class SubtitlesPasteCommand(BaseCommand):
    names = ["sub-paste"]
    help_text = "Pastes subtitles from clipboard."

    @property
    def is_enabled(self) -> bool:
        return self.args.origin.makes_sense

    async def run(self) -> None:
        indexes = await self.args.origin.get_indexes()

        if self.args.dir == "before":
            self._paste_from_clipboard(indexes[0] if indexes else 0)
        elif self.args.dir == "after":
            self._paste_from_clipboard(indexes[-1] + 1 if indexes else 0)
        else:
            raise AssertionError

    def _paste_from_clipboard(self, idx: int) -> None:
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            raise CommandUnavailable("clipboard is empty, aborting")

        items = T.cast(T.List[Event], _unpickle(text))
        with self.api.undo.capture():
            self.api.subs.events.insert(idx, *items)
            self.api.subs.selected_indexes = list(range(idx, idx + len(items)))

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-o",
            "--origin",
            help="where to paste the subtitles",
            type=lambda value: SubtitlesSelection(api, value),
            default="selected",
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--before",
            dest="dir",
            action="store_const",
            const="before",
            help="paste before origin",
        )
        group.add_argument(
            "--after",
            dest="dir",
            action="store_const",
            const="after",
            help="paste after origin",
        )


class SubtitlesPasteIntoCommand(BaseCommand):
    names = ["sub-paste-into"]
    help_text = "Pastes text or times into the given subtitles."

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            self.api.log.error("clipboard is empty, aborting")
            return

        lines = text.split("\n")
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable("nothing to paste into")

        if len(lines) != len(subs):
            raise CommandError(
                f"size mismatch ("
                f"selected {len(subs)} lines, "
                f"got {len(lines)} lines in clipboard)".format(
                    len(subs), len(lines)
                )
            )

        with self.api.undo.capture():
            if self.args.subject == "text":
                for line, sub in zip(lines, subs):
                    sub.text = line

            elif self.args.subject == "times":
                times: T.List[T.Tuple[int, int]] = []
                for line in lines:
                    try:
                        start, end = line.split("-", 1)
                        times.append(
                            (str_to_ms(start.strip()), str_to_ms(end.strip()))
                        )
                    except ValueError:
                        raise ValueError(f"invalid time format: {line}")

                for time, sub in zip(times, subs):
                    sub.start = time[0]
                    sub.end = time[1]

            else:
                raise AssertionError

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-t",
            "--target",
            help="subtitles to paste the subject into",
            type=lambda value: SubtitlesSelection(api, value),
            default="selected",
        )
        parser.add_argument(
            "-s",
            "--subject",
            help="subject to copy",
            choices=("text", "times"),
            required=True,
        )


COMMANDS = [
    SubtitlesCopyCommand,
    SubtitlesPasteCommand,
    SubtitlesPasteIntoCommand,
]
