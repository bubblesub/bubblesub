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

"""Tests for bubblesub command naming."""

import re
import typing as T

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.tests.common import api  # pylint: disable=unused-import


def normalize_class_name(name: str) -> T.Iterable[str]:
    """Cater for some conventions in class naming.

    For example, while commands are named sub-*, classes should be named
    Subtitle*.

    :param name: name to normalize
    :return: collection of names that are okay
    """

    def _handler(match: T.Match) -> str:
        if match.start() == 0:
            return match.group().lower()
        return "-" + match.group(0).lower()

    name = re.sub("Command$", "", name)

    # exceptions
    name = name.replace("Subtitles", "Sub")
    name = name.replace("Subtitle", "Sub")
    name = name.replace("SpectrogramSelection", "Sel")
    name = name.replace("Selection", "Sel")
    name = name.replace("Milliseconds", "Ms")
    name = name.replace("Command", "Cmd")

    name = re.sub("[A-Z]", _handler, name)

    yield name


def normalize_command_name(name: str) -> T.Iterable[str]:
    """Allow some leeway in command naming.

    :param name: name to normalize
    :return: collection of names that are okay
    """
    match = re.match(r"^((?P<prefix>[^/]*)\/)?(?P<stem>.*)$", name)
    assert match
    prefix = match.group("prefix")
    stem = match.group("stem").replace("/", "-")
    stem = stem.replace("subs", "sub")

    yield stem
    if prefix:
        yield f"{prefix}-{stem}"


def verify_name(cls_name: str, cmd_name: str) -> None:
    """Tests whether class name doesn't mismatch given command name.

    :param cls_name: name of the Python class for the command
    :param cmd_name: name of the command as in the UI
    """
    assert set(normalize_class_name(cls_name)) & set(
        normalize_command_name(cmd_name)
    ), f"Class name {cls_name!r} doesn't match command name {cmd_name!r}"


def test_command_naming(  # pylint: disable=redefined-outer-name
    api: Api
) -> None:
    """Checks class names for accordance with the command names they define.

    :param api: core API
    """
    api.cmd.reload_commands()

    assert len(api.cmd.get_all()) >= 1
    for cls in api.cmd.get_all():
        verify_name(cls.__name__, cls.names[0])

    api.cmd.unload()


def test_commands_have_names(  # pylint: disable=redefined-outer-name
    api: Api
) -> None:
    """Checks that commands have names.

    :param api: core API
    """
    api.cmd.reload_commands()

    assert len(api.cmd.get_all()) >= 1
    classes = BaseCommand.__subclasses__()
    assert len(classes) >= 1
    for cls in classes:
        assert isinstance(cls.names, list)
        assert len(cls.names) > 0

    api.cmd.unload()
