![](https://cdn.rawgit.com/rr-/bubblesub/master/docs/logo.svg)

Simple extensible ASS subtitle editor for Linux

![](docs/screen.png)

## Features

- **Python - easily extend it however you want**
- Video preview
- Audio preview (spectrogram)
- Video band for quick assessment of scene boundaries
- Audio and video are synced at all times
- Spectrogram shows where subs start and end
- Slow playback support (with audio pitch correction)
- **I can sub an entire episode without ever having to touch the mouse**
- Mouse users are not excluded and can click their way to all the commands
- **Robust plugin API** (everything GUI is capable of can be done through the API)
- **Simple architecture** (Commands ↔ API ↔ GUI)
- Separate control for persistent inline comments (useful for translating)
- Newlines support in the editor
- Everything is aligned to video frames
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
- `$XDG_CONFIG_HOME/bubblesub/`: contains user configuration
    - `options.yaml`: general options
    - `hotkeys.conf`: configurable user hotkeys
    - `menu.conf`: configurable additional user menus
- `$XDG_CACHE_HOME/bubblesub/`: used to cache time codes and such

#### Example plugin: speech recognition of selected lines

```python
import argparse
import asyncio
import concurrent.futures
import io
import typing as T

import speech_recognition as sr

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.ass.event import Event
from bubblesub.cmd.common import SubtitlesSelection
from bubblesub.cfg.menu import MenuCommand, SubMenu


class SpeechRecognitionCommand(BaseCommand):
    names = ["sr", "google-speech-recognition"]
    help_text = (
        "Puts results of Google speech recognition "
        "for selected subtitles into their notes."
    )

    @property
    def is_enabled(self) -> bool:
        return (
            self.args.target.makes_sense
            and self.api.media.audio.has_audio_source
        )

    async def run(self) -> None:
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.run_in_background,
            await self.args.target.get_subtitles(),
        )

    def run_in_background(self, subs: T.List[Event]) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_sub = {
                executor.submit(self.recognize, sub): sub for sub in subs
            }
            completed, non_completed = concurrent.futures.wait(
                future_to_sub, timeout=5
            )

        with self.api.undo.capture():
            for future, sub in future_to_sub.items():
                if future not in completed:
                    continue
                try:
                    note = future.result()
                except sr.UnknownValueError:
                    self.api.log.warn(f"line #{sub.number}: not recognized")
                except sr.RequestError as ex:
                    self.api.log.error(f"line #{sub.number}: error ({ex})")
                else:
                    self.api.log.info(f"line #{sub.number}: OK")
                    if sub.note:
                        sub.note += r"\N" + note
                    else:
                        sub.note = note

        for future, sub in future_to_sub.items():
            if future in non_completed:
                self.api.log.info(f"line #{sub.number}: timeout")

    def recognize(self, sub: Event) -> str:
        self.api.log.info(f"line #{sub.number} - analyzing")
        recognizer = sr.Recognizer()
        with io.BytesIO() as handle:
            self.api.media.audio.save_wav(handle, [(sub.start, sub.end)])
            handle.seek(0, io.SEEK_SET)
            with sr.AudioFile(handle) as source:
                audio = recognizer.record(source)
            return recognizer.recognize_google(audio, language=self.args.code)

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-t",
            "--target",
            help="subtitles to process",
            type=lambda value: SubtitlesSelection(api, value),
            default="selected",
        )
        parser.add_argument("code", help="language code")


COMMANDS = [SpeechRecognitionCommand]
MENU = [
    SubMenu(
        "&Speech recognition",
        [
            MenuCommand("&Japanese", "sr ja"),
            MenuCommand("&German", "sr de"),
            MenuCommand("&French", "sr fr"),
            MenuCommand("&Italian", "sr it"),
            MenuCommand("&Auto", "sr auto"),
        ],
    )
]
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
- Run formatters: `python setup.py fmt`
  (`bubblesub` uses [`black`](https://github.com/ambv/black))
- Run type checks: `python setup.py mypy`
- Generate documentation: `python setup.py doc`
