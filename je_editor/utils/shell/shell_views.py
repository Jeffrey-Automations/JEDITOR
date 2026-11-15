"""
外框裡有哪些面板、各自放在哪一區
Which views the shell has, and the area each one lives in.

視窗分成四區：左邊的側邊欄、中間的編輯分頁、下方的面板、右邊的第二側邊欄。這裡
只描述「有哪些面板」，不建立任何元件；元件由外框在第一次顯示時才建立。
The window has four areas: the side bar on the left, the editor tabs in the
middle, the panel below them and a secondary side bar on the right. This only
describes which views exist and builds no widget; the shell builds each one the
first time it is shown.

純資料與純邏輯，不含 Qt。
Pure data and pure logic, with no Qt.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

# 面板所在的區域 / The areas a view may live in
AREA_SIDE = "side"
AREA_BOTTOM = "bottom"
AREA_SECONDARY = "secondary"
AREAS: Tuple[str, ...] = (AREA_SIDE, AREA_BOTTOM, AREA_SECONDARY)

# 內建面板的 ID；不隨翻譯變動，設定檔與快捷鍵都以它為準
# The built-in views' IDs. They do not move with the translation, and both the
# settings file and the shortcuts go by them
VIEW_EXPLORER = "explorer"
VIEW_SOURCE_CONTROL = "source_control"
VIEW_OUTLINE = "outline"
VIEW_DEBUG = "debug"
VIEW_TESTS = "tests"
VIEW_TODO = "todo"
VIEW_OUTPUT = "output"
VIEW_PROBLEMS = "problems"
VIEW_TERMINAL = "terminal"
VIEW_DEBUG_CONSOLE = "debug_console"
VIEW_FORMAT_CHECK = "format_check"
VIEW_VARIABLES = "variables"
VIEW_AI_CHAT = "ai_chat"


@dataclass(frozen=True)
class ViewSpec:
    """
    一個面板的描述
    The description of one view.

    :param view_id: 不隨翻譯變動的 ID / the ID, which no translation changes
    :param area: 所在的區域，``AREAS`` 之一 / the area it lives in, one of ``AREAS``
    :param title_key: 標題在語系字典裡的鍵 / the title's key in the language dictionary
    :param icon: 活動列上的圖示名稱；下方面板不需要 / the activity bar icon's
        name, which a bottom view does not need
    :param title: 沒有翻譯鍵時直接用的標題（宿主程式加的面板）/ the title used
        as it is when there is no key, as for a view a host application adds
    """

    view_id: str
    area: str
    title_key: str = ""
    icon: str = ""
    title: str = ""

    def __post_init__(self) -> None:
        if not self.view_id:
            raise ValueError("A view needs an ID")
        if self.area not in AREAS:
            raise ValueError(f"{self.area!r} is not a shell area; expected one of {AREAS}")


# 內建的面板，依顯示順序 / The built-in views, in the order they are shown
BUILTIN_VIEWS: Tuple[ViewSpec, ...] = (
    ViewSpec(VIEW_EXPLORER, AREA_SIDE, "view_explorer", "explorer"),
    ViewSpec(VIEW_OUTLINE, AREA_SIDE, "view_outline", "outline"),
    ViewSpec(VIEW_DEBUG, AREA_SIDE, "view_debug", "debug"),
    ViewSpec(VIEW_TESTS, AREA_SIDE, "view_tests", "tests"),
    ViewSpec(VIEW_TODO, AREA_SIDE, "view_todo", "todo"),
    ViewSpec(VIEW_OUTPUT, AREA_BOTTOM, "view_output"),
    ViewSpec(VIEW_PROBLEMS, AREA_BOTTOM, "view_problems"),
    ViewSpec(VIEW_TERMINAL, AREA_BOTTOM, "view_terminal"),
    # Git 用戶端是一整個並排的介面，側邊欄放不下 / The Git client is a whole side-by-side interface, too wide for a side bar
    ViewSpec(VIEW_SOURCE_CONTROL, AREA_BOTTOM, "view_source_control"),
    ViewSpec(VIEW_DEBUG_CONSOLE, AREA_BOTTOM, "view_debug_console"),
    ViewSpec(VIEW_FORMAT_CHECK, AREA_BOTTOM, "view_format_check"),
    ViewSpec(VIEW_VARIABLES, AREA_BOTTOM, "view_variables"),
    ViewSpec(VIEW_AI_CHAT, AREA_SECONDARY, "view_ai_chat", "ai_chat"),
)


def views_in(area: str, views: Tuple[ViewSpec, ...] = BUILTIN_VIEWS) -> Tuple[ViewSpec, ...]:
    """
    某一區的面板
    The views of one area.

    :param area: 區域 / the area
    :param views: 要篩選的面板 / the views to pick from
    :return: 該區的面板，順序不變 / that area's views, in the same order
    """
    return tuple(view for view in views if view.area == area)


def view_title(view: ViewSpec, words: dict) -> str:
    """
    面板在目前語言下的標題
    A view's title in the language in use.

    :param view: 面板 / the view
    :param words: 目前的語系字典 / the language dictionary in use
    :return: 標題；沒有翻譯時退回面板自己的標題，再退回 ID
        the title, falling back to the view's own title and then its ID
    """
    translated = words.get(view.title_key) if view.title_key else None
    return str(translated or view.title or view.view_id)
