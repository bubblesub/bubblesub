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
from PyQt5 import QtCore
from PyQt5 import QtWidgets

import bubblesub.api
import bubblesub.ui.main_window
import bubblesub.ui.util


def run(api: bubblesub.api.Api, args: argparse.Namespace) -> None:
    QtCore.pyqtRemoveInputHook()
    app = QtWidgets.QApplication(sys.argv)
    loop = quamash.QEventLoop(app)
    asyncio.set_event_loop(loop)

    app.aboutToQuit.connect(api.media.stop)

    if not args.no_config:
        api.opt.load(api.opt.DEFAULT_PATH)

    main_window = bubblesub.ui.main_window.MainWindow(api)
    api.gui.set_main_window(main_window)

    if not args.no_config:
        assert api.opt.root_dir is not None
        try:
            api.cmd.load_plugins(api.opt.root_dir / 'scripts')
        except Exception as ex:  # pylint: disable=broad-except
            api.log.error(str(ex))

    api.media.start()
    main_window.show()

    if args.file:
        api.cmd.run(api.cmd.get('file/open', [args.file]))

    with loop:
        loop.run_forever()

    if not args.no_config:
        assert api.opt.root_dir is not None
        api.opt.save(api.opt.root_dir)
