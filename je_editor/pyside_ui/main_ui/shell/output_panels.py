"""
輸出類的面板：執行結果、格式檢查、除錯輸出、終端機、變數查看器與 Git
The output views: run result, format check, debugger output, terminal, variable inspector and Git.

外框為整個視窗建一組，放進下方面板與側邊欄；沒有外框的宿主視窗裡，編輯分頁自己
建一組放在編輯器下方。兩種情況用的是同一個類別，所以元件怎麼建只寫在這裡。
The shell builds one set for the whole window and places it in the bottom panel
and the side bar; in a host window without the shell an editor tab builds a set
of its own below its editor. Both use this one class, so how the widgets are
built is written here only.
"""
from __future__ import annotations

from PySide6.QtWidgets import QScrollArea, QTabWidget, QWidget

from je_editor.pyside_ui.code.textedit_code_result.code_record import CodeRecord
from je_editor.pyside_ui.code.variable_inspector.inspector_gui import VariableInspector
from je_editor.pyside_ui.git_ui.git_client.git_client_gui import GitGui
from je_editor.pyside_ui.main_ui.console_widget.console_gui import ConsoleWidget
from je_editor.utils.multi_language.multi_language_wrapper import language_wrapper


class OutputPanels:
    """
    一組輸出類的面板
    One set of output views.
    """

    def __init__(self, console_parent: QWidget | None = None) -> None:
        """
        :param console_parent: 終端機的父元件 / the terminal's parent widget
        """
        # 執行結果包在可捲動區域裡 / The run result sits in a scroll area
        self.code_result = CodeRecord()
        self.code_result_scroll_area = QScrollArea()
        self.code_result_scroll_area.setWidgetResizable(True)
        self.code_result_scroll_area.setViewportMargins(0, 0, 0, 0)
        self.code_result_scroll_area.setWidget(self.code_result)
        self.format_check_result = CodeRecord()
        self.debugger_result = CodeRecord()
        self.console_widget = ConsoleWidget(console_parent)
        self.variable_inspector = VariableInspector()
        self.git_gui = GitGui()

    def as_tab_widget(self) -> QTabWidget:
        """
        把整組面板放進一個分頁元件，給沒有外框的編輯分頁用
        Put the whole set into one tab widget, for an editor tab without the shell.

        :return: 新的分頁元件 / the new tab widget
        """
        words = language_wrapper.language_word_dict
        tabs = QTabWidget()
        for widget, title_key in (
            (self.code_result_scroll_area, "editor_code_result"),
            (self.format_check_result, "editor_format_check"),
            (self.debugger_result, "editor_debugger_input_title_label"),
            (self.console_widget, "editor_terminal"),
            (self.variable_inspector, "variable_inspector_title"),
            (self.git_gui, "tab_menu_git_client_tab_name"),
        ):
            tabs.addTab(widget, words.get(title_key))
        return tabs

    def close(self) -> None:
        """關閉終端機的互動式 shell / Shut down the terminal's interactive shell."""
        self.console_widget.close()
