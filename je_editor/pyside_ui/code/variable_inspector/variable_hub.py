"""
一個視窗的變數檢視器從這裡拿變數
Where a window's variable inspectors get the variables they show.

檢視器本身只會顯示交給它的東西；以前沒有任何程式交東西給它，所以永遠是空的。
變數有兩個來源：IPython 主控台的命名空間（主控台在行程內執行，命名空間就是一個
dict，可以直接看、直接改），以及暫停中的除錯器（變數在另一個行程裡，只能照除錯器
回報的文字顯示）。除錯器暫停時以它為準，因為那時使用者看的是停下來的程式。
The inspector only shows what it is given, and nothing gave it anything, so it
was always empty. Variables come from two places: the IPython console's
namespace (the console runs in this process, so the namespace is a dict that can
be read and changed directly) and a paused debugger (its variables live in
another process and can only be shown as the text the debugger reports). A
paused debugger wins, since the stopped program is what the user is looking at.
"""
from __future__ import annotations

import weakref
from collections.abc import Mapping
from enum import Enum

from PySide6.QtCore import QObject, Signal

from je_editor.core.debug.debug_session import DebugState, StopEvent
from je_editor.utils.variable_inspector.variable_rows import VariableRow, debugger_rows


class VariableSource(Enum):
    """
    檢視器現在顯示的是誰的變數
    Whose variables the inspector is showing.
    """

    NONE = "none"
    CONSOLE = "console"
    DEBUGGER = "debugger"


class VariableHub(QObject):
    """
    收集一個視窗裡可以檢視的變數
    Gathers the variables of one window that can be inspected.

    只在畫面執行緒上使用：行程內的主控台也在這條執行緒上執行程式碼，除錯控制器的
    訊號也是送到這裡。
    Used on the GUI thread only: the in-process console runs its code on that
    thread, and the debug controller's signals arrive there too.
    """

    # 來源換了，或暫停中的變數到了 / The source changed, or a paused program's variables arrived
    changed = Signal()

    def __init__(self, debug_controller: QObject | None = None, parent: QObject | None = None) -> None:
        """
        :param debug_controller: 視窗的除錯控制器；沒有時只看主控台
            the window's debug controller; without one only consoles are looked at
        :param parent: Qt 父物件 / the Qt parent
        """
        super().__init__(parent)
        self.setObjectName("VariableHub")
        self._controller = debug_controller
        # 弱參考：主控台關掉之後不該因為這裡而留著 / Weak: a closed console must not live on because of this
        self._shells: list[weakref.ref] = []
        self._paused = False
        self._thread_id = 0
        self._reference = 0
        self._frame_names: dict[int, str] = {}
        self._frame_name = ""
        self._paused_rows: list[VariableRow] = []
        if debug_controller is not None:
            debug_controller.stopped.connect(self._on_stopped)
            debug_controller.stack_ready.connect(self._on_stack)
            debug_controller.scopes_ready.connect(self._on_scopes)
            debug_controller.variables_ready.connect(self._on_variables)
            debug_controller.state_changed.connect(self._on_state)

    # ------------------------------------------------------------------
    # 主控台 / Consoles
    # ------------------------------------------------------------------

    def add_console(self, shell: object) -> None:
        """
        登記一個行程內的 IPython shell；最後登記的那個是檢視器顯示的
        Register an in-process IPython shell; the one registered last is the one shown.

        :param shell: 有 ``user_ns`` 與 ``user_ns_hidden`` 的 shell
            a shell with ``user_ns`` and ``user_ns_hidden``
        """
        self.remove_console(shell)
        self._shells.append(weakref.ref(shell))
        self.changed.emit()

    def remove_console(self, shell: object) -> None:
        """
        主控台關了：不再顯示它的變數
        A console closed: its variables are shown no more.

        :param shell: 之前登記的 shell / the shell registered before
        """
        before = len(self._shells)
        self._shells = [ref for ref in self._shells if ref() is not None and ref() is not shell]
        if len(self._shells) != before:
            self.changed.emit()

    def _shell(self) -> object | None:
        """最後登記、還活著的 shell / The shell registered last that is still alive."""
        for ref in reversed(self._shells):
            shell = ref()
            if shell is not None:
                return shell
        return None

    def namespace(self) -> dict | None:
        """
        主控台的命名空間，就是它本身，改它就是改主控台裡的變數
        The console's namespace itself: changing it changes the console's variables.

        :return: 命名空間；沒有主控台時為 ``None`` / the namespace, ``None`` without a console
        """
        namespace = getattr(self._shell(), "user_ns", None)
        return namespace if isinstance(namespace, dict) else None

    def hidden(self) -> Mapping[str, object]:
        """
        命名空間裡 IPython 自己放的名稱
        The names in the namespace that IPython put there itself.

        :return: 名稱與物件 / the names and their objects
        """
        hidden = getattr(self._shell(), "user_ns_hidden", None)
        return hidden if isinstance(hidden, Mapping) else {}

    # ------------------------------------------------------------------
    # 現在顯示誰的 / What is shown now
    # ------------------------------------------------------------------

    def source(self) -> VariableSource:
        """
        檢視器現在該顯示誰的變數
        Whose variables the inspector should show now.

        :return: 暫停中的除錯器優先，其次是主控台 / a paused debugger first, then a console
        """
        if self._paused:
            return VariableSource.DEBUGGER
        return VariableSource.CONSOLE if self.namespace() is not None else VariableSource.NONE

    def paused_rows(self) -> list[VariableRow]:
        """
        暫停的那一層的變數；還沒查到時是空的
        The variables of the paused frame; empty until they have arrived.

        :return: 列 / the rows
        """
        return list(self._paused_rows)

    def paused_frame(self) -> str:
        """
        暫停在哪個函式
        The function the program is paused in.

        :return: 函式名稱，還不知道時為空字串 / the function's name, empty while unknown
        """
        return self._frame_name

    # ------------------------------------------------------------------
    # 除錯器 / The debugger
    # ------------------------------------------------------------------

    def _on_stopped(self, stop: StopEvent) -> None:
        """程式停了：查它的堆疊，一路查到最裡面那一層的變數 / The program stopped: ask for its stack, down to the innermost frame's variables."""
        self._paused = True
        self._thread_id = stop.thread_id
        self._reference = 0
        self._frame_name = ""
        self._paused_rows = []
        self.changed.emit()
        # 除錯面板也會問，但它不一定開著；多問一次只是多一個回覆
        # The debug panel asks too, but it may not be open; asking twice costs one more reply
        self._controller.request_stack(stop.thread_id)

    def _on_stack(self, thread_id: int, frames: tuple) -> None:
        """堆疊到了：記下每一層的名稱，查最裡面那一層 / The stack arrived: note each frame's name and ask about the innermost."""
        if not self._paused or thread_id != self._thread_id or not frames:
            return
        self._frame_names = {frame.frame_id: frame.name for frame in frames}
        self._controller.request_scopes(frames[0].frame_id)

    def _on_scopes(self, frame_id: int, scopes: tuple) -> None:
        """
        一層的變數群組到了：跟著它，查它的區域變數
        A frame's scopes arrived: follow that frame and ask for its locals.

        使用者在除錯面板選了別層時，面板會查那一層的群組，檢視器也跟著換過去。
        When the user picks another frame in the debug panel, the panel asks for
        that frame's scopes, and the inspector follows it there.
        """
        if not self._paused:
            return
        cheap = [scope for scope in scopes if scope.variables_reference and not scope.expensive]
        if not cheap:
            return
        self._reference = cheap[0].variables_reference
        self._frame_name = self._frame_names.get(frame_id, "")
        self._controller.request_variables(self._reference)

    def _on_variables(self, reference: int, variables: tuple) -> None:
        """等著的那一組變數到了 / The group of variables waited for arrived."""
        if not self._paused or reference != self._reference:
            return
        self._paused_rows = debugger_rows(variables)
        self.changed.emit()

    def _on_state(self, state: DebugState) -> None:
        """程式繼續跑或結束了：回到主控台的變數 / The program runs on or ended: back to the console's variables."""
        if state is DebugState.PAUSED or not self._paused:
            return
        self._paused = False
        self._reference = 0
        self._frame_name = ""
        self._frame_names = {}
        self._paused_rows = []
        self.changed.emit()
