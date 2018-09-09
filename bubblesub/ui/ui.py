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
import asyncio
import sys
from pathlib import Path

import quamash
from PyQt5 import QtCore
from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ui.console
import bubblesub.ui.main_window


def run(api: bubblesub.api.Api, args: argparse.Namespace) -> None:
    QtCore.pyqtRemoveInputHook()
    app = QtWidgets.QApplication(sys.argv + ['--name', 'bubblesub'])
    app.setApplicationName('bubblesub')
    loop = quamash.QEventLoop(app)
    asyncio.set_event_loop(loop)

    console = bubblesub.ui.console.Console(api, None)

    app.aboutToQuit.connect(api.media.stop)

    api.cmd.load_commands(Path(__file__).parent.parent / 'cmd')
    if not args.no_config:
        api.opt.load(api.opt.DEFAULT_PATH)
        api.cmd.load_commands(api.opt.root_dir / 'scripts')
    if args.file:
        api.cmd.execute(['open', '--path', args.file])

    main_window = bubblesub.ui.main_window.MainWindow(api, console)
    api.gui.set_main_window(main_window)

    api.media.start()
    main_window.show()

    with loop:
        loop.run_forever()

    if not args.no_config:
        assert api.opt.root_dir is not None
        api.opt.save(api.opt.root_dir)
