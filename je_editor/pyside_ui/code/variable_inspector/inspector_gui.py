"""
變數檢視器：一張可搜尋的表，顯示主控台或暫停中的除錯器的變數
The variable inspector: a searchable table of a console's or a paused debugger's variables.

要顯示誰的變數由 ``VariableHub`` 決定，列怎麼算在 ``utils/variable_inspector``。
Whose variables to show is ``VariableHub``'s business, and how the rows are
worked out is in ``utils/variable_inspector``.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QSortFilterProxyModel, Qt, QTimer
from PySide6.QtGui import QHideEvent, QShowEvent
from PySide6.QtWidgets import QLabel, QLineEdit, QTableView, QVBoxLayout, QWidget

from je_editor.pyside_ui.code.variable_inspector.variable_hub import VariableHub, VariableSource
from je_editor.utils.multi_language.multi_language_wrapper import language_wrapper
from je_editor.utils.variable_inspector.variable_rows import VariableRow, namespace_rows, parse_value

# 名稱、型別、值 / Name, type, value
_COLUMN_COUNT = 3
_VALUE_COLUMN = 2
# 多久看一次命名空間 / How often the namespace is looked at
_REFRESH_INTERVAL_MS = 500


class VariableModel(QAbstractTableModel):
    """
    變數模型：顯示一個命名空間，或一組已經算好的列
    Variable model: shows a namespace, or a set of rows worked out elsewhere.
    """

    def __init__(self, parent: QObject | None = None, namespace: dict | None = None) -> None:
        """
        :param parent: Qt 父物件；是檢視器時，表格互動中不更新
            the Qt parent; when it is the inspector, nothing is refreshed while its table is in use
        :param namespace: 一開始要顯示的命名空間 / the namespace to start with
        """
        super().__init__(parent)
        self._namespace: dict = namespace if namespace is not None else {}
        self._hidden: Mapping[str, object] = {}
        # 不是 None 時顯示這些列，而且不能編輯（除錯器的變數在另一個行程）
        # When not None these rows are shown, read-only (a debugger's variables live in another process)
        self._given_rows: list[VariableRow] | None = None
        self._rows: list[VariableRow] = []

    @property
    def namespace(self) -> dict:
        """目前顯示的命名空間 / The namespace being shown."""
        return self._namespace

    @namespace.setter
    def namespace(self, ns: dict) -> None:
        self.show_namespace(ns)

    @property
    def variables(self) -> list[VariableRow]:
        """目前顯示的列 / The rows being shown."""
        return list(self._rows)

    def show_namespace(self, namespace: dict, hidden: Mapping[str, object] | None = None) -> None:
        """
        改成顯示一個命名空間，值可以編輯
        Show a namespace from now on; its values can be edited.

        :param namespace: 命名空間本身，編輯會寫回去 / the namespace itself, which edits are written to
        :param hidden: 裡面不屬於使用者的名稱 / the names in it that are not the user's
        """
        self._namespace = namespace
        self._hidden = hidden or {}
        self._given_rows = None
        self.update_data()

    def show_rows(self, rows: list[VariableRow]) -> None:
        """
        改成顯示一組算好的列，唯讀
        Show a set of rows worked out elsewhere, read-only.

        :param rows: 要顯示的列 / the rows to show
        """
        self._given_rows = list(rows)
        self.update_data()

    def editable(self) -> bool:
        """值能不能改 / Whether the values can be changed."""
        return self._given_rows is None

    def update_data(self) -> None:
        """
        重新算一次列，有變才更新表格
        Work the rows out again, and update the table only when they changed.

        每半秒就重設一次模型的話，選取與捲動位置每半秒就掉一次。
        A model reset twice a second dropped the selection and the scroll
        position twice a second.
        """
        parent_widget = self.parent()
        # 避免在 table 正在互動時更新，造成衝突
        # Avoid updating while table is in active state
        table = getattr(parent_widget, "table", None)
        if table is not None and table.state() != QTableView.State.NoState:
            return
        rows = namespace_rows(self._namespace, self._hidden) if self._given_rows is None else self._given_rows
        if rows == self._rows:
            return
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        # 回傳變數數量 / return number of variables
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        # 固定三欄：名稱、型別、值 / fixed 3 columns: name, type, value
        return _COLUMN_COUNT

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        # 提供表格顯示的資料
        # Provide data for table display
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            row = self._rows[index.row()]
            return (row.name, row.type_name, row.value_text)[index.column()]
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        # 設定表頭文字 (支援多語系)
        # Set header labels (multi-language support)
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return [
                language_wrapper.language_word_dict.get("variable_inspector_var_name"),
                language_wrapper.language_word_dict.get("variable_inspector_var_type"),
                language_wrapper.language_word_dict.get("variable_inspector_var_value")
            ][section]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        # 設定欄位屬性，僅允許「值」欄可編輯
        # Set column flags, only "value" column is editable
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return Qt.ItemFlag.NoItemFlags
        base = super().flags(index)
        if index.column() == _VALUE_COLUMN and self.editable():
            base |= Qt.ItemFlag.ItemIsEditable
        return base

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """
        把輸入的值寫回命名空間
        Write the value typed back to the namespace.

        只接受字面值，不執行輸入的東西；不是字面值的當成字串。
        Literals only, so nothing typed is run; anything else is taken as a string.

        :return: 有寫入時為 ``True`` / ``True`` when something was written
        """
        if role != Qt.ItemDataRole.EditRole or index.column() != _VALUE_COLUMN or not self.editable():
            return False
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return False
        row = self._rows[index.row()]
        text = str(value)
        # 沒改就不寫：截短過的文字寫回去會把原本的值換成那段文字
        # Unchanged text is not written: a cut text written back would replace the value with the cut text
        if text == "" or text == row.value_text or row.name not in self._namespace:
            return False
        self._namespace[row.name] = parse_value(text)
        rows = namespace_rows(self._namespace, self._hidden)
        if len(rows) != len(self._rows):
            self.beginResetModel()
            self._rows = rows
            self.endResetModel()
            return True
        self._rows = rows
        self.dataChanged.emit(self.index(index.row(), 0), self.index(index.row(), _VALUE_COLUMN),
                              [Qt.ItemDataRole.DisplayRole])
        return True


class VariableProxy(QSortFilterProxyModel):
    """
    過濾代理模型：支援搜尋與編輯轉發
    Proxy model: supports filtering and forwards editing
    """

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        # 將編輯操作轉發到原始模型
        # Forward editing to source model
        return self.sourceModel().setData(
            self.mapToSource(index), value, role
        )


class VariableInspector(QWidget):
    """
    變數檢視器：顯示並搜尋主控台或暫停中的除錯器的變數
    Variable inspector: shows and searches a console's or a paused debugger's variables.
    """

    def __init__(self, hub: VariableHub | None = None) -> None:
        """
        :param hub: 變數的來源；沒有時顯示說明，等 ``set_hub`` 交給它
            where the variables come from; without one a note is shown until ``set_hub`` gives one
        """
        super().__init__()
        self.setWindowTitle(language_wrapper.language_word_dict.get("variable_inspector_title"))
        layout = QVBoxLayout(self)

        # 現在顯示的是誰的變數 / Whose variables are being shown
        self.source_label = QLabel()
        self.source_label.setWordWrap(True)
        self.source_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.source_label)

        # 搜尋框 / search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(language_wrapper.language_word_dict.get("variable_inspector_search"))
        layout.addWidget(QLabel(language_wrapper.language_word_dict.get("variable_inspector_search")))
        layout.addWidget(self.search_box)

        # 模型與代理模型 / model and proxy model
        self.model = VariableModel(parent=self)
        self.proxy_model = VariableProxy(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)  # 不分大小寫 / case-insensitive
        self.proxy_model.setFilterKeyColumn(0)  # 僅針對變數名稱過濾 / filter by variable name

        # 表格顯示 / table view
        self.table = QTableView()
        self.table.setModel(self.proxy_model)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            self.table.horizontalHeader().ResizeMode.Stretch
        )
        layout.addWidget(self.table, stretch=1)

        # 綁定搜尋框輸入事件 / bind search box input
        self.search_box.textChanged.connect(
            self.proxy_model.setFilterFixedString
        )

        # 看得到的時候才定時更新：藏在別的分頁後面時不必每半秒算一次
        # Refreshed on a timer only while it can be seen: behind another tab
        # there is no reason to work the rows out twice a second
        self.timer = QTimer(self)
        self.timer.setInterval(_REFRESH_INTERVAL_MS)
        self.timer.timeout.connect(self.refresh)

        self._hub: VariableHub | None = None
        self.set_hub(hub)

    def set_hub(self, hub: VariableHub | None) -> None:
        """
        指定變數的來源
        Give the inspector where its variables come from.

        :param hub: 視窗的 ``VariableHub``；``None`` 表示沒有來源
            the window's ``VariableHub``; ``None`` for no source
        """
        if self._hub is not None:
            self._hub.changed.disconnect(self.refresh)
        self._hub = hub
        if hub is not None:
            hub.changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        """照來源現在的狀態更新表格與上面的說明 / Update the table and the note above it from the source as it is now."""
        words = language_wrapper.language_word_dict
        hub = self._hub
        source = hub.source() if hub is not None else VariableSource.NONE
        namespace = hub.namespace() if hub is not None else None
        if hub is not None and source is VariableSource.DEBUGGER:
            self.model.show_rows(hub.paused_rows())
            self.source_label.setText(str(words.get("variable_inspector_source_debugger")).format(
                frame=hub.paused_frame() or "?"))
        elif hub is not None and namespace is not None and source is VariableSource.CONSOLE:
            self.model.show_namespace(namespace, hub.hidden())
            self.source_label.setText(str(words.get("variable_inspector_source_console")))
        else:
            self.model.show_rows([])
            self.source_label.setText(str(words.get("variable_inspector_source_none")))

    def showEvent(self, event: QShowEvent) -> None:
        """看得到了：立刻更新一次，再開始定時更新 / Now visible: refresh at once, then on the timer."""
        super().showEvent(event)
        self.refresh()
        self.timer.start()

    def hideEvent(self, event: QHideEvent) -> None:
        """看不到了：停止定時更新 / No longer visible: stop refreshing."""
        self.timer.stop()
        super().hideEvent(event)
