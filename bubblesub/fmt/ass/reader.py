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

"""ASS file reader."""

import io
import re
import typing as T
from pathlib import Path

from bubblesub.fmt.ass.event import AssEvent
from bubblesub.fmt.ass.file import AssFile
from bubblesub.fmt.ass.style import AssColor, AssStyle
from bubblesub.fmt.ass.util import unescape_ass_tag

TIMESTAMP_RE = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[.,](\d{2,3})")
SECTION_HEADING_RE = re.compile(r"^\[([^\]]+)\]$")


def _deserialize_color(text: str) -> AssColor:
    val = int(text[2:], base=16)
    red = val & 0xFF
    green = (val >> 8) & 0xFF
    blue = (val >> 16) & 0xFF
    alpha = (val >> 24) & 0xFF
    return AssColor(red, green, blue, alpha)


def _timestamp_to_ms(text: str) -> int:
    match = TIMESTAMP_RE.match(text)
    assert match is not None

    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    frac = match.group(4)

    milliseconds: int = int(frac) * 10 ** (3 - len(frac))
    milliseconds += seconds * 1000
    milliseconds += minutes * 60000
    milliseconds += hours * 3_600_000
    return milliseconds


class _ReadContext:
    field_names: T.List[str] = []


def _info_section_handler(
    line: str, ass_file: AssFile, _context: _ReadContext
) -> None:
    if line.startswith(";"):
        return
    try:
        key, value = line.split(":", 1)
        ass_file.meta.set(key, value.lstrip())
    except ValueError:
        ass_file.meta.set(line, "")


def _styles_section_handler(
    line: str, ass_file: AssFile, ctx: _ReadContext
) -> None:
    if line.startswith("Format:"):
        _, rest = line.split(": ", 1)
        ctx.field_names = [p.strip() for p in rest.split(",")]
        return

    _, rest = line.split(": ", 1)
    field_values = rest.strip().split(",")
    field_dict = dict(zip(ctx.field_names, field_values))
    ass_file.styles.append(
        AssStyle(
            name=field_dict["Name"],
            font_name=field_dict["Fontname"],
            font_size=int(float(field_dict["Fontsize"])),
            primary_color=_deserialize_color(field_dict["PrimaryColour"]),
            secondary_color=_deserialize_color(field_dict["SecondaryColour"]),
            outline_color=_deserialize_color(field_dict["OutlineColour"]),
            back_color=_deserialize_color(field_dict["BackColour"]),
            bold=field_dict["Bold"] == "-1",
            italic=field_dict["Italic"] == "-1",
            underline=field_dict["Underline"] == "-1",
            strike_out=field_dict["StrikeOut"] == "-1",
            scale_x=float(field_dict["ScaleX"]),
            scale_y=float(field_dict["ScaleY"]),
            spacing=float(field_dict["Spacing"]),
            angle=float(field_dict["Angle"]),
            border_style=int(field_dict["BorderStyle"]),
            outline=float(field_dict["Outline"]),
            shadow=float(field_dict["Shadow"]),
            alignment=int(field_dict["Alignment"]),
            margin_left=int(float(field_dict["MarginL"])),
            margin_right=int(float(field_dict["MarginR"])),
            margin_vertical=int(float(field_dict["MarginV"])),
            encoding=int(field_dict["Encoding"]),
        )
    )


def _events_section_handler(
    line: str, ass_file: AssFile, ctx: _ReadContext
) -> None:
    if line.startswith("Format:"):
        _, rest = line.split(": ", 1)
        ctx.field_names = [p.strip() for p in rest.split(",")]
        return

    event_type, rest = line.split(": ", 1)
    field_values = rest.strip().split(",", len(ctx.field_names) - 1)
    field_dict = dict(zip(ctx.field_names, field_values))

    if event_type not in {"Comment", "Dialogue"}:
        raise ValueError(f'unknown event type: "{event_type}"')

    text = field_dict["Text"]
    note = ""
    match = re.search(r"{NOTE:(?P<note>[^}]*)}", text)
    if match:
        text = text[: match.start()] + text[match.end() :]
        note = unescape_ass_tag(match.group("note"))

    # ASS tags have centisecond precision
    start = _timestamp_to_ms(field_dict["Start"])
    end = _timestamp_to_ms(field_dict["End"])

    # refine times down to millisecond precision using novelty {TIME:…} tag,
    # but only if the times match the regular ASS times. This is so that
    # subtitle times modified outside of bubblesub with editors that do not
    # write the novelty {TIME:…} tag are not overwritten.
    match = re.search(r"{TIME:(?P<start>-?\d+),(?P<end>-?\d+)}", text)
    if match:
        text = text[: match.start()] + text[match.end() :]
        start_ms = int(match.group("start"))
        end_ms = int(match.group("end"))
        if 0 <= start_ms - start < 10:
            start = start_ms
        if 0 <= end_ms - end < 10:
            end = end_ms

    ass_file.events.append(
        AssEvent(
            layer=int(field_dict["Layer"]),
            start=start,
            end=end,
            style=field_dict["Style"],
            actor=field_dict["Name"],
            margin_left=int(field_dict["MarginL"]),
            margin_right=int(field_dict["MarginR"]),
            margin_vertical=int(field_dict["MarginV"]),
            effect=field_dict["Effect"],
            text=text,
            note=note,
            is_comment=event_type == "Comment",
        )
    )


def _dummy_handler(
    line: str, ass_file: AssFile, context: _ReadContext
) -> None:
    pass


def load_ass(handle: T.IO[str], ass_file: AssFile) -> None:
    """Load ASS from the specified source.

    :param handle: readable stream
    :param ass_file: file to load to
    """
    ctx = _ReadContext()

    ass_file.events.clear()
    ass_file.styles.clear()
    ass_file.meta.clear()

    handler: T.Optional[T.Callable[[str, AssFile, _ReadContext], None]] = None

    text = handle.read()
    text = text.replace("\r", "")
    if text.startswith("\N{BOM}"):
        text = text[len("\N{BOM}") :]
    lines = text.split("\n")

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        try:
            match = SECTION_HEADING_RE.match(line)
            if match:
                section = match.group(1)
                if section == "Script Info":
                    handler = _info_section_handler
                elif section == "V4+ Styles":
                    handler = _styles_section_handler
                elif section == "Events":
                    handler = _events_section_handler
                elif section in [
                    "Aegisub Project Garbage",
                    "Graphics",
                    "Fonts",
                ]:
                    handler = _dummy_handler
                else:
                    raise ValueError(f'unrecognized section: "{section}"')
            elif not handler:
                raise ValueError("expected section")
            else:
                handler(line, ass_file, ctx)  # pylint: disable=not-callable
        except (ValueError, IndexError):
            raise ValueError(f'corrupt ASS file at line #{i+1}: "{line}"')


def read_ass(source: T.Union[Path, T.IO[str], str]) -> AssFile:
    """Read ASS from the specified source.

    :param source: readable stream or a path
    :return: read ass file
    """
    ass_file = AssFile()
    if isinstance(source, str):
        with io.StringIO() as handle:
            handle.write(source)
            handle.seek(0)
            load_ass(handle, ass_file)
    elif isinstance(source, Path):
        with source.open("r") as handle:
            load_ass(handle, ass_file)
    else:
        load_ass(source, ass_file)
    return ass_file
