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

import quamash
from PyQt5 import QtCore, QtWidgets

import bubblesub.ui.console
import bubblesub.ui.main_window
from bubblesub.api import Api
from bubblesub.cfg import ConfigError


def run(api: Api, args: argparse.Namespace) -> None:
    QtCore.pyqtRemoveInputHook()
    app = QtWidgets.QApplication(sys.argv + ["--name", "bubblesub"])
    app.setApplicationName("bubblesub")
    loop = quamash.QEventLoop(app)
    asyncio.set_event_loop(loop)

    console = bubblesub.ui.console.Console(api, None)

    app.aboutToQuit.connect(api.media.stop)

    try:
        if not args.no_config:
            api.cfg.load(api.cfg.DEFAULT_PATH)
            api.cmd.reload_commands()
    except ConfigError as ex:
        api.log.error(str(ex))
    if args.file:
        api.cmd.run_cmdline([["open", "--path", args.file]])

    main_window = bubblesub.ui.main_window.MainWindow(api, console)
    api.gui.set_main_window(main_window)

    api.media.start()
    main_window.show()

    with loop:
        loop.run_forever()

    if not args.no_config:
        assert api.cfg.root_dir is not None
        api.cfg.save(api.cfg.root_dir)
