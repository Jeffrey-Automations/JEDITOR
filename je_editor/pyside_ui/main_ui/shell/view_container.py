"""
側邊欄的容器：一個標題加上一疊面板，面板在第一次顯示時才建立
The side bar's container: a header over a stack of views, each built the first time it is shown.

啟動時只有檔案總管看得見，測試面板、大綱、AI 聊天這些要等使用者點了才需要。先
放一個空頁佔位置，真的要顯示時才呼叫工廠函式，啟動就不必為用不到的面板付出時間
與執行緒。
At startup only the explorer is visible; the test view, the outline and the AI
chat are needed only once someone clicks them. An empty page holds each one's
place and its factory is called when it is really shown, so startup pays neither
the time nor the threads of views nobody opened.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from je_editor.utils.logging.loggin_instance import jeditor_logger
from je_editor.utils.theme.ui_stylesheet import SIDE_BAR_HEADER_NAME

ViewFactory = Callable[[], QWidget]


class LazyPage(QWidget):
    """
    先佔位置、要顯示時才建立內容的頁面
    A page that holds a place and builds its content when it is shown.
    """

    def __init__(self, factory: ViewFactory, parent: QWidget | None = None) -> None:
        """
        :param factory: 建立內容的函式 / the function that builds the content
        :param parent: Qt 父元件 / the Qt parent
        """
        super().__init__(parent)
        self._factory: ViewFactory | None = factory
        self.content: QWidget | None = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def ensure_built(self) -> QWidget | None:
        """
        確保內容已經建立
        Make sure the content has been built.

        工廠函式失敗（例如少了某個選用套件）時記錄下來並留下空頁，不讓一個面板
        拖垮整個視窗；下次顯示不會再試。
        A factory that fails, for want of an optional package for instance, is
        logged and leaves the page empty rather than taking the window down with
        one view; it is not tried again on the next show.

        :return: 內容；建立失敗時為 ``None`` / the content, or ``None`` when building failed
        """
        if self._factory is None:
            return self.content
        factory, self._factory = self._factory, None
        try:
            self.content = factory()
        except (ImportError, RuntimeError, OSError, ValueError, AttributeError) as error:
            jeditor_logger.error("A shell view could not be built: %r", error)
            return None
        # 內容放在可捲動區域裡：面板自己的最小寬度比這一區還寬時出現捲軸，而不是
        # 把整個視窗撐大
        # The content sits in a scroll area: a view whose own minimum width
        # exceeds the area gets a scroll bar instead of forcing the window wider
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(self.content)
        self._layout.addWidget(scroll_area)
        return self.content


class ViewContainer(QWidget):
    """
    標題加上一疊面板
    A header over a stack of views.
    """

    def __init__(self, object_name: str, parent: QWidget | None = None) -> None:
        """
        :param object_name: 樣式用的物件名稱 / the object name the style goes by
        :param parent: Qt 父元件 / the Qt parent
        """
        super().__init__(parent)
        self.setObjectName(object_name)
        self.header = QLabel()
        self.header.setObjectName(SIDE_BAR_HEADER_NAME)
        self.stack = QStackedWidget()
        self._pages: dict[str, LazyPage] = {}
        self._titles: dict[str, str] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.stack)

    def add_view(self, view_id: str, title: str, factory: ViewFactory) -> None:
        """
        加入一個面板，內容等到第一次顯示才建立
        Add a view, whose content waits for its first showing.

        :param view_id: 面板 ID / the view's ID
        :param title: 標題 / the title
        :param factory: 建立內容的函式 / the function that builds the content
        :raises ValueError: ID 已經用過時 / when the ID is already taken
        """
        if view_id in self._pages:
            raise ValueError(f"The view {view_id!r} is already registered")
        page = LazyPage(factory)
        self._pages[view_id] = page
        self._titles[view_id] = title
        self.stack.addWidget(page)

    def view_ids(self) -> tuple[str, ...]:
        """
        已加入的面板 ID
        The IDs of the views added.

        :return: 依加入順序 / in the order they were added
        """
        return tuple(self._pages)

    def show_view(self, view_id: str) -> QWidget | None:
        """
        切換到某個面板，還沒建立的話先建立
        Switch to a view, building it first when it has not been.

        :param view_id: 面板 ID / the view's ID
        :return: 面板的內容；沒有這個面板或建立失敗時為 ``None``
            the view's content, or ``None`` for an unknown view or a failed build
        """
        page = self._pages.get(view_id)
        if page is None:
            return None
        content = page.ensure_built()
        self.stack.setCurrentWidget(page)
        self.header.setText(self._titles[view_id].upper())
        return content

    def current_view(self) -> str:
        """
        目前顯示的面板 ID
        The ID of the view being shown.

        :return: ID，一個面板都沒有時為空字串 / the ID, or an empty string with no view
        """
        current = self.stack.currentWidget()
        for view_id, page in self._pages.items():
            if page is current:
                return view_id
        return ""

    def set_title(self, view_id: str, title: str) -> None:
        """
        換掉一個面板的標題（換語言時）
        Replace a view's title, as a language change does.

        :param view_id: 面板 ID / the view's ID
        :param title: 新標題 / the new title
        """
        if view_id not in self._titles:
            return
        self._titles[view_id] = title
        if self.current_view() == view_id:
            self.header.setText(title.upper())

    def built_content(self) -> list[QWidget]:
        """
        已經建立的面板內容
        The content of every view built so far.

        :return: 元件清單 / the widgets
        """
        return [page.content for page in self._pages.values() if page.content is not None]

    def content_of(self, view_id: str) -> QWidget | None:
        """
        某個面板的內容，還沒建立時為 ``None``
        A view's content, or ``None`` while it has not been built.

        :param view_id: 面板 ID / the view's ID
        :return: 內容 / the content
        """
        page = self._pages.get(view_id)
        return page.content if page is not None else None
