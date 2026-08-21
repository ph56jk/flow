"""Giao thẻ listing sang bản Listing: đúng máy, đúng việc, hoặc không giao.

Đợt thử đầu tiên ghim vào một máy Etsy duy nhất, nên ba câu hỏi quan trọng
nhất ở đây là "thẻ này về máy nào", "gửi cái gì" và "đầu kia trả lời thế nào
thì coi là xong". Payload phải trùng đúng lược đồ bản Listing nhận — sai một
tên trường thì đầu kia im lặng làm sai chứ không báo lỗi.
"""

from __future__ import annotations

import unittest
from typing import Any, Dict, List
from unittest.mock import patch

from flow_web.listing_bridge import (
    ListingBridge,
    ListingBridgeConfig,
    ListingBridgeError,
    build_listing_hook,
)

LISTING_CARD = {
    "name": "TASK-2026-00700",
    "subject": "Khăn tay hoa cúc",
    "meta": "action_1: listing\nacc: acc32\n",
}

QUEUED = {
    "etsy_browser_copy": {
        "configured": True,
        "browser_automation_ready": True,
        "enqueued": True,
        "sku": "HV-1234",
        "image_count": 6,
        "queue_task": {"id": "etsy-copy-abc123", "status": "queued"},
    }
}


class Recorder:
    """Chỗ nhận request thay cho một cổng thật."""

    def __init__(self, response: Dict[str, Any] | None = None) -> None:
        self.calls: List[tuple[str, Dict[str, Any], int]] = []
        self.response = QUEUED if response is None else response

    def __call__(self, url: str, payload: Dict[str, Any], timeout_s: int) -> Dict[str, Any]:
        self.calls.append((url, payload, timeout_s))
        return self.response


def bridge(recorder: Recorder | None = None, **overrides) -> ListingBridge:
    config = ListingBridgeConfig(
        api_url="http://127.0.0.1:8010",
        machines=("etsy-vn32", "etsy-vn16"),
        **overrides,
    )
    return ListingBridge(config, transport=recorder or Recorder())


class ConfigTests(unittest.TestCase):
    def test_no_url_means_off_rather_than_broken(self) -> None:
        self.assertFalse(ListingBridgeConfig().enabled)
        self.assertIsNone(build_listing_hook(ListingBridge(ListingBridgeConfig())))

    def test_the_environment_names_the_backend_and_its_fleet(self) -> None:
        env = {
            "ERP_LISTING_API_URL": "http://127.0.0.1:8010/",
            "ERP_LISTING_PROJECT": "proj-0049",
            "ERP_LISTING_MACHINES": "etsy-vn32; etsy-vn16",
            "ERP_LISTING_MACHINE": "etsy-vn32",
        }
        with patch.dict("os.environ", env, clear=False):
            config = ListingBridgeConfig.from_env()

        self.assertEqual("http://127.0.0.1:8010", config.api_url)
        self.assertEqual("PROJ-0049", config.project_id)
        self.assertEqual(("etsy-vn32", "etsy-vn16"), config.machines)
        self.assertEqual("etsy-vn32", config.default_machine)

    def test_both_halves_read_the_same_card_in_the_same_project(self) -> None:
        # Thẻ chỉ có một. Không khai riêng thì nửa listing phải đọc đúng dự án
        # mà nửa làm ảnh đang chạy, chứ không phải một dự án mặc định nào khác.
        with patch.dict("os.environ", {"ERP_PROJECT_ID": "PROJ-0018"}, clear=False):
            with patch.dict("os.environ", {"ERP_LISTING_PROJECT": ""}, clear=False):
                self.assertEqual("PROJ-0018", ListingBridgeConfig.from_env().project_id)

    def test_a_bridge_with_nowhere_to_send_says_so_instead_of_guessing(self) -> None:
        empty = ListingBridge(ListingBridgeConfig())
        with self.assertRaises(ListingBridgeError) as caught:
            empty.dispatch("TASK-1", LISTING_CARD)
        self.assertIn("ERP_LISTING_API_URL", str(caught.exception))


class MachineTests(unittest.TestCase):
    """Thẻ nói gì thắng cấu hình; cấu hình thắng chỗ trống."""

    def test_the_fleet_number_is_what_acc32_means(self) -> None:
        self.assertEqual("etsy-vn32", bridge().machine_for(LISTING_CARD))

    def test_a_machine_written_on_the_card_beats_the_account(self) -> None:
        card = {"meta": "action_1: listing\nacc: acc32\nmachine: etsy-vn16"}
        self.assertEqual("etsy-vn16", bridge().machine_for(card))

    def test_the_configured_machine_catches_a_card_that_says_nothing(self) -> None:
        card = {"meta": "action_1: listing"}
        self.assertEqual("etsy-vn32", bridge(default_machine="etsy-vn32").machine_for(card))

    def test_an_account_the_fleet_has_never_heard_of_is_not_invented(self) -> None:
        card = {"meta": "action_1: listing\nacc: acc99"}
        self.assertEqual("", bridge().machine_for(card))

    def test_a_card_with_no_machine_anywhere_is_refused_not_sent_somewhere(self) -> None:
        # Đợt thử ghim đúng một máy: gửi sai máy là ảnh lên nhầm shop.
        with self.assertRaises(ListingBridgeError) as caught:
            bridge().payload("TASK-1", {"meta": "action_1: listing"})
        self.assertIn("máy Etsy", str(caught.exception))


class PayloadTests(unittest.TestCase):
    """Đúng lược đồ bản Listing nhận, và đúng nghĩa "chỉ đăng, đừng tạo lại"."""

    def test_the_card_becomes_a_request_to_publish_that_same_card(self) -> None:
        payload = bridge().payload("TASK-2026-00700", LISTING_CARD)

        self.assertEqual(
            {
                "type": "image",
                "title": "Khăn tay hoa cúc",
                "source_job_id": "erp-TASK-2026-00700",
                "erp_enabled": True,
                "telegram_enabled": False,
                "erp_project_id": "PROJ-0013",
                "erp_status_id": "",
                "erp_task_id": "TASK-2026-00700",
                "erp_source_task_id": "TASK-2026-00700",
                "etsy_enabled": True,
                "etsy_browser_copy_enabled": True,
                "etsy_account_id": "acc32",
                "etsy_machine_id": "etsy-vn32",
                "etsy_keep_color_chart": True,
                "etsy_delete_existing_images": True,
                "etsy_publish": False,
            },
            payload,
        )

    def test_nothing_in_the_request_asks_for_a_second_batch_of_images(self) -> None:
        # Ảnh đã có và đã được duyệt 👍 trên chính thẻ này. Một lượt tạo ảnh nữa
        # vừa tốn quota vừa bắt người duyệt duyệt lại bộ ảnh họ chưa từng thấy.
        payload = bridge().payload("TASK-1", LISTING_CARD)
        for asked_to_generate in ("prompt", "count", "aspect", "automation_graph"):
            self.assertNotIn(asked_to_generate, payload)

    def test_a_flag_that_defaults_to_on_is_turned_off_out_loud(self) -> None:
        # ``telegram_enabled`` bên bản Listing mặc định True: im lặng ở đây là
        # đồng ý, không phải là trung lập. Ca này giữ cho ý định nằm trong
        # payload thay vì nằm ở chỗ đường enqueue bên kia tình cờ không đọc tới.
        payload = bridge().payload("TASK-1", LISTING_CARD)
        self.assertIn("telegram_enabled", payload)
        self.assertFalse(payload["telegram_enabled"])

    def test_the_trial_only_ever_builds_a_draft(self) -> None:
        self.assertFalse(bridge().payload("TASK-1", LISTING_CARD)["etsy_publish"])

    def test_a_card_with_no_title_still_names_itself(self) -> None:
        payload = bridge(default_machine="etsy-vn32").payload("TASK-9", {"meta": "action_1: listing"})
        self.assertEqual("Listing TASK-9", payload["title"])


class DispatchTests(unittest.TestCase):
    def test_the_card_lands_in_the_listing_queue_and_comes_back_traceable(self) -> None:
        recorder = Recorder()
        result = bridge(recorder).dispatch("TASK-2026-00700", LISTING_CARD)

        url, payload, timeout = recorder.calls[0]
        self.assertEqual("http://127.0.0.1:8010/api/etsy/browser-copy/enqueue", url)
        self.assertEqual("TASK-2026-00700", payload["erp_source_task_id"])
        self.assertEqual(120, timeout)
        self.assertEqual(
            {
                "queue_task_id": "etsy-copy-abc123",
                "machine_id": "etsy-vn32",
                "sku": "HV-1234",
                "image_count": 6,
            },
            result,
        )

    def test_a_card_the_listing_half_declines_is_reported_not_raised(self) -> None:
        # "Thẻ đã ở cột Done" không phải lỗi — nó là câu trả lời đúng, và bot
        # không nên coi cả lượt quét là hỏng vì nó.
        declined = {
            "etsy_browser_copy": {
                "configured": True,
                "skipped": True,
                "skip_reason": "already_in_done",
                "browser_automation_ready": False,
            }
        }
        result = bridge(Recorder(declined)).dispatch("TASK-1", LISTING_CARD)
        self.assertEqual("thẻ đã ở cột Done", result["skipped"])
        self.assertNotIn("queue_task_id", result)

    def test_a_reason_we_have_no_wording_for_is_passed_through_not_swallowed(self) -> None:
        odd = {"etsy_browser_copy": {"configured": True, "skipped": True, "skip_reason": "chuyện_mới"}}
        self.assertEqual("chuyện_mới", bridge(Recorder(odd)).dispatch("TASK-1", LISTING_CARD)["skipped"])

    def test_a_listing_half_missing_its_credentials_is_a_failure_not_a_skip(self) -> None:
        broken = {"etsy_browser_copy": {"configured": False, "missing": ["erp_credentials"]}}
        with self.assertRaises(ListingBridgeError) as caught:
            bridge(Recorder(broken)).dispatch("TASK-1", LISTING_CARD)
        self.assertIn("erp_credentials", str(caught.exception))

    def test_ready_but_never_queued_is_treated_as_not_sent(self) -> None:
        # Không có mã hàng đợi thì không lần theo được, nên không được báo xong.
        stalled = {
            "etsy_browser_copy": {
                "configured": True,
                "browser_automation_ready": True,
                "enqueued": False,
                "missing": ["images"],
                "queue_task": None,
            }
        }
        with self.assertRaises(ListingBridgeError) as caught:
            bridge(Recorder(stalled)).dispatch("TASK-1", LISTING_CARD)
        self.assertIn("images", str(caught.exception))

    def test_an_answer_in_a_shape_we_do_not_know_is_not_read_as_success(self) -> None:
        with self.assertRaises(ListingBridgeError):
            bridge(Recorder({"ok": True})).dispatch("TASK-1", LISTING_CARD)


class HookTests(unittest.TestCase):
    def test_the_hook_carries_the_card_through_to_the_backend(self) -> None:
        import asyncio

        recorder = Recorder()
        hook = build_listing_hook(bridge(recorder))
        outcome = asyncio.run(hook("TASK-2026-00700", LISTING_CARD))

        self.assertEqual("etsy-copy-abc123", outcome["queue_task_id"])
        self.assertEqual("TASK-2026-00700", recorder.calls[0][1]["erp_task_id"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
