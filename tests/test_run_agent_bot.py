"""``scripts/run_agent_bot.py`` phải dựng bot đủ hai loại việc.

Script này là đường chạy bot ở một máy **không** có Flow — đúng cảnh mà bản
Listing sinh ra để phục vụ. Nếu nó dựng bot mà quên nối cầu Listing thì bot vẫn
sống, vẫn quét, vẫn dọn phiếu, và mọi thẻ ``action_1: listing`` nhận đúng một
câu trả lời: "chưa cấu hình ERP_LISTING_API_URL" — kể cả khi biến đó đã được
đặt đàng hoàng trong ``.env.local``. Không có gì đỏ, không có gì kêu.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import unittest
from pathlib import Path
from typing import Any, Dict
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_script():
    spec = importlib.util.spec_from_file_location(
        "run_agent_bot_script", ROOT / "scripts" / "run_agent_bot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = load_script()


class BotGia:
    async def run_once(self) -> Dict[str, Any]:
        return {"scanned": 0}


class DungBotDuHaiLoaiViec(unittest.TestCase):
    def _chay(self, env: Dict[str, str]) -> Dict[str, Any]:
        ghi_lai: Dict[str, Any] = {}

        def build(config, **kwargs):
            ghi_lai.update(kwargs)
            ghi_lai["config"] = config
            return BotGia()

        moi_truong = {
            "ERP_AGENT_TOKEN": "token-gia-cho-test",
            "ERP_API_URL": "https://erp.invalid/api/method/hvg_workspace.api.graphql",
            "ERP_LISTING_API_URL": "",
            "ERP_LISTING_MACHINE": "",
            "ERP_LISTING_MACHINES": "",
            **env,
        }
        with mock.patch.dict(os.environ, moi_truong, clear=False), \
                mock.patch.object(script, "build_agent_bot", build), \
                mock.patch.object(script, "load_local_env", lambda: None):
            ma = asyncio.run(script.main(["--once", "--dry-run"]))
        self.assertEqual(ma, 0)
        return ghi_lai

    def test_da_dat_erp_listing_api_url_thi_cau_listing_duoc_noi(self):
        ghi_lai = self._chay({"ERP_LISTING_API_URL": "http://127.0.0.1:9100",
                              "ERP_LISTING_MACHINE": "may-01"})
        self.assertIsNotNone(
            ghi_lai.get("listing_hook"),
            "script dựng bot mà không truyền listing_hook: mọi thẻ listing sẽ "
            "nhận 'chưa cấu hình ERP_LISTING_API_URL' dù biến đã được đặt")

    def test_chua_dat_thi_hook_van_la_none_chu_khong_dung_cau_hong(self):
        # Chưa dựng bản Listing thì im lặng nhận diện rồi để yên là đúng — nối
        # một cầu trỏ vào hư không còn tệ hơn: mỗi thẻ thành một lần chờ timeout.
        ghi_lai = self._chay({})
        self.assertIsNone(ghi_lai.get("listing_hook"))

    def test_khong_co_flow_web_url_thi_van_khong_tu_chay_flow(self):
        # Ranh giới cũ, giữ nguyên: một máy không có Flow thì phần tạo ảnh phải
        # tắt hẳn chứ không được âm thầm không làm gì.
        ghi_lai = self._chay({"ERP_LISTING_API_URL": "http://127.0.0.1:9100"})
        self.assertIsNone(ghi_lai.get("autorun_hook"))
        self.assertFalse(ghi_lai["config"].autorun)


if __name__ == "__main__":
    unittest.main()
