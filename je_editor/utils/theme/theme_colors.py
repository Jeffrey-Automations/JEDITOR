"""
編輯器自有顏色的深色與淺色預設值
The editor's own colours, in a dark and a light set.

視窗樣式來自內建主題或 qt-material，但編輯器自己畫的東西——行號、縮排參考線、
變更標記、語法高亮——用的是這裡的顏色。它們原本只有一組值，是照深色底調的，所以選了淺色
樣式之後那些顏色會淡到看不見。
The window style comes from a built-in theme or qt-material, but everything the editor paints itself
— line numbers, indent guides, change markers, syntax — uses the colours here.
There used to be only one set, tuned against a dark background, so choosing a
light style washed them out.

純資料與純邏輯，不含 Qt。
Pure data and pure logic, with no Qt.
"""
from __future__ import annotations

from typing import Dict, List

from je_editor.utils.theme.ui_theme import is_builtin_style, is_light_style

Palette = Dict[str, List[int]]

# 深色底用的顏色 / The colours for a dark background
DARK_COLORS: Palette = {
    "line_number_color": [255, 255, 255],
    "line_number_background_color": [179, 179, 179],
    # 深色底的目前行只需要比底色亮一點；原本這個值接近白色，壓在上面的文字反而
    # 看不清楚
    # On a dark background the current line only needs to lift slightly; this
    # used to be near-white, which buried the text sitting on it
    "current_line_color": [58, 58, 74],
    "normal_output_color": [255, 255, 255],
    "error_output_color": [255, 0, 0],
    "warning_output_color": [204, 204, 0],
    "bookmark_marker_color": [66, 165, 245],
    "fold_marker_color": [120, 120, 120],
    "occurrence_highlight_color": [80, 90, 60],
    "diff_added_marker_color": [76, 175, 80],
    "diff_modified_marker_color": [255, 167, 38],
    "diff_removed_marker_color": [229, 57, 53],
    "lint_underline_color": [255, 138, 101],
    "blame_annotation_color": [130, 130, 130],
    "indent_guide_color": [90, 90, 110],
    "minimap_background_color": [40, 40, 48],
    "minimap_line_color": [130, 130, 150],
    "minimap_viewport_color": [80, 80, 110],
    "extra_cursor_color": [255, 215, 64],
    "breakpoint_marker_color": [229, 57, 53],
    "syntax_keyword_color": [86, 156, 214],
    "syntax_string_color": [206, 145, 120],
    "syntax_comment_color": [106, 153, 85],
    "syntax_number_color": [181, 206, 168],
    "syntax_builtin_color": [78, 201, 176],
    "syntax_self_color": [197, 134, 192],
    "syntax_function_color": [220, 220, 170],
    "debug_execution_line_color": [92, 84, 26],
    "trailing_whitespace_color": [120, 70, 70],
}

# 淺色底用的顏色 / The colours for a light background
LIGHT_COLORS: Palette = {
    "line_number_color": [90, 90, 90],
    "line_number_background_color": [232, 232, 232],
    "current_line_color": [225, 232, 245],
    "normal_output_color": [30, 30, 30],
    "error_output_color": [198, 40, 40],
    "warning_output_color": [150, 120, 0],
    "bookmark_marker_color": [21, 101, 192],
    "fold_marker_color": [130, 130, 130],
    "occurrence_highlight_color": [255, 238, 160],
    "diff_added_marker_color": [46, 125, 50],
    "diff_modified_marker_color": [230, 126, 0],
    "diff_removed_marker_color": [198, 40, 40],
    "lint_underline_color": [216, 67, 21],
    "blame_annotation_color": [145, 145, 145],
    "indent_guide_color": [205, 205, 215],
    "minimap_background_color": [245, 245, 248],
    "minimap_line_color": [160, 160, 175],
    "minimap_viewport_color": [200, 205, 230],
    "extra_cursor_color": [216, 98, 0],
    "breakpoint_marker_color": [198, 40, 40],
    "syntax_keyword_color": [0, 0, 192],
    "syntax_string_color": [163, 21, 21],
    "syntax_comment_color": [0, 128, 0],
    "syntax_number_color": [9, 134, 88],
    "syntax_builtin_color": [38, 127, 153],
    "syntax_self_color": [154, 0, 154],
    "syntax_function_color": [121, 94, 38],
    "debug_execution_line_color": [255, 240, 150],
    "trailing_whitespace_color": [255, 205, 205],
}


# 內建主題在這兩組之上再換掉幾個顏色：行號區與目前行要貼著編輯區的底色，而不是
# qt-material 那種對比強烈的灰
# The built-in themes change a few colours on top of those two sets: the gutter
# and the current line sit close to the editor's background instead of the
# high-contrast grey that suits qt-material
_BUILTIN_DARK_OVERRIDES: Palette = {
    "line_number_color": [110, 116, 128],
    "line_number_background_color": [30, 32, 38],
    "current_line_color": [38, 42, 50],
    "normal_output_color": [213, 217, 224],
    "indent_guide_color": [48, 52, 62],
    "minimap_background_color": [24, 26, 31],
}
_BUILTIN_LIGHT_OVERRIDES: Palette = {
    "line_number_color": [140, 146, 156],
    "line_number_background_color": [255, 255, 255],
    "current_line_color": [243, 245, 248],
    "normal_output_color": [31, 35, 40],
    "indent_guide_color": [225, 228, 233],
    "minimap_background_color": [245, 246, 248],
}

# 內建深色與淺色主題用的顏色 / The colours for the built-in dark and light themes
BUILTIN_DARK_COLORS: Palette = {**DARK_COLORS, **_BUILTIN_DARK_OVERRIDES}
BUILTIN_LIGHT_COLORS: Palette = {**LIGHT_COLORS, **_BUILTIN_LIGHT_OVERRIDES}

# 每一組預設值；判斷「這個顏色是不是使用者自己挑的」時要全部比過
# Every set of defaults, all of which are compared when deciding whether a
# colour is one the user picked
_DEFAULT_PALETTES: tuple[Palette, ...] = (
    DARK_COLORS, LIGHT_COLORS, BUILTIN_DARK_COLORS, BUILTIN_LIGHT_COLORS)


def _source_palette(style_name: str | None) -> Palette:
    """某個樣式對應的那一組預設值 / The set of defaults a style maps to."""
    light = is_light_style(style_name)
    if is_builtin_style(style_name):
        return BUILTIN_LIGHT_COLORS if light else BUILTIN_DARK_COLORS
    return LIGHT_COLORS if light else DARK_COLORS


def palette_for(style_name: str | None) -> Palette:
    """
    取得某個樣式該用的顏色組
    The colour set a style should use.

    :param style_name: 樣式名稱 / the style name
    :return: 顏色組的副本 / a copy of the colours
    """
    return {key: list(value) for key, value in _source_palette(style_name).items()}


def _is_a_default(key: str, value: List[int] | None) -> bool:
    """這個值是不是某一組的預設值 / Whether a value is some set's default."""
    return any(value == palette.get(key) for palette in _DEFAULT_PALETTES)


def retheme(current: Palette, style_name: str | None) -> Palette:
    """
    換主題時把預設色換成新主題的，並保留使用者自己挑過的顏色
    Swap the defaults for the new theme's, keeping any colour the user picked.

    判斷方式是「這個值還是某一組的預設值嗎」：是的話就換成新主題的預設值，不是的
    話代表使用者動過，原樣保留。設定檔會把整份顏色寫回去，因此無法只靠「檔案裡有
    沒有這個鍵」來判斷。
    The test is whether a value is still one of the known defaults: if so it takes
    the new theme's default, and if not the user has chosen it and it stays. The
    settings file writes every colour back, so "is the key in the file" cannot
    tell the two apart.

    :param current: 目前生效的顏色 / the colours in effect now
    :param style_name: 要套用的樣式名稱 / the style being applied
    :return: 套用後的顏色 / the colours afterwards
    """
    target = palette_for(style_name)
    result = dict(current)
    for key, value in target.items():
        existing = current.get(key)
        if existing is None or _is_a_default(key, existing):
            result[key] = list(value)
    return result
