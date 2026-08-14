from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

from fastapi import HTTPException

from flow_web.schemas import ERPConfig, JobArtifact, JobRecord
from flow_web.service import FlowWebService
from flow_web.store import StateStore


class ErpReviewDecisionTests(unittest.TestCase):
    """Reading a Vietnamese reply as approve, reject, or neither."""

    def setUp(self) -> None:
        self.service = FlowWebService.__new__(FlowWebService)

    def _decide(self, text: str) -> str:
        return FlowWebService._erp_review_decision(self.service, text)

    def test_reads_the_plain_verdicts(self) -> None:
        self.assertEqual("approved", self._decide("DUYỆT"))
        self.assertEqual("approved", self._decide("<p>duyệt nhé em</p>"))
        self.assertEqual("approved", self._decide("ok em"))
        self.assertEqual("approved", self._decide("Ảnh này đẹp, lấy nhé"))
        self.assertEqual("rejected", self._decide("bỏ"))
        self.assertEqual("rejected", self._decide("Bỏ ảnh này đi em"))
        self.assertEqual("rejected", self._decide("loại"))

    def test_a_refusal_that_contains_the_approve_word_is_still_a_refusal(self) -> None:
        # "không duyệt" contains "duyệt"; reading it as approval would send an
        # image to the client that a reviewer had just turned down.
        self.assertEqual("rejected", self._decide("không duyệt"))
        self.assertEqual("rejected", self._decide("ko duyệt em ơi"))
        self.assertEqual("rejected", self._decide("Ảnh ok về màu nhưng không duyệt"))

    def test_reads_the_tick_and_cross_marks(self) -> None:
        self.assertEqual("approved", self._decide("✅"))
        self.assertEqual("approved", self._decide("👍 luôn"))
        self.assertEqual("rejected", self._decide("❌"))

    def test_a_comment_without_a_verdict_decides_nothing(self) -> None:
        self.assertEqual("", self._decide("Ảnh này chỉnh lại màu nền giúp chị"))
        self.assertEqual("", self._decide(""))
        # A word that merely contains a keyword must not vote: "bò" is not "bỏ",
        # and "boong" is not "bo".
        self.assertEqual("", self._decide("con bò sữa trong ảnh hơi nhỏ"))
        self.assertEqual("", self._decide("nền boong tàu chưa rõ"))


class ErpReviewFlowTests(unittest.TestCase):
    TASK = "TASK-2026-00616"

    def setUp(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.root = root
        self.patches = [
            patch("flow_web.store.STATE_FILE", root / "state.json"),
            patch("flow_web.store.ensure_app_dirs", lambda: root.mkdir(parents=True, exist_ok=True)),
            patch("flow_web.service.ensure_app_dirs", lambda: root.mkdir(parents=True, exist_ok=True)),
        ]
        for item in self.patches:
            item.start()
        self.store = StateStore()
        self.service = FlowWebService(self.store)
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(api_key="test-key", api_secret="test-secret", project_id="PROJ-0013")
            )
        )
        self.comments: List[Dict[str, Any]] = []
        self.replies: List[Dict[str, Any]] = []

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.tempdir.cleanup()
        self.loop.close()
        asyncio.set_event_loop(None)

    def _job(self, count: int = 3) -> JobRecord:
        artifacts = []
        for index in range(count):
            path = self.root / f"anh-{index}.png"
            path.write_bytes(b"png-bytes-%d" % index)
            artifacts.append(JobArtifact(local_path=str(path), mime_type="image/png", url=""))
        job = JobRecord(
            id="job-erp",
            type="image",
            status="completed",
            input={
                "type": "image",
                "prompt": "khăn tay",
                "count": count,
                "erp_enabled": True,
                "erp_task_id": "TASK-2026-00202",
                "erp_output_task_id": self.TASK,
                "erp_project_id": "PROJ-0013",
            },
            artifacts=artifacts,
        )
        return self.loop.run_until_complete(self.store.add_job(job))

    def _fake_add_comment(self, query, variables, operation, *, key, token):
        comment = {
            "name": f"cmt-{len(self.comments)}",
            "content": variables["content"],
            "attachments": [{"file_url": item} for item in variables.get("attachments") or []],
            "replies": [],
        }
        self.comments.append(comment)
        return {"addTaskComment": {"name": comment["name"], "linked": 1}}

    def _detail(self, *_args, **_kwargs) -> Dict[str, Any]:
        return {"name": self.TASK, "comments": list(self.comments)}

    def _fake_reply(self, key, token, task_id, content, *, parent_comment, attachments=None):
        self.replies.append({"parent": parent_comment, "content": content})
        return {"name": f"reply-{len(self.replies)}"}

    def _publish(self, job_id: str = "job-erp") -> Dict[str, Any]:
        with patch.object(self.service, "_erp_assert_task_in_project"), patch.object(
            self.service, "_erp_task_detail", side_effect=self._detail
        ), patch.object(
            self.service, "_erp_upload_file", side_effect=lambda *a: f"/private/files/{a[-1]}"
        ), patch.object(
            self.service, "_erp_graphql", side_effect=self._fake_add_comment
        ), patch.object(
            self.service, "_upsample_artifact_bytes", side_effect=Exception("no flow session")
        ):
            return self.loop.run_until_complete(self.service.publish_erp_review(job_id))

    def _sync(self, job_id: str = "job-erp") -> Dict[str, Any]:
        with patch.object(self.service, "_erp_task_detail", side_effect=self._detail), patch.object(
            self.service, "_erp_reply_comment", side_effect=self._fake_reply
        ):
            return self.loop.run_until_complete(self.service.sync_erp_review(job_id))

    def _answer(self, comment_index: int, text: str, *, by: str = "Khánh Linh", creation: str = "2026-08-14 10:00:00") -> None:
        self.comments[comment_index]["replies"].append(
            {"name": f"ans-{comment_index}", "content": text, "by_name": by, "creation": creation}
        )

    def test_publish_puts_every_undecided_image_on_the_card(self) -> None:
        self._job()

        summary = self._publish()

        self.assertEqual(3, summary["published"])
        self.assertEqual(0, summary["failed"])
        self.assertEqual(3, summary["pending"])
        self.assertEqual(self.TASK, summary["task_id"])
        self.assertEqual(3, len(self.comments))
        # Each comment carries its own marker plus the instruction a reviewer
        # on the card needs in order to answer.
        self.assertIn("[FLOW_V2_REVIEW job-erp#0] Ảnh 1/3", self.comments[0]["content"])
        self.assertIn('Trả lời comment này "DUYỆT"', self.comments[0]["content"])
        self.assertEqual(1, len(self.comments[0]["attachments"]))

        review = self.store.get_job("job-erp").result["erp_review"]
        self.assertEqual(self.TASK, review["task_id"])
        self.assertEqual("cmt-0", review["items"]["0"]["comment"])
        self.assertTrue(review["items"]["2"]["url"].endswith(".png"))

    def test_publishing_twice_does_not_post_a_second_copy(self) -> None:
        self._job()
        self._publish()

        summary = self._publish()

        self.assertEqual(0, summary["published"])
        self.assertEqual(3, len(self.comments))

    def test_publish_skips_images_that_already_have_a_decision(self) -> None:
        self._job()
        self.loop.run_until_complete(self.service.apply_dashboard_approval("job-erp", 1, "rejected"))

        summary = self._publish()

        self.assertEqual(2, summary["published"])
        self.assertEqual(2, summary["pending"])
        self.assertNotIn("job-erp#1", " ".join(item["content"] for item in self.comments))

    def test_sync_records_the_replies_as_decisions_and_answers_on_the_card(self) -> None:
        self._job()
        self._publish()
        self._answer(0, "Duyệt em nhé")
        self._answer(2, "bỏ")

        summary = self._sync()

        self.assertEqual(2, summary["decided"])
        self.assertEqual(1, summary["pending"])
        approvals = self.store.get_job("job-erp").result["dashboard_approvals"]
        self.assertEqual("approved", approvals["0"]["status"])
        self.assertEqual("rejected", approvals["2"]["status"])
        self.assertEqual("Khánh Linh", approvals["0"]["reviewer"]["name"])
        self.assertEqual("erp", approvals["0"]["source"])
        self.assertNotIn("1", approvals)
        # The reviewer sees the answer land under their own reply thread.
        self.assertEqual(["cmt-0", "cmt-2"], [item["parent"] for item in self.replies])
        self.assertIn("✅ Đã duyệt ảnh 1", self.replies[0]["content"])
        self.assertIn("❌ Đã bỏ ảnh 3", self.replies[1]["content"])

    def test_sync_keeps_the_first_answer_when_a_reviewer_changes_their_mind(self) -> None:
        self._job()
        self._publish()
        self._answer(0, "duyệt", creation="2026-08-14 10:00:00")
        self._answer(0, "thôi bỏ đi", creation="2026-08-14 11:00:00")

        self._sync()
        # A second sync must not be able to overturn a recorded decision.
        again = self._sync()

        self.assertEqual(0, again["decided"])
        approvals = self.store.get_job("job-erp").result["dashboard_approvals"]
        self.assertEqual("approved", approvals["0"]["status"])

    def test_sync_ignores_our_own_comments_and_undecided_chatter(self) -> None:
        self._job()
        self._publish()
        self._answer(0, "[FLOW_V2_REVIEW_RESULT] ✅ Đã duyệt ảnh 1.")
        self._answer(1, "chỉnh lại ánh sáng giúp chị")

        summary = self._sync()

        self.assertEqual(0, summary["decided"])
        self.assertEqual(3, summary["pending"])
        self.assertEqual([], self.replies)

    def test_sync_without_a_published_review_says_so(self) -> None:
        self._job()

        with self.assertRaises(HTTPException) as caught:
            self._sync()

        self.assertEqual(409, caught.exception.status_code)

    def test_publish_rejects_a_job_that_does_not_write_to_erp(self) -> None:
        job = self._job()
        job.input["erp_enabled"] = False
        self.loop.run_until_complete(self.store.patch_job(job.id, result={}))

        with self.assertRaises(HTTPException) as caught:
            self._publish()

        self.assertEqual(400, caught.exception.status_code)

    def test_only_jobs_with_an_open_review_are_polled(self) -> None:
        self._job()
        self.assertEqual([], self.service.erp_review_jobs_to_sync())

        self._publish()
        self.assertEqual(["job-erp"], self.service.erp_review_jobs_to_sync())

        for index in range(3):
            self.loop.run_until_complete(self.service.apply_dashboard_approval("job-erp", index, "approved"))
        # Every image answered: the card has nothing left to read.
        self.assertEqual([], self.service.erp_review_jobs_to_sync())

    def test_the_poller_reads_every_open_review_on_its_own(self) -> None:
        self._job()
        self._publish()
        calls: List[str] = []
        slept: List[Any] = []

        async def fake_sleep(seconds):
            # One lap, then stop the loop the way a shutdown would.
            if slept:
                raise asyncio.CancelledError
            slept.append(seconds)

        async def fake_sync(job_id):
            calls.append(job_id)
            return {}

        with patch.object(self.service, "sync_erp_review", side_effect=fake_sync), patch(
            "flow_web.service.asyncio.sleep", side_effect=fake_sleep
        ):
            with self.assertRaises(asyncio.CancelledError):
                self.loop.run_until_complete(self.service.watch_erp_reviews())

        self.assertEqual(["job-erp"], calls)
        self.assertEqual([self.service.ERP_REVIEW_POLL_DEFAULT_S], slept)

    def test_the_poller_can_be_switched_off(self) -> None:
        with patch.dict("os.environ", {"ERP_REVIEW_POLL_SECONDS": "0"}), patch(
            "flow_web.service.asyncio.sleep"
        ) as sleep:
            self.loop.run_until_complete(self.service.watch_erp_reviews())
        sleep.assert_not_called()

    def _reject_by_tool(self, index: int) -> None:
        job = self.store.get_job("job-erp")
        result = dict(job.result or {})
        approvals = dict(result.get("dashboard_approvals") or {})
        approvals[str(index)] = {
            "artifact_index": index,
            "status": "rejected",
            "reviewer": {"name": "Flow v2 (còn watermark Gemini)"},
            "source": "dashboard",
        }
        result["dashboard_approvals"] = approvals
        self.loop.run_until_complete(self.store.patch_job("job-erp", result=result))

    def test_reopen_returns_tool_rejections_to_the_reviewers(self) -> None:
        job = self._job()
        for artifact in job.artifacts:
            artifact.watermark_status = "cleaned"
        self.loop.run_until_complete(self.store.replace_artifacts("job-erp", list(job.artifacts)))
        self._reject_by_tool(1)
        self.loop.run_until_complete(self.service.apply_dashboard_approval("job-erp", 2, "rejected", "Khánh Linh"))

        summary = self.loop.run_until_complete(self.service.reopen_watermark_rejections("job-erp"))

        self.assertEqual([1], summary["reopened"])
        approvals = self.store.get_job("job-erp").result["dashboard_approvals"]
        # The reviewer's own "no" is untouched; only the tool's is re-opened.
        self.assertNotIn("1", approvals)
        self.assertEqual("rejected", approvals["2"]["status"])
        self.assertEqual(1, len(self.store.get_job("job-erp").result["reopened_approvals"]))
        # And the re-opened image goes back onto the card for a real answer.
        self.assertEqual(2, self._publish()["published"])

    def test_reopen_leaves_an_image_that_is_still_marked(self) -> None:
        job = self._job()
        job.artifacts[1].watermark_status = "metadata_only"
        self.loop.run_until_complete(self.store.replace_artifacts("job-erp", list(job.artifacts)))
        self._reject_by_tool(1)

        summary = self.loop.run_until_complete(self.service.reopen_watermark_rejections("job-erp"))

        self.assertEqual([], summary["reopened"])
        self.assertEqual("rejected", self.store.get_job("job-erp").result["dashboard_approvals"]["1"]["status"])

    def test_the_archive_never_posts_an_image_to_the_same_card_twice(self) -> None:
        from flow_web.schemas import CreateJobRequest

        job = self._job()
        request = CreateJobRequest(**job.input)
        for index in range(3):
            self.loop.run_until_complete(self.service.apply_dashboard_approval("job-erp", index, "approved"))

        with patch.object(self.service, "_erp_assert_task_in_project"), patch.object(
            self.service, "_erp_upload_file", side_effect=lambda *a: f"/private/files/{a[-1]}"
        ), patch.object(self.service, "_erp_graphql", side_effect=self._fake_add_comment), patch.object(
            self.service, "_upsample_artifact_bytes", side_effect=Exception("no flow session")
        ):
            first = self.loop.run_until_complete(
                self.service._archive_erp_artifacts("job-erp", request, list(job.artifacts))
            )
        self.loop.run_until_complete(
            self.store.patch_job("job-erp", result={**(self.store.get_job("job-erp").result or {}), "erp": first})
        )

        with patch.object(self.service, "_erp_assert_task_in_project"), patch.object(
            self.service, "_erp_upload_file"
        ) as upload:
            second = self.loop.run_until_complete(
                self.service._archive_erp_artifacts("job-erp", request, list(job.artifacts))
            )

        self.assertEqual(3, first["sent"])
        self.assertEqual(3, second["sent"])
        self.assertEqual(3, second["reused_review_comments"])
        upload.assert_not_called()

    def test_the_archive_reuses_the_comments_the_reviewer_already_saw(self) -> None:
        from flow_web.schemas import CreateJobRequest

        job = self._job()
        self._publish()
        self._answer(0, "duyệt")
        self._answer(1, "duyệt")
        self._answer(2, "bỏ")
        self._sync()

        request = CreateJobRequest(**job.input)
        with patch.object(self.service, "_erp_assert_task_in_project"), patch.object(
            self.service, "_erp_upload_file"
        ) as upload, patch.object(self.service, "_erp_task_detail", side_effect=self._detail):
            result = self.loop.run_until_complete(
                self.service._archive_erp_artifacts("job-erp", request, list(job.artifacts))
            )

        # Nothing is uploaded a second time: the approved images are already on
        # the card as the very files the reviewer approved.
        upload.assert_not_called()
        self.assertEqual(2, result["sent"])
        self.assertEqual(2, result["reused_review_comments"])
        self.assertEqual(0, result["failed"])
        self.assertEqual(1, result["rejected"])

    def test_the_dashboard_payload_still_carries_the_review_state(self) -> None:
        # The browser gets the compacted jobs, so anything the review queue reads
        # has to survive compaction - otherwise a decided image reads as pending
        # and the ERP row never learns which card the images went to.
        self._job()
        self._publish()
        self._answer(0, "duyệt")
        self._sync()

        job = next(item for item in self.service.get_state_payload()["jobs"] if item["id"] == "job-erp")
        result = job["result"]

        self.assertEqual("approved", result["dashboard_approvals"]["0"]["status"])
        self.assertEqual(1, result["dashboard_approval_summary"]["approved"])
        self.assertEqual(self.TASK, result["erp_review"]["task_id"])
        self.assertEqual({"0", "1", "2"}, set(result["erp_review"]["items"]))
        self.assertTrue(result["erp_review"]["items"]["0"]["url"])


if __name__ == "__main__":
    unittest.main()
