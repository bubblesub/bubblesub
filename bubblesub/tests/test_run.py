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

import os
import pathlib
import signal
import subprocess
import tempfile

import pytest

SERVER_NUM = 99
TIMEOUT = 4


@pytest.mark.ci
def test_run() -> None:
    try:
        subprocess.run(["xvfb-run", "bubblesub"], timeout=TIMEOUT, check=True)
    except subprocess.TimeoutExpired:
        tmp_dir = pathlib.Path(tempfile.gettempdir())
        lock_file = tmp_dir / f".X{SERVER_NUM}-lock"
        pid = int(lock_file.read_text().strip())
        os.kill(pid, signal.SIGINT)
    else:
        assert False, f"program not terminated after {TIMEOUT} s"
