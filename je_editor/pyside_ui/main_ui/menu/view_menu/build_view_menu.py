"""
檢視選單：開關外框的各區，以及直接跳到某個面板
The View menu: toggling the shell's areas, and jumping straight to a view.

每個項目都只是呼叫外框（``workbench``）上的方法，所以選單、活動列與快捷鍵做的是
同一件事。視窗沒有外框時不建立這個選單。
Every item merely calls a method on the shell (``workbench``), so the menu, the
activity bar and the shortcuts all do the same thing. A window without a shell
gets no such menu.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction

from je_editor.pyside_ui.main_ui.save_settings.shortcut_setting import bind
from je_editor.pyside_ui.main_ui.shell.workbench import Workbench, workbench_of
from je_editor.utils.logging.loggin_instance import jeditor_logger
from je_editor.utils.multi_language.multi_language_wrapper import language_wrapper
from je_editor.utils.shell.shell_views import BUILTIN_VIEWS, VIEW_EXPLORER, view_title

if TYPE_CHECKING:
    from je_editor.pyside_ui.main_ui.main_editor import EditorMain

# 有自己快捷鍵的面板，對應到指令名稱 / The views with a shortcut of their own, and its command
_VIEW_COMMANDS = {VIEW_EXPLORER: "show_explorer"}


def set_view_menu(ui_we_want_to_set: EditorMain) -> None:
    """
    建立檢視選單
    Build the View menu.

    :param ui_we_want_to_set: 主編輯器視窗 / the main editor window
    """
    jeditor_logger.info(f"build_view_menu.py set_view_menu ui_we_want_to_set: {ui_we_want_to_set}")
    workbench = workbench_of(ui_we_want_to_set)
    if workbench is None:
        return
    words = language_wrapper.language_word_dict
    menu = ui_we_want_to_set.menu.addMenu(words.get("view_menu_label"))
    ui_we_want_to_set.view_menu = menu

    for label_key, command, slot in (
        ("view_menu_toggle_side_bar", "toggle_side_bar", workbench.toggle_side_bar),
        ("view_menu_toggle_bottom_panel", "toggle_bottom_panel", workbench.toggle_bottom_panel),
        ("view_menu_toggle_secondary_side_bar", "toggle_secondary_side_bar",
         workbench.toggle_secondary_side_bar),
    ):
        action = QAction(words.get(label_key), parent=menu)
        bind(action, command)
        action.triggered.connect(slot)
        menu.addAction(action)

    menu.addSeparator()
    _add_view_actions(menu, workbench)


def _add_view_actions(menu, workbench: Workbench) -> None:
    """每個內建面板一個「顯示」項目 / One "show" item for each built-in view."""
    words = language_wrapper.language_word_dict
    for spec in BUILTIN_VIEWS:
        if workbench.view_spec(spec.view_id) is None:
            continue
        action = QAction(view_title(spec, words), parent=menu)
        command = _VIEW_COMMANDS.get(spec.view_id)
        if command is not None:
            bind(action, command)
        action.triggered.connect(
            lambda _checked=False, wanted=spec.view_id: workbench.show_view(wanted))
        menu.addAction(action)
