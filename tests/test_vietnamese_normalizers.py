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


MARKS_OF_A_COMPARISON = (
    " in ", "==", "!=", "<=", ">=", ".startswith(", ".endswith(",
    ".get(", ".issubset(", ".issuperset(", "any(", "all(",
)


def sites_pointing_nowhere(by_site: dict[str, set[str]], lines: list[str]) -> list[str]:
    """Khoá chỗ so nào không trỏ vào một dòng có phép so thật.

    Trả **lời báo**, không ném: khoá cong là chuyện phải BÁO, không phải
    chuyện làm đổ lượt kiểm. Ba dạng cong đã gặp thật: mất hẳn số dòng,
    số dòng không phải chữ số (``True`` in ra thành ``"True"``), và số
    dòng nằm ngoài file.
    """
    reports = []
    for site in sorted(by_site):
        _, number = parse_site(site)
        if number is None:
            reports.append(f"{site}: khoá chỗ so không còn mang số dòng")
            continue
        if not 0 < number <= len(lines):
            reports.append(f"{site}: số dòng nằm ngoài file ({len(lines)} dòng)")
            continue
        text = lines[number - 1]
        if not any(mark in text for mark in MARKS_OF_A_COMPARISON):
            reports.append(f"{site} trỏ vào {text.strip()[:60]!r}")
    return reports


def parse_site(site: str) -> tuple[str, int | None]:
    """Đọc khoá chỗ so. **Một** bản cài đặt cho mọi luật dùng nó.

    Hai luật cùng bóc khoá là hai bản cài đặt có thể lệch nhau — đúng cái
    bẫy làm mốc ``paired`` bên nửa listing đánh rơi bộ lọc.
    """
    name, colon, tail = site.rpartition(":")
    if not colon or not tail.isdigit():
        return site, None
    return name, int(tail)


@lru_cache(maxsize=1)
def function_line_ranges() -> dict[str, tuple[tuple[int, int], ...]]:
    """Tên hàm → các khoảng dòng của thân hàm ấy trong service.py.

    Dựng riêng từ AST, không dùng lại số nào của bước ghi chỗ so, nên hai
    đường suy ra soi lẫn nhau chứ không cùng sai một kiểu.
    """
    source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
    ranges: dict[str, list[tuple[int, int]]] = {}
    for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ranges.setdefault(node.name, []).append((node.lineno, node.end_lineno or node.lineno))
    return {name: tuple(spans) for name, spans in ranges.items()}


def sites_outside_their_function(by_site: dict[str, set[str]]) -> list[str]:
    """Dòng ghi lại phải nằm trong thân chính HÀM đã ghi nó."""
    ranges = function_line_ranges()
    reports = []
    for site in sorted(by_site):
        name, number = parse_site(site)
        if number is None:
            continue  # khoá cong: để sites_pointing_nowhere báo, đừng báo hai lần
        spans = ranges.get(name)
        if not spans:
            reports.append(f"{site}: service.py không có hàm tên {name!r}")
        elif not any(start <= number <= end for start, end in spans):
            reports.append(f"{site}: dòng nằm ngoài thân {name!r} {list(spans)}")
    return reports


# Hình dạng nào gõ kim THẲNG tại chỗ so, hình dạng nào đọc kim từ một bảng
# có tên. Hai nhóm này phải phủ kín — xem
# ``test_no_shape_falls_between_the_two_groups``.
SHAPES_WRITTEN_INLINE = frozenset({"compare", "comprehension", "startswith"})
SHAPES_FROM_A_TABLE = frozenset({"loop-var", "named-set", "mapping.get-named"})


def carriers_not_named_on_their_line(
    carriers_at: dict[str, set[str]], lines: list[str]
) -> list[str]:
    """Kim đến từ bảng thì **cái tên đã mang bảng tới** phải có trên dòng ấy.

    Với kim gõ thẳng, chữ của kim nằm ngay đó nên hỏi thẳng chữ được. Kim
    đọc từ bảng hằng thì chữ nằm ở chỗ KHAI BẢNG, cách chỗ so có khi vài
    trăm dòng — hỏi chữ là hỏi sai chỗ. Nhưng thứ luôn có mặt tại chỗ so là
    cái định danh đã mang bảng tới: ``generic_titles``, ``self.POLICY_...``.

    Khớp **nguyên từ** chứ không phải chuỗi con: ``bang`` là chuỗi con của
    ``max_bang``, hỏi lỏng thì xanh mà chẳng chứng minh gì (erplisting-21 đo
    được bên họ). Siết lên không mất chỗ nào — 56/56 vẫn khớp nguyên từ.
    """
    reports = []
    for site in sorted(carriers_at):
        _, number = parse_site(site)
        if number is None or not 0 < number <= len(lines):
            continue  # đã có luật khác báo
        text = lines[number - 1]
        for carrier in sorted(carriers_at[site]):
            if not re.search(rf"\b{re.escape(carrier)}\b", text):
                reports.append(
                    f"{site}: kim tới đây qua tên {carrier!r}, "
                    f"mà dòng ấy không nhắc tên đó"
                )
    return reports


def tables_that_lost_their_name(nameless_at: set[str]) -> list[str]:
    """Chỗ so có bảng hằng thật mà không gọi được TÊN bảng ấy.

    Luật (d) hỏi "dòng ấy có nhắc tên bảng không", nên nó chỉ với tới được
    chỗ nào đã ghi được tên. ``box_name`` trả **chuỗi rỗng** cho hình nó
    chưa nhận (``RULES["x"]``, ``self.a.b``), rồi ``if carrier:`` nuốt luôn
    chuỗi rỗng ấy — chỗ so biến khỏi tầm luật (d) và tổng vẫn đọc là 0.

    Trên cây hôm nay là **0/25**: mọi vế mang bảng đều gọi được tên. Nhưng
    0 ấy đo cái "chưa với tới", không đo cái "không thể" — hình chưa nhận
    thì có thật, chỉ là service.py chưa viết kiểu đó ở đúng chỗ so. Phân
    biệt hai thứ ấy là của erplisting-21, đo được bên họ ở ``else ""``.
    """
    return [
        f"{site}: có bảng hằng mà không đọc ra tên bảng — luật (d) mù ở đây"
        for site in sorted(nameless_at)
    ]


def inline_needles_not_written_on_their_own_line(
    literal_at: dict[str, dict[str, int]], lines: list[str]
) -> list[str]:
    """Luật (b) hỏi ở mốc chặt nhất: **đúng dòng của chính hằng ấy**.

    Bản trước hỏi "kim có nằm đâu đó trong cửa sổ ``[dòng nút bọc, hết nút]``
    không". Cửa sổ ấy rộng tới 19 dòng, và luật nào mà **nới dữ liệu ra lại
    làm nó dễ xanh hơn** thì tự nó không đứng được: nới ``end`` thêm 50 dòng,
    bản cửa sổ bắt **0**.

    Gốc bệnh nằm ở cái mốc chứ không ở câu hỏi. Mốc cũ là dòng của nút bọc,
    mà hằng thì nằm rải trong nút — chỉ **284/348** kim nằm đúng trên dòng
    ấy. Lấy mốc là ``lineno`` của chính hằng: **348/348**. Đo xong mới hỏi
    chặt được (cách chữa của erplisting-21, bên họ 313/383 → 383/383).

    Hỏi **có nháy quanh** chứ không hỏi chuỗi con: ở đây có 18 lượt kim dài
    một hai ký tự (``x``, ``n``, ``_``, ``0``, ``1``), mà chuỗi con một ký tự
    thì gần như dòng nào cũng chứa.
    """
    reports = []
    for site in sorted(literal_at):
        for needle, number in sorted(literal_at[site].items()):
            if not 0 < number <= len(lines):
                reports.append(f"{site}: kim {needle!r} trỏ ra ngoài file")
                continue
            text = lines[number - 1]
            if f'"{needle}"' not in text and f"'{needle}'" not in text:
                reports.append(
                    f"{site}: kim {needle!r} gõ thẳng mà dòng {number} "
                    f"không viết hằng ấy"
                )
    return reports


@lru_cache(maxsize=1)
def statement_spans() -> dict[tuple[str, int], tuple[int, int]]:
    """``(tên hàm, dòng)`` → khoảng của **câu lệnh nhỏ nhất** bọc dòng ấy.

    Đọc lại từ cây, độc lập với lượt quét kim.
    """
    source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
    table: dict[tuple[str, int], tuple[int, int]] = {}
    for outer in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
        if not isinstance(outer, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(outer):
            if not isinstance(node, ast.stmt):
                continue
            span = (node.lineno, node.end_lineno or node.lineno)
            for line in range(span[0], span[1] + 1):
                held = table.get((outer.name, line))
                if held is None or span[1] - span[0] < held[1] - held[0]:
                    table[(outer.name, line)] = span
    return table


def anchors_outside_their_statement(
    literal_at: dict[str, dict[str, int]],
    boxes: dict[tuple[str, int], tuple[int, int]] | None = None,
) -> list[str]:
    """Luật (e): mốc của kim phải nằm trong **chính câu lệnh** đã ghi nó.

    Luật chữ một mình không đủ, và đây là chỗ nó mù theo **cấu trúc** chứ
    không phải vì trùng hợp: hễ trong cùng hàm có dòng khác cũng viết đúng
    hằng ấy thì đẩy mốc sang đó, luật chữ vẫn thấy chữ nên **im hoàn toàn**.
    Đo trên cây thật, lấy **mọi** dòng ứng viên: 48 lượt đẩy được như thế,
    luật chữ bắt **0**. (Số cũ ghi ở đây là 18 lượt — sai, vì dụng cụ khi ấy
    lấy ``elsewhere[0]``, tức dòng nhỏ nhất, nên chỉ đếm một chiều.)

    Chia ba theo *hộp của dòng mốc*: **14 lượt** hộp bắt đầu sau chỗ so,
    **31 lượt** hộp khép trước chỗ so — luật này bắt đủ 45 — và **3 lượt**
    vẫn đúng một câu lệnh với chỗ so, luật này im, phải để (g) gánh. Cả hai
    nửa đều phải có mẫu: nửa ``number <= box[1]`` từng không phép thử nào
    giữ đúng vì rổ chỉ được đo một chiều.

    Ca quyết định do erplisting-21 tìm ra bên họ: cùng một kim ở hai phép so
    khác nhau trong một hàm (``shirt``/``tshirt``). Bên tôi cũng có, ở
    ``_flow_operator_card_product_signals`` dòng 12516 và 12592 — tôi đã bỏ
    luật (c) sau khi đo "0 kim trùng tên **giữa hai chỗ so được canh**", mà
    câu hỏi đúng rộng hơn: **bất kỳ dòng nào cũng mang hằng ấy** là đủ để
    luật chữ im, dòng ấy không cần là chỗ so.
    """
    boxes = statement_spans() if boxes is None else boxes
    reports = []
    for site in sorted(literal_at):
        name, number = parse_site(site)
        if number is None:
            continue  # đã có luật khác báo
        for needle, anchor in sorted(literal_at[site].items()):
            # Neo hộp theo **dòng mốc**, không theo dòng chỗ so. Neo nhầm đầu
            # thì ``if x in {...}:`` một dòng, ``return "portrait"`` dòng sau
            # lọt sạch: câu lệnh nhỏ nhất bọc *dòng chỗ so* là cả cái ``if``
            # nên nuốt luôn thân, còn câu lệnh bọc *dòng mốc* là chính cái
            # ``return`` và nó không chứa chỗ so.
            box = boxes.get((name, anchor))
            if box is None:
                reports.append(
                    f"{site}: mốc của kim {needle!r} ở dòng {anchor}, không "
                    f"nằm trong câu lệnh nào của hàm"
                )
                continue
            if not box[0] <= number <= box[1]:
                reports.append(
                    f"{site}: mốc của kim {needle!r} ở dòng {anchor}, câu lệnh "
                    f"{box} của nó không chứa chỗ so"
                )
    return reports


def anchors_outside_their_comparison_node(
    literal_at: dict[str, dict[str, int]],
    node_at: dict[str, dict[str, tuple[int, int]]],
) -> list[str]:
    """Luật (g): mốc phải nằm trong **khoảng của chính nút so** đã ghi nó.

    Đây mới là bất biến thật, và hai luật theo *dòng* ở trên chỉ là xấp xỉ
    của nó. erplisting-21 chỉ đúng chỗ: hằng cùng câu lệnh có thể là hằng
    của **một phép so khác**. Câu lệnh boolean dài
    ``_flow_operator_card_product_signals`` trải 12522–12595 và chứa nhiều
    phép so; đẩy mốc của ``banner`` từ 12551 sang 12585 thì cả (e) lẫn (f)
    đều im vì vẫn "cùng câu lệnh" và vẫn đi xuôi — chỉ luật này kêu.

    Đo trên cây thật: bắt **48/48** lượt đẩy, báo oan **0** trên tập sạch.
    Nó bao trùm (e) và (f) không chỉ bằng số mà bằng chứng minh — span của
    nút nằm gọn trong span câu lệnh, và ``node.lineno`` chính là dòng chỗ
    so, nên mốc lọt (g) thì không thể phạm (e) hay (f). Giữ cả ba vì mỗi
    luật phát biểu một điều đọc được, và vòng trước cho thấy bỏ luật dựa
    trên phép đo sai phạm vi là cách mở lại lỗ.
    """
    reports = []
    for site in sorted(literal_at):
        for needle, anchor in sorted(literal_at[site].items()):
            span = node_at.get(site, {}).get(needle)
            if span is None:
                reports.append(f"{site}: kim {needle!r} không ghi lại khoảng nút so")
                continue
            if not span[0] <= anchor <= span[1]:
                reports.append(
                    f"{site}: mốc của kim {needle!r} ở dòng {anchor}, ngoài "
                    f"nút so {span}"
                )
    return reports


def anchors_standing_before_their_comparison(
    literal_at: dict[str, dict[str, int]],
) -> list[str]:
    """Luật (f): mốc không được đứng **trên** dòng của chính phép so.

    Hằng nằm *trong* phép so, nên dòng so luôn ``<=`` dòng hằng — đo trên
    tập sạch: đúng **348/348**. Lùi mốc lên trên chỗ so là phá bất biến ấy
    ngay cả khi vẫn còn trong một câu lệnh, nên (e) một mình không đủ.

    Ranh giới nói thật/nói dối **không phải** "cùng câu lệnh hay không" —
    đây là chỗ erplisting-21 đo được bên họ: hằng viết ở dòng trước có thể
    là của một phép so **khác** trong cùng câu lệnh (``{... "theu" ...} &
    tokens`` ở một dòng, chỗ so ở dòng sau), nên lùi mốc lên đó là nói dối
    dù không ra khỏi câu lệnh. Bên tôi đo được **0 lượt** như thế trên cây
    hôm nay: mọi lượt (f) bắt thì (e) cũng bắt. Giữ luật này vì nó chặn một
    lớp hỏng có thật chứ không phải vì hôm nay nó bắt thêm được gì — ghim
    bịa là chỗ duy nhất phân biệt được hai luật.
    """
    reports = []
    for site in sorted(literal_at):
        name, number = parse_site(site)
        if number is None:
            continue  # đã có luật khác báo
        for needle, anchor in sorted(literal_at[site].items()):
            if anchor < number:
                reports.append(
                    f"{site}: mốc của kim {needle!r} ở dòng {anchor}, trên cả "
                    f"dòng {number} của phép so"
                )
    return reports


def missing_twins(by_site: dict[str, set[str]]) -> list[str]:
    """Kim có ``_`` mà thiếu bản viết liền **ngay tại chỗ so ấy**.

    Tách ra thành hàm thuần để kiểm được bằng dữ liệu bịa: chọn phạm vi nào
    là một quyết định, và quyết định thì phải có ca chứng minh nó gánh việc.

    Vế ``"_" not in needle`` thì **không** phải một quyết định như thế: kim
    không có ``_`` thì ``twin`` chính là ``needle``, mà ``needle`` vừa lấy ra
    từ ``needles`` — nên ``twin not in needles`` không bao giờ đúng. Bỏ hẳn
    vế ấy đi, cả suite vẫn xanh 70/70 (đã đo). Nó là chỗ rẽ nhanh, không phải
    chỗ chọn phạm vi, nên đừng bịa ca ghim cho nó: ca ấy sẽ xanh với cả bản
    có lẫn bản không, tức không chứng minh gì.
    """
    reports = []
    for site, needles in sorted(by_site.items()):
        for needle in sorted(needles):
            if "_" not in needle:  # rẽ nhanh, dư về logic — xem docstring
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
    shapes_at: dict[str, set[str]] = {}
    carriers_at: dict[str, set[str]] = {}
    inline_at: dict[str, set[str]] = {}
    literal_at: dict[str, dict[str, int]] = {}
    node_at: dict[str, dict[str, tuple[int, int]]] = {}
    # Chỗ so có bảng hằng mà KHÔNG gọi được tên bảng ấy. ``box_name`` trả
    # chuỗi rỗng cho hình nó chưa nhận (``RULES["x"]``, ``self.a.b``), rồi
    # ``if carrier:`` nuốt luôn — chỗ so ấy biến khỏi tầm luật (d) mà tổng
    # vẫn đọc là 0. Ghi lại để có cái mà kêu.
    nameless_at: set[str] = set()


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
    shapes: dict[str, set[str]] = {}
    carriers: dict[str, set[str]] = {}
    inline: dict[str, set[str]] = {}
    literals: dict[str, dict[str, int]] = {}
    nodes: dict[str, dict[str, tuple[int, int]]] = {}
    nameless: set[str] = set()
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
                                keep(value, "loop-var", node, carrier=part.id)
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

        def keep(
            value: object,
            why: str,
            node: ast.AST | None = None,
            carrier: str | None = None,
            literal: ast.AST | None = None,
        ) -> None:
            if isinstance(value, str) and value:
                site = f"{function.name}:{getattr(node, 'lineno', 0)}"
                found.setdefault(value, set()).add(f"{function.name}:{why}")
                sites.setdefault(site, set()).add(value)
                shapes.setdefault(site, set()).add(why)
                if why in SHAPES_WRITTEN_INLINE:
                    inline.setdefault(site, set()).add(value)
                    # Mốc của kim là dòng của CHÍNH HẰNG ấy, không phải dòng
                    # của nút bọc: bảng gõ thẳng trải tới 19 dòng thì hai cái
                    # đó cách nhau xa, và cửa sổ rộng làm luật dễ xanh.
                    anchor = getattr(literal or node, "lineno", 0)
                    literals.setdefault(site, {})[value] = anchor
                    # Khoảng của CHÍNH nút so ấy. Luật theo *dòng* không
                    # tách được hai phép so nằm chung một câu lệnh dài —
                    # bất biến thật là hằng thuộc đúng nút này.
                    nodes.setdefault(site, {})[value] = (
                        getattr(node, "lineno", 0),
                        getattr(node, "end_lineno", 0) or getattr(node, "lineno", 0),
                    )
                if carrier:
                    carriers.setdefault(site, set()).add(carrier)
                elif why == "named-set":
                    # Bảng có thật mà không gọi được tên: đừng bỏ qua im lặng.
                    nameless.add(site)

        def named_set_strings(node: ast.AST) -> list[str]:  # noqa: D401
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
                                keep(element.value, "compare", node, literal=element)
                        for value in named_set_strings(part):
                            keep(value, "named-set", node, carrier=box_name(part))
            if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp)) and isinstance(
                node.elt, ast.Compare
            ):
                inner = node.elt
                if any(holds_result(part) for part in [inner.left, *inner.comparators]):
                    for generator in node.generators:
                        for element in elements(generator.iter):
                            if isinstance(element, ast.Constant):
                                keep(
                                    element.value,
                                    "comprehension",
                                    node,
                                    literal=element,
                                )
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
                    named = receiver.id if isinstance(receiver, ast.Name) else None
                    for key in table.keys:
                        if isinstance(key, ast.Constant):
                            keep(
                                key.value,
                                "mapping.get-named" if named else "mapping.get",
                                node,
                                carrier=named,
                            )
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"startswith", "endswith"}
                and holds_result(node.func.value)
            ):
                for argument in node.args:
                    for element in elements(argument):
                        if isinstance(element, ast.Constant):
                            keep(element.value, "startswith", node, literal=element)

    return SweptNeedles(
        by_text=found,
        functions=[fn.name for fn in functions],
        by_site=sites,
        shapes_at=shapes,
        carriers_at=carriers,
        inline_at=inline,
        literal_at=literals,
        node_at=nodes,
        nameless_at=nameless,
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
        ("_normalize_skill_token", "mapping.get-named"): 58,
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
    # ``mapping.get`` = bảng gõ THẲNG tại chỗ gọi. Tách nhãn ra mới thấy:
    # cả 58 cây kim mapping ở flow-v2 đều đi qua bảng CÓ TÊN
    # (``mapping.get-named``), không cái nào gõ thẳng. Trước khi tách, tôi
    # đã định xếp cả nhóm này vào "gõ thẳng" — xếp thế là sai, và cái sai ấy
    # sẽ lặng lẽ đưa 58 kim ra ngoài luật (d).
    SHAPES_WITH_NO_SITE_HERE = {"startswith", "mapping.get"}

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

    def test_the_tree_really_has_room_for_that_to_happen(self) -> None:
        """Ca bịa ở trên ghim LUẬT; câu này ghim DỮ LIỆU ĐƯA VÀO luật.

        Hai lỗ khác nhau. Ca bịa gọi thẳng ``missing_twins`` nên ai dồn các
        chỗ so lại **ở chỗ gọi** — trước khi dữ liệu tới luật — thì hàm
        thuần vẫn nguyên vẹn và ca bịa vẫn xanh, trong khi phạm vi chặt đã
        chết. Đo thật trên cây này, gộp khoá chỗ so theo dải dòng:

            nguyên  //10  //100  //1000
              3       2      0      0    _compact_match_text
              1       1      0      0    _normalize_prompt_source_header

        Câu này KHÔNG phải câu ghi chép cho vui, dù lúc đầu tôi tưởng thế.
        Đo mới thấy nó là chỗ duy nhất bắt được một kiểu dồn: dồn hết chỗ
        so về **một dòng có phép so thật** (thử ``:14940`` cho mọi chỗ) thì
        kiểm tính chất xanh trơn — vì từng khoá vẫn trỏ đúng vào một phép
        so — mà phạm vi đã sập hoàn toàn. Chỉ câu này đỏ. Hai câu không
        chồng nhau: một câu hỏi "từng dòng có nói thật không", câu này hỏi
        "các dòng có còn khác nhau không".

        Vì thế nó soi cả ba bảng chữ, không chỉ hai bảng mà luật cặp dùng.

        Phần bắt dồn dòng còn lại do
        ``test_every_recorded_line_points_at_a_real_comparison`` gánh: đã thử đặt mốc SỐ ở đây (3 và 1) thì nó
        bắt được //10 nhưng để lọt //2 với //4, mà nâng ngưỡng lên thì mục
        ngay lần thêm bớt một phép so. Ngưỡng đuổi theo cây; tính chất thì
        không.
        """
        for normalizer in NormalizedNeedleAlphabetTests.ALPHABETS:
            sites = needles_compared_with(normalizer).by_site
            by_function: dict[str, set[frozenset]] = {}
            for site, needles in sites.items():
                by_function.setdefault(site.rsplit(":", 1)[0], set()).add(frozenset(needles))
            spread = [name for name, groups in by_function.items() if len(groups) > 1]
            with self.subTest(normalizer=normalizer):
                self.assertTrue(
                    spread, f"{normalizer}: không hàm nào có hai chỗ so khác tập kim"
                )


    def test_every_recorded_line_points_at_a_real_comparison(self) -> None:
        """Số dòng ghi lại phải trỏ vào một phép so THẬT trong service.py.

        Đây là chỗ mốc số nên nhường lại. Mốc số hỏi "còn đủ nhiều không",
        nên bao giờ cũng có mức dồn vừa đủ để lách; kiểm tính chất hỏi
        "từng dòng có nói thật không", nên không có mức nào lách được.

        Nó bắt cùng lúc ba loại hỏng khác nhau — dồn khoá ở chỗ gọi, cộng
        bù sai, và bỏ hẳn phần bù — mà không loại nào cần một con số riêng.

        Hai điều đã đo chứ không đoán:

        * ``any(`` / ``all(`` phải nằm trong danh sách dấu hiệu. Hình dạng
          "comprehension" ghi lại dòng của lời gọi bao ngoài, nên 7 chỗ so
          ở repo này trỏ đúng vào dòng ``any(`` — thiếu dấu ấy là báo oan
          bảy lần, chứ không phải bắt được bảy lỗi.
        * Thêm hai dấu ấy gần như không làm cùn lưỡi: dòng bất kỳ trong
          service.py trúng dấu hiệu 11.4% -> 11.5%. Tức một chỗ so bị dồn
          hay bị lệch có gần chín phần mười khả năng rơi vào dòng không hề
          có phép so, mà ở đây có 89 chỗ so cùng kiểm.
        """
        source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
        lines = source.read_text(encoding="utf-8").split("\n")
        wrong = []
        for normalizer in NormalizedNeedleAlphabetTests.ALPHABETS:
            wrong.extend(
                sites_pointing_nowhere(needles_compared_with(normalizer).by_site, lines)
            )
        self.assertEqual([], wrong[:5], f"{len(wrong)} chỗ so trỏ sai dòng")


    def test_every_recorded_line_sits_inside_the_function_that_recorded_it(self) -> None:
        """Câu hỏi vị trí thứ ba, và nó bắt được thứ hai câu kia không bắt.

        Ba câu không thay nhau được, mỗi câu lộ ra vì có đột biến vượt qua
        được câu trước:

        * *nói thật* — dòng có phép so không? Lọt khi dồn về một dòng hợp lệ.
        * *còn tách nhau* — các dòng có còn khác nhau không? Lọt khi hoán vị
          mỗi chỗ so sang một dòng **riêng biệt** của hàm khác.
        * *đúng nhà* — câu này. Đo ca hoán vị ấy trên 87 khoá: nói thật báo
          **0**, còn tách nhau vẫn **18** hàm y như cũ, đúng nhà báo **86**.

        Bảng khoảng dòng dựng riêng từ AST chứ không dùng lại số của bước
        ghi, nên hai đường suy ra soi lẫn nhau.
        """
        wrong = []
        for normalizer in NormalizedNeedleAlphabetTests.ALPHABETS:
            wrong.extend(sites_outside_their_function(needles_compared_with(normalizer).by_site))
        self.assertEqual([], wrong[:5], f"{len(wrong)} chỗ so ghi sai nhà")

    def test_a_line_from_the_wrong_function_is_reported(self) -> None:
        """Ghim luật bằng dữ liệu bịa, hai chiều, và nói rõ ai KHÔNG bắt.

        Vế "hai luật kia phải xanh" mới là vế chứng minh câu này bắt thêm
        được thứ gì; thiếu nó thì chỉ chứng minh được nó cũng đỏ.
        """
        inside = min(function_line_ranges()["_compact_match_text"])[0]
        self.assertEqual([], sites_outside_their_function({f"_compact_match_text:{inside}": {"a"}}))
        for bent, why in (
            (f"_compact_match_text:{inside + 10_000}", "dòng ngoài thân hàm"),
            ("_khong_ton_tai_dau:1", "hàm không có thật"),
        ):
            with self.subTest(bent=bent, why=why):
                reports = sites_outside_their_function({bent: {"a"}})
                self.assertEqual(1, len(reports))
                self.assertIn(bent, reports[0])
        self.assertEqual([], sites_outside_their_function({"f": {"a"}}),
                         "khoá cong là việc của sites_pointing_nowhere, đừng báo hai lần")


    def test_no_shape_falls_between_the_two_groups(self) -> None:
        """Hai nhóm phải PHỦ KÍN, nếu không hình dạng mới lọt xuống khe.

        Luật (d) chỉ hỏi được nhóm "đọc từ bảng"; luật chữ-của-kim chỉ hỏi
        được nhóm "gõ thẳng". Hình dạng nào không thuộc nhóm nào thì chỉ
        còn ba câu vị trí canh — mà ba câu ấy đều xanh khi hoán vị trong
        cùng một hàm. Nó sẽ nằm im, không ai kêu.

        Đây là câu phải lắp TRƯỚC khi lắp (d), không phải sau.
        """
        seen: set[str] = set()
        for normalizer in NormalizedNeedleAlphabetTests.ALPHABETS:
            for shapes in needles_compared_with(normalizer).shapes_at.values():
                seen |= shapes
        self.assertEqual(
            set(),
            seen - (SHAPES_WRITTEN_INLINE | SHAPES_FROM_A_TABLE),
            "hình dạng này chưa được xếp vào nhóm nào — xếp nó vào một nhóm, "
            "đừng để nó chỉ được canh bằng vị trí",
        )

    def test_a_table_needle_names_its_carrier_on_the_line(self) -> None:
        """Luật (d) trên cây thật, và ca hoán vị trong hàm mà nó bắt được.

        Ba câu vị trí đều mù với hoán vị TRONG CÙNG một hàm: dòng vẫn trong
        thân hàm, vẫn có phép so, các khoá vẫn khác nhau — đo được 0/0/18 y
        như cây sạch. Câu này là câu đầu tiên nhìn thấy nó.

        **Số nhỏ chưa chắc là luật yếu — đếm xem đột biến có cắn không.** Đột
        biến "đổi tên mang giữa các chỗ trong cùng hàm" chỉ làm (d) kêu **2**,
        đọc như luật yếu. Đếm lại: trong 56 khoá mang bảng, tên gần như luôn
        dùng chung trong một hàm (``token`` 25 chỗ, ``term`` 23), nên phép xoay
        là **phép đồng nhất** với 54 khoá — chỉ **2 khoá** đổi được tên, và (d)
        bắt **2/2**. Cùng hình dạng với con số 2/189 mà erplisting-21 đo bên họ,
        hai bên ra độc lập.
        """
        source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
        lines = source.read_text(encoding="utf-8").split("\n")
        wrong = []
        for normalizer in NormalizedNeedleAlphabetTests.ALPHABETS:
            wrong.extend(
                carriers_not_named_on_their_line(
                    needles_compared_with(normalizer).carriers_at, lines
                )
            )
        self.assertEqual([], wrong[:5], f"{len(wrong)} kim ghi sai chỗ mang")

    def test_the_carrier_rule_is_pinned_on_made_up_data(self) -> None:
        lines = ["if x in generic_titles:", "if x in other:"]
        self.assertEqual([], carriers_not_named_on_their_line({"f:1": {"generic_titles"}}, lines))
        reports = carriers_not_named_on_their_line({"f:2": {"generic_titles"}}, lines)
        self.assertEqual(1, len(reports))
        self.assertIn("generic_titles", reports[0])


    def test_an_inline_needle_is_written_on_its_own_line(self) -> None:
        """Luật (b): kim gõ thẳng thì **đúng dòng của chính hằng ấy** phải viết nó.

        Bản đầu hỏi lỏng hơn hai bậc, và cả hai bậc đều là bệnh thật.

        *Bậc một — hỏi chuỗi con.* Ở đây có 18 lượt kim dài một hai ký tự
        (``x``, ``n``, ``_``, ``0``, ``1``); chuỗi con một ký tự thì dòng nào
        chẳng chứa. Siết thành "có hằng chuỗi với nháy quanh": 348/348 vẫn
        đạt, giá bằng 0.

        *Bậc hai — mốc là nút bọc.* Cửa sổ ``[dòng nút bọc, hết nút]`` rộng
        tới 19 dòng, nên **nới dữ liệu ra lại làm luật dễ xanh hơn**: nới
        ``end`` thêm 50 dòng, bản cửa sổ bắt **0**. Gốc bệnh ở cái mốc chứ
        không ở câu hỏi — chỉ **284/348** kim nằm đúng trên dòng nút bọc.
        Lấy mốc là dòng của chính hằng: **348/348**, rồi mới hỏi chặt được.

        Đo trên 348 kim gõ thẳng, cột "cắn" là số kim mà đột biến thực sự
        đổi được mốc — số nhỏ chưa chắc là luật yếu, phải đếm cả cái này:

        ================================  ========  =======  ========  =======
        đột biến                          (b) mốc   cắn      (b) cửa   (c) bắt
                                          chặt               sổ cũ
        ================================  ========  =======  ========  =======
        cây sạch                                 0        –         0        0
        mốc lệch +1                            342  348/348         0       45
        mốc lệch −1                            347  348/348       284       75
        mốc lệch +5                            348  348/348         0       73
        mốc lệch +50                           344  348/348         0       75
        đổi mốc giữa các kim cùng chỗ so         59    59/59         0        0
        đổi mốc giữa các chỗ so cùng hàm        323  323/323         –        –
        ================================  ========  =======  ========  =======

        Mốc chặt bắt được **mọi ca mà hai luật kia bắt, và cả hai ca chúng
        mù**, nên luật cửa sổ và luật (c) ("cửa sổ phải đúng bằng cửa sổ một
        nút có thật") đã bị bỏ cùng trường ``spans_at``. Cách chữa này của
        erplisting-21 (bên họ 313/383 → 383/383).

        **Nhưng bỏ (c) đã mở một lỗ, và luật (e) mới là chỗ bịt.** Luật chữ
        mù theo **cấu trúc** với ca "đẩy mốc sang dòng khác cũng viết đúng
        hằng ấy": 18 kim đẩy được, luật chữ bắt **0**. Xem
        :func:`anchors_outside_their_statement`. Chỗ tôi đo sai lúc bỏ (c):
        hỏi "có kim nào trùng tên giữa hai **chỗ so được canh** không" →
        0, rồi kết luận bỏ là an toàn. Câu hỏi đúng rộng hơn hẳn — **bất kỳ
        dòng nào trong hàm cũng mang hằng ấy** là đủ để luật chữ im, dòng ấy
        không cần là chỗ so. Hỏi lại cho đúng: 18.

        Vài ca sót là trùng hợp thật, ghi ra chứ không làm tròn lên: ``+1``
        sót 6, ``+50`` sót 4 — dòng rơi vào chỗ tình cờ cũng viết đúng hằng ấy.

        (b) và (d) vẫn khác vai: (b) canh *mốc của kim*, (d) canh *số dòng
        trong khoá*. Hoán vị khoá trong cùng hàm thì (d) bắt 12, (b) bắt 0 —
        (b) không đọc số dòng trong khoá. Ghép lại mới phủ hết.
        """
        source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
        lines = source.read_text(encoding="utf-8").split("\n")
        wrong = []
        for normalizer in NormalizedNeedleAlphabetTests.ALPHABETS:
            swept = needles_compared_with(normalizer)
            wrong.extend(
                inline_needles_not_written_on_their_own_line(swept.literal_at, lines)
            )
        self.assertEqual([], wrong[:5], f"{len(wrong)} kim gõ thẳng ghi sai mốc")

    def test_the_two_text_rules_ask_tightly_not_loosely(self) -> None:
        """Hỏi lỏng bằng chuỗi con thì xanh mà không chứng minh gì.

        Cặp phân biệt, vì "chặt hơn" nói suông không phải bằng chứng — bản
        lỏng **im**, bản chặt **kêu đúng một**:

        * kim ``ao`` với dòng ``if x == "gao":`` — ``ao`` là chuỗi con của
          ``gao``, nhưng không có hằng chuỗi ``"ao"`` nào ở đó.
        * tên mang ``bang`` với dòng ``if t in max_bang:`` — chuỗi con của
          ``max_bang``, nhưng không phải nguyên từ.

        Cả hai ca do erplisting-21 đo bên họ rồi gửi sang; bên này dính nặng
        hơn vì có 18 lượt kim dài một hai ký tự (``x``, ``n``, ``_``, ``0``).
        """
        kim_lines = ['if x == "gao":']
        self.assertIn("ao", kim_lines[0], "ca thu phai qua duoc hoi long")
        reports = inline_needles_not_written_on_their_own_line(
            {"f:1": {"ao": 1}}, kim_lines
        )
        self.assertEqual(1, len(reports))
        self.assertIn("ao", reports[0])

        carrier_lines = ["if t in max_bang:"]
        self.assertIn("bang", carrier_lines[0], "ca thu phai qua duoc hoi long")
        reports = carriers_not_named_on_their_line({"f:1": {"bang"}}, carrier_lines)
        self.assertEqual(1, len(reports))
        self.assertIn("bang", reports[0])

    def test_an_anchor_may_not_leave_its_own_statement(self) -> None:
        """Luật (e) trên cây thật: mốc phải nằm trong câu lệnh đã ghi nó.

        Đo lại trên cây thật sau khi neo hộp theo **dòng mốc**. Hai bảng
        trước ghi ở đây (14/14 – 0/4, rồi 33/33 – 6/6 – 0/9) đều đo bằng
        dụng cụ hỏng, đã bỏ: bảng đầu chỉ nhìn một chiều, bảng sau neo hộp
        theo *dòng chỗ so* nên rổ "vẫn trong câu lệnh" nuốt mất 8 ca nói dối.

        ==========================================  ========  =====  =====  =====
        đột biến                                    luật chữ    (e)    (f)    (g)
        ==========================================  ========  =====  =====  =====
        cây sạch                                           0      0      0      0
        câu lệnh của mốc **bắt đầu sau** chỗ so            0  14/14   0/14  14/14
        câu lệnh của mốc **khép trước** chỗ so             0  31/31  31/31  31/31
        cùng câu lệnh nhưng **khác nút so**                0    0/3    2/3    3/3
        ==========================================  ========  =====  =====  =====

        Luật chữ mù ở đây theo **cấu trúc**, không phải trùng hợp: dòng đích
        vẫn viết đúng hằng ấy nên nó vẫn thấy chữ. Rổ thứ ba là chỗ (e) và
        (f) đuối: 2/3 ca là dòng **chú thích** có viết hằng (bắt được vì đi
        lùi), còn ca thứ ba — ``banner`` 12551 → 12585, cùng một câu lệnh
        boolean trải 12522–12595 — thì chỉ (g) kêu.
        """
        for normalizer in NormalizedNeedleAlphabetTests.ALPHABETS:
            swept = needles_compared_with(normalizer)
            with self.subTest(normalizer=normalizer):
                self.assertEqual([], anchors_outside_their_statement(swept.literal_at))
                self.assertEqual(
                    [], anchors_standing_before_their_comparison(swept.literal_at)
                )
                self.assertEqual(
                    [],
                    anchors_outside_their_comparison_node(
                        swept.literal_at, swept.node_at
                    ),
                )

    def test_the_statement_rule_is_pinned_on_made_up_data(self) -> None:
        """Ghim theo đúng thứ tự: **đòi luật chữ im trước**, rồi (e)/(g) mới kêu.

        Không khẳng định luật chữ im thì ca thử này không chứng minh được
        gì thêm — có khi luật kia chỉ kêu ở chỗ luật chữ đã kêu sẵn.
        """
        lines = [
            'ALL = ("shirt", "tee")',
            "def f(x):",
            "    if x in (",
            '        "shirt",',
            "    ):",
            '        return "shirt"',
        ]
        # Hộp câu lệnh bịa: cả cái ``if`` trải 3–6, riêng ``return`` là 6–6.
        boxes = {
            ("f", 1): (1, 1),
            ("f", 3): (3, 6),
            ("f", 4): (3, 6),
            ("f", 5): (3, 6),
            ("f", 6): (6, 6),
        }
        node = {"f:3": {"shirt": (3, 5)}}

        def im_het_luat_chu(bent):
            self.assertEqual(
                [], inline_needles_not_written_on_their_own_line(bent, lines),
                "luat chu phai IM thi ca thu nay moi chung minh duoc gi",
            )

        # A. Mốc lùi hẳn ra ngoài câu lệnh.
        bent = {"f:3": {"shirt": 1}}
        im_het_luat_chu(bent)
        reports = anchors_outside_their_statement(bent, boxes)
        self.assertEqual(1, len(reports))
        self.assertIn("không chứa chỗ so", reports[0])
        self.assertEqual(1, len(anchors_outside_their_comparison_node(bent, node)))

        # B. Mốc xuôi xuống ``return "shirt"`` — đúng ca erplisting-21 bắt
        # được. Neo hộp theo *dòng chỗ so* thì cả cái ``if`` nuốt luôn thân
        # nên ca này lọt; neo theo *dòng mốc* thì hộp là ``return`` (6, 6).
        bent = {"f:3": {"shirt": 6}}
        im_het_luat_chu(bent)
        reports = anchors_outside_their_statement(bent, boxes)
        self.assertEqual(1, len(reports))
        self.assertEqual(
            [], anchors_standing_before_their_comparison(bent),
            "(f) phai IM o chieu xuoi — no khong gac duoc ca nay",
        )
        self.assertEqual(1, len(anchors_outside_their_comparison_node(bent, node)))

        # C. Chỉ (g) gánh: hai phép so khác nhau trong **một** câu lệnh, mốc
        # nhảy sang hằng của phép so kia. (e) im vì vẫn cùng câu lệnh, (f)
        # im vì vẫn đi xuôi. Đây là hình dạng ``banner`` 12551 → 12585 trên
        # cây thật, và là ca duy nhất tách được (g) khỏi hai luật kia.
        doi = [
            'ALL = ("shirt", "tee")',
            "def f(x):",
            '    if ("shirt" in x) or (',
            '            y in ("shirt",)',
            "    ):",
            "        pass",
        ]
        rieng = {"f:3": {"shirt": 4}}
        self.assertEqual(
            [], inline_needles_not_written_on_their_own_line(rieng, doi),
            "luat chu phai IM thi ca thu nay moi chung minh duoc gi",
        )
        self.assertEqual(
            [], anchors_outside_their_statement(rieng, {("f", 4): (3, 5)}),
            "(e) phai IM — day moi la cho (g) ganh viec mot minh",
        )
        self.assertEqual(
            [], anchors_standing_before_their_comparison(rieng),
            "(f) phai IM — day moi la cho (g) ganh viec mot minh",
        )
        reports = anchors_outside_their_comparison_node(rieng, {"f:3": {"shirt": (3, 3)}})
        self.assertEqual(1, len(reports))
        self.assertIn("ngoài nút so", reports[0])

        # D. Chỉ (f) gánh: mốc lùi lên hằng của phép so khác, vẫn trong câu
        # lệnh nên (e) im. Đây là ca ``theu`` erplisting-21 đo được bên họ.
        above = {"f:4": {"shirt": 3}}
        self.assertEqual(
            [], inline_needles_not_written_on_their_own_line(above, doi),
            "luat chu phai IM thi ca thu nay moi chung minh duoc gi",
        )
        self.assertEqual(
            [], anchors_outside_their_statement(above, {("f", 3): (3, 5)}),
            "(e) phai IM — day moi la cho (f) ganh viec mot minh",
        )
        reports = anchors_standing_before_their_comparison(above)
        self.assertEqual(1, len(reports))
        self.assertIn("trên cả dòng", reports[0])

        # E. Chiều IM: mốc khác dòng chỗ so nhưng vẫn trong đúng nút so.
        # Nếu ai siết nhầm thành "mốc == dòng chỗ so" thì ca này đỏ. Bản ghim
        # cũ đặt mốc trùng dòng chỗ so nên mù với đúng cái siết ấy — chỉ cây
        # thật kêu. Ghim mà không cắn thì chưa phải ghim.
        honest = {"f:3": {"shirt": 4}}
        im_het_luat_chu(honest)
        self.assertEqual([], anchors_outside_their_statement(honest, boxes))
        self.assertEqual([], anchors_standing_before_their_comparison(honest))
        self.assertEqual([], anchors_outside_their_comparison_node(honest, node))

    def test_the_real_tree_mutation_is_caught_inside_the_suite(self) -> None:
        """Đẩy mốc **trên cây thật** rồi đòi từng luật trả lời, ngay trong suite.

        Trước đây con số "bắt 14/14" là tôi đo tay bằng script rời — suite
        không giữ nó. Suite chỉ giữ ca ghim bịa, mà ghim thì chỉ canh đúng
        hình dạng nó viết ra.

        Đột biến: với mỗi kim, mọi dòng khác **trong cùng hàm** cũng viết
        đúng hằng ấy đều được dời mốc sang. Chia rổ theo *luật nào lẽ ra
        phải kêu*, rồi đòi:

        * luật chữ **im** ở mọi lượt — nó mù theo cấu trúc, dòng đích vẫn
          viết đúng hằng ấy nên nó vẫn thấy chữ;
        * (g) kêu ở **mọi** lượt, kể cả rổ mà (e) và (f) đều im;
        * (e) kêu đúng hai rổ của nó và im ở rổ thứ ba.

        Rổ thứ ba là chỗ erplisting-21 bắt được lỗi của tôi: mốc vẫn "cùng
        câu lệnh" và vẫn đi xuôi nên (e) lẫn (f) đều im, mà đó là nói dối —
        ``return "portrait"`` viết lại đúng hằng ấy, và một câu lệnh boolean
        dài chứa nhiều phép so khác nhau. Trước khi vá, rổ ấy bị tôi gán
        nhãn "nói thật" nên phép thử **khẳng định im**: im vì được dạy im.
        """
        source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
        lines = source.read_text(encoding="utf-8").split("\n")
        boxes = statement_spans()
        spans = function_line_ranges()
        gio: dict[str, list] = {}
        for normalizer in NormalizedNeedleAlphabetTests.ALPHABETS:
            swept = needles_compared_with(normalizer)
            for site, anchors in swept.literal_at.items():
                name, number = parse_site(site)
                held = spans.get(name)
                if number is None or not held:
                    continue
                low, high = held[0]
                for needle, anchor in anchors.items():
                    span = swept.node_at[site][needle]
                    for line in range(low, high + 1):
                        if line == anchor:
                            continue
                        if (
                            f'"{needle}"' not in lines[line - 1]
                            and f"'{needle}'" not in lines[line - 1]
                        ):
                            continue
                        box = boxes.get((name, line))
                        if box is None or box[0] > number:
                            ro = "cau-lenh-cua-moc-bat-dau-sau-cho-so"
                        elif box[1] < number:
                            ro = "cau-lenh-cua-moc-khep-truoc-cho-so"
                        else:
                            ro = "cung-cau-lenh-nhung-khac-nut-so"
                        gio.setdefault(ro, []).append(
                            ({site: {needle: line}}, {site: {needle: span}}, line, number)
                        )

        # Cả ba rổ phải có mẫu thật. Lấy **mọi** dòng ứng viên chứ không lấy
        # dòng đầu: dụng cụ cũ lấy ``elsewhere[0]`` nên chỉ đếm được một
        # chiều, và rổ thứ ba thì không bao giờ hiện ra.
        for ro in (
            "cau-lenh-cua-moc-bat-dau-sau-cho-so",
            "cau-lenh-cua-moc-khep-truoc-cho-so",
            "cung-cau-lenh-nhung-khac-nut-so",
        ):
            self.assertIn(ro, gio, f"cay that phai co mau ro {ro}")
            for bent, span_at, line, number in gio[ro]:
                self.assertEqual(
                    [], inline_needles_not_written_on_their_own_line(bent, lines),
                    f"luat chu phai IM o dong {line} — no mu theo cau truc",
                )
                self.assertEqual(
                    1, len(anchors_outside_their_comparison_node(bent, span_at)),
                    f"(g) phai bat moc bi day toi dong {line}",
                )
                self.assertEqual(
                    0 if ro == "cung-cau-lenh-nhung-khac-nut-so" else 1,
                    len(anchors_outside_their_statement(bent)),
                    f"(e) doc sai ro {ro} o dong {line}",
                )
                self.assertEqual(
                    1 if line < number else 0,
                    len(anchors_standing_before_their_comparison(bent)),
                    f"(f) doc sai chieu o dong {line}",
                )

    def test_a_rule_that_loses_its_measurements_must_speak_not_skip(self) -> None:
        """Mệnh đề canh "thiếu số đo" phải BÁO, không được lặng lẽ bỏ qua.

        Đây là mệnh đề chết trên cây hiện tại — kim nào cũng có đủ số đo —
        nên bỏ nó đi cả suite vẫn xanh, đo được: đổi thành ``continue`` trơn
        thì 68 phép thử vẫn qua hết. Mà nó chỉ sống dậy đúng lúc bộ quét
        thôi ghi span hoặc bảng câu lệnh hụt: tức đúng lúc luật lặng thinh
        **còn tổng vẫn đọc là 0**. Rỗng-vì-mù trông y hệt rỗng-vì-sạch.

        erplisting-21 tìm ra lỗ này bên họ (`if span is None` không ai ghim)
        rồi bảo tôi kiểm — bên tôi hụt cả hai chỗ, (g) lẫn (e).
        """
        bent = {"f:3": {"shirt": 4}}
        self.assertEqual(
            1, len(anchors_outside_their_comparison_node(bent, {})),
            "(g) mat bang span thi phai BAO, khong duoc im",
        )
        self.assertEqual(
            1, len(anchors_outside_their_statement(bent, {})),
            "(e) mat bang cau lenh thi phai BAO, khong duoc im",
        )

        # Nhánh còn lại thì im là **đúng**, nhưng chỉ đúng vì có luật khác
        # gánh. Chú thích ``# đã có luật khác báo`` trong (e) và (f) là một
        # lời khẳng định, nên phải có ca chứng minh nó, không thì nó chỉ là
        # một câu viết ra cho yên tâm.
        hong = {"_parse_aspect": {"portrait": 5}}
        for rule in (
            anchors_outside_their_statement,
            anchors_standing_before_their_comparison,
        ):
            self.assertEqual([], rule(hong), "khoa hong thi ba luat moc phai nhuong")
        source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
        lines = source.read_text(encoding="utf-8").split("\n")
        self.assertEqual(
            1, len(sites_pointing_nowhere({"_parse_aspect": {"portrait"}}, lines)),
            "luat khac phai that su gach ten khoa hong — khong thi ca kia im vo chu",
        )

    def test_the_other_lost_measurement_branches_are_guarded_too(self) -> None:
        """Quét AST cả họ, không dừng ở ca đầu tiên tìm được.

        erplisting-21 chỉ ra: nhánh mất-số-đo sinh ra từ **thói quen viết
        luật**, nên ca đầu tiên gần như không bao giờ là ca duy nhất. Liệt kê
        bằng AST mọi ``if ...: continue`` trong thân các luật ra **10** nhánh;
        đột biến từng cái đo được **8 có người canh, 2 không**:

        * ``inline_needles_not_written_on_their_own_line`` — vế kim trỏ ra
          ngoài file: cấm báo mà suite vẫn xanh 69/69.
        * ``carriers_not_named_on_their_line`` — mệnh đề gộp hai vế (khoá
          cong **và** ngoài file): cho nó báo bừa mà suite vẫn xanh 69/69,
          tức không ai ghim lời khẳng định ``# đã có luật khác báo``.

        Hai ca này là hai kiểu khác nhau: (b) **tự báo** nên phải ghim là nó
        không được câm; carriers **nhường** nên phải ghim là có luật khác
        thật sự gánh — và luật ấy phải nhìn thấy cùng khoá thì mới gánh nổi.
        """
        lines = ["mot", "hai", "ba"]
        for lech in (0, -1, len(lines) + 1):
            self.assertEqual(
                1,
                len(inline_needles_not_written_on_their_own_line({"f:2": {"shirt": lech}}, lines)),
                f"(b) mốc {lech} ngoài file thì phải BÁO, không được câm",
            )

        # carriers nhường cả hai vế — nhưng chỉ nhường được nếu luật kia
        # thật sự gạch tên đúng khoá ấy.
        for cong in ({"f:khong-phai-so": {"bang"}}, {"f:999999": {"bang"}}):
            self.assertEqual(
                [], carriers_not_named_on_their_line(cong, lines),
                "carriers phải nhường khoá cong / ngoài file",
            )
            self.assertEqual(
                1, len(sites_pointing_nowhere({k: {"shirt"} for k in cong}, lines)),
                "luật khác phải thật sự báo — không thì cả hai cùng im",
            )

        # Và trên cây thật, mọi khoá carriers phải là khoá by_site, vì
        # sites_pointing_nowhere chỉ đọc by_site. Khoá nào chỉ có ở
        # carriers_at là khoá không ai gạch tên hộ.
        rieng = 0
        for normalizer in NormalizedNeedleAlphabetTests.ALPHABETS:
            swept = needles_compared_with(normalizer)
            rieng += len(set(swept.carriers_at) - set(swept.by_site))
        self.assertEqual(0, rieng, "khoá carriers nằm ngoài by_site thì không ai gánh hộ")

    def test_a_table_whose_name_cannot_be_read_is_reported_not_dropped(self) -> None:
        """Họ lỗ thứ HAI: mặc-định-lặng, không phải bỏ-qua-lặng.

        Lượt quét AST trước chỉ tìm ``if ...: continue`` — nên nó mù đúng
        cái hình mà erplisting-21 tìm ra bên họ: ``x if c else ""``. Quét
        lại theo họ ấy (IfExp, ``.get(k, mặc định)``, ``getattr(x, y, mặc
        định)``, ``x or <hằng>``, ``try/except``) ra 40 chỗ, và chỗ nguy
        hiểm nằm ở **dụng cụ**: ``box_name`` trả rỗng cho hình chưa nhận,
        rồi ``if carrier:`` nuốt mất — chỗ so rơi khỏi tầm luật (d).

        Đo trên cây thật: ``box_name`` được gọi **25** lượt trong lượt quét,
        **0** lượt rỗng. Nhưng theo phân biệt của erplisting-21, 0 ấy là
        "chưa với tới" chứ không phải "không thể" — khác hẳn vế ``"_" not in
        needle`` của :func:`missing_twins`, cái đó không đầu vào nào chạm
        được. Bằng chứng nó đổi được kết quả: bịt mắt ``box_name`` thì
        carrier tụt **56 → 54** và giỏ mất-tên lên **0 → 2**: luật (d) mất
        hai chỗ trong khi cây vẫn y nguyên. Giả định đầu của tôi là "mất
        sạch 56" — số đo bác bỏ, vì 54 carrier còn lại đi lối ``loop-var``
        và ``mapping.get-named`` chứ không qua ``box_name``.
        """
        for ma in ('RULES["x"]', "self.a.b", "diem.attr"):
            part = ast.parse(ma, mode="eval").body
            self.assertEqual("", box_name(part), f"{ma}: hình chưa nhận thì trả rỗng")

        self.assertEqual(
            1, len(tables_that_lost_their_name({"f:3"})),
            "có chỗ mất tên bảng thì phải BÁO",
        )

        sach = sum(
            len(needles_compared_with(n).nameless_at)
            for n in NormalizedNeedleAlphabetTests.ALPHABETS
        )
        self.assertEqual(0, sach, "cây sạch: mọi vế mang bảng đều gọi được tên")

        # Bịt mắt dụng cụ. Nếu bộ quét không ghi lại chỗ mất tên thì lượt
        # này XANH mà luật (d) chẳng còn gì để kiểm — rỗng-vì-mù.
        goc = globals()["box_name"]
        globals()["box_name"] = lambda part: ""
        try:
            mu = [needles_compared_with(n) for n in NormalizedNeedleAlphabetTests.ALPHABETS]
        finally:
            globals()["box_name"] = goc
        self.assertEqual(
            54, sum(len(v) for s in mu for v in s.carriers_at.values()),
            "bịt mắt thì luật (d) mất đúng phần carrier đi qua box_name",
        )
        self.assertEqual(
            2, len([r for s in mu for r in tables_that_lost_their_name(s.nameless_at)]),
            "và mất bao nhiêu thì phải kêu bấy nhiêu — không thì (d) tắt lặng lẽ",
        )

    def test_a_widened_ruler_kills_g_but_leaves_e_speaking(self) -> None:
        """Vì sao giữ (e) dù (g) chặt hơn: hai luật hỏng theo hai kiểu.

        (g) đo bằng chính con số nút đã ghi lúc quét, nên nó **tự soi
        mình**: nới thước là nó chết mà không có triệu chứng nào — cây sạch
        vẫn 0, vì rỗng-vì-mù trông y hệt rỗng-vì-sạch. (e) dựng hộp bằng
        một lượt duyệt AST **độc lập** với bước ghi, nên lượt ghi hỏng thì
        nó vẫn kêu.

        erplisting-21 đo được điều này bên họ rồi bảo tôi thử; đo bên tôi ra
        cùng kết luận. Không phải hai bản sao của một luật — một cái CHẶT
        hơn, một cái ĐỘC LẬP hơn, và lệ "chỉ giữ luật nào là người duy nhất
        bắt ở một hàng sổ sách" bỏ sót đúng cái cột này, vì phép đột biến
        quyết định nằm ở **dụng cụ** chứ không ở sổ sách.
        """
        source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
        lines = source.read_text(encoding="utf-8").split("\n")
        spans = function_line_ranges()
        nghe_g = doi = mong_e = nghe_e = 0
        for normalizer in NormalizedNeedleAlphabetTests.ALPHABETS:
            swept = needles_compared_with(normalizer)
            for site, anchors in swept.literal_at.items():
                name, number = parse_site(site)
                held = spans.get(name)
                if number is None or not held:
                    continue
                low, high = held[0]
                for needle, anchor in anchors.items():
                    # Thước bị nới: span của nút thay bằng cả thân hàm.
                    noi = {site: {needle: (low, high)}}
                    nghe_g += len(
                        anchors_outside_their_comparison_node(
                            {site: {needle: anchor}}, noi
                        )
                    )
                    for line in range(low, high + 1):
                        if line == anchor:
                            continue
                        if (
                            f'"{needle}"' not in lines[line - 1]
                            and f"'{needle}'" not in lines[line - 1]
                        ):
                            continue
                        doi += 1
                        bent = {site: {needle: line}}
                        nghe_g += len(
                            anchors_outside_their_comparison_node(bent, noi)
                        )
                        keu_e = len(anchors_outside_their_statement(bent))
                        nghe_e += keu_e
                        mong_e += 1 if keu_e else 0

        self.assertGreater(doi, 0, "khong co luot noi doi thi ca nay vo nghia")
        self.assertEqual(
            0, nghe_g,
            "thuoc bi noi ma (g) van keu thi phep thu nay khong dung cai no tuong",
        )
        self.assertGreater(
            mong_e, 0,
            "(e) phai con keu khi buoc ghi hong — do la cot rieng cua no",
        )
        self.assertEqual(nghe_e, mong_e, "(e) phai keu dung mot loi moi luot")

    def test_every_site_is_covered_by_one_of_the_two_text_rules(self) -> None:
        """Phủ kín ở mức CHỖ SO, không chỉ ở mức nhãn hình dạng.

        Ba câu vị trí đều mù với hoán vị trong cùng một hàm, nên chỗ so nào
        không có luật văn bản nào soi thì coi như không được canh. Đo: 87/87.
        """
        for normalizer in NormalizedNeedleAlphabetTests.ALPHABETS:
            swept = needles_compared_with(normalizer)
            with self.subTest(normalizer=normalizer):
                self.assertEqual(
                    set(),
                    set(swept.by_site) - set(swept.inline_at) - set(swept.carriers_at),
                    "chỗ so này không luật văn bản nào soi",
                )

    def test_the_inline_rule_is_pinned_on_made_up_data(self) -> None:
        """Ghim cả hai chiều, kèm ca **mốc trỏ đúng chỗ nhưng lệch một dòng**."""
        lines = ['if x in {"ao", "quan"}:', "    pass"]
        self.assertEqual([], inline_needles_not_written_on_their_own_line(
            {"f:1": {"ao": 1}}, lines))
        self.assertEqual(1, len(inline_needles_not_written_on_their_own_line(
            {"f:1": {"ao": 2}}, lines)), "moc lech mot dong phai keu")
        reports = inline_needles_not_written_on_their_own_line(
            {"f:1": {"vay": 1}}, lines)
        self.assertEqual(1, len(reports))
        self.assertIn("vay", reports[0])

    def test_a_bent_key_is_reported_not_crashed_on(self) -> None:
        """Khoá cong phải ra LỜI BÁO, không ra vết đổ.

        Ba dạng cong này từng làm lượt kiểm đổ chứ không trượt, mà vết đổ
        trỏ vào dòng ném lỗi nên giục người đọc đi sửa chỗ ném thay vì sửa
        phạm vi. ``True`` đáng ngờ nhất: nó là ``int`` trong Python nên lọt
        mọi phép ``isinstance(..., int)``, mà nó dồn toàn bộ chỗ so về một
        khoá — đúng cái sập phạm vi mà luật này sinh ra để chặn.
        """
        lines = ["if a in b:", "x = 1"]
        self.assertEqual([], sites_pointing_nowhere({"f:1": {"a"}}, lines))
        for bent in ("f", f"f:{True}", "f:99"):
            with self.subTest(bent=bent):
                reports = sites_pointing_nowhere({bent: {"a"}}, lines)
                self.assertEqual(1, len(reports))
                self.assertIn(bent, reports[0])

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
