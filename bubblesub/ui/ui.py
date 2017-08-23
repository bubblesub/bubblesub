import asyncio
import sys
import time
import traceback
import io
import bubblesub.ui.main_window
import bubblesub.ui.util
import quamash
from PyQt5 import QtWidgets


def excepthook(exception_type, exception_value, traceback_object):
    separator = '-' * 80

    with io.StringIO() as handle:
        traceback.print_tb(traceback_object, None, handle)
        handle.seek(0)
        traceback_info = handle.read()

    msg = '\n'.join([
        'An unhandled exception occurred.',
        time.strftime("%Y-%m-%d, %H:%M:%S"),
        separator,
        '%s: \n%s' % (str(exception_type), str(exception_value)),
        separator,
        traceback_info
    ])

    print(msg)
    bubblesub.ui.util.error(msg)


sys.excepthook = excepthook


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
