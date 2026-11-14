# 測試覆蓋度：JEDITOR

測量日期：2026-10-28。數字來自這台 Windows 機器上的一次實測，不是估計，也不是只數檔案。

| 項目 | 內容 |
|---|---|
| 直譯器 | 3.11.9 |
| 直譯器說明 | 專案 .venv |
| 工具 | coverage 7.15.0，`coverage run --branch` |
| 測量範圍 | `je_editor` |
| 測試路徑 | `test` |
| 命令 | `python -m coverage run --branch --source=je_editor -m pytest test` |
| 敘述覆蓋 | 74.06%（11861 / 16015） |
| 分支覆蓋 | 58.47%（2161 / 3696） |
| 測試結果 | 59 failed, 2798 passed, 14 errors in 285.60s (0:04:45)（pytest 結束碼 1） |
| 耗時 | 291.2 秒 |

敘述覆蓋是執行到的敘述數除以全部敘述數。分支覆蓋是執行到的分支數除以全部分支數。兩者分開算，沒有把分支混進敘述百分比。

## 覆蓋較低的檔案

只列這次測量裡敘述覆蓋最低的檔案，最多 12 個。

| 檔案 | 敘述覆蓋 | 已覆蓋 / 敘述 |
|---|---:|---:|
| `je_editor/code_scan/watchdog_thread.py` | 0.0% | 0 / 49 |
| `je_editor/code_scan/watchdog_implement.py` | 0.0% | 0 / 31 |
| `je_editor/code_scan/ruff_thread.py` | 0.0% | 0 / 21 |
| `je_editor/__main__.py` | 0.0% | 0 / 12 |
| `je_editor/pyside_ui/git_ui/code_diff_compare/side_by_side_diff_widget.py` | 10.4% | 18 / 173 |
| `je_editor/pyside_ui/main_ui/plugin_browser/plugin_browser_widget.py` | 14.83% | 31 / 209 |
| `je_editor/pyside_ui/dialog/search_ui/search_replace_widget.py` | 15.51% | 67 / 432 |
| `je_editor/pyside_ui/code/code_format/pep8_format.py` | 17.11% | 13 / 76 |
| `je_editor/plugins/plugin_loader.py` | 17.65% | 15 / 85 |
| `je_editor/pyside_ui/git_ui/git_client/git_branch_tree_widget.py` | 17.78% | 16 / 90 |
| `je_editor/pyside_ui/dialog/file_dialog/create_file_dialog.py` | 21.88% | 7 / 32 |
| `je_editor/pyside_ui/main_ui/editor/process_input.py` | 24.0% | 12 / 50 |

## 重掃（2026-10-28）

同一套覆蓋度命令再跑一次。覆蓋度與上次同一量級。下面是這次仍然失敗的測試。

- FAILED test/test_syntax_engine.py::TestCategories::test_a_string_over_several_lines_colours_each_of_them
- FAILED test/test_syntax_engine.py::TestCategories::test_lines_past_the_first_chunk
- FAILED test/test_syntax_engine.py::TestColumnsCountUtf16Units::test_text_after_wide_characters
- FAILED test/test_syntax_engine.py::TestColumnsCountUtf16Units::test_a_region_starting_after_wide_characters
- FAILED test/test_syntax_engine.py::TestColumnsCountUtf16Units::test_a_lone_surrogate_does_not_stop_the_analysis
- FAILED test/test_syntax_engine.py::TestFollowingAnEdit::test_the_first_text_changes_every_line
- FAILED test/test_syntax_engine.py::TestFollowingAnEdit::test_opening_a_string_reaches_every_line_after_it
- FAILED test/test_syntax_engine.py::TestFollowingAnEdit::test_removing_it_again_puts_the_lines_back
- FAILED test/test_syntax_engine.py::TestFollowingAnEdit::test_an_edit_can_change_a_line_above_it
- FAILED test/test_syntax_engine.py::TestFollowingAnEdit::test_the_result_matches_a_fresh_analysis
- FAILED test/test_syntax_engine.py::TestStructuralRegions::test_outer_regions_come_first
- FAILED test/test_syntax_engine.py::TestStructuralRegions::test_a_region_knows_whether_it_spans_lines
- FAILED test/test_syntax_engine.py::TestStructuralRegions::test_javascript_regions
- FAILED test/test_syntax_engine.py::TestStructuralRegions::test_json_regions
- FAILED test/test_syntax_engine.py::TestQueryFiles::test_the_queries_compile_and_name_known_things[python]
- FAILED test/test_syntax_engine.py::TestQueryFiles::test_the_queries_compile_and_name_known_things[javascript]
- FAILED test/test_syntax_engine.py::TestQueryFiles::test_the_queries_compile_and_name_known_things[json]
- FAILED test/test_syntax_engine.py::TestWhenAGrammarCannotBeUsed::test_the_load_is_tried_once
- FAILED test/test_syntax_engine.py::TestWhenAGrammarCannotBeUsed::test_a_broken_query_file
- FAILED test/test_syntax_engine.py::TestWhenAGrammarCannotBeUsed::test_an_unknown_region_name_is_left_out
- FAILED test/test_syntax_engine.py::TestWhenAGrammarCannotBeUsed::test_a_grammar_that_ships_no_highlight_query
- FAILED test/test_syntax_engine.py::TestWhenAGrammarCannotBeUsed::test_a_text_too_large_is_left_uncoloured
- FAILED test/test_syntax_engine.py::TestTheBindingIsUsedSafely::test_reading_rows_does_not_take_references_away
- FAILED test/test_syntax_engine.py::TestTheSyntaxLanguageService::test_an_open_document_has_a_syntax_tree
- FAILED test/test_syntax_engine.py::TestTheSyntaxLanguageService::test_the_symbols_are_the_named_regions
- FAILED test/test_syntax_engine.py::TestTheSyntaxLanguageService::test_the_tree_follows_the_document
- FAILED test/test_syntax_engine.py::TestTheSyntaxLanguageService::test_the_language_id_counts_before_the_file_name
- FAILED test/test_syntax_engine.py::TestTheSyntaxLanguageService::test_a_capability_it_does_not_offer_is_an_error_reply
- FAILED test/test_syntax_engine.py::TestTheSyntaxLanguageService::test_a_change_to_a_document_it_missed_opens_it
- FAILED test/test_tree_sitter_highlighter.py::TestColours::test_a_python_definition
- FAILED test/test_tree_sitter_highlighter.py::TestColours::test_an_interpolation_is_not_painted_as_string
- FAILED test/test_tree_sitter_highlighter.py::TestColours::test_builtins_types_and_escapes
- FAILED test/test_tree_sitter_highlighter.py::TestColours::test_json_keys_and_values
- FAILED test/test_tree_sitter_highlighter.py::TestColours::test_javascript
- FAILED test/test_tree_sitter_highlighter.py::TestColours::test_a_string_over_several_lines
- FAILED test/test_tree_sitter_highlighter.py::TestFollowingEdits::test_a_string_opened_above_reaches_the_lines_below_at_once
- FAILED test/test_tree_sitter_highlighter.py::TestFollowingEdits::test_removing_it_puts_the_lines_back
- FAILED test/test_tree_sitter_highlighter.py::TestFollowingEdits::test_a_line_above_the_edit_is_repainted_on_the_next_turn
- FAILED test/test_tree_sitter_highlighter.py::TestFollowingEdits::test_replacing_the_whole_text
- FAILED test/test_tree_sitter_highlighter.py::TestChoosingAHighlighter::test_a_language_the_engine_knows_uses_it[main.py-python]
- FAILED test/test_tree_sitter_highlighter.py::TestChoosingAHighlighter::test_a_language_the_engine_knows_uses_it[stubs.pyi-python]
- FAILED test/test_tree_sitter_highlighter.py::TestChoosingAHighlighter::test_a_language_the_engine_knows_uses_it[app.js-javascript]
- FAILED test/test_tree_sitter_highlighter.py::TestChoosingAHighlighter::test_a_language_the_engine_knows_uses_it[data.json-json]
- FAILED test/test_tree_sitter_highlighter.py::TestChoosingAHighlighter::test_a_language_the_engine_knows_uses_it[None-python]
- FAILED test/test_tree_sitter_highlighter.py::TestReplacingAHighlighter::test_the_text_is_recoloured_for_the_new_language
- ERROR test/test_ai_providers.py
- ERROR test/test_syntax_engine.py::TestTheModel::test_a_session_satisfies_the_interface
- ERROR test/test_syntax_engine.py::TestCategories::test_keywords_names_and_types
- ERROR test/test_syntax_engine.py::TestCategories::test_a_definition_its_receiver_and_its_annotations
- ERROR test/test_syntax_engine.py::TestCategories::test_a_comment
- ERROR test/test_syntax_engine.py::TestCategories::test_what_is_inside_a_string_comes_after_the_string
- ERROR test/test_syntax_engine.py::TestCategories::test_an_empty_line_and_a_missing_line_have_nothing
- ERROR test/test_syntax_engine.py::TestCategories::test_a_later_pattern_wins_on_the_same_node
- ERROR test/test_syntax_engine.py::TestFollowingAnEdit::test_the_same_text_changes_nothing
- ERROR test/test_syntax_engine.py::TestFollowingAnEdit::test_typing_in_one_line_changes_that_line
- ERROR test/test_syntax_engine.py::TestFollowingAnEdit::test_adding_and_removing_lines
- ERROR test/test_syntax_engine.py::TestFollowingAnEdit::test_emptying_the_text
- ERROR test/test_syntax_engine.py::TestStructuralRegions::test_classes_functions_and_their_names
- ERROR test/test_syntax_engine.py::TestStructuralRegions::test_regions_follow_an_edit
