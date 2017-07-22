import re
import time
import json
from pathlib import Path
import pysubs2.time


def ass_to_plaintext(text, mask=False):
    return (
        re.sub('{[^}]+}', '\N{FULLWIDTH ASTERISK}' if mask else '', text)
        .replace('\\h', ' ')
        .replace('\\N', ''))


def character_count(text):
    return len(re.sub('[^\\W]+', '', ass_to_plaintext(text), re.I))


def ms_to_str(ms):
    return pysubs2.time.ms_to_str(ms, fractions=True)


def str_to_ms(text):
    result = re.match('''
        ^(?:(?P<hour>\\d+):)?
        (?P<minute>\\d\\d):
        (?P<second>\\d\\d)\\.
        (?P<millisecond>\\d\\d\\d)$''', text.strip(), re.VERBOSE)

    if result:
        hour = int(result.group('hour'))
        minute = int(result.group('minute'))
        second = int(result.group('second'))
        millisecond = int(result.group('millisecond'))
        return pysubs2.time.make_time(
            h=hour, m=minute, s=second, ms=millisecond)
    raise ValueError('Invalid time')


def _get_cache_file_path(section_name):
    return Path('~/.cache/bubblesub/').expanduser() / (section_name + '.json')


def load_cache(section_name, key_name):
    cache_file = _get_cache_file_path(section_name)
    if cache_file.exists():
        return json.loads(cache_file.read_text()).get(key_name, None)
    return None


def save_cache(section_name, key_name, value):
    cache_file = _get_cache_file_path(section_name)
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
    else:
        data = {}
    data[key_name] = value
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data))


class Benchmark:
    def __init__(self, msg):
        self._msg = msg
        self._time = time.time()

    def __enter__(self):
        self._time = time.time()
        print(self._msg)
        return self

    def __exit__(self, *args, **kwargs):
        pass

    def mark(self, msg):
        print('{}: {:.02f} s'.format(msg, time.time() - self._time))
        self._time = time.time()
