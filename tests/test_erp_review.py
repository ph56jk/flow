from __future__ import annotations

import asyncio
import base64
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

from fastapi import HTTPException

from flow_web.schemas import CreateJobRequest, ERPConfig, JobArtifact, JobRecord
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


class _FakeUpsampleClient:
    """A Flow client that hands out reCAPTCHA tokens and can refuse them.

    Only the two things ``_upsample_image_via_flow`` touches are real: minting
    a token (``_client_context``, which on the live client drives the page)
    and posting the upscale (``_fetch``). ``refuse_tokens`` names the tokens
    Google answers with the 403 that left images at 1024.
    """

    BIG = b"anh-2k-that"

    def __init__(
        self,
        test: unittest.TestCase,
        *,
        refuse_tokens: set[str] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._test = test
        self._refuse = set(refuse_tokens or ())
        self._error = error
        self.contexts = 0
        self.tokens_used: List[str] = []
        self.lock_held_while_minting: List[bool] = []
        self._api = self

    async def _client_context(self) -> Dict[str, Any]:
        self.contexts += 1
        self.lock_held_while_minting.append(self._test.service._browser_session_lock.locked())
        return {"token": f"tok-{self.contexts}"}

    async def _fetch(self, method: str, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        token = str((payload.get("clientContext") or {}).get("token") or "")
        self.tokens_used.append(token)
        if self._error is not None:
            raise self._error
        if token in self._refuse:
            raise RuntimeError("HTTP 403 on upsampleImage: reCAPTCHA evaluation failed")
        return {"encodedImage": base64.b64encode(self.BIG).decode()}


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
        # The card's own state, plus what this app writes back onto it. Both
        # are faked here because a rejection now removes a comment and a
        # finished idea moves column - neither may reach the real ERP in a test.
        self.task_status = "Open"
        self.deleted: List[str] = []
        self.notes: List[str] = []
        self.status_writes: List[str] = []
        for item in (
            patch.object(self.service, "_erp_delete_task_comment", side_effect=self._fake_delete),
            patch.object(self.service, "_erp_comment", side_effect=self._fake_note),
            patch.object(self.service, "_erp_update_task_status", side_effect=self._fake_status),
        ):
            self.patches.append(item)
            item.start()

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
            "meta": variables.get("meta") or "",
            "attachments": [{"file_url": item} for item in variables.get("attachments") or []],
            "replies": [],
        }
        self.comments.append(comment)
        return {"addTaskComment": {"name": comment["name"], "linked": 1}}

    def _detail(self, *_args, **_kwargs) -> Dict[str, Any]:
        return {"name": self.TASK, "status": self.task_status, "comments": list(self.comments)}

    def _fake_delete(self, key, token, task_id, comment) -> Dict[str, Any]:
        self.deleted.append(comment)
        self.comments = [item for item in self.comments if item["name"] != comment]
        return {"deleted": comment}

    def _fake_note(self, key, token, task_id, content, parent_comment: str = "") -> Dict[str, Any]:
        self.notes.append(content)
        return {"comment": {"name": f"note-{len(self.notes)}"}}

    def _fake_status(self, key, token, task_id, status) -> Dict[str, Any]:
        self.status_writes.append(status)
        self.task_status = status
        return {"name": task_id, "status": status}

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
        # Nothing readable goes on the card: the marker rides in ``meta`` and
        # the body is the invisible character that keeps ERP from writing
        # "(đã đính kèm tệp)" in its place.
        self.assertEqual("[FLOW_V2_REVIEW job-erp#0]", self.comments[0]["meta"])
        self.assertEqual("\u200b", self.comments[0]["content"])
        self.assertNotIn("DUYỆT", " ".join(item["content"] for item in self.comments))
        self.assertEqual(1, len(self.comments[0]["attachments"]))

        review = self.store.get_job("job-erp").result["erp_review"]
        self.assertEqual(self.TASK, review["task_id"])
        self.assertEqual("cmt-0", review["items"]["0"]["comment"])
        self.assertTrue(review["items"]["2"]["url"].endswith(".png"))

    def test_a_finished_job_puts_its_images_on_the_card_without_being_asked(self) -> None:
        # Reviewers never open this app, so a run that only fills the local
        # dashboard reads on the board as "the bot did nothing".
        job = self._job()
        request = CreateJobRequest(**job.input)

        with patch.object(self.service, "_erp_assert_task_in_project"), patch.object(
            self.service, "_erp_task_detail", side_effect=self._detail
        ), patch.object(
            self.service, "_erp_upload_file", side_effect=lambda *a: f"/private/files/{a[-1]}"
        ), patch.object(
            self.service, "_erp_graphql", side_effect=self._fake_add_comment
        ), patch.object(
            self.service, "_upsample_artifact_bytes", side_effect=Exception("no flow session")
        ):
            published = self.loop.run_until_complete(
                self.service._auto_publish_erp_review("job-erp", request)
            )

        self.assertEqual(3, published)
        self.assertEqual(3, len(self.comments))
        self.assertEqual(["Pending Review"], self.status_writes)

    def test_the_whole_batch_is_upscaled_in_one_flow_session(self) -> None:
        # Opening a Flow project page per image is what made the upload step
        # take longer than the generation it was uploading: twelve page loads
        # at roughly half a minute each, one after another.
        job = self._job()
        request = CreateJobRequest(**job.input)
        sessions = 0
        held: list[bool] = []
        upscaled: list[str] = []

        async def _with_client(fn, workflow_id="", timeout_s=0, hold_session_lock=True):
            nonlocal sessions
            sessions += 1
            held.append(hold_session_lock)
            return await fn(object())

        async def _via_flow(_client, jpeg_bytes, **kwargs):
            upscaled.append(str(kwargs.get("media_generation_id") or ""))
            return jpeg_bytes

        with patch.object(self.service, "_erp_assert_task_in_project"), patch.object(
            self.service, "_erp_task_detail", side_effect=self._detail
        ), patch.object(
            self.service, "_erp_upload_file", side_effect=lambda *a: f"/private/files/{a[-1]}"
        ), patch.object(
            self.service, "_erp_graphql", side_effect=self._fake_add_comment
        ), patch.object(
            self.service, "_flow_upsample_api_enabled", return_value=True
        ), patch.object(
            self.service, "_with_client", side_effect=_with_client
        ), patch.object(
            self.service, "_upsample_image_via_flow", side_effect=_via_flow
        ):
            published = self.loop.run_until_complete(
                self.service._auto_publish_erp_review("job-erp", request)
            )

        self.assertEqual(3, published)
        self.assertEqual(1, sessions)
        self.assertEqual(3, len(upscaled))
        # And it does not keep the browser while it waits on those upscales.
        self.assertEqual([False], held)

    def test_the_batch_can_send_several_upscales_at_once(self) -> None:
        # Off by default - four at a time measured slower than one at a time on
        # live cards, and dropped images. The knob is what lets that be
        # re-measured, so it has to actually reach the batch.
        job = self._job()
        request = CreateJobRequest(**job.input)
        in_flight = 0
        peak = 0

        async def _with_client(fn, workflow_id="", timeout_s=0, hold_session_lock=True):
            return await fn(object())

        all_three = asyncio.Event()

        async def _via_flow(_client, jpeg_bytes, **_kwargs):
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            if in_flight >= 3:
                all_three.set()
            try:
                # One at a time, nobody ever sets this and each image waits
                # out the timeout instead.
                await asyncio.wait_for(all_three.wait(), timeout=2)
            except asyncio.TimeoutError:
                pass
            in_flight -= 1
            return jpeg_bytes

        with patch.dict("os.environ", {"FLOW_UPSAMPLE_CONCURRENCY": "4"}), patch.object(
            self.service, "_erp_assert_task_in_project"
        ), patch.object(
            self.service, "_erp_task_detail", side_effect=self._detail
        ), patch.object(
            self.service, "_erp_upload_file", side_effect=lambda *a: f"/private/files/{a[-1]}"
        ), patch.object(
            self.service, "_erp_graphql", side_effect=self._fake_add_comment
        ), patch.object(
            self.service, "_flow_upsample_api_enabled", return_value=True
        ), patch.object(
            self.service, "_with_client", side_effect=_with_client
        ), patch.object(
            self.service, "_upsample_image_via_flow", side_effect=_via_flow
        ):
            published = self.loop.run_until_complete(
                self.service._auto_publish_erp_review("job-erp", request)
            )

        self.assertEqual(3, published)
        self.assertEqual(3, peak)

    def test_two_cards_take_turns_on_the_2k_batch(self) -> None:
        # The batch lets go of the browser so the next card can generate, but
        # it must not let go of Google. Two batches in flight measured 87-105s
        # an image against 31s alone on live cards, and 5 of one card's 12
        # images came back un-upscaled. Overlap the browser, not the queue.
        from flow_web.service import ImageUpscaleResult

        order: list[str] = []
        first_started = asyncio.Event()
        release_first = asyncio.Event()

        async def _with_client(fn, workflow_id="", timeout_s=0, hold_session_lock=True):
            return await fn(object())

        async def _one(artifact, _url, *, client=None, session_lock_held=True):
            card = str(artifact.local_path)
            order.append(f"{card} bắt đầu")
            if card == "a":
                first_started.set()
                await release_first.wait()
            order.append(f"{card} xong")
            return ImageUpscaleResult()

        def _items(card: str):
            artifact = JobArtifact(local_path=card, mime_type="image/png", url="http://x/1.png")
            return [(0, artifact, "http://x/1.png")]

        async def _run() -> None:
            with patch.object(
                self.service, "_flow_upsample_api_enabled", return_value=True
            ), patch.object(
                self.service, "_with_client", side_effect=_with_client
            ), patch.object(
                self.service, "_upsample_artifact_bytes", side_effect=_one
            ):
                first = asyncio.create_task(self.service._upsample_artifacts_bytes(_items("a")))
                await asyncio.wait_for(first_started.wait(), timeout=2)
                second = asyncio.create_task(self.service._upsample_artifacts_bytes(_items("b")))
                # Every chance to slip in alongside the first batch.
                for _ in range(30):
                    await asyncio.sleep(0)
                release_first.set()
                await asyncio.wait_for(asyncio.gather(first, second), timeout=2)

        self.loop.run_until_complete(_run())
        self.assertEqual(["a bắt đầu", "a xong", "b bắt đầu", "b xong"], order)

    def test_auto_publish_can_be_turned_off(self) -> None:
        job = self._job()
        request = CreateJobRequest(**job.input)

        with patch.dict("os.environ", {"ERP_REVIEW_AUTOPUBLISH": "0"}), patch.object(
            self.service, "publish_erp_review"
        ) as publish:
            published = self.loop.run_until_complete(
                self.service._auto_publish_erp_review("job-erp", request)
            )

        self.assertEqual(0, published)
        publish.assert_not_called()

    def test_a_failed_publish_leaves_the_job_alone(self) -> None:
        # The images already exist; a broken ERP call must not lose them.
        job = self._job()
        request = CreateJobRequest(**job.input)

        with patch.object(
            self.service, "publish_erp_review", side_effect=HTTPException(status_code=502, detail="ERP lỗi")
        ):
            published = self.loop.run_until_complete(
                self.service._auto_publish_erp_review("job-erp", request)
            )

        self.assertEqual(0, published)
        logs = " ".join(entry.message for entry in self.store.get_job("job-erp").logs)
        self.assertIn("Không đăng được ảnh lên thẻ ERP để duyệt", logs)

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
        self.assertNotIn("job-erp#1", " ".join(item["meta"] for item in self.comments))

    def test_sync_records_the_replies_as_decisions_and_writes_nothing_back(self) -> None:
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
        # The card answers for itself - an approved image stays, a rejected one
        # disappears - so the app writes no word of its own either way.
        self.assertEqual([], self.replies)
        self.assertEqual(["cmt-2"], self.deleted)
        self.assertEqual([], self.notes)

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

    def _vote(self, comment_index: int, *, like: int = 0, dislike: int = 0) -> None:
        self.comments[comment_index]["like_count"] = like
        self.comments[comment_index]["dislike_count"] = dislike

    def test_sync_reads_the_thumbs_buttons_when_nobody_typed_an_answer(self) -> None:
        # The ERP grew 👍/👎 buttons after this flow was built. A reviewer who
        # presses one has answered, and leaving those images pending forever
        # would be the app ignoring them.
        self._job()
        self._publish()
        self._vote(0, like=1)
        self._vote(2, dislike=2)

        summary = self._sync()

        self.assertEqual(2, summary["decided"])
        approvals = self.store.get_job("job-erp").result["dashboard_approvals"]
        self.assertEqual("approved", approvals["0"]["status"])
        self.assertEqual("rejected", approvals["2"]["status"])
        # 👎 takes the image off the card, exactly like a typed "bỏ".
        self.assertEqual(["cmt-2"], self.deleted)

    def test_a_typed_answer_beats_the_buttons(self) -> None:
        # A reply says who decided and why; a count says neither.
        self._job()
        self._publish()
        self._vote(0, dislike=3)
        self._answer(0, "duyệt nhé")

        self._sync()

        approvals = self.store.get_job("job-erp").result["dashboard_approvals"]
        self.assertEqual("approved", approvals["0"]["status"])
        self.assertEqual("Khánh Linh", approvals["0"]["reviewer"]["name"])
        self.assertEqual([], self.deleted)

    def test_a_split_vote_is_left_for_a_person_to_settle(self) -> None:
        self._job()
        self._publish()
        self._vote(0, like=2, dislike=2)
        self._vote(1, like=0, dislike=0)

        summary = self._sync()

        self.assertEqual(0, summary["decided"])
        self.assertEqual([], self.deleted)

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

    def test_the_agent_network_wait_can_be_shortened(self) -> None:
        # In Agent mode this wait runs out in full on every card and the
        # images turn up through the project poll ~10s later, so it is ~45s
        # a card of dead time. The default stays put until that is measured;
        # the knob is what makes measuring it possible.
        self.assertEqual(45.0, self.service._flow_agent_network_wait_seconds())

        with patch.dict("os.environ", {"FLOW_AGENT_NETWORK_WAIT_SECONDS": "12"}):
            self.assertEqual(12.0, self.service._flow_agent_network_wait_seconds())
        with patch.dict("os.environ", {"FLOW_AGENT_NETWORK_WAIT_SECONDS": "0"}):
            self.assertEqual(5.0, self.service._flow_agent_network_wait_seconds(), "sàn 5s")
        with patch.dict("os.environ", {"FLOW_AGENT_NETWORK_WAIT_SECONDS": "linh tinh"}):
            self.assertEqual(45.0, self.service._flow_agent_network_wait_seconds())

    def test_a_finished_run_keeps_the_review_it_published(self) -> None:
        # The post-module runner works from a snapshot taken before the
        # modules ran, but the approval module publishes to the card by
        # patching the job directly. Writing that stale snapshot back on
        # completion dropped erp_review - and a job with no items is one
        # erp_review_jobs_to_sync skips, so the card's 👍/👎 replies were
        # never read again.
        self._job()
        self._publish()
        stale = {"count": 3, "mode": "image"}

        merged = self.service._result_with_module_side_writes("job-erp", stale)
        self.loop.run_until_complete(self.store.patch_job("job-erp", result=merged))

        self.assertEqual(3, len(merged["erp_review"]["items"]))
        self.assertEqual(3, merged["count"], "the snapshot's own keys still win")
        self.assertEqual(["job-erp"], self.service.erp_review_jobs_to_sync())

    def test_the_card_fan_out_sizes_itself_to_the_machine(self) -> None:
        # Two cores a card, two held back for Chrome and the app.
        for cores, expected in ((None, 1), (2, 1), (4, 1), (6, 2), (8, 3), (10, 3), (64, 3)):
            with patch.dict("os.environ", {"ERP_IDEA_CONCURRENCY": ""}), patch(
                "os.cpu_count", return_value=cores
            ):
                self.assertEqual(
                    expected, self.service._erp_idea_concurrency(), f"{cores} nhân"
                )

    def test_a_number_set_by_hand_still_beats_the_machine(self) -> None:
        with patch("os.cpu_count", return_value=4):
            with patch.dict("os.environ", {"ERP_IDEA_CONCURRENCY": "4"}):
                self.assertEqual(4, self.service._erp_idea_concurrency())
            with patch.dict("os.environ", {"ERP_IDEA_CONCURRENCY": "9"}):
                self.assertEqual(4, self.service._erp_idea_concurrency(), "trần tay là 4")
            with patch.dict("os.environ", {"ERP_IDEA_CONCURRENCY": "0"}):
                self.assertEqual(1, self.service._erp_idea_concurrency())
            # Anything that is not a number falls back to the machine, not to
            # a hardcoded guess.
            for value in ("auto", "AUTO", "linh tinh"):
                with patch.dict("os.environ", {"ERP_IDEA_CONCURRENCY": value}):
                    self.assertEqual(1, self.service._erp_idea_concurrency(), value)

    def test_the_number_of_recaptcha_rounds_is_bounded(self) -> None:
        self.assertEqual(3, self.service._flow_upsample_recaptcha_rounds())
        with patch.dict("os.environ", {"FLOW_UPSAMPLE_RECAPTCHA_ROUNDS": "2"}):
            self.assertEqual(2, self.service._flow_upsample_recaptcha_rounds())
        with patch.dict("os.environ", {"FLOW_UPSAMPLE_RECAPTCHA_ROUNDS": "0"}):
            self.assertEqual(1, self.service._flow_upsample_recaptcha_rounds(), "ít nhất 1 lượt")
        with patch.dict("os.environ", {"FLOW_UPSAMPLE_RECAPTCHA_ROUNDS": "99"}):
            self.assertEqual(5, self.service._flow_upsample_recaptcha_rounds(), "trần 5 lượt")
        with patch.dict("os.environ", {"FLOW_UPSAMPLE_RECAPTCHA_ROUNDS": "linh tinh"}):
            self.assertEqual(3, self.service._flow_upsample_recaptcha_rounds())

    def test_a_refused_recaptcha_token_is_retried_with_a_fresh_one(self) -> None:
        # The live cards' un-upscaled images were all one 403: "reCAPTCHA
        # evaluation failed". One token used to be one chance, so a refused
        # token left the image at 1024 for good.
        client = _FakeUpsampleClient(self, refuse_tokens={"tok-1"})

        upscaled = self._upsample(client)

        self.assertEqual(_FakeUpsampleClient.BIG, upscaled)
        self.assertEqual(2, client.contexts, "lượt hai phải xin token mới")
        self.assertEqual({"tok-1", "tok-2"}, set(client.tokens_used))

    def test_a_failure_that_is_not_the_token_is_not_paid_for_twice(self) -> None:
        # A fresh token cannot help a 500, so re-minting one only spends time.
        client = _FakeUpsampleClient(self, error=RuntimeError("HTTP 500 internal"))

        upscaled = self._upsample(client)

        self.assertEqual(b"anh-goc", upscaled, "trả lại ảnh gốc để vẫn đăng được")
        self.assertEqual(1, client.contexts)

    def test_the_token_is_minted_under_the_browser_lock_once_the_batch_let_go(self) -> None:
        # Minting runs grecaptcha through page.evaluate and may reload the
        # page. The 2K batch hands the browser back so the next card can
        # generate, so an unguarded mint lands on that card's page - which is
        # what got the token refused in the first place.
        client = _FakeUpsampleClient(self, refuse_tokens={"tok-1"})

        self._upsample(client, session_lock_held=False)

        self.assertEqual([True, True], client.lock_held_while_minting)
        self.assertFalse(self.service._browser_session_lock.locked(), "phải trả khoá lại")

    def test_the_token_is_minted_in_place_while_the_batch_still_holds_the_browser(self) -> None:
        # Taking the same non-reentrant lock a second time would hang forever.
        client = _FakeUpsampleClient(self, refuse_tokens=set())

        self.loop.run_until_complete(self.service._browser_session_lock.acquire())
        try:
            upscaled = self._upsample(client, session_lock_held=True)
        finally:
            self.service._browser_session_lock.release()

        self.assertEqual(_FakeUpsampleClient.BIG, upscaled)

    def test_the_app_stops_paying_for_retries_google_keeps_refusing(self) -> None:
        # Measured live: once Google starts answering upsampleImage with
        # "reCAPTCHA evaluation failed" it refuses every round, fresh token
        # or not. Three rounds an image buys nothing then - the image needs
        # the UI download either way - so it drops to a single probe.
        always_refused = {f"tok-{n}" for n in range(1, 40)}
        for image in range(3):
            client = _FakeUpsampleClient(self, refuse_tokens=always_refused)
            self._upsample(client)
            if image < 2:
                self.assertEqual(3, client.contexts, "hai ảnh đầu vẫn thử đủ lượt")
            else:
                self.assertEqual(1, client.contexts, "sau đó chỉ dò một lần")

    def test_one_good_upscale_gives_the_retries_back(self) -> None:
        for _ in range(2):
            self._upsample(_FakeUpsampleClient(self, refuse_tokens={f"tok-{n}" for n in range(1, 40)}))
        self.assertEqual(2, self.service._flow_upsample_recaptcha_streak)

        self._upsample(_FakeUpsampleClient(self, refuse_tokens=set()))

        self.assertEqual(0, self.service._flow_upsample_recaptcha_streak)
        client = _FakeUpsampleClient(self, refuse_tokens={"tok-1"})
        self._upsample(client)
        self.assertEqual(2, client.contexts, "được thử lại bình thường")

    def test_a_plain_failure_does_not_count_towards_giving_up(self) -> None:
        # Only a refused token says anything about reCAPTCHA. A 500 must not
        # push the app into the one-probe mode.
        for _ in range(3):
            self._upsample(_FakeUpsampleClient(self, error=RuntimeError("HTTP 500 internal")))

        self.assertEqual(0, self.service._flow_upsample_recaptcha_streak)

    def _upsample(self, client: Any, *, session_lock_held: bool = True) -> bytes:
        """Run one upscale against a fake client, with the slow parts stubbed."""

        async def no_ui_download(*_args, **_kwargs):
            return b""

        with patch.object(self.service, "FLOW_UPSAMPLE_RECAPTCHA_BACKOFF_S", 0.0), patch.object(
            self.service, "_upsample_image_via_flow_ui_download", side_effect=no_ui_download
        ), patch.object(
            self.service,
            "_image_size_from_bytes",
            lambda data: (2048, 2048) if data == _FakeUpsampleClient.BIG else (1024, 1024),
        ):
            return self.loop.run_until_complete(
                self.service._upsample_image_via_flow(
                    client,
                    b"anh-goc",
                    media_generation_id="11111111-2222-3333-4444-555555555555",
                    session_lock_held=session_lock_held,
                )
            )

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

    def test_reopen_arms_the_delivery_step_again(self) -> None:
        # The card was already archived once. Without re-arming the ERP step the
        # re-opened image would be approved and then never delivered, because a
        # finished module is skipped when the pipeline resumes.
        job = self._job()
        for artifact in job.artifacts:
            artifact.watermark_status = "cleaned"
        self.loop.run_until_complete(self.store.replace_artifacts("job-erp", list(job.artifacts)))
        result = {
            "automation_execution": {
                "nodes": [
                    {"id": "approval-1", "type": "approval", "status": "completed"},
                    {"id": "erp-1", "type": "erp", "status": "completed", "completed_at": "2026-08-14 10:00:00"},
                ],
                "completed": True,
            }
        }
        self.loop.run_until_complete(self.store.patch_job("job-erp", result=result))
        self._reject_by_tool(1)

        self.loop.run_until_complete(self.service.reopen_watermark_rejections("job-erp"))

        nodes = self.store.get_job("job-erp").result["automation_execution"]["nodes"]
        erp_node = next(node for node in nodes if node["type"] == "erp")
        self.assertEqual("pending", erp_node["status"])
        self.assertNotIn("completed_at", erp_node)
        self.assertFalse(self.store.get_job("job-erp").result["automation_execution"]["completed"])

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

    def test_a_dislike_takes_the_image_off_the_card(self) -> None:
        self._job()
        self._publish()

        self.loop.run_until_complete(
            self.service.apply_dashboard_approval("job-erp", 1, "rejected", "Khánh Linh")
        )

        # The picture is gone from the card and nothing is written in its place;
        # who dropped it is recorded in the job log instead.
        self.assertEqual(["cmt-1"], self.deleted)
        self.assertEqual(["cmt-0", "cmt-2"], [item["name"] for item in self.comments])
        self.assertEqual([], self.notes)
        logs = " ".join(entry.message for entry in self.store.get_job("job-erp").logs)
        self.assertIn("Đã gỡ ảnh 2", logs)
        self.assertIn("Khánh Linh", logs)
        items = self.store.get_job("job-erp").result["erp_review"]["items"]
        self.assertEqual("", items["1"]["comment"])
        self.assertTrue(items["1"]["deleted_at"])

    def test_the_log_does_not_stutter_when_the_button_is_the_reviewer(self) -> None:
        # A vote has no name to credit, so the reviewer string is the button
        # itself and the line must not read "vì 👎 trên thẻ ERP không thích".
        self._job()
        self._publish()

        self.loop.run_until_complete(
            self.service.apply_dashboard_approval("job-erp", 1, "rejected", "👎 trên thẻ ERP")
        )

        logs = " ".join(entry.message for entry in self.store.get_job("job-erp").logs)
        self.assertIn("theo 👎 trên thẻ ERP", logs)
        self.assertNotIn("👎 trên thẻ ERP không thích", logs)

    def test_a_like_leaves_the_image_where_the_reviewer_can_see_it(self) -> None:
        self._job()
        self._publish()

        self.loop.run_until_complete(self.service.apply_dashboard_approval("job-erp", 0, "approved"))

        self.assertEqual([], self.deleted)
        self.assertEqual(3, len(self.comments))

    def test_the_same_image_is_never_deleted_twice(self) -> None:
        self._job()
        self._publish()
        self.loop.run_until_complete(self.service.apply_dashboard_approval("job-erp", 1, "rejected"))

        # A repeat of the same decision is a no-op, so no second delete call.
        self.loop.run_until_complete(self.service.apply_dashboard_approval("job-erp", 1, "rejected"))
        self.loop.run_until_complete(self.service._erp_discard_rejected_review_image("job-erp", 1))

        self.assertEqual(["cmt-1"], self.deleted)

    def test_an_image_the_tool_refused_for_a_watermark_stays_on_the_card(self) -> None:
        # It has not been reviewed by anyone yet: reopen_watermark_rejections
        # hands it back once the mark is cleaned, which needs it to still exist.
        self._job()
        self._publish()

        self.loop.run_until_complete(
            self.service.apply_dashboard_approval("job-erp", 1, "rejected", "Flow v2", source="watermark_gate")
        )

        self.assertEqual([], self.deleted)
        self.assertEqual(3, len(self.comments))

    def test_publishing_moves_the_idea_card_to_pending_review(self) -> None:
        self._job()

        self._publish()

        self.assertEqual(["Pending Review"], self.status_writes)

    def test_a_card_a_person_already_closed_is_not_moved(self) -> None:
        self._job()
        self.task_status = "Cancelled"

        self._publish()

        self.assertEqual([], self.status_writes)

    def test_the_idea_card_is_completed_once_its_approved_images_land(self) -> None:
        from flow_web.schemas import CreateJobRequest

        job = self._job()
        self._publish()
        self._answer(0, "👍")
        self._answer(1, "👎")
        self._answer(2, "duyệt")
        self._sync()
        self.status_writes.clear()

        request = CreateJobRequest(**job.input)
        with patch.object(self.service, "_erp_assert_task_in_project"), patch.object(
            self.service, "_erp_task_detail", side_effect=self._detail
        ):
            result = self.loop.run_until_complete(
                self.service._archive_erp_artifacts("job-erp", request, list(job.artifacts))
            )

        self.assertEqual(2, result["sent"])
        self.assertEqual(["Completed"], self.status_writes)

    def test_a_card_whose_images_were_all_disliked_stays_open(self) -> None:
        from flow_web.schemas import CreateJobRequest

        job = self._job()
        self._publish()
        for index in range(3):
            self._answer(index, "bỏ")
        self._sync()
        self.status_writes.clear()

        request = CreateJobRequest(**job.input)
        with patch.object(self.service, "_erp_assert_task_in_project"), patch.object(
            self.service, "_erp_task_detail", side_effect=self._detail
        ):
            result = self.loop.run_until_complete(
                self.service._archive_erp_artifacts("job-erp", request, list(job.artifacts))
            )

        self.assertEqual(0, result["sent"])
        self.assertEqual([], self.status_writes)

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


class ErpAdvanceStatusTests(unittest.TestCase):
    """Chuyển cột thẻ ERP sau khi ảnh xong — và khi nào thì không chuyển."""

    TASK = "TASK-2026-00906"

    class _Store:
        def __init__(self) -> None:
            self.logs: List[str] = []

        async def append_log(self, job_id: str, line: str) -> None:
            self.logs.append(line)

    def setUp(self) -> None:
        self.service = FlowWebService.__new__(FlowWebService)
        self.service.store = self._Store()
        self.moves: List[Dict[str, str]] = []

    def _advance(self, status: str, *, meta: str, current: str = "Pending Review") -> bool:
        detail = {"name": self.TASK, "status": current, "meta": meta}

        def update(key: str, token: str, task: str, wanted: str) -> Dict[str, Any]:
            self.moves.append({"task": task, "status": wanted})
            return {"name": task, "status": wanted}

        with patch.object(self.service, "_erp_credentials", return_value=("key", "token")), \
                patch.object(self.service, "_erp_task_detail", return_value=detail), \
                patch.object(self.service, "_erp_update_task_status", side_effect=update):
            return asyncio.run(
                self.service._erp_advance_task_status("job-1", self.TASK, status)
            )

    def test_a_plain_card_is_closed_when_its_images_are_done(self) -> None:
        moved = self._advance(FlowWebService.ERP_STATUS_COMPLETED, meta="")

        self.assertTrue(moved)
        self.assertEqual([{"task": self.TASK, "status": "Completed"}], self.moves)

    def test_a_listing_card_is_not_closed_when_its_images_are_done(self) -> None:
        # Thẻ listing xong ảnh mới xong nửa đầu. Đóng nó ở đây là giấu nó khỏi
        # chính con bot: ``is_idea_card`` coi "Completed" là đã đóng, và bảng
        # dự án không trả khối ``meta`` nên lượt lọc ứng viên không thể chừa
        # thẻ listing ra. Đóng sớm một nhịp = thẻ không bao giờ lên được Etsy.
        moved = self._advance(
            FlowWebService.ERP_STATUS_COMPLETED, meta="action_1: listing\nacc: acc32\n"
        )

        self.assertFalse(moved)
        self.assertEqual([], self.moves)
        self.assertTrue(
            any("thẻ listing" in line for line in self.service.store.logs),
            self.service.store.logs,
        )

    def test_a_listing_card_still_moves_to_pending_review(self) -> None:
        # Chỉ chặn đúng nước đóng thẻ. Đưa ảnh lên chờ 👍/👎 vẫn phải chạy,
        # nếu không thì người duyệt không thấy thẻ ở đâu cả.
        moved = self._advance(
            FlowWebService.ERP_STATUS_PENDING_REVIEW,
            meta="action_1: listing\n",
            current="Working",
        )

        self.assertTrue(moved)
        self.assertEqual([{"task": self.TASK, "status": "Pending Review"}], self.moves)


if __name__ == "__main__":
    unittest.main()
