from __future__ import annotations

import asyncio
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, UploadFile

from flow_web.schemas import AppConfig, AuthStatus, CreateJobRequest, JobRecord, PromptCreateRequest, SkillRecord, StateSnapshot
from flow_web.service import FlowWebService
from flow_web.store import StateStore


class TempAppPathsMixin:
    def start_temp_paths(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.temp_root = Path(self._tempdir.name)
        self.data_dir = self.temp_root / "data"
        self.uploads_dir = self.data_dir / "uploads"
        self.downloads_dir = self.data_dir / "downloads"
        self.state_file = self.data_dir / "state.json"

        def ensure_temp_dirs() -> None:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.uploads_dir.mkdir(parents=True, exist_ok=True)
            self.downloads_dir.mkdir(parents=True, exist_ok=True)

        self._patches = [
            patch("flow_web.paths.DATA_DIR", self.data_dir),
            patch("flow_web.paths.STATE_FILE", self.state_file),
            patch("flow_web.paths.UPLOADS_DIR", self.uploads_dir),
            patch("flow_web.paths.DOWNLOADS_DIR", self.downloads_dir),
            patch("flow_web.store.STATE_FILE", self.state_file),
            patch("flow_web.store.ensure_app_dirs", ensure_temp_dirs),
            patch("flow_web.service.UPLOADS_DIR", self.uploads_dir),
            patch("flow_web.service.DOWNLOADS_DIR", self.downloads_dir),
            patch("flow_web.service.ensure_app_dirs", ensure_temp_dirs),
        ]
        for patcher in self._patches:
            patcher.start()
        ensure_temp_dirs()
        self.addCleanup(self.stop_temp_paths)

    def stop_temp_paths(self) -> None:
        for patcher in reversed(getattr(self, "_patches", [])):
            patcher.stop()
        if hasattr(self, "_tempdir"):
            self._tempdir.cleanup()


class FlowWebServiceSyncTests(TempAppPathsMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.start_temp_paths()
        self.store = StateStore()
        self.service = FlowWebService(self.store)

    def test_save_upload_deduplicates_file_name(self) -> None:
        first = UploadFile(filename="demo.jpg", file=io.BytesIO(b"first"))
        second = UploadFile(filename="demo.jpg", file=io.BytesIO(b"second"))

        first_payload = asyncio.run(self.service.save_upload(first))
        second_payload = asyncio.run(self.service.save_upload(second))

        self.assertEqual("demo.jpg", first_payload["file_name"])
        self.assertEqual("demo-1.jpg", second_payload["file_name"])
        self.assertTrue((self.uploads_dir / "demo.jpg").exists())
        self.assertTrue((self.uploads_dir / "demo-1.jpg").exists())

    def test_validate_job_request_requires_authentication(self) -> None:
        request = CreateJobRequest(type="video", prompt="test prompt")
        with patch.object(self.service, "get_auth_status", return_value=AuthStatus(authenticated=False)):
            with self.assertRaises(HTTPException) as ctx:
                self.service._validate_job_request(request)

        self.assertEqual(400, ctx.exception.status_code)
        self.assertIn("đăng nhập", str(ctx.exception.detail).lower())

    def test_resolve_job_request_applies_config_defaults(self) -> None:
        config = AppConfig(
            project_id="pid",
            active_workflow_id="wf-default",
            generation_timeout_s=420,
        )
        request = CreateJobRequest(type="video", prompt="run", timeout_s=0, workflow_id="")

        resolved = self.service._resolve_job_request(request, config)

        self.assertEqual(420, resolved.timeout_s)
        self.assertEqual("wf-default", resolved.workflow_id)
        self.assertEqual("landscape", resolved.aspect)

    def test_video_status_url_supports_nested_generated_video_payload(self) -> None:
        status = SimpleNamespace(
            fife_url="",
            download_url="",
            url="",
            media_name="media-1",
            _raw={
                "media": [
                    {
                        "video": {
                            "generatedVideo": {
                                "outputVideo": {
                                    "fifeUrl": "https://example.com/fallback.mp4",
                                }
                            }
                        }
                    }
                ]
            },
        )

        url = self.service._video_status_url(status, media_name="media-1")

        self.assertEqual("https://example.com/fallback.mp4", url)

    def test_default_title_marks_video_from_image(self) -> None:
        request = CreateJobRequest(
            type="video",
            prompt="samurai",
            start_image_path="/tmp/source.jpg",
        )

        title = self.service._default_title(request)

        self.assertEqual("Tạo video từ ảnh", title)

    def test_prompt_assistant_snapshot_reports_gemini_when_key_exists(self) -> None:
        skills = [
            SkillRecord(
                name="google veo",
                summary="Video prompting for Veo.",
                source_path="guides/video/google-veo/SKILL.md",
                is_builtin=True,
            ),
            SkillRecord(
                name="prompt engineering",
                summary="General prompt writing.",
                source_path="guides/prompting/prompt-engineering/SKILL.md",
                is_builtin=True,
            ),
        ]
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "gemini-2.5-flash"}, clear=False):
            snapshot = self.service._prompt_assistant_snapshot(skills)

        self.assertTrue(snapshot["configured"])
        self.assertEqual("gemini", snapshot["engine"])
        self.assertEqual("Gemini", snapshot["engine_label"])
        self.assertEqual("gemini-2.5-flash", snapshot["model"])

    def test_compose_prompt_draft_adds_dense_detail_for_video(self) -> None:
        request = PromptCreateRequest(
            mode="video",
            brief="hai samurai đối đầu giữa sân đền cổ",
            style="cinematic dramatic",
            must_include="bụi bay, vải áo chuyển động",
            audience="quảng cáo mạng xã hội",
            aspect="landscape",
        )

        prompt = self.service._compose_prompt_draft(request, [])

        self.assertIn("layered foreground midground and background depth", prompt)
        self.assertIn("consistent subject identity across the full clip", prompt)
        self.assertIn("must include bụi bay, vải áo chuyển động", prompt)
        self.assertIn("optimized for quảng cáo mạng xã hội", prompt)
        self.assertGreater(len(prompt), 250)

    def test_gemini_prompt_request_uses_neutral_wording_and_detail_instructions(self) -> None:
        request = PromptCreateRequest(mode="image", brief="ảnh tai nghe màu đen trên nền trắng", aspect="landscape")

        payload = self.service._gemini_prompt_request(request, [], "baseline prompt")
        prompt_text = payload["contents"][0]["parts"][0]["text"]

        self.assertNotIn("chủ nhân", prompt_text.lower())
        self.assertIn("cực kỳ chi tiết", prompt_text)
        self.assertIn("production-ready", prompt_text)
        self.assertIn("Viết cùng ngôn ngữ với brief gốc của người dùng.", prompt_text)

    def test_ensure_prompt_detail_expands_short_prompt_with_baseline(self) -> None:
        short_prompt = "Video quảng cáo cho đồng hồ."
        baseline = (
            "Cinematic product hero shot, đồng hồ cơ màu đen trên nền đá tối, visual style cinematic luxury premium, "
            "lighting is warm golden hour lighting, mood is premium refined mood, wide 16:9 framing, hero product framing "
            "with a slow dolly-in, controlled parallax, and crisp focus transitions, clear subject action and environment "
            "relationship, layered foreground midground and background depth, cohesive color palette with believable contrast, "
            "consistent subject identity across the full clip, high texture fidelity and realistic material response."
        )

        expanded, changed = self.service._ensure_prompt_detail(short_prompt, baseline, "video")

        self.assertTrue(changed)
        self.assertIn("layered foreground midground and background depth", expanded)
        self.assertGreater(len(expanded), len(short_prompt))


class StateStoreRegressionTests(TempAppPathsMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.start_temp_paths()

    def test_store_repairs_incomplete_jobs_after_restart(self) -> None:
        snapshot = StateSnapshot(
            config=AppConfig(project_id="pid"),
            jobs=[
                JobRecord(type="video", status="running", title="Dang chay"),
                JobRecord(type="image", status="polling", title="Dang doi"),
                JobRecord(type="video", status="completed", title="Xong"),
            ],
        )
        self.state_file.write_text(json.dumps(snapshot.model_dump(mode="json"), indent=2), encoding="utf-8")

        store = StateStore()
        jobs = store.snapshot().jobs

        self.assertEqual("interrupted", jobs[0].status)
        self.assertEqual("interrupted", jobs[1].status)
        self.assertEqual("completed", jobs[2].status)
        self.assertIn("khởi động lại", jobs[0].error.lower())


class FlowWebServiceAsyncTests(TempAppPathsMixin, unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.start_temp_paths()
        self.store = StateStore()
        self.service = FlowWebService(self.store)

    async def test_run_flow_job_saves_video_artifact_from_nested_status_url(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = CreateJobRequest(type="video", prompt="samurai fight", count=1)
        job = JobRecord(
            type="video",
            status="queued",
            title=self.service._default_title(request),
            input=request.model_dump(mode="json"),
        )
        await self.store.add_job(job)

        video_job = SimpleNamespace(media_name="media-123", workflow_id="wf-123")
        status = SimpleNamespace(
            fife_url="",
            download_url="",
            url="",
            media_name="media-123",
            _raw={
                "media": [
                    {
                        "video": {
                            "generatedVideo": {
                                "outputVideo": {
                                    "fifeUrl": "https://example.com/video.mp4",
                                }
                            }
                        }
                    }
                ]
            },
        )
        fake_client = SimpleNamespace(generate_video=AsyncMock(return_value=[video_job]))

        async def fake_with_client(fn, workflow_id="", timeout_s=0):
            return await fn(fake_client)

        with patch.object(self.service, "_with_client", side_effect=fake_with_client), patch.object(
            self.service,
            "_wait_for_video_with_progress",
            AsyncMock(return_value=status),
        ):
            await self.service._run_flow_job(job.id, request)

        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertEqual("completed", saved.status)
        self.assertEqual(1, len(saved.artifacts))
        self.assertEqual("https://example.com/video.mp4", saved.artifacts[0].url)
        self.assertEqual("video/mp4", saved.artifacts[0].mime_type)

    async def test_run_flow_job_marks_send_stage_timeout_clearly(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = CreateJobRequest(type="video", prompt="samurai fight", count=1, start_image_path="/tmp/demo.jpg")
        job = JobRecord(
            type="video",
            status="queued",
            title=self.service._default_title(request),
            input=request.model_dump(mode="json"),
        )
        await self.store.add_job(job)

        async def fake_generate_video(*args, **kwargs):
            await asyncio.sleep(0)
            return []

        fake_client = SimpleNamespace(generate_video=fake_generate_video)

        async def fake_with_client(fn, workflow_id="", timeout_s=0):
            return await fn(fake_client)

        async def fake_wait_for(awaitable, timeout=None):
            close = getattr(awaitable, "close", None)
            if callable(close):
                close()
            raise asyncio.TimeoutError

        with patch.object(self.service, "_with_client", side_effect=fake_with_client), patch(
            "flow_web.service.asyncio.wait_for",
            AsyncMock(side_effect=fake_wait_for),
        ):
            await self.service._run_flow_job(job.id, request)

        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertEqual("failed", saved.status)
        self.assertIn("chưa gửi được yêu cầu tạo video", saved.error.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
