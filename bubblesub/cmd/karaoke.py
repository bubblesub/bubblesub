import re
from bubblesub.api.cmd import CoreCommand


class EditKaraokeSplitCommand(CoreCommand):
    name = 'edit/karaoke-split'
    menu_name = 'Split subtitles as karaoke'

    def enabled(self):
        return (
            len(self.api.subs.selected_indexes) == 1
            and '\\k' in self.api.subs.selected_lines[0].text)

    async def run(self):
        with self.api.undo.bulk():
            idx = self.api.subs.selected_indexes[0]
            sub = self.api.subs.lines[idx]
            start = sub.start
            end = sub.end
            syllables = self._get_syllables(sub.text)

            new_selection = []
            self.api.gui.begin_update()
            self.api.subs.lines.remove(idx, 1)
            for i, syllable in enumerate(syllables):
                sub_def = {k: getattr(sub, k) for k in sub.prop.keys()}
                sub_def['text'] = syllable['text']
                sub_def['start'] = start
                sub_def['end'] = min(end, start + syllable['duration'] * 10)
                start = sub_def['end']

                self.api.subs.lines.insert_one(idx + i, **sub_def)
                new_selection.append(idx + i)
            self.api.subs.selected_indexes = new_selection
            self.api.gui.end_update()

    def _get_syllables(self, text):
        match = re.split('({[^{}]*})', text)
        syllables = [{'text': '', 'duration': 0}]
        for group in match:
            if group.startswith('{'):
                match = re.search('\\\\k(\\d+)', group)
                if match:
                    syllables.append({
                        'text': '',
                        'duration': int(match.group(1)),
                    })
                    # remove the leftover \k tag
                    group = group[:match.start()] + group[match.end():]
                    if group == '{}':
                        group = ''
                syllables[-1]['text'] += group
            else:
                syllables[-1]['text'] += group
        if not syllables[0]['text'] and syllables[0]['duration'] == 0:
            syllables = syllables[1:]
        return syllables


class EditKaraokeJoinCommand(CoreCommand):
    name = 'edit/karaoke-join'
    menu_name = 'Join subtitles (as karaoke)'

    def enabled(self):
        return len(self.api.subs.selected_indexes) > 1

    async def run(self):
        with self.api.undo.bulk():
            subs = self.api.subs.selected_lines
            for idx in reversed(self.api.subs.selected_indexes[1:]):
                self.api.subs.lines.remove(idx, 1)
            text = ''
            for sub in subs:
                text += ('{\\k%d}' % (sub.duration // 10)) + sub.text
            subs[0].text = text
            subs[0].end = subs[-1].end
            self.api.subs.selected_indexes = [subs[0].id]


class EditTransformationJoinCommand(CoreCommand):
    name = 'edit/transformation-join'
    menu_name = 'Join subtitles (as transformation)'

    def enabled(self):
        return len(self.api.subs.selected_indexes) > 1

    async def run(self):
        with self.api.undo.bulk():
            subs = self.api.subs.selected_lines
            for idx in reversed(self.api.subs.selected_indexes[1:]):
                self.api.subs.lines.remove(idx, 1)
            text = ''
            note = ''
            pos = 0
            for i, sub in enumerate(subs):
                pos += sub.duration
                text += sub.text
                note += sub.note
                if i != len(subs) - 1:
                    text += (
                        '{\\alpha&HFF&\\t(%d,%d,\\alpha&H00&)}' % (pos, pos))
            subs[0].text = text
            subs[0].note = note
            subs[0].end = subs[-1].end
            self.api.subs.selected_indexes = [subs[0].id]
