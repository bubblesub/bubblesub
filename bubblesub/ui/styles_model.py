import enum
from PyQt5 import QtCore
from PyQt5 import QtGui


def _serialize_color(value):
    return QtGui.QColor(*value)


def _deserialize_color(color):
    return (color.red(), color.green(), color.blue(), color.alpha())


class StylesModelColumn(enum.IntEnum):
    Name = 0
    FontName = 1
    FontSize = 2
    Bold = 3
    Italic = 4
    Underline = 5
    StrikeOut = 6
    PrimaryColor = 7
    SecondaryColor = 8
    BackColor = 9
    OutlineColor = 10
    ShadowWidth = 11
    OutlineWidth = 12
    ScaleX = 13
    ScaleY = 14
    Angle = 15
    Spacing = 16
    MarginLeft = 17
    MarginRight = 18
    MarginVertical = 19
    Alignment = 20


class StylesModel(QtCore.QAbstractTableModel):
    def __init__(self, api, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._styles = api.subs.styles
        self._styles.item_changed.connect(self._proxy_data_changed)
        self._styles.items_inserted.connect(self._proxy_items_inserted)
        self._styles.items_removed.connect(self._proxy_items_removed)

    def rowCount(self, _parent=QtCore.QModelIndex()):
        return len(self._styles)

    def columnCount(self, _parent=QtCore.QModelIndex()):
        return len(StylesModelColumn)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            row_idx = index.row()
            column_idx = index.column()

            style = self._styles[row_idx]
            if column_idx == StylesModelColumn.Name:
                return style.name
            elif column_idx == StylesModelColumn.FontName:
                return style.font_name
            elif column_idx == StylesModelColumn.FontSize:
                return int(style.font_size)
            elif column_idx == StylesModelColumn.Bold:
                return style.bold
            elif column_idx == StylesModelColumn.Italic:
                return style.italic
            elif column_idx == StylesModelColumn.Underline:
                return style.underline
            elif column_idx == StylesModelColumn.StrikeOut:
                return style.strike_out
            elif column_idx == StylesModelColumn.PrimaryColor:
                return _serialize_color(style.primary_color)
            elif column_idx == StylesModelColumn.SecondaryColor:
                return _serialize_color(style.secondary_color)
            elif column_idx == StylesModelColumn.BackColor:
                return _serialize_color(style.back_color)
            elif column_idx == StylesModelColumn.OutlineColor:
                return _serialize_color(style.outline_color)
            elif column_idx == StylesModelColumn.ShadowWidth:
                return float(style.shadow)
            elif column_idx == StylesModelColumn.OutlineWidth:
                return float(style.outline)
            elif column_idx == StylesModelColumn.ScaleX:
                return float(style.scale_x)
            elif column_idx == StylesModelColumn.ScaleY:
                return float(style.scale_y)
            elif column_idx == StylesModelColumn.Angle:
                return float(style.angle)
            elif column_idx == StylesModelColumn.Spacing:
                return float(style.spacing)
            elif column_idx == StylesModelColumn.MarginLeft:
                return int(style.margin_left)
            elif column_idx == StylesModelColumn.MarginRight:
                return int(style.margin_right)
            elif column_idx == StylesModelColumn.MarginVertical:
                return int(style.margin_vertical)
            elif column_idx == StylesModelColumn.Alignment:
                return style.alignment
            assert False

        return QtCore.QVariant()

    def setData(self, index, value, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.EditRole:
            row_idx = index.row()
            column_idx = index.column()
            if row_idx not in range(len(self._styles)):
                return False

            style = self._styles[row_idx]
            if column_idx == StylesModelColumn.Name:
                style.name = value
            elif column_idx == StylesModelColumn.FontName:
                style.font_name = value
            elif column_idx == StylesModelColumn.FontSize:
                style.font_size = int(value)
            elif column_idx == StylesModelColumn.Bold:
                style.bold = bool(value)
            elif column_idx == StylesModelColumn.Italic:
                style.italic = bool(value)
            elif column_idx == StylesModelColumn.Underline:
                style.underline = bool(value)
            elif column_idx == StylesModelColumn.StrikeOut:
                style.strike_out = bool(value)
            elif column_idx == StylesModelColumn.PrimaryColor:
                style.primary_color = _deserialize_color(value)
            elif column_idx == StylesModelColumn.SecondaryColor:
                style.secondary_color = _deserialize_color(value)
            elif column_idx == StylesModelColumn.BackColor:
                style.back_color = _deserialize_color(value)
            elif column_idx == StylesModelColumn.OutlineColor:
                style.outline_color = _deserialize_color(value)
            elif column_idx == StylesModelColumn.ShadowWidth:
                style.shadow = float(value)
            elif column_idx == StylesModelColumn.OutlineWidth:
                style.outline = float(value)
            elif column_idx == StylesModelColumn.ScaleX:
                style.scale_x = float(value)
            elif column_idx == StylesModelColumn.ScaleY:
                style.scale_y = float(value)
            elif column_idx == StylesModelColumn.Spacing:
                style.spacing = float(value)
            elif column_idx == StylesModelColumn.Angle:
                style.angle = float(value)
            elif column_idx == StylesModelColumn.MarginLeft:
                style.margin_left = int(value)
            elif column_idx == StylesModelColumn.MarginRight:
                style.margin_right = int(value)
            elif column_idx == StylesModelColumn.MarginVertical:
                style.margin_vertical = int(value)
            elif column_idx == StylesModelColumn.Alignment:
                style.alignment = int(value)
            else:
                return False
            return True
        return False

    def flags(self, index):
        if index.column() == StylesModelColumn.Name:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        return (
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemIsEditable)

    def _proxy_data_changed(self, idx):
        self.dataChanged.emit(
            self.index(idx, 0),
            self.index(idx, self.columnCount() - 1),
            [QtCore.Qt.DisplayRole | QtCore.Qt.BackgroundRole])

    def _proxy_items_inserted(self, idx, count):
        if count:
            self.rowsInserted.emit(QtCore.QModelIndex(), idx, idx + count - 1)

    def _proxy_items_removed(self, idx, count):
        if count:
            self.rowsRemoved.emit(QtCore.QModelIndex(), idx, idx + count - 1)
