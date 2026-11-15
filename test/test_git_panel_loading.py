"""Tests that the git panel reads a repository on a background thread, not the GUI thread."""
from __future__ import annotations

import threading
from unittest.mock import patch

import pytest

git = pytest.importorskip("git")

MODULE = "je_editor.pyside_ui.git_ui.git_client.git_client_gui"
# Long enough that a slow machine still finishes; a hang fails rather than blocks.
TIMEOUT_MS = 15_000


@pytest.fixture()
def repo(tmp_path):
    """A repository with one commit, one modified file and one untracked file."""
    repository = git.Repo.init(tmp_path, initial_branch="main")
    with repository.config_writer() as config:
        config.set_value("user", "name", "Panel Tester")
        config.set_value("user", "email", "panel@example.com")
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("first\n", encoding="utf-8")
    repository.index.add(["tracked.txt"])
    repository.index.commit("initial")
    repository.close()
    tracked.write_text("first\nsecond\n", encoding="utf-8")
    (tmp_path / "new.txt").write_text("new\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def panel(qapp, qtbot):
    """The git panel with no repository open."""
    from je_editor.pyside_ui.git_ui.git_client.git_client_gui import GitGui
    with patch.object(GitGui, "_restore_last_opened_repository", lambda self: None):
        widget = GitGui()
    qtbot.addWidget(widget)
    yield widget
    widget.close()


def _rows(widget) -> list[str]:
    return [widget.changes_list_widget.item(row).text()
            for row in range(widget.changes_list_widget.count())]


def _loaded(widget, qtbot, path) -> None:
    widget._load_repository_from_path(path)
    qtbot.waitUntil(lambda: widget.current_repo is not None, timeout=TIMEOUT_MS)


class TestOpeningARepository:
    def test_the_call_returns_before_the_repository_is_read(self, panel, repo):
        panel._load_repository_from_path(repo)
        # Still loading: nothing is open yet and the controls wait for it.
        assert panel.current_repo is None
        assert panel.commit_button.isEnabled() is False

    def test_the_repository_is_read_off_the_gui_thread(self, panel, qtbot, repo):
        from je_editor.pyside_ui.git_ui.git_client import git_client_gui
        seen = []
        real = git_client_gui.read_repository_state

        def recording(repository):
            seen.append(threading.current_thread() is threading.main_thread())
            return real(repository)

        with patch(f"{MODULE}.read_repository_state", recording):
            _loaded(panel, qtbot, repo)
        assert seen == [False]

    def test_what_was_read_is_shown(self, panel, qtbot, repo):
        _loaded(panel, qtbot, repo)
        assert panel.branch_selector.currentText() == "main"
        assert "[untracked] new.txt" in _rows(panel)
        assert "[modified] tracked.txt" in _rows(panel)
        assert "Untracked: 1 | Unstaged: 1 | Staged: 0" in panel.repo_status_label.text()
        assert panel.commit_button.isEnabled() is True

    def test_a_folder_that_is_no_repository_is_reported(self, panel, qtbot, tmp_path):
        with patch(f"{MODULE}.QMessageBox.critical") as reported:
            panel._load_repository_from_path(tmp_path)
            qtbot.waitUntil(lambda: reported.called, timeout=TIMEOUT_MS)
        assert panel.current_repo is None
        assert panel.repo_path_label.text() == "Repository: (none)"
        assert panel.commit_button.isEnabled() is False

    def test_a_repository_opened_meanwhile_wins(self, panel, qtbot, repo, tmp_path_factory):
        other = tmp_path_factory.mktemp("other")
        repository = git.Repo.init(other, initial_branch="trunk")
        with repository.config_writer() as config:
            config.set_value("user", "name", "Panel Tester")
            config.set_value("user", "email", "panel@example.com")
        (other / "only.txt").write_text("x\n", encoding="utf-8")
        repository.index.add(["only.txt"])
        repository.index.commit("initial")
        repository.close()

        panel._load_repository_from_path(repo)
        panel._load_repository_from_path(other)
        qtbot.waitUntil(lambda: panel.current_repo is not None, timeout=TIMEOUT_MS)
        qtbot.waitUntil(lambda: not panel._bg_threads, timeout=TIMEOUT_MS)
        assert panel.branch_selector.currentText() == "trunk"
        assert str(other) in panel.repo_path_label.text()


class TestRefreshing:
    def test_a_refresh_picks_up_a_change_on_disk(self, panel, qtbot, repo):
        _loaded(panel, qtbot, repo)
        (repo / "another.txt").write_text("more\n", encoding="utf-8")
        panel._refresh_change_list()
        qtbot.waitUntil(lambda: "[untracked] another.txt" in _rows(panel), timeout=TIMEOUT_MS)

    def test_requests_made_together_are_read_once(self, panel, qtbot, repo):
        from je_editor.pyside_ui.git_ui.git_client import git_client_gui
        _loaded(panel, qtbot, repo)
        qtbot.waitUntil(lambda: not panel._bg_threads, timeout=TIMEOUT_MS)
        reads = []
        real = git_client_gui.read_repository_state

        def counting(repository):
            reads.append(1)
            return real(repository)

        with patch(f"{MODULE}.read_repository_state", counting):
            panel._refresh_branch_list()
            panel._refresh_change_list()
            panel._refresh_change_list()
            qtbot.waitUntil(
                lambda: bool(reads) and not panel._state_read_running
                and not panel._state_read_wanted and not panel._bg_threads,
                timeout=TIMEOUT_MS)
        assert len(reads) == 1

    def test_without_a_repository_the_lists_are_emptied(self, panel):
        panel.changes_list_widget.addItem("left over")
        panel._refresh_change_list()
        assert panel.changes_list_widget.count() == 0

    def test_a_finished_thread_is_let_go(self, panel, qtbot, repo):
        # A thread scheduled for deletion and still listed was asked later
        # whether it was running, which reached a deleted object.
        _loaded(panel, qtbot, repo)
        qtbot.waitUntil(lambda: panel._bg_threads == [], timeout=TIMEOUT_MS)
