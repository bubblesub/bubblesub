# bubblesub - ASS subtitle editor
# Copyright (C) 2018 Marcin Kurczewski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse

from PyQt5.QtWidgets import QMainWindow

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand, CommandCanceled
from bubblesub.cmd.common import FancyPath
from bubblesub.ui.util import (
    AUDIO_FILE_FILTER,
    SUBS_FILE_FILTER,
    VIDEO_FILE_FILTER,
    save_dialog,
    show_prompt,
)


class NewCommand(BaseCommand):
    names = ["new"]
    help_text = "Opens a new file."
    help_text_extra = (
        "Prompts user to save the current file if there are unsaved changes."
    )

    async def run(self) -> None:
        if await self.api.gui.confirm_unsaved_changes():
            self.api.subs.unload()


class OpenCommand(BaseCommand):
    names = ["open"]
    help_text = "Opens an existing subtitles file."
    help_text_extra = (
        "Prompts user to save the current file if there are unsaved changes. "
        "Prompts user to choose where to load the file from if the path "
        "wasn't specified in the command arguments."
    )

    async def run(self) -> None:
        if not await self.api.gui.confirm_unsaved_changes():
            return

        path = await self.args.path.get_load_path(
            file_filter=SUBS_FILE_FILTER,
        )

        self.api.subs.load_ass(path)
        self.api.log.info(f"opened {path}")

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-p",
            "--path",
            help="path to load the subtitles from",
            type=lambda value: FancyPath(api, value),
            default="",
        )


class ReopenCommand(BaseCommand):
    names = ["reopen", "reload"]
    help_text = "Reloads the currently loaded subtitles file from disk."
    help_text_extra = (
        "Prompts user to save the current file if there are unsaved changes. "
        "Resets undo stack."
    )

    @property
    def is_enabled(self) -> bool:
        return bool(self.api.subs.path)

    async def run(self) -> None:
        if not await self.api.gui.confirm_unsaved_changes():
            return

        path = self.api.subs.path
        assert path
        self.api.subs.load_ass(path)
        self.api.log.info(f"reloaded {path}")

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-p",
            "--path",
            help="path to load the subtitles from",
            type=lambda value: FancyPath(api, value),
            default="",
        )


class SaveCommand(BaseCommand):
    names = ["save"]
    help_text = "Saves the current subtitles to an ASS file."
    help_text_extra = (
        "If the currently loaded subtitles weren't ever saved, prompts user "
        "to choose where to save the file to."
    )

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QMainWindow) -> None:
        path = self.api.subs.path
        if not path:
            path = await save_dialog(
                main_window,
                file_filter=SUBS_FILE_FILTER,
                directory=self.api.gui.get_dialog_dir(),
            )
            if not path:
                raise CommandCanceled

        self.api.subs.save_ass(path, remember_path=True)
        self.api.log.info(f"saved subtitles to {path}")


class SaveAsCommand(BaseCommand):
    names = ["save-as"]
    help_text = "Saves the current subtitles to an ASS file."
    help_text_extra = (
        "Prompts user to choose where to save the file to if the path wasn't "
        "specified in the command arguments."
    )

    async def run(self) -> None:
        path = await self.args.path.get_save_path(
            file_filter=SUBS_FILE_FILTER,
            directory=self.api.gui.get_dialog_dir(),
            default_file_name=(
                self.api.subs.path.name if self.api.subs.path else None
            ),
        )

        self.api.subs.save_ass(path, remember_path=True)
        self.api.log.info(f"saved subtitles to {path}")

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-p",
            "--path",
            help="optional path to save the subtitles to",
            type=lambda value: FancyPath(api, value),
            default="",
        )


class LoadVideoCommand(BaseCommand):
    names = ["load-video"]
    help_text = "Loads a video file for video playback."
    help_text_extra = (
        "Prompts user to choose where to load the file from if the path "
        "wasn't specified in the command arguments."
    )

    async def run(self) -> None:
        await self.api.gui.exec(self._run_with_gui)

    async def _run_with_gui(self, main_window: QMainWindow) -> None:
        path = await self.args.path.get_load_path(
            file_filter=VIDEO_FILE_FILTER,
        )

        # show the prompt earlier before loading anything
        # to avoid distracting the user with loading video in the background
        load_audio = await show_prompt(
            f"Do you want to use this video file as the audio source?",
            main_window,
        )

        self.api.video.load_stream(path)
        self.api.subs.remember_video_path_if_needed(path)
        if load_audio:
            self.api.audio.load_stream(path)
            self.api.subs.remember_audio_path_if_needed(path)

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-p",
            "--path",
            help="path to load the video from",
            type=lambda value: FancyPath(api, value),
            default="",
        )


class CycleVideoCommand(BaseCommand):
    names = ["cycle-video"]
    help_text = "Switches to the next loaded video stream."

    async def run(self) -> None:
        self.api.video.cycle_streams()


class SwitchVideoCommand(BaseCommand):
    names = ["switch-video"]
    help_text = "Switches to the chosen loaded video stream."

    async def run(self) -> None:
        idx = self.args.index
        uid = self.api.video.streams[idx].uid
        self.api.video.switch_stream(uid)

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "index", help="index of the stream to switch to", type=int
        )


class ListVideoCommand(BaseCommand):
    names = ["list-video"]
    help_text = "Lists loaded video streams in the console."

    async def run(self) -> None:
        if not self.api.video.streams:
            self.api.log.warn("no loaded video streams")
            return

        for idx, stream in enumerate(self.api.video.streams):
            marker = "X" if stream == self.api.video.current_stream else " "
            self.api.log.info(f"{marker} {idx}. {stream.uid} {stream.path} ")


class LoadAudioCommand(BaseCommand):
    names = ["load-audio"]
    help_text = "Loads an audio file for audio playback."
    help_text_extra = (
        "Prompts user to choose where to load the file from if the path "
        "wasn't specified in the command arguments."
    )

    async def run(self) -> None:
        path = await self.args.path.get_load_path(
            file_filter=AUDIO_FILE_FILTER,
        )

        self.api.audio.load_stream(path)
        self.api.subs.remember_audio_path_if_needed(path)

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-p",
            "--path",
            help="path to load the audio from",
            type=lambda value: FancyPath(api, value),
            default="",
        )


class CycleAudioCommand(BaseCommand):
    names = ["cycle-audio"]
    help_text = "Switches to the next loaded audio stream."

    async def run(self) -> None:
        self.api.audio.cycle_streams()


class SwitchAudioCommand(BaseCommand):
    names = ["switch-audio"]
    help_text = "Switches to the chosen loaded audio stream."

    async def run(self) -> None:
        idx = self.args.index
        uid = self.api.audio.streams[idx].uid
        self.api.audio.switch_stream(uid)

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "index", help="index of the stream to switch to", type=int
        )


class ListAudioCommand(BaseCommand):
    names = ["list-audio"]
    help_text = "Lists loaded audio streams in the console."

    async def run(self) -> None:
        if not self.api.audio.streams:
            self.api.log.warn("no loaded audio streams")
            return

        for idx, stream in enumerate(self.api.audio.streams):
            marker = "X" if stream == self.api.audio.current_stream else " "
            self.api.log.info(
                f"{marker} {idx}. {stream.uid} {stream.path} "
                f"(delay: {stream.delay} ms)"
            )


class SetAudioDelayCommand(BaseCommand):
    names = ["set-audio-delay"]
    help_text = "Sets a delay to the currently loaded audio stream."
    help_text_extra = (
        "Positive delay values will cause the audio to play later, "
        "while negative ones will cause it to play earlier."
    )

    @property
    def is_enabled(self) -> bool:
        return self.api.audio.current_stream

    async def run(self) -> None:
        self.api.audio.current_stream.delay = self.args.delay

    @staticmethod
    def decorate_parser(api: Api, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "delay", help="amount to dealy the stream", type=int
        )


class UnloadVideoCommand(BaseCommand):
    names = ["unload-video"]
    help_text = "Unloads currently loaded video file."

    async def run(self) -> None:
        self.api.video.unload_current_stream()


class UnloadAudioCommand(BaseCommand):
    names = ["unload-audio"]
    help_text = "Unloads currently loaded audio file."

    async def run(self) -> None:
        self.api.audio.unload_current_stream()


COMMANDS = [
    NewCommand,
    OpenCommand,
    ReopenCommand,
    SaveCommand,
    SaveAsCommand,
    LoadVideoCommand,
    CycleVideoCommand,
    SwitchVideoCommand,
    ListVideoCommand,
    LoadAudioCommand,
    CycleAudioCommand,
    SwitchAudioCommand,
    ListAudioCommand,
    UnloadVideoCommand,
    UnloadAudioCommand,
    SetAudioDelayCommand,
]
