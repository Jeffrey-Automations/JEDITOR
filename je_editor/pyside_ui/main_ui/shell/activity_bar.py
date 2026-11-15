"""
活動列：視窗最左邊那一排圖示，用來切換側邊欄的面板
The activity bar: the column of icons at the window's left edge that switches the side bar's view.

它是一條不能移動的工具列，所以落在停駐區之外：宿主程式停在左邊的浮動視窗會排在
它與編輯區之間，不會把它擠走。
It is a toolbar that cannot be moved, which puts it outside the dock areas: a
dock a host application places on the left lands between it and the editor
rather than pushing it aside.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QSizePolicy, QToolBar, QWidget

from je_editor.pyside_ui.main_ui.shell.shell_icons import set_action_icon
from je_editor.utils.theme.ui_stylesheet import ACTIVITY_BAR_NAME

# 圖示邊長（像素）/ The icons' edge, in pixels
_ICON_SIZE = 24


class ActivityBar(QToolBar):
    """
    切換面板的圖示列
    The column of icons that switches views.
    """

    # 使用者點了某個面板的圖示 / The user clicked a view's icon
    view_requested = Signal(str)

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """
        :param title: 工具列的名稱（出現在視窗的右鍵選單）/ the toolbar's name,
            shown in the window's context menu
        :param parent: Qt 父元件 / the Qt parent
        """
        super().__init__(title, parent)
        self.setObjectName(ACTIVITY_BAR_NAME)
        self.setMovable(False)
        self.setFloatable(False)
        self.setOrientation(Qt.Orientation.Vertical)
        self.setIconSize(QSize(_ICON_SIZE, _ICON_SIZE))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self._actions: dict[str, QAction] = {}
        # 撐開中間，把後面加的圖示推到最下面 / Fills the middle, pushing later icons to the bottom
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._spacer_action = self.addWidget(spacer)

    def add_view(self, view_id: str, icon: str, title: str, at_bottom: bool = False) -> QAction:
        """
        加入一個面板的圖示
        Add a view's icon.

        :param view_id: 面板 ID / the view's ID
        :param icon: 圖示名稱 / the icon's name
        :param title: 提示文字 / the tip text
        :param at_bottom: 是否放在最下面那一組 / whether it joins the group at the bottom
        :return: 新的動作 / the new action
        :raises ValueError: ID 已經用過時 / when the ID is already taken
        """
        if view_id in self._actions:
            raise ValueError(f"The view {view_id!r} already has an activity bar icon")
        action = QAction(title, self)
        action.setToolTip(title)
        action.setCheckable(True)
        set_action_icon(action, icon)
        action.triggered.connect(lambda _checked=False, wanted=view_id: self.view_requested.emit(wanted))
        if at_bottom:
            self.addAction(action)
        else:
            self.insertAction(self._spacer_action, action)
        self._actions[view_id] = action
        return action

    def action_of(self, view_id: str) -> QAction | None:
        """
        某個面板的動作
        A view's action.

        :param view_id: 面板 ID / the view's ID
        :return: 動作，沒有時為 ``None`` / the action, or ``None``
        """
        return self._actions.get(view_id)

    def set_checked(self, view_id: str, checked: bool) -> None:
        """
        設定某個圖示是否顯示為使用中
        Set whether an icon shows as in use.

        :param view_id: 面板 ID / the view's ID
        :param checked: 是否使用中 / whether it is in use
        """
        action = self._actions.get(view_id)
        if action is not None:
            action.setChecked(checked)

    def set_title(self, view_id: str, title: str) -> None:
        """
        換掉一個圖示的提示文字（換語言時）
        Replace an icon's tip text, as a language change does.

        :param view_id: 面板 ID / the view's ID
        :param title: 新的文字 / the new text
        """
        action = self._actions.get(view_id)
        if action is not None:
            action.setText(title)
            action.setToolTip(title)
