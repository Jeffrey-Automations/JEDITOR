"""
變數檢視器要顯示的列：從命名空間或除錯器的變數算出來
The rows the variable inspector shows, worked out from a namespace or a debugger's variables.

這裡不碰 Qt。檢視器每半秒看一次命名空間，所以每個值的文字都有長度上限，
也不讓一個壞掉的 ``__repr__`` 把整張表弄垮。
Nothing here touches Qt. The inspector looks at the namespace twice a second,
so the text of every value is bounded, and one broken ``__repr__`` does not take
the whole table down.
"""
from __future__ import annotations

import ast
import reprlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from je_editor.utils.logging.loggin_instance import jeditor_logger

# 一個值最多顯示多少字元 / How many characters of one value are shown
MAX_VALUE_CHARACTERS = 200
# 容器最多列出幾個元素、巢狀幾層 / How many elements of a container are listed, and how deep
_MAX_ELEMENTS = 20
_MAX_DEPTH = 3
# 互動式命名空間裡不屬於使用者的名稱都以底線開頭（IPython 的 ``_``、``_i1``、``__name__``）
# In an interactive namespace the names that are not the user's start with an underscore
_PRIVATE_PREFIX = "_"
_MISSING = object()


def _bounded_repr() -> reprlib.Repr:
    """建立有上限的 repr / Build a repr with limits on every kind of value."""
    bounded = reprlib.Repr()
    bounded.maxlevel = _MAX_DEPTH
    bounded.maxstring = MAX_VALUE_CHARACTERS
    bounded.maxother = MAX_VALUE_CHARACTERS
    bounded.maxlong = MAX_VALUE_CHARACTERS
    for name in ("maxtuple", "maxlist", "maxarray", "maxdict", "maxset", "maxfrozenset", "maxdeque"):
        setattr(bounded, name, _MAX_ELEMENTS)
    return bounded


_REPR = _bounded_repr()


@dataclass(frozen=True)
class VariableRow:
    """
    檢視器的一列
    One row of the inspector.

    :param name: 變數名稱 / the variable's name
    :param type_name: 型別名稱 / the name of its type
    :param value_text: 顯示用的值 / the value, as text to show
    """

    name: str
    type_name: str
    value_text: str


def describe(value: object) -> str:
    """
    把一個值寫成有長度上限的文字
    Write a value as text of bounded length.

    :param value: 任何物件 / any object
    :return: 它的 repr，過長時截短；``__repr__`` 出錯時是一段說明
        its repr, cut when long; a note when its ``__repr__`` fails
    """
    try:
        text = _REPR.repr(value)
    except Exception as error:  # noqa: BLE001 — 使用者物件的 __repr__ 可能丟任何例外 / a user's __repr__ may raise anything
        jeditor_logger.debug("variable_rows.py repr of a %s failed: %r", type(value).__name__, error)
        return f"<{type(value).__name__}: repr failed ({type(error).__name__})>"
    if len(text) > MAX_VALUE_CHARACTERS:
        return text[:MAX_VALUE_CHARACTERS] + "..."
    return text


def namespace_rows(namespace: Mapping[str, object], hidden: Mapping[str, object] | None = None) -> list[VariableRow]:
    """
    命名空間裡屬於使用者的變數
    The variables of a namespace that are the user's.

    和 IPython 的 ``%who`` 同一套規則：底線開頭的不列，``hidden`` 裡同名且是同一個
    物件的也不列（IPython 自己放進去的 ``In``、``Out``、``exit``）；使用者把那個名稱
    指到別的東西之後就會列出來。
    The rule IPython's ``%who`` uses: a name starting with an underscore is left
    out, and so is one that ``hidden`` holds as the very same object (what
    IPython itself put there: ``In``, ``Out``, ``exit``). Once the user binds
    that name to something else, it is listed.

    :param namespace: 命名空間 / the namespace
    :param hidden: 不屬於使用者的名稱與它們的物件 / the names that are not the user's, with their objects
    :return: 依命名空間的順序排列的列 / the rows, in the namespace's order
    """
    not_the_users = hidden or {}
    # 先抄一份：describe() 會呼叫使用者物件的 __repr__，它若動到命名空間，邊走邊改會出錯
    # A copy first: describe() calls a user object's __repr__, and one that touches
    # the namespace would change it while it is being walked
    snapshot = tuple(namespace.items())
    return [
        VariableRow(name, type(value).__name__, describe(value))
        for name, value in snapshot
        if isinstance(name, str) and not name.startswith(_PRIVATE_PREFIX)
        and not_the_users.get(name, _MISSING) is not value
    ]


def debugger_rows(variables: Iterable[object]) -> list[VariableRow]:
    """
    除錯器回報的變數
    The variables a debugger reported.

    除錯器給的值本來就是文字，這裡只截短。
    A debugger gives its values as text already; they are only cut here.

    :param variables: 有 ``name``、``value``、``type_name`` 的物件
        objects with ``name``, ``value`` and ``type_name``
    :return: 依回報順序排列的列 / the rows, in the order reported
    """
    rows = []
    for variable in variables:
        text = str(getattr(variable, "value", ""))
        if len(text) > MAX_VALUE_CHARACTERS:
            text = text[:MAX_VALUE_CHARACTERS] + "..."
        rows.append(VariableRow(str(getattr(variable, "name", "")), str(getattr(variable, "type_name", "")), text))
    return rows


def parse_value(text: str) -> object:
    """
    把使用者在「值」欄輸入的文字變成值
    Turn what the user typed in the value column into a value.

    只接受字面值（``ast.literal_eval``），不執行任何程式碼；不是字面值的就當成字串。
    Literals only (``ast.literal_eval``), so nothing typed is ever run; what is
    not a literal is taken as a string.

    :param text: 輸入的文字 / the text typed
    :return: 字面值，或原本的文字 / the literal, or the text itself
    """
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return text
