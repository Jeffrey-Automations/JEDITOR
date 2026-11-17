"""
Tests for the Python the editor's own tools run on, run from source and packaged.

In a packaged executable ``sys.executable`` is the editor: the debugger and the
test panel started it with ``-m`` and opened another editor (PROGRESS #30).
"""
from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from je_editor.adapters.debug import debugpy_adapter
from je_editor.adapters.debug.dap_session import DapSession
from je_editor.core.debug.debug_session import DebugLaunchRequest
from je_editor.core.registry.named_registry import NamedRegistry
from je_editor.utils import packaged_build
from je_editor.utils.exception.exception_tags import compiler_not_found_error
from je_editor.utils.packaged_build import is_packaged, tool_python
from test.test_dap_session import ScriptedAdapter

_VENV_PYTHON = ("venv", "Scripts", "python.exe") if sys.platform == "win32" else ("venv", "bin", "python3")


@pytest.fixture()
def packaged(monkeypatch):
    """Stand in for a packaged build, with nothing on PATH."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(packaged_build.shutil, "which", lambda _name: None)


def _file(path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return str(path)


class TestKnowingAPackagedBuild:
    def test_run_from_source_it_is_not(self):
        assert is_packaged() is False

    def test_a_pyinstaller_build_is(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        assert is_packaged() is True

    def test_a_standalone_nuitka_build_is(self, monkeypatch):
        monkeypatch.setitem(packaged_build.__dict__, "__compiled__", SimpleNamespace(standalone=True))
        assert is_packaged() is True

    def test_a_nuitka_build_under_a_python_is_not(self, monkeypatch):
        monkeypatch.setitem(packaged_build.__dict__, "__compiled__", SimpleNamespace(standalone=False))
        assert is_packaged() is False


class TestThePythonForTools:
    def test_run_from_source_it_is_the_editors_own_whatever_was_chosen(self, tmp_path):
        assert tool_python(_file(tmp_path / "chosen.exe"), tmp_path) == sys.executable

    def test_packaged_it_is_the_one_chosen(self, packaged, tmp_path):
        chosen = _file(tmp_path / "chosen.exe")
        _file(tmp_path.joinpath(*_VENV_PYTHON))

        assert tool_python(chosen, tmp_path) == chosen

    def test_a_chosen_one_that_is_gone_gives_way_to_the_working_folders_venv(self, packaged, tmp_path):
        venv_python = _file(tmp_path.joinpath(*_VENV_PYTHON))

        assert tool_python(str(tmp_path / "gone.exe"), tmp_path) == venv_python

    def test_a_dot_venv_counts_too(self, packaged, tmp_path):
        names = ("Scripts", "python.exe") if sys.platform == "win32" else ("bin", "python3")
        dot_venv = _file(tmp_path.joinpath(".venv", *names))

        assert tool_python(None, tmp_path) == dot_venv

    def test_then_a_python_on_path(self, packaged, tmp_path, monkeypatch):
        monkeypatch.setattr(packaged_build.shutil, "which", lambda name: f"/usr/bin/{name}")

        assert tool_python(None, tmp_path) == "/usr/bin/python3"

    def test_the_microsoft_store_placeholder_is_passed_over(self, packaged, tmp_path, monkeypatch):
        found = {"python3": r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python3.exe",
                 "python": r"C:\Python312\python.exe"}
        monkeypatch.setattr(packaged_build.shutil, "which", found.get)

        assert tool_python(None, tmp_path) == r"C:\Python312\python.exe"

    def test_with_none_anywhere_there_is_none(self, packaged, tmp_path):
        assert tool_python(None, tmp_path) is None


class TestTheDebugAdapter:
    def test_run_from_source_it_runs_on_this_interpreter(self):
        assert debugpy_adapter.adapter_command("C:/other/python.exe") == (sys.executable, "-m", "debugpy.adapter")

    def test_packaged_it_runs_on_the_interpreter_of_the_launch(self, packaged, tmp_path):
        chosen = _file(tmp_path / "python.exe")

        assert debugpy_adapter.adapter_command(chosen) == (chosen, "-m", "debugpy.adapter")

    def test_packaged_with_no_python_there_is_no_command(self, packaged, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        assert debugpy_adapter.adapter_command(None) is None

    def test_a_launch_starts_the_adapter_on_its_own_interpreter(self, packaged, tmp_path):
        chosen = _file(tmp_path / "python.exe")
        adapter = ScriptedAdapter()
        session = debugpy_adapter.debugpy_session(adapter)

        assert session.launch(DebugLaunchRequest("main.py", interpreter=chosen)) is True

        assert adapter.spec.command == (chosen, "-m", "debugpy.adapter")

    def test_with_no_python_nothing_is_started_and_the_console_says_why(self, packaged, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        adapter = ScriptedAdapter()
        session = debugpy_adapter.debugpy_session(adapter)
        said: list[str] = []
        session.output.subscribe(lambda event: said.append(event.text))

        assert session.launch(DebugLaunchRequest("main.py")) is False

        assert adapter.spec is None
        assert said == [compiler_not_found_error + "\n"]

    def test_a_fixed_command_still_works(self):
        adapter = ScriptedAdapter()
        session = DapSession(("adapter",), adapter, "scripted", lambda launch: {}, lambda attach: {})

        assert session.launch(DebugLaunchRequest("main.py")) is True
        assert adapter.spec.command == ("adapter",)

    def test_packaged_it_is_registered_without_a_debugpy_of_its_own(self, packaged, monkeypatch):
        # The adapter runs on the user's Python; a debugpy inside the editor would be of no use
        monkeypatch.setattr(debugpy_adapter, "debugpy_available", lambda: False)
        registry: NamedRegistry = NamedRegistry("debug adapter")

        debugpy_adapter.register_builtin_debug_adapters(registry, ScriptedAdapter)

        assert registry.names() == ["debugpy"]


class TestTheTestPanel:
    def test_pytest_runs_on_the_python_it_is_given(self):
        from je_editor.pyside_ui.main_ui.test_panel.test_panel_widget import pytest_command

        assert pytest_command(python="C:/project/venv/python.exe")[:3] == ["C:/project/venv/python.exe", "-m", "pytest"]
        assert pytest_command()[0] == sys.executable

    def test_packaged_a_run_uses_the_chosen_interpreter(self, packaged, tmp_path, qapp):
        from je_editor.pyside_ui.main_ui.test_panel.test_panel_widget import PytestRunThread

        chosen = _file(tmp_path / "python.exe")
        thread = PytestRunThread(str(tmp_path), chosen_python=chosen)
        with patch("je_editor.pyside_ui.main_ui.test_panel.test_panel_widget.subprocess.run",
                   return_value=SimpleNamespace(stdout="", stderr="")) as run:
            thread.run()

        assert run.call_args.args[0][:3] == [chosen, "-m", "pytest"]

    def test_packaged_with_no_python_the_panel_is_told_why(self, packaged, tmp_path, qapp):
        from je_editor.pyside_ui.main_ui.test_panel.test_panel_widget import PytestRunThread

        thread = PytestRunThread(str(tmp_path))
        said: list[str] = []
        thread.finished_output.connect(said.append)
        with patch("je_editor.pyside_ui.main_ui.test_panel.test_panel_widget.subprocess.run") as run:
            thread.run()

        run.assert_not_called()
        assert said == [compiler_not_found_error]
