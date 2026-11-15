"""
編輯器替使用者啟動的程式用什麼環境變數
The environment of the programs the editor starts for the user.

以前這些程式直接沿用編輯器自己的環境。嵌入編輯器的宿主（例如 PyBreeze）會為了自己
這個行程設定一些變數，那些變數跟著進了使用者的程式：PyBreeze 設的
``LOCUST_SKIP_MONKEY_PATCH`` 讓從編輯器執行的 locust 腳本一次只跑一個使用者。
宿主可以在這裡登記一個函式，由它決定子行程拿到的環境。
These programs used to inherit the editor's own environment. A host that embeds
the editor (PyBreeze, say) sets variables for its own process, and they went
along into the user's programs: PyBreeze's ``LOCUST_SKIP_MONKEY_PATCH`` made a
locust script run from the editor run one user at a time. A host registers a
function here, and it decides what environment a child gets.

適用於執行、除錯、Shell、終端機與測試面板啟動的程式；編輯器自己用的工具（git、
ruff、語言伺服器）不經過這裡。
It applies to what Run, the debugger, the shell, the terminal and the test panel
start; the tools the editor uses for itself (git, ruff, language servers) do not
go through here.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Mapping

from je_editor.utils.logging.loggin_instance import jeditor_logger

EnvironmentProvider = Callable[[], Mapping[str, str]]

# 宿主登記的函式；沒有登記時子行程沿用編輯器的環境
# The function the host registered; without one a child inherits the editor's environment
_provider: EnvironmentProvider | None = None


def set_child_environment_provider(provider: EnvironmentProvider | None) -> None:
    """
    登記決定子行程環境的函式
    Register the function that decides a child process's environment.

    每啟動一個程式就呼叫一次，所以它看到的是當下的環境。
    It is called once for every program started, so it sees the environment as
    it is at that moment.

    :param provider: 回傳完整環境（名稱與值都是字串）的函式；``None`` 取消登記
        a function returning the whole environment, names and values as
        strings; ``None`` to unregister
    :raises TypeError: 給的不是可呼叫的東西 / when what is given cannot be called
    """
    global _provider
    if provider is not None and not callable(provider):
        raise TypeError("the child environment provider has to be callable")
    _provider = provider


def child_environment() -> dict[str, str]:
    """
    編輯器替使用者啟動的程式該拿到的環境
    The environment a program the editor starts for the user should get.

    宿主的函式出錯或回傳的不是環境時，改用編輯器自己的環境並記錄下來：寧可讓程式
    照以前的方式跑起來，也不要讓「執行」因為宿主的錯而完全不能用。
    When the host's function fails, or returns something that is not an
    environment, the editor's own is used and the fault is logged: better that
    the program runs as it used to than that Run stops working over a host's bug.

    :return: 一份新的 dict，可以再加東西 / a new dict, free to be added to
    """
    if _provider is None:
        return dict(os.environ)
    try:
        given = _provider()
    except Exception as error:  # noqa: BLE001 — 宿主的函式可能丟任何例外 / a host's function may raise anything
        jeditor_logger.error("child_environment.py the host's provider failed: %r", error)
        return dict(os.environ)
    if not isinstance(given, Mapping) or not all(
            isinstance(name, str) and isinstance(value, str) for name, value in given.items()):
        jeditor_logger.error(
            "child_environment.py the host's provider returned a %s that is not an environment",
            type(given).__name__)
        return dict(os.environ)
    return dict(given)
