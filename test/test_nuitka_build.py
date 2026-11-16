"""Tests for the Nuitka build of the executable and the check CI runs on it (exe/)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_EXE = _ROOT / "exe"
# Stands in for the built executable: a file that is there, started as nothing else
_EDITOR = str(Path(sys.executable).resolve())


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"exe_{name}", _EXE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def build():
    return _load("build_nuitka")


@pytest.fixture(scope="module")
def check():
    return _load("check_build")


class TestTheBuildCommand:
    def test_it_builds_the_start_script_standalone_with_the_package_and_its_data(self, build):
        command = build.nuitka_command()

        assert command[1:3] == ["-m", "nuitka"]
        assert "--mode=standalone" in command
        assert {"--include-package=je_editor", "--include-package-data=je_editor"} <= set(command)
        assert command[-1].endswith("start_editor.py")

    def test_it_never_asks_a_question_ci_could_not_answer(self, build):
        assert "--assume-yes-for-downloads" in build.nuitka_command()

    def test_ci_checks_the_executable_where_the_build_puts_it(self, build):
        workflow = (_ROOT / ".github" / "workflows" / "dev.yml").read_text(encoding="utf-8")
        built = (build.DIST_DIR / "JEditor.exe").relative_to(_ROOT).as_posix()

        assert "--output-filename=JEditor" in build.nuitka_command()
        assert f"python exe/check_build.py {built}" in workflow

    def test_the_icon_it_names_is_there(self, build):
        if sys.platform == "win32":
            icon = next(part for part in build.nuitka_command() if part.startswith("--windows-icon-from-ico="))
            assert Path(icon.split("=", 1)[1]).is_file()


class TestTheCheck:
    @staticmethod
    def _run_as_the_editor(check, monkeypatch, code: str) -> None:
        """Have the check start a Python running *code* in place of the executable."""
        original = check.subprocess.Popen

        def popen(command, *args, **options):
            # Only the editor: subprocess.run starts taskkill through Popen too
            if command == [_EDITOR]:
                command = [sys.executable, "-c", code]
            return original(command, *args, **options)

        monkeypatch.setattr(check.subprocess, "Popen", popen)

    def test_without_an_executable_it_says_how_to_run_it(self, check, capsys):
        assert check.main([]) == 2
        assert check.main(["no/such/JEditor.exe"]) == 2
        assert "usage" in capsys.readouterr().err

    def test_an_editor_that_ends_at_once_fails_with_what_it_wrote(self, check, monkeypatch):
        self._run_as_the_editor(check, monkeypatch, "import sys; sys.stderr.write('no display'); sys.exit(3)")

        with pytest.raises(AssertionError, match="ended with 3: no display"):
            check.check_editor_starts(Path(_EDITOR))

    def test_an_editor_still_running_passes_and_is_stopped(self, check, monkeypatch):
        monkeypatch.setattr(check, "IDE_UP_SECONDS", 2)
        self._run_as_the_editor(check, monkeypatch, "import time; time.sleep(120)")

        assert check.check_editor_starts(Path(_EDITOR)) == "still running after 2 s"

    def test_a_failed_check_fails_the_run(self, check, monkeypatch, capsys):
        self._run_as_the_editor(check, monkeypatch, "import sys; sys.exit(1)")

        assert check.main([_EDITOR]) == 1
        assert "[FAIL] editor start" in capsys.readouterr().out
