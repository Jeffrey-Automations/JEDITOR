from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from je_editor.pyside_ui.git_ui.code_diff_compare.side_by_side_diff_widget import SideBySideDiffWidget

# unified diff 裡新檔案那一行的開頭 / What the new file's line of a unified diff starts with
_NEW_FILE_HEADER = "+++ "
# 取不到檔名時分頁的標題 / The tab's title when no file name can be found
_UNNAMED_DIFF = "diff"


class MultiFileDiffViewer(QWidget):
    """
    Multi-file diff viewer using tabs to display each file.
    多檔案差異檢視器，使用分頁 (tab) 來顯示每個檔案的差異。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the multi-file diff viewer.
        初始化多檔案差異檢視器。
        """
        super().__init__(parent)
        # Tab widget to hold each file's diff
        # 用來存放每個檔案差異的分頁元件
        self.tabs = QTabWidget()

        # Layout: vertical box with only the tab widget
        # 版面配置：垂直佈局，僅包含分頁元件
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

    def set_diff_text(self, diff_text: str) -> None:
        """
        Set the diff text and split it into per-file tabs.
        設定差異文字，並依檔案拆分成多個分頁。
        """
        self.tabs.clear()
        file_diffs = self._split_by_file(diff_text)
        for file_name, ftext in file_diffs:
            viewer = SideBySideDiffWidget()  # 每個檔案使用 side-by-side viewer
            viewer.set_diff_text(ftext)
            self.tabs.addTab(viewer, file_name)  # 新增分頁，標題為檔名

    def _split_by_file(self, diff_text: str) -> list[tuple[str, str]]:
        """
        Split a unified diff text into chunks per file.
        將 unified diff 文字依檔案切分。
        """
        chunks = []
        current = []
        file_name = None

        for line in diff_text.splitlines():
            if line.startswith("diff --git"):
                # 如果遇到新的檔案 diff，先把前一個檔案的內容存起來
                if current and file_name:
                    chunks.append((file_name, "\n".join(current)))
                    current = []
                # 解析檔名，格式通常為 "diff --git a/file b/file"
                parts = line.split()
                if len(parts) >= 4:
                    file_name = parts[2][2:]  # 去掉 "a/"
                else:
                    file_name = "unknown"
                current.append(line)
            else:
                current.append(line)

        # 最後一個檔案也要加入結果。沒有 "diff --git" 標頭的 diff（編輯器自己比出來
        # 的「與 HEAD 的差異」）是單一檔案，檔名從 "+++" 那一行取；以前這種 diff
        # 會整個被丟掉，分頁開出來是空的
        # The last file joins the result too. A diff with no "diff --git" header
        # -- the editor's own diff against HEAD -- is a single file, named from
        # its "+++" line; such a diff used to be dropped whole, leaving the tab empty
        if current:
            chunks.append((file_name or self._name_from_header(current), "\n".join(current)))

        return chunks

    @staticmethod
    def _name_from_header(lines: list[str]) -> str:
        """
        從 unified diff 的 "+++" 標頭取出檔名
        Take the file name from a unified diff's "+++" header.

        :param lines: 一個檔案的 diff / one file's diff
        :return: 檔名；沒有標頭時為 ``diff`` / the file name, or ``diff`` with no header
        """
        for line in lines:
            if line.startswith(_NEW_FILE_HEADER):
                # "+++ b/name.py (working copy)" 或 "+++ b/name.py<TAB>時間"
                # "+++ b/name.py (working copy)" or "+++ b/name.py<TAB>timestamp"
                name = line[len(_NEW_FILE_HEADER):].split("\t")[0].split(" (")[0].strip()
                return name.removeprefix("b/") or _UNNAMED_DIFF
        return _UNNAMED_DIFF

    def set_dark_theme(self) -> None:
        """
        Apply dark theme to all tabs.
        對所有分頁套用深色主題。
        """
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, SideBySideDiffWidget):
                w.set_dark_theme()

    def set_light_theme(self) -> None:
        """
        Apply light theme to all tabs.
        對所有分頁套用淺色主題。
        """
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, SideBySideDiffWidget):
                w.set_light_theme()
