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
        self.assertEqual("Veo 3.1 - Fast", resolved.model)
        self.assertEqual("landscape", resolved.aspect)

    def test_resolve_job_request_normalizes_image_model(self) -> None:
        config = AppConfig(project_id="pid", generation_timeout_s=420)
        request = CreateJobRequest(type="image", prompt="run", model="Nano Banana 2")

        resolved = self.service._resolve_job_request(request, config)

        self.assertEqual("NARWHAL", resolved.model)

    def test_canonical_project_url_uses_vi_locale_route(self) -> None:
        self.assertEqual(
            "https://labs.google/fx/vi/tools/flow/project/f2d33dc4-39f7-4f0e-8249-ce97a5c9a403",
            self.service._project_url("f2d33dc4-39f7-4f0e-8249-ce97a5c9a403"),
        )

    def test_detects_placeholder_project_route(self) -> None:
        self.assertTrue(
            self.service._looks_like_placeholder_project_url(
                "https://labs.google/fx/vi/tools/flow/project/[projectId]"
            )
        )
        self.assertTrue(
            self.service._looks_like_placeholder_project_url(
                "https://labs.google/fx/tools/flow/project/%5BprojectId%5D/edit/demo"
            )
        )
        self.assertFalse(
            self.service._looks_like_placeholder_project_url(
                "https://labs.google/fx/tools/flow/project/f2d33dc4-39f7-4f0e-8249-ce97a5c9a403"
            )
        )

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

    def test_default_title_marks_image_with_references_as_edit(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="ghép logo lên áo",
            reference_image_paths=["/tmp/model.jpg", "/tmp/logo.png"],
        )

        title = self.service._default_title(request)

        self.assertEqual("Chỉnh ảnh từ ảnh tham chiếu", title)

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

    def test_logout_flow_clears_local_profile_session(self) -> None:
        profile_dir = self.temp_root / "flow-profile"
        cookies_path = profile_dir / "Default" / "Cookies"
        cookies_path.parent.mkdir(parents=True, exist_ok=True)
        cookies_path.write_bytes(b"cookie-data")

        with patch("flow._storage.PROFILE_DIR", profile_dir), patch("flow._storage.ensure_dirs") as ensure_dirs:
            result = asyncio.run(self.service.logout_flow())

        self.assertTrue(result["ok"])
        self.assertTrue(result["had_session"])
        self.assertFalse(result["auth"]["authenticated"])
        self.assertFalse(cookies_path.exists())
        ensure_dirs.assert_called_once()

    def test_logout_flow_blocks_when_jobs_are_running(self) -> None:
        asyncio.run(self.store.add_job(JobRecord(type="video", status="running", title="Đang chạy")))

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(self.service.logout_flow())

        self.assertEqual(409, ctx.exception.status_code)
        self.assertIn("đang có tác vụ chạy", str(ctx.exception.detail).lower())


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

    async def test_with_client_keeps_shared_flow_browser_open_in_visible_mode(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", headless=False, generation_timeout_s=300))
        fake_browser = SimpleNamespace()
        fake_client = SimpleNamespace(name="shared-client")

        with patch.object(
            self.service,
            "_ensure_shared_browser",
            AsyncMock(return_value=fake_browser),
        ) as ensure_shared_browser, patch.object(
            self.service,
            "_build_client_from_shared_browser",
            AsyncMock(return_value=fake_client),
        ) as build_client, patch.object(
            self.service,
            "_close_shared_browser",
            AsyncMock(),
        ) as close_shared_browser:
            result = await self.service._with_client(lambda client: asyncio.sleep(0, result=client.name))

        self.assertEqual("shared-client", result)
        ensure_shared_browser.assert_awaited_once()
        build_client.assert_awaited_once()
        close_shared_browser.assert_not_called()

    async def test_open_login_flow_page_opens_new_tab_and_brings_it_to_front(self) -> None:
        page = SimpleNamespace(
            bring_to_front=AsyncMock(),
            goto=AsyncMock(),
            evaluate=AsyncMock(return_value=True),
        )
        context = SimpleNamespace(new_page=AsyncMock(return_value=page))
        browser = SimpleNamespace(context=context, _page=None, page=AsyncMock(return_value=page))

        with patch.object(
            self.service,
            "_foreground_native_flow_window",
            AsyncMock(),
        ) as foreground_native_window:
            result = await self.service._open_login_flow_page(browser)

        self.assertIs(result, page)
        context.new_page.assert_awaited_once()
        page.bring_to_front.assert_awaited()
        page.goto.assert_awaited()
        self.assertEqual(
            "https://labs.google/fx/vi/tools/flow",
            page.goto.await_args.args[0],
        )
        page.evaluate.assert_awaited()
        foreground_native_window.assert_awaited_once()

    async def test_enqueue_login_fails_immediately_when_browser_cannot_open(self) -> None:
        with patch.object(
            self.service,
            "_launch_login_browser",
            AsyncMock(side_effect=RuntimeError("Khong mo duoc cua so Chromium")),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await self.service.enqueue_login()

        self.assertEqual(500, ctx.exception.status_code)
        self.assertIn("khong mo duoc cua so chromium", str(ctx.exception.detail).lower())
        jobs = self.store.snapshot().jobs
        self.assertEqual(1, len(jobs))
        self.assertEqual("failed", jobs[0].status)

    async def test_ensure_valid_flow_project_page_redirects_placeholder_route(self) -> None:
        page = SimpleNamespace(
            url="https://labs.google/fx/vi/tools/flow/project/[projectId]",
            goto=AsyncMock(),
        )

        await self.service._ensure_valid_flow_project_page(
            page,
            "https://labs.google/fx/tools/flow/project/f2d33dc4-39f7-4f0e-8249-ce97a5c9a403",
        )

        page.goto.assert_awaited()
        args = page.goto.await_args.args
        self.assertEqual(
            "https://labs.google/fx/tools/flow/project/f2d33dc4-39f7-4f0e-8249-ce97a5c9a403",
            args[0],
        )

    async def test_repair_placeholder_flow_tabs_redirects_all_stale_tabs(self) -> None:
        stale_page = SimpleNamespace(
            url="https://labs.google/fx/vi/tools/flow/project/[projectId]",
            goto=AsyncMock(),
        )
        good_page = SimpleNamespace(
            url="https://labs.google/fx/tools/flow/project/f2d33dc4-39f7-4f0e-8249-ce97a5c9a403",
            goto=AsyncMock(),
        )
        browser = SimpleNamespace(
            context=SimpleNamespace(
                pages=[stale_page, good_page],
            )
        )

        await self.service._repair_placeholder_flow_tabs(
            browser,
            "https://labs.google/fx/tools/flow/project/f2d33dc4-39f7-4f0e-8249-ce97a5c9a403",
        )

        stale_page.goto.assert_awaited()
        good_page.goto.assert_not_awaited()

    async def test_close_placeholder_flow_tabs_closes_stale_tabs_and_keeps_valid_page(self) -> None:
        stale_page = SimpleNamespace(
            url="https://labs.google/fx/vi/tools/flow/project/[projectId]",
            close=AsyncMock(),
        )
        good_page = SimpleNamespace(
            url="https://labs.google/fx/tools/flow/project/f2d33dc4-39f7-4f0e-8249-ce97a5c9a403",
            close=AsyncMock(),
        )
        browser = SimpleNamespace(
            context=SimpleNamespace(
                pages=[stale_page, good_page],
            ),
            _page=None,
        )

        await self.service._close_placeholder_flow_tabs(
            browser,
            "https://labs.google/fx/tools/flow/project/f2d33dc4-39f7-4f0e-8249-ce97a5c9a403",
        )

        stale_page.close.assert_awaited_once()
        good_page.close.assert_not_awaited()

    async def test_close_placeholder_flow_tabs_opens_fresh_page_when_only_stale_tab_exists(self) -> None:
        stale_page = SimpleNamespace(
            url="https://labs.google/fx/vi/tools/flow/project/[projectId]",
            close=AsyncMock(),
        )
        fresh_page = SimpleNamespace(
            url="about:blank",
            goto=AsyncMock(),
        )
        context = SimpleNamespace(
            pages=[stale_page],
            new_page=AsyncMock(return_value=fresh_page),
        )
        browser = SimpleNamespace(
            context=context,
            _page=None,
        )

        async def pages_after_close() -> list[object]:
            return [fresh_page]

        stale_page.close.side_effect = lambda: context.pages.clear()

        await self.service._close_placeholder_flow_tabs(
            browser,
            "https://labs.google/fx/tools/flow/project/f2d33dc4-39f7-4f0e-8249-ce97a5c9a403",
        )

        stale_page.close.assert_awaited_once()
        context.new_page.assert_awaited_once()
        fresh_page.goto.assert_awaited()

    async def test_acquire_fresh_flow_page_prefers_matching_project_tab(self) -> None:
        matching_page = SimpleNamespace(
            url="https://labs.google/fx/tools/flow/project/f2d33dc4-39f7-4f0e-8249-ce97a5c9a403",
        )
        other_page = SimpleNamespace(
            url="https://labs.google/fx/tools/flow",
        )
        context = SimpleNamespace(
            pages=[other_page, matching_page],
            new_page=AsyncMock(),
        )
        browser = SimpleNamespace(context=context, _page=None)

        page = await self.service._acquire_fresh_flow_page(
            browser,
            "https://labs.google/fx/tools/flow/project/f2d33dc4-39f7-4f0e-8249-ce97a5c9a403",
        )

        self.assertIs(page, matching_page)
        context.new_page.assert_not_awaited()

    async def test_acquire_fresh_flow_page_creates_new_tab_when_no_matching_tab_exists(self) -> None:
        old_page = SimpleNamespace(url="https://labs.google/fx/tools/flow")
        fresh_page = SimpleNamespace(url="about:blank")
        context = SimpleNamespace(
            pages=[old_page],
            new_page=AsyncMock(return_value=fresh_page),
        )
        browser = SimpleNamespace(context=context, _page=None, page=AsyncMock(return_value=old_page))

        page = await self.service._acquire_fresh_flow_page(
            browser,
            "https://labs.google/fx/tools/flow/project/f2d33dc4-39f7-4f0e-8249-ce97a5c9a403",
        )

        self.assertIs(page, fresh_page)
        context.new_page.assert_awaited_once()

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

        fake_client.generate_video.assert_awaited_once()
        self.assertEqual("Veo 3.1 - Fast", fake_client.generate_video.await_args.kwargs["model"])
        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertEqual("completed", saved.status)
        self.assertEqual(1, len(saved.artifacts))
        self.assertEqual("https://example.com/video.mp4", saved.artifacts[0].url)
        self.assertEqual("video/mp4", saved.artifacts[0].mime_type)

    async def test_run_flow_job_fails_when_video_submit_returns_too_few_jobs(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = CreateJobRequest(type="video", prompt="cat", count=2)
        job = JobRecord(
            type="video",
            status="queued",
            title=self.service._default_title(request),
            input=request.model_dump(mode="json"),
        )
        await self.store.add_job(job)

        only_one_job = SimpleNamespace(media_name="media-123", workflow_id="wf-123")
        fake_client = SimpleNamespace(generate_video=AsyncMock(return_value=[only_one_job]))

        async def fake_with_client(fn, workflow_id="", timeout_s=0):
            return await fn(fake_client)

        with patch.object(self.service, "_with_client", side_effect=fake_with_client):
            await self.service._run_flow_job(job.id, request)

        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertEqual("failed", saved.status)
        self.assertIn("1/2 clip", saved.error)

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

    async def test_run_flow_job_uploads_reference_images_for_image_edit(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        reference_a = self.uploads_dir / "model.jpg"
        reference_b = self.uploads_dir / "logo.png"
        reference_a.write_bytes(b"model")
        reference_b.write_bytes(b"logo")

        request = CreateJobRequest(
            type="image",
            prompt="ghép logo này lên áo của người mẫu",
            count=1,
            reference_image_paths=[str(reference_a), str(reference_b)],
        )
        job = JobRecord(
            type="image",
            status="queued",
            title=self.service._default_title(request),
            input=request.model_dump(mode="json"),
        )
        await self.store.add_job(job)

        fake_image = SimpleNamespace(
            media_name="img-123",
            workflow_id="wf-123",
            fife_url="https://example.com/result.jpg",
            prompt=request.prompt,
            dimensions={"width": 1280, "height": 720},
        )
        captured_body = {}

        async def fake_fetch(method: str, url: str, body: dict):
            captured_body["method"] = method
            captured_body["url"] = url
            captured_body["body"] = body
            return {
                "media": [
                    {
                        "name": fake_image.media_name,
                        "workflowId": fake_image.workflow_id,
                        "image": {"generatedImage": {"fifeUrl": fake_image.fife_url}},
                    }
                ]
            }

        fake_client = SimpleNamespace(
            _api=SimpleNamespace(
                project_id="pid",
                _client_context=AsyncMock(
                    return_value={
                        "projectId": "pid",
                        "tool": "PINHOLE",
                        "sessionId": ";123",
                        "recaptchaContext": {"token": "abc", "applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB"},
                    }
                ),
                get_project_data=AsyncMock(
                    return_value={
                        "projectContents": {
                            "workflows": [
                                {"name": "wf-base", "metadata": {"primaryMediaId": "ref-model"}},
                                {"name": "wf-ref", "metadata": {"primaryMediaId": "ref-logo"}},
                            ]
                        }
                    }
                ),
                _fetch=AsyncMock(side_effect=fake_fetch),
                generate_image=AsyncMock(side_effect=AssertionError("Legacy reference_images payload should not be used")),
            ),
            generate_image=AsyncMock(return_value=[fake_image]),
        )

        async def fake_with_client(fn, workflow_id="", timeout_s=0):
            return await fn(fake_client)

        with patch.object(self.service, "_with_client", side_effect=fake_with_client), patch.object(
            self.service,
            "_upload_project_image_robust",
            AsyncMock(side_effect=["ref-model", "ref-logo"]),
        ) as upload_project_image:
            await self.service._run_flow_job(job.id, request)

        upload_project_image.assert_any_await(fake_client, str(reference_a.resolve()))
        upload_project_image.assert_any_await(fake_client, str(reference_b.resolve()))
        fake_client._api._fetch.assert_awaited_once()
        self.assertEqual("POST", captured_body["method"])
        self.assertEqual("projects/pid/flowMedia:batchGenerateImages", captured_body["url"])
        request_body = captured_body["body"]["requests"][0]
        self.assertEqual("wf-base", request_body["clientContext"]["workflowId"])
        self.assertEqual(
            [
                {"imageInputType": "IMAGE_INPUT_TYPE_BASE_IMAGE", "name": "ref-model"},
                {"imageInputType": "IMAGE_INPUT_TYPE_REFERENCE", "name": "ref-logo"},
            ],
            request_body["imageInputs"],
        )

        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertEqual("completed", saved.status)
        self.assertEqual(1, len(saved.artifacts))
        self.assertEqual("https://example.com/result.jpg", saved.artifacts[0].url)

    async def test_generate_image_edit_result_uses_first_image_as_base_and_rest_as_reference(self) -> None:
        captured_body = {}

        async def fake_fetch(method: str, url: str, body: dict):
            captured_body["method"] = method
            captured_body["url"] = url
            captured_body["body"] = body
            return {
                "media": [
                    {
                        "name": "img-1",
                        "workflowId": "wf-base",
                        "image": {"generatedImage": {"fifeUrl": "https://example.com/edited.jpg"}},
                    },
                    {
                        "name": "img-2",
                        "workflowId": "wf-base",
                        "image": {"generatedImage": {"fifeUrl": "https://example.com/edited-2.jpg"}},
                    },
                ]
            }

        fake_client = SimpleNamespace(
            _api=SimpleNamespace(
                project_id="pid",
                _client_context=AsyncMock(
                    return_value={
                        "projectId": "pid",
                        "tool": "PINHOLE",
                        "sessionId": ";123",
                        "recaptchaContext": {"token": "abc", "applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB"},
                    }
                ),
                _fetch=AsyncMock(side_effect=fake_fetch),
                get_project_data=AsyncMock(
                    return_value={
                        "projectContents": {
                            "workflows": [
                                {"name": "wf-base", "metadata": {"primaryMediaId": "base-media"}},
                                {"name": "wf-ref", "metadata": {"primaryMediaId": "logo-media"}},
                            ]
                        }
                    }
                ),
            )
        )

        images = await self.service._generate_image_edit_result(
            fake_client,
            "ghép logo lên áo",
            model="IMAGEN_3",
            aspect="portrait",
            count=2,
            reference_media_names=["base-media", "logo-media"],
        )

        self.assertEqual(2, len(images))
        self.assertEqual("POST", captured_body["method"])
        self.assertEqual("projects/pid/flowMedia:batchGenerateImages", captured_body["url"])
        self.assertEqual(2, len(captured_body["body"]["requests"]))
        for request_payload in captured_body["body"]["requests"]:
            self.assertEqual("IMAGEN_3", request_payload["imageModelName"])
            self.assertEqual("IMAGE_ASPECT_RATIO_PORTRAIT", request_payload["imageAspectRatio"])
            self.assertEqual("wf-base", request_payload["clientContext"]["workflowId"])
            self.assertEqual(
                [
                    {"imageInputType": "IMAGE_INPUT_TYPE_BASE_IMAGE", "name": "base-media"},
                    {"imageInputType": "IMAGE_INPUT_TYPE_REFERENCE", "name": "logo-media"},
                ],
                request_payload["imageInputs"],
            )

    async def test_run_flow_job_uses_direct_image_api_for_exact_count(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = CreateJobRequest(type="image", prompt="meo de thuong", count=2, aspect="square", model="IMAGEN_3")
        job = JobRecord(
            type="image",
            status="queued",
            title=self.service._default_title(request),
            input=request.model_dump(mode="json"),
        )
        await self.store.add_job(job)

        fake_images = [
            SimpleNamespace(
                media_name="img-1",
                workflow_id="wf-1",
                fife_url="https://example.com/img-1.jpg",
                prompt=request.prompt,
                dimensions={"width": 1024, "height": 1024},
            ),
            SimpleNamespace(
                media_name="img-2",
                workflow_id="wf-1",
                fife_url="https://example.com/img-2.jpg",
                prompt=request.prompt,
                dimensions={"width": 1024, "height": 1024},
            ),
        ]
        fake_client = SimpleNamespace(
            _api=SimpleNamespace(generate_image=AsyncMock(return_value=fake_images)),
            generate_image=AsyncMock(side_effect=AssertionError("UI image generation should not be used")),
        )

        async def fake_with_client(fn, workflow_id="", timeout_s=0):
            return await fn(fake_client)

        with patch.object(self.service, "_with_client", side_effect=fake_with_client):
            await self.service._run_flow_job(job.id, request)

        fake_client._api.generate_image.assert_awaited_once()
        kwargs = fake_client._api.generate_image.await_args.kwargs
        self.assertEqual(2, kwargs["count"])
        self.assertEqual("IMAGEN_3", kwargs["model"])
        self.assertEqual("IMAGE_ASPECT_RATIO_SQUARE", kwargs["aspect_ratio"])

        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertEqual("completed", saved.status)
        self.assertEqual(2, len(saved.artifacts))

    async def test_generate_images_with_retry_reloads_project_after_recaptcha_error(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = CreateJobRequest(type="image", prompt="meo de thuong", count=1, aspect="square")
        job = JobRecord(
            type="image",
            status="queued",
            title=self.service._default_title(request),
            input=request.model_dump(mode="json"),
        )
        await self.store.add_job(job)

        fake_image = SimpleNamespace(
            media_name="img-1",
            workflow_id="wf-1",
            fife_url="https://example.com/img-1.jpg",
            prompt=request.prompt,
            dimensions={"width": 1024, "height": 1024},
        )
        fake_client = SimpleNamespace()

        with patch.object(
            self.service,
            "_generate_images_once",
            AsyncMock(side_effect=RuntimeError("HTTP 403 on batchGenerateImages: reCAPTCHA evaluation failed")),
        ) as generate_once, patch.object(
            self.service,
            "_reload_flow_project_page",
            AsyncMock(),
        ) as reload_project:
            with patch.object(
                self.service,
                "_generate_images_via_ui",
                AsyncMock(return_value=[fake_image]),
            ) as generate_via_ui:
                result = await self.service._generate_images_with_retry(fake_client, job.id, request, [])

        self.assertEqual([fake_image], result)
        self.assertEqual(1, generate_once.await_count)
        reload_project.assert_awaited_once_with(fake_client)
        generate_via_ui.assert_awaited_once_with(fake_client, request, [])

    async def test_generate_images_via_ui_uses_single_reference_fallback(self) -> None:
        request = CreateJobRequest(type="image", prompt="them kinh", count=1, aspect="portrait")
        fake_image = SimpleNamespace(media_name="img-1")
        fake_client = SimpleNamespace()

        with patch.object(
            self.service,
            "_generate_single_reference_image_via_ui",
            AsyncMock(return_value=[fake_image]),
        ) as single_ref:
            result = await self.service._generate_images_via_ui(fake_client, request, ["base-media"])

        self.assertEqual([fake_image], result)
        single_ref.assert_awaited_once()

    async def test_resolve_image_reference_media_uses_robust_upload_helper(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        reference_a = self.uploads_dir / "model.jpg"
        reference_b = self.uploads_dir / "logo.png"
        reference_a.write_bytes(b"model")
        reference_b.write_bytes(b"logo")
        job = JobRecord(type="image", status="queued", title="test")
        await self.store.add_job(job)

        request = CreateJobRequest(
            type="image",
            prompt="ghép logo này lên áo của người mẫu",
            count=1,
            reference_image_paths=[str(reference_a), str(reference_b)],
        )
        fake_client = SimpleNamespace()

        with patch.object(
            self.service,
            "_upload_project_image_robust",
            AsyncMock(side_effect=["ref-model", "ref-logo"]),
        ) as upload_project_image:
            result = await self.service._resolve_image_reference_media(fake_client, job.id, request)

        self.assertEqual(["ref-model", "ref-logo"], result)
        upload_project_image.assert_any_await(fake_client, str(reference_a.resolve()))
        upload_project_image.assert_any_await(fake_client, str(reference_b.resolve()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
