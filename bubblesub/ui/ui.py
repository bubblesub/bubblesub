import asyncio
import sys
import bubblesub.ui.main_window
import quamash
from PyQt5 import QtWidgets


class Ui:
    def __init__(self, api, args):
        self._api = api
        self._args = args

    def run(self):
        app = QtWidgets.QApplication(sys.argv)
        loop = quamash.QEventLoop(app)
        asyncio.set_event_loop(loop)
        main_window = bubblesub.ui.main_window.MainWindow(self._api)
        self._api.gui.set_main_window(main_window)

        if self._args.file:
            self._api.subs.load_ass(self._args.file)

        main_window.show()
        with loop:
            loop.run_forever()
