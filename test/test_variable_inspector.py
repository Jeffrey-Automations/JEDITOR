"""Tests for the variable inspector: its rows, where its variables come from, and the table."""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from je_editor.core.debug.debug_session import DebugLaunchRequest, DebugState, Variable
from je_editor.core.services.editor_services import EditorServices
from je_editor.pyside_ui.code.variable_inspector.inspector_gui import VariableInspector, VariableModel
from je_editor.pyside_ui.code.variable_inspector.variable_hub import VariableHub, VariableSource
from je_editor.pyside_ui.main_ui.debug_panel.debug_controller import DebugController
from je_editor.pyside_ui.main_ui.debug_panel.debug_panel_widget import DebugPanelWidget
from je_editor.utils.multi_language.multi_language_wrapper import language_wrapper
from je_editor.utils.variable_inspector.variable_rows import (
    MAX_VALUE_CHARACTERS, VariableRow, debugger_rows, describe, namespace_rows, parse_value
)
from test.test_debug_panel import FakeSession

pytestmark = pytest.mark.usefixtures("qapp")


def _word(key: str) -> str:
    return str(language_wrapper.language_word_dict.get(key))


class _Shell:
    """Stands in for an in-process IPython shell: a namespace, and what IPython put in it."""

    def __init__(self, **variables: object) -> None:
        self.user_ns_hidden = {"exit": object(), "In": [""]}
        self.user_ns = {**self.user_ns_hidden, "_": None, "__name__": "__main__", **variables}


class TestTheRows:
    def test_the_users_variables_are_listed_in_the_order_they_were_made(self):
        rows = namespace_rows({"total": 3, "name": "ada"})

        assert rows == [VariableRow("total", "int", "3"), VariableRow("name", "str", "'ada'")]

    def test_names_starting_with_an_underscore_are_left_out(self):
        assert namespace_rows({"_": 1, "__name__": "__main__", "_i1": "x = 1", "kept": 1}) == [
            VariableRow("kept", "int", "1")]

    def test_what_the_console_itself_put_there_is_left_out(self):
        shell = _Shell(answer=42)

        assert [row.name for row in namespace_rows(shell.user_ns, shell.user_ns_hidden)] == ["answer"]

    def test_a_name_of_the_consoles_the_user_bound_to_something_else_is_listed(self):
        shell = _Shell()
        shell.user_ns["exit"] = "my own"

        assert namespace_rows(shell.user_ns, shell.user_ns_hidden) == [VariableRow("exit", "str", "'my own'")]

    def test_a_key_that_is_not_a_name_is_left_out(self):
        assert namespace_rows({1: "one", "kept": 1}) == [VariableRow("kept", "int", "1")]

    def test_a_real_ipython_shell_shows_only_what_the_user_made(self):
        interactive = pytest.importorskip("IPython.core.interactiveshell")
        shell = interactive.InteractiveShell()
        shell.run_cell("answer = 6 * 7")

        assert namespace_rows(shell.user_ns, shell.user_ns_hidden) == [VariableRow("answer", "int", "42")]

    @pytest.mark.parametrize("value", ["x" * 5000, list(range(5000)), {index: index for index in range(5000)}])
    def test_a_long_value_is_cut(self, value):
        assert len(describe(value)) <= MAX_VALUE_CHARACTERS + len("...")

    def test_a_repr_that_fails_does_not_take_the_table_down(self):
        class Broken:
            def __repr__(self) -> str:
                raise RuntimeError("no repr today")

        rows = namespace_rows({"broken": Broken(), "fine": 1})

        assert rows[0].value_text.startswith("<Broken ")
        assert rows[1] == VariableRow("fine", "int", "1")

    def test_a_value_that_cannot_even_be_measured_is_said_so(self):
        # Named like a built-in container, it is asked for its length before its repr
        impostor = type("list", (), {})()

        assert describe(impostor) == "<list: repr failed (TypeError)>"

    def test_a_debuggers_variables_are_shown_as_it_reports_them(self):
        rows = debugger_rows((Variable("first", "1", "int"), Variable("text", "y" * 5000, "str")))

        assert rows[0] == VariableRow("first", "int", "1")
        assert len(rows[1].value_text) == MAX_VALUE_CHARACTERS + len("...")

    @pytest.mark.parametrize(("typed", "value"), [
        ("42", 42), ("[1, 2]", [1, 2]), ("'text'", "text"), ("None", None), ("{'a': 1}", {"a": 1}),
        ("plain words", "plain words"), ("__import__('os').getcwd()", "__import__('os').getcwd()"),
        ("1 +", "1 +"),
    ])
    def test_a_typed_value_is_a_literal_or_a_string_and_is_never_run(self, typed, value):
        assert parse_value(typed) == value


class TestWhereTheVariablesComeFrom:
    @pytest.fixture
    def hub(self):
        built = VariableHub()
        yield built
        built.deleteLater()

    def test_with_no_console_there_is_nothing_to_show(self, hub):
        assert hub.source() is VariableSource.NONE
        assert hub.namespace() is None

    def test_a_consoles_namespace_is_the_namespace_itself(self, hub, qtbot):
        shell = _Shell(answer=42)

        with qtbot.waitSignal(hub.changed):
            hub.add_console(shell)

        assert hub.source() is VariableSource.CONSOLE
        assert hub.namespace() is shell.user_ns
        assert hub.hidden() is shell.user_ns_hidden

    def test_the_console_opened_last_is_the_one_shown(self, hub):
        first, second = _Shell(), _Shell()
        hub.add_console(first)
        hub.add_console(second)

        assert hub.namespace() is second.user_ns

    def test_a_console_that_closes_gives_way_to_the_one_before(self, hub, qtbot):
        first, second = _Shell(), _Shell()
        hub.add_console(first)
        hub.add_console(second)

        with qtbot.waitSignal(hub.changed):
            hub.remove_console(second)

        assert hub.namespace() is first.user_ns

    def test_a_console_that_is_gone_without_closing_is_not_kept_alive(self, hub):
        shell = _Shell()
        hub.add_console(shell)

        del shell

        assert hub.source() is VariableSource.NONE

    def test_removing_a_console_never_registered_changes_nothing(self, hub, qtbot):
        with qtbot.assertNotEmitted(hub.changed):
            hub.remove_console(_Shell())


class TestAPausedDebugger:
    @pytest.fixture
    def fake(self):
        return FakeSession()

    @pytest.fixture
    def controller(self, fake):
        services = EditorServices()
        services.debug_adapters.register("debugpy", lambda: fake)
        built = DebugController(services)
        yield built
        built.deleteLater()
        services.shutdown()

    @pytest.fixture
    def hub(self, controller):
        built = VariableHub(controller)
        yield built
        built.deleteLater()

    def test_a_program_that_stops_shows_the_locals_of_where_it_stopped(self, hub, controller, fake):
        # No debug panel is open: the hub asks for the stack itself
        controller.launch(DebugLaunchRequest("main.py"), {})

        fake.stop_at()

        assert hub.source() is VariableSource.DEBUGGER
        assert hub.paused_frame() == "add"
        assert hub.paused_rows() == [VariableRow("first", "int", "1"), VariableRow("items", "list", "[1, 2]")]

    def test_a_paused_debugger_is_shown_rather_than_the_console(self, hub, controller, fake):
        shell = _Shell(answer=42)
        hub.add_console(shell)
        controller.launch(DebugLaunchRequest("main.py"), {})

        fake.stop_at()

        assert hub.source() is VariableSource.DEBUGGER

    def test_a_program_that_runs_on_gives_the_console_back(self, hub, controller, fake, qtbot):
        shell = _Shell(answer=42)
        hub.add_console(shell)
        controller.launch(DebugLaunchRequest("main.py"), {})
        fake.stop_at()

        with qtbot.waitSignal(hub.changed):
            controller.resume()

        assert hub.source() is VariableSource.CONSOLE
        assert hub.paused_rows() == []

    def test_a_program_that_ends_while_paused_is_shown_no_more(self, hub, controller, fake):
        controller.launch(DebugLaunchRequest("main.py"), {})
        fake.stop_at()

        fake.move_to(DebugState.TERMINATED)

        assert hub.source() is VariableSource.NONE

    def test_a_program_that_only_runs_changes_nothing(self, hub, controller, qtbot):
        with qtbot.assertNotEmitted(hub.changed):
            controller.launch(DebugLaunchRequest("main.py"), {})

    def test_the_children_of_a_variable_opened_in_the_panel_are_not_taken_for_the_locals(
            self, hub, controller, fake, qtbot):
        panel = DebugPanelWidget(controller)
        qtbot.addWidget(panel)
        controller.launch(DebugLaunchRequest("main.py"), {})
        fake.stop_at()
        local_scope = panel.variable_tree.topLevelItem(0)

        local_scope.child(1).setExpanded(True)

        assert [row.name for row in hub.paused_rows()] == ["first", "items"]

    def test_with_the_debug_panel_open_its_variables_are_listed_once(self, hub, controller, fake, qtbot):
        # Both ask for the same locals: the panel must not show them twice
        panel = DebugPanelWidget(controller)
        qtbot.addWidget(panel)
        controller.launch(DebugLaunchRequest("main.py"), {})

        fake.stop_at()

        local_scope = panel.variable_tree.topLevelItem(0)
        assert [local_scope.child(index).text(0) for index in range(local_scope.childCount())] == ["first", "items"]
        assert panel.stack_list.count() == 2

    def test_another_frame_picked_in_the_panel_is_followed(self, hub, controller, fake, qtbot):
        panel = DebugPanelWidget(controller)
        qtbot.addWidget(panel)
        controller.launch(DebugLaunchRequest("main.py"), {})
        fake.stop_at()

        panel.stack_list.setCurrentRow(1)

        assert hub.paused_frame() == "<module>"


class TestTheTable:
    @pytest.fixture
    def hub(self):
        built = VariableHub()
        yield built
        built.deleteLater()

    @pytest.fixture
    def inspector(self, hub, qtbot):
        built = VariableInspector(hub)
        qtbot.addWidget(built)
        return built

    @staticmethod
    def _names(inspector: VariableInspector) -> list[str]:
        model = inspector.proxy_model
        return [model.index(row, 0).data() for row in range(model.rowCount())]

    def test_an_inspector_given_nothing_says_how_to_get_variables(self, qtbot):
        inspector = VariableInspector()
        qtbot.addWidget(inspector)

        assert inspector.model.rowCount() == 0
        assert inspector.source_label.text() == _word("variable_inspector_source_none")

    def test_a_console_that_opens_fills_the_table(self, inspector, hub):
        shell = _Shell(answer=42, name="ada")
        hub.add_console(shell)

        assert self._names(inspector) == ["answer", "name"]
        assert inspector.source_label.text() == _word("variable_inspector_source_console")

    def test_a_variable_made_later_turns_up_on_the_next_look(self, inspector, hub):
        shell = _Shell(answer=42)
        hub.add_console(shell)

        shell.user_ns["later"] = [1, 2]
        inspector.refresh()

        assert self._names(inspector) == ["answer", "later"]

    def test_a_look_that_finds_nothing_new_leaves_the_table_alone(self, inspector, hub, qtbot):
        # A reset twice a second dropped the selection and the scroll position
        shell = _Shell(answer=42)
        hub.add_console(shell)

        with qtbot.assertNotEmitted(inspector.model.modelReset):
            inspector.refresh()

    def test_the_search_box_filters_by_name(self, inspector, hub):
        shell = _Shell(answer=42, name="ada")
        hub.add_console(shell)

        inspector.search_box.setText("NAM")

        assert self._names(inspector) == ["name"]

    def test_a_value_typed_in_is_written_to_the_console(self, inspector, hub):
        shell = _Shell(answer=42)
        hub.add_console(shell)
        value_cell = inspector.proxy_model.index(0, 2)

        assert value_cell.flags() & Qt.ItemFlag.ItemIsEditable
        assert inspector.proxy_model.setData(value_cell, "[1, 2, 3]")

        assert shell.user_ns["answer"] == [1, 2, 3]
        assert value_cell.data() == "[1, 2, 3]"
        assert inspector.proxy_model.index(0, 1).data() == "list"

    def test_a_value_left_as_it_was_is_not_written_back(self, inspector, hub):
        # The text shown may be a cut one: written back, it would replace the value
        long_text = "x" * 5000
        shell = _Shell(text=long_text)
        hub.add_console(shell)
        value_cell = inspector.proxy_model.index(0, 2)

        assert not inspector.proxy_model.setData(value_cell, value_cell.data())

        assert shell.user_ns["text"] is long_text

    def test_only_the_value_can_be_edited(self, inspector, hub):
        shell = _Shell(answer=42)
        hub.add_console(shell)

        assert not inspector.proxy_model.index(0, 0).flags() & Qt.ItemFlag.ItemIsEditable
        assert not inspector.proxy_model.setData(inspector.proxy_model.index(0, 0), "renamed")
        assert "renamed" not in shell.user_ns

    def test_rows_given_from_elsewhere_are_read_only(self, qtbot):
        model = VariableModel()
        model.show_rows([VariableRow("first", "int", "1")])
        value_cell = model.index(0, 2)

        assert not value_cell.flags() & Qt.ItemFlag.ItemIsEditable
        assert not model.setData(value_cell, "2")
        assert model.variables == [VariableRow("first", "int", "1")]

    def test_a_namespace_set_the_old_way_is_still_shown(self):
        model = VariableModel()

        model.namespace = {"answer": 42}

        assert model.namespace == {"answer": 42}
        assert model.rowCount() == 1

    def test_it_looks_again_only_while_it_can_be_seen(self, inspector, qtbot):
        assert not inspector.timer.isActive()

        inspector.show()
        qtbot.waitExposed(inspector)
        assert inspector.timer.isActive()

        inspector.hide()
        assert not inspector.timer.isActive()

    def test_another_hub_replaces_the_first(self, inspector, hub):
        shells = [_Shell(answer=42), _Shell(elsewhere=1), _Shell(ignored=1)]
        hub.add_console(shells[0])
        other = VariableHub()
        other.add_console(shells[1])

        inspector.set_hub(other)
        hub.add_console(shells[2])

        assert self._names(inspector) == ["elsewhere"]
        other.deleteLater()


class TestTheConsoleRegistersItself:
    def test_an_ipython_console_gives_the_window_its_shell_and_takes_it_back_on_closing(self, qtbot, monkeypatch):
        console = pytest.importorskip("je_editor.pyside_ui.main_ui.ipython_widget.ipython_console")

        class Manager:
            def __init__(self) -> None:
                self.kernel = type("Kernel", (), {"shell": _Shell(answer=42)})()

            def start_kernel(self) -> None:
                """Nothing to start."""

            def client(self):
                return type("Client", (), {"start_channels": lambda self: None, "stop_channels": lambda self: None})()

            def restart_kernel(self) -> None:
                """Nothing to restart."""

            def shutdown_kernel(self) -> None:
                """Nothing to shut down."""

        monkeypatch.setattr(console, "QtInProcessKernelManager", Manager)
        monkeypatch.setattr(console, "RichJupyterWidget", QWidget)
        monkeypatch.setattr(console.guisupport, "start_event_loop_qt4", lambda _app: None)
        window = QWidget()
        qtbot.addWidget(window)
        window.variable_hub = VariableHub(parent=window)

        widget = console.IpythonWidget(window)
        qtbot.addWidget(widget)

        assert window.variable_hub.namespace() is widget.kernel.shell.user_ns

        widget.close()

        assert window.variable_hub.source() is VariableSource.NONE


class TestWithTheRealDebugger:
    def test_a_program_stopped_at_a_breakpoint_fills_the_inspector(self, qtbot, tmp_path):
        from je_editor.adapters.debug.debugpy_adapter import debugpy_available
        from je_editor.adapters.default_services import build_default_services
        from je_editor.core.debug.debug_session import Breakpoint
        from je_editor.core.uri.resource_uri import to_uri
        from je_editor.core.workspace.workspace_model import Workspace

        if not debugpy_available():
            pytest.skip("debugpy is not installed")
        program = tmp_path / "program.py"
        program.write_text(
            "def add(first, second):\n    total = first + second\n    return total\n\n\nprint(add(2, 40))\n",
            encoding="utf-8")
        services = build_default_services(Workspace.single_root(str(tmp_path)))
        controller = DebugController(services)
        hub = VariableHub(controller)
        inspector = VariableInspector(hub)
        qtbot.addWidget(inspector)
        uri = to_uri(program)
        try:
            assert controller.launch(
                DebugLaunchRequest(str(program), working_directory=str(tmp_path)), {uri: [Breakpoint(uri, 3)]})

            qtbot.waitUntil(lambda: len(hub.paused_rows()) >= 3, timeout=60_000)

            shown = {row.name: (row.type_name, row.value_text) for row in inspector.model.variables}
            assert shown["first"] == ("int", "2")
            assert shown["second"] == ("int", "40")
            assert shown["total"] == ("int", "42")
            assert hub.paused_frame() == "add"
            assert not inspector.model.editable()

            controller.resume()
            qtbot.waitUntil(lambda: hub.source() is VariableSource.NONE, timeout=60_000)
            assert inspector.model.rowCount() == 0
        finally:
            controller.stop()
            qtbot.waitUntil(lambda: not controller.is_active(), timeout=60_000)
            hub.deleteLater()
            controller.deleteLater()
            services.shutdown()


def test_a_repr_that_changes_the_namespace_does_not_break_the_listing():
    namespace: dict = {}

    class Meddling:
        def __repr__(self) -> str:
            namespace["added_while_listing"] = 1
            return "meddling"

    namespace["meddler"] = Meddling()

    assert namespace_rows(namespace) == [VariableRow("meddler", "Meddling", "meddling")]
