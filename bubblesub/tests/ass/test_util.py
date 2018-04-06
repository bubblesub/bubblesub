import pytest
import bubblesub.ass.util


@pytest.mark.parametrize('ass_text,expected', [
    ('test', ['test']),
    ('one two', ['one', 'two']),
    ('one\\Ntwo', ['one', 'two']),
    ('one\\ntwo', ['one', 'two']),
    ('one\\htwo', ['one', 'two']),
    ('\\None two', ['one', 'two']),
    ('\\none two', ['one', 'two']),
    ('\\hone two', ['one', 'two']),
    ('1st', ['1st']),
    ('1st 2nd', ['1st', '2nd']),
])
def test_iter_words_ass_line(ass_text, expected):
    actual = [
        match.group(0)
        for match in bubblesub.ass.util.iter_words_ass_line(ass_text)
    ]
    assert actual == expected
