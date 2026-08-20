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
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
