"""
檔案總管面板：工作區的檔案樹，根目錄不只一個時上方多一個選單
The explorer view: the workspace's file tree, with a list above it once there is more than one root.

整個視窗共用一份。以前每個編輯分頁各有一棵樹，切換分頁時展開的資料夾就跟著換，
而且每一棵都各自監看磁碟。沒有外框的宿主視窗裡，編輯分頁仍然會自己建一份。
One is shared by the whole window. Every editor tab used to carry a tree of its
own, so the expanded folders changed with the tab and each tree watched the disk
separately. In a host window without the shell an editor tab still builds one
for itself.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDir
from PySide6.QtWidgets import QComboBox, QFileSystemModel, QTreeView, QVBoxLayout, QWidget

from je_editor.pyside_ui.main_ui.workspace.workspace_roots import labelled_root_paths

# 檔案系統模型的第一欄是名稱；其餘（大小、類型、日期）在側邊欄裡只佔位置
# The file system model's first column is the name; the rest (size, type, date)
# only take up room in a side bar
_NAME_COLUMN = 0


class ExplorerPanel(QWidget):
    """
    工作區的檔案樹
    The workspace's file tree.
    """

    def __init__(self, main_window: object, parent: QWidget | None = None) -> None:
        """
        :param main_window: 提供工作區根目錄的視窗 / the window whose workspace roots are shown
        :param parent: Qt 父元件 / the Qt parent
        """
        super().__init__(parent)
        self._main_window = main_window
        self.model = QFileSystemModel(self)
        self.model.setRootPath(QDir.currentPath())
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(True)
        for column in range(_NAME_COLUMN + 1, self.model.columnCount()):
            self.tree.hideColumn(column)

        # 工作區有好幾個根目錄時，用這個選單決定樹狀檢視顯示哪一個
        # With several workspace roots, this list decides which one the tree shows
        self.root_combobox = QComboBox()
        self.root_combobox.currentIndexChanged.connect(self.show_selected_root)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.root_combobox)
        layout.addWidget(self.tree)
        self.refresh_roots()

    def refresh_roots(self) -> None:
        """
        讓根目錄選單跟著工作區走
        Bring the root list in step with the workspace.

        只有一個根目錄時不必選，選單收起來。
        One root needs no choosing, so the list is hidden.
        """
        roots = labelled_root_paths(self._main_window)
        shown = self.root_combobox.currentData()
        self.root_combobox.blockSignals(True)
        try:
            self.root_combobox.clear()
            for label, path in roots:
                self.root_combobox.addItem(label, path)
            self.root_combobox.setCurrentIndex(max(self.root_combobox.findData(shown), 0))
        finally:
            self.root_combobox.blockSignals(False)
        self.root_combobox.setVisible(len(roots) > 1)
        self.show_selected_root()

    def show_selected_root(self) -> None:
        """讓樹狀檢視顯示選單選中的根目錄 / Make the tree show the root picked in the list."""
        path = self.root_combobox.currentData()
        if path:
            self.tree.setRootIndex(self.model.index(path))

    def selected_path(self) -> Path | None:
        """
        樹狀檢視目前選中的路徑
        The path selected in the tree.

        :return: 路徑，沒有選取時為 ``None`` / the path, or ``None`` with no selection
        """
        indexes = self.tree.selectedIndexes()
        if not indexes:
            return None
        return Path(self.model.fileInfo(indexes[0]).absoluteFilePath())
