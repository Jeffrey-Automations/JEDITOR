"""
Python 的除錯轉接器：debugpy
The debug adapter for Python: debugpy.

debugpy 的轉接器以 ``python -m debugpy.adapter`` 啟動，從標準輸入與輸出講 DAP。
轉接器用編輯器自己的直譯器跑（debugpy 裝在那裡），被除錯的程式則可以用別的
直譯器：debugpy 會把自己帶進去，那個環境不必另外安裝。
debugpy's adapter is started with ``python -m debugpy.adapter`` and speaks DAP
over standard input and output. The adapter runs on the editor's own
interpreter, where debugpy is installed, while the program being debugged may
use another one: debugpy brings itself along, so that environment needs no
install of its own.

打包好的執行檔沒有自己的直譯器（``sys.executable`` 是編輯器本身），轉接器就用使用者的
Python 跑（``utils/packaged_build.tool_python``），那個 Python 要裝有 debugpy；沒裝的話，
它印出的錯誤會出現在除錯主控台。
A packaged executable has no interpreter of its own (``sys.executable`` is the
editor itself), so the adapter runs on the user's Python
(``utils/packaged_build.tool_python``), which needs debugpy installed; when it
has not, its error shows in the debug console.
"""
from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable

from je_editor.adapters.debug.dap_session import DapSession
from je_editor.adapters.debug.socket_channel import SocketChannel
from je_editor.core.debug.debug_session import (
    DebugAttachRequest, DebugLaunchRequest, DebugSessionFactory
)
from je_editor.core.process.task_service import TaskRunner
from je_editor.core.registry.named_registry import NamedRegistry
from je_editor.utils.packaged_build import is_packaged, tool_python

ADAPTER_NAME = "debugpy"
_ADAPTER_MODULE = "debugpy.adapter"
_TYPE = "python"


def debugpy_available() -> bool:
    """
    這個直譯器能不能啟動 debugpy 的轉接器
    Whether this interpreter can start debugpy's adapter.

    :return: debugpy 有安裝時為 ``True`` / ``True`` when debugpy is installed
    """
    return importlib.util.find_spec(ADAPTER_NAME) is not None


def adapter_command(interpreter: str | None = None) -> tuple[str, ...] | None:
    """
    啟動 debugpy 轉接器的指令
    The command that starts debugpy's adapter.

    :param interpreter: 這次要用的直譯器；只有打包版會用它跑轉接器
        the interpreter of this run; only a packaged build runs the adapter on it
    :return: 引數清單；打包版找不到 Python 時為 ``None``
        the argument list, or ``None`` when a packaged build finds no Python
    """
    python = tool_python(interpreter) if is_packaged() else sys.executable
    return (python, "-m", _ADAPTER_MODULE) if python else None


def _command_for(request_: object) -> tuple[str, ...] | None:
    """一次請求的轉接器指令，用它指定的直譯器 / The adapter's command for one request, on the interpreter it names."""
    return adapter_command(getattr(request_, "interpreter", "") or None)


def launch_arguments(request: DebugLaunchRequest) -> dict:
    """
    把啟動請求變成 debugpy 的 ``launch`` 引數
    Turn a launch request into debugpy's ``launch`` arguments.

    輸出走除錯協定回來（``internalConsole``），不另外開終端機。
    Output comes back through the protocol (``internalConsole``); no terminal is opened.

    :param request: 啟動所需的資訊 / what to launch
    :return: ``launch`` 的引數 / the ``launch`` arguments
    """
    arguments: dict = {
        "request": "launch", "type": _TYPE, "program": request.program,
        "args": list(request.arguments), "console": "internalConsole", "redirectOutput": True,
        "stopOnEntry": request.stop_on_entry, "justMyCode": request.just_my_code,
    }
    if request.working_directory:
        arguments["cwd"] = request.working_directory
    if request.interpreter:
        arguments["python"] = [request.interpreter]
    return arguments


def attach_arguments(request: DebugAttachRequest) -> dict:
    """
    把連線請求變成 debugpy 的 ``attach`` 引數
    Turn an attach request into debugpy's ``attach`` arguments.

    以 ``debugpy --listen`` 啟動的程式自己帶著轉接器在那個連接埠等，所以連線是直接
    連過去講協定（見 :func:`attach_channel`），這裡的 ``connect`` 只是說明連到哪裡。
    A program started with ``debugpy --listen`` waits on that port with an
    adapter of its own, so the protocol is spoken straight to it (see
    :func:`attach_channel`) and ``connect`` here only says where that is.

    :param request: 要接上哪裡 / where to attach
    :return: ``attach`` 的引數 / the ``attach`` arguments
    """
    return {
        "request": "attach", "type": _TYPE, "justMyCode": request.just_my_code,
        "connect": {"host": request.host, "port": request.port},
    }


def attach_channel(request: DebugAttachRequest) -> SocketChannel:
    """
    接上等待中的程式要用的通道：直接連到它的連接埠
    The channel for attaching to a waiting program: a connection straight to its port.

    :param request: 要接上哪裡 / where to attach
    :return: 還沒連線的通道 / a channel that has not connected yet
    """
    return SocketChannel(request.host, request.port)


def debugpy_session(runner: TaskRunner) -> DapSession:
    """
    建立一個以 debugpy 除錯的工作階段
    Build a session that debugs with debugpy.

    :param runner: 用來啟動轉接器的地方 / where the adapter is started
    :return: 還沒啟動的工作階段 / a session that has not started yet
    """
    return DapSession(_command_for, runner, ADAPTER_NAME, launch_arguments, attach_arguments,
                      attach_channel)


def register_builtin_debug_adapters(registry: NamedRegistry[DebugSessionFactory],
                                    runner: Callable[[], TaskRunner]) -> None:
    """
    登記內建的除錯轉接器
    Register the built-in debug adapters.

    debugpy 沒有安裝時不登記，編輯器就會退回原本的 pdb 主控台。打包版一律登記：轉接器在使用者的
    Python 上跑，裝在編輯器裡的 debugpy 用不到。
    Without debugpy nothing is registered, and the editor falls back to its pdb
    console. A packaged build always registers it: the adapter runs on the
    user's Python, and a debugpy inside the editor would be of no use.

    :param registry: 除錯轉接器的登記表 / the registry of debug adapters
    :param runner: 取得要用來啟動轉接器的執行器 / gives the runner the adapter is started with
    """
    if is_packaged() or debugpy_available():
        registry.register(ADAPTER_NAME, lambda: debugpy_session(runner()))
