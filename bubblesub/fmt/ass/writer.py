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

"""ASS file writer."""

import functools
import typing as T
from collections import OrderedDict
from pathlib import Path

from bubblesub.fmt.ass.event import AssEvent
from bubblesub.fmt.ass.file import AssFile
from bubblesub.fmt.ass.style import AssColor, AssStyle
from bubblesub.fmt.ass.util import escape_ass_tag
from bubblesub.util import ms_to_times

NOTICE = "Script generated by bubblesub\nhttps://github.com/rr-/bubblesub"


def _escape(text: str) -> str:
    return text.replace(",", ";")


def _serialize_color(col: AssColor) -> str:
    return f"&H{col.alpha:02X}{col.blue:02X}{col.green:02X}{col.red:02X}"


def _ms_to_timestamp(milliseconds: int) -> str:
    hours, minutes, seconds, milliseconds = ms_to_times(milliseconds)
    return f"{hours:01d}:{minutes:02d}:{seconds:02d}.{milliseconds // 10:02d}"


def write_meta(ass_file: AssFile, handle: T.IO[str]) -> None:
    """Write ASS meta to a file.

    :param ass_file: ASS file to take the metadata from
    :param handle: handle to write the metadata to
    """
    meta: T.Dict[str, str] = OrderedDict()
    meta["ScriptType"] = "sentinel"  # make sure script type is the first entry
    meta.update(ass_file.meta.items())
    meta["ScriptType"] = "v4.00+"

    print("[Script Info]", file=handle)
    for line in NOTICE.splitlines(False):
        print(";", line, file=handle)
    for key, value in meta.items():
        print(key, "" if value is None else value, sep=": ", file=handle)


def write_styles(ass_file: AssFile, handle: T.IO[str]) -> None:
    """Write ASS styles to a file.

    :param ass_file: ASS file to take the styles from
    :param handle: handle to write the styles to
    """
    print("[V4+ Styles]", file=handle)
    print(
        "Format: Name, Fontname, Fontsize, PrimaryColour, "
        "SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding",
        file=handle,
    )
    for style in ass_file.styles:
        write_style(style, handle)


@functools.lru_cache(maxsize=1024)
def serialize_style(style: AssStyle) -> str:
    """Serializes ASS style to plain text.

    :param style: ASS style to serialize
    :return: serialized ASS style
    """
    return "Style: " + ",".join(
        [
            _escape(style.name),
            _escape(style.font_name),
            _escape(f"{style.font_size:d}"),
            _escape(_serialize_color(style.primary_color)),
            _escape(_serialize_color(style.secondary_color)),
            _escape(_serialize_color(style.outline_color)),
            _escape(_serialize_color(style.back_color)),
            _escape("-1" if style.bold else "0"),
            _escape("-1" if style.italic else "0"),
            _escape("-1" if style.underline else "0"),
            _escape("-1" if style.strike_out else "0"),
            _escape(f"{style.scale_x:}"),
            _escape(f"{style.scale_y:}"),
            _escape(f"{style.spacing:}"),
            _escape(f"{style.angle:}"),
            _escape(f"{style.border_style:d}"),
            _escape(f"{style.outline:}"),
            _escape(f"{style.shadow:}"),
            _escape(f"{style.alignment:d}"),
            _escape(f"{style.margin_left:d}"),
            _escape(f"{style.margin_right:d}"),
            _escape(f"{style.margin_vertical:d}"),
            _escape(f"{style.encoding:d}"),
        ]
    )


def write_style(style: AssStyle, handle: T.IO[str]) -> None:
    """Write ASS style to a file.

    :param style: ASS style to write
    :param handle: handle to write the style to
    """
    print(serialize_style(style), file=handle)


def write_events(ass_file: AssFile, handle: T.IO[str]) -> None:
    """Write ASS events to a file.

    :param ass_file: ASS file to take the events from
    :param handle: handle to write the events to
    """
    print("[Events]", file=handle)
    print(
        "Format: Layer, Start, End, Style, Name, "
        "MarginL, MarginR, MarginV, Effect, Text",
        file=handle,
    )
    for event in ass_file.events:
        write_event(event, handle)


@functools.lru_cache(maxsize=1024)
def serialize_event(event: AssEvent) -> str:
    """Serializes ASS event to plain text.

    :param event: ASS event to serialize
    :return: serialized ASS event
    """
    text = event.text

    if event.start is not None and event.end is not None:
        text = "{TIME:%d,%d}" % (event.start, event.end) + text

    if event.note:
        text += "{NOTE:%s}" % escape_ass_tag(event.note.replace("\n", "\\N"))

    event_type = "Comment" if event.is_comment else "Dialogue"
    return (
        event_type
        + ": "
        + ",".join(
            [
                _escape(f"{event.layer:d}"),
                _escape(_ms_to_timestamp(event.start)),
                _escape(_ms_to_timestamp(event.end)),
                _escape(event.style),
                _escape(event.actor),
                _escape(f"{event.margin_left:d}"),
                _escape(f"{event.margin_right:d}"),
                _escape(f"{event.margin_vertical:d}"),
                _escape(event.effect),
                text,
            ]
        )
    )


def write_event(event: AssEvent, handle: T.IO[str]) -> None:
    """Write ASS event to a file.

    :param event: ASS event to write
    :param handle: handle to write the event to
    """
    print(serialize_event(event), file=handle)


def write_ass(ass_file: AssFile, target: T.Union[Path, T.IO[str]]) -> None:
    """Save ASS to the specified target.

    :param ass_file: file to save
    :param target: writable stream or a path
    """
    if isinstance(target, Path):
        with target.open("w") as handle:
            write_ass(ass_file, handle)
            return

    write_meta(ass_file, target)
    print("", file=target)
    write_styles(ass_file, target)
    print("", file=target)
    write_events(ass_file, target)
