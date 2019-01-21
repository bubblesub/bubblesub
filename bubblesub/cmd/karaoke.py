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
from copy import copy

import ass_tag_parser

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand, CommandUnavailable, CommandError
from bubblesub.ass.event import Event
from bubblesub.cmd.common import SubtitlesSelection


class _Syllable:
    def __init__(self, text: str, duration: int) -> None:
        self.text = text
        self.duration = duration


class SubtitlesSplitKaraokeCommand(BaseCommand):
    names = ["sub-split-karaoke"]
    help_text = "Splits given subtitles according to the karaoke tags inside."

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable("nothing to split")

        new_selection: T.List[Event] = []
        with self.api.undo.capture(), self.api.gui.throttle_updates():
            for sub in subs:
                if "\\k" not in sub.text:
                    continue

                start = sub.start
                end = sub.end
                try:
                    syllables = list(self._get_syllables(sub.text))
                except ass_tag_parser.ParseError as ex:
                    raise CommandError(str(ex))

                idx = sub.index
                self.api.subs.events.remove(idx, 1)

                new_subs: T.List[Event] = []
                for i, syllable in enumerate(syllables):
                    sub_copy = copy(sub)
                    sub_copy.start = start
                    sub_copy.end = min(end, start + syllable.duration)
                    sub_copy.text = syllable.text
                    if i > 0:
                        sub_copy.note = ""
                    start = sub_copy.end
                    new_subs.append(sub_copy)

                self.api.subs.events.insert(idx, *new_subs)
                new_selection += new_subs

            self.api.subs.selected_indexes = [
                sub.index for sub in new_selection
            ]

    def _get_syllables(self, text: str) -> T.Iterable[_Syllable]:
        chunks: T.List[T.List[ass_tag_parser.AssItem]] = [[]]
        durations: T.List[int] = [0]

        for item in ass_tag_parser.parse_ass(text):
            if isinstance(item, ass_tag_parser.AssTagKaraoke):
                durations.append(item.duration)
                chunks.append([])
            elif not isinstance(
                item,
                (
                    ass_tag_parser.AssTagListOpening,
                    ass_tag_parser.AssTagListEnding,
                ),
            ):
                chunks[-1].append(item)

        while chunks and durations and not chunks[0] and not durations[0]:
            chunks.pop(0)
            durations.pop(0)

        for duration, chunk in zip(durations, chunks):
            text = ass_tag_parser.compose_ass(chunk)
            yield _Syllable(text, duration)

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-t",
            "--target",
            help="subtitles to split",
            type=lambda value: SubtitlesSelection(api, value),
            default="selected",
        )


class SubtitlesMergeKaraokeCommand(BaseCommand):
    names = ["sub-merge-karaoke", "sub-join-karaoke"]
    help_text = "Merges given subtitles adding karaoke timing tags inbetween."

    @property
    def is_enabled(self) -> bool:
        return self.args.target.makes_sense

    async def run(self) -> None:
        subs = await self.args.target.get_subtitles()
        if not subs:
            raise CommandUnavailable("nothing to merge")

        with self.api.undo.capture():
            subs[0].begin_update()

            if self.args.invisible:
                text = ""
                for i, sub in enumerate(subs):
                    text += sub.text
                    if i != len(subs) - 1:
                        pos = subs[i + 1].start - subs[0].start
                        text += r"{\alpha&HFF&\t(%d,%d,\alpha&H00&)}" % (
                            pos,
                            pos,
                        )
                subs[0].text = text
            else:
                subs[0].text = "".join(
                    ("{\\k%d}" % (sub.duration // 10)) + sub.text
                    for sub in subs
                )

            subs[0].note = "".join(sub.note for sub in subs)
            subs[0].end = subs[-1].end
            subs[0].end_update()

            assert subs[0].index is not None
            self.api.subs.events.remove(subs[0].index + 1, len(subs) - 1)
            self.api.subs.selected_indexes = [subs[0].index]

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-t",
            "--target",
            help="subtitles to merge",
            type=lambda value: SubtitlesSelection(api, value),
            default="selected",
        )
        parser.add_argument(
            "--invisible",
            help="use alternative karaoke transformation",
            action="store_true",
        )


COMMANDS = [SubtitlesSplitKaraokeCommand, SubtitlesMergeKaraokeCommand]
