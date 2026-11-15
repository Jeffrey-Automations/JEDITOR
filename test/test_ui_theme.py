"""Tests for the built-in window themes: their tokens, style sheet, icons and editor colours."""
from __future__ import annotations

import re

import pytest

from je_editor.utils.theme.theme_colors import (
    BUILTIN_DARK_COLORS, BUILTIN_LIGHT_COLORS, DARK_COLORS, LIGHT_COLORS, palette_for, retheme
)
from je_editor.utils.theme.ui_icons import ICON_CANVAS, has_icon, icon_names, icon_svg
from je_editor.utils.theme.ui_stylesheet import (
    ACTIVITY_BAR_NAME, BOTTOM_PANEL_NAME, IMAGE_NAMES, SIDE_BAR_NAME, build_stylesheet
)
from je_editor.utils.theme.ui_theme import (
    BUILTIN_STYLE_LABELS, DARK_TOKENS, DEFAULT_STYLE, LIGHT_TOKENS, MATERIAL_STYLES,
    STYLE_DARK, STYLE_LIGHT, is_builtin_style, is_light_style, style_choices, tokens_for
)
from je_editor.utils.shell.shell_views import BUILTIN_VIEWS

HEX_COLOUR = re.compile(r"^#[0-9a-f]{6}$")


def _brightness(colour: str) -> int:
    """The sum of a ``#rrggbb`` colour's channels."""
    return sum(int(colour[index:index + 2], 16) for index in (1, 3, 5))


class TestTellingStylesApart:
    @pytest.mark.parametrize("name", [STYLE_DARK, STYLE_LIGHT, " JEditor_Dark "])
    def test_a_built_in_theme_is_recognised(self, name):
        assert is_builtin_style(name) is True

    @pytest.mark.parametrize("name", ["dark_amber.xml", "light_blue.xml", "", None])
    def test_a_material_style_is_not_built_in(self, name):
        assert is_builtin_style(name) is False

    def test_the_built_in_light_theme_is_light(self):
        assert is_light_style(STYLE_LIGHT) is True
        assert is_light_style(STYLE_DARK) is False

    def test_a_dark_material_style_named_after_a_light_colour_stays_dark(self):
        assert is_light_style("dark_lightgreen.xml") is False

    def test_the_default_is_a_built_in_theme(self):
        assert is_builtin_style(DEFAULT_STYLE)

    def test_the_menu_lists_the_built_in_themes_first(self):
        choices = style_choices()
        assert [name for name, _label in choices[:len(BUILTIN_STYLE_LABELS)]] == \
            list(BUILTIN_STYLE_LABELS)
        assert [name for name, _label in choices[len(BUILTIN_STYLE_LABELS):]] == \
            list(MATERIAL_STYLES)

    def test_no_style_is_listed_twice(self):
        names = [name for name, _label in style_choices()]
        assert len(names) == len(set(names))


class TestTheTokens:
    def test_both_themes_define_the_same_tokens(self):
        assert set(DARK_TOKENS) == set(LIGHT_TOKENS)

    @pytest.mark.parametrize("tokens", [DARK_TOKENS, LIGHT_TOKENS])
    def test_every_token_is_a_hex_colour(self, tokens):
        for name, value in tokens.items():
            assert HEX_COLOUR.match(value), name

    def test_the_light_theme_really_is_lighter(self):
        assert _brightness(LIGHT_TOKENS["editor_background"]) > \
            _brightness(DARK_TOKENS["editor_background"])

    @pytest.mark.parametrize("tokens", [DARK_TOKENS, LIGHT_TOKENS])
    def test_text_stands_out_from_the_editor_background(self, tokens):
        # A third of the full range apart is far more than any unreadable pairing.
        apart = abs(_brightness(tokens["text"]) - _brightness(tokens["editor_background"]))
        assert apart > 255

    def test_a_material_style_borrows_the_tokens_of_its_lightness(self):
        assert tokens_for("light_blue.xml") == LIGHT_TOKENS
        assert tokens_for("dark_amber.xml") == DARK_TOKENS

    def test_the_tokens_are_a_copy(self):
        tokens = tokens_for(STYLE_DARK)
        tokens["text"] = "#000000"
        assert DARK_TOKENS["text"] != "#000000"


class TestTheStyleSheet:
    @pytest.mark.parametrize("tokens", [DARK_TOKENS, LIGHT_TOKENS])
    def test_no_placeholder_is_left_unfilled(self, tokens):
        assert "$" not in build_stylesheet(tokens)

    def test_the_braces_balance(self):
        sheet = build_stylesheet(DARK_TOKENS)
        assert sheet.count("{") == sheet.count("}")

    @pytest.mark.parametrize("name", [ACTIVITY_BAR_NAME, SIDE_BAR_NAME, BOTTOM_PANEL_NAME])
    def test_the_shell_widgets_are_styled_by_name(self, name):
        assert f"#{name}" in build_stylesheet(DARK_TOKENS)

    def test_the_two_themes_differ_only_in_colour(self):
        strip = re.compile(r"#[0-9a-f]{6}")
        assert strip.sub("#", build_stylesheet(DARK_TOKENS)) == \
            strip.sub("#", build_stylesheet(LIGHT_TOKENS))

    def test_a_missing_token_is_reported(self):
        incomplete = {key: value for key, value in DARK_TOKENS.items() if key != "accent"}
        with pytest.raises(KeyError):
            build_stylesheet(incomplete)

    def test_image_rules_are_left_out_without_images(self):
        assert "url(" not in build_stylesheet(DARK_TOKENS)

    def test_image_rules_name_the_files_given(self):
        urls = {name: f"C:/themes/{name}.svg" for name in IMAGE_NAMES}
        sheet = build_stylesheet(DARK_TOKENS, urls)
        for url in urls.values():
            assert f'url("{url}")' in sheet


class TestTheIcons:
    @pytest.mark.parametrize("name", icon_names())
    def test_every_icon_carries_the_colour_asked_for(self, name):
        svg = icon_svg(name, "#123456")
        assert svg.startswith("<svg ") and svg.endswith("</svg>")
        assert 'stroke="#123456"' in svg

    def test_the_size_is_applied(self):
        svg = icon_svg("run", "#000000", 48)
        assert 'width="48" height="48"' in svg
        assert f'viewBox="0 0 {ICON_CANVAS} {ICON_CANVAS}"' in svg

    def test_an_unknown_icon_is_refused(self):
        assert has_icon("no_such_icon") is False
        with pytest.raises(KeyError):
            icon_svg("no_such_icon", "#000000")

    def test_every_view_with_an_icon_names_one_that_exists(self):
        for view in BUILTIN_VIEWS:
            if view.icon:
                assert has_icon(view.icon), view.view_id


class TestTheEditorColoursOfABuiltInTheme:
    def test_each_built_in_palette_covers_every_colour(self):
        assert set(BUILTIN_DARK_COLORS) == set(DARK_COLORS)
        assert set(BUILTIN_LIGHT_COLORS) == set(LIGHT_COLORS)

    def test_a_built_in_theme_gets_its_own_palette(self):
        assert palette_for(STYLE_DARK) == BUILTIN_DARK_COLORS
        assert palette_for(STYLE_LIGHT) == BUILTIN_LIGHT_COLORS

    def test_the_gutter_matches_the_editor_background(self):
        red, green, blue = BUILTIN_DARK_COLORS["line_number_background_color"]
        assert f"#{red:02x}{green:02x}{blue:02x}" == DARK_TOKENS["editor_background"]

    def test_moving_from_a_material_style_takes_the_built_in_defaults(self):
        result = retheme(dict(DARK_COLORS), STYLE_DARK)
        assert result == BUILTIN_DARK_COLORS

    def test_moving_back_to_a_material_style_restores_its_defaults(self):
        assert retheme(dict(BUILTIN_LIGHT_COLORS), "dark_amber.xml") == DARK_COLORS

    def test_a_colour_the_user_picked_survives_a_built_in_theme(self):
        current = dict(DARK_COLORS)
        current["line_number_color"] = [1, 2, 3]
        assert retheme(current, STYLE_LIGHT)["line_number_color"] == [1, 2, 3]
