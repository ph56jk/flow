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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flow_web.service import FlowWebService


def service() -> FlowWebService:
    return FlowWebService.__new__(FlowWebService)


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
    AST toàn bộ 33 hàm gọi hàm này thì ra 293 kim, 70 kim có chữ ``d``,
    và **tám** trong số đó sinh ra từ ``đ``. Ba khoá kia chỉ là ba khoá
    được nhớ tên, không phải cả tập.

    Sáu mươi hai kim còn lại đã phân loại tay ngày 2026-08-20 và KHÔNG
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
        """Mọi hằng ASCII được đem so với kết quả `_normalize_skill_token`."""
        source = Path(__file__).resolve().parents[1] / "flow_web" / "service.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        shape = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")

        def is_norm_call(node: ast.AST) -> bool:
            return (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_normalize_skill_token"
            )

        found: set[str] = set()

        def keep(value: object) -> None:
            if isinstance(value, str) and len(value) >= 2 and shape.match(value):
                found.add(value)

        def elements(node: ast.AST) -> list[ast.expr]:
            if isinstance(node, ast.Constant):
                return [node]
            if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
                return list(node.elts)
            return []

        functions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and any(is_norm_call(child) for child in ast.walk(node))
        ]
        self.assertEqual(self.FUNCTIONS_CALLING_THE_NORMALIZER, len(functions))

        for function in functions:
            literal_dicts: dict[str, ast.Dict] = {}
            normalized_names: set[str] = set()
            for node in ast.walk(function):
                if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                    continue
                target = node.targets[0]
                if not isinstance(target, ast.Name):
                    continue
                if any(is_norm_call(child) for child in ast.walk(node.value)):
                    normalized_names.add(target.id)
                if isinstance(node.value, ast.Dict):
                    literal_dicts[target.id] = node.value

            def looks_normalized(node: ast.AST) -> bool:
                return any(
                    is_norm_call(child)
                    or (isinstance(child, ast.Name) and child.id in normalized_names)
                    for child in ast.walk(node)
                )

            for node in ast.walk(function):
                # 1) so sánh thẳng: ``x == "kim"``, ``"kim" in x``, ``x in {...}``
                if isinstance(node, ast.Compare) and any(
                    isinstance(op, (ast.In, ast.NotIn, ast.Eq, ast.NotEq)) for op in node.ops
                ):
                    for part in (node.left, *node.comparators):
                        for element in elements(part):
                            if isinstance(element, ast.Constant):
                                keep(element.value)
                # 2) ``any(term in normalized for term in (...))``
                if (
                    isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp))
                    and isinstance(node.elt, ast.Compare)
                    and any(
                        isinstance(op, (ast.In, ast.NotIn, ast.Eq, ast.NotEq))
                        for op in node.elt.ops
                    )
                ):
                    for generator in node.generators:
                        for element in elements(generator.iter):
                            if isinstance(element, ast.Constant):
                                keep(element.value)
                # 3) ``mapping.get(normalized)`` — chỉ dict thật sự bị tra bằng token
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get"
                    and node.args
                    and looks_normalized(node.args[0])
                ):
                    receiver = node.func.value
                    table = receiver if isinstance(receiver, ast.Dict) else (
                        literal_dicts.get(receiver.id) if isinstance(receiver, ast.Name) else None
                    )
                    if isinstance(table, ast.Dict):
                        for key in table.keys:
                            if isinstance(key, ast.Constant):
                                keep(key.value)
        return found

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


if __name__ == "__main__":
    unittest.main()
