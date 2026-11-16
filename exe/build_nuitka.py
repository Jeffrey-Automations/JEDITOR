"""
用 Nuitka 建置 JEditor 的執行檔
Build the JEditor executable with Nuitka.

在專案根目錄、裝好 ``dev_requirements.txt``（裡面釘了 Nuitka）的環境裡執行::
Run from the repository's root, in an environment that has ``dev_requirements.txt``
(which pins Nuitka)::

    python exe/build_nuitka.py

結果是 ``exe/build/start_editor.dist`` 資料夾，裡面有 ``JEditor``（Windows 上是
``JEditor.exe``）與它需要的一切，旁邊有一份編譯報告。``python exe/check_build.py
<執行檔>`` 會檢查它；CI 兩個都跑（``.github/workflows/dev.yml`` 的 ``nuitka-build``）。
The result is a folder, ``exe/build/start_editor.dist``, holding ``JEditor``
(``JEditor.exe`` on Windows) and everything it needs, with a compilation report
beside it. ``python exe/check_build.py <the executable>`` checks it; CI runs both
(the ``nuitka-build`` job of ``.github/workflows/dev.yml``).

Nuitka 把套件編成 C，所以需要 C 編譯器：Windows 上有 Visual Studio 建置工具就用它，
沒有就讓 Nuitka 自己下載 MinGW（``--assume-yes-for-downloads``）。它的快取
（``NUITKA_CACHE_DIR``）讓第二次建置快很多。
Nuitka compiles the package to C, so a C compiler has to be there: on Windows the
Visual Studio build tools when installed, else a MinGW that Nuitka downloads by
itself (``--assume-yes-for-downloads``). Its cache (``NUITKA_CACHE_DIR``) makes a
second build much faster.
"""
from __future__ import annotations

import os
import subprocess  # nosec B404 - 固定的引數清單，不經過 shell / a fixed argument list, never a shell
import sys
from pathlib import Path

_EXE_DIR = Path(__file__).resolve().parent
_ROOT = _EXE_DIR.parent
_BUILD_DIR = _EXE_DIR / "build"
_ICON = _EXE_DIR / "editor.ico"
# 執行檔所在的資料夾 / Where the executable lands
DIST_DIR = _BUILD_DIR / "start_editor.dist"


def nuitka_command() -> list[str]:
    """
    建置執行檔的 Nuitka 指令
    The Nuitka command line that builds the executable.

    :return: 引數清單 / the argument list
    """
    command = [
        sys.executable, "-m", "nuitka",
        "--mode=standalone",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        # 有些面板用到時才匯入（menu/lazy_widgets.py），插件也是依名稱載入
        # Some panels are imported when opened (menu/lazy_widgets.py), and plugins by name
        "--include-package=je_editor",
        # 套件裡附帶的圖示、主題與語言檔 / The icons, themes and language files shipped inside it
        "--include-package-data=je_editor",
        "--output-filename=JEditor",
        f"--output-dir={_BUILD_DIR}",
        f"--report={_BUILD_DIR / 'compilation-report.xml'}",
    ]
    if sys.platform == "win32":
        command.append(f"--windows-icon-from-ico={_ICON}")
    command.append(str(_EXE_DIR / "start_editor.py"))
    return command


def main() -> int:
    """
    執行建置
    Run the build.

    :return: Nuitka 的結束碼 / Nuitka's exit code
    """
    completed = subprocess.run(  # nosemgrep  # noqa: S603  # nosec B603
        nuitka_command(), cwd=_ROOT, env=dict(os.environ), check=False, shell=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
