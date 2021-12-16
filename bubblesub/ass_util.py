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

"""Various ASS utilities."""

import re
from collections.abc import Iterable
from functools import lru_cache
from typing import cast

import ass_tag_parser
import regex

from bubblesub.spell_check import BaseSpellChecker


@lru_cache(maxsize=5000)
def character_count(text: str) -> int:
    """Count how many characters an ASS line contains.

    Doesn't take into account effects such as text invisibility etc.

    :param text: input ASS line
    :return: number of characters
    """
    return len(
        regex.sub(
            r"\W+",
            "",
            ass_tag_parser.ass_to_plaintext(text),
            flags=regex.I | regex.U,
        )
    )


def iter_words_ass_line(text: str) -> Iterable[re.Match[str]]:
    """Iterate over words within an ASS line.

    Doesn't take into account effects such as text invisibility etc.

    :param text: input ASS line
    :return: iterator over regex matches
    """
    text = regex.sub(
        r"\\[Nnh]", "  ", text  # two spaces to preserve match positions
    )

    return cast(
        Iterable[re.Match[str]],
        regex.finditer(
            r"[\p{L}\p{S}\p{N}][\p{L}\p{S}\p{N}\p{P}]*\p{L}|\p{L}", text
        ),
    )


@lru_cache(maxsize=500)
def spell_check_ass_line(
    spell_checker: BaseSpellChecker, text: str
) -> Iterable[tuple[int, int, str]]:
    """Iterate over badly spelled words within an ASS line.

    Doesn't take into account effects such as text invisibility etc.

    :param spell_checker: spell checker to validate the words with
    :param text: input ASS line
    :return: iterator over tuples with start, end and text
    """
    try:
        ass_line = ass_tag_parser.parse_ass(text)
    except ass_tag_parser.ParseError:
        return []

    results: list[tuple[int, int, str]] = []

    for item in ass_line:
        if isinstance(item, ass_tag_parser.AssText):
            for match in iter_words_ass_line(item.text):
                word = match.group(0)
                if not spell_checker.check(word):
                    results.append(
                        (
                            item.meta.start + match.start(),
                            item.meta.start + match.end(),
                            word,
                        )
                    )

    return results
