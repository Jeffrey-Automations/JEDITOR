"""Tests for the shell's pure side: the table of views and the layout state."""
from __future__ import annotations

import json

import pytest

from je_editor.utils.multi_language.english import english_word_dict
from je_editor.utils.shell.layout_state import (
    DEFAULT_SIDE_BAR_WIDTH, MAX_AREA_SIZE, MIN_AREA_SIZE, ShellLayout, layout_from_setting,
    layout_to_setting, with_known_views
)
from je_editor.utils.shell.shell_views import (
    AREA_BOTTOM, AREA_SECONDARY, AREA_SIDE, AREAS, BUILTIN_VIEWS, VIEW_EXPLORER, VIEW_OUTPUT,
    ViewSpec, view_title, views_in
)


class TestTheBuiltInViews:
    def test_no_id_is_used_twice(self):
        ids = [view.view_id for view in BUILTIN_VIEWS]
        assert len(ids) == len(set(ids))

    def test_every_area_has_a_view(self):
        for area in AREAS:
            assert views_in(area), area

    def test_every_title_is_translated(self):
        for view in BUILTIN_VIEWS:
            assert english_word_dict.get(view.title_key), view.view_id

    def test_a_view_outside_the_bottom_panel_has_an_icon(self):
        for view in views_in(AREA_SIDE) + views_in(AREA_SECONDARY):
            assert view.icon, view.view_id

    def test_the_default_layout_names_views_that_exist(self):
        layout = ShellLayout()
        assert layout.side_view in {view.view_id for view in views_in(AREA_SIDE)}
        assert layout.bottom_view in {view.view_id for view in views_in(AREA_BOTTOM)}

    def test_views_keep_their_order_within_an_area(self):
        side = [view.view_id for view in BUILTIN_VIEWS if view.area == AREA_SIDE]
        assert [view.view_id for view in views_in(AREA_SIDE)] == side


class TestDescribingAView:
    def test_an_unknown_area_is_refused(self):
        with pytest.raises(ValueError):
            ViewSpec("mine", "floating")

    def test_an_empty_id_is_refused(self):
        with pytest.raises(ValueError):
            ViewSpec("", AREA_SIDE)

    def test_the_title_comes_from_the_dictionary(self):
        view = ViewSpec("mine", AREA_SIDE, title_key="view_explorer")
        assert view_title(view, {"view_explorer": "Dateien"}) == "Dateien"

    def test_a_view_without_a_key_uses_its_own_title(self):
        assert view_title(ViewSpec("mine", AREA_SIDE, title="Navigation"), {}) == "Navigation"

    def test_a_view_with_nothing_else_falls_back_to_its_id(self):
        assert view_title(ViewSpec("mine", AREA_SIDE, title_key="missing"), {}) == "mine"


class TestReadingALayout:
    def test_a_layout_survives_the_settings_file(self):
        layout = ShellLayout(side_bar_visible=False, side_view="outline", secondary_visible=True,
                             side_bar_width=333)
        stored = json.loads(json.dumps(layout_to_setting(layout)))
        assert layout_from_setting(stored) == layout

    @pytest.mark.parametrize("raw", [None, [], "explorer", 3])
    def test_anything_but_a_mapping_gives_the_default(self, raw):
        assert layout_from_setting(raw) == ShellLayout()

    def test_a_missing_field_takes_its_default(self):
        assert layout_from_setting({"side_bar_visible": False}) == \
            ShellLayout(side_bar_visible=False)

    def test_a_wrong_type_takes_its_default(self):
        layout = layout_from_setting(
            {"side_bar_visible": "yes", "side_view": 5, "side_bar_width": "wide"})
        assert layout == ShellLayout()

    def test_a_boolean_is_not_taken_for_a_width(self):
        assert layout_from_setting({"side_bar_width": True}).side_bar_width == \
            DEFAULT_SIDE_BAR_WIDTH

    @pytest.mark.parametrize("width, expected", [
        (1, MIN_AREA_SIZE), (10 ** 9, MAX_AREA_SIZE), (301.7, 301),
    ])
    def test_a_size_is_kept_within_bounds(self, width, expected):
        assert layout_from_setting({"side_bar_width": width}).side_bar_width == expected

    def test_an_unknown_field_is_ignored(self):
        assert layout_from_setting({"floating_toolbar": True}) == ShellLayout()


class TestViewsThatNoLongerExist:
    def test_a_view_that_is_gone_goes_back_to_the_default(self):
        layout = ShellLayout(side_view="from_a_plugin", bottom_view="also_gone")
        fixed = with_known_views(layout, [VIEW_EXPLORER], [VIEW_OUTPUT])
        assert (fixed.side_view, fixed.bottom_view) == (VIEW_EXPLORER, VIEW_OUTPUT)

    def test_a_view_that_exists_is_kept(self):
        layout = ShellLayout(side_view="outline")
        assert with_known_views(layout, [VIEW_EXPLORER, "outline"], [VIEW_OUTPUT]) is layout

    def test_the_sizes_are_untouched(self):
        layout = ShellLayout(side_view="gone", side_bar_width=444)
        assert with_known_views(layout, [VIEW_EXPLORER], [VIEW_OUTPUT]).side_bar_width == 444
