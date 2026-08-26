"""Worker (JS) và runner (Python) phải trả lời giống nhau về phạm vi.

Hai lớp kiểm phạm vi trùng nhau là cố ý: runner từ chối *ghi* file ngoài phạm
vi, Worker từ chối *nhận* kết quả ngoài phạm vi.  Nhưng hai bản cài đặt trùng
nhau thì sẽ trôi khỏi nhau, và một chỗ trôi ở đây nghĩa là một file lẽ ra được
bảo vệ lại đi lọt.  Test này bắt cái trôi đó.

Chạy:  python3 -m unittest automation_center.tests.test_scope_parity
   hoặc: python3 automation_center/tests/test_scope_parity.py
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
CENTER = HERE.parent
WORKER = CENTER / "src" / "worker.js"


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "orchestrator_runner", CENTER / "runner" / "orchestrator_runner.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load_runner()

# Đường dẫn thật trong repo, cộng những kiểu lách mà một agent bị lái có thể thử.
PATHS = [
    ".env", ".env.local", ".env.worker-dev.local",
    "flow-v2/.env.local", "a/b/c/.env", "a/b/.env.production",
    "automation_center/runner/orchestrator.env",
    "automation_center/runner/content_image_runner.py",
    "automation_center/src/worker.js",
    "automation_center/src/other.js",
    "automation_center/public/app.js",
    "automation_center/public/styles.css",
    "automation_center/migrations/0004_orchestrator_agent.sql",
    "automation_center/migrations/nested/x.sql",
    "automation_center/scripts/set-runner-secret.sh",
    "automation_center/wrangler.jsonc",
    "wrangler.jsonc", "wrangler.toml", "a/b/wrangler.toml",
    ".gitignore", ".github/workflows/deploy.yml", ".github/a/b/c.yml",
    "keys/server.pem", "keys/deep/nested/id.key",
    "docs/credentials-rotation.md", "src/secret_helper.py",
    "flow_web/service.py", "flow_web/static/app.js",
    "tests/test_erp_review.py", "README.md",
    "notenv/app.py", "environment/setup.py", "my.envelope.txt",
    # Hoa thường: máy trung tâm chạy Windows nên đây là cùng một file.
    ".ENV", "Flow-v2/.Env.Local", "src/Secrets.json", "docs/CREDENTIALS.md",
    "keys/Server.PEM", "AUTOMATION_CENTER/src/worker.js",
    # Biên của mẫu, nơi hai bản cài đặt dễ trôi khỏi nhau nhất.
    ".env.d/foo", "a/.env.d/b/c", "github.io/x.js", ".githubx/y.yml",
    "x/wrangler.jsonc/y.txt", "keys/a.pem/b.txt", "a/b/.github/w.yml",
]

SCOPES = [
    ["**"],
    ["flow_web/**"],
    ["flow_web/*"],
    ["flow_web/*/*.js"],
    ["automation_center/public/**"],
    ["docs/*.md"],
    ["**/*.py"],
    ["automation_center/**/*.js"],
    [],
]


def js_verdicts() -> dict:
    """Hỏi chính bản cài đặt của Worker, không chép lại logic của nó."""
    script = f"""
    import {{ isProtectedPath, matchesAnyGlob }} from {json.dumps(str(WORKER))};
    const paths = {json.dumps(PATHS)};
    const scopes = {json.dumps(SCOPES)};
    console.log(JSON.stringify({{
      protected: paths.map(isProtectedPath),
      scope: scopes.map((globs) => paths.map((path) => matchesAnyGlob(path, globs))),
    }}));
    """
    out = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        capture_output=True, text=True, check=True, cwd=CENTER)
    return json.loads(out.stdout)


@unittest.skipIf(shutil.which("node") is None, "cần node để đọc bản cài đặt của Worker")
class ScopeParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = js_verdicts()

    def test_runner_khong_long_hon_worker_ve_file_bao_ve(self):
        # Không đòi hai bên khớp tuyệt đối: runner dùng fnmatch, Worker dùng
        # glob "**", nên runner chặt hơn ở vài chỗ (ví dụ ".env.d/foo").  Chặt
        # hơn là hướng an toàn — file đó không bao giờ được ghi.  Điều KHÔNG
        # được phép là ngược lại: runner ghi một file mà Worker coi là bảo vệ.
        for path, worker_says in zip(PATHS, self.js["protected"]):
            if not worker_says:
                continue
            with self.subTest(path=path):
                self.assertTrue(
                    runner.is_protected(path),
                    f"{path}: Worker coi là file bảo vệ nhưng runner sẵn sàng ghi")

    def test_khong_ben_nao_bo_sot_file_bi_mat(self):
        # Cả hai cùng lỏng theo một kiểu vẫn là "khớp nhau", nên neo lại danh
        # sách tuyệt đối ở cả hai phía.
        must_block = [
            ".env", ".env.local", "a/b/c/.env", ".ENV", "Flow-v2/.Env.Local",
            "automation_center/runner/orchestrator.env",
            "automation_center/src/worker.js",
            "keys/server.pem", "keys/Server.PEM", "src/Secrets.json",
            "docs/CREDENTIALS.md", "automation_center/migrations/0004_orchestrator_agent.sql",
        ]
        js_by_path = dict(zip(PATHS, self.js["protected"]))
        for path in must_block:
            with self.subTest(path=path):
                self.assertTrue(js_by_path[path], f"{path}: Worker để lọt")
                self.assertTrue(runner.is_protected(path), f"{path}: runner để lọt")

    def test_khop_pham_vi_khop_nhau(self):
        for globs, expected_row in zip(SCOPES, self.js["scope"]):
            for path, expected in zip(PATHS, expected_row):
                with self.subTest(globs=globs, path=path):
                    self.assertEqual(
                        runner.in_scope(path, globs), expected,
                        f"{globs} vs {path}: Worker nói {expected}, runner nói "
                        f"{runner.in_scope(path, globs)}")

    def test_chuan_hoa_duong_dan_khop_nhau(self):
        cases = ["../../etc/passwd", "flow_web/../.env.local", "/etc/passwd",
                 "C:/Windows/x.dll", "flow_web//service.py", "./service.py",
                 "a\nb.py", "", "flow_web\\static\\app.js", "flow_web/static/app.js"]
        script = f"""
        import {{ normaliseRepoPath }} from {json.dumps(str(WORKER))};
        console.log(JSON.stringify({json.dumps(cases)}.map(normaliseRepoPath)));
        """
        out = subprocess.run(["node", "--input-type=module", "--eval", script],
                             capture_output=True, text=True, check=True, cwd=CENTER)
        for raw, expected in zip(cases, json.loads(out.stdout)):
            with self.subTest(raw=raw):
                self.assertEqual(runner.normalise_path(raw), expected)

    def test_tran_diff_hai_ben_bang_nhau(self):
        # Runner cắt diff rồi gửi kèm cờ "đã cắt"; Worker cắt lần nữa và tự bật
        # cờ khi chính nó là bên cắt.  Hai trần lệch nhau thì cờ nói dối theo
        # đúng một trong hai chiều — hoặc bỏ sót diff bị cắt, hoặc dựng cảnh
        # báo đỏ trên diff còn nguyên.  Cả hai đều làm hỏng bước duyệt.
        script = f"""
        import {{ CONTROL_LIMITS }} from {json.dumps(str(WORKER))};
        console.log(JSON.stringify(CONTROL_LIMITS.DIFF_TEXT_MAX));
        """
        out = subprocess.run(["node", "--input-type=module", "--eval", script],
                             capture_output=True, text=True, check=True, cwd=CENTER)
        self.assertEqual(runner.DIFF_LIMIT, json.loads(out.stdout))

    def test_file_bi_mat_that_su_bi_chan_o_ca_hai_ben(self):
        # Không chỉ "giống nhau" — phải giống nhau ở phía chặn.  Hai bên cùng
        # sai theo một kiểu vẫn là parity, nên neo lại vài trường hợp tuyệt đối.
        for path in [".env", ".env.local", "a/b/c/.env",
                     "automation_center/runner/orchestrator.env",
                     "automation_center/src/worker.js", "keys/server.pem"]:
            with self.subTest(path=path):
                self.assertTrue(runner.is_protected(path))
        for path in ["flow_web/service.py", "automation_center/public/app.js"]:
            with self.subTest(path=path):
                self.assertFalse(runner.is_protected(path))


class KhungQuyChieuDuongDan(unittest.TestCase):
    """Lớp bảo vệ chỉ đúng khi REPO_DIR là gốc git — khoá lại điều đó.

    Bốn mục trong ``PROTECTED_GLOBS`` neo ở gốc repo và không mở đầu bằng
    ``**/``.  Nếu runner báo đường dẫn tính từ *gốc git* trong khi gốc git nằm
    cao hơn REPO_DIR, bốn mục ấy hết tác dụng mà không kêu một tiếng.
    """

    def _repo(self, tmp: Path, nested: bool) -> Path:
        root = tmp / "workspace"
        work = root / "flow-v2" if nested else root
        (work / "automation_center" / "src").mkdir(parents=True)
        (work / "automation_center" / "src" / "worker.js").write_text("x\n")
        (work / "flow_web").mkdir()
        (work / "flow_web" / "service.py").write_text("x\n")
        for args in (["init", "-q", "-b", "main"],
                     ["config", "user.email", "t@t"],
                     ["config", "user.name", "t"],
                     ["add", "-A"],
                     ["-c", "commit.gpgsign=false", "commit", "-q", "--no-verify", "-m", "init"]):
            subprocess.run(["git", *args], cwd=root, check=True,
                           capture_output=True, text=True)
        return work

    def test_hai_lenh_git_dem_theo_hai_khung_khac_nhau(self):
        # Tiền đề của cả lớp bảo vệ, đo chứ không tin: ``ls-files`` đếm từ thư
        # mục đang đứng, ``diff --numstat`` đếm từ gốc git.  Ngày nào git đổi
        # điều này thì test đỏ ở đây trước, chứ không đỏ ở chỗ file bị ghi.
        with tempfile.TemporaryDirectory() as raw:
            work = self._repo(Path(raw), nested=True)
            (work / "automation_center" / "src" / "worker.js").write_text("x\ny\n")
            subprocess.run(["git", "add", "-A"], cwd=work, check=True, capture_output=True)
            def run(*args):
                return subprocess.run(["git", *args], cwd=work, check=True,
                                      capture_output=True, text=True).stdout
            self.assertIn("automation_center/src/worker.js\n", run("ls-files"))
            self.assertNotIn("flow-v2/", run("ls-files"))
            self.assertIn("flow-v2/automation_center/src/worker.js",
                          run("diff", "--cached", "--numstat"))

    def test_worker_js_chi_duoc_bao_ve_o_khung_repo(self):
        # Đây là thiệt hại thật khi hai khung lệch nhau, viết thẳng ra để ai
        # đọc cũng thấy vì sao `require_repo_root` là bắt buộc.
        self.assertTrue(runner.is_protected("automation_center/src/worker.js"))
        self.assertFalse(runner.is_protected("flow-v2/automation_center/src/worker.js"))
        self.assertTrue(runner.is_protected("automation_center/migrations/0001.sql"))
        self.assertFalse(runner.is_protected("flow-v2/automation_center/migrations/0001.sql"))

    def test_dan_test_duong_dan_thuong_khong_bat_duoc_lech_khung(self):
        # Vì sao lỗi này sống lâu: mọi mục còn lại đều có anh em ``**/`` nên
        # thêm tiền tố vào cũng không đổi kết quả.  Một dàn test chỉ có .env và
        # wrangler.jsonc sẽ xanh trong khi worker.js đã mất bảo vệ.
        for path in (".env", ".env.local", "wrangler.jsonc", "credentials.json",
                     "keys/server.pem"):
            with self.subTest(path=path):
                self.assertEqual(runner.is_protected(path),
                                 runner.is_protected(f"flow-v2/{path}"),
                                 f"{path}: tiền tố đổi kết quả, mục này KHÔNG che lỗi")

    def test_repo_dir_la_thu_muc_con_thi_runner_tu_choi_chay(self):
        # Điều người vận hành thấy: trỏ AGENT_REPO_DIR vào bản clone lồng nhau
        # thì runner không chạy.  Ở bố cục này chốt chặn là ``.git`` không nằm
        # tại REPO_DIR, nên câu báo là câu "không phải một repo git" — vẫn là
        # từ chối, và đó mới là điều cần khoá.
        with tempfile.TemporaryDirectory() as raw:
            work = self._repo(Path(raw), nested=True)
            with mock.patch.object(runner, "REPO_DIR", work):
                with self.assertRaises(RuntimeError) as caught:
                    runner.require_repo_root()
                self.assertEqual(runner.repo_prefix(), "flow-v2/")
        self.assertIn(str(work), str(caught.exception))

    def test_co_git_tai_repo_dir_nhung_goc_o_cho_khac_thi_van_bi_tu_choi(self):
        # Nhánh thứ hai của `require_repo_root`, cái mà chốt ``.git`` không đỡ
        # được: nếu ngày nào đó chốt kia được nới ra cho chạy từ thư mục con —
        # nghe rất tiện — thì đây là thứ giữ lớp bảo vệ lại.
        with tempfile.TemporaryDirectory() as raw:
            work = self._repo(Path(raw), nested=False)
            with mock.patch.object(runner, "REPO_DIR", work), \
                 mock.patch.object(runner, "repo_prefix", lambda: "flow-v2/"):
                with self.assertRaises(RuntimeError) as caught:
                    runner.require_repo_root()
        self.assertIn("PROTECTED_GLOBS", str(caught.exception))

    def test_duong_dan_staged_duoc_quy_ve_khung_repo(self):
        # `staged_stats` tự quy đổi, không phụ thuộc vào việc ai đã gọi
        # `require_repo_root` trước đó: dựng đúng bố cục lồng nhau rồi đọc thẳng.
        with tempfile.TemporaryDirectory() as raw:
            work = self._repo(Path(raw), nested=True)
            (work / "automation_center" / "src" / "worker.js").write_text("x\ny\n")
            subprocess.run(["git", "add", "-A"], cwd=work, check=True, capture_output=True)
            with mock.patch.object(runner, "REPO_DIR", work):
                paths, _, _ = runner.staged_stats()
        self.assertEqual(paths, ["automation_center/src/worker.js"])
        self.assertTrue(runner.is_protected(paths[0]),
                        "đường dẫn trả ra phải là thứ `is_protected` nhận ra")

    def test_staged_stats_tra_diff_day_du_chu_khong_tu_cat(self):
        # Đây là chỗ **duy nhất** còn nhìn thấy diff đầy đủ.  Cắt ngay tại đây
        # là vứt mất thông tin "đã cắt" trước khi có ai kịp ghi nó lại: thứ gửi
        # lên Center sẽ luôn vừa khít trần, nên bên kia đo bao nhiêu cũng kết
        # luận "còn nguyên" — người duyệt đọc nửa diff mà màn hình báo là đủ.
        # Cắt là việc của `handle_request`, sau khi đã đặt cờ.
        with tempfile.TemporaryDirectory() as raw:
            work = self._repo(Path(raw), nested=False)
            (work / "flow_web" / "service.py").write_text(
                "".join(f"dong so {i}\n" for i in range(8000)))
            subprocess.run(["git", "add", "-A"], cwd=work, check=True, capture_output=True)
            with mock.patch.object(runner, "REPO_DIR", work):
                _, _, diff = runner.staged_stats()
        self.assertGreater(
            len(diff), runner.DIFF_LIMIT,
            "staged_stats đã cắt diff — cờ diff_truncated sẽ không bao giờ bật")

    def test_repo_dir_la_goc_thi_staged_stats_noi_bang_khung_repo(self):
        with tempfile.TemporaryDirectory() as raw:
            work = self._repo(Path(raw), nested=False)
            (work / "automation_center" / "src" / "worker.js").write_text("x\ny\n")
            subprocess.run(["git", "add", "-A"], cwd=work, check=True, capture_output=True)
            with mock.patch.object(runner, "REPO_DIR", work):
                runner.require_repo_root()
                paths, lines, _ = runner.staged_stats()
            self.assertEqual(paths, ["automation_center/src/worker.js"])
            self.assertTrue(runner.is_protected(paths[0]))
            self.assertEqual(lines, 1)


# Đặt cuối file, không đặt giữa: unittest.main() chạy đúng những lớp đã được
# nạp tới thời điểm nó chạy.  Nằm trước một lớp test là bỏ sót lớp đó mà vẫn
# in "OK" — đúng cái kiểu hỏng mà một file test không được phép có.
if __name__ == "__main__":
    unittest.main()
