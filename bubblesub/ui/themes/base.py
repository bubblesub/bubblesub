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

from functools import lru_cache
from pathlib import Path

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication

from bubblesub.ui.assets import ASSETS_DIR


class BaseTheme:
    name: str = NotImplemented
    title: str = NotImplemented

    def apply(self) -> None:
        QApplication.setStyle("fusion")

        app = QApplication.instance()
        assert app
        app.setStyleSheet(
            (ASSETS_DIR / f"{self.name}.qss")
            .read_text()
            .replace("$ASSETS_DIR", str(ASSETS_DIR))
        )

    @property
    def palette(self) -> dict[str, str]:
        raise NotImplementedError("not implemented")

    @lru_cache(maxsize=None)
    def get_icon(self, name: str) -> QIcon:
        pixmap = QPixmap(str(self.get_icon_path(name))).scaled(
            QSize(48, 48),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        return QIcon(pixmap)

    def get_icon_path(self, name: str) -> Path:
        paths = [
            (ASSETS_DIR / self.name / f"icon-{name}.svg"),
            (ASSETS_DIR / self.name / f"icon-{name}.png"),
            (ASSETS_DIR / f"icon-{name}.svg"),
            (ASSETS_DIR / f"icon-{name}.png"),
        ]
        for path in paths:
            if path.exists():
                return path
        return Path("")
