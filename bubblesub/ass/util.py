import typing as T

import ass_tag_parser
import enchant
import regex


def escape_ass_tag(text: str) -> str:
    return (
        text
        .replace('\\', r'\\')
        .replace('{', r'\[')
        .replace('}', r'\]'))


def unescape_ass_tag(text: str) -> str:
    return (
        text
        .replace(r'\\', '\\')
        .replace(r'\[', '{')
        .replace(r'\]', '}'))


def ass_to_plaintext(text: str, mask: bool = False) -> str:
    return str(
        regex.sub('{[^}]+}', '\N{FULLWIDTH ASTERISK}' if mask else '', text)
        .replace('\\h', ' ')
        .replace('\\N', '\N{SYMBOL FOR NEWLINE}'))


def character_count(text: str) -> int:
    return len(
        regex.sub(r'\W+', '', ass_to_plaintext(text), flags=regex.I | regex.U))


def iter_words_ass_line(ass_text: str) -> T.Iterable[T.Match[str]]:
    ass_text = regex.sub(
        r'\\[Nnh]',
        '  ',  # two spaces to preserve match positions
        ass_text)

    return T.cast(
        T.Iterable[T.Match[str]],
        regex.finditer(
            r'[\p{L}\p{S}\p{N}][\p{L}\p{S}\p{N}\p{P}]*\p{L}|\p{L}',
            ass_text,
        ),
    )


def spell_check_ass_line(
        dictionary: enchant.Dict,
        ass_text: str,
) -> T.Iterable[T.Tuple[int, int, str]]:
    try:
        ass_struct = ass_tag_parser.parse_ass(ass_text)
    except ass_tag_parser.ParsingError:
        return
    for item in ass_struct:
        if item['type'] != 'text':
            continue

        text_start, _text_end = item['pos']
        for match in iter_words_ass_line(item['text']):
            word = match.group(0)
            if not dictionary.check(word):
                yield (
                    text_start + match.start(),
                    text_start + match.end(),
                    word)
