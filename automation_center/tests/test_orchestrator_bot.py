"""Agent điều phối điều khiển bot khác: ranh giới ở phía runner.

Quyền thật nằm ở Worker — nhánh ``bot_action`` kiểm lại ``capability(role,
"run")`` rồi chạy đúng lõi mà nút bấm trên web dùng.  Nhưng runner là nơi
quyết định *có gửi lệnh nào đi hay không*, và nó cũng là nơi duy nhất chạm vào
git.  Test này khoá hai điều: runner không rò tên bot cho người không có
quyền, và một yêu cầu điều khiển bot không được đụng vào repo.

Chạy:  python3 automation_center/tests/test_orchestrator_bot.py
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CENTER = HERE.parent


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "orchestrator_runner", CENTER / "runner" / "orchestrator_runner.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load_runner()

BOTS = [
    {"id": "bot-anh", "name": "Agent tạo ảnh", "status": "active"},
    {"id": "bot-erp", "name": "Đăng ERP", "status": "paused"},
]


class NguCanhBot(unittest.TestCase):
    def test_khong_co_quyen_thi_khong_thay_ten_bot(self):
        # Center vẫn chặn lần nữa, nhưng đưa danh sách bot cho một người không
        # điều khiển được bot là mời model thử — và mỗi lần thử là một yêu cầu
        # thất bại mà người dùng phải tự hiểu vì sao.
        lines = runner.bot_context_lines(
            {"may_control_bots": False, "bots": BOTS})
        joined = "\n".join(lines)
        self.assertNotIn("bot-anh", joined)
        self.assertNotIn("bot-erp", joined)

    def test_co_quyen_thi_thay_du_id_de_goi_dung(self):
        joined = "\n".join(runner.bot_context_lines(
            {"may_control_bots": True, "bots": BOTS}))
        self.assertIn("bot-anh", joined)
        self.assertIn("bot-erp", joined)

    def test_khong_co_bot_nao_thi_noi_thang_la_khong_co(self):
        joined = "\n".join(runner.bot_context_lines(
            {"may_control_bots": True, "bots": []}))
        self.assertNotIn("bot_id=", joined)


class DieuKhienBotKhongChamGit(unittest.TestCase):
    """``handle_request`` với action "bot" phải báo cáo rồi dừng.

    Chạm git ở đây nghĩa là một lệnh "dừng bot" cũng có thể làm bẩn bản làm
    việc của agent, và lần sửa code kế tiếp sẽ hỏng vì lý do không liên quan.
    """

    def setUp(self):
        self.reported = []
        self.git_calls = []
        self._report = runner.report
        self._git = runner.git
        self._plan = runner.plan_change
        runner.report = lambda request_id, status, **extra: (
            self.reported.append((request_id, status, extra)) or {})
        runner.git = lambda *args, **kwargs: self.git_calls.append(args) or ""

    def tearDown(self):
        runner.report = self._report
        runner.git = self._git
        runner.plan_change = self._plan

    def request(self):
        return {"id": "req-1", "scope": {"allow_globs": ["flow_web/**"],
                                         "max_files": 3, "max_lines": 200}}

    def test_lenh_bot_duoc_chuyen_di_ma_khong_dung_toi_repo(self):
        commands = [{"bot_id": "bot-anh", "command": "pause"}]
        runner.plan_change = lambda request, scope: {
            "action": "bot", "summary": "Tạm dừng bot tạo ảnh", "commands": commands}
        runner.handle_request(self.request())
        self.assertEqual(self.git_calls, [])
        self.assertEqual(len(self.reported), 1)
        request_id, status, extra = self.reported[0]
        self.assertEqual((request_id, status), ("req-1", "bot_action"))
        self.assertEqual(extra["bot_commands"], commands)

    def test_nhieu_lenh_bi_cat_con_nam(self):
        # Trần này lặp lại trần của Worker.  Một model đi chệch có thể sinh ra
        # hàng chục lệnh; cắt ở cả hai đầu để không bên nào là chỗ duy nhất giữ.
        runner.plan_change = lambda request, scope: {
            "action": "bot", "summary": "x",
            "commands": [{"bot_id": f"bot-{i}", "command": "run"} for i in range(9)]}
        runner.handle_request(self.request())
        self.assertEqual(len(self.reported[0][2]["bot_commands"]), 5)

    def test_noi_dieu_khien_bot_nhung_khong_dua_lenh_nao_thi_that_bai(self):
        runner.plan_change = lambda request, scope: {
            "action": "bot", "summary": "Tôi sẽ dừng bot", "commands": []}
        runner.handle_request(self.request())
        self.assertEqual(self.reported[0][1], "failed")
        self.assertEqual(self.git_calls, [])

    def test_khong_co_pham_vi_thi_khong_toi_duoc_buoc_hoi_chatgpt(self):
        # Người chưa được cấp phạm vi không dùng agent được, kể cả để điều
        # khiển bot: Worker đã chặn từ lúc xếp việc, runner chặn lại lần nữa.
        def khong_duoc_goi(request, scope):
            raise AssertionError("plan_change không được chạy khi thiếu phạm vi")

        runner.plan_change = khong_duoc_goi
        runner.handle_request({"id": "req-2", "scope": {"allow_globs": []}})
        self.assertEqual(self.reported[0][1], "failed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
