from PyQt5 import QtCore


class AudioApi(QtCore.QObject):
    view_changed = QtCore.pyqtSignal([])
    selection_changed = QtCore.pyqtSignal([])

    def __init__(self, video_api):
        super().__init__()
        self._min = 0
        self._max = 0
        self._view_start = 0
        self._view_end = 0
        self._selection_start = None
        self._selection_end = None

        self._video_api = video_api
        self._video_api.timecodes_updated.connect(self._timecodes_updated)

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    @property
    def size(self):
        return self._max - self._min

    @property
    def view_start(self):
        return self._view_start

    @property
    def view_end(self):
        return self._view_end

    @property
    def view_size(self):
        return self._view_end - self._view_start

    @property
    def selection_start(self):
        return self._selection_start

    @property
    def selection_end(self):
        return self._selection_end

    @property
    def has_selection(self):
        return not (
            self._selection_start is None or self._selection_end is None)

    @property
    def selection_size(self):
        if not self.has_selection:
            return 0
        return self._selection_end - self._selection_start

    def unselect(self):
        self._selection_start = None
        self._selection_end = None
        self.selection_changed.emit()

    def select(self, start_pts, end_pts):
        self._selection_start = self._clip(start_pts)
        self._selection_end = self._clip(end_pts)
        self.selection_changed.emit()

    def view(self, start_pts, end_pts):
        self._view_start = self._clip(start_pts)
        self._view_end = self._clip(end_pts)
        self.view_changed.emit()

    def zoom_view(self, factor):
        factor = max(0.001, min(1, factor))
        old_origin = self.view_start - self._min
        old_view_size = self.view_size / 2
        self._view_start = self.min
        self._view_end = self._clip(self.min + self.size * factor)
        new_view_size = self.view_size / 2
        distance = old_origin - new_view_size + old_view_size
        self.move_view(distance)  # emits view_changed

    def move_view(self, distance):
        view_size = self.view_size
        if self._view_start + distance < self.min:
            self.view(self.min, self.min + view_size)
        elif self._view_end + distance > self.max:
            self.view(self.max - view_size, self.max)
        else:
            self.view(self._view_start + distance, self._view_end + distance)

    def _set_max_pts(self, max_pts):
        self._min = 0
        self._max = max_pts
        self.zoom_view(1)  # emits view_changed

    def _timecodes_updated(self):
        if self._video_api.timecodes:
            self._set_max_pts(self._video_api.timecodes[-1])
        else:
            self._set_max_pts(0)

    def _clip(self, value):
        return max(min(self._max, value), self._min)
