"""Various ASS utilities."""
import typing as T

import ass_tag_parser
import enchant
import regex


def escape_ass_tag(text: str) -> str:
    """
    Escape text so that it doesn't get treated as ASS tags.

    :param text: text to escape
    :return: escaped text
    """
    return (
        text
        .replace('\\', r'\\')
        .replace('{', r'\[')
        .replace('}', r'\]')
    )


def unescape_ass_tag(text: str) -> str:
    """
    Do the reverse operation to escape_ass_tag().

    :param text: text to unescape
    :return: unescaped text
    """
    return (
        text
        .replace(r'\\', '\\')
        .replace(r'\[', '{')
        .replace(r'\]', '}')
    )


def ass_to_plaintext(text: str, mask: bool = False) -> str:
    """
    Strip ASS tags from an ASS line.

    :param text: input ASS line
    :param mask: whether to mark ASS tags with special characters
    :return: plain text
    """
    return str(
        regex.sub('{[^}]+}', '\N{FULLWIDTH ASTERISK}' if mask else '', text)
        .replace('\\h', ' ')
        .replace('\\N', '\N{SYMBOL FOR NEWLINE}')
    )


def character_count(text: str) -> int:
    """
    Count how many characters an ASS line contains.

    Doesn't take into account effects such as text invisibility etc.

    :param text: input ASS line
    :return: number of characters
    """
    return len(
        regex.sub(r'\W+', '', ass_to_plaintext(text), flags=regex.I | regex.U)
    )


def iter_words_ass_line(text: str) -> T.Iterable[T.Match[str]]:
    """
    Iterate over words within an ASS line.

    Doesn't take into account effects such as text invisibility etc.

    :param text: input ASS line
    :return: iterator over regex matches
    """
    text = regex.sub(
        r'\\[Nnh]',
        '  ',  # two spaces to preserve match positions
        text
    )

    return T.cast(
        T.Iterable[T.Match[str]],
        regex.finditer(
            r'[\p{L}\p{S}\p{N}][\p{L}\p{S}\p{N}\p{P}]*\p{L}|\p{L}',
            text
        )
    )


def spell_check_ass_line(
        dictionary: enchant.Dict,
        text: str
) -> T.Iterable[T.Tuple[int, int, str]]:
    """
    Iterate over badly spelled words within an ASS line.

    Doesn't take into account effects such as text invisibility etc.

    :param dictionary: dictionary object to validate the words with
    :param text: input ASS line
    :return: iterator over tuples with start, end and text
    """
    try:
        ass_struct = ass_tag_parser.parse_ass(text)
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
                    word
                )
