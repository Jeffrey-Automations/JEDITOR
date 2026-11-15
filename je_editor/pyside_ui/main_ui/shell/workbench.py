"""
視窗的外框：活動列、側邊欄、編輯分頁、下方面板與第二側邊欄
The window's shell: activity bar, side bar, editor tabs, bottom panel and secondary side bar.

::

    ┌──┬───────────┬──────────────────────┬───────────┐
    │活│ 側邊欄    │ 編輯分頁             │ 第二      │
    │動│ side bar  │ editor tabs          │ 側邊欄    │
    │列│           ├──────────────────────┤ secondary │
    │  │           │ 下方面板 bottom panel│           │
    └──┴───────────┴──────────────────────┴───────────┘

外框只管「哪一區開著、顯示哪個面板」，面板自己的內容不歸它管。面板以 ID 登記，
宿主程式與外掛用 ``register_view`` 加自己的；其他模組用 ``reveal_view`` 請外框
把某個面板顯示出來，不必知道它放在哪一區。
The shell looks after which area is open and which view it shows; what a view
holds is the view's own business. Views are registered by ID, and a host
application or plugin adds its own through ``register_view``. Other modules ask
for a view with ``reveal_view`` without knowing which area it lives in.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QSizePolicy, QSplitter, QTabWidget, QToolButton, QWidget
)

from je_editor.pyside_ui.main_ui.save_settings.user_setting_file import user_setting_dict
from je_editor.pyside_ui.main_ui.shell.activity_bar import ActivityBar
from je_editor.pyside_ui.main_ui.shell.explorer_panel import ExplorerPanel
from je_editor.pyside_ui.main_ui.shell.output_panels import OutputPanels
from je_editor.pyside_ui.main_ui.shell.shell_icons import set_action_icon
from je_editor.pyside_ui.main_ui.shell.view_container import LazyPage, ViewContainer, ViewFactory
from je_editor.utils.multi_language.multi_language_wrapper import language_wrapper
from je_editor.utils.shell.layout_state import (
    LAYOUT_SETTING_KEY, ShellLayout, layout_from_setting, layout_to_setting, with_known_views
)
from je_editor.utils.shell.shell_views import (
    AREA_BOTTOM, AREA_SECONDARY, AREA_SIDE, BUILTIN_VIEWS, VIEW_AI_CHAT, VIEW_DEBUG,
    VIEW_DEBUG_CONSOLE, VIEW_EXPLORER, VIEW_FORMAT_CHECK, VIEW_OUTLINE, VIEW_OUTPUT,
    VIEW_PROBLEMS, VIEW_SOURCE_CONTROL, VIEW_TERMINAL, VIEW_TESTS, VIEW_TODO, VIEW_VARIABLES,
    ViewSpec, view_title
)
from je_editor.utils.theme.ui_stylesheet import (
    BOTTOM_PANEL_NAME, SECONDARY_SIDE_BAR_NAME, SIDE_BAR_NAME
)

# 分隔器裡各區的位置 / Where each area sits in its splitter
_SIDE_INDEX = 0
_CENTER_INDEX = 1
_SECONDARY_INDEX = 2
_EDITOR_INDEX = 0
_BOTTOM_INDEX = 1

# 視窗還沒顯示、量不到寬高時用來分配比例的尺寸
# The size the proportions are worked out against while the window has not been
# shown and so has no measurable width or height
_NOMINAL_WIDTH = 1400
_NOMINAL_HEIGHT = 800


def _outline_view(window: QMainWindow) -> QWidget:
    """建立大綱面板 / Build the outline view."""
    from je_editor.pyside_ui.main_ui.outline_panel.outline_panel_widget import OutlinePanelWidget
    return OutlinePanelWidget(window)


def _debug_view(window: QMainWindow) -> QWidget:
    """建立除錯面板 / Build the debug view."""
    from je_editor.pyside_ui.main_ui.debug_panel.debug_actions import build_debug_panel
    return build_debug_panel(window)


def _tests_view(window: QMainWindow) -> QWidget:
    """建立測試面板 / Build the test view."""
    from je_editor.pyside_ui.main_ui.test_panel.test_panel_widget import TestPanelWidget
    return TestPanelWidget(window)


def _todo_view(window: QMainWindow) -> QWidget:
    """建立 TODO 面板 / Build the TODO view."""
    from je_editor.pyside_ui.main_ui.todo_panel.todo_panel_widget import TodoPanelWidget
    return TodoPanelWidget(window)


def _problems_view(window: QMainWindow) -> QWidget:
    """建立問題面板 / Build the problems view."""
    from je_editor.pyside_ui.main_ui.problems_panel.problems_panel_widget import (
        ProblemsPanelWidget
    )
    return ProblemsPanelWidget(window)


def _ai_chat_view(window: QMainWindow) -> QWidget:
    """建立 AI 聊天面板 / Build the AI chat view."""
    from je_editor.pyside_ui.main_ui.ai_widget.chat_ui import ChatUI
    return ChatUI(window)


# 等到第一次顯示才建立的內建面板 / The built-in views that wait for their first showing
_LAZY_BUILDERS: dict[str, Callable[[QMainWindow], QWidget]] = {
    VIEW_OUTLINE: _outline_view,
    VIEW_DEBUG: _debug_view,
    VIEW_TESTS: _tests_view,
    VIEW_TODO: _todo_view,
    VIEW_PROBLEMS: _problems_view,
    VIEW_AI_CHAT: _ai_chat_view,
}


class Workbench(QObject):
    """
    主視窗的外框
    The main window's shell.
    """

    def __init__(self, window: QMainWindow, tab_widget: QTabWidget) -> None:
        """
        :param window: 要裝上外框的主視窗 / the main window the shell is fitted to
        :param tab_widget: 編輯分頁，會成為中間那一區 / the editor tabs, which become the middle area
        """
        super().__init__(window)
        self._window = window
        self.tab_widget = tab_widget
        self._views: dict[str, ViewSpec] = {}
        self._bottom_pages: dict[str, QWidget] = {}
        self._layout = ShellLayout()
        words = language_wrapper.language_word_dict

        # 整個視窗共用的檔案樹與輸出面板 / The file tree and output views the whole window shares
        self.explorer = ExplorerPanel(window)
        self.output = OutputPanels()

        self.activity_bar = ActivityBar(words.get("view_activity_bar_title", ""), window)
        window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.activity_bar)
        self.side_bar = ViewContainer(SIDE_BAR_NAME)
        self.secondary_side_bar = ViewContainer(SECONDARY_SIDE_BAR_NAME)
        self.bottom_panel = QTabWidget()
        self.bottom_panel.setObjectName(BOTTOM_PANEL_NAME)
        self.bottom_panel.setDocumentMode(True)
        self._add_hide_panel_button()

        self.center_splitter = QSplitter(Qt.Orientation.Vertical)
        self.center_splitter.addWidget(tab_widget)
        self.center_splitter.addWidget(self.bottom_panel)
        self.center_splitter.setCollapsible(_EDITOR_INDEX, False)
        # 中間這一區的寬度不受內容的最小寬度限制：終端機那一排按鈕很寬，否則打開
        # 第二側邊欄時被擠掉的會是兩邊的側邊欄
        # The middle area's width is not held to its content's minimum: the
        # terminal's row of buttons is wide, and otherwise opening the secondary
        # side bar would squeeze the side bars rather than the middle
        self.center_splitter.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(self.side_bar)
        self.main_splitter.addWidget(self.center_splitter)
        self.main_splitter.addWidget(self.secondary_side_bar)
        self.main_splitter.setCollapsible(_CENTER_INDEX, False)
        self.main_splitter.setStretchFactor(_SIDE_INDEX, 0)
        self.main_splitter.setStretchFactor(_CENTER_INDEX, 1)
        self.main_splitter.setStretchFactor(_SECONDARY_INDEX, 0)
        self.center_splitter.setStretchFactor(_EDITOR_INDEX, 1)
        self.center_splitter.setStretchFactor(_BOTTOM_INDEX, 0)
        window.setCentralWidget(self.main_splitter)
        # 使用者拖動分隔線時記下尺寸；只有這時讀到的尺寸是排版完成後的
        # Sizes are recorded when the user drags a divider, the one moment the
        # sizes read back are those of a finished layout
        self.main_splitter.splitterMoved.connect(self._remember_sizes)
        self.center_splitter.splitterMoved.connect(self._remember_sizes)

        self.explorer.tree.clicked.connect(self._open_selected_file)
        self.activity_bar.view_requested.connect(self.toggle_view)
        self.bottom_panel.currentChanged.connect(self._build_bottom_page)
        self._register_builtin_views()
        self.apply_layout(self._layout)

    # ---------------- Registration 登記 ----------------
    def _add_hide_panel_button(self) -> None:
        """在下方面板的角落放一顆收起面板的按鈕 / Put a button that hides the panel in its corner."""
        action = QAction(language_wrapper.language_word_dict.get(
            "view_menu_toggle_bottom_panel", ""), self.bottom_panel)
        set_action_icon(action, "bottom_panel")
        action.triggered.connect(lambda: self.set_bottom_panel_visible(False))
        button = QToolButton()
        button.setDefaultAction(action)
        button.setAutoRaise(True)
        self.bottom_panel.setCornerWidget(button, Qt.Corner.TopRightCorner)
        self._hide_panel_action = action

    def _register_builtin_views(self) -> None:
        """登記內建的面板 / Register the built-in views."""
        ready: dict[str, QWidget] = {
            VIEW_EXPLORER: self.explorer,
            VIEW_OUTPUT: self.output.code_result_scroll_area,
            VIEW_TERMINAL: self.output.console_widget,
            VIEW_DEBUG_CONSOLE: self.output.debugger_result,
            VIEW_FORMAT_CHECK: self.output.format_check_result,
            VIEW_VARIABLES: self.output.variable_inspector,
        }
        for spec in BUILTIN_VIEWS:
            if spec.view_id == VIEW_DEBUG and getattr(self._window, "debug_controller", None) is None:
                # 沒有除錯控制器的宿主視窗沒有東西可以顯示 / A host window with no debug controller has nothing to show
                continue
            widget = ready.get(spec.view_id)
            if widget is not None:
                self.register_view(spec, widget=widget)
                continue
            if spec.view_id == VIEW_SOURCE_CONTROL:
                # 已經建好，但仍以工廠登記：這樣它會被包進可捲動的頁面
                # Already built, yet registered through a factory, which is what wraps it in a scrollable page
                self.register_view(spec, lambda: self.output.git_gui)
                continue
            builder = _LAZY_BUILDERS[spec.view_id]
            self.register_view(spec, lambda build=builder: build(self._window))

    def register_view(self, spec: ViewSpec, factory: ViewFactory | None = None,
                      widget: QWidget | None = None) -> None:
        """
        登記一個面板
        Register a view.

        宿主程式與外掛用這個方法把自己的面板放進側邊欄、下方面板或第二側邊欄。
        A host application or a plugin uses this to place a view of its own in
        the side bar, the bottom panel or the secondary side bar.

        :param spec: 面板的描述 / the view's description
        :param factory: 第一次顯示時建立內容的函式 / the function that builds the
            content on the first showing
        :param widget: 已經建好的內容；與 ``factory`` 擇一 / content already built,
            given instead of ``factory``
        :raises ValueError: ID 已經登記過，或兩個參數都沒給時
            when the ID is already registered, or neither argument is given
        """
        if spec.view_id in self._views:
            raise ValueError(f"The view {spec.view_id!r} is already registered")
        if factory is None and widget is None:
            raise ValueError("A view needs a factory or a widget")
        build: ViewFactory = factory if factory is not None else (lambda: widget)
        title = view_title(spec, language_wrapper.language_word_dict)
        if spec.area == AREA_BOTTOM:
            page = widget if widget is not None else LazyPage(build)
            self._bottom_pages[spec.view_id] = page
            self.bottom_panel.addTab(page, title)
        else:
            container = self.side_bar if spec.area == AREA_SIDE else self.secondary_side_bar
            container.add_view(spec.view_id, title, build)
            self.activity_bar.add_view(
                spec.view_id, spec.icon or VIEW_EXPLORER, title,
                at_bottom=spec.area == AREA_SECONDARY)
        self._views[spec.view_id] = spec
        self._add_view_menu_entry(spec)

    def add_view(self, view_id: str, area: str, factory: ViewFactory | None = None,
                 widget: QWidget | None = None, *, title_key: str = "", icon: str = "",
                 title: str = "") -> None:
        """
        以一般引數登記一個面板，宿主程式不必匯入 ``ViewSpec``
        Register a view from plain arguments, so a host application need not import ``ViewSpec``.

        :param view_id: 不隨翻譯變動的 ID / the ID, which no translation changes
        :param area: ``"side"``、``"bottom"`` 或 ``"secondary"`` / ``"side"``, ``"bottom"`` or ``"secondary"``
        :param factory: 第一次顯示時建立內容的函式 / the function that builds the content on the first showing
        :param widget: 已經建好的內容；與 ``factory`` 擇一 / content already built, given instead of ``factory``
        :param title_key: 標題在語系字典裡的鍵，換語言時跟著換 / the title's key in
            the language dictionary, which follows a language change
        :param icon: 活動列的圖示名稱，見 ``ui_icons`` / the activity bar icon's name, see ``ui_icons``
        :param title: 沒有翻譯鍵時直接用的標題 / the title used as it is when there is no key
        :raises ValueError: 區域不對、ID 已經登記過，或沒有內容時
            for an unknown area, an ID already registered, or nothing to show
        """
        self.register_view(
            ViewSpec(view_id, area, title_key=title_key, icon=icon, title=title), factory, widget)

    def _add_view_menu_entry(self, spec: ViewSpec) -> None:
        """
        檢視選單已經建好的話，替後來登記的面板補上一個項目
        Give a view registered after the View menu was built an entry in it.

        內建面板登記時選單還不存在，它們的項目由選單自己建立。
        The menu does not exist yet when the built-in views are registered, and
        builds their entries itself.
        """
        menu = getattr(self._window, "view_menu", None)
        if menu is None:
            return
        action = QAction(view_title(spec, language_wrapper.language_word_dict), menu)
        action.triggered.connect(
            lambda _checked=False, wanted=spec.view_id: self.show_view(wanted))
        menu.addAction(action)

    def view_ids(self, area: str | None = None) -> tuple[str, ...]:
        """
        已登記的面板 ID
        The IDs of the registered views.

        :param area: 只列這一區；省略時全部 / only this area, or every one when omitted
        :return: 依登記順序 / in the order they were registered
        """
        return tuple(
            view_id for view_id, spec in self._views.items()
            if area is None or spec.area == area)

    def view_spec(self, view_id: str) -> ViewSpec | None:
        """
        某個面板的描述
        A view's description.

        :param view_id: 面板 ID / the view's ID
        :return: 描述，沒有登記時為 ``None`` / the description, or ``None`` when unregistered
        """
        return self._views.get(view_id)

    # ---------------- Showing 顯示 ----------------
    def _container_of(self, area: str) -> ViewContainer:
        """某一區的容器 / The container of an area."""
        return self.side_bar if area == AREA_SIDE else self.secondary_side_bar

    def _build_bottom_page(self, index: int) -> None:
        """切到下方面板的某一頁時，把還沒建立的內容建起來 / Build a bottom page's content on switching to it."""
        page = self.bottom_panel.widget(index)
        if isinstance(page, LazyPage):
            page.ensure_built()

    def show_view(self, view_id: str) -> QWidget | None:
        """
        顯示一個面板，所在的區域收著的話一併打開
        Show a view, opening its area when that is hidden.

        :param view_id: 面板 ID / the view's ID
        :return: 面板的內容；沒有這個面板或建立失敗時為 ``None``
            the view's content, or ``None`` for an unknown view or a failed build
        """
        spec = self._views.get(view_id)
        if spec is None:
            return None
        if spec.area == AREA_BOTTOM:
            page = self._bottom_pages[view_id]
            self.bottom_panel.setCurrentWidget(page)
            self.set_bottom_panel_visible(True)
            return page.ensure_built() if isinstance(page, LazyPage) else page
        container = self._container_of(spec.area)
        content = container.show_view(view_id)
        self._set_area_visible(spec.area, True)
        return content

    def toggle_view(self, view_id: str) -> None:
        """
        活動列的行為：點目前的面板收起那一區，點別的就切過去
        What the activity bar does: clicking the current view hides its area, and
        clicking another switches to it.

        :param view_id: 面板 ID / the view's ID
        """
        spec = self._views.get(view_id)
        if spec is None:
            return
        if spec.area != AREA_BOTTOM:
            container = self._container_of(spec.area)
            if not container.isHidden() and container.current_view() == view_id:
                self._set_area_visible(spec.area, False)
                return
        self.show_view(view_id)

    def is_view_shown(self, view_id: str) -> bool:
        """
        某個面板目前是不是顯示著
        Whether a view is the one being shown in an open area.

        :param view_id: 面板 ID / the view's ID
        :return: 顯示中為 ``True`` / ``True`` while it is shown
        """
        spec = self._views.get(view_id)
        if spec is None:
            return False
        if spec.area == AREA_BOTTOM:
            return (not self.bottom_panel.isHidden()
                    and self.bottom_panel.currentWidget() is self._bottom_pages[view_id])
        container = self._container_of(spec.area)
        return not container.isHidden() and container.current_view() == view_id

    def widget_of(self, view_id: str) -> QWidget | None:
        """
        某個面板的內容，還沒建立時為 ``None``
        A view's content, or ``None`` while it has not been built.

        :param view_id: 面板 ID / the view's ID
        :return: 內容 / the content
        """
        spec = self._views.get(view_id)
        if spec is None:
            return None
        if spec.area == AREA_BOTTOM:
            page = self._bottom_pages[view_id]
            return page.content if isinstance(page, LazyPage) else page
        return self._container_of(spec.area).content_of(view_id)

    def _set_area_visible(self, area: str, visible: bool) -> None:
        """顯示或收起側邊欄或第二側邊欄 / Show or hide the side bar or the secondary side bar."""
        container = self._container_of(area)
        if visible and not container.current_view() and container.view_ids():
            container.show_view(container.view_ids()[0])
        elif visible and container.current_view():
            # 上次收起時還沒建立的面板，這時才建立 / A view not yet built when last hidden is built now
            container.show_view(container.current_view())
        container.setVisible(visible)
        self._apply_sizes()
        self._sync_activity_bar()

    def set_side_bar_visible(self, visible: bool) -> None:
        """
        顯示或收起側邊欄
        Show or hide the side bar.

        :param visible: 是否顯示 / whether it is shown
        """
        self._set_area_visible(AREA_SIDE, visible)

    def set_secondary_side_bar_visible(self, visible: bool) -> None:
        """
        顯示或收起第二側邊欄
        Show or hide the secondary side bar.

        :param visible: 是否顯示 / whether it is shown
        """
        self._set_area_visible(AREA_SECONDARY, visible)

    def set_bottom_panel_visible(self, visible: bool) -> None:
        """
        顯示或收起下方面板
        Show or hide the bottom panel.

        :param visible: 是否顯示 / whether it is shown
        """
        if visible:
            self._build_bottom_page(self.bottom_panel.currentIndex())
        self.bottom_panel.setVisible(visible)
        self._apply_sizes()

    def toggle_side_bar(self) -> None:
        """切換側邊欄 / Toggle the side bar."""
        self.set_side_bar_visible(self.side_bar.isHidden())

    def toggle_secondary_side_bar(self) -> None:
        """切換第二側邊欄 / Toggle the secondary side bar."""
        self.set_secondary_side_bar_visible(self.secondary_side_bar.isHidden())

    def toggle_bottom_panel(self) -> None:
        """切換下方面板 / Toggle the bottom panel."""
        self.set_bottom_panel_visible(self.bottom_panel.isHidden())

    def _sync_activity_bar(self) -> None:
        """讓活動列的圖示反映目前顯示的面板 / Make the activity bar's icons reflect the views shown."""
        for view_id, spec in self._views.items():
            if spec.area != AREA_BOTTOM:
                self.activity_bar.set_checked(view_id, self.is_view_shown(view_id))

    # ---------------- Layout 版面 ----------------
    def _remember_sizes(self, *_moved: int) -> None:
        """
        把目前開著的區域的尺寸記下來
        Record the size of every area that is open.

        收著的區域寬度是零，不能拿來蓋掉上次的寬度，否則再打開時就縮成一條線。
        A hidden area measures zero, which must not replace its last width or it
        would reopen as a sliver.

        :param _moved: ``splitterMoved`` 帶來的位置與索引，用不到
            the position and index ``splitterMoved`` carries, which are not needed
        """
        widths = self.main_splitter.sizes()
        heights = self.center_splitter.sizes()
        changes: dict[str, int] = {}
        if not self.side_bar.isHidden() and widths[_SIDE_INDEX] > 0:
            changes["side_bar_width"] = widths[_SIDE_INDEX]
        if not self.secondary_side_bar.isHidden() and widths[_SECONDARY_INDEX] > 0:
            changes["secondary_width"] = widths[_SECONDARY_INDEX]
        if not self.bottom_panel.isHidden() and heights[_BOTTOM_INDEX] > 0:
            changes["bottom_panel_height"] = heights[_BOTTOM_INDEX]
        if changes:
            self._layout = layout_from_setting({**layout_to_setting(self._layout), **changes})

    def _apply_sizes(self) -> None:
        """把記住的尺寸套用到分隔器上 / Apply the remembered sizes to the splitters."""
        side = 0 if self.side_bar.isHidden() else self._layout.side_bar_width
        secondary = 0 if self.secondary_side_bar.isHidden() else self._layout.secondary_width
        # 分隔器還沒顯示時沒有可信的寬高，用一個名目尺寸分配比例
        # A splitter not yet shown has no extent to trust, so a nominal one shares out the proportions
        shown = self.main_splitter.isVisible()
        width = self.main_splitter.width() if shown else _NOMINAL_WIDTH
        self.main_splitter.setSizes([side, max(width - side - secondary, 1), secondary])
        bottom = 0 if self.bottom_panel.isHidden() else self._layout.bottom_panel_height
        height = self.center_splitter.height() if shown else _NOMINAL_HEIGHT
        self.center_splitter.setSizes([max(height - bottom, 1), bottom])

    def layout(self) -> ShellLayout:
        """
        目前的版面
        The layout as it stands.

        :return: 版面 / the layout
        """
        current_bottom = self.bottom_panel.currentWidget()
        bottom_view = next(
            (view_id for view_id, page in self._bottom_pages.items() if page is current_bottom),
            self._layout.bottom_view)
        return layout_from_setting({
            **layout_to_setting(self._layout),
            "side_bar_visible": not self.side_bar.isHidden(),
            "side_view": self.side_bar.current_view() or self._layout.side_view,
            "bottom_panel_visible": not self.bottom_panel.isHidden(),
            "bottom_view": bottom_view,
            "secondary_visible": not self.secondary_side_bar.isHidden(),
        })

    def apply_layout(self, layout: ShellLayout) -> None:
        """
        套用一份版面
        Apply a layout.

        :param layout: 要套用的版面 / the layout to apply
        """
        self._layout = with_known_views(
            layout, self.view_ids(AREA_SIDE), self.view_ids(AREA_BOTTOM))
        # 先設好顯示與否再選面板：收著的區域不必為了還原版面而建立它的面板
        # Visibility first and the view after it: a hidden area need not build
        # its view just to have the layout restored
        self.side_bar.setVisible(self._layout.side_bar_visible)
        self.secondary_side_bar.setVisible(self._layout.secondary_visible)
        self.bottom_panel.setVisible(self._layout.bottom_panel_visible)
        if self._layout.side_bar_visible:
            self.side_bar.show_view(self._layout.side_view)
        if self._layout.secondary_visible and self.secondary_side_bar.view_ids():
            self.secondary_side_bar.show_view(self.secondary_side_bar.view_ids()[0])
        page = self._bottom_pages.get(self._layout.bottom_view)
        if page is not None:
            self.bottom_panel.setCurrentWidget(page)
        if self._layout.bottom_panel_visible:
            self._build_bottom_page(self.bottom_panel.currentIndex())
        self._apply_sizes()
        self._sync_activity_bar()

    def restore_layout(self) -> None:
        """
        從使用者設定還原版面
        Restore the layout from the user settings.

        視窗顯示之後再套用一次尺寸：顯示之前分隔器還沒有寬高，只能照比例分配。
        The sizes are applied once more after the window is shown: before that
        the splitters have no extent and can only share it out in proportion.
        """
        self.apply_layout(layout_from_setting(user_setting_dict.get(LAYOUT_SETTING_KEY)))
        QTimer.singleShot(0, self, self._apply_sizes)

    @staticmethod
    def has_saved_layout() -> bool:
        """
        使用者設定裡有沒有存過版面
        Whether the user settings hold a layout.

        宿主程式用它分辨「第一次啟動」與「使用者上次就是這樣擺的」：前者可以先
        顯示自己的面板，後者要照存下來的版面。
        A host application tells a first start from a layout the user left this
        way with it: the first may show the host's own view, and the second has
        to follow what was saved.

        :return: 有的話為 ``True`` / ``True`` when there is one
        """
        return bool(user_setting_dict.get(LAYOUT_SETTING_KEY))

    def save_layout(self) -> None:
        """把目前的版面記進使用者設定 / Record the current layout in the user settings."""
        user_setting_dict[LAYOUT_SETTING_KEY] = layout_to_setting(self.layout())

    # ---------------- Files 檔案 ----------------
    def _open_selected_file(self) -> None:
        """開啟檔案樹選中的檔案 / Open the file selected in the tree."""
        path = self.explorer.selected_path()
        if path is not None and path.is_file():
            self.open_file(path)

    def open_file(self, path: Path) -> None:
        """
        在編輯分頁開啟一個檔案
        Open a file in the editor tabs.

        目前的分頁是空白且沒改過的話就用它，否則開新分頁；檔案已經開著就切過去。
        The current tab is used when it is blank and untouched, and a new one is
        opened otherwise; a file already open is switched to.

        :param path: 檔案路徑 / the file's path
        """
        from je_editor.pyside_ui.main_ui.editor.editor_widget import EditorWidget

        current = self.tab_widget.currentWidget()
        blank = (
            isinstance(current, EditorWidget)
            and current.current_file is None
            and not current.code_edit.toPlainText()
        )
        if blank:
            current.open_an_file(path)
            # 分頁沒有換，狀態列不會自己更新成新檔案的語言與編碼
            # The tab did not change, so the status bar would not move to the
            # new file's language and encoding by itself
            refresh = getattr(self._window, "refresh_status_bar", None)
            if callable(refresh):
                refresh()
            return
        opener = getattr(self._window, "go_to_new_tab", None)
        if callable(opener):
            opener(path)

    # ---------------- Lifecycle 生命週期 ----------------
    def retranslate(self) -> None:
        """依目前語言重新標示外框 / Relabel the shell in the language now in use."""
        words = language_wrapper.language_word_dict
        self.activity_bar.setWindowTitle(words.get("view_activity_bar_title", ""))
        self._hide_panel_action.setText(words.get("view_menu_toggle_bottom_panel", ""))
        for view_id, spec in self._views.items():
            title = view_title(spec, words)
            if spec.area == AREA_BOTTOM:
                index = self.bottom_panel.indexOf(self._bottom_pages[view_id])
                self.bottom_panel.setTabText(index, title)
            else:
                self._container_of(spec.area).set_title(view_id, title)
                self.activity_bar.set_title(view_id, title)
            content = self.widget_of(view_id)
            relabel = getattr(content, "retranslate", None)
            if callable(relabel):
                relabel()

    def close_views(self) -> None:
        """
        關閉每個已經建立的面板，讓它們收掉自己的執行緒與子程序
        Close every view that was built, so each stops its own threads and child processes.
        """
        for view_id in self._views:
            content = self.widget_of(view_id)
            if content is not None:
                content.close()
        self.output.close()


def workbench_of(window: object) -> Workbench | None:
    """
    取得視窗的外框
    The shell of a window.

    :param window: 主視窗 / the main window
    :return: 外框；視窗沒有時為 ``None`` / the shell, or ``None`` when the window has none
    """
    workbench = getattr(window, "workbench", None)
    return workbench if isinstance(workbench, Workbench) else None


def reveal_view(window: object, view_id: str) -> bool:
    """
    請視窗的外框把某個面板顯示出來
    Ask a window's shell to show a view.

    :param window: 主視窗 / the main window
    :param view_id: 面板 ID / the view's ID
    :return: 有顯示時為 ``True``；視窗沒有外框或沒有這個面板時為 ``False``
        ``True`` when it was shown, ``False`` with no shell or no such view
    """
    workbench = workbench_of(window)
    if workbench is None or workbench.view_spec(view_id) is None:
        return False
    workbench.show_view(view_id)
    return True
