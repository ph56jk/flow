"""Codex CLI chỉ được là đường truyền chữ, không bao giờ là thứ ghi file.

Runner gọi model qua hai đường: HTTP tới OpenAI, hoặc ``codex exec`` đã đăng
nhập sẵn trên máy trung tâm.  Đường thứ hai nguy hiểm ở chỗ codex vốn *là* một
agent biết sửa file — nếu ai đó thêm một cờ mở quyền, model sẽ có một lối ghi
file không đi qua ``in_scope()`` và ``is_protected()``, và ba lớp an toàn của
runner mất tác dụng mà không có gì đỏ để nhìn.

Những bài dưới đây khoá tay nó lại: sandbox chỉ đọc, thư mục làm việc là thư mục
tạm rỗng chứ không phải bản repo của agent, lời nhắc đi qua stdin, và một lượt
hỏng thì báo lỗi chứ không treo runner.

Chạy:  python3 automation_center/tests/test_codex_provider.py
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

CENTER = Path(__file__).resolve().parent.parent
RUNNER = CENTER / "runner" / "orchestrator_runner.py"

CO_MO_QUYEN = (
    "workspace-write",
    "danger-full-access",
    "--add-dir",
    "--approve-for-me",
    "--dangerously-bypass-approvals-and-sandbox",
    "--dangerously-bypass-hook-trust",
)


def nap_runner():
    spec = importlib.util.spec_from_file_location("orchestrator_runner_duoi_test", RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runner = nap_runner()


def codex_gia(tra_loi: str, *, ma_thoat: int = 0, stderr: str = "", ghi_file: bool = True):
    da_goi = {}

    def chay(argv, **kwargs):
        da_goi["argv"] = list(argv)
        da_goi["stdin"] = kwargs.get("input")
        da_goi["timeout"] = kwargs.get("timeout")
        if ghi_file:
            vi_tri = argv.index("--output-last-message")
            Path(argv[vi_tri + 1]).write_text(tra_loi, encoding="utf-8")
        return SimpleNamespace(returncode=ma_thoat, stdout="", stderr=stderr)

    return chay, da_goi


TRA_LOI_MAU = json.dumps({
    "action": "answer",
    "summary": "xong",
    "paths": None,
    "files": None,
    "commands": None,
}, ensure_ascii=False)


class KhoaTayCodex(unittest.TestCase):
    def test_khong_bao_gio_cho_codex_quyen_ghi(self):
        argv = runner.codex_argv(
            "codex",
            work_dir=Path("/tmp/lam-viec"),
            schema_path=Path("/tmp/lam-viec/schema.json"),
            out_path=Path("/tmp/lam-viec/ra.json"),
        )
        self.assertIn("--sandbox", argv)
        self.assertEqual("read-only", argv[argv.index("--sandbox") + 1])
        for co in CO_MO_QUYEN:
            with self.subTest(co=co):
                self.assertNotIn(co, argv,
                                 f"{co} cho model một đường ghi file không đi qua "
                                 "in_scope() và is_protected()")

    def test_thu_muc_lam_viec_khong_phai_ban_repo_cua_agent(self):
        with tempfile.TemporaryDirectory() as repo:
            cu = runner.REPO_DIR
            runner.REPO_DIR = Path(repo)
            try:
                chay, da_goi = codex_gia(TRA_LOI_MAU)
                runner.call_codex([{"role": "user", "content": "chào"}], chay=chay)
            finally:
                runner.REPO_DIR = cu
            argv = da_goi["argv"]
            self.assertIn("--cd", argv)
            lam_viec = Path(argv[argv.index("--cd") + 1]).resolve()
            repo_path = Path(repo).resolve()
            self.assertNotEqual(lam_viec, repo_path)
            self.assertNotIn(repo_path, lam_viec.parents,
                             "thư mục làm việc của codex nằm trong bản repo của agent")

    def test_loi_nhac_di_qua_stdin_va_giu_du_moi_luot(self):
        chay, da_goi = codex_gia(TRA_LOI_MAU)
        runner.call_codex([
            {"role": "system", "content": "luật chơi"},
            {"role": "user", "content": "yêu cầu gốc"},
            {"role": "assistant", "content": '{"action":"read"}'},
            {"role": "user", "content": "nội dung file vừa đọc"},
        ], chay=chay)
        stdin = da_goi["stdin"] or ""
        for manh in ("luật chơi", "yêu cầu gốc", '{"action":"read"}', "nội dung file vừa đọc"):
            with self.subTest(manh=manh):
                self.assertIn(manh, stdin)
        self.assertNotIn("luật chơi", " ".join(da_goi["argv"]))

    def test_noi_thang_rang_khong_co_cong_cu_nao_dung_duoc(self):
        chay, da_goi = codex_gia(TRA_LOI_MAU)
        runner.call_codex([{"role": "user", "content": "chào"}], chay=chay)
        self.assertIn("read", (da_goi["stdin"] or "").lower())
        self.assertRegex(da_goi["stdin"] or "", r"không.*(shell|công cụ)")

    def test_co_timeout_cung(self):
        chay, da_goi = codex_gia(TRA_LOI_MAU)
        runner.call_codex([{"role": "user", "content": "chào"}], chay=chay)
        self.assertTrue(da_goi["timeout"], "thiếu timeout thì một lượt hỏng treo runner vô hạn")


class ChonNhaCungCap(unittest.TestCase):
    def test_khong_co_khoa_thi_dung_codex(self):
        self.assertEqual("codex", runner.chon_nha_cung_cap("auto", "", "/usr/bin/codex"))

    def test_co_khoa_thi_giu_duong_http_cu(self):
        self.assertEqual("openai", runner.chon_nha_cung_cap("auto", "sk-abc", "/usr/bin/codex"))

    def test_ep_duoc_tung_ben(self):
        self.assertEqual("codex", runner.chon_nha_cung_cap("codex", "sk-abc", "/usr/bin/codex"))
        self.assertEqual("openai", runner.chon_nha_cung_cap("openai", "sk-abc", None))

    def test_khong_co_duong_nao_thi_bao_thang(self):
        for cai_dat, khoa, codex in (("auto", "", None), ("codex", "sk-abc", None), ("openai", "", "/usr/bin/codex")):
            with self.subTest(cai_dat=cai_dat):
                with self.assertRaises(RuntimeError):
                    runner.chon_nha_cung_cap(cai_dat, khoa, codex)


class DocKetQua(unittest.TestCase):
    def test_doc_duoc_json_tran(self):
        self.assertEqual({"action": "answer"}, runner.doc_ket_qua_codex('{"action": "answer"}'))

    def test_doc_duoc_json_boc_trong_hang_rao(self):
        raw = 'Đây là kết quả:\n```json\n{"action": "answer", "summary": "ừ"}\n```\n'
        self.assertEqual("answer", runner.doc_ket_qua_codex(raw)["action"])

    def test_khong_phai_json_thi_bao_loi_kem_nguyen_van(self):
        with self.assertRaises(RuntimeError) as bat:
            runner.doc_ket_qua_codex("xin lỗi, tôi không làm được")
        self.assertIn("xin lỗi", str(bat.exception))

    def test_codex_thoat_loi_thi_khong_nuot(self):
        chay, _ = codex_gia("", ma_thoat=1, stderr="not logged in", ghi_file=False)
        with self.assertRaises(RuntimeError) as bat:
            runner.call_codex([{"role": "user", "content": "chào"}], chay=chay)
        self.assertIn("not logged in", str(bat.exception))

    def test_qua_gio_thi_bao_loi_chu_khong_treo(self):
        def chay(argv, **kwargs):
            raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout") or 1)

        with self.assertRaises(RuntimeError):
            runner.call_codex([{"role": "user", "content": "chào"}], chay=chay)


class LuocDoRaCuaCodex(unittest.TestCase):
    def test_phu_du_bon_hanh_dong_va_moi_khoa_runner_doc(self):
        luoc_do = runner.CODEX_OUTPUT_SCHEMA
        self.assertEqual(
            {"read", "answer", "edit", "bot"},
            set(luoc_do["properties"]["action"]["enum"]))
        for khoa in ("action", "summary", "paths", "files", "commands"):
            with self.subTest(khoa=khoa):
                self.assertIn(khoa, luoc_do["properties"])
                self.assertIn(khoa, luoc_do["required"])
        tep = luoc_do["properties"]["files"]["items"]
        self.assertEqual({"path", "content"}, set(tep["properties"]))
        lenh = luoc_do["properties"]["commands"]["items"]
        self.assertEqual({"bot_id", "command", "prompt", "count", "aspect"}, set(lenh["properties"]))

    def test_luoc_do_la_json_hop_le(self):
        json.loads(json.dumps(runner.CODEX_OUTPUT_SCHEMA))


if __name__ == "__main__":
    unittest.main()
