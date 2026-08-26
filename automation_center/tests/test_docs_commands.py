"""Lệnh test in trong tài liệu phải chạy được y như đã in.

Bốn file test của Worker dựng lại schema thật bằng ``node:sqlite``.  Trên Node
22 thứ đó nằm sau cờ ``--experimental-sqlite``, và thiếu cờ thì chúng không
"đỏ" — chúng **chết** với ``ERR_UNKNOWN_BUILTIN_MODULE`` trước khi có test nào
chạy.  Người làm theo tài liệu sẽ đọc dòng cuối, thấy số test ít hơn thực tế,
và kết luận là máy mình hỏng.  Nên lệnh in trong tài liệu phải đúng.

Chạy:  python3 automation_center/tests/test_docs_commands.py
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CENTER = HERE.parent
ROOT = CENTER.parent

# Quét **mọi** tài liệu trong repo, không phải một danh sách chép tay: file
# tài liệu mới là chỗ lệnh hỏng dễ mọc lại nhất, mà danh sách cứng thì đúng
# những file mới ấy lại là những file không ai quét.
BO_QUA = {".git", ".venv", "node_modules", "dist", "build", ".mypy_cache"}

NODE_TEST = re.compile(r"node\s+--test[^\n`|]*")


def cac_file_tai_lieu() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*.md")
                  if not BO_QUA & set(path.relative_to(ROOT).parts))


def cac_lenh_node_test() -> list[tuple[Path, str]]:
    found = []
    for doc in cac_file_tai_lieu():
        for match in NODE_TEST.finditer(doc.read_text(encoding="utf-8")):
            found.append((doc, match.group(0).strip()))
    return found


class LenhTrongTaiLieu(unittest.TestCase):
    def test_moi_lenh_node_test_deu_co_co_experimental_sqlite(self):
        lenh = cac_lenh_node_test()
        self.assertTrue(lenh, "không tìm thấy lệnh node --test nào trong tài liệu")
        for doc, command in lenh:
            with self.subTest(doc=doc.name, command=command):
                self.assertIn(
                    "--experimental-sqlite", command,
                    f"{doc.relative_to(ROOT)}: “{command}” sẽ chết vì "
                    "ERR_UNKNOWN_BUILTIN_MODULE chứ không chạy")

    def test_van_con_file_dung_node_sqlite_nen_luat_tren_van_co_ly_do(self):
        # Neo lại lý do của cờ.  Ngày nào không còn file nào dùng node:sqlite
        # thì luật trên thành một luật vô cớ, và test này đỏ trước để nói ra.
        dung_sqlite = [path.name for path in sorted((CENTER / "tests").glob("*.test.mjs"))
                       if "node:sqlite" in path.read_text(encoding="utf-8")]
        self.assertGreaterEqual(
            len(dung_sqlite), 1,
            "không còn file test nào dùng node:sqlite — luật bắt buộc "
            "--experimental-sqlite ở trên đã hết lý do, hãy bỏ nó đi")

    def test_quet_duoc_ca_file_tai_lieu_moi(self):
        # Chốt của lần sửa trên: danh sách file là kết quả quét, không phải
        # danh sách chép tay — nên một tài liệu mới viết sai lệnh vẫn bị bắt.
        ten = {path.name for path in cac_file_tai_lieu()}
        self.assertIn("runner-host-runbook.md", ten)
        self.assertGreater(len(ten), 4, "chỉ quét đúng bốn file cũ thì chưa phải quét")


if __name__ == "__main__":
    unittest.main()
