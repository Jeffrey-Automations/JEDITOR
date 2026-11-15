"""Tests for the window's shell: its areas, its views, its layout and the theme applied to it."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QAction
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QTabWidget

from je_editor.pyside_ui.main_ui.save_settings.user_setting_file import user_setting_dict
from je_editor.pyside_ui.main_ui.shell.shell_icons import (
    ICON_PROPERTY, refresh_action_icons, set_action_icon, themed_icon
)
from je_editor.pyside_ui.main_ui.shell.ui_style import apply_ui_style, write_theme_images
from je_editor.pyside_ui.main_ui.shell.view_container import LazyPage, ViewContainer
from je_editor.pyside_ui.main_ui.shell.workbench import Workbench, reveal_view, workbench_of
from je_editor.utils.shell.layout_state import LAYOUT_SETTING_KEY, ShellLayout
from je_editor.utils.shell.shell_views import (
    AREA_BOTTOM, AREA_SECONDARY, AREA_SIDE, VIEW_AI_CHAT, VIEW_DEBUG, VIEW_DEBUG_CONSOLE,
    VIEW_EXPLORER, VIEW_OUTPUT, VIEW_TERMINAL, ViewSpec
)
from je_editor.utils.theme.ui_icons import icon_names, icon_svg
from je_editor.utils.theme.ui_stylesheet import IMAGE_NAMES
from je_editor.utils.theme.ui_theme import DARK_TOKENS, LIGHT_TOKENS, STYLE_DARK, STYLE_LIGHT


class _Window(QMainWindow):
    """A main window with what the shell asks of one, and nothing else."""

    def __init__(self) -> None:
        super().__init__()
        self.go_to_new_tab = MagicMock()


@pytest.fixture()
def window(qapp, qtbot, tmp_dir):
    host = _Window()
    qtbot.addWidget(host)
    host.tab_widget = QTabWidget()
    host.workbench = Workbench(host, host.tab_widget)
    yield host
    host.workbench.close_views()


@pytest.fixture()
def workbench(window) -> Workbench:
    return window.workbench


@pytest.fixture()
def _layout_setting_untouched():
    saved = user_setting_dict.get(LAYOUT_SETTING_KEY)
    yield
    user_setting_dict[LAYOUT_SETTING_KEY] = saved if saved is not None else {}


@pytest.fixture()
def _style_untouched(qapp):
    """Put the application's style sheet, the configured style and the editor colours back."""
    from je_editor.pyside_ui.main_ui.save_settings.user_color_setting_file import (
        update_actually_color_dict, user_setting_color_dict
    )
    sheet, palette, style = qapp.styleSheet(), qapp.palette(), user_setting_dict.get("ui_style")
    colours = {key: list(value) for key, value in user_setting_color_dict.items()}
    yield
    qapp.setStyleSheet(sheet)
    qapp.setPalette(palette)
    user_setting_dict["ui_style"] = style
    user_setting_color_dict.clear()
    user_setting_color_dict.update(colours)
    update_actually_color_dict()


class TestTheAreas:
    def test_the_editor_tabs_sit_in_the_middle(self, window, workbench):
        assert window.centralWidget() is workbench.main_splitter
        assert workbench.center_splitter.indexOf(window.tab_widget) == 0

    def test_every_area_has_its_built_in_views(self, workbench):
        assert VIEW_EXPLORER in workbench.view_ids(AREA_SIDE)
        assert VIEW_OUTPUT in workbench.view_ids(AREA_BOTTOM)
        assert workbench.view_ids(AREA_SECONDARY) == (VIEW_AI_CHAT,)

    def test_a_window_without_a_debug_controller_gets_no_debug_view(self, workbench):
        assert workbench.view_spec(VIEW_DEBUG) is None

    def test_it_starts_on_the_explorer_with_the_secondary_side_bar_closed(self, workbench):
        assert workbench.is_view_shown(VIEW_EXPLORER)
        assert workbench.secondary_side_bar.isHidden()
        assert not workbench.bottom_panel.isHidden()

    def test_the_output_views_are_pages_of_the_bottom_panel(self, workbench):
        # The editor tabs switch the bottom panel to these widgets directly.
        for widget in (workbench.output.code_result_scroll_area,
                       workbench.output.debugger_result, workbench.output.console_widget):
            assert workbench.bottom_panel.indexOf(widget) >= 0


class TestShowingViews:
    def test_a_view_is_built_only_when_it_is_shown(self, workbench):
        assert workbench.widget_of("todo") is None
        shown = workbench.show_view("todo")
        assert shown is not None and workbench.widget_of("todo") is shown

    def test_showing_a_view_opens_its_area(self, workbench):
        workbench.set_side_bar_visible(False)
        workbench.show_view(VIEW_EXPLORER)
        assert not workbench.side_bar.isHidden()

    def test_showing_a_bottom_view_selects_its_tab(self, workbench):
        workbench.set_bottom_panel_visible(False)
        workbench.show_view(VIEW_TERMINAL)
        assert workbench.is_view_shown(VIEW_TERMINAL)
        assert workbench.bottom_panel.currentWidget() is workbench.output.console_widget

    def test_clicking_the_current_views_icon_closes_the_side_bar(self, workbench):
        workbench.activity_bar.action_of(VIEW_EXPLORER).trigger()
        assert workbench.side_bar.isHidden()
        workbench.activity_bar.action_of(VIEW_EXPLORER).trigger()
        assert workbench.is_view_shown(VIEW_EXPLORER)

    def test_clicking_another_views_icon_switches_to_it(self, workbench):
        workbench.activity_bar.action_of("outline").trigger()
        assert workbench.side_bar.current_view() == "outline"
        assert not workbench.side_bar.isHidden()

    def test_the_activity_bar_marks_only_the_view_shown(self, workbench):
        workbench.show_view("outline")
        assert workbench.activity_bar.action_of("outline").isChecked()
        assert not workbench.activity_bar.action_of(VIEW_EXPLORER).isChecked()

    def test_the_secondary_side_bar_toggles(self, workbench):
        workbench.toggle_secondary_side_bar()
        assert workbench.is_view_shown(VIEW_AI_CHAT)
        workbench.toggle_secondary_side_bar()
        assert workbench.secondary_side_bar.isHidden()

    def test_the_panels_corner_button_hides_it(self, workbench):
        workbench.bottom_panel.cornerWidget().defaultAction().trigger()
        assert workbench.bottom_panel.isHidden()

    def test_an_unknown_view_is_not_shown(self, workbench):
        assert workbench.show_view("no_such_view") is None
        assert workbench.is_view_shown("no_such_view") is False


class TestReachingTheShellFromElsewhere:
    def test_a_window_with_a_shell_reveals_a_view(self, window, workbench):
        workbench.set_bottom_panel_visible(False)
        assert reveal_view(window, VIEW_DEBUG_CONSOLE) is True
        assert workbench.is_view_shown(VIEW_DEBUG_CONSOLE)

    def test_a_window_without_a_shell_is_left_alone(self):
        assert reveal_view(MagicMock(), VIEW_OUTPUT) is False
        assert workbench_of(MagicMock()) is None

    def test_an_unknown_view_reports_failure(self, window):
        assert reveal_view(window, "no_such_view") is False


class TestAddingAView:
    def test_a_host_can_add_a_side_view(self, workbench):
        built = []
        spec = ViewSpec("navigation", AREA_SIDE, icon="outline", title="Navigation")
        workbench.register_view(spec, lambda: built.append(QLabel("nav")) or built[-1])
        assert built == []
        assert workbench.show_view("navigation") is built[0]
        assert workbench.side_bar.header.text() == "NAVIGATION"
        assert workbench.activity_bar.action_of("navigation").isChecked()

    def test_a_host_can_add_a_bottom_view_already_built(self, workbench):
        page = QLabel("report")
        workbench.register_view(ViewSpec("report", AREA_BOTTOM, title="Report"), widget=page)
        workbench.show_view("report")
        assert workbench.bottom_panel.currentWidget() is page
        assert workbench.bottom_panel.tabText(workbench.bottom_panel.currentIndex()) == "Report"

    def test_a_host_can_add_a_view_from_plain_arguments(self, workbench):
        page = QLabel("nav")
        workbench.add_view("navigation", "side", widget=page, icon="navigation",
                           title_key="view_explorer")
        assert workbench.show_view("navigation") is page
        assert workbench.view_spec("navigation").area == AREA_SIDE

    def test_an_unknown_area_is_refused(self, workbench):
        with pytest.raises(ValueError):
            workbench.add_view("floating", "elsewhere", widget=QLabel())

    def test_an_id_cannot_be_registered_twice(self, workbench):
        with pytest.raises(ValueError):
            workbench.register_view(ViewSpec(VIEW_EXPLORER, AREA_SIDE), lambda: QLabel())

    def test_a_view_needs_something_to_show(self, workbench):
        with pytest.raises(ValueError):
            workbench.register_view(ViewSpec("empty", AREA_SIDE))

    def test_a_view_that_fails_to_build_leaves_the_window_standing(self, workbench):
        def broken():
            raise RuntimeError("no such package")

        workbench.register_view(ViewSpec("broken", AREA_SIDE, title="Broken"), broken)
        assert workbench.show_view("broken") is None
        assert workbench.side_bar.current_view() == "broken"


class TestTheLayout:
    def test_the_layout_describes_what_is_open(self, workbench):
        workbench.show_view("outline")
        workbench.show_view(VIEW_TERMINAL)
        workbench.set_secondary_side_bar_visible(True)
        layout = workbench.layout()
        assert (layout.side_view, layout.bottom_view) == ("outline", VIEW_TERMINAL)
        assert layout.secondary_visible is True

    def test_a_layout_can_be_applied(self, workbench):
        workbench.apply_layout(ShellLayout(
            side_bar_visible=False, bottom_panel_visible=False, bottom_view=VIEW_TERMINAL))
        assert workbench.side_bar.isHidden() and workbench.bottom_panel.isHidden()
        assert workbench.bottom_panel.currentWidget() is workbench.output.console_widget

    def test_a_hidden_secondary_side_bar_builds_nothing(self, workbench):
        workbench.apply_layout(ShellLayout(secondary_visible=False))
        assert workbench.widget_of(VIEW_AI_CHAT) is None

    def test_a_layout_naming_a_missing_view_falls_back(self, workbench):
        workbench.apply_layout(ShellLayout(side_view="from_a_plugin"))
        assert workbench.side_bar.current_view() == VIEW_EXPLORER

    @pytest.mark.usefixtures("_layout_setting_untouched")
    def test_the_layout_is_saved_and_restored(self, workbench):
        workbench.show_view("outline")
        workbench.set_bottom_panel_visible(False)
        workbench.save_layout()
        assert user_setting_dict[LAYOUT_SETTING_KEY]["side_view"] == "outline"
        workbench.apply_layout(ShellLayout())
        workbench.restore_layout()
        assert workbench.side_bar.current_view() == "outline"
        assert workbench.bottom_panel.isHidden()

    @pytest.mark.usefixtures("_layout_setting_untouched")
    def test_a_first_start_has_no_saved_layout(self, workbench):
        user_setting_dict[LAYOUT_SETTING_KEY] = {}
        assert workbench.has_saved_layout() is False
        workbench.save_layout()
        assert workbench.has_saved_layout() is True

    @pytest.mark.usefixtures("_layout_setting_untouched")
    def test_a_view_added_after_the_first_restore_is_restored_by_a_second(self, workbench):
        user_setting_dict[LAYOUT_SETTING_KEY] = {"side_view": "navigation"}
        workbench.restore_layout()
        assert workbench.side_bar.current_view() == VIEW_EXPLORER
        workbench.add_view("navigation", "side", widget=QLabel("nav"), title="Navigation")
        workbench.restore_layout()
        assert workbench.is_view_shown("navigation")

    @pytest.mark.usefixtures("_layout_setting_untouched")
    def test_a_corrupt_setting_restores_the_default_layout(self, workbench):
        user_setting_dict[LAYOUT_SETTING_KEY] = "not a layout"
        workbench.restore_layout()
        assert workbench.is_view_shown(VIEW_EXPLORER)

    def test_a_hidden_area_keeps_its_width(self, window, workbench, qtbot):
        window.resize(1400, 800)
        window.show()
        qtbot.waitExposed(window)
        workbench.apply_layout(ShellLayout(side_bar_width=300))
        workbench.set_side_bar_visible(False)
        workbench.set_side_bar_visible(True)
        assert workbench.layout().side_bar_width == 300
        assert abs(workbench.main_splitter.sizes()[0] - 300) <= 2


class TestOpeningFromTheExplorer:
    def test_a_file_opens_in_a_new_tab(self, window, workbench, tmp_dir):
        target = tmp_dir / "main.py"
        target.write_text("x = 1\n", encoding="utf-8")
        workbench.open_file(target)
        window.go_to_new_tab.assert_called_once_with(target)

    def test_clicking_a_folder_opens_nothing(self, window, workbench, tmp_dir):
        with patch.object(workbench.explorer, "selected_path", return_value=Path(tmp_dir)):
            workbench.explorer.tree.clicked.emit(workbench.explorer.tree.rootIndex())
        window.go_to_new_tab.assert_not_called()

    def test_clicking_a_file_opens_it(self, window, workbench, tmp_dir):
        target = tmp_dir / "main.py"
        target.write_text("x = 1\n", encoding="utf-8")
        with patch.object(workbench.explorer, "selected_path", return_value=target):
            workbench.explorer.tree.clicked.emit(workbench.explorer.tree.rootIndex())
        window.go_to_new_tab.assert_called_once_with(target)

    def test_the_tree_shows_names_only(self, workbench):
        tree = workbench.explorer.tree
        assert tree.isHeaderHidden()
        assert all(tree.isColumnHidden(column)
                   for column in range(1, workbench.explorer.model.columnCount()))


@pytest.fixture()
def editor_tab(window):
    """A real editor tab in the window that has the shell."""
    window.python_compiler = None
    with patch(
        "je_editor.pyside_ui.code.plaintext_code_edit.code_edit_plaintext.venv_check"
    ) as venv:
        venv.return_value = MagicMock(exists=MagicMock(return_value=False))
        from je_editor.pyside_ui.main_ui.editor.editor_widget import EditorWidget
        tab = EditorWidget(window)
        window.tab_widget.addTab(tab, "Editor")
        window.tab_widget.setCurrentWidget(tab)
    yield tab
    tab.close()


class TestAnEditorTabInTheShell:
    def test_it_uses_the_windows_tree_and_output(self, editor_tab, workbench):
        assert editor_tab.project_treeview is workbench.explorer.tree
        assert editor_tab.code_result is workbench.output.code_result
        assert editor_tab.git_gui is workbench.output.git_gui
        assert editor_tab.code_difference_result is workbench.bottom_panel

    def test_it_holds_no_tree_or_output_of_its_own(self, editor_tab, workbench):
        assert not editor_tab.isAncestorOf(workbench.explorer)
        assert not editor_tab.isAncestorOf(workbench.output.code_result)

    def test_switching_to_the_debugger_output_works_as_before(self, editor_tab, workbench):
        editor_tab.code_difference_result.setCurrentWidget(editor_tab.debugger_result)
        assert workbench.is_view_shown(VIEW_DEBUG_CONSOLE)

    def test_closing_the_tab_leaves_the_shared_terminal_running(self, editor_tab, workbench):
        with patch.object(workbench.output.console_widget, "close") as closed:
            editor_tab.close()
        closed.assert_not_called()

    def test_a_blank_tab_takes_the_file_opened_from_the_explorer(
            self, window, workbench, editor_tab, tmp_dir):
        target = tmp_dir / "main.py"
        target.write_text("x = 1\n", encoding="utf-8")
        workbench.open_file(target)
        window.go_to_new_tab.assert_not_called()
        assert Path(editor_tab.current_file) == target

    def test_the_tab_is_titled_with_the_file_name(self, window, editor_tab, tmp_dir):
        target = tmp_dir / "main.py"
        target.write_text("x = 1\n", encoding="utf-8")
        editor_tab.open_an_file(target)
        index = window.tab_widget.indexOf(editor_tab)
        assert window.tab_widget.tabText(index) == "main.py"
        assert window.tab_widget.tabToolTip(index) == str(target)
        assert editor_tab.objectName() == str(target)


class TestViewContainers:
    def test_a_lazy_page_builds_once(self, qapp):
        calls = []
        page = LazyPage(lambda: calls.append(1) or QLabel("content"))
        first = page.ensure_built()
        assert page.ensure_built() is first and calls == [1]

    def test_the_header_follows_the_view(self, qapp):
        container = ViewContainer("Any")
        container.add_view("one", "First", QLabel)
        container.add_view("two", "Second", QLabel)
        container.show_view("two")
        assert (container.current_view(), container.header.text()) == ("two", "SECOND")
        container.set_title("two", "Zweite")
        assert container.header.text() == "ZWEITE"

    def test_only_shown_views_are_built(self, qapp):
        container = ViewContainer("Any")
        container.add_view("one", "First", QLabel)
        container.add_view("two", "Second", QLabel)
        container.show_view("one")
        assert container.content_of("two") is None
        assert len(container.built_content()) == 1


class TestThemedIcons:
    @pytest.mark.parametrize("name", icon_names())
    def test_every_icon_renders(self, qapp, name):
        assert QSvgRenderer(QByteArray(icon_svg(name, "#ffffff").encode("utf-8"))).isValid()
        assert not themed_icon(name, DARK_TOKENS).isNull()

    def test_a_theme_change_redraws_the_actions_that_carry_an_icon(self, qapp, window):
        with_icon = set_action_icon(QAction("Run", window), "run", DARK_TOKENS)
        QAction("Plain", window)
        before = with_icon.icon().cacheKey()
        assert with_icon.property(ICON_PROPERTY) == "run"
        redrawn = refresh_action_icons(window, LIGHT_TOKENS)
        # The activity bar's and the panel's own actions are redrawn with it.
        assert redrawn >= 1
        assert with_icon.icon().cacheKey() != before


@pytest.mark.usefixtures("_style_untouched")
class TestApplyingAStyle:
    def test_a_built_in_theme_sets_the_style_sheet_and_palette(self, qapp, window):
        assert apply_ui_style(window, STYLE_DARK) is True
        assert DARK_TOKENS["editor_background"] in qapp.styleSheet()
        assert qapp.palette().window().color().name() == DARK_TOKENS["surface"]

    def test_the_base_style_is_set_only_once(self, qapp, window):
        # setStyle re-polishes every widget on the GUI thread: over a second in a full window.
        apply_ui_style(window, STYLE_DARK)
        with patch.object(QApplication, "setStyle") as set_style:
            apply_ui_style(window, STYLE_LIGHT)
            apply_ui_style(window, STYLE_DARK)
        set_style.assert_not_called()

    def test_an_icon_is_drawn_once_for_a_set_of_colours(self, qapp):
        first = themed_icon("run", DARK_TOKENS)
        assert themed_icon("run", DARK_TOKENS).cacheKey() == first.cacheKey()
        assert themed_icon("run", LIGHT_TOKENS).cacheKey() != first.cacheKey()

    def test_a_styles_images_are_written_once(self, qapp):
        urls = write_theme_images(DARK_TOKENS, STYLE_DARK)
        with patch("pathlib.Path.write_text") as written:
            assert write_theme_images(DARK_TOKENS, STYLE_DARK) == urls
        written.assert_not_called()

    def test_the_light_theme_replaces_the_dark_one(self, qapp, window):
        apply_ui_style(window, STYLE_DARK)
        apply_ui_style(window, STYLE_LIGHT)
        assert LIGHT_TOKENS["editor_background"] in qapp.styleSheet()
        assert DARK_TOKENS["editor_background"] not in qapp.styleSheet()

    def test_no_style_name_means_the_default_theme(self, qapp):
        assert apply_ui_style(None, None) is True
        assert DARK_TOKENS["editor_background"] in qapp.styleSheet()

    def test_a_material_style_goes_through_qt_material(self, qapp):
        with patch("qt_material.apply_stylesheet") as material:
            apply_ui_style(None, "dark_teal.xml")
        material.assert_called_once_with(QApplication.instance(), theme="dark_teal.xml")

    def test_a_window_with_style_tools_applies_the_material_style_itself(self, qapp, window):
        window.apply_stylesheet = MagicMock()
        apply_ui_style(window, "light_blue.xml")
        window.apply_stylesheet.assert_called_once_with(QApplication.instance(), "light_blue.xml")

    def test_the_images_the_style_sheet_names_exist(self, qapp):
        urls = write_theme_images(DARK_TOKENS, STYLE_DARK)
        assert set(urls) == set(IMAGE_NAMES)
        for url in urls.values():
            assert Path(url).is_file() and "\\" not in url


class TestTheViewMenu:
    @pytest.fixture()
    def view_menu(self, window):
        from PySide6.QtWidgets import QMenuBar

        from je_editor.pyside_ui.main_ui.menu.view_menu.build_view_menu import set_view_menu
        window.menu = QMenuBar()
        set_view_menu(window)
        yield window.view_menu
        window.menu.deleteLater()

    def _action(self, menu, key):
        from je_editor.utils.multi_language.multi_language_wrapper import language_wrapper
        wanted = language_wrapper.language_word_dict.get(key)
        return next(action for action in menu.actions() if action.text() == wanted)

    def test_the_toggles_drive_the_shell(self, view_menu, workbench):
        self._action(view_menu, "view_menu_toggle_side_bar").trigger()
        self._action(view_menu, "view_menu_toggle_bottom_panel").trigger()
        self._action(view_menu, "view_menu_toggle_secondary_side_bar").trigger()
        assert workbench.side_bar.isHidden() and workbench.bottom_panel.isHidden()
        assert not workbench.secondary_side_bar.isHidden()

    def test_every_registered_built_in_view_can_be_shown_from_the_menu(self, view_menu, workbench):
        self._action(view_menu, "view_terminal").trigger()
        assert workbench.is_view_shown(VIEW_TERMINAL)
        texts = [action.text() for action in view_menu.actions()]
        assert len(texts) == len(set(texts))

    def test_a_view_added_later_gets_an_entry(self, view_menu, workbench):
        workbench.add_view("report", "bottom", widget=QLabel("report"), title="Report")
        entry = next(action for action in view_menu.actions() if action.text() == "Report")
        workbench.set_bottom_panel_visible(False)
        entry.trigger()
        assert workbench.is_view_shown("report")

    def test_its_shortcuts_are_reserved_for_the_window(self, view_menu):
        from je_editor.utils.shortcuts.shortcut_registry import (
            WINDOW_SHORTCUTS, normalise_sequence
        )
        reserved = {normalise_sequence(sequence) for sequence in WINDOW_SHORTCUTS.values()}
        bound = [normalise_sequence(action.shortcut().toString())
                 for action in view_menu.actions() if action.shortcut().toString()]
        assert bound and set(bound) <= reserved

    def test_a_window_without_a_shell_gets_no_view_menu(self, qapp, qtbot):
        from PySide6.QtWidgets import QMenuBar

        from je_editor.pyside_ui.main_ui.menu.view_menu.build_view_menu import set_view_menu
        bare = QMainWindow()
        qtbot.addWidget(bare)
        bare.menu = QMenuBar()
        set_view_menu(bare)
        assert bare.menu.actions() == []


@pytest.mark.usefixtures("_style_untouched")
class TestChoosingAStyleFromTheMenu:
    def test_the_style_named_in_the_actions_data_is_stored_and_applied(self, qapp, window):
        from je_editor.pyside_ui.main_ui.menu.style_menu.build_style_menu import set_style
        action = QAction("JEditor Light", window)
        action.setData(STYLE_LIGHT)
        set_style(window, action)
        assert user_setting_dict["ui_style"] == STYLE_LIGHT
        assert LIGHT_TOKENS["editor_background"] in qapp.styleSheet()


SAVE_DIALOG = "je_editor.pyside_ui.dialog.file_dialog.save_file_dialog"
OPEN_DIALOG = "je_editor.pyside_ui.dialog.file_dialog.open_file_dialog"


class TestSavingTheTabInFront:
    """Save File, Run and Debug used to open the Save As dialog every time."""

    def test_a_tab_with_a_file_is_written_where_it_is(self, window, editor_tab, tmp_dir):
        from je_editor.pyside_ui.dialog.file_dialog.save_file_dialog import save_current_file
        target = tmp_dir / "main.py"
        target.write_text("x = 1\n", encoding="utf-8")
        editor_tab.open_an_file(target)
        editor_tab.code_edit.setPlainText("x = 2\n")
        with patch(f"{SAVE_DIALOG}.QFileDialog") as dialog:
            assert save_current_file(window) is True
        dialog.assert_not_called()
        assert target.read_text(encoding="utf-8") == "x = 2\n"
        assert editor_tab._is_modified is False

    def test_a_tab_without_a_file_is_asked_where(self, window, editor_tab, tmp_dir):
        from je_editor.pyside_ui.dialog.file_dialog.save_file_dialog import save_current_file
        target = tmp_dir / "new.py"
        editor_tab.code_edit.setPlainText("y = 1\n")
        with patch(f"{SAVE_DIALOG}.QFileDialog") as dialog:
            dialog.return_value.getSaveFileName.return_value = (str(target), "")
            assert save_current_file(window) is True
        assert target.read_text(encoding="utf-8") == "y = 1\n"
        assert Path(editor_tab.current_file) == target

    def test_cancelling_the_question_saves_nothing(self, window, editor_tab):
        from je_editor.pyside_ui.dialog.file_dialog.save_file_dialog import save_current_file
        with patch(f"{SAVE_DIALOG}.QFileDialog") as dialog:
            dialog.return_value.getSaveFileName.return_value = ("", "")
            assert save_current_file(window) is False

    def test_a_tab_that_is_no_editor_is_not_saved(self, window):
        from je_editor.pyside_ui.dialog.file_dialog.save_file_dialog import save_current_file
        window.tab_widget.addTab(QLabel("browser"), "Browser")
        assert save_current_file(window) is False


class TestOpeningAFileFromTheMenu:
    """File > Open File used to replace the text of the tab in front without asking."""

    def test_it_opens_in_its_own_tab_and_leaves_the_tab_in_front_alone(
            self, window, editor_tab, tmp_dir):
        from je_editor.pyside_ui.dialog.file_dialog.open_file_dialog import _open_in_a_tab
        editor_tab.code_edit.setPlainText("unsaved work")
        target = tmp_dir / "other.py"
        target.write_text("z = 1\n", encoding="utf-8")
        with patch(f"{OPEN_DIALOG}._prompt_for_file", return_value=str(target)):
            _open_in_a_tab(window)
        window.go_to_new_tab.assert_called_once_with(target)
        assert editor_tab.code_edit.toPlainText() == "unsaved work"

    def test_a_blank_tab_takes_the_file(self, window, editor_tab, tmp_dir):
        from je_editor.pyside_ui.dialog.file_dialog.open_file_dialog import _open_in_a_tab
        target = tmp_dir / "other.py"
        target.write_text("z = 1\n", encoding="utf-8")
        with patch(f"{OPEN_DIALOG}._prompt_for_file", return_value=str(target)):
            opened = _open_in_a_tab(window)
        assert opened is editor_tab
        assert editor_tab.code_edit.toPlainText() == "z = 1\n"

    def test_cancelling_opens_nothing(self, window, editor_tab):
        from je_editor.pyside_ui.dialog.file_dialog.open_file_dialog import _open_in_a_tab
        with patch(f"{OPEN_DIALOG}._prompt_for_file", return_value=""):
            assert _open_in_a_tab(window) is None
        window.go_to_new_tab.assert_not_called()


class TestTheEditorsOwnWrite:
    """
    One write raises the file watcher twice on Windows, and the second used to
    ask whether to reload a file "modified externally" after an auto-save.
    """

    def _opened(self, editor_tab, tmp_dir):
        target = tmp_dir / "main.py"
        target.write_text("x = 1\n", encoding="utf-8")
        editor_tab.open_an_file(target)
        return target

    def test_a_file_holding_the_editors_text_asks_nothing(self, editor_tab, tmp_dir):
        target = self._opened(editor_tab, tmp_dir)
        with patch("je_editor.pyside_ui.main_ui.editor.editor_widget.QMessageBox.question") as asked:
            editor_tab._on_file_changed_externally(str(target))
            editor_tab._on_file_changed_externally(str(target))
        asked.assert_not_called()

    def test_another_programs_change_is_still_asked_about(self, editor_tab, tmp_dir):
        from PySide6.QtWidgets import QMessageBox
        target = self._opened(editor_tab, tmp_dir)
        # The handler is called by hand below; the real watcher would call it
        # again later, outside the patch, and open the real question.
        editor_tab._file_watcher.blockSignals(True)
        target.write_text("x = 99\n", encoding="utf-8")
        with patch("je_editor.pyside_ui.main_ui.editor.editor_widget.QMessageBox.question",
                   return_value=QMessageBox.StandardButton.No) as asked:
            editor_tab._on_file_changed_externally(str(target))
        asked.assert_called_once()
        assert editor_tab.code_edit.toPlainText() == "x = 1\n"


@pytest.mark.usefixtures("_style_untouched")
class TestASavedStyleThatIsNoName:
    @pytest.mark.parametrize("saved", [42, ["dark"], "", "   ", None])
    def test_it_falls_back_to_the_default_theme(self, qapp, saved):
        # A number in the settings file used to raise TypeError out of the window's constructor.
        assert apply_ui_style(None, saved) is True
        assert DARK_TOKENS["editor_background"] in qapp.styleSheet()
