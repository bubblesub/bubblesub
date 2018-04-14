import re
import typing as T

from bubblesub.ass.file import AssFile
from bubblesub.ass.style import Color
from bubblesub.ass.util import unescape_ass_tag

TIMESTAMP_RE = re.compile(r'(\d{1,2}):(\d{2}):(\d{2})[.,](\d{2,3})')
SECTION_HEADING_RE = re.compile(r'^\[([^\]]+)\]')


def _deserialize_color(text: str) -> Color:
    val = int(text[2:], base=16)
    red = val & 0xFF
    green = (val >> 8) & 0xFF
    blue = (val >> 16) & 0xFF
    alpha = (val >> 24) & 0xFF
    return Color(red, green, blue, alpha)


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
    milliseconds += hours * 3600000
    return milliseconds


class ReadContext:
    field_names: T.List[str] = []


def _inside_info_section(
        line: str,
        ass_file: AssFile,
        _context: ReadContext
) -> None:
    if line.startswith(';'):
        return
    key, value = line.split(': ', 1)
    ass_file.info[key] = value


def _inside_meta_section(
        line: str,
        ass_file: AssFile,
        _context: ReadContext
) -> None:
    if line.startswith(';'):
        return
    key, value = line.split(': ', 1)
    ass_file.meta[key] = value


def _inside_styles_section(
        line: str,
        ass_file: AssFile,
        ctx: ReadContext
) -> None:
    if line.startswith('Format:'):
        _, rest = line.split(': ', 1)
        ctx.field_names = [p.strip() for p in rest.split(',')]
        return

    _, rest = line.split(': ', 1)
    field_values = rest.strip().split(',')
    field_dict = dict(zip(ctx.field_names, field_values))
    ass_file.styles.insert_one(
        name=field_dict['Name'],
        font_name=field_dict['Fontname'],
        font_size=float(field_dict['Fontsize']),
        primary_color=_deserialize_color(field_dict['PrimaryColour']),
        secondary_color=_deserialize_color(field_dict['SecondaryColour']),
        outline_color=_deserialize_color(field_dict['OutlineColour']),
        back_color=_deserialize_color(field_dict['BackColour']),
        bold=field_dict['Bold'] == '-1',
        italic=field_dict['Italic'] == '-1',
        underline=field_dict['Underline'] == '-1',
        strike_out=field_dict['StrikeOut'] == '-1',
        scale_x=float(field_dict['ScaleX']),
        scale_y=float(field_dict['ScaleY']),
        spacing=float(field_dict['Spacing']),
        angle=float(field_dict['Angle']),
        border_style=int(field_dict['BorderStyle']),
        outline=float(field_dict['Outline']),
        shadow=float(field_dict['Shadow']),
        alignment=int(field_dict['Alignment']),
        margin_left=int(field_dict['MarginL']),
        margin_right=int(field_dict['MarginR']),
        margin_vertical=int(field_dict['MarginV']),
        encoding=int(field_dict['Encoding'])
    )


def _inside_events_section(
        line: str,
        ass_file: AssFile,
        ctx: ReadContext
) -> None:
    if line.startswith('Format:'):
        _, rest = line.split(': ', 1)
        ctx.field_names = [p.strip() for p in rest.split(',')]
        return

    event_type, rest = line.split(': ', 1)
    field_values = rest.strip().split(',', len(ctx.field_names) - 1)
    field_dict = dict(zip(ctx.field_names, field_values))

    if event_type not in {'Comment', 'Dialogue'}:
        raise ValueError(f'Unknown event type: "{event_type}"')

    text = field_dict['Text']
    note = ''
    match = re.search(r'{NOTE:(?P<note>[^}]*)}', text)
    if match:
        text = text[:match.start()] + text[match.end():]
        note = unescape_ass_tag(match.group('note'))

    start: T.Optional[int] = None
    end: T.Optional[int] = None
    match = re.search(r'{TIME:(?P<start>-?\d+),(?P<end>-?\d+)}', text)
    if match:
        text = text[:match.start()] + text[match.end():]
        start = int(match.group('start'))
        end = int(match.group('end'))

    ass_file.events.insert_one(
        layer=int(field_dict['Layer']),
        start=(start or _timestamp_to_ms(field_dict['Start'])),
        end=(end or _timestamp_to_ms(field_dict['End'])),
        style=field_dict['Style'],
        actor=field_dict['Name'],
        margin_left=int(field_dict['MarginL']),
        margin_right=int(field_dict['MarginR']),
        margin_vertical=int(field_dict['MarginV']),
        effect=field_dict['Effect'],
        text=text,
        note=note,
        is_comment=event_type == 'Comment'
    )


def load_ass(handle: T.IO, ass_file: AssFile) -> None:
    ctx = ReadContext()

    ass_file.events.clear()
    ass_file.styles.clear()
    ass_file.meta.clear()
    ass_file.info.clear()

    handler: T.Optional[T.Callable[[str, AssFile, ReadContext], None]] = None

    for i, line in enumerate(handle):
        line = line.strip()
        if not line:
            continue

        try:
            match = SECTION_HEADING_RE.match(line)
            if match:
                section = match.group(1)
                if section == 'Script Info':
                    handler = _inside_info_section
                elif section == 'Aegisub Project Garbage':
                    handler = _inside_meta_section
                elif section == 'V4+ Styles':
                    handler = _inside_styles_section
                elif section == 'Events':
                    handler = _inside_events_section
                else:
                    raise ValueError(f'Unrecognized section: "{section}"')
            elif not handler:
                raise ValueError('Expected section')
            else:
                handler(line, ass_file, ctx)  # pylint: disable=not-callable
        except (ValueError, IndexError):
            raise ValueError(f'Corrupt ASS file at line #{i+1}: "{line}"')
