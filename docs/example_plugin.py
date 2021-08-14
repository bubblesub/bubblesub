# Example plugin: speech recognition of selected lines
import argparse
import asyncio
import concurrent.futures
import io
import typing as T

import speech_recognition as sr
from ass_parser import AssEvent

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.cfg.menu import MenuCommand, SubMenu
from bubblesub.cmd.common import SubtitlesSelection


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
            and self.api.audio.current_stream
            and self.api.audio.current_stream.is_ready
        )

    async def run(self) -> None:
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.run_in_background,
            await self.args.target.get_subtitles(),
        )

    def run_in_background(self, events: T.List[AssEvent]) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_event = {
                executor.submit(self.recognize, event): event
                for event in events
            }
            completed, non_completed = concurrent.futures.wait(
                future_to_event, timeout=5
            )

        with self.api.undo.capture():
            for future, event in future_to_event.items():
                if future not in completed:
                    continue
                try:
                    note = future.result()
                except sr.UnknownValueError:
                    self.api.log.warn(f"line #{event.number}: not recognized")
                except sr.RequestError as ex:
                    self.api.log.error(f"line #{event.number}: error ({ex})")
                else:
                    self.api.log.info(f"line #{event.number}: OK")
                    if event.note:
                        event.note += r"\N" + note
                    else:
                        event.note = note

        for future, event in future_to_event.items():
            if future in non_completed:
                self.api.log.info(f"line #{event.number}: timeout")

    def recognize(self, event: AssEvent) -> str:
        self.api.log.info(f"line #{event.number} - analyzing")
        recognizer = sr.Recognizer()
        with io.BytesIO() as handle:
            self.api.audio.current_stream.save_wav(
                handle, event.start, event.end
            )
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
