"""
外框用的圖示：一組線條風格的 SVG
The shell's icons: a set of line-drawn SVGs.

圖示以文字存放而不是圖檔，所以不必另外打包進 wheel，而且顏色是代進去的——同一個
圖示在深色與淺色主題、一般與選取狀態各畫一次就好。
The icons are kept as text rather than image files, so nothing extra has to be
packaged into the wheel, and the colour is filled in: one icon is simply drawn
again for the dark and the light theme, and for its normal and selected state.

純資料與純邏輯，不含 Qt。
Pure data and pure logic, with no Qt.
"""
from __future__ import annotations

from typing import Dict, Tuple

# 畫布邊長；每個圖示的座標都以它為準 / The canvas edge every icon's coordinates assume
ICON_CANVAS = 24

_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 {canvas} {canvas}" fill="none" stroke="{color}" stroke-width="1.6" '
    'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
)

# 圖示名稱對應 SVG 內容 / Icon name mapped to its SVG body
_ICON_BODIES: Dict[str, str] = {
    "explorer": (
        '<path d="M15 3H8a2 2 0 0 0-2 2v11"/>'
        '<rect x="10" y="7" width="9" height="14" rx="2"/>'
    ),
    "search": '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.6-4.6"/>',
    "source_control": (
        '<circle cx="7" cy="5.5" r="2.2"/><circle cx="7" cy="18.5" r="2.2"/>'
        '<circle cx="17" cy="8.5" r="2.2"/>'
        '<path d="M7 7.7v8.6M17 10.7c0 3.6-5 3-9.2 5.2"/>'
    ),
    "debug": (
        '<ellipse cx="12" cy="14" rx="5" ry="6"/>'
        '<path d="M9.5 8.6a2.5 2.5 0 0 1 5 0M4 13h3M17 13h3M5 19.5l2.6-1.6'
        'M19 19.5l-2.6-1.6M5 7.5l2.8 2.3M19 7.5l-2.8 2.3M12 10v10"/>'
    ),
    "tests": (
        '<path d="M9 3h6M10 3v6l-5.2 9.2A1.9 1.9 0 0 0 6.5 21h11a1.9 1.9 0 0 0 1.7-2.8'
        'L14 9V3M7.6 15h8.8"/>'
    ),
    "outline": '<path d="M4 5h16M9 12h11M14 19h6M5.5 5v7H9M10.5 12v7H14"/>',
    "todo": '<path d="M4 7l2 2 3.5-4M4 16.5l2 2 3.5-4M13.5 7H20M13.5 17H20"/>',
    "ai_chat": (
        '<path d="M5 4.5h14a2 2 0 0 1 2 2V15a2 2 0 0 1-2 2h-6.5L8 21v-4H5a2 2 0 0 1-2-2'
        'V6.5a2 2 0 0 1 2-2z"/><path d="M8 9.5h8M8 12.5h5"/>'
    ),
    "bottom_panel": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 14.5h18"/>',
    "side_bar": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/>',
    "new_file": (
        '<path d="M13 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/>'
        '<path d="M13 3v6h6M12 12.5v5M9.5 15h5"/>'
    ),
    "open_file": (
        '<path d="M3 7a2 2 0 0 1 2-2h4l2 2.5h8a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2H5'
        'a2 2 0 0 1-2-2z"/>'
    ),
    "save_file": (
        '<path d="M5 3h11l5 5v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/>'
        '<path d="M7 3v5h8V3M7 21v-7h10v7"/>'
    ),
    "close": '<path d="M7 7l10 10M17 7L7 17"/>',
    "run": '<path d="M7 4.5l12 7.5-12 7.5z"/>',
    "stop": '<rect x="5.5" y="5.5" width="13" height="13" rx="2"/>',
    "checkout": '<path d="M4 12.5l5 5L20 6.5"/>',
    "refresh": (
        '<path d="M20 11a8 8 0 0 0-14.5-4.200L4 8.5M4 4v4.5h4.5M4 13a8 8 0 0 0 14.5 4.200'
        'L20 15.5M20 20v-4.5h-4.5"/>'
    ),
    "command_palette": '<path d="M5 8l4 4-4 4M12 16.5h7"/>',
    "quick_open": (
        '<path d="M13 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h3"/><path d="M13 3v6h6v2"/>'
        '<circle cx="15.5" cy="16.5" r="3"/><path d="M21 22l-3.300-3.300"/>'
    ),
    "go_to_symbol": (
        '<path d="M9 4c-2 0-3 1-3 3v2.5c0 1.5-1 2.5-2 2.5 1 0 2 1 2 2.5V17c0 2 1 3 3 3'
        'M15 4c2 0 3 1 3 3v2.5c0 1.5 1 2.5 2 2.5-1 0-2 1-2 2.5V17c0 2-1 3-3 3"/>'
    ),
}


def icon_names() -> Tuple[str, ...]:
    """
    所有圖示的名稱
    Every icon's name.

    :return: 名稱，依字母排序 / the names, sorted
    """
    return tuple(sorted(_ICON_BODIES))


def has_icon(name: str) -> bool:
    """
    有沒有這個名稱的圖示
    Whether an icon by this name exists.

    :param name: 圖示名稱 / the icon's name
    :return: 有的話為 ``True`` / ``True`` when it does
    """
    return name in _ICON_BODIES


def icon_svg(name: str, color: str, size: int = ICON_CANVAS) -> str:
    """
    取得一個圖示的 SVG 文字
    The SVG text of one icon.

    :param name: 圖示名稱 / the icon's name
    :param color: 線條顏色，例如 ``#d5d9e0`` / the stroke colour, such as ``#d5d9e0``
    :param size: 輸出的邊長（像素）/ the edge of the output, in pixels
    :return: 完整的 SVG 文件 / the whole SVG document
    :raises KeyError: 沒有這個圖示時 / when no icon has that name
    """
    if name not in _ICON_BODIES:
        raise KeyError(f"No shell icon is named {name!r}")
    return _SVG.format(size=size, canvas=ICON_CANVAS, color=color, body=_ICON_BODIES[name])
