"""
編輯器是不是打包好的執行檔，以及要用哪個 Python 跑它自己的工具
Whether the editor runs as a packaged executable, and which Python runs its own tools.

除錯器的轉接器（``-m debugpy.adapter``）與測試面板（``-m pytest``）是以某個 Python 啟動
的模組。從原始碼執行時那就是編輯器自己的直譯器；在打包好的執行檔裡，``sys.executable``
是編輯器本身，拿它加 ``-m`` 啟動只會再開一個編輯器。那時改用使用者的 Python：在
Python Env 選的那一個，否則工作資料夾裡的 ``venv`` 或 ``.venv``，再否則 ``PATH`` 上的。
The debugger's adapter (``-m debugpy.adapter``) and the test panel
(``-m pytest``) are modules started with some Python. Run from source that is
the editor's own interpreter; in a packaged executable ``sys.executable`` is the
editor itself, and started with ``-m`` it only opens another editor. Then the
user's Python is used: the one chosen under Python Env, else a ``venv`` or
``.venv`` in the working folder, else one on ``PATH``.

PyInstaller 以 ``sys.frozen`` 標記打包的程式；Nuitka 的 standalone 建置則是每個編譯過的
模組都有 ``__compiled__``，它的 ``standalone`` 為真。
PyInstaller marks a packaged program with ``sys.frozen``; a standalone Nuitka
build gives every compiled module a ``__compiled__`` whose ``standalone`` is true.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from je_editor.utils.logging.loggin_instance import jeditor_logger

# 工作資料夾裡會被當成專案環境的資料夾 / The folders in the working folder taken as the project's environment
_VENV_FOLDERS = ("venv", ".venv")
# Windows 的 Microsoft Store 預留的 python.exe：沒裝 Python 時它只會印出提示並以 9009 結束
# Windows' Microsoft Store placeholder python.exe: with no Python installed it
# only prints a hint and exits with 9009
_STORE_PLACEHOLDER = "windowsapps"


def is_packaged() -> bool:
    """
    ``sys.executable`` 是不是編輯器本身，而不是一個 Python
    Whether ``sys.executable`` is the editor itself rather than a Python.

    :return: 打包好的執行檔時為 ``True`` / ``True`` in a packaged executable
    """
    if getattr(sys, "frozen", False):
        return True
    compiled = globals().get("__compiled__")
    return bool(getattr(compiled, "standalone", False))


def _is_file(path: str | Path) -> bool:
    """這個路徑是不是一個檔案；查不到時當成不是 / Whether a path is a file; one that cannot be looked at is not."""
    try:
        return Path(path).is_file()
    except OSError as error:
        jeditor_logger.info("packaged_build.py %s cannot be looked at: %r", path, error)
        return False


def _venv_python(folder: Path) -> str | None:
    """工作資料夾裡 ``venv`` 或 ``.venv`` 的 Python / The Python of a ``venv`` or ``.venv`` in a folder."""
    names = ("Scripts/python.exe",) if sys.platform == "win32" else ("bin/python3", "bin/python")
    for venv in _VENV_FOLDERS:
        for name in names:
            candidate = folder / venv / name
            if _is_file(candidate):
                return str(candidate)
    return None


def _python_on_path() -> str | None:
    """``PATH`` 上的 Python，略過 Microsoft Store 的預留程式 / A Python on ``PATH``, passing over the Store's placeholder."""
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found and _STORE_PLACEHOLDER not in found.lower():
            return found
    return None


def tool_python(chosen: str | None = None, working_folder: str | Path | None = None) -> str | None:
    """
    執行編輯器自己的工具（除錯轉接器、pytest）要用的 Python
    The Python the editor's own tools (the debug adapter, pytest) are run with.

    :param chosen: 使用者在 Python Env 選的直譯器 / the interpreter chosen under Python Env
    :param working_folder: 找 ``venv`` 的地方，預設是目前的工作目錄
        where a ``venv`` is looked for; the current directory by default
    :return: 從原始碼執行時是 ``sys.executable``；打包版依序是選的、``venv`` 的、``PATH`` 上的，
        都沒有時為 ``None``
        ``sys.executable`` when run from source; in a packaged build the one
        chosen, a ``venv``'s or one on ``PATH``, in that order, and ``None`` when
        there is none
    """
    if not is_packaged():
        return sys.executable
    if chosen and _is_file(chosen):
        return chosen
    return _venv_python(Path(working_folder) if working_folder else Path.cwd()) or _python_on_path()
