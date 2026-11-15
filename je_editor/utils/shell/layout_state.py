"""
外框的版面狀態：哪些區域開著、各自顯示哪個面板、有多寬
The shell's layout state: which areas are open, the view each shows, and how wide.

版面狀態與面板本身分開存放：收起側邊欄、換一個面板、拖動分隔線都只改這份資料，
面板裡的內容（展開到哪一層、輸出了什麼）不必重建。存進設定檔的也是這一份。
Layout state is kept apart from the views themselves: hiding the side bar,
switching view and dragging a divider change only this data, and what a view
holds -- how far a tree is expanded, what was printed -- is never rebuilt. It is
also what the settings file stores.

純資料與純邏輯，不含 Qt。
Pure data and pure logic, with no Qt.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from typing import Any, Iterable

from je_editor.utils.shell.shell_views import VIEW_EXPLORER, VIEW_OUTPUT

# 存在使用者設定裡的鍵 / The key this is stored under in the user settings
LAYOUT_SETTING_KEY = "shell_layout"

# 區域尺寸的上下限（像素）；設定檔被手動改成離譜的值時拉回來
# The bounds of an area's size, in pixels, which pull a hand-edited settings
# file back from an absurd value
MIN_AREA_SIZE = 120
MAX_AREA_SIZE = 4000

DEFAULT_SIDE_BAR_WIDTH = 270
DEFAULT_BOTTOM_PANEL_HEIGHT = 230
DEFAULT_SECONDARY_WIDTH = 380


@dataclass(frozen=True)
class ShellLayout:
    """
    外框的版面
    The shell's layout.

    :param side_bar_visible: 側邊欄是否顯示 / whether the side bar is shown
    :param side_view: 側邊欄顯示的面板 / the view the side bar shows
    :param bottom_panel_visible: 下方面板是否顯示 / whether the bottom panel is shown
    :param bottom_view: 下方面板顯示的分頁 / the tab the bottom panel shows
    :param secondary_visible: 第二側邊欄是否顯示 / whether the secondary side bar is shown
    :param side_bar_width: 側邊欄寬度 / the side bar's width
    :param bottom_panel_height: 下方面板高度 / the bottom panel's height
    :param secondary_width: 第二側邊欄寬度 / the secondary side bar's width
    """

    side_bar_visible: bool = True
    side_view: str = VIEW_EXPLORER
    bottom_panel_visible: bool = True
    bottom_view: str = VIEW_OUTPUT
    secondary_visible: bool = False
    side_bar_width: int = DEFAULT_SIDE_BAR_WIDTH
    bottom_panel_height: int = DEFAULT_BOTTOM_PANEL_HEIGHT
    secondary_width: int = DEFAULT_SECONDARY_WIDTH


_DEFAULT = ShellLayout()


def _clean(name: str, value: Any) -> Any:
    """
    把一個欄位的值整理成可用的；不能用時回傳預設值
    Tidy one field's value into something usable, or give the default back.
    """
    default = getattr(_DEFAULT, name)
    if isinstance(default, bool):
        return value if isinstance(value, bool) else default
    if isinstance(default, int):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return max(MIN_AREA_SIZE, min(MAX_AREA_SIZE, int(value)))
    return value if isinstance(value, str) and value else default


def layout_from_setting(raw: Any) -> ShellLayout:
    """
    從設定檔裡的資料讀出版面
    Read a layout out of what the settings file holds.

    設定檔可能被手動編輯，也可能來自舊版本：不是字典、少了欄位、型別不對，都退回
    那個欄位的預設值，絕不能擋住視窗開啟。
    A settings file may be hand-edited or come from an older version: not a
    mapping, a missing field or a wrong type all fall back to that field's
    default, and never stop the window from opening.

    :param raw: 設定裡 ``shell_layout`` 的值 / the value of ``shell_layout``
    :return: 版面 / the layout
    """
    if not isinstance(raw, dict):
        return _DEFAULT
    return ShellLayout(**{
        item.name: _clean(item.name, raw.get(item.name)) for item in fields(ShellLayout)
    })


def layout_to_setting(layout: ShellLayout) -> dict:
    """
    把版面轉成可以寫進設定檔的字典
    Turn a layout into the mapping the settings file stores.

    :param layout: 版面 / the layout
    :return: 只含 JSON 型別的字典 / a mapping of JSON types only
    """
    return asdict(layout)


def with_known_views(layout: ShellLayout, side_views: Iterable[str],
                     bottom_views: Iterable[str]) -> ShellLayout:
    """
    把指向不存在面板的欄位換回預設面板
    Point any field naming a view that does not exist back at the default one.

    上次開著的面板可能是某個外掛加的，而這次外掛沒有載入。
    The view left open last time may have come from a plugin that is not loaded
    this time.

    :param layout: 讀進來的版面 / the layout as read
    :param side_views: 目前有的側邊欄面板 ID / the side bar view IDs that exist
    :param bottom_views: 目前有的下方面板 ID / the bottom view IDs that exist
    :return: 每個欄位都指向現有面板的版面 / a layout whose fields all name existing views
    """
    changes = {}
    if layout.side_view not in set(side_views):
        changes["side_view"] = _DEFAULT.side_view
    if layout.bottom_view not in set(bottom_views):
        changes["bottom_view"] = _DEFAULT.bottom_view
    return replace(layout, **changes) if changes else layout
