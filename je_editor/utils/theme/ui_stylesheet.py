"""
把色票組成整個視窗用的 QSS
Turn a set of colour tokens into the QSS for the whole window.

樣式只有一份範本，深色與淺色差在代進去的色票，所以兩個主題的間距、圓角與層次
不會各走各的。物件名稱（``ActivityBar``、``SideBar`` 這些）由外框的元件設定，
這裡只是照名字上色。
There is one template, and dark and light differ only in the tokens put into it,
so the two themes cannot drift apart in spacing, corners or layering. The object
names (``ActivityBar``, ``SideBar`` and the rest) are set by the shell's widgets;
this only colours by name.

純邏輯，不含 Qt。
Pure logic, with no Qt.
"""
from __future__ import annotations

from string import Template
from typing import Mapping

from je_editor.utils.theme.ui_theme import Tokens

# 外框元件的物件名稱；元件與樣式都從這裡取，兩邊才不會各寫一份
# The shell widgets' object names, read by both the widgets and the style so the
# two never hold separate copies
ACTIVITY_BAR_NAME = "ActivityBar"
SIDE_BAR_NAME = "SideBar"
SECONDARY_SIDE_BAR_NAME = "SecondarySideBar"
SIDE_BAR_HEADER_NAME = "SideBarHeader"
BOTTOM_PANEL_NAME = "BottomPanel"
EDITOR_TABS_NAME = "EditorTabs"
MAIN_TOOLBAR_NAME = "MainToolBar"
STATUS_ITEM_NAME = "StatusItem"

_NAMES = {
    "activity_bar": ACTIVITY_BAR_NAME,
    "side_bar": SIDE_BAR_NAME,
    "secondary_side_bar": SECONDARY_SIDE_BAR_NAME,
    "side_bar_header": SIDE_BAR_HEADER_NAME,
    "bottom_panel": BOTTOM_PANEL_NAME,
    "editor_tabs": EDITOR_TABS_NAME,
    "main_toolbar": MAIN_TOOLBAR_NAME,
    "status_item": STATUS_ITEM_NAME,
}

_TEMPLATE = Template("""
QWidget {
    background-color: $surface;
    color: $text;
    selection-background-color: $selection;
    selection-color: $text;
    outline: 0;
}
QWidget:disabled { color: $text_disabled; }
QMainWindow, QDialog { background-color: $surface; }
QMainWindow::separator { background: $border; width: 1px; height: 1px; }
QToolTip {
    background-color: $raised; color: $text;
    border: 1px solid $border; padding: 4px 8px;
}

QMenuBar { background-color: $chrome; border-bottom: 1px solid $border; padding: 2px 4px; }
QMenuBar::item { background: transparent; padding: 5px 10px; border-radius: 4px; }
QMenuBar::item:selected, QMenuBar::item:pressed { background-color: $hover; }
QMenu { background-color: $raised; border: 1px solid $border; padding: 4px; }
QMenu::item { padding: 6px 28px 6px 22px; border-radius: 4px; }
QMenu::item:selected { background-color: $accent; color: $accent_text; }
QMenu::item:disabled { color: $text_disabled; }
QMenu::separator { height: 1px; background: $border; margin: 4px 8px; }

QToolBar { background-color: $chrome; border: 0; spacing: 2px; padding: 3px 6px; }
QToolBar::separator { background: $border; width: 1px; height: 1px; margin: 5px 6px; }
QToolButton {
    background: transparent; border: 0; border-radius: 5px; padding: 5px;
}
QToolButton:hover { background-color: $hover; }
QToolButton:pressed, QToolButton:checked { background-color: $raised; }
QToolBar#$main_toolbar { border-bottom: 1px solid $border; }
QToolBar#$main_toolbar QLabel { background: transparent; color: $text_muted; }

QToolBar#$activity_bar {
    background-color: $chrome; border-right: 1px solid $border; padding: 6px 0; spacing: 4px;
}
QToolBar#$activity_bar QWidget { background-color: transparent; }
QToolBar#$activity_bar QToolButton {
    border-radius: 0; padding: 9px 11px; border-left: 2px solid transparent;
}
QToolBar#$activity_bar QToolButton:hover { background: transparent; }
QToolBar#$activity_bar QToolButton:checked {
    background: transparent; border-left: 2px solid $accent;
}

QWidget#$side_bar, QWidget#$secondary_side_bar { background-color: $surface; }
QLabel#$side_bar_header {
    background-color: $surface; color: $text_muted;
    padding: 9px 14px; font-weight: 600;
}

QTabWidget::pane { border: 0; background-color: $surface; }
QTabBar { background-color: $chrome; qproperty-drawBase: 0; }
QTabBar::tab {
    background-color: $chrome; color: $text_muted;
    padding: 7px 14px; border: 0; border-top: 2px solid transparent;
    border-right: 1px solid $border;
}
QTabBar::tab:hover { color: $text; background-color: $hover; }
QTabBar::tab:selected {
    background-color: $editor_background; color: $text; border-top: 2px solid $accent;
}
QTabBar::close-button { subcontrol-position: right; margin-left: 4px; border-radius: 3px; }
QTabBar::close-button:hover { background-color: $raised; }
QTabWidget#$editor_tabs::pane { background-color: $editor_background; }
QTabWidget#$bottom_panel::pane { border-top: 1px solid $border; }
QTabWidget#$bottom_panel > QTabBar, QTabWidget#$bottom_panel QTabBar { background-color: $surface; }
QTabWidget#$bottom_panel QTabBar::tab {
    background-color: $surface; border-right: 0; border-top: 0;
    border-bottom: 2px solid transparent; padding: 6px 12px;
}
QTabWidget#$bottom_panel QTabBar::tab:selected {
    background-color: $surface; color: $text; border-bottom: 2px solid $accent;
}

QSplitter::handle { background-color: $border; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }

QPlainTextEdit, QTextEdit, QTextBrowser {
    background-color: $editor_background; color: $text; border: 0;
    selection-background-color: $selection;
}
QScrollArea, QAbstractScrollArea { border: 0; }

QTreeView, QListView, QTableView, QListWidget, QTreeWidget, QTableWidget {
    background-color: $surface; alternate-background-color: $surface;
    border: 0; show-decoration-selected: 1;
}
QTreeView::item, QListView::item, QListWidget::item, QTreeWidget::item { padding: 3px 4px; }
QTreeView::item:hover, QListView::item:hover, QTableView::item:hover { background-color: $hover; }
QTreeView::item:selected, QListView::item:selected, QTableView::item:selected {
    background-color: $selection; color: $text;
}
QHeaderView::section {
    background-color: $surface; color: $text_muted;
    border: 0; border-bottom: 1px solid $border; padding: 5px 8px;
}
QTableView { gridline-color: $border; }
QTableCornerButton::section { background-color: $surface; border: 0; }

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: $raised; color: $text;
    border: 1px solid $border; border-radius: 5px; padding: 4px 8px;
    selection-background-color: $selection;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: $accent; }
QComboBox QAbstractItemView {
    background-color: $raised; border: 1px solid $border; selection-background-color: $accent;
    selection-color: $accent_text;
}

QPushButton {
    background-color: $raised; color: $text;
    border: 1px solid $border; border-radius: 5px; padding: 5px 14px;
}
QPushButton:hover { background-color: $hover; }
QPushButton:pressed { background-color: $selection; }
QPushButton:default { background-color: $accent; color: $accent_text; border-color: $accent; }
QPushButton:default:hover { background-color: $accent_hover; }

QCheckBox, QRadioButton, QLabel { background: transparent; }
QGroupBox {
    border: 1px solid $border; border-radius: 6px; margin-top: 10px; padding-top: 8px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: $text_muted; }
QProgressBar {
    background-color: $raised; border: 0; border-radius: 3px; text-align: center;
}
QProgressBar::chunk { background-color: $accent; border-radius: 3px; }

QScrollBar:vertical { background: transparent; width: 12px; margin: 0; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 0; }
QScrollBar::handle:vertical {
    background-color: $scrollbar; min-height: 28px; border-radius: 3px; margin: 2px 3px;
}
QScrollBar::handle:horizontal {
    background-color: $scrollbar; min-width: 28px; border-radius: 3px; margin: 3px 2px;
}
QScrollBar::handle:hover { background-color: $scrollbar_hover; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QDockWidget { titlebar-close-icon: none; color: $text_muted; }
QDockWidget::title {
    background-color: $surface; padding: 7px 12px; border-bottom: 1px solid $border;
}

QStatusBar { background-color: $chrome; color: $text_muted; border-top: 1px solid $border; }
QStatusBar::item { border: 0; }
QStatusBar QLabel { background: transparent; color: $text_muted; padding: 2px 8px; }
QStatusBar QLabel#$status_item { color: $text; }
""")


# 要用圖檔的樣式：QSS 只能以路徑指定圖片，所以這一段要等圖檔寫好才加得上去
# The rules that need image files. QSS can only name an image by path, so this
# part is added once the files have been written
IMAGE_TAB_CLOSE = "tab_close"
IMAGE_TAB_CLOSE_HOVER = "tab_close_hover"
IMAGE_NAMES = (IMAGE_TAB_CLOSE, IMAGE_TAB_CLOSE_HOVER)

_IMAGE_TEMPLATE = Template("""
QTabBar::close-button { image: url("$tab_close"); }
QTabBar::close-button:hover { image: url("$tab_close_hover"); }
""")


def build_stylesheet(tokens: Tokens, image_urls: Mapping[str, str] | None = None) -> str:
    """
    用一組色票組出視窗的 QSS
    Build the window's QSS from a set of tokens.

    :param tokens: 色票，鍵見 ``ui_theme.DARK_TOKENS`` / the tokens, keyed as
        ``ui_theme.DARK_TOKENS`` is
    :param image_urls: ``IMAGE_NAMES`` 裡每個名字對應的圖檔路徑（用正斜線）；省略時
        不含需要圖檔的樣式 / the image file path, with forward slashes, for each
        name in ``IMAGE_NAMES``; omitted, the rules needing images are left out
    :return: QSS 字串 / the QSS text
    :raises KeyError: 色票或圖檔少了範本要用的鍵時 / when a token or an image the
        template uses is missing
    """
    sheet = _TEMPLATE.substitute({**tokens, **_NAMES})
    if image_urls is not None:
        sheet += _IMAGE_TEMPLATE.substitute(image_urls)
    return sheet.strip()
