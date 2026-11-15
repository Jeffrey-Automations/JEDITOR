"""
把外框的 SVG 圖示畫成 ``QIcon``，並在換主題時重畫
Draw the shell's SVG icons as ``QIcon`` objects, and draw them again on a theme change.

圖示的顏色來自主題的色票，所以換主題時每個圖示都要重畫。動作上記著自己用的是
哪個圖示（一個動態屬性），換主題時把視窗底下帶著這個屬性的動作全部找出來重設，
不必另外維護一份清單。
An icon's colour comes from the theme's tokens, so a theme change redraws every
one. Each action records which icon it uses, as a dynamic property, and a theme
change finds every action under the window carrying that property and sets it
again -- no separate list has to be kept.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QObject, Qt
from PySide6.QtGui import QAction, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from je_editor.pyside_ui.main_ui.save_settings.user_setting_file import user_setting_dict
from je_editor.utils.theme.ui_icons import ICON_CANVAS, icon_svg
from je_editor.utils.theme.ui_theme import DEFAULT_STYLE, Tokens, tokens_for

# 動作上記錄圖示名稱的屬性 / The property an action records its icon's name under
ICON_PROPERTY = "shell_icon_name"

# 每個圖示各畫一倍與兩倍大小，高解析度螢幕才不會糊
# Each icon is drawn at one and two times its size, so a high-density screen
# does not blur it
_SCALES = (1, 2)


def current_tokens() -> Tokens:
    """
    目前設定的樣式所用的色票
    The tokens of the style the settings name.

    :return: 色票 / the tokens
    """
    return tokens_for(user_setting_dict.get("ui_style", DEFAULT_STYLE))


def _pixmap(name: str, color: str, size: int, scale: int) -> QPixmap:
    """把一個圖示以某個顏色畫成點陣圖 / Draw one icon in one colour as a pixmap."""
    edge = size * scale
    pixmap = QPixmap(edge, edge)
    pixmap.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(icon_svg(name, color, edge).encode("utf-8")))
    painter = QPainter(pixmap)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    pixmap.setDevicePixelRatio(scale)
    return pixmap


def themed_icon(name: str, tokens: Tokens | None = None, size: int = ICON_CANVAS) -> QIcon:
    """
    取得一個照主題上色的圖示
    An icon coloured for the theme.

    一般狀態用次要文字色，滑過與選取時用主要文字色，停用時用停用色，所以同一個
    圖示可以直接用在可勾選的按鈕上。
    The normal state takes the muted text colour, hovering and being checked take
    the main text colour, and disabled takes the disabled one, so the same icon
    serves a checkable button as it is.

    :param name: 圖示名稱，見 ``ui_icons`` / the icon's name, see ``ui_icons``
    :param tokens: 色票；省略時用目前設定的樣式 / the tokens, or the configured style's
    :param size: 邊長（像素）/ the edge, in pixels
    :return: 圖示 / the icon
    :raises KeyError: 沒有這個圖示時 / when no icon has that name
    """
    colours = tokens or current_tokens()
    icon = QIcon()
    states = (
        (colours["text_muted"], QIcon.Mode.Normal, QIcon.State.Off),
        (colours["text"], QIcon.Mode.Normal, QIcon.State.On),
        (colours["text"], QIcon.Mode.Active, QIcon.State.Off),
        (colours["text"], QIcon.Mode.Active, QIcon.State.On),
        (colours["text_disabled"], QIcon.Mode.Disabled, QIcon.State.Off),
    )
    for colour, mode, state in states:
        for scale in _SCALES:
            icon.addPixmap(_pixmap(name, colour, size, scale), mode, state)
    return icon


def set_action_icon(action: QAction, name: str, tokens: Tokens | None = None) -> QAction:
    """
    給一個動作設定圖示，並記下圖示名稱以便換主題時重畫
    Give an action its icon, recording the name so a theme change can redraw it.

    :param action: 動作 / the action
    :param name: 圖示名稱 / the icon's name
    :param tokens: 色票；省略時用目前設定的樣式 / the tokens, or the configured style's
    :return: 同一個動作 / the same action
    """
    action.setProperty(ICON_PROPERTY, name)
    action.setIcon(themed_icon(name, tokens))
    return action


def refresh_action_icons(root: QObject, tokens: Tokens | None = None) -> int:
    """
    把某個物件底下所有動作的圖示照新主題重畫
    Redraw the icon of every action under an object for a new theme.

    :param root: 通常是主視窗 / usually the main window
    :param tokens: 新主題的色票；省略時用目前設定的樣式 / the new theme's tokens
    :return: 重畫了幾個 / how many were redrawn
    """
    colours = tokens or current_tokens()
    redrawn = 0
    for action in root.findChildren(QAction):
        name = action.property(ICON_PROPERTY)
        if name:
            action.setIcon(themed_icon(str(name), colours))
            redrawn += 1
    return redrawn
