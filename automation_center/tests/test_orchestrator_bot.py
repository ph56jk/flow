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


class DiffBiCatThiPhaiNoiRaLaBiCat(unittest.TestCase):
    """Cờ "diff đã bị cắt" phải do runner gửi, không phải Worker đoán.

    Runner là chỗ **duy nhất** còn nhìn thấy diff đầy đủ.  Thứ gửi lên Center
    đã cắt sẵn, nên bên kia so độ dài trước/sau lúc nào cũng thấy bằng nhau và
    kết luận "không bị cắt" — người duyệt đọc nửa diff mà màn hình báo là đủ.
    """

    def setUp(self):
        self.reported = []
        self.saved = {name: getattr(runner, name) for name in (
            "report", "git", "plan_change", "require_clean_repo",
            "write_files", "staged_stats", "run_tests", "is_cancelled")}
        runner.report = lambda request_id, status, **extra: (
            self.reported.append((request_id, status, extra)) or {})
        runner.git = lambda *args, **kwargs: (
            "deadbeefcafe\n" if args[:1] == ("rev-parse",) else "")
        runner.require_clean_repo = lambda: None
        runner.write_files = lambda entries, allow_globs, max_files: ["flow_web/x.py"]
        runner.run_tests = lambda: (True, "test xanh")
        runner.is_cancelled = lambda request_id: False
        runner.plan_change = lambda request, scope: {
            "action": "edit", "summary": "sửa một dòng",
            "files": [{"path": "flow_web/x.py", "content": "y\n"}]}

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(runner, name, value)

    def _run(self, diff: str):
        runner.staged_stats = lambda: (["flow_web/x.py"], 3, diff)
        runner.handle_request({"id": "req-diff", "scope": {
            "allow_globs": ["flow_web/**"], "max_files": 3, "max_lines": 200}})
        self.assertEqual(len(self.reported), 1, self.reported)
        request_id, status, extra = self.reported[0]
        self.assertEqual(status, "awaiting_approval", extra.get("error"))
        return extra

    def test_diff_dai_hon_tran_thi_cat_va_bao_da_cat(self):
        extra = self._run("d" * (runner.DIFF_LIMIT + 4000))
        self.assertEqual(extra["diff_truncated"], 1)
        self.assertEqual(len(extra["diff_text"]), runner.DIFF_LIMIT)

    def test_diff_vua_tran_thi_khong_bao_nham_la_da_cat(self):
        # Báo nhầm cũng hỏng theo kiểu khác: cảnh báo đỏ hiện ở mọi yêu cầu thì
        # chẳng ai còn đọc nó, và lần bị cắt thật sẽ trôi qua như mọi lần.
        extra = self._run("d" * runner.DIFF_LIMIT)
        self.assertEqual(extra["diff_truncated"], 0)
        self.assertEqual(len(extra["diff_text"]), runner.DIFF_LIMIT)

    def test_diff_ngan_thi_di_nguyen_ven(self):
        extra = self._run("diff --git a/x b/x\n+một dòng\n")
        self.assertEqual(extra["diff_truncated"], 0)
        self.assertEqual(extra["diff_text"], "diff --git a/x b/x\n+một dòng\n")


class MergeXongThiDonNhanh(unittest.TestCase):
    """Nhánh ``agent/<id>`` đã merge phải bị xoá ngay tại chỗ.

    Máy trung tâm chạy hết yêu cầu này tới yêu cầu khác trên cùng một bản làm
    việc.  Nhánh đã merge không còn nghĩa gì nữa nhưng vẫn nằm lại, nên sau vài
    chục lượt ``git branch`` là một danh sách rác — và ngày nào tên nhánh trùng
    lại (12 ký tự đầu của id) thì ``checkout -B`` ghi đè im lặng lên nhánh cũ.
    """

    def setUp(self):
        self.reported = []
        self.git_calls = []
        self.saved = {name: getattr(runner, name)
                      for name in ("report", "git", "require_clean_repo")}
        runner.report = lambda request_id, status, **extra: (
            self.reported.append((request_id, status, extra)) or {})

        def fake_git(*args, **kwargs):
            self.git_calls.append(args)
            return "deadbeefcafe\n" if args[:1] == ("rev-parse",) else ""

        runner.git = fake_git
        runner.require_clean_repo = lambda: None

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(runner, name, value)

    def test_merge_xong_thi_xoa_nhanh(self):
        runner.apply_approved({"id": "req-2", "branch": "agent/abc123"})
        self.assertIn(("branch", "-D", "agent/abc123"), self.git_calls)
        # Xoá **sau** khi merge, không phải trước: xoá trước là mất luôn thay đổi.
        self.assertLess(self.git_calls.index(("merge", "--no-edit", "agent/abc123")),
                        self.git_calls.index(("branch", "-D", "agent/abc123")))
        self.assertEqual(self.reported[-1][1], "applied")

    def test_merge_hong_thi_giu_nhanh_lai_de_con_xem(self):
        def fake_git(*args, **kwargs):
            self.git_calls.append(args)
            if args[:1] == ("merge",) and "--abort" not in args:
                raise RuntimeError("xung đột")
            return ""

        runner.git = fake_git
        runner.apply_approved({"id": "req-3", "branch": "agent/abc123"})
        self.assertNotIn(("branch", "-D", "agent/abc123"), self.git_calls)
        self.assertEqual(self.reported[-1][1], "failed")



if __name__ == "__main__":
    unittest.main(verbosity=2)
