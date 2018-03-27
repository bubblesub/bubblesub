import ass_tag_parser
import regex


def escape_ass_tag(text):
    return (
        text
        .replace('\\', r'\\')
        .replace('{', r'\[')
        .replace('}', r'\]'))


def unescape_ass_tag(text):
    return (
        text
        .replace(r'\\', '\\')
        .replace(r'\[', '{')
        .replace(r'\]', '}'))


def ass_to_plaintext(text, mask=False):
    return (
        regex.sub('{[^}]+}', '\N{FULLWIDTH ASTERISK}' if mask else '', text)
        .replace('\\h', ' ')
        .replace('\\N', ' '))


def character_count(text):
    return len(
        regex.sub(r'\W+', '', ass_to_plaintext(text), flags=regex.I | regex.U))


def iter_words_ass_line(ass_text):
    ass_text = regex.sub(
        r'\\[Nnh]',
        '  ',  # two spaces to preserve match positions
        ass_text)
    return regex.finditer(
        r'[\p{L}\p{S}\p{N}][\p{L}\p{S}\p{N}\p{P}]*\p{L}|\p{L}', ass_text)


def spell_check_ass_line(dictionary, ass_text):
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
