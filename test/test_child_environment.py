"""Tests for the environment of the programs the editor starts for the user."""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

import je_editor
from je_editor.adapters.process.local_task_runner import LocalTaskRunner
from je_editor.core.process.task_service import OutputStream, TaskSpec
from je_editor.utils.child_process import child_environment as environment_module
from je_editor.utils.child_process.child_environment import child_environment, set_child_environment_provider

# A variable a host sets for its own process, which the user's programs must not see
HOST_ONLY = "JEDITOR_TEST_HOST_ONLY"
WAIT_SECONDS = 30
_PACKAGE = Path(je_editor.__file__).resolve().parent

# Where the editor starts a program for the user, and how each start is written
STARTS_WITH_SUBPROCESS = [
    "pyside_ui/code/code_process/code_exec.py",
    "pyside_ui/code/shell_process/shell_exec.py",
    "adapters/process/local_task_runner.py",
    "pyside_ui/main_ui/test_panel/test_panel_widget.py",
]


@pytest.fixture(autouse=True)
def no_provider_left_behind():
    yield
    set_child_environment_provider(None)


@pytest.fixture()
def host_variable(monkeypatch):
    monkeypatch.setenv(HOST_ONLY, "for the host alone")


def without_the_hosts_own() -> dict[str, str]:
    return {name: value for name, value in os.environ.items() if name != HOST_ONLY}


class TestTheEnvironmentAChildGets:
    def test_with_no_host_it_is_the_editors_own(self, host_variable):
        given = child_environment()

        assert given == dict(os.environ)
        assert given[HOST_ONLY] == "for the host alone"

    def test_it_is_a_copy_that_can_be_added_to(self):
        given = child_environment()
        given["ADDED_BY_A_CALLER"] = "1"

        assert "ADDED_BY_A_CALLER" not in os.environ

    def test_a_host_decides_what_a_child_gets(self, host_variable):
        set_child_environment_provider(without_the_hosts_own)

        assert HOST_ONLY not in child_environment()
        assert child_environment()["PATH"] == os.environ["PATH"]

    def test_the_host_is_asked_for_every_program(self):
        asked = []

        def counting() -> dict[str, str]:
            asked.append(1)
            return {"RUN": str(len(asked))}

        set_child_environment_provider(counting)

        assert [child_environment()["RUN"], child_environment()["RUN"]] == ["1", "2"]

    def test_what_the_host_returned_is_not_handed_out_itself(self):
        kept = {"ONLY": "this"}
        set_child_environment_provider(lambda: kept)

        child_environment()["ADDED"] = "1"

        assert kept == {"ONLY": "this"}

    def test_unregistering_gives_the_editors_own_back(self, host_variable):
        set_child_environment_provider(without_the_hosts_own)

        set_child_environment_provider(None)

        assert HOST_ONLY in child_environment()

    def test_something_that_cannot_be_called_is_refused_at_once(self):
        with pytest.raises(TypeError):
            set_child_environment_provider({"PATH": "x"})

    def test_a_host_that_fails_does_not_stop_programs_from_running(self, host_variable, monkeypatch):
        logged = []
        monkeypatch.setattr(environment_module.jeditor_logger, "error", lambda *args: logged.append(args))

        def broken() -> dict[str, str]:
            raise RuntimeError("the host has a bug")

        set_child_environment_provider(broken)

        assert child_environment() == dict(os.environ)
        assert len(logged) == 1

    @pytest.mark.parametrize("returned", [None, ["PATH"], {"PATH": 1}, {1: "PATH"}, {"PATH": None}])
    def test_what_is_not_an_environment_is_not_used(self, returned, monkeypatch):
        logged = []
        monkeypatch.setattr(environment_module.jeditor_logger, "error", lambda *args: logged.append(args))
        set_child_environment_provider(lambda: returned)

        assert child_environment() == dict(os.environ)
        assert len(logged) == 1

    def test_the_log_names_no_value_of_the_environment(self, monkeypatch):
        logged = []
        monkeypatch.setattr(environment_module.jeditor_logger, "error", lambda *args: logged.append(args))
        set_child_environment_provider(lambda: {"API_TOKEN": 12345})

        child_environment()

        assert "12345" not in repr(logged) and "API_TOKEN" not in repr(logged)

    def test_hosts_reach_it_from_the_package(self):
        assert je_editor.set_child_environment_provider is set_child_environment_provider
        assert je_editor.child_environment is child_environment


class TestAProgramReallyStarted:
    @staticmethod
    def _seen_by_a_child(**options) -> str:
        runner = LocalTaskRunner()
        task = runner.create(TaskSpec(
            (sys.executable, "-c", f"import os; print(os.environ.get('{HOST_ONLY}', 'not set'))"), **options))
        written = []
        task.output.subscribe(lambda stream, data: written.append(data) if stream is OutputStream.STDOUT else None)
        try:
            assert task.start() is True
            assert task.wait(WAIT_SECONDS) is True
        finally:
            runner.shutdown()
        return "".join(written).strip()

    def test_with_no_host_the_child_sees_the_editors_variables(self, host_variable):
        assert self._seen_by_a_child() == "for the host alone"

    def test_a_variable_the_host_keeps_to_itself_does_not_reach_the_child(self, host_variable):
        set_child_environment_provider(without_the_hosts_own)

        assert self._seen_by_a_child() == "not set"

    def test_what_a_task_asks_for_is_added_on_top(self, host_variable):
        set_child_environment_provider(without_the_hosts_own)

        assert self._seen_by_a_child(environment={HOST_ONLY: "asked for by the task"}) == "asked for by the task"

    def test_the_terminals_shell_gets_it_too(self, qtbot, host_variable):
        from je_editor.pyside_ui.main_ui.console_widget.qprocess_adapter import ConsoleProcessAdapter

        set_child_environment_provider(without_the_hosts_own)
        adapter = ConsoleProcessAdapter()
        try:
            with qtbot.waitSignal(adapter.started, timeout=5000):
                adapter.start_shell()

            given = adapter.proc.processEnvironment()
            assert not given.contains(HOST_ONLY)
            assert given.value("PATH") == os.environ["PATH"]
        finally:
            adapter.shutdown()


def _starts_without_the_environment(source: str) -> list[int]:
    """The lines of the ``subprocess.Popen`` / ``subprocess.run`` calls in *source* that pass no ``env``."""
    missing = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        called = node.func
        if isinstance(called.value, ast.Name) and called.value.id == "subprocess" and called.attr in ("Popen", "run"):
            if not any(keyword.arg == "env" for keyword in node.keywords):
                missing.append(node.lineno)
    return missing


class TestEveryStartPassesTheEnvironment:
    """A start added later without ``env=`` would hand the host's own variables to the user's program again."""

    @pytest.mark.parametrize("module", STARTS_WITH_SUBPROCESS)
    def test_each_start_names_its_environment(self, module):
        source = (_PACKAGE / module).read_text(encoding="utf-8")

        assert "child_environment()" in source
        assert _starts_without_the_environment(source) == []

    def test_the_check_notices_a_start_without_one(self):
        assert _starts_without_the_environment("import subprocess\nsubprocess.Popen(['x'], shell=False)\n") == [2]
        assert _starts_without_the_environment("import subprocess\nsubprocess.run(['x'], env={})\n") == []
