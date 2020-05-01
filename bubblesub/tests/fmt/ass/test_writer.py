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

"""Tests for bubblesub.fmt.ass.writer module."""

import io
import tempfile
from pathlib import Path
from unittest.mock import patch

from bubblesub.fmt.ass.file import AssFile
from bubblesub.fmt.ass.writer import write_ass


@patch(
    "bubblesub.fmt.ass.writer.write_meta",
    side_effect=lambda ass_file, handle: handle.write("META"),
)
@patch(
    "bubblesub.fmt.ass.writer.write_styles",
    side_effect=lambda ass_file, handle: handle.write("STYLES"),
)
@patch(
    "bubblesub.fmt.ass.writer.write_events",
    side_effect=lambda ass_file, handle: handle.write("EVENTS"),
)
def test_write_ass_handle(
    write_meta_mock, write_styles_mock, write_events_mock
) -> None:
    """Test the write_ass function for file handles.

    :param write_meta_mock: mock to write_meta function
    :param write_styles_mock: mock to write_styles function
    :param write_events_mock: mock to write_events function
    """
    handle = io.StringIO()
    ass_file = AssFile()

    write_ass(ass_file, handle)
    handle.seek(0)
    content = handle.read()

    assert content == "META\nSTYLES\nEVENTS"


@patch(
    "bubblesub.fmt.ass.writer.write_meta",
    side_effect=lambda ass_file, handle: handle.write("META"),
)
@patch(
    "bubblesub.fmt.ass.writer.write_styles",
    side_effect=lambda ass_file, handle: handle.write("STYLES"),
)
@patch(
    "bubblesub.fmt.ass.writer.write_events",
    side_effect=lambda ass_file, handle: handle.write("EVENTS"),
)
def test_write_ass_file(
    write_meta_mock, write_styles_mock, write_events_mock
) -> None:
    """Test the write_ass function for file paths.

    :param write_meta_mock: mock to write_meta function
    :param write_styles_mock: mock to write_styles function
    :param write_events_mock: mock to write_events function
    """
    ass_file = AssFile()
    with tempfile.TemporaryDirectory() as dir_name:
        path = Path(dir_name) / "tmp.ass"

        write_ass(ass_file, path)
        content = path.read_text()

    assert content == "META\nSTYLES\nEVENTS"
