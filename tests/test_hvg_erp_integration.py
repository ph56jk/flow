from __future__ import annotations

import asyncio
import io
import json
import os
import tempfile
import time
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.error import HTTPError

from fastapi import HTTPException

from flow_web.schemas import (
    CreateJobRequest,
    ERPConfig,
    ERPConfigUpdateRequest,
    ERPIdeaBatchRequest,
    JobArtifact,
    JobRecord,
)
from flow_web.service import FlowBrowserProfile, FlowWebService
from flow_web.store import StateStore


class _Response:
    status = 200

    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None


class _StillRunning:
    """Stands in for a job task in flight, without leaving a real one behind."""

    def done(self) -> bool:
        return False


class _ErpServiceTestCase(unittest.TestCase):
    """Shared harness: a temp state store plus a credentialed FlowWebService."""

    def setUp(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        state_file = root / "state.json"
        self.patches = [
            patch("flow_web.store.STATE_FILE", state_file),
            patch("flow_web.store.ensure_app_dirs", lambda: root.mkdir(parents=True, exist_ok=True)),
            patch("flow_web.service.ensure_app_dirs", lambda: root.mkdir(parents=True, exist_ok=True)),
        ]
        for item in self.patches:
            item.start()
        self.store = StateStore()
        self.service = FlowWebService(self.store)
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(api_key="test-key", api_secret="test-secret", project_id="PROJ-0049")
            )
        )

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.tempdir.cleanup()
        self.loop.close()
        asyncio.set_event_loop(None)


class HvgErpIntegrationTests(_ErpServiceTestCase):
    def test_graphql_uses_post_header_without_secret_in_url(self) -> None:
        with patch("flow_web.service.urlopen", return_value=_Response({"data": {"projectOverview": {}}})) as mocked:
            payload = self.service._erp_graphql(
                "query ProjectOverview($project: String!) { projectOverview(project: $project) }",
                {"project": "PROJ-0049"},
                "ProjectOverview",
                key="test-key",
                token="test-secret",
            )

        self.assertEqual({"projectOverview": {}}, payload)
        request = mocked.call_args.args[0]
        self.assertEqual(
            "https://erp.havigroup.llc/api/method/hvg_workspace.graphql.endpoint.graphql",
            request.full_url,
        )
        self.assertNotIn("test-key", request.full_url)
        self.assertNotIn("test-secret", request.full_url)
        self.assertEqual("token test-key:test-secret", request.get_header("Authorization"))
        self.assertEqual("Flow-v2-HaviGroup-ERP/1.0", request.get_header("User-agent"))
        self.assertEqual("POST", request.get_method())

    def test_config_stays_on_one_project_and_masks_credentials(self) -> None:
        response = self.loop.run_until_complete(
            self.service.update_erp_config(
                ERPConfigUpdateRequest(
                    api_key="new-key",
                    api_secret="new-secret",
                    base_url="https://erp.havigroup.llc",
                    project_id="PROJ-0049",
                    task_id="TASK-0001",
                    status="Open",
                )
            )
        )
        self.assertNotIn("api_key", response)
        self.assertNotIn("api_secret", response)
        self.assertEqual("PROJ-0049", response["project_id"])

        # The owner may point the app at another project, but the app still
        # works inside exactly one project and rejects anything malformed.
        switched = self.loop.run_until_complete(
            self.service.update_erp_config(ERPConfigUpdateRequest(project_id="PROJ-0013"))
        )
        self.assertEqual("PROJ-0013", switched["project_id"])
        self.assertEqual("PROJ-0013", self.service._erp_allowed_project_id())

        with self.assertRaises(HTTPException) as ctx:
            self.loop.run_until_complete(
                self.service.update_erp_config(ERPConfigUpdateRequest(project_id="not-a-project"))
            )
        self.assertEqual(400, ctx.exception.status_code)

    def test_the_agent_projects_setting_widens_the_fence_without_moving_it(self) -> None:
        # Dropping the agent bot onto a card is meant to be the only setup
        # step, so a card outside ERP_PROJECT_ID has to be reachable — but the
        # configured project must stay allowed, and stay the default.
        self.assertEqual(["PROJ-0049"], self.service._erp_allowed_project_ids())
        with patch.dict(os.environ, {"ERP_AGENT_PROJECTS": "proj-0013 ; PROJ-0051"}):
            self.assertEqual(
                ["PROJ-0049", "PROJ-0013", "PROJ-0051"], self.service._erp_allowed_project_ids()
            )
            self.assertEqual("PROJ-0013", self.service._erp_required_project_id("PROJ-0013"))
            self.assertEqual("PROJ-0049", self.service._erp_required_project_id(""))

        with self.assertRaisesRegex(RuntimeError, "PROJ-0049"):
            self.service._erp_required_project_id("PROJ-0013")

    def test_a_board_the_bot_was_added_to_is_allowed_without_editing_env(self) -> None:
        # Thêm bot vào một board trên ERP là xong. Không phải khai lại board đó
        # ở ERP_AGENT_PROJECTS nữa, nếu không "chỉ cần thêm bot" là nói dối.
        bot = SimpleNamespace(state=SimpleNamespace(projects=["PROJ-0013", "proj-0051"]))
        with patch.object(self.service, "agent_bot", return_value=bot):
            self.assertEqual(
                ["PROJ-0049", "PROJ-0013", "PROJ-0051"], self.service._erp_allowed_project_ids()
            )
            self.assertEqual("PROJ-0051", self.service._erp_required_project_id("PROJ-0051"))
            # Dự án mặc định vẫn là mặc định.
            self.assertEqual("PROJ-0049", self.service._erp_required_project_id(""))

    def test_a_board_the_bot_no_longer_sees_falls_back_out_of_the_fence(self) -> None:
        # Gỡ bot khỏi board là board đó hết chạy — phạm vi do ERP quyết.
        bot = SimpleNamespace(state=SimpleNamespace(projects=[]))
        with patch.object(self.service, "agent_bot", return_value=bot):
            self.assertEqual(["PROJ-0049"], self.service._erp_allowed_project_ids())
            with self.assertRaisesRegex(RuntimeError, "PROJ-0013"):
                self.service._erp_required_project_id("PROJ-0013")

    def test_no_bot_configured_leaves_the_fence_exactly_as_it_was(self) -> None:
        with patch.object(self.service, "agent_bot", return_value=None):
            self.assertEqual(["PROJ-0049"], self.service._erp_allowed_project_ids())

    def test_a_bot_that_cannot_be_built_does_not_take_the_fence_down_with_it(self) -> None:
        with patch.object(self.service, "agent_bot", side_effect=RuntimeError("hỏng")):
            self.assertEqual(["PROJ-0049"], self.service._erp_allowed_project_ids())

    def test_the_env_fence_and_the_bots_own_boards_add_up(self) -> None:
        bot = SimpleNamespace(state=SimpleNamespace(projects=["PROJ-0013", "PROJ-0077"]))
        with patch.dict(os.environ, {"ERP_AGENT_PROJECTS": "PROJ-0013"}), patch.object(
            self.service, "agent_bot", return_value=bot
        ):
            # PROJ-0013 khai hai lần vẫn chỉ có một chỗ trong danh sách.
            self.assertEqual(
                ["PROJ-0049", "PROJ-0013", "PROJ-0077"], self.service._erp_allowed_project_ids()
            )

    def test_a_task_is_placed_in_whichever_allowed_project_actually_holds_it(self) -> None:
        boards = {
            "PROJ-0049": {"columns": [{"status": "Open", "tasks": [{"name": "TASK-0001"}]}]},
            "PROJ-0013": {"columns": [{"status": "Open", "tasks": [{"name": "TASK-0002"}]}]},
        }
        with patch.dict(os.environ, {"ERP_AGENT_PROJECTS": "PROJ-0013"}), patch.object(
            self.service, "_erp_task_board", side_effect=lambda _k, _t, project: boards[project]
        ):
            self.assertEqual("PROJ-0049", self.service._erp_task_project_id("key", "secret", "TASK-0001"))
            self.assertEqual("PROJ-0013", self.service._erp_task_project_id("key", "secret", "TASK-0002"))
            # A card in neither board is refused rather than defaulted, or its
            # images would be published back onto the wrong project's cards.
            with self.assertRaisesRegex(RuntimeError, "TASK-0009"):
                self.service._erp_task_project_id("key", "secret", "TASK-0009")

    def test_stale_local_state_cannot_redirect_credentialed_graphql_requests(self) -> None:
        normalized = self.store._normalize_erp_config(
            ERPConfig(api_key="key", api_secret="secret", base_url="https://unexpected.example")
        )
        self.assertEqual("https://erp.havigroup.llc", normalized.base_url)

    def test_graphql_errors_and_auth_failures_are_explicit_and_redacted(self) -> None:
        with patch("flow_web.service.urlopen", return_value=_Response({"data": None, "errors": [{"message": "bad query"}]})):
            with self.assertRaisesRegex(RuntimeError, "ERP GraphQL: bad query"):
                self.service._erp_graphql("query { myWork }", {}, "MyWork", key="key", token="secret")

        for status in (401, 429):
            error = HTTPError("https://erp.havigroup.llc", status, "error", {}, io.BytesIO(b"key=key token=secret"))
            with patch("flow_web.service.urlopen", side_effect=error):
                with self.assertRaisesRegex(RuntimeError, f"HTTP {status}"):
                    self.service._erp_graphql("query { myWork }", {}, "MyWork", key="key", token="secret")

    def test_task_board_is_normalized_as_project_tasks(self) -> None:
        board = {
            "columns": [
                {"status": "Open", "tasks": [{"name": "TASK-0001", "subject": "Source product"}]},
            ],
            "total": 1,
        }
        with patch.object(self.service, "_erp_task_board", return_value=board):
            tasks = self.service._erp_get_json("boards/PROJ-0049/cards", "key", "secret")

        self.assertEqual(1, len(tasks))
        self.assertEqual("TASK-0001", tasks[0]["id"])
        self.assertEqual("Open", tasks[0]["idList"])
        self.assertIn("erp.havigroup.llc", tasks[0]["url"])

    def test_task_detail_checks_membership_before_reading_task(self) -> None:
        with patch.object(self.service, "_erp_assert_task_in_project") as assert_member, patch.object(
            self.service, "_erp_task_detail", return_value={"name": "TASK-0001", "subject": "Source product"}
        ):
            self.service._erp_get_json("cards/TASK-0001", "key", "secret")

        assert_member.assert_called_once_with("key", "secret", "TASK-0001")

    def test_archive_writes_only_dashboard_approved_https_artifact_urls_to_source_task(self) -> None:
        request = CreateJobRequest(
            type="image",
            erp_enabled=True,
            erp_project_id="PROJ-0049",
            erp_source_task_id="TASK-0001",
            erp_task_id="TASK-0001",
        )
        artifacts = [
            JobArtifact(media_name="approved.jpg", url="https://media.example/approved.jpg"),
            JobArtifact(media_name="rejected.jpg", url="https://media.example/rejected.jpg"),
        ]
        job = JobRecord(
            type="image",
            result={
                "dashboard_approvals": {
                    "0": {"status": "approved"},
                    "1": {"status": "rejected"},
                }
            },
        )
        self.loop.run_until_complete(self.store.add_job(job))
        with patch.object(self.service, "_erp_assert_task_in_project") as assert_task, patch.object(
            self.service,
            "_erp_attach_url",
            return_value={"id": "https://media.example/approved.jpg", "name": "approved.jpg", "url": "https://media.example/approved.jpg"},
        ) as attach:
            result = self.loop.run_until_complete(self.service._archive_erp_artifacts(job.id, request, artifacts))

        assert_task.assert_called_once_with("test-key", "test-secret", "TASK-0001")
        attach.assert_called_once()
        self.assertEqual("https://media.example/approved.jpg", attach.call_args.args[3])
        self.assertEqual(1, result["sent"])
        self.assertEqual(1, result["rejected"])

    def test_archive_waits_without_a_dashboard_decision(self) -> None:
        request = CreateJobRequest(type="image", erp_enabled=True, erp_project_id="PROJ-0049", erp_source_task_id="TASK-0001")
        artifact = JobArtifact(media_name="pending.jpg", url="https://media.example/pending.jpg")
        job = JobRecord(type="image", result={"dashboard_approvals": {}})
        self.loop.run_until_complete(self.store.add_job(job))
        with patch.object(self.service, "_erp_attach_url") as attach:
            result = self.loop.run_until_complete(self.service._archive_erp_artifacts(job.id, request, [artifact]))

        attach.assert_not_called()
        self.assertTrue(result["waiting_approval"])

    def test_resume_preserves_original_indexes_when_first_artifact_is_rejected(self) -> None:
        request = CreateJobRequest(type="image", erp_enabled=True, erp_project_id="PROJ-0049")
        rejected = JobArtifact(media_name="rejected.jpg", url="https://media.example/rejected.jpg")
        approved = JobArtifact(media_name="approved.jpg", url="https://media.example/approved.jpg")
        job = JobRecord(
            type="image",
            input=request.model_dump() if hasattr(request, "model_dump") else request.dict(),
            artifacts=[rejected, approved],
            result={
                "dashboard_approvals": {
                    "0": {"status": "rejected"},
                    "1": {"status": "approved"},
                }
            },
        )
        self.loop.run_until_complete(self.store.add_job(job))
        with patch.object(self.service, "_automation_modules_after", return_value=[{"enabled": True, "type": "erp"}]), patch.object(
            self.service, "_run_automation_post_modules", new_callable=AsyncMock, return_value={"erp": {"sent": 1}}
        ) as resume:
            self.loop.run_until_complete(self.service._resume_automation_after_approval(job.id, "approval"))

        received = resume.call_args.args[2]
        self.assertEqual(["rejected.jpg", "approved.jpg"], [item.media_name for item in received])

    def test_imported_telegram_module_is_removed_before_automation_runs(self) -> None:
        request = CreateJobRequest(
            type="image",
            erp_enabled=True,
            automation_graph={
                "modules": [
                    {"id": "flow", "type": "flow"},
                    {"id": "legacy-telegram", "type": "telegram"},
                    {"id": "approval", "type": "approval"},
                    {"id": "erp", "type": "erp"},
                ],
                "edges": [
                    {"source": "flow", "target": "legacy-telegram"},
                    {"source": "legacy-telegram", "target": "approval"},
                    {"source": "approval", "target": "erp"},
                ],
            },
        )

        graph = self.service._automation_graph_payload(request)

        self.assertNotIn("telegram", [item["type"] for item in graph["modules"]])
        module_ids = {item["id"] for item in graph["modules"]}
        self.assertTrue(all(edge["source"] in module_ids and edge["target"] in module_ids for edge in graph["edges"]))
        approval = next(item for item in graph["modules"] if item["type"] == "approval")
        self.assertEqual("dashboard", approval["settings"]["approvalMode"])

    def test_dashboard_approval_resumes_erp_only_after_final_decision(self) -> None:
        request = CreateJobRequest(type="image", erp_enabled=True, erp_project_id="PROJ-0049")
        artifact = JobArtifact(media_name="approved.jpg", url="https://media.example/approved.jpg")
        job = JobRecord(
            type="image",
            input=request.model_dump() if hasattr(request, "model_dump") else request.dict(),
            artifacts=[artifact],
            result={
                "automation_execution": {
                    "nodes": [
                        {"id": "approval", "type": "approval", "status": "running", "output": {}},
                        {"id": "erp", "type": "erp", "status": "pending", "output": {}},
                    ]
                }
            },
        )
        self.loop.run_until_complete(self.store.add_job(job))
        with patch.object(
            self.service,
            "_run_automation_post_modules",
            new_callable=AsyncMock,
            return_value={"erp": {"sent": 1}},
        ) as resume:
            approval = self.loop.run_until_complete(
                self.service.apply_dashboard_approval(job.id, 0, "approved")
            )

        self.assertEqual("approved", approval["status"])
        resume.assert_awaited_once()
        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertEqual("approved", saved.result["dashboard_approvals"]["0"]["status"])
        self.assertEqual(0, saved.result["dashboard_approval_summary"]["pending"])

    def test_dashboard_can_add_public_image_to_open_idea_review(self) -> None:
        source = JobArtifact(media_name="flow-output.jpg", url="https://media.example/flow-output.jpg")
        job = JobRecord(
            type="image",
            artifacts=[source],
            result={
                "automation_execution": {
                    "nodes": [
                        {"id": "approval", "type": "approval", "status": "running", "output": {}},
                        {"id": "erp", "type": "erp", "status": "pending", "output": {}},
                    ]
                }
            },
        )
        self.loop.run_until_complete(self.store.add_job(job))

        added = self.loop.run_until_complete(
            self.service.add_dashboard_artifact(
                job.id,
                "https://media.example/revised-idea.png",
                "Ảnh chị Phương sửa",
                "Hồ Thanh Phong",
            )
        )

        self.assertEqual("Ảnh chị Phương sửa", added["label"])
        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertEqual(2, len(saved.artifacts))
        self.assertEqual("https://media.example/revised-idea.png", saved.artifacts[1].public_url)
        self.assertEqual(2, saved.result["dashboard_approval_summary"]["pending"])
        approval_node = saved.result["automation_execution"]["nodes"][0]
        self.assertEqual("running", approval_node["status"])

    def test_dashboard_rejects_unsafe_or_closed_idea_additions(self) -> None:
        job = JobRecord(
            type="image",
            artifacts=[JobArtifact(media_name="flow-output.jpg", url="https://media.example/flow-output.jpg")],
            result={
                "automation_execution": {
                    "nodes": [{"id": "approval", "type": "approval", "status": "running", "output": {}}]
                }
            },
        )
        self.loop.run_until_complete(self.store.add_job(job))

        with self.assertRaises(HTTPException) as invalid_url:
            self.loop.run_until_complete(self.service.add_dashboard_artifact(job.id, "http://media.example/nope.jpg"))
        self.assertEqual(400, invalid_url.exception.status_code)

        saved = self.store.get_job(job.id)
        saved.result["automation_execution"]["nodes"][0]["status"] = "completed"
        self.loop.run_until_complete(self.store.patch_job(job.id, result=saved.result))
        with self.assertRaises(HTTPException) as completed_review:
            self.loop.run_until_complete(self.service.add_dashboard_artifact(job.id, "https://media.example/late.jpg"))
        self.assertEqual(409, completed_review.exception.status_code)


class HvgErpIdeaFanOutTests(_ErpServiceTestCase):
    """The "Phân rã công việc" flow: one child card = one idea = one job."""

    PARENT = "TASK-2026-00202"
    CHILD_A = "TASK-2026-00615"
    CHILD_B = "TASK-2026-00616"

    def _details(
        self,
        *,
        child_a_has_flow_images: bool = False,
        child_a_comments: list | None = None,
        child_b_comments: list | None = None,
        child_b_blank: bool = False,
        child_a_cover: str = "",
        child_b_cover: str = "",
    ) -> dict:
        return {
            self.PARENT: {
                "name": self.PARENT,
                "subject": "Idea",
                "status": "Working",
                "description": "<p>Tạo 85 idea cho khăn tay thêu tay mùa christmas</p>",
                "cover_image": "/private/files/khan-tay.jpg",
                "children": [
                    {"name": self.CHILD_A, "subject": "a"},
                    {"name": self.CHILD_B, "subject": "b"},
                ],
            },
            self.CHILD_A: {
                "name": self.CHILD_A,
                "subject": "a",
                # Child cards stay in Open while the parent Idea card has
                # already been moved on to Working.
                "status": "Open",
                "description": "<p>Khăn tay đặt cạnh cây thông</p>",
                "cover_image": child_a_cover,
                "comments": (
                    [{"content": "[FLOW_V2_ARTIFACT] https://erp.havigroup.llc/files/flow-1.png"}]
                    if child_a_has_flow_images
                    else list(child_a_comments or [])
                ),
            },
            self.CHILD_B: {
                "name": self.CHILD_B,
                "subject": "b",
                "status": "Open",
                "description": "" if child_b_blank else "<p>Khăn tay trong hộp quà</p>",
                "cover_image": child_b_cover,
                "comments": list(child_b_comments or []),
            },
        }

    def _enqueue(
        self,
        request,
        *,
        child_a_has_flow_images: bool = False,
        child_a_comments: list | None = None,
        child_b_comments: list | None = None,
        child_b_blank: bool = False,
        child_a_cover: str = "",
        child_b_cover: str = "",
    ) -> dict:
        details = self._details(
            child_a_has_flow_images=child_a_has_flow_images,
            child_a_comments=child_a_comments,
            child_b_comments=child_b_comments,
            child_b_blank=child_b_blank,
            child_a_cover=child_a_cover,
            child_b_cover=child_b_cover,
        )
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(api_key="test-key", api_secret="test-secret", project_id="PROJ-0013")
            )
        )
        with patch.object(
            self.service, "_erp_task_project_id", return_value="PROJ-0013"
        ), patch.object(
            self.service, "_erp_task_detail", side_effect=lambda _key, _token, task_id: details[task_id]
        ), patch.object(
            self.service, "_erp_task_attachment_files", return_value=[]
        ), patch.object(self.service, "_run_flow_job", new_callable=AsyncMock) as run:
            response = self.loop.run_until_complete(self.service.enqueue_erp_idea_jobs(request))
            # Let the sequential runner drain so its calls are observable.
            self.loop.run_until_complete(asyncio.sleep(0))
            self.loop.run_until_complete(asyncio.sleep(0))
        self._run_flow_job = run
        return response

    def test_each_idea_card_gets_its_own_job_writing_back_to_that_card(self) -> None:
        response = self._enqueue(ERPIdeaBatchRequest(task_id=self.PARENT, count=12))

        self.assertEqual([self.CHILD_A, self.CHILD_B], [item["task_id"] for item in response["queued"]])
        self.assertEqual("PROJ-0013", response["project_id"])
        self.assertEqual(12, response["count"])
        # The idea image lives on the parent card, including as its cover.
        self.assertTrue(response["source_attachment_id"].endswith("khan-tay.jpg"))

        jobs = [self.store.get_job(item["job_id"]) for item in response["queued"]]
        for job, child_id in zip(jobs, [self.CHILD_A, self.CHILD_B]):
            self.assertIsNotNone(job)
            self.assertEqual(child_id, job.input["erp_output_task_id"])
            self.assertEqual(self.PARENT, job.input["erp_source_task_id"])
            self.assertEqual("PROJ-0013", job.input["erp_project_id"])
            self.assertEqual(12, job.input["count"])
        self.assertIn("Khăn tay đặt cạnh cây thông", jobs[0].input["prompt"])
        self.assertIn("Khăn tay trong hộp quà", jobs[1].input["prompt"])
        self.assertNotIn("<p>", jobs[0].input["prompt"])

    def test_ideas_that_already_carry_flow_images_are_skipped_unless_asked_for(self) -> None:
        response = self._enqueue(ERPIdeaBatchRequest(task_id=self.PARENT), child_a_has_flow_images=True)
        self.assertEqual([self.CHILD_B], [item["task_id"] for item in response["queued"]])
        self.assertEqual([self.CHILD_A], [item["task_id"] for item in response["skipped"]])

        rerun = self._enqueue(
            ERPIdeaBatchRequest(task_id=self.PARENT, include_done=True), child_a_has_flow_images=True
        )
        self.assertEqual([self.CHILD_A, self.CHILD_B], [item["task_id"] for item in rerun["queued"]])

    def test_an_idea_whose_images_are_still_awaiting_a_decision_is_not_run_again(self) -> None:
        # The card carries a full set of images nobody has answered yet. Only
        # counting the approved output would put a second set on top of them.
        pending = [{"content": "[FLOW_V2_REVIEW job-1#0] Ảnh 1/12 chờ duyệt"}]

        response = self._enqueue(ERPIdeaBatchRequest(task_id=self.PARENT), child_b_comments=pending)

        self.assertEqual([self.CHILD_A], [item["task_id"] for item in response["queued"]])
        self.assertEqual(
            [{"task_id": self.CHILD_B, "subject": "b", "reason": "đang có ảnh chờ duyệt trên thẻ"}],
            response["skipped"],
        )

    def test_an_image_only_comment_still_says_the_card_has_been_run(self) -> None:
        # New comments put nothing on the card but the picture: the markers the
        # gate reads now travel in the comment's ``meta``. Missing them would
        # hand the card a second set of images on top of the first.
        done = [{"content": "\u200b", "meta": "[FLOW_V2_ARTIFACT] flow-1.png"}]
        pending = [{"content": "\u200b", "meta": "[FLOW_V2_REVIEW job-1#0]"}]

        response = self._enqueue(
            ERPIdeaBatchRequest(task_id=self.PARENT), child_a_comments=done, child_b_comments=pending
        )

        self.assertEqual([], response["queued"])
        self.assertEqual(
            [
                {"task_id": self.CHILD_A, "subject": "a", "reason": "đã có ảnh Flow"},
                {"task_id": self.CHILD_B, "subject": "b", "reason": "đang có ảnh chờ duyệt trên thẻ"},
            ],
            response["skipped"],
        )

    def test_an_idea_card_uses_its_own_picture_as_the_source(self) -> None:
        # On this board the idea is a picture: each child card's cover shows
        # the embroidery to make content for. Falling back to the parent's
        # image would ask every card the same question.
        response = self._enqueue(
            ERPIdeaBatchRequest(task_id=self.PARENT), child_a_cover="/private/files/tho-noel.jpg"
        )

        first, second = (self.store.get_job(item["job_id"]) for item in response["queued"])
        self.assertTrue(first.input["erp_source_attachment_ids"][0].endswith("tho-noel.jpg"))
        self.assertEqual(self.CHILD_A, first.input["erp_source_task_id"])
        self.assertEqual(self.CHILD_A, first.input["erp_output_task_id"])
        self.assertIn("ảnh idea của chính thẻ này", first.input["prompt"])
        # The card with no picture of its own still borrows the parent's.
        self.assertTrue(second.input["erp_source_attachment_ids"][0].endswith("khan-tay.jpg"))
        self.assertEqual(self.PARENT, second.input["erp_source_task_id"])

    def test_the_source_column_follows_the_card_the_image_comes_from(self) -> None:
        # ERP Source refuses to read a card outside the column it was given.
        # Handing it the parent's column killed every job with "Card ERP đã
        # chọn không nằm trong cột Open" once the source became the child card.
        response = self._enqueue(
            ERPIdeaBatchRequest(task_id=self.PARENT), child_a_cover="/private/files/tho-noel.jpg"
        )

        first, second = (self.store.get_job(item["job_id"]) for item in response["queued"])
        self.assertEqual("Open", first.input["erp_status_id"])
        self.assertEqual("Open", first.input["automation_graph"]["modules"][0]["settings"]["erpStatus"])
        # The card without a picture reads the parent's, so the parent's column.
        self.assertEqual("Working", second.input["erp_status_id"])
        self.assertEqual("Working", second.input["automation_graph"]["modules"][0]["settings"]["erpStatus"])

    def test_two_idea_cards_are_in_flight_at_the_same_time(self) -> None:
        # Running the cards one behind the other left the browser idle through
        # the whole watermark/upload tail of the card in front of it.
        details = self._details()
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(api_key="test-key", api_secret="test-secret", project_id="PROJ-0013")
            )
        )
        in_flight = 0
        peak = 0

        async def _run(_job_id: str, _request) -> None:
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0)
            in_flight -= 1

        with patch.object(
            self.service, "_erp_task_project_id", return_value="PROJ-0013"
        ), patch.object(
            self.service, "_erp_task_detail", side_effect=lambda _key, _token, task_id: details[task_id]
        ), patch.object(
            self.service, "_erp_task_attachment_files", return_value=[]
        ), patch.object(self.service, "_run_flow_job", new=_run):
            self.loop.run_until_complete(
                self.service.enqueue_erp_idea_jobs(ERPIdeaBatchRequest(task_id=self.PARENT))
            )
            for _ in range(10):
                self.loop.run_until_complete(asyncio.sleep(0))

        self.assertEqual(2, peak)

    def test_a_card_whose_idea_is_only_a_picture_is_still_run(self) -> None:
        # Title "b" and no description, but the cover carries the idea.
        response = self._enqueue(
            ERPIdeaBatchRequest(task_id=self.PARENT),
            child_b_blank=True,
            child_b_cover="/private/files/xe-tai-thong.jpg",
        )

        self.assertEqual([self.CHILD_A, self.CHILD_B], [item["task_id"] for item in response["queued"]])

    def test_an_idea_card_with_no_idea_text_is_not_run(self) -> None:
        # A card titled "b" with an empty description gives the same prompt as
        # every other empty card, so the run would just repeat one image.
        response = self._enqueue(ERPIdeaBatchRequest(task_id=self.PARENT), child_b_blank=True)

        self.assertEqual([self.CHILD_A], [item["task_id"] for item in response["queued"]])
        self.assertEqual(
            [
                {
                    "task_id": self.CHILD_B,
                    "subject": "b",
                    "reason": "thẻ con chưa có nội dung idea (tiêu đề/mô tả trống)",
                }
            ],
            response["skipped"],
        )

        forced = self._enqueue(
            ERPIdeaBatchRequest(task_id=self.PARENT, include_done=True), child_b_blank=True
        )
        self.assertEqual([self.CHILD_A, self.CHILD_B], [item["task_id"] for item in forced["queued"]])

    def test_an_idea_this_app_already_ran_is_not_run_again(self) -> None:
        # The first run may still be generating, so the card itself is empty:
        # the job that targets it is the only record that it was started.
        self.loop.run_until_complete(
            self.store.add_job(
                JobRecord(type="image", status="running", input={"erp_output_task_id": self.CHILD_B})
            )
        )

        response = self._enqueue(ERPIdeaBatchRequest(task_id=self.PARENT))

        self.assertEqual([self.CHILD_A], [item["task_id"] for item in response["queued"]])
        self.assertEqual("đã có lượt chạy trong app", response["skipped"][0]["reason"])

    def test_a_run_that_failed_leaves_the_idea_free_to_run_again(self) -> None:
        self.loop.run_until_complete(
            self.store.add_job(
                JobRecord(type="image", status="failed", input={"erp_output_task_id": self.CHILD_B})
            )
        )

        response = self._enqueue(ERPIdeaBatchRequest(task_id=self.PARENT))

        self.assertEqual([self.CHILD_A, self.CHILD_B], [item["task_id"] for item in response["queued"]])

    def test_a_run_the_app_never_finished_leaves_the_idea_free_to_run_again(self) -> None:
        # "interrupted" is stamped on a job that was still running when the app
        # went down. Nothing resumes it, so treating it as a live run fenced the
        # idea card off for good and the card stayed empty forever.
        self.loop.run_until_complete(
            self.store.add_job(
                JobRecord(type="image", status="interrupted", input={"erp_output_task_id": self.CHILD_B})
            )
        )

        response = self._enqueue(ERPIdeaBatchRequest(task_id=self.PARENT))

        self.assertEqual([self.CHILD_A, self.CHILD_B], [item["task_id"] for item in response["queued"]])
        self.assertEqual([], response["skipped"])

    def test_the_watcher_runs_the_children_of_the_configured_idea_card(self) -> None:
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(
                    api_key="test-key",
                    api_secret="test-secret",
                    project_id="PROJ-0013",
                    task_id=self.PARENT,
                )
            )
        )
        details = self._details(child_a_has_flow_images=True)

        with patch.object(
            self.service, "_erp_task_project_id", return_value="PROJ-0013"
        ), patch.object(
            self.service, "_erp_task_detail", side_effect=lambda _key, _token, task_id: details[task_id]
        ), patch.object(self.service, "_run_flow_job", new_callable=AsyncMock):
            response = self.loop.run_until_complete(self.service.autorun_erp_idea_children())
            self.loop.run_until_complete(asyncio.sleep(0))

        # Only the idea that has no images yet - nobody had to press anything.
        self.assertEqual([self.CHILD_B], [item["task_id"] for item in response["queued"]])

    def test_the_watcher_does_nothing_until_an_idea_card_is_configured(self) -> None:
        with patch.object(self.service, "_erp_task_detail") as detail:
            response = self.loop.run_until_complete(self.service.autorun_erp_idea_children())

        detail.assert_not_called()
        self.assertEqual([], response["queued"])
        self.assertIn("chưa cấu hình", response["reason"])

    def test_the_watcher_waits_for_the_run_in_flight(self) -> None:
        # One browser, one Flow session: a second fan-out on top of a running
        # one would fight it for the same window.
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(
                    api_key="test-key",
                    api_secret="test-secret",
                    project_id="PROJ-0013",
                    task_id=self.PARENT,
                )
            )
        )
        self.service._tasks["busy"] = _StillRunning()

        with patch.object(self.service, "_erp_task_detail") as detail:
            response = self.loop.run_until_complete(self.service.autorun_erp_idea_children())

        detail.assert_not_called()
        self.assertEqual("đang có lượt chạy", response["reason"])

    def test_the_watcher_holds_off_while_every_flow_profile_is_out_of_quota(self) -> None:
        # Mỗi vòng watcher vẫn xếp job cho từng thẻ con dù biết chắc lượt nào
        # cũng chết ở bước mở Flow, và job hỏng thì đẩy lịch sử thật ra khỏi
        # dashboard: sáng 19/08 sáu thẻ đã lấp trọn 50 chỗ trong ba phút một
        # vòng. Vá vẫn chạy vì đăng bù ảnh có sẵn không cần Flow.
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(
                    api_key="test-key",
                    api_secret="test-secret",
                    project_id="PROJ-0013",
                    task_id=self.PARENT,
                )
            )
        )
        profile = FlowBrowserProfile(index=0, label="Flow profile 1", path=Path(self.tempdir.name) / "profile")
        self.service._flow_profile_quota_blocked_until = {profile.key: time.time() + 3600}

        with patch.object(self.service, "_flow_profile_specs", return_value=[profile]), patch.object(
            self.service, "repair_erp_idea_children", new_callable=AsyncMock, return_value={"republished": []}
        ) as repair, patch.object(
            self.service, "enqueue_erp_idea_jobs", new_callable=AsyncMock
        ) as enqueue:
            response = self.loop.run_until_complete(self.service.autorun_erp_idea_children())

        enqueue.assert_not_awaited()
        repair.assert_awaited_once()
        self.assertEqual([], response["queued"])
        self.assertIn("hết quota Agent", response["reason"])

    def test_the_agent_bot_holds_off_while_every_flow_profile_is_out_of_quota(self) -> None:
        profile = FlowBrowserProfile(index=0, label="Flow profile 1", path=Path(self.tempdir.name) / "profile")
        self.service._flow_profile_quota_blocked_until = {profile.key: time.time() + 3600}

        with patch.object(self.service, "_flow_profile_specs", return_value=[profile]), patch.object(
            self.service, "repair_erp_idea_children", new_callable=AsyncMock, return_value={"republished": []}
        ), patch.object(self.service, "enqueue_erp_idea_jobs", new_callable=AsyncMock) as enqueue:
            response = self.loop.run_until_complete(self.service._agent_bot_autorun(self.PARENT))

        enqueue.assert_not_awaited()
        self.assertEqual([], response["queued"])
        self.assertIn("hết quota Agent", response["reason"])

    def test_a_profile_still_free_keeps_the_watcher_running(self) -> None:
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(
                    api_key="test-key",
                    api_secret="test-secret",
                    project_id="PROJ-0013",
                    task_id=self.PARENT,
                )
            )
        )
        blocked = FlowBrowserProfile(index=0, label="Flow profile 1", path=Path(self.tempdir.name) / "one")
        free = FlowBrowserProfile(index=1, label="Flow profile 2", path=Path(self.tempdir.name) / "two")
        self.service._flow_profile_quota_blocked_until = {blocked.key: time.time() + 3600}

        with patch.object(self.service, "_flow_profile_specs", return_value=[blocked, free]), patch.object(
            self.service, "repair_erp_idea_children", new_callable=AsyncMock, return_value={"republished": []}
        ), patch.object(
            self.service, "enqueue_erp_idea_jobs", new_callable=AsyncMock, return_value={"queued": []}
        ) as enqueue:
            self.loop.run_until_complete(self.service.autorun_erp_idea_children())

        enqueue.assert_awaited_once()

    def test_only_the_requested_child_cards_are_run(self) -> None:
        response = self._enqueue(ERPIdeaBatchRequest(task_id=self.PARENT, child_task_ids=[self.CHILD_B]))
        self.assertEqual([self.CHILD_B], [item["task_id"] for item in response["queued"]])

    def test_idea_images_land_on_the_idea_card_outside_the_parent_reply_thread(self) -> None:
        request = CreateJobRequest(
            type="image",
            erp_enabled=True,
            erp_project_id="PROJ-0049",
            erp_task_id=self.PARENT,
            erp_source_task_id=self.PARENT,
            erp_output_task_id=self.CHILD_A,
        )
        artifact = JobArtifact(media_name="idea-a.jpg", url="https://media.example/idea-a.jpg")
        job = JobRecord(type="image", result={"dashboard_approvals": {"0": {"status": "approved"}}})
        self.loop.run_until_complete(self.store.add_job(job))

        with patch.object(self.service, "_erp_assert_task_in_project") as assert_task, patch.object(
            self.service, "_erp_source_comment_id"
        ) as source_comment, patch.object(
            self.service,
            "_erp_attach_url",
            return_value={"id": "https://media.example/idea-a.jpg", "name": "idea-a.jpg", "url": "https://media.example/idea-a.jpg"},
        ) as attach:
            result = self.loop.run_until_complete(self.service._archive_erp_artifacts(job.id, request, [artifact]))

        assert_task.assert_called_once_with("test-key", "test-secret", self.CHILD_A)
        source_comment.assert_not_called()
        self.assertEqual(self.CHILD_A, attach.call_args.args[2])
        self.assertEqual(1, result["sent"])

    def test_an_idea_card_receives_nothing_until_every_image_is_decided(self) -> None:
        """The reviewer's gate guards the idea card, not just the source card."""
        request = CreateJobRequest(
            type="image",
            erp_enabled=True,
            erp_project_id="PROJ-0049",
            erp_task_id=self.PARENT,
            erp_source_task_id=self.PARENT,
            erp_output_task_id=self.CHILD_A,
        )
        artifacts = [
            JobArtifact(media_name="idea-a-1.jpg", url="https://media.example/idea-a-1.jpg"),
            JobArtifact(media_name="idea-a-2.jpg", url="https://media.example/idea-a-2.jpg"),
        ]
        job = JobRecord(type="image", result={"dashboard_approvals": {"0": {"status": "approved"}}})
        self.loop.run_until_complete(self.store.add_job(job))

        with patch.object(self.service, "_erp_assert_task_in_project") as assert_task, patch.object(
            self.service, "_erp_attach_url"
        ) as attach:
            result = self.loop.run_until_complete(self.service._archive_erp_artifacts(job.id, request, artifacts))

        assert_task.assert_not_called()
        attach.assert_not_called()
        self.assertTrue(result["waiting_approval"])
        self.assertEqual(1, result["pending"])

    def test_a_rejected_idea_image_never_reaches_the_idea_card(self) -> None:
        request = CreateJobRequest(
            type="image",
            erp_enabled=True,
            erp_project_id="PROJ-0049",
            erp_task_id=self.PARENT,
            erp_source_task_id=self.PARENT,
            erp_output_task_id=self.CHILD_A,
        )
        artifacts = [
            JobArtifact(media_name="idea-a-1.jpg", url="https://media.example/idea-a-1.jpg"),
            JobArtifact(media_name="idea-a-2.jpg", url="https://media.example/idea-a-2.jpg"),
        ]
        job = JobRecord(
            type="image",
            result={"dashboard_approvals": {"0": {"status": "rejected"}, "1": {"status": "approved"}}},
        )
        self.loop.run_until_complete(self.store.add_job(job))

        with patch.object(self.service, "_erp_assert_task_in_project"), patch.object(
            self.service, "_erp_source_comment_id"
        ), patch.object(
            self.service,
            "_erp_attach_url",
            return_value={"id": "https://media.example/idea-a-2.jpg", "name": "idea-a-2.jpg", "url": "https://media.example/idea-a-2.jpg"},
        ) as attach:
            result = self.loop.run_until_complete(self.service._archive_erp_artifacts(job.id, request, artifacts))

        self.assertEqual(1, attach.call_count)
        self.assertEqual(self.CHILD_A, attach.call_args.args[2])
        self.assertEqual("https://media.example/idea-a-2.jpg", attach.call_args.args[3])
        # The surviving image keeps its original position, so a rejected first
        # image cannot make image 2 land on the card named as image 1.
        self.assertTrue(attach.call_args.args[4].endswith("-2.jpg"), attach.call_args.args[4])
        self.assertEqual(1, result["sent"])

    def test_a_cover_image_is_a_usable_source_attachment(self) -> None:
        attachments = self.service._erp_extract_task_attachments(
            {"name": self.PARENT, "cover_image": "/private/files/khan-tay.jpg"}
        )
        self.assertEqual(1, len(attachments))
        self.assertEqual("khan-tay.jpg", attachments[0]["name"])
        self.assertTrue(attachments[0]["url"].startswith("https://erp.havigroup.llc/"))

    def test_a_named_source_card_may_sit_outside_the_saved_source_column(self) -> None:
        """An "Idea" card lives in Working; only the auto sweep is column-locked."""
        request = CreateJobRequest(
            type="image",
            erp_enabled=True,
            erp_project_id="PROJ-0013",
            erp_status_id="Working",
            erp_task_id=self.PARENT,
            erp_source_task_id=self.PARENT,
            erp_source_attachment_ids=["private/files/khan-tay.jpg"],
            automation_graph={
                "version": 1,
                "edges": [],
                "modules": [
                    {
                        "id": "erp_source",
                        "type": "erp_source",
                        "enabled": True,
                        "settings": {"erpTask": self.PARENT, "erpStatus": "Working"},
                    },
                    {"id": "flow", "type": "flow", "enabled": True},
                ],
            },
        )
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(
                    api_key="test-key",
                    api_secret="test-secret",
                    project_id="PROJ-0013",
                    status="Open",  # the saved sweep column, not this card's column
                )
            )
        )
        job = JobRecord(type="image")
        self.loop.run_until_complete(self.store.add_job(job))

        with patch.object(
            self.service, "_erp_auto_source_list_ids", side_effect=lambda *_a, **_k: []
        ) as list_ids, patch.object(
            self.service, "_erp_task_hint_by_id", return_value={"name": self.PARENT, "status": "Working"}
        ), patch.object(
            self.service, "_download_erp_task_image_attachments", return_value=["/tmp/khan-tay.jpg"]
        ), patch.object(
            self.service, "_set_automation_module_status", new_callable=AsyncMock
        ):
            resolved = self.loop.run_until_complete(
                self.service._request_with_erp_source_images(job.id, request)
            )

        self.assertEqual("Working", list_ids.call_args.args[3])
        self.assertEqual("Working", resolved.erp_status_id)
        self.assertEqual(self.PARENT, resolved.erp_source_task_id)

    def test_the_project_guard_follows_the_configured_project(self) -> None:
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(api_key="test-key", api_secret="test-secret", project_id="PROJ-0013")
            )
        )
        self.assertEqual("PROJ-0013", self.service._erp_allowed_project_id())
        self.assertEqual("PROJ-0013", self.service._erp_required_project_id("PROJ-0013"))
        with self.assertRaisesRegex(RuntimeError, "PROJ-0013"):
            self.service._erp_required_project_id("PROJ-0049")


class HvgErpIdeaRepairTests(_ErpServiceTestCase):
    """Thẻ idea đứng im dù app tưởng đã chạy xong thì phải tự vá lại."""

    PARENT = "TASK-2026-00202"
    CHILD = "TASK-2026-00615"

    def setUp(self) -> None:
        super().setUp()
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(
                    api_key="test-key",
                    api_secret="test-secret",
                    project_id="PROJ-0013",
                    task_id=self.PARENT,
                )
            )
        )

    def _details(self, *, child_comments: list | None = None, child_status: str = "Open") -> dict:
        return {
            self.PARENT: {
                "name": self.PARENT,
                "subject": "Idea",
                "status": "Working",
                "description": "<p>Tạo idea cho khăn tay thêu tay</p>",
                "cover_image": "/private/files/khan-tay.jpg",
                "children": [{"name": self.CHILD, "subject": "Idea 1"}],
            },
            self.CHILD: {
                "name": self.CHILD,
                "subject": "Idea 1",
                "status": child_status,
                "description": "<p>Khăn tay đặt cạnh cây thông</p>",
                "cover_image": "",
                "comments": list(child_comments or []),
            },
        }

    def _job(
        self,
        *,
        images: int,
        wanted: int = 12,
        status: str = "completed",
        approvals: dict | None = None,
        created_at: str = "2026-08-18T09:00:00Z",
    ) -> JobRecord:
        job = JobRecord(
            type="image",
            status=status,
            created_at=created_at,
            input={"erp_output_task_id": self.CHILD, "count": wanted, "erp_enabled": True},
            artifacts=[
                JobArtifact(media_name=f"idea-{index}.jpg", url=f"https://media.example/idea-{index}.jpg")
                for index in range(images)
            ],
            result={"dashboard_approvals": approvals} if approvals else {},
        )
        self.loop.run_until_complete(self.store.add_job(job))
        return job

    def _review_comment(self, job_id: str, index: int) -> dict:
        """Đúng hình hài một bình luận ảnh chờ duyệt: chữ trống, dấu ở meta."""
        return {
            "name": f"cmt-{index}",
            "content": "​",
            "meta": f"[FLOW_V2_REVIEW {job_id}#{index}]",
            "attachments": [{"file_url": f"/files/flow-{index}.jpg"}],
        }

    def _repair(self, details: dict) -> tuple[dict, AsyncMock]:
        with patch.object(
            self.service, "_erp_task_project_id", return_value="PROJ-0013"
        ), patch.object(
            self.service, "_erp_task_detail", side_effect=lambda _key, _token, task_id: details[task_id]
        ), patch.object(
            self.service, "_erp_task_attachment_files", return_value=[]
        ), patch.object(
            self.service, "publish_erp_review", new_callable=AsyncMock
        ) as publish, patch.object(self.service, "_run_flow_job", new_callable=AsyncMock):
            publish.return_value = {"published": 12}
            response = self.loop.run_until_complete(self.service.repair_erp_idea_children())
            self.loop.run_until_complete(asyncio.sleep(0))
        return response, publish

    def test_a_finished_run_whose_images_never_reached_the_card_is_posted_again(self) -> None:
        # The network dropped while the images were going up. The run still
        # says "completed", so from then on nothing ever looked at this card.
        job = self._job(images=12)

        response, publish = self._repair(self._details())

        publish.assert_awaited_once_with(job.id)
        self.assertEqual(
            [{"task_id": self.CHILD, "job_id": job.id, "published": 12}], response["republished"]
        )
        self.assertEqual([], response["topped_up"])

    def test_the_rest_of_a_half_posted_batch_goes_up(self) -> None:
        job = self._job(images=12)
        details = self._details(child_comments=[self._review_comment(job.id, 0)])

        _response, publish = self._repair(details)

        publish.assert_awaited_once_with(job.id)

    def test_a_batch_already_fully_on_the_card_is_left_alone(self) -> None:
        job = self._job(images=2)
        details = self._details(
            child_comments=[self._review_comment(job.id, 0), self._review_comment(job.id, 1)]
        )

        response, publish = self._repair(details)

        publish.assert_not_awaited()
        self.assertEqual([], response["republished"])

    def test_an_older_batch_is_not_stacked_onto_a_card_that_already_shows_one(self) -> None:
        # The card shows the newer run's images. Putting the older run's
        # twelve up as well is what turns one card into a wall of duplicates.
        self._job(images=12, created_at="2026-08-15T02:00:00Z")
        newer = self._job(images=12, created_at="2026-08-15T04:00:00Z")
        details = self._details(
            child_comments=[self._review_comment(newer.id, index) for index in range(12)]
        )

        _response, publish = self._repair(details)

        publish.assert_not_awaited()

    def test_a_card_whose_images_were_all_rejected_is_not_refilled(self) -> None:
        # A blank card is not proof nothing was posted: 👎 removes the comment.
        # The decisions on the run are what tell the two apart.
        self._job(images=2, wanted=2, approvals={"0": {"status": "rejected"}, "1": {"status": "rejected"}})

        response, publish = self._repair(self._details())

        publish.assert_not_awaited()
        self.assertEqual([], response["topped_up"])

    def test_a_run_that_made_fewer_images_than_asked_is_topped_up(self) -> None:
        # Flow returned one of the twelve. Nothing on the card is wrong, so
        # there is nothing to post again - the other eleven must be made.
        job = self._job(images=1)
        details = self._details(child_comments=[self._review_comment(job.id, 0)])

        response, publish = self._repair(details)

        publish.assert_not_awaited()
        self.assertEqual([{"count": 11, "task_ids": [self.CHILD]}], [
            {"count": item["count"], "task_ids": item["task_ids"]} for item in response["topped_up"]
        ])
        queued = response["topped_up"][0]["queued"]
        self.assertEqual([self.CHILD], [item["task_id"] for item in queued])
        topped = self.store.get_job(queued[0]["job_id"])
        self.assertEqual(11, topped.input["count"])
        self.assertEqual(self.CHILD, topped.input["erp_output_task_id"])

    def test_topping_up_gives_up_after_too_many_runs(self) -> None:
        for index in range(self.service.ERP_IDEA_TOPUP_MAX_JOBS):
            self._job(images=1, created_at=f"2026-08-1{index}T09:00:00Z")
        details = self._details(
            child_comments=[self._review_comment(job_id, 0) for job_id in self.service._erp_child_job_ids(self.CHILD)]
        )

        response, _publish = self._repair(details)

        self.assertEqual([], response["topped_up"])
        self.assertIn("đã chạy quá nhiều lượt", response["skipped"][0]["reason"])

    def test_a_card_someone_closed_is_left_alone(self) -> None:
        self._job(images=1)

        response, publish = self._repair(self._details(child_status="Completed"))

        publish.assert_not_awaited()
        self.assertEqual([], response["topped_up"])

    def test_the_watcher_repairs_before_it_looks_for_new_ideas(self) -> None:
        # A card stuck behind a half-finished run is not in the "never run"
        # list, so the fan-out below would never see it.
        job = self._job(images=12)
        details = self._details()

        with patch.object(
            self.service, "_erp_task_project_id", return_value="PROJ-0013"
        ), patch.object(
            self.service, "_erp_task_detail", side_effect=lambda _key, _token, task_id: details[task_id]
        ), patch.object(
            self.service, "_erp_task_attachment_files", return_value=[]
        ), patch.object(
            self.service, "publish_erp_review", new_callable=AsyncMock
        ) as publish, patch.object(self.service, "_run_flow_job", new_callable=AsyncMock):
            publish.return_value = {"published": 12}
            response = self.loop.run_until_complete(self.service.autorun_erp_idea_children())
            self.loop.run_until_complete(asyncio.sleep(0))

        publish.assert_awaited_once_with(job.id)
        self.assertEqual(
            [self.CHILD], [item["task_id"] for item in response["repaired"]["republished"]]
        )


class HvgErpIdeaIntakeTests(_ErpServiceTestCase):
    """Thả ảnh lên thẻ Idea là có thẻ con: mỗi ảnh một thẻ, không phải gõ gì."""

    PARENT = "TASK-2026-00202"
    CHILD_A = "TASK-2026-00615"
    PRODUCT = "/private/files/khan-tay.jpg"

    def _board(
        self,
        dropped: list[str],
        children: list[str] | None = None,
        files: list[str] | None = None,
    ) -> dict:
        """A parent Idea card carrying the product photo plus dropped ideas."""
        details: dict = {
            self.PARENT: {
                "name": self.PARENT,
                "subject": "Idea",
                "status": "Working",
                "description": "<p>Khăn tay thêu tay mùa christmas</p>",
                "cover_image": self.PRODUCT,
                "children": [{"name": name, "subject": "a"} for name in (children or [])],
                "comments": [
                    {
                        "name": f"drop-{index}",
                        "content": "",
                        "attachments": [{"file_url": url, "file_name": Path(url).name}],
                    }
                    for index, url in enumerate(dropped)
                ],
            }
        }
        # Dropping a file straight onto the card in the ERP UI lands here, and
        # nowhere in taskDetail - hence the separate taskAttachments read.
        details["__files__"] = [
            # `name` on an ERP file row is the docname, not the file name.
            {"name": f"docname{index}", "file_name": Path(url).name, "file_url": url}
            for index, url in enumerate(files or [])
        ]
        for name in children or []:
            details[name] = {
                "name": name,
                "subject": "a",
                "status": "Open",
                "description": "<p>Khăn tay cạnh cây thông</p>",
                "cover_image": "",
                "comments": [],
            }
        return details

    def _wire(self, details: dict):
        """Stand in for every ERP write the intake makes, and record them."""
        created: list[dict] = []
        attached: list[dict] = []
        covers: list[tuple[str, str]] = []

        def _create(_key, _token, parent, project, subject, *, status="Open", description=""):
            child_id = f"TASK-NEW-{len(created)}"
            created.append({"id": child_id, "parent": parent, "project": project, "subject": subject, "status": status})
            details[parent]["children"].append({"name": child_id, "subject": subject})
            details[child_id] = {
                "name": child_id,
                "subject": subject,
                "status": status,
                "description": description,
                "cover_image": "",
                "comments": [],
            }
            return child_id

        def _download(_key, _token, _task_id, attachment):
            return f"bytes:{attachment.get('name')}".encode(), "image/jpeg"

        def _attach(
            _key, _token, task_id, data, mime, name, set_cover,
            parent_comment="", comment_text="", silent_comment=False,
        ):
            attached.append(
                {"task": task_id, "name": name, "bytes": data, "comment": comment_text, "silent": silent_comment}
            )
            # Bản sao trùng từng byte và trùng tên thì ERP dùng lại đúng tệp cũ,
            # nên thẻ con trỏ về chính đường dẫn của ảnh trên thẻ cha - đo trên
            # ERP thật. Đó cũng là thứ giữ chỗ cho ảnh, thay cho dòng chữ đánh
            # dấu ngày trước.
            url = f"/private/files/{name}"
            details[task_id]["comments"].append(
                {"name": f"cmt-{len(attached)}", "content": comment_text, "attachments": [{"file_url": url, "file_name": name}]}
            )
            return {"url": url, "name": name}

        def _cover(_key, _token, task_id, data, _mime, name):
            url = f"/private/files/{name}"
            covers.append((task_id, url))
            details[task_id]["cover_image"] = url
            details[task_id]["cover_bytes"] = data

        def _add_agent(_key, _token, task_id, bot_user):
            self.agents_added.append((task_id, bot_user))
            details[task_id].setdefault("agents", []).append({"bot_user": bot_user})

        self.agents_added = []
        return created, attached, covers, patch.multiple(
            self.service,
            _erp_task_project_id=lambda *_args, **_kwargs: "PROJ-0013",
            _erp_task_detail=lambda _key, _token, task_id: details[task_id],
            _erp_task_attachment_files=lambda _key, _token, task_id: (
                details.get("__files__", []) if task_id == self.PARENT else []
            ),
            _erp_create_child_task=_create,
            _erp_download_attachment_bytes=_download,
            _erp_attach_file_bytes=_attach,
            _erp_set_task_cover=_cover,
            _erp_add_task_agent=_add_agent,
        )

    def _intake(self, details: dict):
        created, attached, covers, wiring = self._wire(details)
        with wiring:
            outcome, child_details = self.loop.run_until_complete(
                self.service._erp_intake_idea_images(
                    "test-key", "test-secret", self.PARENT, "PROJ-0013", details[self.PARENT]
                )
            )
        return outcome, child_details, created, attached, covers

    def test_every_image_dropped_on_the_idea_card_becomes_a_child_card(self) -> None:
        details = self._board(
            ["/private/files/tho-noel.jpg", "/private/files/xe-tai-thong.jpg"], children=[self.CHILD_A]
        )

        outcome, _details, created, attached, covers = self._intake(details)

        self.assertEqual(["TASK-NEW-0", "TASK-NEW-1"], [item["task_id"] for item in outcome])
        # Numbered on from the cards already there, so the board reads in order.
        self.assertEqual(["Idea 2", "Idea 3"], [item["subject"] for item in created])
        self.assertEqual([self.PARENT, self.PARENT], [item["parent"] for item in created])
        self.assertEqual(["PROJ-0013", "PROJ-0013"], [item["project"] for item in created])
        self.assertEqual(["Open", "Open"], [item["status"] for item in created])

        # Each new card carries its own picture, and it is that card's cover so
        # the board shows the idea rather than an empty rectangle.
        self.assertEqual(["tho-noel.jpg", "xe-tai-thong.jpg"], [item["name"] for item in attached])
        self.assertEqual(["TASK-NEW-0", "TASK-NEW-1"], [item["task"] for item in attached])
        self.assertEqual(
            [
                ("TASK-NEW-0", "/private/files/tho-noel.jpg"),
                ("TASK-NEW-1", "/private/files/xe-tai-thong.jpg"),
            ],
            covers,
        )
        # The cover is set from the same bytes the card carries, because the
        # ERP refuses a cover that is not a file of that card's own.
        self.assertEqual(
            [item["bytes"] for item in attached],
            [details[task_id]["cover_bytes"] for task_id, _url in covers],
        )

    def test_a_new_child_card_carries_the_parents_agent(self) -> None:
        # Gắn agent vào thẻ cha là đã nói cả cụm việc này là của bot; thẻ con
        # sinh ra với ô người phụ trách trống trông như bị bỏ quên.
        details = self._board(["/private/files/tho-noel.jpg"], children=[self.CHILD_A])
        details[self.PARENT]["agents"] = [{"bot_user": "agent-kin@bots.hvg.internal"}]

        outcome, _details, _created, _attached, _covers = self._intake(details)

        self.assertEqual(
            [("TASK-NEW-0", "agent-kin@bots.hvg.internal")], self.agents_added
        )
        self.assertEqual(["TASK-NEW-0"], [item["task_id"] for item in outcome])

    def test_a_parent_with_no_agent_hands_down_no_agent(self) -> None:
        details = self._board(["/private/files/tho-noel.jpg"], children=[self.CHILD_A])

        self._intake(details)

        self.assertEqual([], self.agents_added)

    def test_every_agent_on_the_parent_is_handed_down(self) -> None:
        details = self._board(
            ["/private/files/tho-noel.jpg", "/private/files/xe-tai-thong.jpg"], children=[self.CHILD_A]
        )
        details[self.PARENT]["agents"] = [
            {"bot_user": "agent-kin@bots.hvg.internal"},
            {"bot_user": "agent-hai@bots.hvg.internal"},
        ]

        self._intake(details)

        self.assertEqual(
            [
                ("TASK-NEW-0", "agent-kin@bots.hvg.internal"),
                ("TASK-NEW-0", "agent-hai@bots.hvg.internal"),
                ("TASK-NEW-1", "agent-kin@bots.hvg.internal"),
                ("TASK-NEW-1", "agent-hai@bots.hvg.internal"),
            ],
            self.agents_added,
        )

    def test_the_product_photo_stays_the_product_photo(self) -> None:
        # The first image on the card is what every idea is a picture *of*, and
        # a card without a picture of its own still falls back to it. Turning it
        # into an idea card would run the product photo against itself.
        details = self._board(["/private/files/tho-noel.jpg"], children=[self.CHILD_A])

        outcome, _details, _created, attached, _covers = self._intake(details)

        self.assertEqual(1, len(outcome))
        self.assertEqual(["tho-noel.jpg"], [item["name"] for item in attached])

    def test_a_card_with_only_the_product_photo_creates_nothing(self) -> None:
        details = self._board([], children=[self.CHILD_A])

        outcome, child_details, created, _attached, _covers = self._intake(details)

        self.assertEqual([], outcome)
        self.assertEqual([], created)
        # Nothing to do means nothing read either: no child card was fetched.
        self.assertEqual({}, child_details)

    def test_the_same_image_is_not_given_a_second_card(self) -> None:
        # The ledger is on the cards themselves: the child card carries the very
        # picture it was made from, so a card deleted by hand really does put
        # its image back in the queue.
        details = self._board(["/private/files/tho-noel.jpg"], children=[self.CHILD_A])
        self._intake(details)

        again, _details, created, attached, _covers = self._intake(details)

        self.assertEqual([], again)
        self.assertEqual([], created)
        self.assertEqual([], attached)

    def test_the_child_card_is_given_the_picture_and_nothing_else(self) -> None:
        # Thẻ con là chỗ người ta nhìn, không phải sổ tay của bot: không một
        # dòng chữ nào được viết lên đó, kể cả dòng mặc định của app.
        details = self._board(["/private/files/tho-noel.jpg"], children=[self.CHILD_A])

        _outcome, _details, _created, attached, _covers = self._intake(details)

        self.assertEqual([""], [item["comment"] for item in attached])
        self.assertEqual([True], [item["silent"] for item in attached])
        for comment in details["TASK-NEW-0"]["comments"]:
            self.assertEqual("", comment["content"])

    def test_the_cover_alone_is_enough_to_hold_the_place(self) -> None:
        # Ảnh dán được nhưng bình luận mất - vẫn không được tạo thẻ thứ hai.
        details = self._board(["/private/files/tho-noel.jpg"], children=[self.CHILD_A])
        self._intake(details)
        details["TASK-NEW-0"]["comments"] = []

        again, _details, created, _attached, _covers = self._intake(details)

        self.assertEqual([], again)
        self.assertEqual([], created)

    def test_the_old_written_marker_still_holds_its_place(self) -> None:
        # Thẻ sinh ra trước thay đổi này còn mang dòng đánh dấu cũ; đọc sót nó
        # là tạo lại một thẻ đã có.
        details = self._board(["/private/files/tho-noel.jpg"], children=[self.CHILD_A])
        details[self.CHILD_A]["comments"] = [
            {"name": "cu", "content": "[FLOW_V2_IDEA src=/private/files/tho-noel.jpg] tho-noel.jpg", "attachments": []}
        ]

        outcome, _details, created, _attached, _covers = self._intake(details)

        self.assertEqual([], outcome)
        self.assertEqual([], created)

    def test_flow_output_on_a_child_card_claims_nothing(self) -> None:
        # Ảnh Flow tự sinh nằm trong thẻ con không được coi là chỗ đã giữ của
        # một ảnh idea nào cả.
        details = self._board(["/private/files/tho-noel.jpg"], children=[self.CHILD_A])
        details[self.CHILD_A]["comments"] = [
            {
                "name": "art",
                "content": "[FLOW_V2_REVIEW job#0] Ảnh 1/12 chờ duyệt",
                "attachments": [{"file_url": "/private/files/flow-abc-1.png", "file_name": "flow-abc-1.png"}],
            }
        ]

        outcome, _details, created, _attached, _covers = self._intake(details)

        self.assertEqual(1, len(outcome))
        self.assertEqual(1, len(created))

    def test_a_new_card_is_run_in_the_same_pass_that_created_it(self) -> None:
        details = self._board(["/private/files/tho-noel.jpg"], children=[self.CHILD_A])
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(api_key="test-key", api_secret="test-secret", project_id="PROJ-0013")
            )
        )
        _created, _attached, _covers, wiring = self._wire(details)
        with wiring, patch.object(self.service, "_run_flow_job", new_callable=AsyncMock):
            response = self.loop.run_until_complete(
                self.service.enqueue_erp_idea_jobs(ERPIdeaBatchRequest(task_id=self.PARENT))
            )
            self.loop.run_until_complete(asyncio.sleep(0))

        self.assertEqual(["TASK-NEW-0"], [item["task_id"] for item in response["created"]])
        self.assertEqual([self.CHILD_A, "TASK-NEW-0"], [item["task_id"] for item in response["queued"]])
        job = self.store.get_job(response["queued"][1]["job_id"])
        # The new card runs on its own picture, not on the parent's product photo.
        self.assertEqual("TASK-NEW-0", job.input["erp_output_task_id"])
        self.assertEqual("TASK-NEW-0", job.input["erp_source_task_id"])
        self.assertTrue(job.input["erp_source_attachment_ids"][0].endswith("tho-noel.jpg"))

    def test_a_file_dropped_straight_onto_the_card_is_found_too(self) -> None:
        # This is what the ERP UI actually does with a drag-and-drop: the file
        # joins the card's attachment list, where taskDetail never shows it and
        # its row is keyed by docname rather than by file name.
        details = self._board([], children=[self.CHILD_A], files=["/private/files/tho-noel.jpg"])

        outcome, _details, created, attached, _covers = self._intake(details)

        self.assertEqual(["Idea 2"], [item["subject"] for item in created])
        self.assertEqual(["tho-noel.jpg"], [item["name"] for item in attached])
        self.assertEqual(["/private/files/tho-noel.jpg"], [item["source"] for item in outcome])

    def test_a_card_whose_only_images_were_dragged_on_still_runs(self) -> None:
        # The whole point of the feature: a card where the user did nothing but
        # drag pictures onto it. Every one of those files sits in the Task's own
        # attachment list, which taskDetail does not report - so the card reads
        # back with no cover, no comments and no children, and the run used to
        # be refused before the intake ever got to look.
        details = self._board(
            [],
            files=["/private/files/san-pham.jpg", "/private/files/tho-noel.jpg"],
        )
        details[self.PARENT]["cover_image"] = ""
        details[self.PARENT]["children"] = []
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(api_key="test-key", api_secret="test-secret", project_id="PROJ-0013")
            )
        )
        _created, _attached, _covers, wiring = self._wire(details)
        with wiring, patch.object(self.service, "_run_flow_job", new_callable=AsyncMock):
            response = self.loop.run_until_complete(
                self.service.enqueue_erp_idea_jobs(ERPIdeaBatchRequest(task_id=self.PARENT))
            )
            self.loop.run_until_complete(asyncio.sleep(0))

        # The first file is the product photo; the second one gets the card.
        self.assertEqual(["TASK-NEW-0"], [item["task_id"] for item in response["created"]])
        self.assertEqual(["tho-noel.jpg"], [item["image"] for item in response["created"]])
        self.assertEqual(["TASK-NEW-0"], [item["task_id"] for item in response["queued"]])
        self.assertEqual([], response["skipped"])

    def test_a_child_with_no_picture_anywhere_is_skipped_not_refused(self) -> None:
        # The parent's images all live in its attachment list, so it has no
        # source image to lend; the hand-made child has none of its own either.
        # That is one card's problem, not a reason to refuse the whole run.
        details = self._board(
            [],
            children=[self.CHILD_A],
            files=["/private/files/san-pham.jpg", "/private/files/tho-noel.jpg"],
        )
        details[self.PARENT]["cover_image"] = ""
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(api_key="test-key", api_secret="test-secret", project_id="PROJ-0013")
            )
        )
        _created, _attached, _covers, wiring = self._wire(details)
        with wiring, patch.object(self.service, "_run_flow_job", new_callable=AsyncMock):
            response = self.loop.run_until_complete(
                self.service.enqueue_erp_idea_jobs(ERPIdeaBatchRequest(task_id=self.PARENT))
            )
            self.loop.run_until_complete(asyncio.sleep(0))

        self.assertEqual(["TASK-NEW-0"], [item["task_id"] for item in response["queued"]])
        self.assertEqual([self.CHILD_A], [item["task_id"] for item in response["skipped"]])
        self.assertIn("chưa có ảnh nguồn", response["skipped"][0]["reason"])

    def test_the_intake_can_be_switched_off(self) -> None:
        details = self._board(["/private/files/tho-noel.jpg"], children=[self.CHILD_A])
        with patch.dict(os.environ, {"ERP_IDEA_INTAKE": "0"}):
            outcome, _details, created, _attached, _covers = self._intake(details)

        self.assertEqual([], outcome)
        self.assertEqual([], created)


if __name__ == "__main__":
    unittest.main()
