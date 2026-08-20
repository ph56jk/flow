"""Bẫy chữ ``đ`` trong các bộ chuẩn hoá tiếng Việt.

``đ`` (U+0111) là một chữ cái riêng, không phải ``d`` cộng dấu, nên
``unicodedata.normalize`` không tách nó ra. Mọi bộ chuẩn hoá "bỏ dấu rồi
so với hằng số ASCII" ở đây đều phải gấp ``đ`` thành ``d`` TRƯỚC khi bỏ
dấu, nếu không hằng số nào chứa chữ ``d`` vốn sinh ra từ ``đ`` sẽ không
bao giờ khớp — và không có lỗi nào được ném ra.

Các ca dưới đây ghim **câu người ta gõ**, không ghim chuỗi đã chuẩn hoá,
để chúng còn đúng nếu bộ chuẩn hoá bên dưới đổi cách viết.
"""

from __future__ import annotations

import ast
import re
import sys
import unittest
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flow_web.service import (
    PRODUCT_SHOT_RULE_PRIORITY,
    PRODUCT_SHOT_RULES,
    FlowWebService,
)


def service() -> FlowWebService:
    return FlowWebService.__new__(FlowWebService)


FOLDERS = (
    "_normalize_skill_token",
    "_compact_match_text",
    "_tokenize_match_words",
)

# Hàm TRẢ VỀ giá trị đã gấp sẵn, nên biến nhận kết quả của nó cũng là "đã
# gấp". Danh sách do người viết nên phải có chỗ canh — và phải canh đúng
# thứ: tôi đã suýt nhận nhầm ``_erp_query_aliases`` vào đây. Hàm ấy CÓ gấp
# bên trong (``key = self._compact_match_text(cleaned)`` để khử trùng lặp)
# nhưng lại trả về ``cleaned`` — chữ người đọc được, còn nguyên dấu cách.
# Nhận nhầm là tự tay tắt ca ghép-đôi cho mọi biến ăn kết quả của nó, mà
# ca canh "hàm này có gấp gì không" vẫn xanh. Nên phải hỏi: **cái được
# TRẢ VỀ** có gấp không.
FOLDING_HELPERS = ("_user_assistant_erp_query_groups",)


def literal_bindings_of(function: ast.AST) -> dict[str, object]:
    """Tên → giá trị hằng gán cho nó ngay trong hàm.

    Chỉ nhận tên được ghi **đúng một lần**. Tên bị gán lại — hoặc còn làm
    biến chạy của một vòng lặp khác — thì lúc đem so không biết nó đang
    mang giá trị nào, mà đoán bừa chính là cách vụ ``token`` sinh ra 14 lỗi
    bảng chữ cái ma.
    """
    written: dict[str, int] = {}
    for node in ast.walk(function):
        written_targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            written_targets = list(node.targets)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            written_targets = [node.target]
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            written_targets = [node.target]
        elif isinstance(node, ast.comprehension):
            written_targets = [node.target]
        for target in written_targets:
            for child in ast.walk(target):
                if isinstance(child, ast.Name):
                    written[child.id] = written.get(child.id, 0) + 1

    bindings: dict[str, object] = {}
    for node in ast.walk(function):
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            targets = [node.targets[0]]
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        if len(targets) == 1 and isinstance(targets[0], ast.Name):
            if written.get(targets[0].id, 0) != 1:
                continue
            try:
                bindings[targets[0].id] = ast.literal_eval(node.value)
            except Exception:
                pass
    return bindings


def literal_loop_names(function: ast.AST) -> set[str]:
    """Biến chạy của vòng lặp duyệt trên hằng — tức cây kim viết thẳng.

    Phải gỡ tuple theo CỘT: ``for triggers, values in alias_groups`` rồi
    ``for trigger in triggers``. Dàn phẳng thì cột bí danh trả về bị lẫn
    vào cột cây kim.
    """
    bindings = literal_bindings_of(function)
    values: dict[str, list] = {}

    def resolve(expr: ast.AST) -> list:
        if isinstance(expr, (ast.Set, ast.List, ast.Tuple)):
            try:
                return list(ast.literal_eval(expr))
            except Exception:
                return []
        if isinstance(expr, ast.Name):
            bound = bindings.get(expr.id)
            if isinstance(bound, (list, tuple, set)):
                return list(bound)
            spread: list = []
            for value in values.get(expr.id, ()):
                if isinstance(value, (list, tuple, set)):
                    spread.extend(value)
            return spread
        return []

    def bind(target: ast.expr, items: list) -> None:
        if isinstance(target, ast.Name):
            values.setdefault(target.id, []).extend(items)
        elif isinstance(target, ast.Tuple):
            for index, element in enumerate(target.elts):
                bind(
                    element,
                    [
                        item[index]
                        for item in items
                        if isinstance(item, (list, tuple)) and len(item) > index
                    ],
                )

    for _ in range(3):
        for node in ast.walk(function):
            if isinstance(node, ast.For):
                bind(node.target, resolve(node.iter))
            elif isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
                for generator in node.generators:
                    bind(generator.target, resolve(generator.iter))

    return {
        name
        for name, items in values.items()
        if items and all(isinstance(item, str) for item in items)
    }


def folded_names(function: ast.AST) -> set[str]:
    """Mọi biến mang giá trị ĐÃ gấp, tính cả lan truyền.

    Ba đường lan: dẫn xuất (``x = y.replace(...)`` với ``y`` đã gấp), biến
    chạy vòng lặp trên tập đã gấp, và bộ tích luỹ (``seen.add(key)``).
    Thiếu lan truyền thì 14 phép so hiện ra như lệch, cả 14 đều là oan.
    """

    def calls_folder(node: ast.AST) -> bool:
        return any(
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr in (*FOLDERS, *FOLDING_HELPERS)
            for child in ast.walk(node)
        )

    def loads(node: ast.AST) -> set[str]:
        return {
            child.id
            for child in ast.walk(node)
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
        }

    folded: set[str] = set()
    for _ in range(8):
        before = len(folded)
        for node in ast.walk(function):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if len(targets) == 1 and isinstance(targets[0], ast.Name) and node.value is not None:
                    sources = loads(node.value)
                    if calls_folder(node.value) or (sources and sources <= folded):
                        folded.add(targets[0].id)
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                sources = loads(node.iter)
                if calls_folder(node.iter) or (sources and sources <= folded):
                    folded.add(node.target.id)
            if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
                for generator in node.generators:
                    if not isinstance(generator.target, ast.Name):
                        continue
                    sources = loads(generator.iter)
                    if calls_folder(generator.iter) or (sources and sources <= folded):
                        folded.add(generator.target.id)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"add", "append", "update", "extend"}
                and isinstance(node.func.value, ast.Name)
                and node.args
            ):
                sources = loads(node.args[0])
                if sources and sources <= folded:
                    folded.add(node.func.value.id)
        if len(folded) == before:
            break
    return folded


def both_sides_folded_functions() -> list[ast.FunctionDef]:
    """Họ hàm gấp CẢ HAI PHÍA: gấp từ hai nguồn khác nhau trong cùng hàm.

    Tự tìm chứ đừng chép tay danh sách — danh sách chép tay mục ngay: lúc
    viết ba hàm luật sản phẩm thì họ này đã có 13 thành viên.
    """
    source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    family: list[ast.FunctionDef] = []
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef):
            continue
        sources: set[str] = set()
        for node in ast.walk(function):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
                continue
            if not isinstance(node.targets[0], ast.Name):
                continue
            for child in ast.walk(node.value):
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute)
                    and child.func.attr in FOLDERS
                ):
                    sources |= {
                        argument.id
                        for argument in child.args
                        if isinstance(argument, ast.Name)
                    }
        if len(sources) >= 2:
            family.append(function)
    return family


@lru_cache(maxsize=1)
def outer_literal_boxes() -> dict[str, tuple[str, ...]]:
    """Bảng hằng chuỗi khai ở mức module hoặc mức lớp của ``service.py``."""
    source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    boxes: dict[str, tuple[str, ...]] = {}
    holders: list[ast.AST] = [tree, *[n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]]
    for holder in holders:
        for statement in holder.body:
            if not (isinstance(statement, ast.Assign) and len(statement.targets) == 1):
                continue
            target = statement.targets[0]
            if not isinstance(target, ast.Name):
                continue
            try:
                value = ast.literal_eval(statement.value)
            except Exception:
                continue
            if isinstance(value, (set, frozenset, list, tuple, dict)) and value:
                items = tuple(value)
                if all(isinstance(item, str) for item in items):
                    boxes[target.id] = items
    return boxes


def box_name(part: ast.AST) -> str:
    """Tên bảng hằng mà một vế của phép so đang trỏ tới (``self.X`` hoặc ``X``)."""
    if isinstance(part, ast.Attribute) and isinstance(part.value, ast.Name):
        return part.attr if part.value.id == "self" else ""
    return part.id if isinstance(part, ast.Name) else ""


def missing_twins(by_site: dict[str, set[str]]) -> list[str]:
    """Kim có ``_`` mà thiếu bản viết liền **ngay tại chỗ so ấy**.

    Tách ra thành hàm thuần để kiểm được bằng dữ liệu bịa: chọn phạm vi nào
    là một quyết định, và quyết định thì phải có ca chứng minh nó gánh việc.
    """
    reports = []
    for site, needles in sorted(by_site.items()):
        for needle in sorted(needles):
            if "_" not in needle:
                continue
            twin = needle.replace("_", "")
            if twin not in needles:
                reports.append(
                    f"{site}: {needle!r} cần bản viết liền {twin!r} ngay tại chỗ so ấy"
                )
    return reports


class SweptNeedles(NamedTuple):
    """Kết quả quét: cây kim ASCII, kèm nơi tìm thấy, kèm các hàm đã quét."""

    by_text: dict[str, set[str]]
    functions: list[str]
    # Gom theo TỪNG CHỖ SO (hàm + số dòng), không theo hàm. Phạm vi của một
    # bất biến quyết định đột biến có cắn hay không: ``vogoi`` nằm ở hàm
    # khác KHÔNG cứu được vế ``compact`` của ``_erp_query_aliases``. Gom
    # theo dòng còn gộp đúng hai vế của ``x in normalized or x in compact``
    # thành một chỗ, vì đó mới thật là một phép so.
    by_site: dict[str, set[str]] = {}


def needles_compared_with(normalizer: str) -> SweptNeedles:
    """Mọi hằng chuỗi được đem so với đầu ra của ``normalizer``.

    Quét theo BIẾN chứ không theo hàm: chỉ nhận hằng nào thật sự so với
    chính biến giữ kết quả chuẩn hoá. Quét theo hàm — lấy mọi hằng trong
    hàm nào có gọi bộ chuẩn hoá — vừa nhiễu (kéo theo cả khoá payload và
    từ vựng sản phẩm) vừa vẫn sót, vì cây kim có thể nằm ở nhánh khác.

    Bắt đủ bốn hình dạng, kể cả hình dạng cây kim nằm bên TRÁI toán tử:
    ``x == "k"``, ``x in {...}``, ``"k" in x``, ``any(k in x for k in (...))``,
    cộng dict tra bằng ``.get(x)`` và ``x.startswith("k")``.

    KHÔNG lọc theo hình dạng chuỗi. Bộ lọc ``^[a-z0-9_]+$`` của lượt quét
    đầu chính là thứ đã giấu mất họ lỗi "cây kim viết sai bảng chữ cái":
    nó vứt đúng những cây kim hỏng trước khi có ai kịp nhìn thấy chúng.
    """
    source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))

    def is_call(node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == normalizer
        )

    def elements(node: ast.AST) -> list[ast.expr]:
        if isinstance(node, ast.Constant):
            return [node]
        if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
            return list(node.elts)
        return []

    found: dict[str, set[str]] = {}
    sites: dict[str, set[str]] = {}
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(is_call(child) for child in ast.walk(node))
    ]

    for function in functions:
        holders: set[str] = set()
        literal_dicts: dict[str, ast.Dict] = {}

        # Cây kim có thể không nằm ngay tại phép so: nó nằm trong một bảng
        # hằng, và chỗ so chỉ thấy BIẾN CHẠY của vòng lặp —
        # ``for trigger in triggers: ... trigger in normalized``. Lượt quét
        # đầu đòi vế lặp phải là tuple hằng viết tại chỗ, nên cả bảng
        # ``alias_groups`` của ``_erp_query_aliases`` (20 cây kim) lọt lưới.
        # Gỡ tuple theo CỘT chứ đừng dàn phẳng: cùng bảng ấy, cột 0 là kim
        # đem so, cột 1 là bí danh trả về — dàn phẳng thì ``"tap de"`` ở cột
        # 1 bị báo oan là sai bảng chữ cái.
        literal_bindings = literal_bindings_of(function)

        def iterable_values(expr: ast.AST, scope: dict[str, list]) -> list:
            if isinstance(expr, (ast.Set, ast.List, ast.Tuple)):
                try:
                    return list(ast.literal_eval(expr))
                except Exception:
                    return []
            if isinstance(expr, ast.Name):
                bound = literal_bindings.get(expr.id)
                if isinstance(bound, (list, tuple, set)):
                    return list(bound)
                spread: list = []
                for value in scope.get(expr.id, ()):
                    if isinstance(value, (list, tuple, set)):
                        spread.extend(value)
                return spread
            return []

        def bind(target: ast.expr, values: list, scope: dict[str, list]) -> None:
            if isinstance(target, ast.Name):
                # GHI ĐÈ, không cộng dồn: cùng một hàm có thể dùng lại tên
                # ``token`` ở hai vòng khác nhau. Cộng dồn thì cây kim của
                # vòng này bị quy oan cho vòng kia — đúng cái đã làm 14 slug
                # của ``_select_prompt_skills`` hiện ra như lỗi bảng chữ cái.
                scope[target.id] = list(values)
            elif isinstance(target, ast.Tuple):
                for index, element in enumerate(target.elts):
                    bind(
                        element,
                        [
                            value[index]
                            for value in values
                            if isinstance(value, (list, tuple)) and len(value) > index
                        ],
                        scope,
                    )

        def scan(node: ast.AST, scope: dict[str, list]) -> None:
            """Đi cây theo PHẠM VI, mỗi vòng lặp một bản sao ràng buộc."""
            if isinstance(node, ast.For):
                scan(node.iter, scope)
                inner = dict(scope)
                bind(node.target, iterable_values(node.iter, scope), inner)
                for child in [*node.body, *node.orelse]:
                    scan(child, inner)
                return
            if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.DictComp)):
                inner = dict(scope)
                for generator in node.generators:
                    scan(generator.iter, inner)
                    bind(generator.target, iterable_values(generator.iter, inner), inner)
                for child in ast.iter_child_nodes(node):
                    if child not in node.generators:
                        scan(child, inner)
                for generator in node.generators:
                    for condition in generator.ifs:
                        scan(condition, inner)
                return
            if isinstance(node, ast.Compare) and any(
                isinstance(op, (ast.In, ast.NotIn, ast.Eq, ast.NotEq)) for op in node.ops
            ):
                parts = [node.left, *node.comparators]
                if any(holds_result(part) for part in parts):
                    for part in parts:
                        if holds_result(part) or not isinstance(part, ast.Name):
                            continue
                        for value in scope.get(part.id, ()):
                            if isinstance(value, str):
                                keep(value, "loop-var", node)
            for child in ast.iter_child_nodes(node):
                scan(child, scope)

        for node in ast.walk(function):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if any(is_call(child) for child in ast.walk(node.value)):
                holders.add(target.id)
            if isinstance(node.value, ast.Dict):
                literal_dicts[target.id] = node.value

        def holds_result(node: ast.AST) -> bool:
            return is_call(node) or (isinstance(node, ast.Name) and node.id in holders)

        def keep(value: object, why: str, node: ast.AST | None = None) -> None:
            if isinstance(value, str) and value:
                found.setdefault(value, set()).add(f"{function.name}:{why}")
                sites.setdefault(
                    f"{function.name}:{getattr(node, 'lineno', 0)}", set()
                ).add(value)

        def named_set_strings(node: ast.AST) -> list[str]:
            """Hình dạng kim thứ SÁU: ``normalized in generic_exact``.

            Bốn hình dạng đầu chỉ nhìn thấy tập hằng viết THẲNG tại chỗ.
            Tập gán vào biến trước rồi mới đem so thì lọt lưới, mà "0 cây
            kim" đọc y hệt "sạch". Repo này thủng đúng chỗ ấy: 25 cây kim ở
            ``_sanitize_user_assistant_product_filter`` và
            ``_erp_auto_search_query`` chưa từng bị lượt quét nhìn thấy.
            """
            if not isinstance(node, ast.Name):
                return []
            bound = literal_bindings.get(node.id)
            if not isinstance(bound, (set, frozenset, list, tuple)):
                return []
            return [item for item in bound if isinstance(item, str)]

        for statement in function.body:
            scan(statement, {})

        for node in ast.walk(function):
            if isinstance(node, ast.Compare) and any(
                isinstance(op, (ast.In, ast.NotIn, ast.Eq, ast.NotEq)) for op in node.ops
            ):
                parts = [node.left, *node.comparators]
                if any(holds_result(part) for part in parts):
                    for part in parts:
                        if holds_result(part):
                            continue
                        for element in elements(part):
                            if isinstance(element, ast.Constant):
                                keep(element.value, "compare", node)
                        for value in named_set_strings(part):
                            keep(value, "named-set", node)
            if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp)) and isinstance(
                node.elt, ast.Compare
            ):
                inner = node.elt
                if any(holds_result(part) for part in [inner.left, *inner.comparators]):
                    for generator in node.generators:
                        for element in elements(generator.iter):
                            if isinstance(element, ast.Constant):
                                keep(element.value, "comprehension", node)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and any(holds_result(child) for child in ast.walk(node.args[0]))
            ):
                receiver = node.func.value
                table = receiver if isinstance(receiver, ast.Dict) else (
                    literal_dicts.get(receiver.id) if isinstance(receiver, ast.Name) else None
                )
                if isinstance(table, ast.Dict):
                    for key in table.keys:
                        if isinstance(key, ast.Constant):
                            keep(key.value, "mapping.get", node)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"startswith", "endswith"}
                and holds_result(node.func.value)
            ):
                for argument in node.args:
                    for element in elements(argument):
                        if isinstance(element, ast.Constant):
                            keep(element.value, "startswith", node)

    return SweptNeedles(
        by_text=found, functions=[fn.name for fn in functions], by_site=sites
    )


class NormalizedNeedleAlphabetTests(unittest.TestCase):
    """Cây kim phải viết bằng đúng bảng chữ mà bộ chuẩn hoá nhả ra.

    Họ lỗi này không dính gì tới ``đ``, nhưng chết cùng một kiểu im lặng.
    `_normalize_skill_token` đổi mọi ký tự ngoài ``[a-z0-9]`` thành ``_``,
    nên đầu ra không bao giờ có dấu cách; ai viết cây kim "thoi trang" như
    văn xuôi thì cây ấy chết vĩnh viễn. Ba cây từng hỏng ở đây:
    ``"thoi trang"``, ``"thuong hieu"`` (cả hai lỗi chảy thật) và
    ``"vỏ_gối"`` (vô hại vì ``vo_goi`` ngay cạnh phủ hết, nhưng làm người
    đọc sau tưởng bảng ấy nhận được kim có dấu).

    Điều khiến nó không thể phát hiện bằng mắt: **cùng chuỗi "thoi trang"
    lại viết ĐÚNG** ở ``POLICY_APPAREL_TERMS``, vì `_normalize_policy_text`
    giữ dấu cách. Một chuỗi y hệt, hai bảng chữ cái, một chỗ sống một chỗ
    chết. Nên câu hỏi không phải "cây kim này viết đúng không" mà là "nó
    đang so với bộ chuẩn hoá NÀO".
    """

    # Bộ chuẩn hoá → bảng chữ nó nhả ra. Đọc thẳng từ bước ``re.sub`` cuối
    # cùng của mỗi hàm.
    ALPHABETS = {
        "_normalize_skill_token": r"[a-z0-9_]*",
        "_normalize_prompt_source_header": r"[a-z0-9]*",
        "_compact_match_text": r"[a-z0-9]*",
    }

    def test_every_needle_uses_the_alphabet_its_normalizer_emits(self) -> None:
        """Đúng luật là **hợp ít nhất MỘT** bảng chữ nó thật sự bị đem so.

        Không phải "hợp bảng chữ của từng bộ chuẩn hoá gặp nó". Có chỗ cố ý
        so một cây kim với hai bộ cùng lúc —
        ``trigger in normalized or trigger in compact`` ở
        ``_erp_query_aliases`` — nên ``"tap_de"`` sai bảng chữ của
        `_compact_match_text` mà vẫn sống nhờ vế `normalized`. Bắt nó hợp cả
        hai là đòi một thứ code không cần, và sẽ đẩy người sửa sau đi xoá
        gạch dưới, tức là giết cây kim thật.
        """
        seen: dict[str, set[str]] = {}
        for normalizer in self.ALPHABETS:
            swept = needles_compared_with(normalizer)
            with self.subTest(normalizer=normalizer):
                self.assertTrue(swept.by_text, "quét rỗng thì test này vô nghĩa")
            for text in swept.by_text:
                seen.setdefault(text, set()).add(normalizer)

        wrong = {
            text: sorted(normalizers)
            for text, normalizers in seen.items()
            if not any(
                re.fullmatch(self.ALPHABETS[normalizer], text) for normalizer in normalizers
            )
        }
        self.assertEqual({}, wrong)

    def test_a_needle_compared_with_two_normalizers_needs_only_one_alphabet(self) -> None:
        """Ghim chính nhóm khiến luật phải nới, kèm bằng chứng nó sống.

        Bảng ``alias_groups`` cố ý viết cặp: dạng có gạch dưới cho
        `_normalize_skill_token`, dạng liền cho `_compact_match_text`.
        """
        svc = service()
        skill = needles_compared_with("_normalize_skill_token").by_text
        compact = needles_compared_with("_compact_match_text").by_text

        for underscored, joined, typed in (
            ("tap_de", "tapde", "tạp dề"),
            ("gau_bong", "gaubong", "gấu bông"),
            ("bup_be", "bupbe", "búp bê"),
            ("ao_tre_em", "aotreem", "áo trẻ em"),
        ):
            with self.subTest(needle=underscored):
                self.assertIn(underscored, skill)
                self.assertIn(underscored, compact)
                self.assertNotRegex(underscored, r"^[a-z0-9]*$")
                self.assertIn(underscored, svc._normalize_skill_token(typed))
                self.assertIn(joined, svc._compact_match_text(typed))

    def test_the_same_string_is_correct_for_the_other_normalizer(self) -> None:
        # Nhóm đối chứng, và là lý do không thể sửa bằng cách cấm dấu cách
        # ở mọi nơi: `_normalize_policy_text` GIỮ dấu cách, nên "thoi trang"
        # ở bảng policy là đúng và phải tiếp tục khớp.
        svc = service()

        self.assertIn("thoi trang", svc._normalize_policy_text("ảnh thời trang nữ"))
        self.assertNotIn("thoi trang", svc._normalize_skill_token("ảnh thời trang nữ"))
        self.assertIn("thoi_trang", svc._normalize_skill_token("ảnh thời trang nữ"))

    def test_the_policy_tables_use_the_alphabet_that_normalizer_emits(self) -> None:
        # Chiều ngược lại của cùng một họ lỗi. `_normalize_policy_text` kết
        # bằng ``[^a-zA-Z0-9\s] -> " "`` rồi gộp khoảng trắng, nên nó nhả ra
        # ``[a-z0-9 ]``: mục nào có gạch dưới hay còn dấu là chết vĩnh viễn.
        # Ba bảng POLICY_* là hằng lớp nên đọc thẳng, không cần quét AST.
        svc = service()
        terms = set(svc.POLICY_MINOR_TERMS)
        terms |= set(svc.POLICY_APPEARANCE_TERMS)
        terms |= set(svc.POLICY_APPAREL_TERMS)

        self.assertTrue(terms, "quét rỗng thì test này vô nghĩa")
        self.assertEqual([], sorted(t for t in terms if not re.fullmatch(r"[a-z0-9 ]*", t)))


class PromptSourceHeaderTests(unittest.TestCase):
    """Cột "Đã dùng" của bảng tính phải nhận ra được."""

    def test_the_used_column_is_found_when_named_in_vietnamese(self) -> None:
        svc = service()
        candidates = {"used", "done", "completed", "generated", "processed", "dadung", "dungroi", "xong"}

        self.assertEqual("Đã dùng", svc._find_prompt_source_column(["Prompt", "Đã dùng"], candidates))

    def test_the_two_sibling_spellings_still_work(self) -> None:
        # "dungroi"/"xong" không có đ nên chúng vẫn sống ngay cả khi chưa gấp —
        # đó là lý do cột "Đã dùng" hỏng một mình mà không ai thấy.
        svc = service()
        candidates = {"dadung", "dungroi", "xong"}

        self.assertEqual("Dùng rồi", svc._find_prompt_source_column(["Prompt", "Dùng rồi"], candidates))
        self.assertEqual("Xong", svc._find_prompt_source_column(["Prompt", "Xong"], candidates))

    def test_folding_does_not_invent_truthy_values(self) -> None:
        # Chiều ngược lại: gấp ``đ`` không được biến "Đóng"/"Đã huỷ" thành bật.
        svc = service()

        self.assertTrue(svc._truthy_sheet_value("Có"))
        self.assertFalse(svc._truthy_sheet_value("Đóng"))
        self.assertFalse(svc._truthy_sheet_value("Đã huỷ"))
        self.assertIsNone(svc._config_bool("Đúng", default=None))


class PromptSourceHeaderClosedSetTests(unittest.TestCase):
    """Đếm trên tập đóng: bảng khoá cột có bao nhiêu mục chết vì ``đ``.

    Năm hàm dưới đây là toàn bộ chỗ so kết quả của
    ``_normalize_prompt_source_header`` với một bảng khoá viết sẵn. Test
    dựng lại bảng khoá bằng cách đọc AST của chính service.py, nên thêm
    một khoá mới mà không phân loại nó là đỏ ngay — không phải chờ ai đó
    nhớ ra phải sửa test.
    """

    FUNCTIONS_HOLDING_THE_KEY_TABLES = frozenset(
        {
            "_table_rows_to_dicts",
            "_prompt_source_preview_payload",
            "_truthy_sheet_value",
            "_config_bool",
            "_find_prompt_source_column",
        }
    )
    # Khoá duy nhất có chữ ``d`` vốn là ``đ``, kèm câu người ta gõ ra nó.
    KEY_BORN_FROM_D_STROKE = {"dadung": "Đã dùng"}
    # Toàn bộ khoá có chữ ``d`` KHÔNG sinh ra từ ``đ``. Phải liệt kê tay:
    # nhìn vào chuỗi ASCII thì "daxong" và "index" giống hệt nhau, không có
    # cách máy móc nào tách được. Đổi lại, thêm bất kỳ khoá nào có ``d`` mà
    # không xếp vào một trong hai bảng là test đỏ, tức người thêm buộc phải
    # trả lời "chữ d này từ đâu ra".
    KEYS_WITH_A_REAL_D = frozenset(
        {
            # tiếng Việt, ``d`` thật — chính chúng là lý do cột "Đã dùng"
            # hỏng một mình mà không ai thấy.
            "dungroi",
            # tiếng Anh
            "card",
            "cardid",
            "cardurl",
            "completed",
            "disabled",
            "done",
            "enabled",
            "erpcard",
            "erpcardid",
            "erpcardurl",
            "erplistid",
            "generated",
            "index",
            "listid",
            "processed",
            "product",
            "productcode",
            "productid",
            "productkey",
            "productname",
            "producttitle",
            "promptindex",
            "sourcecard",
            "sourcecardurl",
            "used",
        }
    )

    def _key_tables(self) -> set[str]:
        source = Path(FlowWebService.__module__.replace(".", "/") + ".py")
        source = Path(__file__).resolve().parents[1] / source
        tree = ast.parse(source.read_text(encoding="utf-8"))
        keys: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name not in self.FUNCTIONS_HOLDING_THE_KEY_TABLES:
                continue
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Set):
                    continue
                values = [
                    element.value
                    for element in sub.elts
                    if isinstance(element, ast.Constant) and isinstance(element.value, str)
                ]
                if values and len(values) == len(sub.elts):
                    keys |= set(values)
        return keys

    def test_the_key_tables_are_found_at_all(self) -> None:
        # Chống rỗng: nếu AST không tìm thấy bảng nào thì mọi test dưới đây
        # xanh một cách vô nghĩa.
        keys = self._key_tables()

        self.assertGreater(len(keys), 40)
        self.assertIn("promptcontent", keys)

    def test_the_keys_holding_a_d_are_a_closed_set(self) -> None:
        keys = self._key_tables()
        with_d = {key for key in keys if "d" in key}

        self.assertEqual(with_d, set(self.KEY_BORN_FROM_D_STROKE) | self.KEYS_WITH_A_REAL_D)

    def test_the_one_d_stroke_key_is_reachable_from_what_a_person_types(self) -> None:
        svc = service()
        for key, typed in self.KEY_BORN_FROM_D_STROKE.items():
            for spelling in (typed, typed.lower(), typed.upper(), typed.title()):
                with self.subTest(typed=spelling):
                    self.assertEqual(key, svc._normalize_prompt_source_header(spelling))

    def test_no_key_was_written_to_match_the_broken_output(self) -> None:
        # Bẫy ngược: nếu ai đó từng "vá" bằng cách viết thẳng chuỗi hỏng
        # (``adung``) vào bảng thì bước gấp ``đ`` sẽ làm hỏng lại chỗ ấy.
        keys = self._key_tables()

        self.assertNotIn("adung", keys)


class SkillTokenClosedSetTests(unittest.TestCase):
    """Đếm bao nhiêu kim so khớp chết vì ``đ`` — tám, không phải ba.

    Chú thích trong `_normalize_skill_token` từng nêu tên ba khoá. Quét
    AST toàn bộ 33 hàm gọi hàm này thì ra 256 kim, 61 kim có chữ ``d``,
    và **tám** trong số đó sinh ra từ ``đ``. Ba khoá kia chỉ là ba khoá
    được nhớ tên, không phải cả tập.

    Năm mươi ba kim còn lại đã phân loại tay ngày 2026-08-20 và KHÔNG
    ghim ở đây: chúng là từ vựng sản phẩm (`wedding_hoop`,
    `stuffed_animal`, ...) còn đang mọc thêm, ghim vào chỉ tổ đỏ vặt.
    Hệ quả phải nói thẳng: **thêm một kim tiếng Việt có ``đ`` sẽ KHÔNG
    tự động bị bắt** — chỉ có tám kim dưới đây và các dạng hỏng của
    chúng là được canh.
    """

    FUNCTIONS_CALLING_THE_NORMALIZER = 33
    # Kim → câu người thật gõ ra nó. Ghim câu gõ, không ghim chuỗi đã
    # chuẩn hoá, để test còn đúng nếu bộ chuẩn hoá đổi cách viết.
    NEEDLES_BORN_FROM_D_STROKE = (
        ("bat_dau", "bắt đầu"),
        ("dieu_khien_flow", "điều khiển flow giúp tôi"),
        ("he_thong_tu_dong", "dùng hệ thống tự động"),
        ("chuyen_dong_camera", "chuyển động camera"),
        ("do_phan_giai", "độ phân giải"),
        ("dang_nhap", "đăng nhập"),
        ("dung", "đứng"),
        ("dem", "cảnh đêm"),
    )
    # Đúng những gì bộ chuẩn hoá nhả ra TRƯỚC bản vá. Không kim nào được
    # phép mang hình dạng này: có nghĩa là ai đó đã "vá" bằng cách chép
    # luôn chuỗi hỏng vào bảng, và bước gấp ``đ`` sẽ làm hỏng lại chỗ ấy.
    DAMAGED_SPELLINGS = (
        "bat_au",
        "ieu_khien_flow",
        "he_thong_tu_ong",
        "chuyen_ong_camera",
        "o_phan_giai",
        "ang_nhap",
    )

    def _needles(self) -> set[str]:
        needles = needles_compared_with("_normalize_skill_token")
        self.assertEqual(self.FUNCTIONS_CALLING_THE_NORMALIZER, len(needles.functions))
        return set(needles.by_text)

    def test_the_sweep_finds_the_needles_at_all(self) -> None:
        # Chống rỗng: quét hỏng thì mọi test dưới đây xanh vô nghĩa.
        needles = self._needles()

        self.assertGreater(len(needles), 200)
        self.assertIn("dieu_khien_flow", needles)

    def test_every_needle_born_from_d_stroke_is_still_a_needle(self) -> None:
        # Đổi tên hay bỏ một trong tám kim thì phải thấy ngay, vì các ca
        # đo dưới đây đứng trên đúng tám tên ấy.
        needles = self._needles()
        for needle, _typed in self.NEEDLES_BORN_FROM_D_STROKE:
            with self.subTest(needle=needle):
                self.assertIn(needle, needles)

    def test_every_needle_born_from_d_stroke_is_reachable(self) -> None:
        svc = service()
        for needle, typed in self.NEEDLES_BORN_FROM_D_STROKE:
            with self.subTest(needle=needle):
                self.assertIn(needle, svc._normalize_skill_token(typed))

    def test_no_needle_was_written_in_its_damaged_spelling(self) -> None:
        needles = self._needles()
        for damaged in self.DAMAGED_SPELLINGS:
            with self.subTest(damaged=damaged):
                self.assertNotIn(damaged, needles)


class SkillTokenIntentTests(unittest.TestCase):
    """Ba khoá ý định viết bằng ASCII, cả ba sinh ra từ chữ có ``đ``."""

    def test_dieu_khien_flow_asks_for_the_flow_operator(self) -> None:
        self.assertTrue(service()._flow_operator_requested("điều khiển flow giúp tôi"))

    def test_he_thong_tu_dong_asks_for_the_flow_operator(self) -> None:
        self.assertTrue(service()._flow_operator_requested("dùng hệ thống tự động"))

    def test_bat_dau_means_run_it(self) -> None:
        self.assertTrue(service()._flow_operator_wants_run("bắt đầu"))

    def test_an_unrelated_sentence_still_asks_for_nothing(self) -> None:
        svc = service()

        self.assertFalse(svc._flow_operator_requested("cho tôi xem ảnh của thẻ này"))
        self.assertFalse(svc._flow_operator_wants_run("để đó đã"))


class AutoErpStopSignalTests(unittest.TestCase):
    """Cả lưới dừng của Auto ERP, lấy bằng AST chứ không lấy bằng trí nhớ.

    Lưới này khớp **chuỗi con**, nên gỡ một mắt lưới là chuyện lặng lẽ: sửa
    câu chữ cho hay hơn — bỏ "trước khi bấm tạo", đổi "không dùng" thành
    "không có" — thì thẻ hỏng vì không kéo được ảnh nguồn lại kéo cả loạt
    chạy tiếp, không lỗi nào được ném ra. Ghim cả lưới chứ không ghim vài
    mẫu, vì mẫu chọn tay đã lừa được cả hai phiên làm việc này một lượt.

    Cách lấy: duyệt AST toàn bộ 251 chuỗi ``raise`` trong ``service.py``, giữ
    lại đúng những chuỗi làm hàm trả True. Hai điều KHÔNG được làm, đều đã
    từng làm và đều ra số sai:

    * đừng tự nghĩ ra câu cho khớp cây kim — nó đo trí nhớ, không đo code;
    * đừng ghim vế đầu của một câu dài hơn — vế sau thường chứa cây kim khác
      còn sống, cắt đi là tưởng mình vừa vá được một lỗ đang chảy.

    Đo trên toàn bộ 251 chuỗi: gấp ``đ`` ở hàm này đổi hành vi của **0** câu.
    Đúng một câu đổi (23970) và nó đổi nhờ cây kim hẹp ``chi gui prompt``.
    """

    # Chép bằng máy từ AST, không chép bằng tay. Chỗ ``{...}`` trong f-string
    # bị bỏ đi nên đuôi trông cụt — không sao, lưới khớp chuỗi con. Không ghi
    # số dòng: sửa một chú thích là số dòng mục ruỗng, chuỗi thì không.
    STOPPING_SET = (
        'Auto AI ERP bắt buộc dùng Tác nhân Flow. App chưa thấy nút Tác nhân trên màn hình Flow, nên đã dừng trước khi nhập lệnh để tránh tạo ảnh không dùng ảnh nguồn.',
        'Auto AI ERP cần mở panel Tác nhân Flow trước khi kéo ảnh vào AI. App đã dừng để tránh chỉ gửi prompt mà không có ảnh nguồn.',
        'Auto AI ERP chưa kéo/upload được ảnh ERP vào Tác nhân Flow. App đã dừng trước khi bấm tạo để tránh tạo ảnh không dùng ảnh nguồn. Chi tiết: ;',
        'Auto AI ERP chua xac minh duoc anh nguon trong panel Tac nhan Flow. App da dung truoc khi bam tao de tranh Flow Agent dung ngu canh/anh cu. Chi tiet:',
        'Flow vua gui request tao anh nhung request khong co anh goc dang chon. Em da dung lai de tranh luu anh moi khong dung card ERP.',
    )

    def test_every_raise_in_the_stopping_set_still_stops(self) -> None:
        svc = service()

        for detail in self.STOPPING_SET:
            with self.subTest(detail=detail[:60]):
                self.assertTrue(svc._auto_erp_should_stop_on_child_error(detail))

    def test_it_stops_when_the_source_image_never_arrived(self) -> None:
        self.assertTrue(service()._auto_erp_should_stop_on_child_error("Chưa kéo/upload được ảnh ERP cho thẻ này"))

    def test_it_stops_when_the_wrong_source_image_was_used(self) -> None:
        self.assertTrue(service()._auto_erp_should_stop_on_child_error("Không dùng ảnh nguồn"))

    def test_it_stops_when_every_profile_is_out_of_quota(self) -> None:
        self.assertTrue(service()._auto_erp_should_stop_on_child_error("Tất cả Chrome profile Flow đã hết quota"))

    def test_an_unlisted_error_does_not_stop_the_batch(self) -> None:
        svc = service()

        self.assertFalse(svc._auto_erp_should_stop_on_child_error("Một lỗi bất kỳ không nằm trong danh sách"))
        self.assertFalse(svc._auto_erp_waitable_empty_error("Một lỗi bất kỳ không nằm trong danh sách"))

    def test_an_empty_board_is_still_something_to_wait_for(self) -> None:
        self.assertTrue(service()._auto_erp_waitable_empty_error("Chưa tìm thấy card phù hợp"))


class AutoErpStopSignalWordingTests(unittest.TestCase):
    """Một cây kim lệch một từ, không dính gì tới chữ ``đ``.

    Thẻ báo "chỉ gửi prompt mà không CÓ ảnh nguồn", danh sách lại viết
    "không DÙNG ảnh nguồn". Ba câu raise khác đi tới hàm này đều đã dừng
    đúng nhờ cây kim khác che; riêng câu này không cây kim nào nhận, nên
    panel Tác nhân Flow không mở được mà cả loạt vẫn chạy tiếp.
    """

    def test_it_stops_when_the_agent_panel_never_opened(self) -> None:
        detail = (
            "Auto AI ERP cần mở panel Tác nhân Flow trước khi kéo ảnh vào AI. "
            "App đã dừng để tránh chỉ gửi prompt mà không có ảnh nguồn."
        )

        self.assertTrue(service()._auto_erp_should_stop_on_child_error(detail))

    def test_one_card_without_a_fresh_source_image_does_not_stop_the_batch(self) -> None:
        # Cây kim phải hẹp: đây là điều kiện của riêng một thẻ, thẻ sau vẫn
        # có thể chạy được, nên nó không được kéo theo cả loạt dừng.
        detail = "Card ERP này chỉ còn ảnh output cũ của Flow, không có ảnh nguồn mới để làm reference."

        self.assertFalse(service()._auto_erp_should_stop_on_child_error(detail))


class SkillFieldKeyTests(unittest.TestCase):
    """Ba khoá ASCII nữa sinh ra từ chữ có ``đ``, do phiên listing chỉ ra."""

    def test_do_phan_giai_is_the_resolution_field(self) -> None:
        self.assertEqual("do_phan_giai", service()._normalize_skill_token("Độ phân giải"))

    def test_dang_nhap_reaches_the_flow_answer(self) -> None:
        self.assertEqual("dang_nhap", service()._normalize_skill_token("đăng nhập"))

    def test_chuyen_dong_camera_is_a_camera_motion_skill(self) -> None:
        self.assertEqual("camera_motion", service()._parse_skill_type("chuyển động camera"))


class ProductRuleBothSidesNormalizedTests(unittest.TestCase):
    """Vì sao hai bảng luật sản phẩm KHÔNG dính họ lỗi "sai bảng chữ cái".

    Các bảng ở ``PRODUCT_SHOT_RULES`` và ở ``signatures`` bên trong
    ``_flow_operator_product_rule_key_from_visual_text`` chứa đầy cây kim
    có dấu cách (``"passport cover"``) và có dấu tiếng Việt
    (``"bọc passport"``). Ở mọi bảng khác trong repo, viết như vậy là kim
    chết — bộ chuẩn hoá phát ra ``[a-z0-9_]`` nên không chuỗi nào có dấu
    cách hay dấu thanh khớp được.

    Ở đây thì không, và lý do là cấu trúc chứ không phải may mắn: hai hàm
    ấy **chuẩn hoá cả hai phía** trước khi so, ``alias_normalized =
    self._normalize_skill_token(alias_text)``. Kim viết bằng chữ người đọc
    được, rồi mới được gấp về đúng bảng chữ cái ngay lúc so.

    Đó cũng là lý do lượt quét theo biến không quy được cây kim nào ở đây
    về ``_normalize_skill_token``: chúng không phải hằng đem so trực tiếp.
    Miễn nhiễm này mất đi lặng lẽ nếu có ai đem thẳng một hằng ra so với
    biến đã chuẩn hoá, nên ``test_no_product_rule_needle_is_compared_raw``
    canh đúng chỗ đó.
    """

    CONSUMERS = (
        "_flow_operator_card_name_product_rule_key",
        "_flow_operator_product_rule_key_from_text",
        "_flow_operator_product_rule_key_from_visual_text",
    )

    # Bốn bí danh này có khớp, nhưng luật đứng trước trong thứ tự ưu tiên
    # giành mất — ``album`` ở vị trí 15, ``guest_book`` ở 17, và ``album``
    # đã tự khai đúng bốn cách viết ấy. Đây là chuyện phân loại sản phẩm,
    # không phải kim chết; ghim lại để lần che khuất TIẾP THEO lộ ra.
    ALIASES_SHADOWED_BY_AN_EARLIER_RULE = {
        ("guest_book", "photo album", "album"),
        ("guest_book", "wedding photo album", "album"),
        ("guest_book", "fabric photo album", "album"),
        ("guest_book", "embroidered photo album", "album"),
    }

    def setUp(self) -> None:
        self.service = service()

    def _signature_terms(self) -> list[tuple[str, str, str]]:
        """Bảng ``signatures`` là biến cục bộ nên phải đọc bằng AST."""
        source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        terms: list[tuple[str, str, str]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name != "_flow_operator_product_rule_key_from_visual_text":
                continue
            for child in ast.walk(node):
                if not isinstance(child, ast.AnnAssign):
                    continue
                if getattr(child.target, "id", "") != "signatures":
                    continue
                for key, buckets in ast.literal_eval(child.value).items():
                    for bucket, values in buckets.items():
                        for value in values:
                            terms.append((key, bucket, value))
        return terms

    def _aliases(self) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        for key in PRODUCT_SHOT_RULE_PRIORITY:
            for alias in (PRODUCT_SHOT_RULES.get(key) or {}).get("aliases", ()):
                pairs.append((key, alias))
        return pairs

    def test_both_tables_are_found_at_all(self) -> None:
        """Sàn chống ca rỗng: đọc hụt bảng thì các ca dưới xanh vô nghĩa."""
        aliases = self._aliases()
        terms = self._signature_terms()
        self.assertEqual(len(PRODUCT_SHOT_RULE_PRIORITY), len(PRODUCT_SHOT_RULES))
        self.assertGreater(len(aliases), 400, "bảng bí danh đọc hụt")
        self.assertGreater(len(terms), 600, "bảng signatures đọc hụt")
        self.assertTrue(any(" " in alias for _, alias in aliases))
        self.assertTrue(any("ọ" in alias for _, alias in aliases))

    def test_no_product_rule_needle_is_compared_raw(self) -> None:
        """Hằng đem so thẳng với biến đã chuẩn hoá = miễn nhiễm đã mất."""
        swept = needles_compared_with("_normalize_skill_token")
        for consumer in self.CONSUMERS:
            self.assertIn(consumer, swept.functions, "hàm không còn gọi bộ chuẩn hoá")
        raw = {
            text: places
            for text, places in swept.by_text.items()
            if any(place.split(":", 1)[0] in self.CONSUMERS for place in places)
        }
        self.assertEqual({}, raw)

    def test_every_needle_survives_the_normalizer_it_is_folded_by(self) -> None:
        """Đo trên TẬP ĐÓNG: cả hai bảng, không lấy mẫu."""
        alphabet = re.compile(r"[a-z0-9_]*")
        needles = [alias for _, alias in self._aliases()]
        needles += [term for _, _, term in self._signature_terms()]
        for needle in needles:
            with self.subTest(needle=needle):
                folded = self.service._normalize_skill_token(needle)
                self.assertTrue(folded, "kim chuẩn hoá ra rỗng thì không khớp gì")
                self.assertRegex(folded, alphabet)
                self.assertTrue(self.service._compact_match_text(needle))

    def test_every_alias_finds_a_rule_from_its_own_text(self) -> None:
        """Gõ đúng chữ trong bảng mà không ra luật nào = kim chết."""
        shadowed = set()
        for key, alias in self._aliases():
            with self.subTest(rule=key, alias=alias):
                got = self.service._flow_operator_product_rule_key_from_text(alias)
                self.assertTrue(got, "không luật nào nhận")
                if got != key:
                    shadowed.add((key, alias, got))
        self.assertEqual(self.ALIASES_SHADOWED_BY_AN_EARLIER_RULE, shadowed)

    def test_the_family_is_bigger_than_the_three_rule_functions(self) -> None:
        """Sàn chống ca rỗng, và lời nhắc vì sao phải tự tìm họ.

        Tôi mở màn bằng ba hàm luật sản phẩm vì grep "passport" dẫn tới đó.
        Quét đúng hình dạng "gấp cả hai phía" thì ra **13** hàm — mười cái
        kia chưa từng ai soi. Danh sách chép tay mục ngay lúc viết.
        """
        family = {function.name for function in both_sides_folded_functions()}
        self.assertGreaterEqual(len(family), 13)
        self.assertTrue(set(self.CONSUMERS) <= family)
        self.assertIn("_erp_task_matches_query", family)
        self.assertIn("_flow_agent_text_matches_terms", family)

    def test_the_folding_helpers_really_fold(self) -> None:
        """``FOLDING_HELPERS`` do người viết, nên phải có chỗ canh nó mục.

        Nhận sai một tên vào đây là tự tay tắt ca ghép-đôi cho mọi biến ăn
        kết quả của nó. Tính chất cần đúng: **mọi thứ hàm ấy có thể trả về
        đều nằm trong bảng chữ đã gấp** — hoặc vì nó được gấp, hoặc vì nó
        được viết sẵn bằng đúng bảng chữ ấy.

        Đừng canh bằng "hàm này có gấp gì không": ``_erp_query_aliases``
        thoả điều đó (nó gấp để khử trùng lặp) mà vẫn trả về chữ có dấu
        cách. Nó là nhóm đối chứng ở dưới.
        """
        source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        seen = {
            function.name: function
            for function in ast.walk(tree)
            if isinstance(function, ast.FunctionDef)
        }
        emitted = re.compile(r"[a-z0-9]*")

        def literals(function: ast.FunctionDef) -> list[str]:
            return sorted(
                {
                    node.value
                    for node in ast.walk(function)
                    if isinstance(node, ast.Constant) and isinstance(node.value, str)
                }
            )

        for helper in FOLDING_HELPERS:
            with self.subTest(helper=helper):
                self.assertIn(helper, seen, "tên trong danh sách không còn là hàm nào")
                function = seen[helper]
                self.assertTrue(
                    any(
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr in FOLDERS
                        for node in ast.walk(function)
                    ),
                    "hàm này không hề gấp gì",
                )
                self.assertEqual(
                    [],
                    [text for text in literals(function) if not emitted.fullmatch(text)],
                    "có hằng viết ngoài bảng chữ đã gấp lọt được ra ngoài",
                )

    def test_a_function_that_folds_inside_is_not_a_folding_helper(self) -> None:
        """Nhóm đối chứng sống: chứng minh ca trên phân biệt được thật.

        ``_erp_query_aliases`` gấp bên trong nhưng trả về ``cleaned`` — còn
        nguyên dấu cách. Nếu ca trên chỉ hỏi "có gấp không" thì hàm này lọt,
        và tôi đã suýt nhận nó vào danh sách.
        """
        source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        control = next(
            function
            for function in ast.walk(tree)
            if isinstance(function, ast.FunctionDef) and function.name == "_erp_query_aliases"
        )

        self.assertNotIn("_erp_query_aliases", FOLDING_HELPERS)
        self.assertTrue(
            any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in FOLDERS
                for node in ast.walk(control)
            ),
            "nhóm đối chứng phải THOẢ tiêu chí yếu, nếu không nó không chứng minh gì",
        )
        spaced = [
            node.value
            for node in ast.walk(control)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and " " in node.value
        ]
        self.assertTrue(spaced, "không còn hằng có dấu cách thì đối chứng hết tác dụng")

    def test_the_needle_side_is_folded_before_every_comparison(self) -> None:
        """Nửa một: không phép so nào một phía đã gấp mà phía kia thì chưa.

        Quét cả HỌ tự tìm được, không riêng ba hàm luật sản phẩm. Ba bộ gấp
        phía kim dư thừa cho nhau nên bỏ một cái vẫn không ca hành vi nào
        đỏ — đo rồi, không đoán.
        """
        checked = 0
        for function in both_sides_folded_functions():
            folded = folded_names(function)
            literals = literal_loop_names(function)

            def side(node: ast.AST) -> str:
                if isinstance(node, ast.Name) and node.id in folded:
                    return "folded"
                if isinstance(node, ast.Name) and node.id not in literals:
                    return "raw"
                return "other"

            pairs: list[tuple[ast.expr, ast.expr]] = []
            for node in ast.walk(function):
                if isinstance(node, ast.Compare) and any(
                    isinstance(op, (ast.In, ast.NotIn, ast.Eq)) for op in node.ops
                ):
                    for right in node.comparators:
                        pairs.append((node.left, right))
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"issubset", "issuperset"}
                    and node.args
                ):
                    pairs.append((node.func.value, node.args[0]))

            for left, right in pairs:
                kinds = {side(left), side(right)}
                if "folded" not in kinds:
                    continue
                checked += 1
                with self.subTest(function=function.name, line=getattr(left, "lineno", 0)):
                    self.assertNotIn(
                        "raw",
                        kinds,
                        f"{ast.unparse(left)} <-> {ast.unparse(right)}: "
                        "một phía đã gấp, phía kia chưa — kim không bao giờ khớp",
                    )

        self.assertGreaterEqual(checked, 60, "không quét trúng phép so nào")

    def test_no_folded_needle_is_left_unread(self) -> None:
        """Nửa thứ hai: biến đã gấp mà không còn ai đọc = một mắt lưới vừa chết.

        Ca ghép-đôi ở trên chỉ soi phép so CÒN SỐNG. Xoá hẳn một nhánh thì
        không còn phép so nào để soi, mà dòng gấp vẫn nằm đó trơ ra — đo
        rồi: ba đột biến "xoá hẳn nhánh" đều xanh dưới ca ghép-đôi. Phiên
        listing đo độc lập ở nửa họ và ra cùng kết quả.

        "Được đọc" phải là **mọi lần đọc biến**, đừng thu hẹp thành "làm
        toán hạng của phép so": ``term_tokens`` chỉ xuất hiện ở
        ``len(term_tokens) == 1``, định nghĩa hẹp biến nó thành mồ côi giả
        ngay ở bản sạch.
        """
        orphans: list[tuple[str, str, int]] = []
        checked = 0
        for function in both_sides_folded_functions():
            reads: set[str] = {
                node.id
                for node in ast.walk(function)
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
            }
            for node in ast.walk(function):
                if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                    continue
                target = node.targets[0]
                if not isinstance(target, ast.Name):
                    continue
                if not any(
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute)
                    and child.func.attr in FOLDERS
                    for child in ast.walk(node.value)
                ):
                    continue
                checked += 1
                if target.id not in reads:
                    orphans.append((function.name, target.id, node.lineno))

        self.assertGreaterEqual(checked, 40, "không quét trúng chỗ gấp nào")
        self.assertEqual([], orphans)

    def test_a_spaced_and_an_accented_needle_both_route(self) -> None:
        """Chứng cứ sống cho việc phía KIM cũng được gấp, không riêng phía kia."""
        for typed in ("Passport Cover", "boc passport", "bọc hộ chiếu thêu tay"):
            with self.subTest(typed=typed):
                self.assertEqual(
                    "passport_cover",
                    self.service._flow_operator_product_rule_key_from_text(typed),
                )


if __name__ == "__main__":
    unittest.main()


class SweepReachTests(unittest.TestCase):
    """Ghim TẦM VỚI của chính lượt quét, không chỉ kết quả nó trả về.

    Mọi test bảng chữ cái ở trên đều đọc "0 vi phạm" là xanh. Nhưng lượt
    quét hỏng cũng trả về 0 vi phạm — y hệt. Đó không phải giả thuyết: hình
    dạng kim thứ SÁU (``normalized in generic_exact``, tập hằng gán vào biến
    rồi mới đem so) đã giấu 25 cây kim ở hai hàm suốt thời gian bảng chữ cái
    báo sạch, và trồng một cây kim sai bảng chữ vào đúng hai tập ấy thì cả
    bộ test vẫn xanh trơn. Nên phải đo được rằng lượt quét CÓ nhìn thấy
    những chỗ nó tự nhận là đã nhìn.
    """

    # Sàn đo ngày 2026-08-20. Là SÀN chứ không phải con số chính xác: thêm
    # cây kim mới vào service.py là chuyện thường, mất cây kim thì không.
    FLOOR_NEEDLES = {
        "_normalize_skill_token": 284,
        "_normalize_prompt_source_header": 18,
        "_compact_match_text": 42,
    }
    FLOOR_FUNCTIONS = {
        "_normalize_skill_token": 33,
        "_normalize_prompt_source_header": 4,
        "_compact_match_text": 20,
    }
    # (bộ chuẩn hoá, hình dạng) → số ĐIỂM kim tối thiểu. Chia theo hình dạng
    # mới bắt được ca "hình dạng A chết trong khi hình dạng B mọc thêm", vì
    # tổng vẫn tăng.
    FLOOR_SHAPES = {
        ("_normalize_skill_token", "comprehension"): 263,
        ("_normalize_skill_token", "loop-var"): 305,
        ("_normalize_skill_token", "compare"): 32,
        ("_normalize_skill_token", "mapping.get"): 58,
        ("_normalize_skill_token", "named-set"): 25,
        ("_normalize_prompt_source_header", "compare"): 26,
        ("_compact_match_text", "compare"): 7,
        ("_compact_match_text", "loop-var"): 40,
        ("_compact_match_text", "comprehension"): 20,
    }
    # Hình dạng lượt quét biết đọc nhưng **flow-v2 (nửa làm ảnh)** không có
    # chỗ nào dùng. Ghi kèm TÊN REPO chứ đừng ghim trống: nửa listing đo bên
    # họ ra 2 chỗ thật (``normalized.startswith("auto_erp_etsy")`` và
    # ``"auto_erp_amazon"``), nên "chưa có chỗ như thế" là kết luận riêng của
    # repo này, không phải tính chất của hình dạng. Đo được 0 chỗ gọi
    # ``.startswith``/``.endswith`` trên giá trị đã gấp, trên cả sáu bộ
    # chuẩn hoá của ``flow_web/service.py``. "0 cây kim" ở đây nghĩa là "repo
    # này chưa có chỗ nào như thế", không phải "hình dạng này chạy tốt".
    SHAPES_WITH_NO_SITE_HERE = {"startswith"}

    @staticmethod
    def _shape_counts(normalizer: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for wheres in needles_compared_with(normalizer).by_text.values():
            for where in wheres:
                counts[where.rsplit(":", 1)[1]] = counts.get(where.rsplit(":", 1)[1], 0) + 1
        return counts

    def test_the_sweep_still_reaches_as_far_as_it_did(self) -> None:
        for normalizer, floor in self.FLOOR_NEEDLES.items():
            with self.subTest(normalizer=normalizer):
                swept = needles_compared_with(normalizer)
                self.assertGreaterEqual(len(swept.by_text), floor)
                self.assertGreaterEqual(
                    len(swept.functions), self.FLOOR_FUNCTIONS[normalizer]
                )

    def test_no_needle_shape_quietly_stops_firing(self) -> None:
        for (normalizer, shape), floor in self.FLOOR_SHAPES.items():
            with self.subTest(normalizer=normalizer, shape=shape):
                self.assertGreaterEqual(self._shape_counts(normalizer).get(shape, 0), floor)

    def test_a_shape_with_no_site_here_is_recorded_as_such(self) -> None:
        """Ghim đúng cái mình KHÔNG đo được, để lần sau khỏi tưởng đã đo."""
        fired = set()
        for normalizer in self.FLOOR_NEEDLES:
            fired |= set(self._shape_counts(normalizer))
        self.assertEqual(set(), fired & self.SHAPES_WITH_NO_SITE_HERE)

        source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        sites = []
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            holders = folded_names(function)
            for node in ast.walk(function):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"startswith", "endswith"}
                ):
                    continue
                receiver = node.func.value
                if isinstance(receiver, ast.Name) and receiver.id in holders:
                    sites.append(f"{function.name}:{node.lineno}")
                elif (
                    isinstance(receiver, ast.Call)
                    and isinstance(receiver.func, ast.Attribute)
                    and receiver.func.attr in FOLDERS
                ):
                    sites.append(f"{function.name}:{node.lineno}")
        self.assertEqual([], sites, "có chỗ dùng rồi thì phải bỏ khỏi danh sách 'chưa có chỗ'")

    def test_every_folding_function_is_either_swept_or_explained(self) -> None:
        """Phân hoạch: hàm nào gấp mà lượt quét không thấy cây kim nào?

        Ba khả năng, và chỉ một là lành: (1) hàm thuộc họ gấp-cả-hai-vế nên
        kim của nó là biến chứ không phải hằng; (2) hàm chỉ so hai giá trị
        đã gấp với nhau, không có hằng nào để mà quét; (3) lượt quét thủng.
        Không có test này thì (3) đội lốt (2) và không ai biết.
        """
        source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        family = {function.name for function in both_sides_folded_functions()}

        swept: set[str] = set()
        for normalizer in self.FLOOR_NEEDLES:
            for wheres in needles_compared_with(normalizer).by_text.values():
                swept |= {where.rsplit(":", 1)[0] for where in wheres}

        blind = []
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            folds = [
                node
                for node in ast.walk(function)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in FOLDERS
            ]
            if len(folds) < 2 or function.name in family or function.name in swept:
                continue
            # Lý do (2) phải TỰ kiểm chứ không phải danh sách miễn trừ chép
            # tay: hàm được tha đúng khi trong nó không có hằng chuỗi nào
            # nằm ở một phép so. Ai thêm cây kim vào đó thì mất quyền tha.
            literals = [
                element.value
                for node in ast.walk(function)
                if isinstance(node, ast.Compare)
                for part in [node.left, *node.comparators]
                for element in ast.walk(part)
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            ]
            # …và bảng hằng nằm NGOÀI hàm cũng tính là cây kim. Đo được 0
            # chỗ như thế hôm nay, nhưng repo có sẵn 90 bảng hằng mức lớp:
            # để nguyên thì hình dạng thứ BẢY chỉ cần một dòng mới là lọt,
            # và nó sẽ lọt dưới danh nghĩa "hàm này không có hằng nào".
            for node in ast.walk(function):
                if not isinstance(node, ast.Compare):
                    continue
                parts = [node.left, *node.comparators]
                if not any(
                    isinstance(part, ast.Name) and part.id in folded_names(function)
                    for part in parts
                ):
                    continue
                for part in parts:
                    box = outer_literal_boxes().get(box_name(part))
                    if box:
                        literals.extend(sorted(box)[:5])
            if literals:
                blind.append(f"{function.name} -> {sorted(set(literals))[:5]}")
        self.assertEqual([], blind)


class DiacriticFoldBoundaryTests(unittest.TestCase):
    """Sáu bộ chuẩn hoá KHÔNG xử lý chữ ``đ`` giống nhau, và đó là cố ý.

    Ba bộ gấp ``đ`` → ``d``. Hai bộ **XOÁ HẲN** nó: ``_compact_match_text``
    và ``_tokenize_match_words`` biến ``"đầm"`` thành ``"am"``, ``"đồ"``
    thành ``"o"``. Không phải "chưa gấp" mà là mất chữ.

    Vì sao test bảng chữ cái ở trên không bao giờ thấy: cây kim ``"dam"``
    hợp lệ hoàn hảo với ``[a-z0-9]``. Nó chỉ chết lúc chạy, khi đem so với
    ``"am"``. Đây là họ lỗi khác — sai NGỮ NGHĨA chứ không sai lớp ký tự —
    nên phải đo riêng.

    **Đo trên tập đóng của repo này** (không chép kết luận của nửa listing):
    4768 hằng chuỗi trong ``service.py``, 654 hằng có chữ ``đ``, đối chiếu
    với 42 cây kim so bằng `_compact_match_text` → **21 cặp đổi kết quả**
    nếu bắt `_compact_match_text` gấp ``đ``. Cả 21 đều là **đụng chuỗi con
    trong văn xuôi** — các hằng ấy là câu thông báo cho người dùng, không
    phải cây kim sản phẩm. Không cây kim sản phẩm nào đổi phân loại.

    **Nên KHÔNG đổi hành vi, chỉ ghim.** Đổi để "cho nhất quán" là đánh đổi
    một khác biệt vô hại lấy rủi ro trên đường chạy thật.
    """

    # BA hành vi, không phải hai. Gộp KEEPS vào "không gấp" là để người đọc
    # sau lướt thành "chỉ mất dấu thôi" — trong khi DELETES là mất hẳn con chữ.
    KEEPS_D = ("_strip_accents",)
    FOLDS_D = ("_normalize_skill_token", "_normalize_prompt_source_header", "_normalize_policy_text")
    DELETES_D = ("_compact_match_text", "_tokenize_match_words")

    def test_the_boundary_is_where_it_is_recorded_to_be(self) -> None:
        svc = service()
        for name in self.KEEPS_D:
            with self.subTest(normalizer=name, side="giữ"):
                # Bỏ dấu nhưng KHÔNG đụng tới ``đ``: "đồng hồ" → "đong ho".
                self.assertEqual("đ", getattr(svc, name)("đ"))
                self.assertEqual("đong ho", getattr(svc, name)("đồng hồ"))
        for name in self.FOLDS_D:
            with self.subTest(normalizer=name, side="gấp"):
                self.assertEqual("d", getattr(svc, name)("đ"))
        for name in self.DELETES_D:
            with self.subTest(normalizer=name, side="xoá"):
                result = getattr(svc, name)("đ")
                self.assertEqual([] if isinstance(result, list) else "", result)

    def test_a_d_word_reaches_the_two_alphabets_differently(self) -> None:
        """Cùng một từ, hai chính tả cây kim. Viết nhầm là kim chết câm."""
        svc = service()
        for typed, skill_form, compact_form in (
            ("đầm", "dam", "am"),
            ("đồ", "do", "o"),
            ("đá", "da", "a"),
            ("đèn", "den", "en"),
        ):
            with self.subTest(word=typed):
                self.assertEqual(skill_form, svc._normalize_skill_token(typed))
                self.assertEqual(compact_form, svc._compact_match_text(typed))
                # Đây mới là câu quan trọng: viết "dam" rồi đem so với
                # `_compact_match_text` thì KHÔNG BAO GIỜ khớp "đầm".
                self.assertNotIn(skill_form, svc._compact_match_text(typed))

    def test_the_live_d_needle_is_not_affected(self) -> None:
        """Nhóm đối chứng: ``tạp dề`` có chữ ``d`` THƯỜNG, không phải ``đ``.

        Không có nó thì test trên đọc như "mọi cây kim có chữ d đều nguy",
        và người sửa sau sẽ đi xoá ``tapde`` — một cây kim đang sống.
        """
        svc = service()
        self.assertNotIn("đ", "tạp dề")
        self.assertEqual("tapde", svc._compact_match_text("tạp dề"))
        self.assertEqual("tap_de", svc._normalize_skill_token("tạp dề"))

    def test_no_product_needle_would_change_if_compact_folded_d(self) -> None:
        """Đo lại tập đóng mỗi lần chạy, đừng tin con số 21 đã chép."""
        svc = service()
        source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        constants = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.strip()
        }
        needles = set(needles_compared_with("_compact_match_text").by_text)

        product_needle_changed = []
        for text in sorted(constant for constant in constants if "đ" in constant.lower()):
            now = svc._compact_match_text(text)
            folded = svc._compact_match_text(text.replace("đ", "d").replace("Đ", "D"))
            if now == folded:
                continue
            for needle in needles:
                if (needle in now) == (needle in folded):
                    continue
                # Phân biệt máy móc: hằng có dấu cách là câu văn xuôi, đụng
                # chuỗi con ở đó không định tuyến gì cả. Hằng là một token
                # trơn mà đổi phân loại thì mới là cây kim sản phẩm.
                if " " not in text.strip():
                    product_needle_changed.append(f"{needle!r} <- {text!r}")
        self.assertEqual([], product_needle_changed)


class UnderscoreTwinTests(unittest.TestCase):
    """Kim có ``_`` mà bị đo bằng bảng chữ không cho ``_`` thì phải có bản viết liền.

    Bảng ``alias_groups`` cố ý gõ tay từng cặp: ``tap_de`` cho
    `_normalize_skill_token`, ``tapde`` cho `_compact_match_text`, rồi so
    bằng ``or``. Hôm nay đủ cả 5 cặp — nhưng "hôm nay đủ" không phải là một
    cái lưới. Chiều nguy hiểm là **thêm kim mới**: gõ ``vo_goi`` mà quên
    ``vogoi`` thì vế compact chết câm, và test bảng chữ cái vẫn xanh vì
    ``vo_goi`` hợp lệ với `_normalize_skill_token`.

    **Vì sao không viết thành test ĐẾM.** Đếm cũng đỏ, nhưng đỏ với lời
    "22 != 21" — và câu đó dẫn người sửa đi sửa CON SỐ, còn cặp thì thiếu
    vĩnh viễn. Test này phải gọi đúng tên cây kim còn thiếu.

    Tập "bảng chữ không cho gạch dưới" **suy ra** từ ``ALPHABETS`` chứ
    không gõ tay: thêm một bộ chuẩn hoá mới là nó tự vào diện kiểm.
    """

    @staticmethod
    def _alphabets_without_underscore() -> list[str]:
        return [
            normalizer
            for normalizer, alphabet in NormalizedNeedleAlphabetTests.ALPHABETS.items()
            if not re.fullmatch(alphabet, "a_b")
        ]

    def test_the_derived_set_is_not_empty(self) -> None:
        """Không có câu này thì cả lớp test dưới vô nghĩa mà vẫn xanh."""
        derived = self._alphabets_without_underscore()
        self.assertIn("_compact_match_text", derived)
        self.assertNotIn("_normalize_skill_token", derived)

    def test_every_underscored_needle_has_a_joined_twin(self) -> None:
        """Đôi phải nằm ở CHÍNH CHỖ SO ấy, không phải đâu đó trong repo.

        Đây là chỗ tôi đã sai một lần: bản đầu soi toàn repo, nên trồng
        ``vo_goi`` vào ``_erp_query_aliases`` mà bộ test vẫn xanh — vì
        ``vogoi`` có sẵn ở ``_flow_operator_card_product_signals``. Cây kim
        ở hàm khác **không cứu được** vế ``compact`` của phép so này. Lúc ấy
        tôi kết luận "đột biến trồng hỏng"; thật ra đột biến đúng, phạm vi
        bất biến mới là chỗ hỏng.

        Gom theo dòng nên hai vế ``x in normalized or x in compact`` được
        tính là MỘT chỗ — đúng như code định làm.
        """
        missing = []
        for normalizer in self._alphabets_without_underscore():
            missing.extend(
                f"{report} thì {normalizer} mới khớp được"
                for report in missing_twins(needles_compared_with(normalizer).by_site)
            )
        self.assertEqual([], missing)

    def test_the_per_site_scope_is_what_catches_it(self) -> None:
        """Chứng minh PHẠM VI gánh việc, bằng dữ liệu bịa chứ không bằng cây thật.

        Đo trên cây hiện tại thì cả ba phạm vi (toàn repo / từng hàm / từng
        chỗ so) đều 0 vi phạm. Dừng ở đó sẽ ra kết luận dễ chịu "siết cũng
        thế thôi" — nhưng **trùng kết quả trên cây sạch là điều kiện cần,
        không phải điều kiện đủ**. Muốn biết phạm vi nào mạnh hơn thì phải
        có ca mà chỉ phạm vi chặt bắt được.

        Ca ấy đây: cùng một hàm, kim gạch dưới ở chỗ so này, bản viết liền ở
        chỗ so kia. Gộp theo hàm thì "đủ đôi"; theo chỗ so thì vế ``compact``
        của chỗ thứ nhất chết câm.
        """
        scattered = {"f:1": {"tap_de"}, "f:2": {"tapde"}}
        self.assertEqual([], missing_twins({"f:1": {"tap_de", "tapde"}}))
        self.assertEqual(
            [], missing_twins({"f:0": set().union(*scattered.values())}),
            "gộp theo hàm thì ca này lọt — đó chính là điều cần chứng minh",
        )
        reports = missing_twins(scattered)
        self.assertEqual(1, len(reports))
        self.assertIn("f:1", reports[0])
        self.assertIn("tapde", reports[0])

    FLOOR_DISTINGUISHING_FUNCTIONS = {
        "_compact_match_text": 3,
        "_normalize_prompt_source_header": 1,
    }

    def test_the_tree_really_has_room_for_that_to_happen(self) -> None:
        """Ca bịa ở trên ghim LUẬT; câu này ghim DỮ LIỆU ĐƯA VÀO luật.

        Hai lỗ khác nhau. Ca bịa gọi thẳng ``missing_twins`` nên ai dồn các
        chỗ so lại **ở chỗ gọi** — trước khi dữ liệu tới luật — thì hàm
        thuần vẫn nguyên vẹn và ca bịa vẫn xanh, trong khi phạm vi chặt đã
        chết. Đo thật trên cây này, gộp khoá chỗ so theo dải dòng:

            nguyên  //10  //100  //1000
              3       2      0      0    _compact_match_text
              1       1      0      0    _normalize_prompt_source_header

        Nên mốc phải là CON SỐ chứ không phải "có hay không": dồn theo //10
        làm hụt một phần ba mà câu hỏi có-hay-không vẫn xanh. Mốc dưới đây
        bắt được //10 ở cột compact.

        Giới hạn ghi rõ: cột header chỉ có 1 hàm phân biệt được, nên mốc 1
        ở đó chỉ bắt được lượt dồn sạch, không bắt được dồn nhẹ. Đó là số
        đo của cây hiện tại, không phải chỗ để nâng bừa cho đẹp.
        """
        for normalizer in self._alphabets_without_underscore():
            sites = needles_compared_with(normalizer).by_site
            by_function: dict[str, set[frozenset]] = {}
            for site, needles in sites.items():
                by_function.setdefault(site.rsplit(":", 1)[0], set()).add(frozenset(needles))
            spread = [name for name, groups in by_function.items() if len(groups) > 1]
            with self.subTest(normalizer=normalizer):
                self.assertGreaterEqual(
                    len(spread),
                    self.FLOOR_DISTINGUISHING_FUNCTIONS[normalizer],
                    f"{normalizer}: số hàm có hai chỗ so khác tập kim tụt xuống "
                    f"{sorted(spread)} — nhiều khả năng khoá chỗ so vừa bị dồn "
                    f"ở chỗ gọi, chứ luật cặp thì vẫn xanh",
                )

    def test_both_halves_of_each_pair_really_route(self) -> None:
        """Bằng chứng sống, không chỉ đối xứng chính tả.

        Không có nhóm này thì luật trên đọc như trò chơi chuỗi ký tự, và
        người sửa sau có thể "sửa" bằng cách bịa ra bản viết liền cho một
        cây kim mà không bộ chuẩn hoá nào từng nhả ra nó.
        """
        svc = service()
        for underscored, joined, typed in (
            ("tap_de", "tapde", "tạp dề"),
            ("gau_bong", "gaubong", "gấu bông"),
            ("bup_be", "bupbe", "búp bê"),
            ("ao_tre_em", "aotreem", "áo trẻ em"),
            ("baby_doll", "babydoll", "baby doll"),
        ):
            with self.subTest(pair=underscored):
                self.assertEqual(underscored, svc._normalize_skill_token(typed))
                self.assertEqual(joined, svc._compact_match_text(typed))
