"""
用到時才匯入的面板
The panels imported only when they are opened.

AI 聊天面板會帶進 ``langchain_openai`` 與 ``openai``，IPython 主控台會帶進整個
IPython，FrontEngine 也是一整個套件。選單在啟動時就建好，若在選單模組的最上面匯入
它們，啟動時間有一大半是在載入這些還沒有人打開的東西。
The AI chat panel brings in ``langchain_openai`` and ``openai``, the IPython
console brings in all of IPython, and FrontEngine is a whole package. The menus
are built at startup, so importing these at the top of the menu modules spent
most of the start loading things nobody had opened yet.
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget


def chat_ui(main_window: QWidget) -> QWidget:
    """
    建立 AI 聊天面板
    Build the AI chat panel.

    :param main_window: 主視窗 / the main window
    :return: 面板 / the panel
    """
    from je_editor.pyside_ui.main_ui.ai_widget.chat_ui import ChatUI
    return ChatUI(main_window)


def ipython_widget(main_window: QWidget) -> QWidget:
    """
    建立 IPython 主控台
    Build the IPython console.

    :param main_window: 主視窗 / the main window
    :return: 主控台 / the console
    """
    from je_editor.pyside_ui.main_ui.ipython_widget.ipython_console import IpythonWidget
    return IpythonWidget(main_window)


def frontengine_ui(**options: bool) -> QWidget:
    """
    建立 FrontEngine 的主介面
    Build FrontEngine's main interface.

    :param options: 傳給 ``FrontEngineMainUI`` 的引數 / the arguments given to ``FrontEngineMainUI``
    :return: 介面 / the interface
    """
    from frontengine import FrontEngineMainUI
    return FrontEngineMainUI(**options)
