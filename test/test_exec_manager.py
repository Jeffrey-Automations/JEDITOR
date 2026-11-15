"""Tests for ExecManager and ShellManager inheritance from BaseProcessManager."""
from __future__ import annotations

import queue
from unittest.mock import MagicMock

from je_editor.pyside_ui.code.code_process.code_exec import ExecManager
from je_editor.pyside_ui.code.shell_process.shell_exec import ShellManager


class TestExecManagerInheritance:
    def test_inherits_base(self):
        from je_editor.pyside_ui.code.base_process_manager import BaseProcessManager
        assert issubclass(ExecManager, BaseProcessManager)

    def test_still_run_program_alias(self):
        mgr = ExecManager()
        assert mgr.still_run_program is True
        mgr.still_run_program = False
        assert mgr.still_running is False
        mgr.still_running = True
        assert mgr.still_run_program is True

    def test_exit_message_prefix(self):
        mgr = ExecManager()
        assert mgr._exit_message_prefix() == "Program"

    def test_default_queues(self):
        mgr = ExecManager()
        assert isinstance(mgr.run_output_queue, queue.Queue)
        assert isinstance(mgr.run_error_queue, queue.Queue)


class TestShellManagerInheritance:
    def test_inherits_base(self):
        from je_editor.pyside_ui.code.base_process_manager import BaseProcessManager
        assert issubclass(ShellManager, BaseProcessManager)

    def test_still_run_shell_alias(self):
        mgr = ShellManager()
        assert mgr.still_run_shell is True
        mgr.still_run_shell = False
        assert mgr.still_running is False

    def test_exit_message_prefix(self):
        mgr = ShellManager()
        assert mgr._exit_message_prefix() == "Shell command"

    def test_after_done_function_stored(self):
        fn = MagicMock()
        mgr = ShellManager(after_done_function=fn)
        assert mgr.after_done_function is fn


class TestTheSlotARunWasStoredIn:
    """
    A finished run cleared ``exec_program`` whatever it was: a debugger left
    ``exec_python_debugger`` set, so that tab could never debug again.
    """

    def _manager(self, tab):
        from je_editor.pyside_ui.code.code_process.code_exec import ExecManager
        manager = ExecManager.__new__(ExecManager)
        manager.main_window = tab
        manager.timer = None
        manager.exit_program = lambda: None
        return manager

    def test_a_finished_debugger_frees_the_debugger_slot(self):
        from types import SimpleNamespace
        tab = SimpleNamespace(exec_program=None, exec_python_debugger=None)
        manager = self._manager(tab)
        tab.exec_python_debugger = manager
        manager.full_exit_program()
        assert tab.exec_python_debugger is None

    def test_a_finished_debugger_leaves_a_running_program_alone(self):
        from types import SimpleNamespace
        running = object()
        tab = SimpleNamespace(exec_program=running, exec_python_debugger=None)
        manager = self._manager(tab)
        tab.exec_python_debugger = manager
        manager.full_exit_program()
        assert tab.exec_program is running

    def test_a_finished_program_frees_the_program_slot(self):
        from types import SimpleNamespace
        tab = SimpleNamespace(exec_program=None, exec_python_debugger=None)
        manager = self._manager(tab)
        tab.exec_program = manager
        manager.full_exit_program()
        assert tab.exec_program is None
