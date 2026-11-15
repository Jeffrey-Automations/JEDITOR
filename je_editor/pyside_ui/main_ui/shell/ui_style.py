"""
把一個樣式名稱套用到整個應用程式
Apply a style, by name, to the whole application.

樣式有兩種：專案自己的主題（QSS 由色票組成）與 qt-material 的樣式檔。選單、啟動
流程與宿主程式都呼叫這裡，由這裡決定走哪一條路，並讓圖示跟著換色。
A style is one of two kinds: the project's own themes, whose QSS is built from
tokens, and the qt-material style files. The menu, the startup and a host
application all call in here, which picks the route and recolours the icons to
match.
"""
from __future__ import annotations

import atexit
import shutil
import tempfile
from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from je_editor.pyside_ui.main_ui.shell.shell_icons import refresh_action_icons
from je_editor.utils.logging.loggin_instance import jeditor_logger
from je_editor.utils.theme.ui_icons import icon_svg
from je_editor.utils.theme.ui_stylesheet import (
    IMAGE_TAB_CLOSE, IMAGE_TAB_CLOSE_HOVER, build_stylesheet
)
from je_editor.utils.theme.ui_theme import DEFAULT_STYLE, Tokens, is_builtin_style, tokens_for

# 內建主題以 Fusion 為底：它完全照調色盤畫，沒被 QSS 蓋到的細節（樹的箭頭、勾選框）
# 才會跟著主題走
# The built-in themes sit on Fusion, which paints purely from the palette, so
# whatever the QSS does not reach -- a tree's arrows, a check box -- still
# follows the theme
_BASE_STYLE = "Fusion"
# 應用程式上記著「底層樣式已經設過」的屬性。setStyle 會把每個元件重新拋光一次，
# 元件多的時候要一秒以上，而且全在畫面執行緒上，所以同一個樣式不設第二次
# The application property recording that the base style is already set.
# setStyle re-polishes every widget, over a second with many of them and all of
# it on the GUI thread, so the same style is never set twice
_BASE_STYLE_PROPERTY = "jeditor_base_style"

# 分頁關閉鈕的邊長（像素）/ The edge of a tab's close button, in pixels
_CLOSE_ICON_SIZE = 16

# QSS 用到的圖檔放在這個行程專用的暫存資料夾，結束時刪掉
# The image files the QSS refers to live in a temporary folder of this process, removed at exit
_image_directory: Path | None = None
# 已經寫好圖檔的樣式；同一個樣式再套用時不必再寫一次檔
# The styles whose images are already written, so applying one again writes no file
_written_images: dict[str, dict[str, str]] = {}


def _image_folder() -> Path:
    """取得放圖檔的暫存資料夾，第一次用到時建立 / The temporary image folder, created on first use."""
    global _image_directory
    if _image_directory is None:
        _image_directory = Path(tempfile.mkdtemp(prefix="jeditor_theme_"))
        atexit.register(shutil.rmtree, _image_directory, ignore_errors=True)
    return _image_directory


def write_theme_images(tokens: Tokens, style_name: str) -> dict[str, str]:
    """
    把 QSS 要用的圖示寫成檔案
    Write the icons the QSS needs out as files.

    :param tokens: 色票 / the tokens
    :param style_name: 樣式名稱，用來區分檔名 / the style's name, which keeps the file names apart
    :return: 圖檔名稱對應路徑（正斜線）/ image name mapped to its path, with forward slashes
    :raises OSError: 寫不進暫存資料夾時 / when the temporary folder cannot be written
    """
    written = _written_images.get(style_name)
    if written is not None:
        return dict(written)
    urls: dict[str, str] = {}
    for name, colour in ((IMAGE_TAB_CLOSE, tokens["text_muted"]),
                         (IMAGE_TAB_CLOSE_HOVER, tokens["text"])):
        target = _image_folder() / f"{style_name}_{name}.svg"
        target.write_text(icon_svg("close", colour, _CLOSE_ICON_SIZE), encoding="utf-8")
        urls[name] = target.as_posix()
    _written_images[style_name] = dict(urls)
    return urls


def _builtin_stylesheet(tokens: Tokens, style_name: str) -> str:
    """組出內建主題的 QSS；圖檔寫不出來時退回沒有圖的版本 / A built-in theme's QSS, without images when they cannot be written."""
    try:
        return build_stylesheet(tokens, write_theme_images(tokens, style_name))
    except OSError as error:
        jeditor_logger.warning("Theme images could not be written: %r", error)
        return build_stylesheet(tokens)


def build_palette(tokens: Tokens) -> QPalette:
    """
    用色票組出 Qt 的調色盤
    Build Qt's palette from the tokens.

    :param tokens: 色票 / the tokens
    :return: 調色盤 / the palette
    """
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: "surface",
        QPalette.ColorRole.WindowText: "text",
        QPalette.ColorRole.Base: "editor_background",
        QPalette.ColorRole.AlternateBase: "surface",
        QPalette.ColorRole.Text: "text",
        QPalette.ColorRole.Button: "raised",
        QPalette.ColorRole.ButtonText: "text",
        QPalette.ColorRole.ToolTipBase: "raised",
        QPalette.ColorRole.ToolTipText: "text",
        QPalette.ColorRole.Highlight: "selection",
        QPalette.ColorRole.HighlightedText: "text",
        QPalette.ColorRole.PlaceholderText: "text_muted",
        QPalette.ColorRole.Link: "accent",
        QPalette.ColorRole.Mid: "border",
        QPalette.ColorRole.Dark: "chrome",
        QPalette.ColorRole.Light: "hover",
    }
    for role, token in roles.items():
        palette.setColor(role, QColor(tokens[token]))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                 QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(tokens["text_disabled"]))
    return palette


def _apply_material(window: QWidget | None, app: QApplication, style_name: str) -> None:
    """套用一個 qt-material 樣式檔 / Apply one qt-material style file."""
    # 先放掉內建主題留下的調色盤，否則 qt-material 的樣式會疊在別人的顏色上
    # Drop the palette a built-in theme left behind first, or the qt-material
    # style would sit on top of somebody else's colours
    app.setPalette(app.style().standardPalette())
    apply_from_window = getattr(window, "apply_stylesheet", None)
    if callable(apply_from_window):
        apply_from_window(app, style_name)
        return
    from qt_material import apply_stylesheet
    apply_stylesheet(app, theme=style_name)


def apply_ui_style(window: QWidget | None, style_name: str | None) -> bool:
    """
    把樣式套用到應用程式，並重畫視窗的圖示
    Apply a style to the application and redraw the window's icons.

    :param window: 主視窗；``None`` 時只套用樣式 / the main window, or ``None``
        to apply the style alone
    :param style_name: 樣式名稱，``None`` 表示預設樣式 / the style's name,
        ``None`` meaning the default one
    :return: 有套用時為 ``True``；還沒有 ``QApplication`` 時為 ``False``
        ``True`` when it was applied, ``False`` with no ``QApplication`` yet
    """
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return False
    name = style_name or DEFAULT_STYLE
    jeditor_logger.info(f"ui_style.py apply_ui_style {name}")
    tokens = tokens_for(name)
    if is_builtin_style(name):
        if app.property(_BASE_STYLE_PROPERTY) != _BASE_STYLE:
            app.setStyle(_BASE_STYLE)
            app.setProperty(_BASE_STYLE_PROPERTY, _BASE_STYLE)
        app.setPalette(build_palette(tokens))
        app.setStyleSheet(_builtin_stylesheet(tokens, name))
    else:
        _apply_material(window, app, name)
    if window is not None:
        refresh_action_icons(window, tokens)
    return True
