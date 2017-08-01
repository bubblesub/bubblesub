import re
from bubblesub.cmd.registry import BaseCommand


class EditKaraokeSplitCommand(BaseCommand):
    name = 'edit/karaoke-split'

    def enabled(self, api):
        return (len(api.subs.selected_indexes) == 1
            and '\\k' in api.subs.selected_lines[0].text)

    def run(self, api):
        idx = api.subs.selected_indexes[0]
        sub = api.subs.lines[idx]
        start = sub.start
        end = sub.end
        syllables = self._get_syllables(sub.text)

        new_selection = []
        api.gui.begin_update()
        api.subs.lines.remove(idx, 1)
        for i, syllable in enumerate(syllables):
            prev_syllable = syllables[i - 1] if i > 0 else None

            sub_def = {k: getattr(sub, k) for k in sub.prop.keys()}
            sub_def['text'] = syllable['text']
            sub_def['start'] = start
            sub_def['end'] = min(end, start + syllable['duration'] * 10)
            start = sub_def['end']

            api.subs.lines.insert_one(idx + i, **sub_def)
            new_selection.append(idx + i)
        api.subs.selected_indexes = new_selection
        api.gui.end_update()

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


class EditKaraokeJoinCommand(BaseCommand):
    name = 'edit/karaoke-join'

    def enabled(self, api):
        return len(api.subs.selected_indexes) > 1

    def run(self, api):
        subs = api.subs.selected_lines
        for idx in reversed(api.subs.selected_indexes[1:]):
            api.subs.lines.remove(idx, 1)
        text = ''
        for sub in subs:
            text += ('{\\k%d}' % (sub.duration // 10)) + sub.text
        subs[0].text = text
        subs[0].end = subs[-1].end
        api.subs.selected_indexes = [subs[0].number]
