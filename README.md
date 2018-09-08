![](https://cdn.rawgit.com/rr-/bubblesub/master/docs/logo.svg)

Simple extensible ASS subtitle editor for Linux

![](docs/screen.png)

## Features

- **Python - easily extend it however you want**
- Video preview
- Audio preview (spectrogram)
- Audio and video are synced at all times
- Spectrogram shows where subs start and end
- Slow playback support (with audio pitch correction)
- **I can sub an entire episode without ever having to touch the mouse**
- Mouse users are not excluded and can click their way to all the commands
- **Robust plugin API** (everything GUI is capable of can be done through the API)
- **Simple architecture** (Commands ↔ API ↔ GUI)
- Separate control for persistent inline comments (useful for translating)
- Newlines support in the editor
- Seeking is aligned to video frames
- Style editor with realistic preview
- No bloat

## Installation

- Install system dependencies
    - [`libmpv`](https://github.com/mpv-player/mpv.git)
    - [`ffms`](https://github.com/FFMS/ffms2)
    - [`fftw`](https://github.com/FFTW/fftw3)
    - `QT5` and `PyQT5` bindings
- Clone the repository: `git clone https://github.com/rr-/bubblesub`
- Enter its directory: `cd bubblesub`
- Install `bubblesub`: `pip install --user .`

## Documentation

- For API documentation, please consult the docstrings in the `bubblesub.api`
module.
- For default hotkeys and commands descriptions, please consult [this
file](https://github.com/rr-/bubblesub/tree/master/docs/doc.md).

## Configuration and plugins

- `$XDG_CONFIG_HOME/bubblesub/scripts`: contains user plugins
- `$XDG_CONFIG_HOME/bubblesub/`: contains user configuration in JSON and INI
- `$XDG_CACHE_HOME/bubblesub/`: used to cache time codes and such

#### Example plugin: speech recognition of selected lines

```python
import argparse
import asyncio
import io

import speech_recognition as sr
from bubblesub.api.cmd import BaseCommand
from bubblesub.opt.menu import MenuCommand
from bubblesub.opt.menu import SubMenu


async def _work(language, api, line):
    api.log.info(f'line #{line.number} - analyzing')
    recognizer = sr.Recognizer()
    try:
        def recognize():
            with io.BytesIO() as handle:
                api.media.audio.save_wav(handle, line.start, line.end)
                handle.seek(0, io.SEEK_SET)
                with sr.AudioFile(handle) as source:
                    audio = recognizer.record(source)
            return recognizer.recognize_google(audio, language=language)

        # don't clog the UI thread
        note = await asyncio.get_event_loop().run_in_executor(None, recognize)
    except sr.UnknownValueError:
        api.log.warn(f'line #{line.number}: not recognized')
    except sr.RequestError as ex:
        api.log.error(f'line #{line.number}: error ({ex})')
    else:
        api.log.info(f'line #{line.number}: OK')
        with api.undo.capture():
            if line.note:
                line.note = line.note + r'\N' + note
            else:
                line.note = note


class SpeechRecognitionCommand(BaseCommand):
    names = ['google-speech-recognition']
    help_text = (
        'Puts results of Google speech recognition '
        'for selected subtitles into their notes.'
    )

    @property
    def is_enabled(self):
        return self.api.subs.has_selection \
            and self.api.media.audio.has_audio_source

    async def run(self):
        for line in self.api.subs.selected_events:
            await _work(self.args.code, self.api, line)

    @staticmethod
    def _decorate_parser(parser: argparse.ArgumentParser) -> None:
        parser.add_argument('code', help='language code')


def register(cmd_api):
    cmd_api.register_plugin_command(
        SpeechRecognitionCommand,
        SubMenu(
            '&Speech recognition',
            [
                MenuCommand('&Japanese', '/google-speech-recognition ja'),
                MenuCommand('&German', '/google-speech-recognition de'),
                MenuCommand('&French', '/google-speech-recognition fr'),
                MenuCommand('&Italian', '/google-speech-recognition it'),
                MenuCommand('&Auto', '/google-speech-recognition auto')
            ]
        )
    )
```

## Questions

1. Why not aegisub?

    Because it doesn't cover my needs, it's too convoluted and its development
    is too slow.

2. Windows builds?

    This is a hobby project and wrestling with Windows to have it compile a
    single C dependency library isn't my idea of a well-spent afternoon.
    It should be possible with MSYS2.

## Contributing

1. I want to report a bug.

    Please use GitHub issues.

2. I want a feature.

    Chances are I'm too busy to work on features I don't personally need,
    so pull requests are strongly encouraged.

**Basic development guidelines**

- Install development dependencies: `pip install --user -e '.[develop]'`
- Run tests: `python setup.py test`
- Run linters: `python setup.py lint`
- Run type checks: `python setup.py mypy`
- Generate documentation: `python setup.py doc`
