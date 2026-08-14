from __future__ import annotations

import asyncio
import io
import json
import tempfile
import unittest
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
from flow_web.service import FlowWebService
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

    def _details(self, *, child_a_has_flow_images: bool = False) -> dict:
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
                "description": "<p>Khăn tay đặt cạnh cây thông</p>",
                "comments": (
                    [{"content": "[FLOW_V2_ARTIFACT] https://erp.havigroup.llc/files/flow-1.png"}]
                    if child_a_has_flow_images
                    else []
                ),
            },
            self.CHILD_B: {"name": self.CHILD_B, "subject": "b", "description": "<p>Khăn tay trong hộp quà</p>"},
        }

    def _enqueue(self, request, *, child_a_has_flow_images: bool = False) -> dict:
        details = self._details(child_a_has_flow_images=child_a_has_flow_images)
        self.loop.run_until_complete(
            self.store.replace_erp_config(
                ERPConfig(api_key="test-key", api_secret="test-secret", project_id="PROJ-0013")
            )
        )
        with patch.object(self.service, "_erp_assert_task_in_project"), patch.object(
            self.service, "_erp_task_detail", side_effect=lambda _key, _token, task_id: details[task_id]
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


if __name__ == "__main__":
    unittest.main()
