"""
內建視窗主題的色票，以及「這個樣式名稱是哪一種」的判斷
The colour tokens of the built-in window themes, and telling one style name from another.

視窗樣式有兩個來源：專案自己的主題（這裡的色票，由 ``ui_stylesheet`` 組成 QSS），
以及 qt-material 的樣式檔（``dark_amber.xml`` 那一類）。設定裡的 ``ui_style`` 只是
一個名字，這個模組負責回答它屬於哪一邊、是深色還是淺色、該用哪一組色票。
A window style comes from one of two places: the project's own themes (the tokens
here, turned into QSS by ``ui_stylesheet``) or a qt-material style file such as
``dark_amber.xml``. The ``ui_style`` setting is only a name, and this module
answers which side it belongs to, whether it is dark or light, and which tokens
go with it.

純資料與純邏輯，不含 Qt。
Pure data and pure logic, with no Qt.
"""
from __future__ import annotations

from typing import Dict, Tuple

Tokens = Dict[str, str]

# 內建主題的名字；存進設定的就是這個字串
# The built-in themes' names, which are what the setting stores
STYLE_DARK = "jeditor_dark"
STYLE_LIGHT = "jeditor_light"

# 新安裝預設用的樣式 / The style a fresh installation starts with
DEFAULT_STYLE = STYLE_DARK

# 樣式選單上顯示的名稱 / The names the Style menu shows
BUILTIN_STYLE_LABELS: Dict[str, str] = {
    STYLE_DARK: "JEditor Dark",
    STYLE_LIGHT: "JEditor Light",
}

# 仍然可以選的 qt-material 樣式 / The qt-material styles that stay selectable
MATERIAL_STYLES: Tuple[str, ...] = (
    "dark_amber.xml", "dark_blue.xml", "dark_cyan.xml", "dark_lightgreen.xml",
    "dark_pink.xml", "dark_purple.xml", "dark_red.xml", "dark_teal.xml",
    "dark_yellow.xml", "light_amber.xml", "light_blue.xml", "light_cyan.xml",
    "light_cyan_500.xml", "light_lightgreen.xml", "light_pink.xml", "light_purple.xml",
)

# 深色主題：編輯區最亮，往外的面板與外框一層比一層暗，視線自然落在程式碼上
# The dark theme: the editor is the lightest surface and each ring of chrome
# around it is a step darker, which is what draws the eye to the code
DARK_TOKENS: Tokens = {
    "editor_background": "#1e2026",
    "surface": "#181a1f",
    "chrome": "#131519",
    "raised": "#262a32",
    "hover": "#2a2e37",
    "border": "#2b2f38",
    "text": "#d5d9e0",
    "text_muted": "#8a909c",
    "text_disabled": "#5a5f69",
    "accent": "#4c9bf5",
    "accent_hover": "#6aadf7",
    "accent_text": "#ffffff",
    "selection": "#2c4a70",
    "scrollbar": "#3a3f4a",
    "scrollbar_hover": "#4d5361",
    "danger": "#e5534b",
    "warning": "#d4a72c",
    "success": "#57ab5a",
}

# 淺色主題：同樣的層次反過來，編輯區是白的，外框略灰
# The light theme: the same layering the other way up, a white editor inside
# slightly grey chrome
LIGHT_TOKENS: Tokens = {
    "editor_background": "#ffffff",
    "surface": "#f5f6f8",
    "chrome": "#eaecef",
    "raised": "#ffffff",
    "hover": "#e2e5ea",
    "border": "#d6d9df",
    "text": "#1f2328",
    "text_muted": "#646c77",
    "text_disabled": "#a4aab3",
    "accent": "#2f6fde",
    "accent_hover": "#1f5bc4",
    "accent_text": "#ffffff",
    "selection": "#cbe0ff",
    "scrollbar": "#c5cad2",
    "scrollbar_hover": "#a8aeb8",
    "danger": "#cf222e",
    "warning": "#9a6700",
    "success": "#1a7f37",
}

_BUILTIN_TOKENS: Dict[str, Tokens] = {
    STYLE_DARK: DARK_TOKENS,
    STYLE_LIGHT: LIGHT_TOKENS,
}

_LIGHT_PREFIX = "light"
_LIGHT_SUFFIX = "_light"


def _normalised(style_name: str | None) -> str:
    """樣式名稱去空白並轉小寫 / A style name trimmed and lower-cased."""
    return str(style_name or "").strip().lower()


def is_builtin_style(style_name: str | None) -> bool:
    """
    這個樣式是不是專案自己的主題
    Whether a style is one of the project's own themes.

    :param style_name: 設定裡的樣式名稱 / the style name from the settings
    :return: 內建主題時為 ``True`` / ``True`` for a built-in theme
    """
    return _normalised(style_name) in _BUILTIN_TOKENS


def is_light_style(style_name: str | None) -> bool:
    """
    這個樣式是不是淺色的
    Whether a style is a light one.

    qt-material 的淺色樣式檔名以 ``light`` 開頭，內建的則以 ``_light`` 結尾。
    A light qt-material file name starts with ``light``, and the built-in one
    ends in ``_light``.

    :param style_name: 樣式名稱，例如 ``light_blue.xml`` / a style name
    :return: 淺色時為 ``True`` / ``True`` when it is light
    """
    name = _normalised(style_name)
    return name.startswith(_LIGHT_PREFIX) or name.endswith(_LIGHT_SUFFIX)


def tokens_for(style_name: str | None) -> Tokens:
    """
    取得某個樣式該用的色票
    The tokens that go with a style.

    qt-material 的樣式沒有自己的色票，拿明暗相同的內建那一組：圖示這類由編輯器
    自己畫的東西要靠它才看得見。
    A qt-material style has no tokens of its own and takes the built-in set of
    the same lightness, which is what keeps what the editor draws itself -- its
    icons -- visible on it.

    :param style_name: 樣式名稱 / the style name
    :return: 色票的副本 / a copy of the tokens
    """
    builtin = _BUILTIN_TOKENS.get(_normalised(style_name))
    if builtin is None:
        builtin = LIGHT_TOKENS if is_light_style(style_name) else DARK_TOKENS
    return dict(builtin)


def style_choices() -> Tuple[Tuple[str, str], ...]:
    """
    樣式選單要列的每一項
    Every entry the Style menu lists.

    :return: ``(樣式名稱, 顯示名稱)``，內建主題在前 / ``(style name, label)``
        pairs, the built-in themes first
    """
    builtin = tuple(BUILTIN_STYLE_LABELS.items())
    return builtin + tuple((name, name) for name in MATERIAL_STYLES)
