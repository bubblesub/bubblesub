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

    if not args.no_config:
        api.opt.load(api.opt.DEFAULT_PATH)

    main_window = bubblesub.ui.main_window.MainWindow(api)
    api.gui.set_main_window(main_window)

    if not args.no_config:
        assert api.opt.location is not None
        try:
            api.cmd.load_plugins(api.opt.location / 'scripts')
        except Exception as ex:
            api.log.error(str(ex))

    api.media.start()
    main_window.show()

    if args.file:
        api.subs.load_ass(args.file)

    with loop:
        loop.run_forever()

    if not args.no_config:
        assert api.opt.location is not None
        api.opt.save(api.opt.location)
