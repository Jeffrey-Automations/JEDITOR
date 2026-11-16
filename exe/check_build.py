"""
檢查 exe/build_nuitka.py 建出來的執行檔，CI 建置之後就跑這個
Check an executable that exe/build_nuitka.py built, the way CI does after the build.

    python exe/check_build.py exe/build/start_editor.dist/JEditor.exe

在 Qt 的 offscreen 平台上啟動編輯器，過一段時間它還在執行才算啟動成功；之後連同它
啟動的程式一起停掉。只用標準函式庫：它在建置旁邊的一般 Python 裡執行。
The editor is started on Qt's offscreen platform and counts as started when it
is still running after a while; it is then stopped with everything it started.
Standard library only: it runs in a plain Python, beside the build.
"""
from __future__ import annotations

import os
import subprocess  # nosec B404 - 固定的引數清單，不經過 shell / fixed argument lists, never a shell
import sys
import tempfile
import time
from pathlib import Path

# 編輯器要撐過這麼久才算啟動成功 / How long the editor has to stay up to count as started
IDE_UP_SECONDS = 60
_POLL_SECONDS = 1
_STOP_SECONDS = 30
_LAST_LINES = 30


def check_editor_starts(executable: Path) -> str:
    """
    編輯器啟動並保持執行
    The editor starts and stays up.

    :param executable: 建出來的執行檔 / the built executable
    :return: 觀察了多久 / how long it was watched
    :raises AssertionError: 它在時間內就結束了 / when it ended within that time
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as home:
        log = Path(home) / "stderr.txt"
        # 自己的家目錄與工作目錄：不讀也不留下這台機器上的設定
        # A home and working folder of its own: no settings of this machine are read or left behind
        environment = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "USERPROFILE": home, "HOME": home}
        with log.open("wb") as errors:
            editor = subprocess.Popen(  # nosemgrep  # noqa: S603  # nosec B603
                [str(executable)], cwd=home, env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=errors, shell=False)
            try:
                code = _watch(editor)
            finally:
                _stop_tree(editor)
        if code is not None:
            raise AssertionError(f"the editor ended with {code}: {_tail(log.read_bytes())}")
    return f"still running after {IDE_UP_SECONDS} s"


def _watch(process: subprocess.Popen) -> int | None:
    """
    看著程式一段時間
    Watch a process for a while.

    :return: 它的結束碼；還在執行時為 ``None`` / its exit code, ``None`` while it still runs
    """
    deadline = time.monotonic() + IDE_UP_SECONDS
    while time.monotonic() < deadline and process.poll() is None:
        time.sleep(_POLL_SECONDS)
    return process.poll()


def _stop_tree(process: subprocess.Popen) -> None:
    """停掉程式與它啟動的所有程式 / Stop a process and every process it started."""
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        taskkill = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"
        subprocess.run(  # nosemgrep  # noqa: S603  # nosec B603
            [str(taskkill), "/T", "/F", "/PID", str(process.pid)], capture_output=True,
            timeout=_STOP_SECONDS, check=False, shell=False)
    # taskkill can be refused, and on other systems there is no tree to end: the process itself then
    if process.poll() is None:
        process.kill()
    process.wait(_STOP_SECONDS)


def _tail(output: bytes | None) -> str:
    """程式最後寫的幾行，放進失敗訊息 / The last lines a process wrote, for a failure message."""
    lines = (output or b"").decode("utf-8", errors="replace").splitlines()
    return "\n".join(lines[-_LAST_LINES:])


def main(arguments: list[str]) -> int:
    """
    檢查引數指定的執行檔
    Check the executable named in the arguments.

    :param arguments: 一個引數：執行檔的路徑 / one argument: the executable's path
    :return: 通過時為 0 / 0 when it passes
    """
    if len(arguments) != 1 or not Path(arguments[0]).is_file():
        sys.stderr.write("usage: python exe/check_build.py <the built executable>\n")
        return 2
    try:
        sys.stdout.write(f"[pass] editor start: {check_editor_starts(Path(arguments[0]).resolve())}\n")
    except (AssertionError, OSError, subprocess.SubprocessError) as error:
        sys.stdout.write(f"[FAIL] editor start: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
