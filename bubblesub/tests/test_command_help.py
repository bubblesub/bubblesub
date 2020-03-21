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

"""Tests for bubblesub command help text."""

from bubblesub.api import Api
from bubblesub.api.cmd import BaseCommand
from bubblesub.tests.common import api  # pylint: disable=unused-import


def test_commands_have_help_text(  # pylint: disable=redefined-outer-name
    api: Api,
) -> None:
    """Checks that commands have help text.

    :param api: core API
    """
    api.cmd.reload_commands()

    assert len(api.cmd.get_all()) >= 1
    classes = BaseCommand.__subclasses__()
    assert len(classes) >= 1
    for cls in classes:
        assert isinstance(cls.help_text, str)
        assert len(cls.help_text) > 0

    api.cmd.unload()


def test_commands_help_text_format(  # pylint: disable=redefined-outer-name
    api: Api,
) -> None:
    """Checks that commands' help text is a single sentence and has no trailing
    whitespace.

    :param api: core API
    """
    api.cmd.reload_commands()

    assert len(api.cmd.get_all()) >= 1
    classes = BaseCommand.__subclasses__()
    assert len(classes) >= 1
    for cls in classes:
        assert isinstance(cls.help_text, str)
        assert cls.help_text.count(".") == 1, cls
        assert cls.help_text.strip() == cls.help_text, cls
        assert cls.help_text_extra.strip() == cls.help_text_extra, cls

    api.cmd.unload()
