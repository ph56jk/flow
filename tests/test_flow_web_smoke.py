from __future__ import annotations

import asyncio
import base64
import contextlib
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, UploadFile

from flow_web.messages import classify_job_error, humanize_flow_error
from flow_web.schemas import (
    AppConfig,
    AuthStatus,
    CreateJobRequest,
    FlowOperatorRequest,
    IntegrationConfigUpdateRequest,
    JobArtifact,
    JobRecord,
    PromptBatchRequest,
    PromptCreateRequest,
    ResetReadyTrelloRequest,
    SkillRecord,
    StateSnapshot,
    StoryboardPlanRequest,
    TrelloConfig,
    TrelloConfigUpdateRequest,
    UserAssistantRequest,
)
from flow_web.service import FlowAgentQuotaError, FlowBrowserProfile, FlowWebService, ImageUpscaleResult
from flow_web.shot_rules import PRODUCT_SHOT_RULES
from flow_web.store import StateStore


def _model_dump_for_test(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


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
            patch("flow_web.service.DATA_DIR", self.data_dir),
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
        self._batch_pause_env = patch.dict(
            os.environ,
            {
                "FLOW_AGENT_BATCH_PAUSE_MIN_S": "0",
                "FLOW_AGENT_BATCH_PAUSE_MAX_S": "0",
            },
            clear=False,
        )
        self._batch_pause_env.start()
        self.addCleanup(self._batch_pause_env.stop)
        # Keep the Gemini design-inventory step offline in tests; individual tests re-patch it on the instance.
        self._design_inventory_patch = patch.object(
            FlowWebService,
            "_gemini_describe_trello_source_design",
            return_value={"inventory": ""},
        )
        self._design_inventory_patch.start()
        self.addCleanup(self._design_inventory_patch.stop)
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

    def test_flow_profile_specs_support_multiple_chrome_profiles_from_env(self) -> None:
        first = self.temp_root / "flow-a"
        second = self.temp_root / "flow-b"
        with patch.dict(
            os.environ,
            {
                "FLOW_CHROME_PROFILE_DIRS": f"Main={first};Backup={second}",
                "FLOW_CHROME_PROFILE_PROJECTS": (
                    "Backup=https://labs.google/fx/vi/tools/flow/project/4671337a-b32d-468a-a47a-bac90541ca2e"
                ),
                "FLOW_CHROME_PROFILE_COUNT": "",
            },
            clear=False,
        ):
            specs = self.service._flow_profile_specs()

        self.assertEqual(["Main", "Backup"], [spec.label for spec in specs])
        self.assertEqual(first, specs[0].path)
        self.assertEqual(second, specs[1].path)
        self.assertEqual("", specs[0].project_id)
        self.assertEqual("4671337a-b32d-468a-a47a-bac90541ca2e", specs[1].project_id)

    def test_state_uses_active_flow_profile_project_from_env_when_config_is_empty(self) -> None:
        profile_dir = self.temp_root / "flow-acc2"
        project_id = "98b0631c-45ac-4ea1-b735-005c248965c8"
        with patch.dict(
            os.environ,
            {
                "FLOW_CHROME_PROFILE_DIRS": f"Acc2={profile_dir}",
                "FLOW_CHROME_PROFILE_PROJECTS": f"Acc2={project_id}",
                "FLOW_CHROME_PROFILE_COUNT": "",
            },
            clear=False,
        ):
            state = self.service.get_state()

        self.assertEqual(project_id, state["config"]["project_id"])
        self.assertEqual(f"https://labs.google/fx/vi/tools/flow/project/{project_id}", state["config"]["project_url"])
        self.assertEqual("Acc2", state["config"]["project_name"])

    def test_prompt_batch_child_request_syncs_trello_graph_scope_to_item(self) -> None:
        base = CreateJobRequest(
            type="image",
            prompt="",
            model="NARWHAL",
            trello_board_id="board123",
            trello_card_id="shirt-card",
            trello_list_id="shirt-list",
            trello_attachment_ids=["old-att"],
            automation_graph={
                "modules": [
                    {
                        "id": "trello-source",
                        "type": "trello_source",
                        "settings": {
                            "trelloBoard": "board123",
                            "trelloCard": "shirt-card",
                            "trelloList": "shirt-list",
                            "trelloAttachmentIds": ["old-att"],
                        },
                    },
                    {
                        "id": "flow",
                        "type": "flow",
                        "settings": {
                            "flowAgentEnabled": False,
                            "flowAgentAutoApprove": False,
                            "imageAspect": "landscape",
                            "imageCount": 1,
                        },
                    },
                    {
                        "id": "trello-log",
                        "type": "trello",
                        "settings": {
                            "trelloBoard": "board123",
                            "trelloCard": "shirt-card",
                            "trelloList": "shirt-list",
                            "trelloAttachmentIds": ["old-att"],
                        },
                    },
                ]
            },
        )
        child = self.service._prompt_batch_child_request(
            base,
            {
                "prompt": "new prompt",
                "flow_agent_instruction": True,
                "trello_card_id": "ready-card",
                "trello_list_id": "ready-list",
                "trello_attachment_ids": ["ready-att"],
            },
            0,
            1,
        )

        self.assertEqual("ready-card", child.trello_card_id)
        self.assertEqual("ready-list", child.trello_list_id)
        self.assertEqual(["ready-att"], child.trello_attachment_ids)
        self.assertEqual("ready-card", child.trello_source_card_id)
        self.assertEqual(["ready-att"], child.trello_source_attachment_ids)
        self.assertEqual("square", child.aspect)
        self.assertEqual(12, child.count)
        self.assertEqual("GEMINI_3_PRO_IMAGE", child.model)
        self.assertTrue(child.flow_agent_enabled)
        self.assertTrue(child.flow_agent_auto_approve)
        graph = child.automation_graph.model_dump(mode="json")
        trello_modules = [module for module in graph["modules"] if module["type"] in {"trello_source", "trello"}]
        for module in trello_modules:
            self.assertEqual("ready-list", module["settings"]["trelloList"])
            self.assertEqual("ready-card", module["settings"]["trelloCard"])
            self.assertEqual(["ready-att"], module["settings"]["trelloAttachmentIds"])
        flow_module = next(module for module in graph["modules"] if module["type"] == "flow")
        self.assertEqual("square", flow_module["settings"]["imageAspect"])
        self.assertEqual(12, flow_module["settings"]["imageCount"])
        self.assertEqual("GEMINI_3_PRO_IMAGE", flow_module["settings"]["imageModel"])
        self.assertTrue(flow_module["settings"]["flowAgentEnabled"])
        self.assertTrue(flow_module["settings"]["flowAgentAutoApprove"])

    def test_prompt_batch_child_request_uses_missing_flow_agent_count(self) -> None:
        base = CreateJobRequest(
            type="image",
            prompt="",
            count=4,
            automation_graph={
                "modules": [
                    {"id": "flow", "type": "flow", "settings": {"imageCount": 4}},
                ]
            },
        )

        child = self.service._prompt_batch_child_request(
            base,
            {
                "prompt": "finish missing outputs",
                "flow_agent_instruction": True,
                "flow_agent_image_count": 2,
                "trello_card_name": "partial card",
            },
            0,
            1,
        )

        self.assertEqual(2, child.count)
        self.assertIn("2 ảnh", child.title)
        graph = child.automation_graph.model_dump(mode="json")
        flow_module = next(module for module in graph["modules"] if module["type"] == "flow")
        self.assertEqual(2, flow_module["settings"]["imageCount"])

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

    def test_resolve_job_request_uses_nano_banana_pro_by_default(self) -> None:
        config = AppConfig(project_id="pid", generation_timeout_s=420)
        request = CreateJobRequest(type="image", prompt="run", model="")

        resolved = self.service._resolve_job_request(request, config)

        self.assertEqual("GEMINI_3_PRO_IMAGE", resolved.model)

    def test_resolve_job_request_normalizes_nano_banana_pro_model(self) -> None:
        config = AppConfig(project_id="pid", generation_timeout_s=420)
        request = CreateJobRequest(type="image", prompt="run", model="Nano Banana Pro")

        resolved = self.service._resolve_job_request(request, config)

        self.assertEqual("GEMINI_3_PRO_IMAGE", resolved.model)

    def test_flow_image_call_validation_requires_selected_source(self) -> None:
        good_call = SimpleNamespace(
            req={
                "requests": [
                    {
                        "clientContext": {"workflowId": "workflow-source"},
                        "imageInputs": [{"mediaName": "media-source"}],
                    }
                ]
            }
        )
        prompt_only_call = SimpleNamespace(req={"requests": [{"clientContext": {"workflowId": "fresh-workflow"}}]})
        attached_file_call = SimpleNamespace(req={"requests": [{"imageInputs": [{"name": "agent-uploaded-media"}]}]})

        self.assertTrue(self.service._flow_image_call_uses_selected_image(good_call, "media-source", "workflow-source"))
        self.assertFalse(self.service._flow_image_call_uses_selected_image(prompt_only_call, "media-source", "workflow-source"))
        self.assertTrue(
            self.service._flow_image_call_uses_selected_image(
                attached_file_call,
                "media-source",
                "workflow-source",
                allow_any_image_input=True,
            )
        )
        self.assertFalse(self.service._flow_image_call_uses_selected_image(attached_file_call, "media-source", "workflow-source"))

    def test_auto_trello_generic_title_does_not_filter_ready_cards(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4)
        cards = [
            {
                "id": "card-1",
                "shortLink": "short-1",
                "idList": "ready",
                "name": "baby pillowcase",
                "url": "https://trello.example/c/card-1",
                "_image_attachments": [{"id": "att-1", "name": "source.jpg", "mimeType": "image/jpeg"}],
            },
            {
                "id": "card-2",
                "shortLink": "short-2",
                "idList": "ready",
                "name": "embroidered apron",
                "url": "https://trello.example/c/card-2",
                "_image_attachments": [{"id": "att-2", "name": "source.png", "mimeType": "image/png"}],
            },
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(2, len(items))
        self.assertEqual("", self.service._trello_auto_search_query(request))
        self.assertEqual({"card-1", "card-2"}, {item["trello_card_id"] for item in items})

    def test_auto_trello_ready_for_ai_label_does_not_filter_ready_cards(self) -> None:
        request = CreateJobRequest(
            type="image",
            title="Auto AI Trello: chờ sản phẩm mới liên tục",
            prompt_product="phần ready for AI",
            prompt_product_key="phần ready for AI",
            prompt_notes="Trello search: phần ready for AI",
            count=4,
        )
        cards = [
            {
                "id": "card-apron",
                "shortLink": "apron",
                "idList": "ready",
                "name": "embroidered apron",
                "url": "https://trello.example/c/apron",
                "_image_attachments": [{"id": "att-apron", "name": "source.jpg", "mimeType": "image/jpeg"}],
            },
            {
                "id": "card-pillow",
                "shortLink": "pillow",
                "idList": "ready",
                "name": "baby pillowcase",
                "url": "https://trello.example/c/pillow",
                "_image_attachments": [{"id": "att-pillow", "name": "source.png", "mimeType": "image/png"}],
            },
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual("", self.service._trello_auto_search_query(request))
        self.assertEqual({"card-apron", "card-pillow"}, {item["trello_card_id"] for item in items})

    def test_auto_trello_card_description_guides_flow_agent_prompt(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4)
        cards = [
            {
                "id": "card-desc",
                "shortLink": "desc",
                "idList": "ready",
                "name": "Custom order",
                "desc": (
                    "AI NOTE: Personalized embroidered pillowcase named Emma. "
                    "Use a soft pastel nursery scene. Do not change the name Emma."
                ),
                "url": "https://trello.example/c/desc",
                "_image_attachments": [{"id": "att-desc", "name": "source.jpg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-desc"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        prompt = items[0]["prompt"]
        self.assertIn("Product-specific notes from the Trello card description", prompt)
        self.assertIn("Do not change the name Emma", prompt)
        self.assertIn("Treat the Trello description as user-supplied product guidance", prompt)
        self.assertIn("baby pillowcase or cushion shape", items[0]["design_analysis"])
        self.assertIn("Hands embroidering pillowcase", items[0]["shot_labels"])

    def _design_inventory_card(self, card_id: str = "card-inventory") -> dict[str, Any]:
        return {
            "id": card_id,
            "shortLink": card_id,
            "idList": "ready",
            "name": "advent_calendar",
            "desc": "",
            "url": f"https://trello.example/c/{card_id}",
            "_image_attachments": [{"id": "att-inv", "name": "calendar.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["att-inv"],
        }

    def _design_inventory_patches(self, describe_payload: dict[str, Any]) -> list[Any]:
        return [
            patch.object(self.service, "_gemini_api_key", return_value="gemini-key"),
            patch.object(self.service, "_trello_credentials", return_value=("trello-key", "trello-token")),
            patch.object(self.service, "_trello_download_attachment_bytes", return_value=(b"image-bytes", "image/jpeg")),
            patch.object(
                self.service,
                "_gemini_classify_trello_source_product_rule",
                return_value={
                    "product_rule_key": "advent_calendar",
                    "confidence": 0.95,
                    "visible_product": "linen advent calendar with dinosaur embroidery",
                    "reason": "pocket grid visible",
                },
            ),
            patch.object(self.service, "_trello_should_write_ai_title_description", return_value=False),
            patch.object(self.service, "_gemini_describe_trello_source_design", return_value=describe_payload),
        ]

    def test_design_inventory_locks_prompt_and_qa_checklist(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        card = self._design_inventory_card()
        describe_payload = {
            "inventory": (
                "Cream cotton wall advent calendar with 'Merry Rex-mas' lettering in green and red, a T-rex and a "
                "triceratops both wearing red Santa hats above 25 numbered pockets with dark teal numbers."
            ),
            "base_color": "cream",
            "text_elements": ["Merry Rex-mas"],
            "motifs": ["T-rex with red Santa hat", "triceratops with red Santa hat"],
            "must_not_change": ["two hatted dinosaurs", "cream fabric"],
        }
        patches = self._design_inventory_patches(describe_payload)
        with contextlib.ExitStack() as stack:
            mocks = [stack.enter_context(item) for item in patches]
            items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)
        describe = mocks[-1]

        describe.assert_called_once()
        self.assertEqual(1, len(items))
        self.assertIn("Merry Rex-mas", card["_design_inventory_text"])
        self.assertIn("Must not change: two hatted dinosaurs; cream fabric", card["_design_inventory_text"])
        self.assertIn("EXACT DESIGN INVENTORY of the source product", items[0]["design_analysis"])
        self.assertIn("Merry Rex-mas", items[0]["notes"])
        prompt = items[0]["prompt"]
        self.assertIn("Design replication lock", prompt)
        self.assertIn("never describe the product generically", prompt)
        self.assertIn("restates the exact design inventory", prompt)

        child = CreateJobRequest(
            type="image",
            title="child",
            prompt=prompt,
            prompt_notes=items[0]["notes"],
            prompt_product="advent_calendar",
        )
        self.assertIn("Merry Rex-mas", self.service._design_inventory_from_request(child))
        self.assertNotIn("Flow Agent will write the final prompts", self.service._design_inventory_from_request(child))
        qa_prompt = self.service._trello_source_qa_prompt(child)
        self.assertIn("exact replica of the source product", qa_prompt)
        self.assertIn("Design inventory of the source product", qa_prompt)
        self.assertIn("Merry Rex-mas", qa_prompt)
        self.assertIn("is a REJECT", qa_prompt)
        # Colorway lineup shots may carry different names per variant (matches the prompt's colorway rule).
        self.assertIn("multi-product lineup shot", qa_prompt)
        self.assertIn("is NOT a defect", qa_prompt)
        # Planned shot-list exceptions (colorways, craft/process shots) must not be rejected as design changes.
        self.assertIn("Planned exceptions that are part of the shot list", qa_prompt)
        self.assertIn("stitched in a hoop", qa_prompt)
        self.assertIn("different fabric base color is acceptable", qa_prompt)
        self.assertNotIn("Ornament pose rule", qa_prompt)

        ornament = CreateJobRequest(type="image", title="child", prompt="x", prompt_product="Ornament Round")
        ornament_prompt = self.service._trello_source_qa_prompt(ornament)
        self.assertIn("Ornament pose rule", ornament_prompt)
        self.assertIn("stands upright or balances on its edge", ornament_prompt)
        self.assertIn("hanging from its cord or loop, lying completely flat", ornament_prompt)
        self.assertIn("Never show the ornament standing upright", PRODUCT_SHOT_RULES["ornament_round"]["shots"][0][2])
        self.assertEqual(12, PRODUCT_SHOT_RULES["ornament_round"]["target_count"])
        self.assertEqual(12, PRODUCT_SHOT_RULES["pn_ornament"]["target_count"])

    def test_design_inventory_is_cached_per_source_attachment(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        describe_payload = {"inventory": "Cream linen calendar with two hatted dinosaurs."}
        patches = self._design_inventory_patches(describe_payload)
        with contextlib.ExitStack() as stack:
            mocks = [stack.enter_context(item) for item in patches]
            first_card = self._design_inventory_card()
            second_card = self._design_inventory_card()
            self.service._flow_operator_enrich_card_with_visual_product_rule(request, first_card)
            self.service._flow_operator_enrich_card_with_visual_product_rule(request, second_card)
        describe = mocks[-1]

        describe.assert_called_once()
        self.assertEqual(first_card["_design_inventory_text"], second_card["_design_inventory_text"])
        self.assertIn("two hatted dinosaurs", second_card["_design_inventory_text"])

    def test_design_inventory_failure_keeps_prompt_usable(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        card = self._design_inventory_card("card-inventory-fail")
        patches = self._design_inventory_patches({})
        patches[-1] = patch.object(
            self.service,
            "_gemini_describe_trello_source_design",
            side_effect=RuntimeError("Gemini API returned HTTP 503."),
        )
        with contextlib.ExitStack() as stack:
            for item in patches:
                stack.enter_context(item)
            items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)

        self.assertEqual(1, len(items))
        self.assertIn("HTTP 503", card["_design_inventory_error"])
        self.assertNotIn("EXACT DESIGN INVENTORY", items[0]["design_analysis"])
        self.assertIn("Design replication lock", items[0]["prompt"])
        self.assertEqual("", self.service._design_inventory_from_request(CreateJobRequest(type="image", prompt=items[0]["prompt"])))

    def test_gemini_thinking_budget_and_usage_tracking(self) -> None:
        with patch.dict(os.environ, {"GEMINI_QA_THINKING_BUDGET": "", "GEMINI_LIGHT_THINKING_BUDGET": ""}, clear=False):
            with patch.object(self.service, "_gemini_model", return_value="gemini-2.5-flash"):
                self.assertEqual({"thinkingConfig": {"thinkingBudget": 512}}, self.service._gemini_thinking_config("qa"))
                self.assertEqual({"thinkingConfig": {"thinkingBudget": 0}}, self.service._gemini_thinking_config("light"))
            with patch.object(self.service, "_gemini_model", return_value="gemini-2.5-pro"):
                self.assertEqual({"thinkingConfig": {"thinkingBudget": 128}}, self.service._gemini_thinking_config("light"))
            with patch.object(self.service, "_gemini_model", return_value="gemini-3.8-flash"):
                self.assertEqual({}, self.service._gemini_thinking_config("qa"))
        with patch.dict(os.environ, {"GEMINI_QA_THINKING_BUDGET": "-1"}, clear=False), patch.object(
            self.service, "_gemini_model", return_value="gemini-2.5-flash"
        ):
            self.assertEqual({}, self.service._gemini_thinking_config("qa"))

        payload = json.dumps({"generationConfig": {"temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}}}).encode("utf-8")
        stripped = json.loads(FlowWebService._strip_thinking_config(payload).decode("utf-8"))
        self.assertNotIn("thinkingConfig", stripped["generationConfig"])

        summary = self.service._record_gemini_usage(
            "gemini-2.5-flash",
            "kiểm tra ảnh trước khi upload Trello",
            {"promptTokenCount": 14000, "candidatesTokenCount": 300, "thoughtsTokenCount": 500},
        )
        self.assertEqual(800, summary["output_tokens"])
        self.assertAlmostEqual(14000 / 1e6 * 0.30 + 800 / 1e6 * 2.50, summary["estimated_usd"], places=5)
        self.service._record_gemini_usage("gemini-2.5-flash", "the source design inventory", {"promptTokenCount": 1000, "candidatesTokenCount": 700})
        usage = self.service.get_gemini_usage()
        today = usage["today_usage"]
        self.assertEqual(2, today["calls"])
        self.assertEqual(15000, today["prompt_tokens"])
        self.assertEqual(500, today["thinking_tokens"])
        self.assertIn("the source design inventory", today["by_context"])
        self.assertTrue((self.data_dir / FlowWebService.GEMINI_USAGE_FILE_NAME).is_file())

    def test_visual_rule_file_cache_survives_new_service_instance(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        describe_payload = {"inventory": "Cream linen calendar with two hatted dinosaurs."}
        patches = self._design_inventory_patches(describe_payload)
        with contextlib.ExitStack() as stack:
            mocks = [stack.enter_context(item) for item in patches]
            first_card = self._design_inventory_card("card-file-cache")
            self.service._flow_operator_enrich_card_with_visual_product_rule(request, first_card)
        self.assertEqual(1, mocks[-1].call_count)
        self.assertTrue((self.data_dir / FlowWebService.VISUAL_RULE_CACHE_FILE_NAME).is_file())

        fresh_service = FlowWebService(self.store)
        second_card = self._design_inventory_card("card-file-cache")
        with patch.object(fresh_service, "_gemini_api_key", return_value="gemini-key"), patch.object(
            fresh_service, "_trello_credentials", return_value=("trello-key", "trello-token")
        ), patch.object(fresh_service, "_trello_download_attachment_bytes") as download, patch.object(
            fresh_service, "_gemini_classify_trello_source_product_rule"
        ) as classify, patch.object(fresh_service, "_gemini_describe_trello_source_design") as describe, patch.object(
            fresh_service, "_trello_should_write_ai_title_description", return_value=False
        ):
            fresh_service._flow_operator_enrich_card_with_visual_product_rule(request, second_card)

        download.assert_not_called()
        classify.assert_not_called()
        describe.assert_not_called()
        self.assertEqual("advent_calendar", second_card["_visual_product_rule_key"])
        self.assertIn("two hatted dinosaurs", second_card["_design_inventory_text"])

    def test_file_chooser_guard_feeds_pending_source_and_installs_once(self) -> None:
        handlers: list[Any] = []

        class _FakePage:
            def on(self, event: str, handler: Any) -> None:
                handlers.append((event, handler))

        class _FakeChooser:
            def __init__(self) -> None:
                self.files: list[Any] = []

            async def set_files(self, files: Any) -> None:
                self.files.append(files)

        page = _FakePage()
        self.service._install_flow_page_file_chooser_guard(page)
        self.service._install_flow_page_file_chooser_guard(page)
        self.assertEqual(1, len(handlers))
        self.assertEqual("filechooser", handlers[0][0])

        source = self.uploads_dir / "guard-source.jpg"
        source.write_bytes(b"source")

        async def _run() -> tuple[_FakeChooser, _FakeChooser]:
            self.service._flow_agent_chooser_file = str(source)
            self.service._flow_agent_chooser_expecting = False
            pending = _FakeChooser()
            handlers[0][1](pending)
            await asyncio.sleep(0.05)
            self.service._flow_agent_chooser_file = ""
            idle = _FakeChooser()
            handlers[0][1](idle)
            await asyncio.sleep(0.05)
            return pending, idle

        pending, idle = asyncio.run(_run())
        self.assertEqual([str(source)], pending.files)
        self.assertEqual([[]], idle.files)
        self.assertEqual(1, self.service._flow_agent_chooser_handled)

    def test_mark_chrome_profile_clean_exit_clears_crash_flag(self) -> None:
        profile_dir = self.temp_root / "profile-clean-exit"
        preferences = profile_dir / "Default" / "Preferences"
        preferences.parent.mkdir(parents=True, exist_ok=True)
        preferences.write_text(json.dumps({"profile": {"exit_type": "Crashed", "exited_cleanly": False, "name": "x"}}), encoding="utf-8")

        self.assertTrue(self.service._mark_chrome_profile_clean_exit(profile_dir))
        saved = json.loads(preferences.read_text(encoding="utf-8"))
        self.assertEqual("Normal", saved["profile"]["exit_type"])
        self.assertTrue(saved["profile"]["exited_cleanly"])
        self.assertEqual("x", saved["profile"]["name"])
        self.assertFalse(self.service._mark_chrome_profile_clean_exit(profile_dir))
        self.assertFalse(self.service._mark_chrome_profile_clean_exit(self.temp_root / "missing-profile"))

    def test_auto_trello_design_qa_rejection_is_retried_not_stopped(self) -> None:
        detail = "Gemini chặn upload Trello vì ảnh generated không khớp ảnh nguồn/card nguồn (different dinosaur; ảnh lỗi: 2, 6)."
        self.assertTrue(self.service._auto_trello_is_design_qa_rejection(detail))
        self.assertFalse(self.service._auto_trello_should_stop_on_child_error(detail))
        self.assertFalse(self.service._auto_trello_is_design_qa_rejection("Đã xảy ra lỗi. Hãy thử lại."))
        self.assertEqual(2, FlowWebService.AUTO_TRELLO_DESIGN_QA_MAX_RETRIES)

    def test_trello_ai_title_description_block_preserves_existing_description(self) -> None:
        description = "Original buyer notes.\nKeep the flower motif exact."

        updated = self.service._trello_description_with_ai_title(
            description,
            title="Personalized Linen Drawstring Bag with Lavender Embroidery, Handmade Jewelry Pouch",
            product_type="Drawstring Bag",
            embroidery_design="Lavender Sprig",
            model="gemini-2.5-flash",
            updated_at="2026-06-08T10:00:00+00:00",
        )

        self.assertEqual(
            f"{description}\n\nPersonalized Linen Drawstring Bag with Lavender Embroidery, Handmade Jewelry Pouch",
            updated,
        )
        self.assertIn("Personalized Linen Drawstring Bag with Lavender Embroidery", updated)
        self.assertNotIn("AI Suggested Etsy Title:", updated)
        self.assertNotIn("AI Product Type:", updated)
        self.assertNotIn("AI Embroidery Design:", updated)
        self.assertNotIn("AI Title Status:", updated)
        self.assertNotIn("AI Title Source:", updated)
        self.assertNotIn("AI Title Updated:", updated)
        self.assertNotIn(self.service.TRELLO_AI_TITLE_BEGIN_MARKER, updated)
        self.assertNotIn(self.service.TRELLO_AI_TITLE_END_MARKER, updated)

    def test_trello_ai_title_update_writes_backup_before_description_put(self) -> None:
        card = {
            "id": "card-title",
            "name": "source product",
            "desc": "Original card description",
            "url": "https://trello.example/c/card-title",
        }

        with patch.object(self.service, "_trello_put_json", return_value={"desc": "updated desc"}) as put_json:
            result = self.service._write_trello_ai_title_to_description(
                key="key",
                token="token",
                card=card,
                title_payload={
                    "title": "Personalized Linen Drawstring Bag with Lavender Embroidery, Handmade Jewelry Pouch",
                    "product_type": "Drawstring Bag",
                    "embroidery_design": "Lavender Sprig",
                },
            )

        self.assertEqual("updated", result["status"])
        self.assertIn("Personalized Linen Drawstring Bag", result["title"])
        put_json.assert_called_once()
        self.assertEqual("updated desc", card["desc"])
        backup_path = Path(result["backup_path"])
        self.assertTrue(backup_path.is_file())
        payload = json.loads(backup_path.read_text(encoding="utf-8"))
        self.assertEqual(1, len(payload))
        self.assertEqual("card-title", payload[0]["card_id"])
        self.assertEqual("Lavender Sprig", payload[0]["embroidery_design"])
        self.assertEqual("Original card description", payload[0]["old_description"])
        self.assertEqual(
            "Original card description\n\nPersonalized Linen Drawstring Bag with Lavender Embroidery, Handmade Jewelry Pouch",
            payload[0]["new_description"],
        )
        self.assertNotIn("AI Suggested Etsy Title:", payload[0]["new_description"])
        self.assertNotIn("AI Product Type:", payload[0]["new_description"])
        self.assertNotIn(self.service.TRELLO_AI_TITLE_BEGIN_MARKER, payload[0]["new_description"])
        self.assertNotIn(self.service.TRELLO_AI_TITLE_END_MARKER, payload[0]["new_description"])

    def test_trello_ai_title_title_only_backup_prevents_duplicate_append(self) -> None:
        card = {
            "id": "card-title",
            "name": "source product",
            "desc": "Original card description\n\nPersonalized Linen Drawstring Bag with Lavender Embroidery, Handmade Jewelry Pouch",
            "url": "https://trello.example/c/card-title",
        }
        self.service._write_trello_ai_title_description_backup(
            card_id="card-title",
            card_name="source product",
            card_url="https://trello.example/c/card-title",
            old_description="Original card description",
            new_description=card["desc"],
            title="Personalized Linen Drawstring Bag with Lavender Embroidery, Handmade Jewelry Pouch",
            product_type="Drawstring Bag",
            embroidery_design="Lavender Sprig",
        )

        self.assertFalse(self.service._trello_should_write_ai_title_description(card))

    def test_ai_title_enforces_visible_embroidery_design_in_title(self) -> None:
        title = self.service._title_with_embroidery_design(
            "Personalized Linen Drawstring Bag, Handmade Jewelry Pouch",
            "Lavender Daisy Floral",
            "Drawstring Bag",
        )

        self.assertIn("Lavender Daisy Floral", title)
        self.assertIn("Drawstring Bag", title)

    def test_ai_title_fallback_uses_embroidery_design_from_context(self) -> None:
        payload = self.service._fallback_trello_product_title(
            card_name="lavender daisy drawstring bag",
            attachment_name="pale_sage_linen_lavender_daisy_drawstring_bag.jpeg",
            product_rule_key="drawstring_bag",
            visible_product="linen drawstring bag with lavender daisy embroidery",
        )

        self.assertEqual("Lavender Daisy Floral", payload["embroidery_design"])
        self.assertIn("Lavender Daisy Floral", payload["title"])
        self.assertIn("Drawstring Bag", payload["title"])

    def test_ai_title_fallback_ignores_personalized_name_as_design(self) -> None:
        payload = self.service._fallback_trello_product_title(
            card_name="Custom order for Emma",
            attachment_name="emma_personalized_name_linen_drawstring_bag.jpeg",
            product_rule_key="drawstring_bag",
            visible_product="linen drawstring bag with embroidered name Emma",
        )

        self.assertEqual("Decorative Embroidery", payload["embroidery_design"])
        self.assertNotIn("Emma", payload["title"])
        self.assertNotIn("Personalized Name", payload["title"])
        self.assertIn("Drawstring Bag", payload["title"])

    def test_ai_title_scrubs_gemini_personalized_name_design(self) -> None:
        title = self.service._title_without_personalized_text_design(
            "Emma Hand Embroidered Linen Drawstring Bag, Handmade Jewelry Pouch Gift",
            "Emma",
        )

        self.assertNotIn("Emma", title)
        self.assertIn("Hand Embroidered Linen Drawstring Bag", title)

    def test_auto_trello_ai_title_missing_gemini_records_error_on_item(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        card = {
            "id": "card-no-gemini-title",
            "shortLink": "no-gemini-title",
            "idList": "ready",
            "name": "embroidered drawstring pouch",
            "desc": "Buyer note: handmade linen bag.",
            "url": "https://trello.example/c/no-gemini-title",
            "_image_attachments": [{"id": "att-title", "name": "drawstring_bag.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["att-title"],
        }

        with patch.object(self.service, "_gemini_api_key", return_value=""):
            items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)

        self.assertEqual(1, len(items))
        self.assertIn("Gemini", card["_ai_title_error"])
        self.assertIn("Gemini", items[0]["ai_title_error"])
        self.assertEqual("", items[0]["ai_suggested_title"])
        self.assertIn("Drawstring Bag category", items[0]["design_analysis"])

    def test_auto_trello_enrichment_writes_ai_title_to_description(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        card = {
            "id": "card-ai-title",
            "shortLink": "ai-title",
            "idList": "ready",
            "name": "Sage_green_linen_drawstring_bag.jpeg",
            "desc": "Buyer note: keep lavender embroidery.",
            "url": "https://trello.example/c/ai-title",
            "_image_attachments": [{"id": "att-title", "name": "drawstring_bag.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["att-title"],
        }

        with patch.object(self.service, "_gemini_api_key", return_value="gemini-key"), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("trello-key", "trello-token"),
        ), patch.object(
            self.service,
            "_trello_download_attachment_bytes",
            return_value=(b"image-bytes", "image/jpeg"),
        ), patch.object(
            self.service,
            "_gemini_classify_trello_source_product_rule",
            return_value={
                "product_rule_key": "drawstring_bag",
                "confidence": 0.95,
                "visible_product": "embroidered linen drawstring bag",
                "reason": "visible pouch with cords",
            },
        ), patch.object(
            self.service,
            "_gemini_suggest_trello_product_title",
            return_value={
                "title": "Personalized Linen Drawstring Bag with Lavender Embroidery, Handmade Jewelry Pouch",
                "product_type": "Drawstring Bag",
                "reason": "source is an embroidered pouch",
            },
        ) as suggest_title, patch.object(
            self.service,
            "_trello_put_json",
            return_value={
                "desc": "Buyer note: keep lavender embroidery.\n\nPersonalized Linen Drawstring Bag with Lavender Embroidery, Handmade Jewelry Pouch"
            },
        ) as put_json:
            self.service._flow_operator_enrich_card_with_visual_product_rule(request, card)

        suggest_title.assert_called_once()
        put_json.assert_called_once()
        self.assertEqual("drawstring_bag", card["_visual_product_rule_key"])
        self.assertIn("Personalized Linen Drawstring Bag", card["_ai_suggested_title"])
        self.assertTrue(Path(card["_ai_title_backup_path"]).is_file())

    def test_auto_trello_ai_title_falls_back_when_gemini_returns_no_text(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        card = {
            "id": "card-ai-title-fallback",
            "shortLink": "ai-title-fallback",
            "idList": "ready",
            "name": "Hand-embroidered_drawstring_bag_pale_sage.jpeg",
            "desc": "",
            "url": "https://trello.example/c/ai-title-fallback",
            "_image_attachments": [{"id": "att-title", "name": "drawstring_bag_pale_sage.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["att-title"],
        }

        with patch.object(self.service, "_gemini_api_key", return_value="gemini-key"), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("trello-key", "trello-token"),
        ), patch.object(
            self.service,
            "_trello_download_attachment_bytes",
            return_value=(b"image-bytes", "image/jpeg"),
        ), patch.object(
            self.service,
            "_gemini_classify_trello_source_product_rule",
            return_value={
                "product_rule_key": "drawstring_bag",
                "confidence": 0.95,
                "visible_product": "embroidered linen drawstring bag",
                "reason": "visible pouch with cords",
            },
        ), patch.object(
            self.service,
            "_gemini_suggest_trello_product_title",
            side_effect=RuntimeError("Gemini không trả về nội dung AI product title."),
        ), patch.object(
            self.service,
            "_trello_put_json",
            return_value={"desc": "Hand Embroidered Linen Drawstring Bag, Handmade Jewelry Pouch Gift"},
        ) as put_json:
            self.service._flow_operator_enrich_card_with_visual_product_rule(request, card)

        put_json.assert_called_once()
        self.assertIn("Hand Embroidered", card["_ai_suggested_title"])
        self.assertIn("Drawstring Bag", card["_ai_suggested_title"])
        self.assertIn("_ai_title_fallback_reason", card)
        self.assertTrue(Path(card["_ai_title_backup_path"]).is_file())

    def test_auto_trello_pennant_card_keeps_banner_category(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4)
        cards = [
            {
                "id": "card-pennant",
                "shortLink": "pennant",
                "idList": "ready",
                "name": "Small_pennant-shaped_white_linen_nursery_202605260834.jpeg",
                "url": "https://trello.example/c/pennant",
                "_image_attachments": [{"id": "att-pennant", "name": "small_pennant_bear_noah.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-pennant"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertIn("Banner category", item["design_analysis"])
        self.assertIn("Pennant/banner category lock", item["prompt"])
        self.assertIn("top dowel or rod", item["prompt"])
        self.assertIn("clearly visible wall hook", item["prompt"])
        self.assertIn("rope/cord visibly hanging", item["prompt"])
        self.assertIn("Never create a pillow/cushion/blanket/shirt/hoop version", item["prompt"])
        self.assertIn("image 7 is the only allowed four-panel close-up collage", item["prompt"])
        self.assertIn("woman sitting at a clean craft table", item["prompt"])
        self.assertIn("mother and baby together", item["prompt"])
        self.assertIn("flat and neatly folded", item["prompt"])
        self.assertNotIn("Nursery hero arrangement", item["shot_labels"])
        self.assertEqual(
            [
                "Banner image 1 Mẹ và bé chạm vào cờ thêu tên",
                "Banner image 2 Hero cờ treo trong nursery",
                "Banner image 3 2 cờ cùng kiểu, khác tên, khác màu nền",
                "Banner image 4 2 cờ đặt trên bàn với đồ em bé",
                "Banner image 5 3 cờ, 3 màu nền",
                "Banner image 6 4 cờ treo cùng nhau",
                "Banner image 7 Collage 4 ảnh nhỏ",
                "Banner image 8 Người phụ nữ đang thêu cờ",
                "Banner image 9 Mẹ và bé cùng sờ hình thêu",
                "Banner image 10 2 bé với 2 cờ, không lộ mặt",
                "Banner image 11 Em bé ngủ, cờ treo gần nôi",
                "Banner image 12 Cờ trong hộp quà mở",
            ],
            item["shot_labels"],
        )

    def test_auto_trello_user_pennant_instruction_overrides_generic_card_name(self) -> None:
        request = CreateJobRequest(
            type="image",
            title="Auto image from Trello card",
            count=4,
            prompt=(
                "Tạo 12 ảnh riêng biệt cho chiếc cờ vải treo trang trí em bé giống chính xác ảnh tham khảo. "
                "Giữ dáng cờ pennant chóp nhọn, thanh gỗ ngang, dây treo bằng thừng, chất liệu linen, "
                "vị trí và bố cục thêu; ảnh 9 mẹ và em bé chạm tay vào họa tiết thêu."
            ),
        )
        cards = [
            {
                "id": "card-generic-embroidery",
                "shortLink": "generic",
                "idList": "ready",
                "name": "Detailed_hand-embroidery_on_a_white_202605261049.jpeg",
                "url": "https://trello.example/c/generic",
                "_image_attachments": [{"id": "att-generic", "name": "source.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-generic"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertIn("Banner category", item["design_analysis"])
        self.assertIn("Banner image 9 Mẹ và bé cùng sờ hình thêu", item["prompt"])
        self.assertIn("Banner image 12 Cờ trong hộp quà mở", item["prompt"])
        self.assertIn("For the required process shot only, a round embroidery hoop is allowed", item["prompt"])
        self.assertNotIn("Pastel fabric colorway lineup", item["shot_labels"])
        self.assertEqual("Banner image 1 Mẹ và bé chạm vào cờ thêu tên", item["shot_labels"][0])
        self.assertEqual("Banner image 12 Cờ trong hộp quà mở", item["shot_labels"][-1])

    def test_havi_product_shot_rules_supply_twelve_safe_shots_for_each_product(self) -> None:
        for product_key, rule in PRODUCT_SHOT_RULES.items():
            with self.subTest(product_key=product_key):
                shots = self.service._flow_operator_product_rule_shot_suite(product_key)
                target_count = int(rule.get("target_count") or self.service.FLOW_AGENT_TARGET_OUTPUT_COUNT)
                joined = " ".join(
                    f"{shot.get('label', '')} {shot.get('brief', '')}".lower()
                    for shot in shots
                )

                self.assertGreaterEqual(len(shots), target_count)
                self.assertNotIn("inactive", joined)
                self.assertIn("Product/category lock", shots[0]["brief"])
                self.assertIn("white daylight", joined)

    def test_banner_wall_hanging_shots_require_visible_wall_hook(self) -> None:
        shots = self.service._flow_operator_product_rule_shot_suite("banner")
        self.assertGreaterEqual(len(shots), 12)

        hook_briefs = [shot["brief"] for shot in shots if "clearly visible wall hook" in shot["brief"]]
        self.assertGreaterEqual(len(hook_briefs), 6)
        self.assertTrue(all("rope/cord visibly hanging" in brief for brief in hook_briefs))

        by_index = {index: shot["brief"] for index, shot in enumerate(shots, start=1)}
        self.assertNotIn("clearly visible wall hook", by_index[4])
        self.assertNotIn("clearly visible wall hook", by_index[7])
        self.assertNotIn("clearly visible wall hook", by_index[8])
        self.assertNotIn("clearly visible wall hook", by_index[12])

    def test_auto_trello_uses_havi_plush_shot_rules_from_excel(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4, prompt="Gấu bông")
        cards = [
            {
                "id": "card-plush",
                "shortLink": "plush",
                "idList": "ready",
                "name": "Personalized_teddy_bear_gau_bong_202605261012.jpeg",
                "url": "https://trello.example/c/plush",
                "_image_attachments": [{"id": "att-plush", "name": "gau_bong_teddy.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-plush"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertIn("Gấu bông category", item["design_analysis"])
        self.assertEqual("Gấu bông image 1 Product display", item["shot_labels"][0])
        self.assertIn("Baby hug", item["shot_labels"][1])
        self.assertIn("Three stuffed animals", item["prompt"])
        self.assertIn("HAVI product shot rule lock", item["prompt"])
        self.assertNotIn("Full doll/plush product", item["prompt"])

    def test_auto_trello_uses_havi_tooth_fairy_pillow_shot_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=10, prompt="goi rang")
        cards = [
            {
                "id": "card-tooth-pillow",
                "shortLink": "tooth-pillow",
                "idList": "ready",
                "name": "goi rang tooth fairy pillow",
                "url": "https://trello.example/c/tooth-pillow",
                "_image_attachments": [{"id": "att-tooth", "name": "tooth_fairy_pillow.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-tooth"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        all_rule_shots = self.service._flow_operator_product_rule_shot_suite("tooth_fairy_pillow")

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(10, len(all_rule_shots))
        self.assertEqual(10, item["flow_agent_image_count"])
        self.assertIn("Tooth Fairy Pillow category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Tooth Fairy Pillow", item["prompt"])
        self.assertEqual("Tooth Fairy Pillow image 1 Clean hero flat lay on beige linen", item["shot_labels"][0])
        self.assertEqual("Tooth Fairy Pillow image 10 Open kraft gift box", item["shot_labels"][-1])
        self.assertIn("My First Tooth", item["prompt"])
        self.assertIn("socks color matching the embroidery thread color", item["prompt"])
        self.assertIn("vintage brass door knob", item["prompt"])
        self.assertIn("white crib rail", item["prompt"])
        self.assertIn("open kraft cardboard gift box", item["prompt"])
        self.assertIn("generate exactly 10", item["prompt"])
        self.assertIn("10 generated output images plus the 1 source image", item["prompt"])
        self.assertNotIn("Supplemental", " ".join(item["shot_labels"]))
        self.assertNotIn("Baby Pillowcase category", item["design_analysis"])

    def test_auto_trello_uses_havi_baby_christmas_album_shot_rules(self) -> None:
        request = CreateJobRequest(
            type="image",
            title="Auto image from Trello card",
            count=12,
            prompt="Baby Christmas Album",
        )
        cards = [
            {
                "id": "card-baby-christmas-album",
                "shortLink": "baby-christmas-album",
                "idList": "ready",
                "name": "Baby Christmas Album",
                "url": "https://trello.example/c/baby-christmas-album",
                "_image_attachments": [
                    {"id": "att-album", "name": "baby_christmas_album.jpeg", "mimeType": "image/jpeg"}
                ],
                "_selected_attachment_ids": ["att-album"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        all_rule_shots = self.service._flow_operator_product_rule_shot_suite("baby_christmas_album")

        self.assertEqual("baby_christmas_album", self.service._flow_operator_product_rule_key_from_text("Baby Christmas Album"))
        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(all_rule_shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Baby Christmas Album category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Baby Christmas Album", item["prompt"])
        self.assertEqual(
            "Baby Christmas Album image 1 Christmas welcome table with closed and open albums",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "Baby Christmas Album image 12 Woman hands embroidering matching cover motif",
            item["shot_labels"][-1],
        )
        self.assertIn("exactly two horizontal photos per visible page", item["prompt"])
        self.assertIn("Santa hat", item["prompt"])
        self.assertIn("exactly four horizontal photos total", item["prompt"])
        self.assertIn("The needle eye must visibly contain thread", item["prompt"])
        self.assertIn("Never use a yellow, amber, dark, or moody cast", item["prompt"])
        self.assertIn("The explicitly numbered close-up detail collage shot is the only allowed four-panel image", item["prompt"])
        self.assertNotIn("Baby Album category", item["design_analysis"])

    def test_auto_trello_uses_havi_christmas_album_shot_rules(self) -> None:
        request = CreateJobRequest(
            type="image",
            title="Auto image from Trello card",
            count=12,
            prompt="Christmas Album",
        )
        cards = [
            {
                "id": "card-christmas-album",
                "shortLink": "christmas-album",
                "idList": "ready",
                "name": "Christmas Album (12).jpeg",
                "url": "https://trello.example/c/christmas-album",
                "_image_attachments": [
                    {"id": "att-album", "name": "christmas_album.jpeg", "mimeType": "image/jpeg"}
                ],
                "_selected_attachment_ids": ["att-album"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        all_rule_shots = self.service._flow_operator_product_rule_shot_suite("christmas_album")

        self.assertEqual("christmas_album", self.service._flow_operator_product_rule_key_from_text("Christmas Album"))
        self.assertEqual(
            "christmas_album",
            self.service._flow_operator_card_name_product_rule_key("Christmas Album (12).jpeg"),
        )
        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(all_rule_shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Christmas Album category", item["design_analysis"])
        self.assertNotIn("Baby Christmas Album category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Christmas Album", item["prompt"])
        self.assertEqual(
            "Christmas Album image 1 Dark coffee table with tea on Christmas morning",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "Christmas Album image 12 Premium album on bright Christmas table",
            item["shot_labels"][-1],
        )
        self.assertIn("steaming cup of tea", item["prompt"])
        self.assertIn("exactly two horizontal photos", item["prompt"])
        self.assertIn("two different cover fabric colors", item["prompt"])
        self.assertIn("same embroidery design, placement, scale", item["prompt"])
        self.assertIn("needle eye must visibly contain thread", item["prompt"])
        self.assertIn("completely free of a yellow cast", item["prompt"])
        self.assertIn("only allowed four-panel image", item["prompt"])

    def test_auto_trello_uses_havi_baby_album_shot_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12, prompt="baby album")
        cards = [
            {
                "id": "card-baby-album",
                "shortLink": "baby-album",
                "idList": "ready",
                "name": "hand_embroidered_baby_album_first_birthday",
                "url": "https://trello.example/c/baby-album",
                "_image_attachments": [{"id": "att-album", "name": "baby_photo_album.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-album"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        all_rule_shots = self.service._flow_operator_product_rule_shot_suite("baby_album")

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(all_rule_shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Baby Album category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Baby Album", item["prompt"])
        self.assertEqual("Baby Album image 1 Birthday welcome table with two display shelves", item["shot_labels"][0])
        self.assertEqual("Baby Album image 12 Woman hands embroidering matching cover motif", item["shot_labels"][-1])
        self.assertIn("two horizontal baby photos inside clear plastic pocket sleeves", item["prompt"])
        self.assertIn("one small board reading \"1st Birthday\"", item["prompt"])
        self.assertIn("Create one square detail collage made of four small close-up photos", item["prompt"])
        self.assertIn("The explicitly numbered close-up detail collage shot is the only allowed four-panel image", item["prompt"])
        self.assertIn("baby photo album, it must remain the same cotton linen baby album", item["prompt"])
        self.assertIn("highlight every stitch of the exact source embroidery", item["prompt"])
        self.assertIn("Put the exact embroidered area from the source cover at the sharp focus point", item["prompt"])
        self.assertNotIn("source daisy or floral embroidery", item["prompt"])
        self.assertNotIn("embroidered flower or main cover motif", item["prompt"])
        self.assertIn("show a baby sitting on a sofa and looking through the album interior photo pages", item["prompt"])
        self.assertNotIn("Guest Book category", item["design_analysis"])

    def test_auto_trello_uses_havi_crown_shot_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        cards = [
            {
                "id": "card-crown",
                "shortLink": "crown",
                "idList": "ready",
                "name": "Olive_green_linen_crown_with_202606050851.jpeg",
                "url": "https://trello.example/c/crown",
                "_image_attachments": [{"id": "att-crown", "name": "olive_green_linen_crown.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-crown"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertIn("Crown category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Crown", item["prompt"])
        self.assertIn("Crown image 1 Crown upright on wood birthday table", item["shot_labels"])
        self.assertIn("Crown image 8 Four-panel crown making process", item["shot_labels"])
        self.assertIn("Crown image 11 Crown on cake stand", item["shot_labels"])
        self.assertTrue(any("Supplemental full product hero" in label for label in item["shot_labels"]))
        self.assertIn("pom-pom or felt-ball tips", item["prompt"])
        self.assertNotIn("Fabric Cross category", item["design_analysis"])

    def test_auto_trello_uses_havi_birthday_hat_fallback_rule(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        cards = [
            {
                "id": "card-birthday-hat",
                "shortLink": "birthday-hat",
                "idList": "ready",
                "name": "mu_sinh_nhat_linen_theu_tay.jpeg",
                "url": "https://trello.example/c/birthday-hat",
                "_image_attachments": [{"id": "att-hat", "name": "birthday_hat_linen.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-hat"],
            }
        ]

        signals = self.service._flow_operator_card_product_signals(request, cards[0])
        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual("birthday_hat", signals["product_rule_key"])
        self.assertEqual(1, len(items))
        item = items[0]
        all_rule_shots = self.service._flow_operator_product_rule_shot_suite("birthday_hat")
        self.assertEqual(12, len(all_rule_shots))
        self.assertIn("Birthday Hat category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Birthday Hat", item["prompt"])
        self.assertEqual("Birthday Hat image 1 White wood birthday tabletop", item["shot_labels"][0])
        self.assertIn("Birthday Hat image 6 Square close-up detail infographic", item["shot_labels"])
        self.assertIn("Birthday Hat image 8 Four-panel birthday hat making process", item["shot_labels"])
        self.assertIn("Birthday Hat image 11 Birthday hat on cake pedestal beside cake", item["shot_labels"])
        self.assertEqual("Birthday Hat image 12 Birthday hat on round wood pedestal with linen drape", item["shot_labels"][-1])
        self.assertNotIn("Supplemental", " ".join(item["shot_labels"]))
        self.assertIn("Infographic text exception", item["prompt"])
        self.assertIn("Only the explicitly numbered infographic, detail, or process shots", item["prompt"])
        self.assertIn("Chi tiet can canh", item["prompt"])
        self.assertIn("birthday hat, it must remain the same linen birthday hat", item["prompt"])
        self.assertIn("pom-pom or felt-ball details", item["prompt"])
        self.assertIn("Detected occasion/season: First birthday", item["prompt"])
        self.assertIn("small cake or cake pedestal", item["prompt"])
        self.assertNotIn("never make a collage", item["prompt"])
        self.assertNotIn("Crown category", item["design_analysis"])

    def test_auto_trello_adapts_decor_to_halloween_bag_context(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=14)
        cards = [
            {
                "id": "card-halloween-bag",
                "shortLink": "halloween-bag",
                "idList": "ready",
                "name": "Halloween trick or treat linen candy bag",
                "url": "https://trello.example/c/halloween-bag",
                "_image_attachments": [{"id": "att-halloween", "name": "trick_or_treat_bag.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-halloween"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Halloween Treat Bag category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Halloween Treat Bag", item["prompt"])
        self.assertIn("Detected occasion/season: Halloween", item["prompt"])
        self.assertIn("mini pumpkins", item["prompt"])
        self.assertIn("wrapped candy in orange/black/purple", item["prompt"])

    def test_auto_trello_uses_havi_halloween_pillow_shot_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        cards = [
            {
                "id": "card-halloween-pillow",
                "shortLink": "halloween-pillow",
                "idList": "ready",
                "name": "Halloween baby pillow with wool embroidery",
                "url": "https://trello.example/c/halloween-pillow",
                "_image_attachments": [{"id": "att-pillow", "name": "halloween_pillow_source.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-pillow"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        all_rule_shots = self.service._flow_operator_product_rule_shot_suite("halloween_pillow")

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(all_rule_shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Halloween Pillow category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Halloween Pillow", item["prompt"])
        self.assertEqual("Halloween Pillow image 1 Two Halloween pillows on white rug with pumpkins", item["shot_labels"][0])
        self.assertEqual("Halloween Pillow image 12 Pillow on sofa with airy Halloween decor", item["shot_labels"][-1])
        self.assertIn("pink gingham and blue gingham", item["prompt"])
        self.assertIn("2x2 grid collage", item["prompt"])
        self.assertIn("wool embroidery thread", item["prompt"])
        self.assertIn("baby teepee", item["prompt"])
        self.assertIn("large sharp wool embroidery needle with a wooden handle", item["prompt"])
        self.assertIn("Detected occasion/season: Halloween", item["prompt"])
        self.assertNotIn("Halloween Treat Bag category", item["design_analysis"])

    def test_auto_trello_uses_christmas_pillowcase_before_generic_pillow_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        cards = [
            {
                "id": "card-christmas-pillowcase",
                "shortLink": "christmas-pillowcase",
                "idList": "ready",
                "name": "Christmas Pillowcase (12).jpeg",
                "url": "https://trello.example/c/christmas-pillowcase",
                "_image_attachments": [
                    {"id": "att-pillow", "name": "punch_needle_christmas_pillow.jpeg", "mimeType": "image/jpeg"}
                ],
                "_selected_attachment_ids": ["att-pillow"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        shots = self.service._flow_operator_product_rule_shot_suite("christmas_pillowcase")

        self.assertEqual(
            "christmas_pillowcase",
            self.service._flow_operator_product_rule_key_from_text("Christmas Pillowcase"),
        )
        self.assertEqual(
            "christmas_pillowcase",
            self.service._flow_operator_card_name_product_rule_key("Christmas Pillowcase (12).jpeg"),
        )
        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Christmas Pillowcase category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Christmas Pillowcase", item["prompt"])
        self.assertNotIn("HAVI product shot rule lock: Baby Pillowcase uses", item["prompt"])
        self.assertNotIn("HAVI product shot rule lock: Linen Pillowcase uses", item["prompt"])
        self.assertEqual(
            "Christmas Pillowcase image 1 Two coordinated Christmas pillows on soft white rug",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "Christmas Pillowcase image 12 Front-facing pillow on sofa with Santa decorations",
            item["shot_labels"][-1],
        )
        self.assertIn("preserve exactly four corner pompoms on each pillow", item["prompt"])
        self.assertIn("if the source has no pompoms, never add any pompoms", item["prompt"])
        self.assertIn("if the source has no name, never add one", item["prompt"])
        self.assertIn("exactly four macro photographs", item["prompt"])
        self.assertIn("large sharp wooden-handled punch needle", item["prompt"])
        self.assertIn("wool yarn visibly threaded through the rear or tail", item["prompt"])
        self.assertNotIn("Detected occasion/season: Halloween", item["prompt"])

    def test_auto_trello_adapts_decor_to_christmas_context(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        cards = [
            {
                "id": "card-christmas-bag",
                "shortLink": "christmas-bag",
                "idList": "ready",
                "name": "Christmas Noel linen drawstring gift bag",
                "desc": "Holiday listing photos for Christmas gift packaging with clean white daylight.",
                "url": "https://trello.example/c/christmas-bag",
                "_image_attachments": [{"id": "att-bag", "name": "embroidered_drawstring_pouch.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-bag"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertIn("Drawstring Bag category", item["design_analysis"])
        self.assertIn("Detected occasion/season: Christmas", item["prompt"])
        self.assertIn("evergreen sprigs", item["prompt"])
        self.assertIn("matte ornaments", item["prompt"])
        self.assertNotIn("Detected occasion/season: Halloween", item["prompt"])

    def test_auto_trello_uses_pc_stocks_punch_needle_shot_rules(self) -> None:
        request = CreateJobRequest(
            type="image",
            title="Auto image from Trello card",
            count=12,
            prompt="PC Stocks",
        )
        cards = [
            {
                "id": "card-pc-stocks",
                "shortLink": "pc-stocks",
                "idList": "ready",
                "name": "PC Stocks (12).jpeg",
                "url": "https://trello.example/c/pc-stocks",
                "_image_attachments": [
                    {"id": "att-stocking", "name": "punch_needle_christmas_stocking.jpeg", "mimeType": "image/jpeg"}
                ],
                "_selected_attachment_ids": ["att-stocking"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        all_rule_shots = self.service._flow_operator_product_rule_shot_suite("pc_stocks")

        self.assertEqual("pc_stocks", self.service._flow_operator_product_rule_key_from_text("PC Stocks"))
        self.assertEqual(
            "pc_stocks",
            self.service._flow_operator_card_name_product_rule_key("PC Stocks (12).jpeg"),
        )
        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(all_rule_shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("PC Stocks category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: PC Stocks", item["prompt"])
        self.assertEqual(
            "PC Stocks image 1 Stocking hanging on real Christmas tree branch",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "PC Stocks image 12 Hand-held close-up showing flat one-sided construction",
            item["shot_labels"][-1],
        )
        self.assertIn("thick raised wool punch-needle loop texture", item["prompt"])
        self.assertIn("flat, one-sided decorative stocking panel", item["prompt"])
        self.assertIn("no opening, pocket, interior cavity, or storage function", item["prompt"])
        self.assertNotIn("looking naturally into the opening", item["prompt"])
        self.assertNotIn("Fill it with small gifts", item["prompt"])
        self.assertIn("large punch needle with a wooden handle", item["prompt"])
        self.assertIn("one navy stocking, one forest-green stocking, and one deep-red stocking", item["prompt"])
        self.assertIn("exactly five flat one-sided decorative stockings", item["prompt"])
        self.assertIn("natural ivory, dusty pink, soft sage green, navy blue, and deep Christmas red", item["prompt"])
        self.assertNotIn("Size Chart", item["prompt"])
        self.assertNotIn("Cuff Width", item["prompt"])
        self.assertNotIn("Foot Width", item["prompt"])
        self.assertNotIn("Overall Height", item["prompt"])
        self.assertNotIn("Infographic text exception", item["prompt"])
        self.assertIn("Detected occasion/season: Christmas", item["prompt"])
        self.assertNotIn("Ornament Round category", item["design_analysis"])

    def test_auto_trello_uses_napkin_set_shot_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=10)
        cards = [
            {
                "id": "card-napkin-set",
                "shortLink": "napkin-set",
                "idList": "ready",
                "name": "Napkin Set (6).jpeg",
                "url": "https://trello.example/c/napkin-set",
                "_image_attachments": [
                    {"id": "att-napkins", "name": "white_linen_fall_napkins.jpeg", "mimeType": "image/jpeg"}
                ],
                "_selected_attachment_ids": ["att-napkins"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        shots = self.service._flow_operator_product_rule_shot_suite("napkin_set")

        self.assertEqual("napkin_set", self.service._flow_operator_product_rule_key_from_text("Napkin Set"))
        self.assertEqual("napkin_set", self.service._flow_operator_product_rule_key_from_text("fall linen napkins"))
        self.assertEqual(
            "napkin_set",
            self.service._flow_operator_card_name_product_rule_key("Napkin Set (6).jpeg"),
        )
        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(10, len(shots))
        self.assertEqual(10, item["flow_agent_image_count"])
        self.assertIn("Napkin Set category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Napkin Set", item["prompt"])
        self.assertEqual(
            "Napkin Set image 1 Single embroidered napkin centered on white dinner plate",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "Napkin Set image 10 Aligned embroidered corners on white wood table",
            item["shot_labels"][-1],
        )
        self.assertIn("exactly six handmade white linen dinner napkins", item["prompt"])
        self.assertIn("Never repeat one motif across several napkins", item["prompt"])
        self.assertIn("one source napkin on each plate", item["prompt"])
        self.assertIn("realistically threaded needle", item["prompt"])
        self.assertIn("No collage, contact sheet, grid", item["prompt"])

    def test_auto_trello_uses_halloween_banner_shot_rules_before_generic_banner(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=14)
        cards = [
            {
                "id": "card-halloween-banner",
                "shortLink": "halloween-banner",
                "idList": "ready",
                "name": "Halloween Banner (14).jpeg",
                "url": "https://trello.example/c/halloween-banner",
                "_image_attachments": [
                    {"id": "att-banner", "name": "hand_embroidered_halloween_linen_banner.jpeg", "mimeType": "image/jpeg"}
                ],
                "_selected_attachment_ids": ["att-banner"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        shots = self.service._flow_operator_product_rule_shot_suite("halloween_banner")

        self.assertEqual("halloween_banner", self.service._flow_operator_product_rule_key_from_text("Halloween Banner"))
        self.assertEqual(
            "halloween_banner",
            self.service._flow_operator_card_name_product_rule_key("Halloween Banner (14).jpeg"),
        )
        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Halloween Banner category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Halloween Banner", item["prompt"])
        self.assertNotIn("HAVI product shot rule lock: Banner uses", item["prompt"])
        self.assertEqual(
            "Halloween Banner image 1 Small banner centered above decorated crib",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "Halloween Banner image 12 Small banner hanging naturally on wardrobe or room door",
            item["shot_labels"][-1],
        )
        self.assertIn("same wooden hanging rod", item["prompt"])
        self.assertIn("realistically small relative to doors, wardrobes, cribs", item["prompt"])
        self.assertIn('exact words "Happy Halloween"', item["prompt"])
        self.assertIn("exactly four macro photographs", item["prompt"])
        self.assertIn("hand-stitched thread relief and linen fibers", item["prompt"])

    def test_auto_trello_uses_christmas_banner_shot_rules_before_other_banner_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=13)
        cards = [
            {
                "id": "card-christmas-banner",
                "shortLink": "christmas-banner",
                "idList": "ready",
                "name": "Christmas Banner (13).jpeg",
                "url": "https://trello.example/c/christmas-banner",
                "_image_attachments": [
                    {"id": "att-banner", "name": "hand_embroidered_christmas_linen_banner.jpeg", "mimeType": "image/jpeg"}
                ],
                "_selected_attachment_ids": ["att-banner"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        shots = self.service._flow_operator_product_rule_shot_suite("christmas_banner")

        self.assertEqual("christmas_banner", self.service._flow_operator_product_rule_key_from_text("Christmas Banner"))
        self.assertEqual(
            "christmas_banner",
            self.service._flow_operator_card_name_product_rule_key("Christmas Banner (13).jpeg"),
        )
        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Christmas Banner category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Christmas Banner", item["prompt"])
        self.assertNotIn("HAVI product shot rule lock: Halloween Banner", item["prompt"])
        self.assertNotIn("HAVI product shot rule lock: Banner uses", item["prompt"])
        self.assertEqual(
            "Christmas Banner image 1 Small banner hanging from child-room door hook",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "Christmas Banner image 12 Baby seated on floor holding small Christmas banner",
            item["shot_labels"][-1],
        )
        self.assertIn("realistically small relative to doors, wardrobes, cribs", item["prompt"])
        self.assertIn("exactly four macro photographs", item["prompt"])
        self.assertIn("Happy Christmas", item["prompt"])
        self.assertIn("one vase of fresh evergreen branches", item["prompt"])
        self.assertIn("one small plush Santa Claus figure", item["prompt"])
        self.assertIn("one plate of colorful Christmas candy", item["prompt"])
        self.assertIn("no pumpkins or ghosts", item["prompt"])
        self.assertIn("clearly visible wall hook", item["prompt"])

    def test_auto_trello_uses_ornament_round_christmas_shot_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=14)
        cards = [
            {
                "id": "card-ornament-round",
                "shortLink": "ornament-round",
                "idList": "ready",
                "name": "Ornament_Round Christmas embroidered linen keepsake",
                "url": "https://trello.example/c/ornament-round",
                "_image_attachments": [{"id": "att-ornament", "name": "round_christmas_ornament.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-ornament"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        all_rule_shots = self.service._flow_operator_product_rule_shot_suite("ornament_round")

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(all_rule_shots))
        self.assertNotIn("Minimal Christmas table", [shot.get("label") if isinstance(shot, dict) else shot[0] for shot in all_rule_shots])
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Ornament Round category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Ornament Round", item["prompt"])
        self.assertEqual("Ornament Round image 1 Round ornament on white wood table with pine branch", item["shot_labels"][0])
        self.assertEqual("Ornament Round image 12 Four-panel macro of embroidery frame and clasp", item["shot_labels"][-1])
        self.assertIn("Detected occasion/season: Christmas", item["prompt"])
        self.assertIn("Merry Christmas", item["prompt"])
        self.assertIn("Planned prop text exception", item["prompt"])
        self.assertIn("metal clasp or fastener", item["prompt"])
        self.assertIn("raised hand-stitch texture", item["prompt"])
        self.assertIn("four-panel process collage", item["prompt"])
        self.assertNotIn("Wedding Hoop category", item["design_analysis"])

    def test_auto_trello_uses_pn_ornament_shot_rules(self) -> None:
        self.assertEqual(
            "pn_ornament",
            self.service._flow_operator_card_name_product_rule_key("PN Ornament"),
        )
        self.assertEqual(
            "pn_ornament",
            self.service._flow_operator_card_name_product_rule_key("Punch Needle Christmas Ornament (7).jpeg"),
        )
        self.assertEqual(
            "ornament_round",
            self.service._flow_operator_card_name_product_rule_key("Ornament_Round"),
        )

        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=14)
        card = {
            "id": "card-pn-ornament",
            "shortLink": "pn-ornament",
            "idList": "ready",
            "name": "PN Ornament (5).jpeg",
            "url": "https://trello.example/c/pn-ornament",
            "_image_attachments": [
                {"id": "att-pn-ornament", "name": "punch_needle_christmas_ornament.jpeg", "mimeType": "image/jpeg"}
            ],
            "_selected_attachment_ids": ["att-pn-ornament"],
        }

        items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)
        shots = self.service._flow_operator_product_rule_shot_suite("pn_ornament")

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("PN Ornament category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: PN Ornament", item["prompt"])
        self.assertEqual(
            "PN Ornament image 1 Punch Needle ornament on white wood table with pine branch",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "PN Ornament image 12 Punch Needle loops linen frame and metal clasp close-ups",
            item["shot_labels"][-1],
        )
        self.assertIn("thick raised punch-needle loop-pile texture", item["prompt"])
        self.assertIn("large wooden-handled punch needle", item["prompt"])
        self.assertIn("Only images 8 and 14 may be four-panel collages", item["prompt"])
        self.assertNotIn("HAVI product shot rule lock: Ornament Round", item["prompt"])

    def test_auto_trello_uses_advent_calendar_shot_rules(self) -> None:
        self.assertEqual(
            "advent_calendar",
            self.service._flow_operator_card_name_product_rule_key("advent_calendar"),
        )
        self.assertEqual(
            "advent_calendar",
            self.service._flow_operator_card_name_product_rule_key(
                "Embroidered Christmas countdown calendar (8).jpeg"
            ),
        )

        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        card = {
            "id": "card-advent-calendar",
            "shortLink": "advent-calendar",
            "idList": "ready",
            "name": "advent_calendar (8).jpeg",
            "url": "https://trello.example/c/advent-calendar",
            "_image_attachments": [
                {"id": "att-advent", "name": "embroidered_advent_calendar.jpeg", "mimeType": "image/jpeg"}
            ],
            "_selected_attachment_ids": ["att-advent"],
        }

        items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)
        shots = self.service._flow_operator_product_rule_shot_suite("advent_calendar")

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Advent Calendar category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Advent Calendar", item["prompt"])
        self.assertEqual(
            "Advent Calendar image 1 Complete advent calendar centered on bright Christmas wall",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "Advent Calendar image 12 Advent calendar above bright Christmas console table",
            item["shot_labels"][-1],
        )
        self.assertIn("exact pocket count and grid", item["prompt"])
        self.assertIn("no missing, duplicated, swapped", item["prompt"])
        self.assertIn("Only image 6 may be a four-panel collage", item["prompt"])
        self.assertNotIn("HAVI product shot rule lock: Banner", item["prompt"])

    def test_auto_trello_uses_christmas_fabric_cross_before_generic_fabric_cross(self) -> None:
        self.assertEqual(
            "christmas_fabric_cross",
            self.service._flow_operator_card_name_product_rule_key("Christmas Fabric Cross"),
        )
        self.assertEqual(
            "christmas_fabric_cross",
            self.service._flow_operator_card_name_product_rule_key("Christmas Fabric Cross (4).jpeg"),
        )
        self.assertEqual(
            "fabric_cross",
            self.service._flow_operator_card_name_product_rule_key("Fabric Cross"),
        )

        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        card = {
            "id": "card-christmas-fabric-cross",
            "shortLink": "christmas-fabric-cross",
            "idList": "ready",
            "name": "Christmas Fabric Cross (4).jpeg",
            "url": "https://trello.example/c/christmas-fabric-cross",
            "_image_attachments": [
                {"id": "att-cross", "name": "christmas_fabric_cross.jpeg", "mimeType": "image/jpeg"}
            ],
            "_selected_attachment_ids": ["att-cross"],
        }

        items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)
        shots = self.service._flow_operator_product_rule_shot_suite("christmas_fabric_cross")

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Christmas Fabric Cross category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Christmas Fabric Cross", item["prompt"])
        self.assertEqual(
            "Christmas Fabric Cross image 1 Baby gently holding exact fabric cross in Christmas nursery",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "Christmas Fabric Cross image 12 Three neutral fabric-color crosses in pine-lined wicker basket",
            item["shot_labels"][-1],
        )
        self.assertIn("same exact cross silhouette", item["prompt"])
        self.assertIn("Only image 7 may be one four-panel 2x2 process collage", item["prompt"])
        self.assertIn("No yellow", item["prompt"])
        self.assertNotIn("HAVI product shot rule lock: Fabric Cross\n", item["prompt"])

    def test_auto_trello_birthday_hat_text_overrides_crown_visual_fallback(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        card = {
            "id": "card-birthday-hat-visual",
            "shortLink": "birthday-hat-visual",
            "idList": "ready",
            "name": "mu_sinh_nhat_linen_theu_tay.jpeg",
            "url": "https://trello.example/c/birthday-hat-visual",
            "_image_attachments": [{"id": "att-hat", "name": "source.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["att-hat"],
            "_visual_product_rule_key": "crown",
            "_visual_product_rule_confidence": 0.92,
            "_visual_product_rule_visible_product": "soft fabric crown-like birthday hat",
        }

        signals = self.service._flow_operator_card_product_signals(request, card)
        items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)

        self.assertEqual("birthday_hat", signals["product_rule_key"])
        self.assertEqual(1, len(items))
        self.assertIn("Birthday Hat category", items[0]["design_analysis"])
        self.assertNotIn("Crown category", items[0]["design_analysis"])

    def test_auto_trello_uses_havi_drawstring_bag_shot_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        cards = [
            {
                "id": "card-drawstring-bag",
                "shortLink": "drawstring-bag",
                "idList": "ready",
                "name": "Sage_green_linen_drawstring_bag_tui_rut_day_202606080915.jpeg",
                "url": "https://trello.example/c/drawstring-bag",
                "_image_attachments": [{"id": "att-bag", "name": "embroidered_drawstring_pouch.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-bag"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        all_rule_shots = self.service._flow_operator_product_rule_shot_suite("drawstring_bag")

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(all_rule_shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Drawstring Bag category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Drawstring Bag", item["prompt"])
        self.assertIn("Show one single cotton linen drawstring bag standing naturally", item["prompt"])
        self.assertIn("Show three drawstring bags standing upright together in a shallow light wooden tray", item["prompt"])
        self.assertIn("Create one square detail collage made of four small close-up photos", item["prompt"])
        self.assertIn("Place one drawstring bag neatly inside a small open paper gift box", item["prompt"])
        self.assertNotIn("light wood shelf with fabric-covered books", item["prompt"])
        self.assertNotIn("held naturally in one adult woman hand", item["prompt"])
        self.assertNotIn("relaxing tea-table corner", item["prompt"])
        self.assertNotIn("hanging naturally from a small wooden hook or rail", item["prompt"])
        self.assertNotIn("suspended by one side of its own drawstring cord", item["prompt"])
        self.assertIn("drawstring cord color must match", item["prompt"])
        self.assertIn("not a hoop product", item["prompt"])
        self.assertNotIn("Banner category", item["design_analysis"])

    def test_auto_trello_uses_havi_passport_cover_shot_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        cards = [
            {
                "id": "card-passport-cover",
                "shortLink": "passport-cover",
                "idList": "ready",
                "name": "Bọc passport",
                "url": "https://trello.example/c/passport-cover",
                "_image_attachments": [{"id": "att-passport", "name": "doi_Cozy_Lodge_thanh_ten_202606060853.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-passport"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        all_rule_shots = self.service._flow_operator_product_rule_shot_suite("passport_cover")

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(all_rule_shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Passport Cover category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Passport Cover", item["prompt"])
        self.assertIn("Travel desk with phone and boarding pass", item["shot_labels"][0])
        self.assertIn("Place the passport cover beside a phone, boarding pass, earbuds, and a small wallet", item["prompt"])
        self.assertIn("Create one square detail collage made of four small close-up photos", item["prompt"])
        self.assertIn("Place one passport cover neatly inside a small open light-colored paper gift box", item["prompt"])
        self.assertIn("same passport cover/passport holder form", item["prompt"])
        self.assertIn("The explicitly numbered close-up detail collage shot is the only allowed four-panel image", item["prompt"])
        self.assertNotIn("Drawstring Bag category", item["design_analysis"])
        self.assertNotIn("Show one single cotton linen drawstring bag standing naturally", item["prompt"])

    def test_auto_trello_uses_havi_hair_bow_shot_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        cards = [
            {
                "id": "card-hair-bow",
                "shortLink": "hair-bow",
                "idList": "ready",
                "name": "no_buoc_toc_theu_tay_linen_202606090812.jpeg",
                "url": "https://trello.example/c/hair-bow",
                "_image_attachments": [{"id": "att-hair-bow", "name": "embroidered_hair_tie_bow.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-hair-bow"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        all_rule_shots = self.service._flow_operator_product_rule_shot_suite("hair_bow")

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(all_rule_shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Hair Bow category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Hair Bow", item["prompt"])
        self.assertIn("Bow in wooden tray with linen props", item["shot_labels"][0])
        self.assertIn("Three bows arranged on vanity table", item["prompt"])
        self.assertIn("Four bows laid on bright tabletop", item["prompt"])
        self.assertIn("Every bow must rest fully on the table", item["prompt"])
        self.assertIn("Do not clip, pin, hang, peg, suspend, or attach the bows", item["prompt"])
        self.assertIn("Place one hand-embroidered cotton linen hair bow naturally", item["prompt"])
        self.assertIn("elastic scrunchie ring or clip/hair-tie construction", item["prompt"])
        self.assertIn("Create one square detail collage made of four small close-up photos", item["prompt"])
        self.assertIn("Place one hair bow neatly inside a small open light-colored paper gift box", item["prompt"])
        self.assertIn("same hair accessory form with its bow shape, tails, center knot, and elastic/clip hardware", item["prompt"])
        self.assertIn("The explicitly numbered close-up detail collage shot is the only allowed four-panel image", item["prompt"])
        self.assertNotIn("Four bows clipped on clothesline", item["prompt"])
        self.assertNotIn("wooden hair accessory rack", item["prompt"])
        self.assertNotIn("Passport Cover category", item["design_analysis"])
        self.assertNotIn("Drawstring Bag category", item["design_analysis"])

    def test_auto_trello_visual_product_rule_overrides_random_card_name(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        cards = [
            {
                "id": "card-dress",
                "shortLink": "dress",
                "idList": "ready",
                "name": "A_single_white_linen_pillow_202605271042.jpeg",
                "url": "https://trello.example/c/dress",
                "_image_attachments": [{"id": "att-dress", "name": "source.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-dress"],
                "_visual_product_rule_key": "dress_baby",
                "_visual_product_rule_confidence": 0.94,
                "_visual_product_rule_visible_product": "baby dress with ruffled sleeves",
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertIn("Dress Baby category", item["design_analysis"])
        self.assertNotIn("Linen Pillowcase category", item["design_analysis"])
        self.assertIn("Visual source classification as Dress Baby", item["design_analysis"])
        self.assertEqual(12, len(item["shot_labels"]))
        self.assertTrue(item["shot_labels"][0].startswith("Dress Baby image 1 "))
        self.assertIn("mannequin", item["prompt"])
        self.assertIn("HAVI product shot rule lock: Dress Baby", item["prompt"])
        self.assertIn("back placket must show exactly two", item["prompt"])
        self.assertIn("no third button", item["prompt"])
        self.assertIn("Do not add any text overlay or caption", item["prompt"])
        self.assertNotIn("This lovely cotton linen children's dress", item["prompt"])
        self.assertNotIn("Pastel fabric colorway lineup", item["shot_labels"])

    def test_auto_trello_uses_halloween_dress_baby_before_generic_dress_rule(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        cards = [
            {
                "id": "card-halloween-dress",
                "shortLink": "halloween-dress",
                "idList": "ready",
                "name": "Halloween Dress Baby (12).jpeg",
                "url": "https://trello.example/c/halloween-dress",
                "_image_attachments": [
                    {"id": "att-dress", "name": "embroidered_halloween_baby_dress.jpeg", "mimeType": "image/jpeg"}
                ],
                "_selected_attachment_ids": ["att-dress"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        shots = self.service._flow_operator_product_rule_shot_suite("halloween_dress_baby")

        self.assertEqual(
            "halloween_dress_baby",
            self.service._flow_operator_product_rule_key_from_text("Halloween Dress Baby"),
        )
        self.assertEqual(
            "halloween_dress_baby",
            self.service._flow_operator_card_name_product_rule_key("Halloween Dress Baby (12).jpeg"),
        )
        self.assertEqual(
            "halloween_dress_baby",
            self.service._flow_operator_product_rule_key_from_text("Halloween Baby Dress"),
        )
        self.assertEqual(
            "halloween_dress_baby",
            self.service._flow_operator_card_name_product_rule_key("Halloween Baby Dress (12).jpeg"),
        )
        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Halloween Dress Baby category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Halloween Dress Baby", item["prompt"])
        self.assertNotIn("HAVI product shot rule lock: Dress Baby uses", item["prompt"])
        self.assertEqual(
            "Halloween Dress Baby image 1 Four pastel dresses on child mannequins in two rows",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "Halloween Dress Baby image 12 Three-year-old wearing dress at bright Halloween party",
            item["shot_labels"][-1],
        )
        self.assertIn("never add or remove a button", item["prompt"])
        self.assertNotIn("exactly two small natural wooden buttons", item["prompt"])
        self.assertIn("exactly eight distinct process panels", item["prompt"])
        self.assertIn("Vietnamese seamstress", item["prompt"])
        self.assertIn("exactly four high-resolution close-up photographs", item["prompt"])
        self.assertIn("American Halloween trick-or-treat scene", item["prompt"])
        self.assertNotIn("birthday party", item["prompt"].lower())
        self.assertNotIn("back-to-school", item["prompt"].lower())

    def test_auto_trello_uses_christmas_dress_baby_before_generic_dress_rule(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        cards = [
            {
                "id": "card-christmas-dress",
                "shortLink": "christmas-dress",
                "idList": "ready",
                "name": "Christmas Dress Baby (12).jpeg",
                "url": "https://trello.example/c/christmas-dress",
                "_image_attachments": [
                    {"id": "att-dress", "name": "embroidered_christmas_baby_dress.jpeg", "mimeType": "image/jpeg"}
                ],
                "_selected_attachment_ids": ["att-dress"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)
        shots = self.service._flow_operator_product_rule_shot_suite("christmas_dress_baby")

        self.assertEqual(
            "christmas_dress_baby",
            self.service._flow_operator_product_rule_key_from_text("Christmas Dress Baby"),
        )
        self.assertEqual(
            "christmas_dress_baby",
            self.service._flow_operator_card_name_product_rule_key("Christmas Dress Baby (12).jpeg"),
        )
        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Christmas Dress Baby category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Christmas Dress Baby", item["prompt"])
        self.assertNotIn("HAVI product shot rule lock: Dress Baby uses", item["prompt"])
        self.assertEqual(
            "Christmas Dress Baby image 1 Four pastel Christmas dresses on child mannequins in two rows",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "Christmas Dress Baby image 12 Two four-year-old children wearing dresses under Christmas tree",
            item["shot_labels"][-1],
        )
        self.assertIn("collar must remain clean white in every colorway", item["prompt"])
        self.assertIn("never add or remove a button", item["prompt"])
        self.assertNotIn("exactly two small natural wooden buttons", item["prompt"])
        self.assertIn("exactly eight distinct process panels", item["prompt"])
        self.assertIn("Vietnamese seamstress", item["prompt"])
        self.assertIn("exactly four high-resolution close-up photographs", item["prompt"])
        self.assertIn("three-year-old girl wearing the exact source dress", item["prompt"])
        self.assertNotIn("birthday party", item["prompt"].lower())
        self.assertNotIn("back-to-school", item["prompt"].lower())

    def test_auto_trello_uses_havi_vows_book_active_rules_only(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4, prompt="Vows Book")
        cards = [
            {
                "id": "card-vows",
                "shortLink": "vows",
                "idList": "ready",
                "name": "Wedding_Vows_Book_Bride_Groom_202605261100.jpeg",
                "url": "https://trello.example/c/vows",
                "_image_attachments": [{"id": "att-vows", "name": "vows_book.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-vows"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual("Vows Book image 1 Đôi uyên ương cùng đọc", item["shot_labels"][0])
        self.assertIn("Đôi uyên ương cùng đọc", item["prompt"])
        self.assertTrue(any("Supplemental lifestyle variant" in label for label in item["shot_labels"]))
        self.assertNotIn("Cô dâu đọc vows riêng", item["prompt"])
        self.assertNotIn("2 cuốn trên pale surface", item["prompt"])

    def test_auto_trello_recognizes_vows_notebook_filename_as_vows_book(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4)
        cards = [
            {
                "id": "card-vows-notebook",
                "shortLink": "vows-notebook",
                "idList": "ready",
                "name": "Vows notebook Autumn (10).jpeg",
                "url": "https://trello.example/c/vows-notebook",
                "_image_attachments": [
                    {
                        "id": "att-vows-notebook",
                        "name": "Vows notebook Autumn (10).jpeg",
                        "mimeType": "image/jpeg",
                    }
                ],
                "_selected_attachment_ids": ["att-vows-notebook"],
            }
        ]

        rule_key = self.service._flow_operator_card_name_product_rule_key(cards[0]["name"])
        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual("vows_book", rule_key)
        self.assertEqual(1, len(items))
        self.assertTrue(items[0]["shot_labels"][0].startswith("Vows Book image 1 "))

    def test_auto_trello_recognizes_halloween_notebook_rule(self) -> None:
        self.assertEqual(
            "halloween_notebook",
            self.service._flow_operator_card_name_product_rule_key("Halloween Notebook (3).jpeg"),
        )

    def test_auto_trello_routes_album_and_notebook_names_without_guessing_ambiguous_cards(self) -> None:
        self.assertEqual(
            "album",
            self.service._flow_operator_card_name_product_rule_key("Halloween Album"),
        )
        self.assertEqual(
            "notebook",
            self.service._flow_operator_card_name_product_rule_key("Autumn Notebook"),
        )
        self.assertEqual(
            "",
            self.service._flow_operator_card_name_product_rule_key("Thanksgiving Album Notebook"),
        )
        self.assertEqual(
            "halloween_notebook",
            self.service._flow_operator_card_name_product_rule_key("Halloween Notebook"),
        )
        self.assertEqual(
            "christmas_album",
            self.service._flow_operator_card_name_product_rule_key("Christmas Album"),
        )

        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        ambiguous_card = {
            "id": "card-ambiguous-album-notebook",
            "name": "Autumn Album Notebook",
            "_visual_product_rule_key": "album",
            "_visual_product_rule_confidence": 0.99,
            "_image_attachments": [
                {"id": "att-book", "name": "embroidered_album_notebook.jpeg", "mimeType": "image/jpeg"}
            ],
        }
        signals = self.service._flow_operator_card_product_signals(request, ambiguous_card)

        self.assertTrue(signals["ambiguous_album_notebook_name"])
        self.assertEqual("", signals["product_rule_key"])
        self.assertEqual(12, len(self.service._flow_operator_product_rule_shot_suite("album")))
        self.assertEqual(12, len(self.service._flow_operator_product_rule_shot_suite("notebook")))

    def test_auto_trello_recognizes_wreath_sash_rule(self) -> None:
        self.assertEqual(
            "christmas_sash",
            self.service._flow_operator_card_name_product_rule_key("Christmas Sash"),
        )
        self.assertEqual(
            "family_halloween_sash",
            self.service._flow_operator_card_name_product_rule_key("Family Halloween Sash"),
        )
        self.assertEqual(
            "halloween_wreath_sash",
            self.service._flow_operator_card_name_product_rule_key("halloween wreath sash"),
        )
        self.assertEqual(
            "wreath_sash",
            self.service._flow_operator_card_name_product_rule_key("Autumn wreath sash"),
        )

    def test_auto_trello_uses_christmas_sash_shot_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        card = {
            "id": "card-christmas-sash",
            "shortLink": "christmas-sash",
            "idList": "ready",
            "name": "Christmas Sash (4).jpeg",
            "url": "https://trello.example/c/christmas-sash",
            "_image_attachments": [
                {"id": "att-sash", "name": "christmas_wreath_sash.jpeg", "mimeType": "image/jpeg"}
            ],
            "_selected_attachment_ids": ["att-sash"],
        }

        items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)
        shots = self.service._flow_operator_product_rule_shot_suite("christmas_sash")

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Christmas Sash category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Christmas Sash", item["prompt"])
        self.assertEqual(
            "Christmas Sash image 1 Close front view of sash tied below evergreen wreath",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "Christmas Sash image 12 Artisan hand-stitching exact Christmas sash motif",
            item["shot_labels"][-1],
        )
        self.assertIn("motif tail on the left and the lettering tail on the right", item["prompt"])
        self.assertIn("exactly at 6 o'clock", item["prompt"])
        self.assertIn("never a decorative bow", item["prompt"])
        self.assertIn("Only image 6 may be a four-panel 2x2 collage", item["prompt"])
        self.assertIn("realistically small and never enlarge or lengthen", item["prompt"])
        self.assertIn("panels one and two show two different close sections", item["prompt"])
        self.assertIn("needle eye is visibly threaded", item["prompt"])
        self.assertIn("red, evergreen-green, and bronze-gold thread spools", item["prompt"])
        self.assertIn("images 7 and 11 may vary the linen base color", item["prompt"])
        self.assertNotIn("Halloween Wreath Sash category", item["design_analysis"])

    def test_auto_trello_uses_jewelry_box_shot_rules(self) -> None:
        self.assertEqual(
            "jewelry_box",
            self.service._flow_operator_card_name_product_rule_key("Jewery Box"),
        )
        self.assertEqual(
            "jewelry_box",
            self.service._flow_operator_card_name_product_rule_key("Personalized Jewellery Box"),
        )

        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        card = {
            "id": "card-jewelry-box",
            "shortLink": "jewelry-box",
            "idList": "ready",
            "name": "Jewery Box (4).jpeg",
            "url": "https://trello.example/c/jewelry-box",
            "_image_attachments": [
                {"id": "att-box", "name": "white_linen_embroidered_jewelry_boxes.jpeg", "mimeType": "image/jpeg"}
            ],
            "_selected_attachment_ids": ["att-box"],
        }

        items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)
        shots = self.service._flow_operator_product_rule_shot_suite("jewelry_box")

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Jewelry Box category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Jewelry Box", item["prompt"])
        self.assertEqual(
            "Jewelry Box image 1 Complete embroidered jewelry-box collection in two balanced rows",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "Jewelry Box image 12 Complete closed collection with wedding jewelry and veil",
            item["shot_labels"][-1],
        )
        self.assertIn("exactly two shallow side-by-side rectangular compartments", item["prompt"])
        self.assertIn("one single straight divider", item["prompt"])
        self.assertIn("Anita, Mom, Alice, Maria, Chloe, Jessie, Crystal, Eloise, and Jenna", item["prompt"])
        self.assertIn("show the complete source collection together", item["prompt"])

    def test_auto_trello_uses_halloween_wreath_sash_shot_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        card = {
            "id": "card-halloween-wreath-sash",
            "shortLink": "halloween-wreath-sash",
            "idList": "ready",
            "name": "Halloween Wreath Sash (7).jpeg",
            "url": "https://trello.example/c/halloween-wreath-sash",
            "_image_attachments": [
                {"id": "att-sash", "name": "halloween_wreath_sash.jpeg", "mimeType": "image/jpeg"}
            ],
            "_selected_attachment_ids": ["att-sash"],
        }

        items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)
        shots = self.service._flow_operator_product_rule_shot_suite("halloween_wreath_sash")

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Halloween Wreath Sash category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Halloween Wreath Sash", item["prompt"])
        self.assertEqual(
            "Halloween Wreath Sash image 1 Hands embroidering Halloween design on linen",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "Halloween Wreath Sash image 12 Sash tied around dark wooden banister post",
            item["shot_labels"][-1],
        )
        self.assertIn("exactly at the 6 o'clock position", item["prompt"])
        self.assertIn("never printed, digitally applied, machine embroidered, or machine-flat", item["prompt"])
        self.assertIn("This is the only output in the set that may be a collage", item["prompt"])
        self.assertIn("never a bow", item["prompt"])

    def test_auto_trello_uses_family_halloween_sash_shot_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        card = {
            "id": "card-family-halloween-sash",
            "shortLink": "family-halloween-sash",
            "idList": "ready",
            "name": "Family Halloween Sash",
            "url": "https://trello.example/c/family-halloween-sash",
            "_image_attachments": [
                {"id": "att-sash", "name": "family_halloween_wreath_sash.jpeg", "mimeType": "image/jpeg"}
            ],
            "_selected_attachment_ids": ["att-sash"],
        }

        items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)
        shots = self.service._flow_operator_product_rule_shot_suite("family_halloween_sash")

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual(12, len(shots))
        self.assertEqual(12, item["flow_agent_image_count"])
        self.assertIn("Family Halloween Sash category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Family Halloween Sash", item["prompt"])
        self.assertEqual(
            "Family Halloween Sash image 1 Hands embroidering matching Halloween sash linen",
            item["shot_labels"][0],
        )
        self.assertEqual(
            "Family Halloween Sash image 12 Three neutral linen sash colorways on wooden table",
            item["shot_labels"][-1],
        )
        self.assertIn("never printed, digitally applied, machine embroidered, or machine-flat", item["prompt"])
        self.assertIn("same total length, tail width, and knot size", item["prompt"])
        self.assertIn("clearly longer than the wreath diameter", item["prompt"])
        self.assertIn("exactly at the 6 o'clock position", item["prompt"])
        self.assertIn("physically mounted flat against that surface with a hidden hook", item["prompt"])
        self.assertNotIn("Four-panel embroidery weave hem and knot macro proof", " ".join(item["shot_labels"]))
        self.assertNotIn("Create one square 2x2 grid", item["prompt"])
        self.assertIn("This must be one standalone lifestyle photograph, never a collage", item["prompt"])
        self.assertNotIn("Maple leaf wreath on dark front door at night", " ".join(item["shot_labels"]))
        self.assertNotIn("Pumpkin maple leaf wreath above dark console", " ".join(item["shot_labels"]))
        self.assertIn("Sash tied around dark wooden banister post", " ".join(item["shot_labels"]))
        self.assertIn("Three neutral sash colorways on side-by-side fall wreaths", " ".join(item["shot_labels"]))
        self.assertIn("three different neutral linen base colors", item["prompt"])
        self.assertIn("Do not change the motif design, motif colors, or sash borders", item["prompt"])
        self.assertIn("Welcome", item["prompt"])
        self.assertIn("Planned prop text exception", item["prompt"])
        self.assertIn("no landscape crop, portrait crop, contact sheet, grid, or multiple-frame canvas", item["prompt"])
        self.assertNotIn("Wreath Sash category", item["design_analysis"])

    def test_auto_trello_ring_bearer_pillow_does_not_fallback_to_wedding_pillowcase(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        card = {
            "id": "card-ring-bearer-pillow",
            "shortLink": "ring-bearer-pillow",
            "idList": "ready",
            "name": "Ring Bearer Pillow",
            "url": "https://trello.example/c/ring-bearer-pillow",
            "desc": (
                "AI Suggested Etsy Title:\n"
                "Personalized Leaf Wreath Ring Bearer Pillow, Custom Wedding Ceremony Pillow, "
                "Embroidered Linen Ring Cushion\n\n"
                "AI Product Type:\nRing Bearer Pillow"
            ),
            "_image_attachments": [{"id": "att-ring", "name": "Tao_anh_goi_dung_nhan.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["att-ring"],
        }

        signals = self.service._flow_operator_card_product_signals(request, card)
        items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)

        self.assertEqual("ring_bearer_pillow", signals["text_product_rule_key"])
        self.assertEqual("ring_bearer_pillow", signals["product_rule_key"])
        self.assertEqual(1, len(items))
        item = items[0]
        self.assertIn("Ring Bearer Pillow category", item["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Ring Bearer Pillow", item["prompt"])
        self.assertTrue(item["shot_labels"][0].startswith("Ring Bearer Pillow image 1 "))
        self.assertNotIn("Wedding Pillowcase category", item["design_analysis"])
        self.assertFalse(any(label.startswith("Wedding Pillowcase image") for label in item["shot_labels"]))

    def test_auto_trello_clear_card_name_overrides_wrong_visual_product_rule(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12)
        card = {
            "id": "card-name-wins",
            "shortLink": "card-name-wins",
            "idList": "ready",
            "name": "Ring Bearer Pillow",
            "url": "https://trello.example/c/card-name-wins",
            "_image_attachments": [{"id": "att-ring", "name": "source.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["att-ring"],
            "_visual_product_rule_key": "wedding_pillowcase",
            "_visual_product_rule_confidence": 0.94,
            "_visual_product_rule_visible_product": "square wedding cushion",
        }

        signals = self.service._flow_operator_card_product_signals(request, card)
        items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)

        self.assertEqual("ring_bearer_pillow", signals["card_name_product_rule_key"])
        self.assertEqual("ring_bearer_pillow", signals["product_rule_key"])
        self.assertIn("Ring Bearer Pillow category", items[0]["design_analysis"])
        self.assertNotIn("Wedding Pillowcase category", items[0]["design_analysis"])

    def test_auto_trello_prioritizes_specific_havi_pillowcase_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4, prompt="Wedding Pillowcase")
        cards = [
            {
                "id": "card-wedding-pillow",
                "shortLink": "wedding-pillow",
                "idList": "ready",
                "name": "Wedding_Pillowcase_Bride_Groom_202605261200.jpeg",
                "url": "https://trello.example/c/wedding-pillow",
                "_image_attachments": [{"id": "att-pillow", "name": "wedding_pillowcase.jpeg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["att-pillow"],
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertIn("Wedding Pillowcase category", item["design_analysis"])
        self.assertEqual("Wedding Pillowcase image 1 Cô dâu ôm/cầm gối", item["shot_labels"][0])
        self.assertIn("two pillows neatly arranged", item["prompt"])
        self.assertNotIn("Mẹ bế bé + gối thêu tên", item["prompt"])

    def test_flow_agent_multi_image_prompt_allows_only_pennant_detail_collage(self) -> None:
        base = (
            "Required shot plan: "
            "1. Pennant image 1 baby room flag scene: one single pennant. "
            "7. Pennant image 7 four-panel embroidery close-up collage: one single 1:1 square image made of four small close-up panels."
        )

        prompt = self.service._flow_agent_multi_image_prompt(base, 12)

        self.assertIn("image 7 may be one 1:1 four-panel close-up collage", prompt)
        self.assertIn("the only exception is the Required shot plan's image 7", prompt)
        self.assertIn("Follow the Required shot plan already written in the base brief exactly", prompt)
        self.assertNotIn("Do NOT create a 12-frame grid, contact sheet, collage, storyboard", prompt)

    def test_flow_agent_multi_image_prompt_locks_second_split_to_required_items_9_12(self) -> None:
        base = (
            "Required shot plan: "
            "1. Pennant image 1 baby room flag scene: one single pennant.; "
            "2. Pennant image 2 alternate nursery corner: one single pennant.; "
            "3. Pennant image 3 two hanging color variants: two pennants.; "
            "4. Pennant image 4 two tabletop color variants: two pennants.; "
            "5. Pennant image 5 three nursery color variants: three pennants.; "
            "6. Pennant image 6 four nursery color variants: four pennants.; "
            "7. Pennant image 7 four-panel embroidery close-up collage: four panels.; "
            "8. Pennant image 8 woman embroidering in hoop: hoop as tool.; "
            "9. Pennant image 9 mother and baby touch embroidery: mother and baby touch stitches.; "
            "10. Pennant image 10 two babies touch two pennants: faces not visible.; "
            "11. Pennant image 11 sleeping baby room scene: baby sleeping near crib.; "
            "12. Pennant image 12 flat gift box presentation: folded flat in open box. "
            "Lighting and color rule for every output: clean white daylight."
        )

        prompt = self.service._flow_agent_multi_image_prompt(base, 4, shot_offset=8, full_total=12)

        self.assertIn("CURRENT UI PASS SHOT RANGE: create ONLY Required shot plan items 9-12", prompt)
        self.assertIn("Do not create, summarize, repeat, or restart Required shot plan items 1-8", prompt)
        self.assertIn("Pennant image 9 mother and baby touch embroidery", prompt)
        self.assertIn("Pennant image 12 flat gift box presentation", prompt)
        self.assertIn("not as a new set starting at image 1", prompt)
        self.assertIn("does not reset the numbered shot range", prompt)

    def test_auto_trello_generic_tao_filename_skips_without_product_rule(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4)
        card = {
            "id": "card-generic",
            "shortLink": "generic",
            "idList": "ready",
            "name": "tạo_hình_ảnh_một_chiếc_202605161423 (1).jpeg",
            "url": "https://trello.example/c/generic",
            "_image_attachments": [{"id": "att-generic", "name": "tạo_hình_ảnh_một_chiếc_202605161423 (1).jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["att-generic"],
        }

        signals = self.service._flow_operator_card_product_signals(request, card)

        self.assertFalse(signals["is_shirt"])
        items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)

        self.assertEqual([], items)
        self.assertEqual("missing_product_rule", card["_auto_trello_skip_code"])
        self.assertIn("HAVI product shot rule", card["_auto_trello_skip_reason"])
        self.assertIn("bo qua card nay", card["_auto_trello_skip_reason"])

    def test_auto_trello_baby_photo_frame_uses_hoop_rules(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4)
        card = {
            "id": "card-baby-frame",
            "shortLink": "baby-frame",
            "idList": "ready",
            "name": "khung dung anh baby",
            "url": "https://trello.example/c/baby-frame",
            "_image_attachments": [{"id": "att-frame", "name": "source.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["att-frame"],
        }

        signals = self.service._flow_operator_card_product_signals(request, card)
        items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)

        self.assertEqual("hoops_with_photos", signals["product_rule_key"])
        self.assertEqual(1, len(items))
        self.assertNotIn("_auto_trello_skip_code", card)
        self.assertIn("Hoops With Photos category", items[0]["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Hoops With Photos", items[0]["prompt"])
        self.assertTrue(items[0]["shot_labels"][0].startswith("Hoops With Photos image 1 "))

    def test_auto_trello_skips_unknown_rule_card_when_later_card_is_valid(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4)
        generic_card = {
            "id": "card-generic",
            "shortLink": "generic",
            "idList": "ready",
            "name": "tao_hinh_image_202605161423.jpeg",
            "url": "https://trello.example/c/generic",
            "_image_attachments": [{"id": "att-generic", "name": "image.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["att-generic"],
        }
        dress_card = {
            "id": "card-dress",
            "shortLink": "dress",
            "idList": "ready",
            "name": "Dress Baby linen product",
            "url": "https://trello.example/c/dress",
            "_image_attachments": [{"id": "att-dress", "name": "dress_baby.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["att-dress"],
        }

        items = self.service._trello_ai_prompt_items_for_image_cards([generic_card, dress_card], request, 1)

        self.assertEqual(1, len(items))
        self.assertEqual("card-dress", items[0]["trello_card_id"])
        self.assertIn("HAVI product shot rule lock: Dress Baby", items[0]["prompt"])

    def test_auto_trello_scan_reports_skipped_unknown_rule_card_without_failing(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="",
            trello_board_id="board123",
            trello_list_id="ready-list",
        )
        generic_card = {
            "id": "card-generic",
            "shortLink": "generic",
            "idList": "ready-list",
            "name": "tao_hinh_image_202605161423.jpeg",
            "url": "https://trello.example/c/generic",
            "_image_attachments": [{"id": "att-generic", "name": "image.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["att-generic"],
        }

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=[generic_card],
        ), patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ):
            items, discovery = self.service._trello_prompt_items_for_image_cards(request, [], 1)

        self.assertEqual([], items)
        self.assertEqual(1, discovery["skipped_missing_product_rule_cards"])
        self.assertEqual(["card-generic"], discovery["skipped_missing_product_rule_card_ids"])
        self.assertIn("HAVI product shot rule", discovery["skipped_missing_product_rule_details"][0])

    def test_auto_trello_scan_reports_and_skips_complete_card(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="",
            trello_board_id="board123",
            trello_list_id="ready-list",
        )
        complete_card = {
            "id": "card-complete",
            "shortLink": "complete",
            "idList": "ready-list",
            "name": "halloween wreath sash",
            "url": "https://trello.example/c/complete",
            "_image_attachments": [{"id": "source", "name": "source.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["source"],
            "_flow_output_count": 12,
        }

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=[complete_card],
        ), patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ):
            items, discovery = self.service._trello_prompt_items_for_image_cards(request, [], 1)

        self.assertEqual([], items)
        self.assertEqual(1, discovery["skipped_complete_cards"])
        self.assertEqual(["card-complete"], discovery["skipped_complete_card_ids"])
        self.assertEqual("complete_output_set", complete_card["_auto_trello_skip_code"])

    def test_auto_trello_generic_card_uses_visual_product_rule_instead_of_fallback(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4)
        card = {
            "id": "card-generic-dress",
            "shortLink": "generic-dress",
            "idList": "ready",
            "name": "Full-length_professional_product_photography_of_202605281034.jpeg",
            "url": "https://trello.example/c/generic-dress",
            "_image_attachments": [{"id": "att-dress", "name": "source.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["att-dress"],
            "_visual_product_rule_key": "dress_baby",
            "_visual_product_rule_confidence": 0.91,
            "_visual_product_rule_visible_product": "baby linen dress",
        }

        items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)

        self.assertEqual(1, len(items))
        self.assertIn("Dress Baby category", items[0]["design_analysis"])
        self.assertIn("Visual source classification as Dress Baby", items[0]["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Dress Baby", items[0]["prompt"])
        self.assertTrue(items[0]["shot_labels"][0].startswith("Dress Baby image 1 "))
        self.assertNotIn("Detail craft proof", items[0]["shot_labels"])

    def test_auto_trello_generic_card_infers_dress_rule_from_visual_description(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4)
        card = {
            "id": "6a17f150f691950be79b94a8",
            "shortLink": "generic-visual-dress",
            "idList": "ready",
            "name": "Full-length_professional_product_photography_of_202605281034.jpeg",
            "url": "https://trello.example/c/generic-visual-dress",
            "_image_attachments": [{"id": "6a17f150f691950be79b95d2", "name": "source.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["6a17f150f691950be79b95d2"],
        }

        with patch.object(self.service, "_gemini_api_key", return_value="gemini-key"), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("trello-key", "trello-token"),
        ), patch.object(
            self.service,
            "_trello_download_attachment_bytes",
            return_value=(b"image", "image/jpeg"),
        ), patch.object(
            self.service,
            "_gemini_classify_trello_source_product_rule",
            return_value={
                "product_rule_key": "",
                "confidence": 0.62,
                "visible_product": "white linen sleeveless child dress on a hanger with ruffled sleeves and skirt",
                "reason": "The main product is a small child garment with a bodice, skirt, pocket, and flutter sleeves.",
            },
        ):
            items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)

        self.assertEqual(1, len(items))
        self.assertEqual("dress_baby", card["_visual_product_rule_key"])
        self.assertIn("Dress Baby category", items[0]["design_analysis"])
        self.assertIn("Visual source classification as Dress Baby", items[0]["design_analysis"])
        self.assertIn("HAVI product shot rule lock: Dress Baby", items[0]["prompt"])
        self.assertTrue(items[0]["shot_labels"][0].startswith("Dress Baby image 1 "))
        self.assertNotIn("Detail craft proof", items[0]["shot_labels"])

    def test_visual_product_rule_maps_photo_album_to_album(self) -> None:
        parsed = self.service._flow_operator_product_rule_from_visual_payload(
            {
                "product_rule_key": "",
                "confidence": 0.62,
                "visible_product": "fabric covered wedding photo album scrapbook with embroidered cover",
                "reason": "The main object is a handmade keepsake album with a linen cover.",
            }
        )

        self.assertEqual("album", parsed["product_rule_key"])
        self.assertTrue(parsed["inferred_from_visual_text"])

    def test_visual_product_rule_infers_all_havi_products_from_visual_description(self) -> None:
        examples = {
            "wedding_pillowcase": "square cushion embroidered with bride and groom names for a romantic wedding keepsake",
            "tooth_fairy_pillow": "tooth-shaped cream linen tooth fairy pillow with a white ribbon hanger and hand embroidered name for a first tooth keepsake",
            "christmas_pillowcase": "Christmas baby pillowcase with raised wool embroidery, optional four corner pompoms, and festive nursery styling",
            "halloween_pillow": "soft baby pillow with wool embroidered pumpkin ghost motif for a Halloween nursery crib",
            "baby_pillowcase": "soft rectangular cushion with nursery name embroidery for an infant crib",
            "linen_pillowcase": "rectangular cushion cover made from linen fabric with embroidery for home decor sofa styling",
            "ring_bearer_pillow": "small square cushion with ribbons holding wedding rings for the ceremony",
            "hoops_with_photos": "round wooden embroidery frame containing a baby portrait photo with stitched name and date",
            "wedding_hoop": "round wooden embroidery frame with floral stitched couple names for wedding decor",
            "bride_handkerchief": "embroidered bridal cloth square folded with lace edge for wedding tears keepsake",
            "halloween_notebook": "fabric covered Halloween recipe notebook embroidered with pumpkins ghosts and autumn leaves",
            "vows_book": "small fabric covered booklet for personal vows with embroidered cover lettering",
            "baby_christmas_album": "cotton linen baby Christmas photo album with hand embroidered cover, clear plastic photo pockets, Santa ornament evergreen and gingerbread decor",
            "christmas_album": "hand embroidered cotton linen Christmas photo album with Christmas tree motif, clear photo pockets, festive ornaments and dried orange decor",
            "baby_album": "cotton linen baby photo album for a first birthday with hand embroidered cover and clear plastic photo pockets",
            "album": "hand embroidered linen photo album with a fabric cover, bound spine, and clear plastic photo pockets",
            "notebook": "hand embroidered linen fabric covered notebook with bound paper pages and a stitched cover motif",
            "guest_book": "fabric covered embroidered guest book for wedding guests to sign",
            "bouquet_ribbon": "long fabric strip tied to a bridal bouquet with stitched lettering",
            "christmas_sash": "handmade Christmas wreath sash with two pointed linen tails, raised embroidery and text tied below an evergreen wreath with red berries",
            "family_halloween_sash": "family Halloween wreath sash with two pointed white linen tails, embroidered ghost motif and text tied to a maple leaf wreath",
            "halloween_wreath_sash": "handmade Halloween wreath sash with two long pointed linen tails and raised pumpkin embroidery tied at the bottom center of a dark twig wreath",
            "wreath_sash": "two long pointed linen wreath sash tails tied around a green wreath with floral embroidery and an initial",
            "hair_bow": "cotton linen embroidered hair bow scrunchie with center knot and long tails for a ponytail",
            "passport_cover": "cotton linen passport cover holder with hand embroidered travel motif beside a boarding pass",
            "pc_stocks": "compact hanging Christmas stocking with white cuff, heel, toe, hanging loop, and thick raised punch needle wool yarn motif",
            "pn_ornament": "small Christmas linen ornament in a wooden hoop with metal clasp, hanging cord, and thick raised punch needle wool loop pile motif",
            "ornament_round": "small round Christmas tree ornament with linen in a wooden mini hoop, metal clasp, hanging cord, and raised hand embroidery",
            "jewelry_box": "collection of small rounded rectangular silver framed jewelry boxes with white linen hand embroidered lids, front clasps, and exactly two interior compartments",
            "napkin_set": "set of six white linen dinner napkins with six distinct hand embroidered autumn flowers leaves and acorns",
            "advent_calendar": "tall linen Christmas advent countdown wall hanging with numbered pockets, a wooden dowel, hanging cord, and hand embroidery",
            "halloween_bag": "small linen Halloween trick-or-treat candy bag with one handle and hand embroidered pumpkin motif",
            "drawstring_bag": "cotton linen drawstring pouch with rope cords, gathered top, and hand embroidered lavender motif",
            "christmas_banner": "small Christmas linen wall banner with wooden hanging rod, cord hanger, raised hand embroidery, and Noel decor",
            "halloween_banner": "small Halloween linen wall banner with wooden hanging rod, cord, and raised hand embroidery",
            "banner": "flat triangular nursery wall hanging with top wooden dowel cord hanger and pointed V bottom",
            "birthday_hat": "hand embroidered linen birthday hat with tie strings, pom-pom details, ruffle trim, and birthday party styling",
            "crown": "soft fabric birthday crown made of linen with pom-pom tips and embroidered details for a baby party",
            "christmas_fabric_cross": "soft sewn Christmas fabric cross keepsake made of linen with raised hand embroidery, a hanging loop, and pine decor",
            "fabric_cross": "soft sewn religious cross keepsake made of linen with embroidered name",
            "christmas_dress_baby": "Christmas baby linen dress with a white collar, ruffled shoulders, hand embroidery, and two wooden back buttons",
            "halloween_dress_baby": "Halloween baby linen dress with ruffled shoulders, hand embroidery, and two wooden back buttons",
            "dress_baby": "white linen sleeveless child dress on a hanger with ruffled sleeves and skirt",
            "plush": "soft stuffed animal toy bear with fabric pile seams and stitched face",
        }

        self.assertEqual(set(PRODUCT_SHOT_RULES), set(examples))
        for product_key, visual_text in examples.items():
            with self.subTest(product_key=product_key):
                parsed = self.service._flow_operator_product_rule_from_visual_payload(
                    {
                        "product_rule_key": "",
                        "confidence": 0.62,
                        "visible_product": visual_text,
                        "reason": "The main object is visible.",
                    }
                )

                self.assertEqual(product_key, parsed["product_rule_key"])
                self.assertTrue(parsed["inferred_from_visual_text"])

    def test_visual_product_rule_overrides_fabric_cross_when_visible_product_is_crown(self) -> None:
        parsed = self.service._flow_operator_product_rule_from_visual_payload(
            {
                "product_rule_key": "fabric_cross",
                "confidence": 1.0,
                "visible_product": "fabric crown with embroidery and pom-poms",
                "reason": "The main object is a soft linen birthday crown accessory with pointed tips.",
            }
        )

        self.assertEqual("crown", parsed["product_rule_key"])
        self.assertTrue(parsed["inferred_from_visual_text"])

    def test_visual_product_rule_does_not_infer_dress_from_excluded_product_form(self) -> None:
        payload = {
            "product_rule_key": "",
            "confidence": 0.9,
            "visible_product": "embroidered pillow with a baby dress motif",
            "reason": "The main object is a square pillow.",
        }

        parsed = self.service._flow_operator_product_rule_from_visual_payload(payload)

        self.assertNotEqual("dress_baby", parsed["product_rule_key"])

    def test_auto_trello_partial_card_generates_full_twelve_image_set(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4)
        cards = [
            {
                "id": "partial-card",
                "shortLink": "partial",
                "idList": "ready",
                "name": "embroidered apron",
                "url": "https://trello.example/c/partial",
                "_image_attachments": [{"id": "source-att", "name": "source.jpg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["source-att"],
                "_flow_output_count": 2,
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        self.assertEqual(12, items[0]["flow_agent_image_count"])
        self.assertEqual(2, items[0]["flow_agent_existing_output_count"])
        self.assertEqual(["source-att"], items[0]["trello_attachment_ids"])
        self.assertIn("already has 2/12 Flow output", items[0]["prompt"])
        self.assertIn("fresh full 12-image set", items[0]["prompt"])
        self.assertIn("do not subtract any existing output attachments", items[0]["prompt"])
        self.assertNotIn("Continue the same set by creating exactly 9 new missing image", items[0]["prompt"])

    def test_auto_trello_fresh_ready_card_generates_full_twelve_image_set(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4)
        cards = [
            {
                "id": "complete-card",
                "shortLink": "complete",
                "idList": "ready",
                "name": "embroidered pillowcase",
                "url": "https://trello.example/c/complete",
                "_image_attachments": [{"id": "source-att", "name": "source.jpg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["source-att"],
                "_flow_output_count": 0,
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        self.assertEqual(12, items[0]["flow_agent_image_count"])
        self.assertEqual(0, items[0]["flow_agent_existing_output_count"])
        self.assertEqual(["source-att"], items[0]["trello_attachment_ids"])
        self.assertIn("generate exactly 12", items[0]["prompt"])
        self.assertIn("clean clear white neutral daylight", items[0]["prompt"])
        self.assertIn("no yellow/orange/golden/tungsten", items[0]["prompt"])
        self.assertIn("Every output must make stitched or embroidered areas look genuinely hand embroidered", items[0]["prompt"])
        self.assertIn("tack-sharp around the embroidered areas", items[0]["prompt"])
        self.assertIn("make the hand-embroidery technique obvious", items[0]["prompt"])
        self.assertIn("Only if the source image visibly contains an embroidered/personalized name", items[0]["prompt"])
        self.assertIn("Colorway text/name rule", items[0]["prompt"])
        self.assertIn("each differently colored product variant must use a different plausible name/text", items[0]["prompt"])
        self.assertIn("If the source has no embroidered name, keep all variants nameless", items[0]["prompt"])
        self.assertIn("12 generated output images plus the 1 source image", items[0]["prompt"])
        self.assertEqual(
            [
                "Embroidery craft proof",
                "Nursery hero arrangement",
                "Lifestyle baby room scene",
                "Gift box presentation",
                "Flat lay motif story",
                "Collection variation scene",
                "Hands embroidering pillowcase",
                "Personalized detail vignette",
                "Pastel fabric colorway lineup",
                "Crib colorway trio",
                "Pastel swatch flat lay",
                "Color option display",
            ],
            items[0]["shot_labels"],
        )

    def test_auto_trello_eight_output_card_generates_full_twelve_image_set(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4)
        cards = [
            {
                "id": "complete-card",
                "shortLink": "complete",
                "idList": "ready",
                "name": "embroidered pillowcase",
                "url": "https://trello.example/c/complete",
                "_image_attachments": [{"id": "source-att", "name": "source.jpg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["source-att"],
                "_flow_output_count": 8,
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        self.assertEqual(12, items[0]["flow_agent_image_count"])
        self.assertEqual(8, items[0]["flow_agent_existing_output_count"])
        self.assertIn("already has 8/12 Flow output", items[0]["prompt"])
        self.assertIn("fresh full 12-image set", items[0]["prompt"])
        self.assertNotIn("Continue the same set by creating exactly 4 new missing image", items[0]["prompt"])
        self.assertEqual(
            [
                "Embroidery craft proof",
                "Nursery hero arrangement",
                "Lifestyle baby room scene",
                "Gift box presentation",
                "Flat lay motif story",
                "Collection variation scene",
                "Hands embroidering pillowcase",
                "Personalized detail vignette",
                "Pastel fabric colorway lineup",
                "Crib colorway trio",
                "Pastel swatch flat lay",
                "Color option display",
            ],
            items[0]["shot_labels"],
        )
        self.assertIn("Only if the source image visibly has an embroidered/personalized name", items[0]["prompt"])
        self.assertIn("Colorway text/name rule", items[0]["prompt"])
        self.assertIn("never repeat the exact same readable name/text across all color variants", items[0]["prompt"])
        self.assertIn("otherwise all options must remain nameless", items[0]["prompt"])

    def test_auto_trello_ten_output_card_generates_full_twelve_image_set(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4)
        cards = [
            {
                "id": "nearly-complete-card",
                "shortLink": "nearly",
                "idList": "ready",
                "name": "embroidered pillowcase",
                "url": "https://trello.example/c/nearly",
                "_image_attachments": [{"id": "source-att", "name": "source.jpg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["source-att"],
                "_flow_output_count": 10,
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        self.assertEqual(12, items[0]["flow_agent_image_count"])
        self.assertEqual(10, items[0]["flow_agent_existing_output_count"])
        self.assertIn("already has 10/12 Flow output", items[0]["prompt"])
        self.assertIn("fresh full 12-image set", items[0]["prompt"])
        self.assertNotIn("Continue the same set by creating exactly 2 new missing image", items[0]["prompt"])
        self.assertIn("source image is not a generated output", items[0]["prompt"])
        self.assertEqual(12, len(items[0]["shot_labels"]))
        self.assertEqual("Embroidery craft proof", items[0]["shot_labels"][0])
        self.assertEqual("Color option display", items[0]["shot_labels"][-1])

    def test_auto_trello_hoop_uses_name_variants_instead_of_colorways(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=4)
        cards = [
            {
                "id": "hoop-card",
                "shortLink": "hoop",
                "idList": "ready",
                "name": "wedding hoop personalized embroidery",
                "url": "https://trello.example/c/hoop",
                "_image_attachments": [{"id": "source-att", "name": "wedding_hoop_emma.jpg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["source-att"],
                "_flow_output_count": 0,
            }
        ]

        items = self.service._trello_ai_prompt_items_for_image_cards(cards, request, 40)

        self.assertEqual(1, len(items))
        self.assertEqual(12, items[0]["flow_agent_image_count"])
        self.assertIn("Wedding Hoop category", items[0]["design_analysis"])
        self.assertNotIn("Pastel fabric colorway lineup", items[0]["shot_labels"])
        self.assertNotIn("Color option display", items[0]["shot_labels"])
        self.assertEqual(
            [
                "Wedding Hoop image 1 Flat display — thêu hoa",
                "Wedding Hoop image 2 Cận thêu tay",
                "Wedding Hoop image 3 Giữa vest chú rể & áo cô dâu",
                "Wedding Hoop image 4 Cô dâu đứng cầm showcase",
                "Wedding Hoop image 5 4 vòng trên voile trắng",
                "Wedding Hoop image 6 Gift box",
                "Wedding Hoop image 7 Tay thêu — process lifestyle",
                "Wedding Hoop image 8 Đôi uyên ương cầm #1",
                "Wedding Hoop image 9 2 vòng tên khác — trên gỗ",
                "Wedding Hoop image 10 Treo trên móc tường",
                "Wedding Hoop image 11 Flat — cận chi tiết thêu #2",
                "Wedding Hoop image 12 Kệ nhỏ ngoài trời — reception",
            ],
            items[0]["shot_labels"],
        )
        self.assertIn("HAVI product shot rule lock", items[0]["prompt"])
        self.assertIn("Two identical rings with different names", items[0]["prompt"])
        self.assertIn("If the source has no embroidered name", items[0]["prompt"])

    def test_project_generated_images_extracts_new_flow_media(self) -> None:
        project_data = {
            "projectContents": {
                "workflows": [
                    {
                        "name": "wf-old",
                        "projectId": "pid",
                        "metadata": {"displayName": "Old prompt", "createTime": "2026-05-15T08:00:00Z"},
                        "medias": [
                            {
                                "name": "old-media",
                                "projectId": "pid",
                                "image": {"generatedImage": {"fifeUrl": "https://example.com/old.jpg"}},
                            }
                        ],
                    },
                    {
                        "name": "wf-video",
                        "projectId": "pid",
                        "metadata": {"displayName": "Video item", "createTime": "2026-05-15T08:02:00Z"},
                        "medias": [{"name": "video-media", "video": {"encodedVideo": {"url": "https://example.com/v.mp4"}}}],
                    },
                    {
                        "name": "wf-new",
                        "projectId": "pid",
                        "metadata": {"displayName": "New prompt", "createTime": "2026-05-15T08:01:00Z"},
                        "medias": [
                            {
                                "name": "new-media",
                                "projectId": "pid",
                                "dimensions": {"width": 1024, "height": 1024},
                                "image": {
                                    "generatedImage": {
                                        "fifeUrl": "https://example.com/new.jpg",
                                        "prompt": "Generated prompt",
                                        "seed": 7,
                                        "modelNameType": "NARWHAL",
                                    }
                                },
                            }
                        ],
                    },
                ]
            }
        }

        images = self.service._project_generated_images(project_data, known_media={"old-media"}, prompt="Fallback prompt")

        self.assertEqual(1, len(images))
        self.assertEqual("new-media", images[0].media_name)
        self.assertEqual("wf-new", images[0].workflow_id)
        self.assertEqual("https://example.com/new.jpg", images[0].fife_url)
        self.assertEqual("Generated prompt", images[0].prompt)
        self.assertEqual({"width": 1024, "height": 1024}, images[0].dimensions)

    def test_trello_archive_skips_without_credentials(self) -> None:
        request = CreateJobRequest(type="image", prompt="cat")
        artifact = JobArtifact(label="Ảnh 1", url="https://example.com/cat.jpg", mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.dict(os.environ, {"TRELLO_API_KEY": "", "TRELLO_TOKEN": ""}, clear=False):
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        self.assertEqual({"configured": False}, result)

    def test_trello_archive_attaches_image_to_configured_card(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="cat",
            trello_card_id="https://trello.com/c/abc123/demo-card",
        )
        artifact = JobArtifact(label="Ảnh 1", media_name="media", url="https://example.com/cat.jpg", mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.dict(
            os.environ,
            {
                "TRELLO_API_KEY": "key",
                "TRELLO_TOKEN": "token",
                "TRELLO_CARD_ID": "",
                "TRELLO_LIST_ID": "",
                "TRELLO_UPLOAD_MODE": "url",
            },
            clear=False,
        ), patch.object(
            self.service,
            "_trello_attach_url",
            return_value={"id": "att-1", "name": "flow-cat.jpg", "url": "https://trello.example/att-1"},
        ) as attach_url:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        attach_url.assert_called_once()
        self.assertEqual("abc123", attach_url.call_args.args[2])
        self.assertFalse(attach_url.call_args.args[5])
        self.assertTrue(result["configured"])
        self.assertEqual(1, result["sent"])
        self.assertEqual(0, result["failed"])
        self.assertEqual("abc123", result["card_id"])

    def test_trello_archive_moves_card_to_content_review_after_twelve_outputs(self) -> None:
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    board_id="board123",
                    card_id="https://trello.com/c/abc123/demo-card",
                    upload_mode="url",
                )
            )
        )
        request = CreateJobRequest(
            type="image",
            prompt="cat",
            trello_board_id="board123",
            trello_card_id="https://trello.com/c/abc123/demo-card",
        )
        artifacts = [
            JobArtifact(label=f"Anh {index + 1}", media_name=f"media-{index}", url=f"https://example.com/cat-{index}.jpg", mime_type="image/jpeg")
            for index in range(12)
        ]
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.object(
            self.service,
            "_trello_attach_url",
            side_effect=[
                {"id": f"att-{index}", "name": f"flow-test-{index}.jpg", "url": f"https://trello.example/att-{index}"}
                for index in range(12)
            ],
        ) as attach_url, patch.object(
            self.service,
            "_trello_image_card_by_id",
            return_value={
                "id": "abc123",
                "name": "demo-card",
                "_image_attachments": [{"id": "source", "name": "source.png", "mimeType": "image/png"}],
                "_flow_output_count": 12,
            },
        ) as image_card, patch.object(
            self.service,
            "_trello_card_flow_output_count",
            return_value=12,
        ) as output_count, patch.object(
            self.service,
            "_trello_content_review_list_id",
            return_value="review-list",
        ) as review_list, patch.object(
            self.service,
            "_trello_move_card_to_list",
            return_value={"id": "abc123", "idList": "review-list", "url": "https://trello.example/c/abc123"},
        ) as move_card:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, artifacts))

        self.assertEqual(12, attach_url.call_count)
        image_card.assert_called_once_with("key", "token", "abc123")
        output_count.assert_not_called()
        review_list.assert_called_once_with("key", "token", "board123", "Content Review")
        move_card.assert_called_once_with("key", "token", "abc123", "review-list")
        self.assertEqual(12, result["sent"])
        self.assertTrue(result["content_review"]["moved"])
        self.assertEqual("review-list", result["content_review"]["list_id"])
        saved = self.store.get_job(job.id)
        messages = [entry.message for entry in saved.logs]
        self.assertIn("Đang upload 12 ảnh kết quả lên Trello.", messages)
        self.assertIn("Đang upload ảnh 1/12 lên Trello.", messages)
        self.assertIn("Đã upload ảnh 12/12 lên Trello.", messages)
        self.assertEqual("Đã upload 12/12 ảnh lên Trello.", saved.progress_hint.detail)

    def test_trello_archive_moves_partial_card_when_total_outputs_reaches_twelve(self) -> None:
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    board_id="board123",
                    card_id="https://trello.com/c/abc123/demo-card",
                    upload_mode="url",
                )
            )
        )
        request = CreateJobRequest(
            type="image",
            prompt="cat",
            trello_board_id="board123",
            trello_card_id="https://trello.com/c/abc123/demo-card",
        )
        artifacts = [
            JobArtifact(label=f"Anh {index + 1}", media_name=f"media-{index}", url=f"https://example.com/cat-{index}.jpg", mime_type="image/jpeg")
            for index in range(4)
        ]
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.object(
            self.service,
            "_trello_attach_url",
            side_effect=[
                {"id": f"att-{index}", "name": f"flow-test-{index}.jpg", "url": f"https://trello.example/att-{index}"}
                for index in range(4)
            ],
        ), patch.object(
            self.service,
            "_trello_image_card_by_id",
            return_value={
                "id": "abc123",
                "name": "demo-card",
                "_image_attachments": [{"id": "source", "name": "source.png", "mimeType": "image/png"}],
                "_flow_output_count": 12,
            },
        ) as image_card, patch.object(
            self.service,
            "_trello_card_flow_output_count",
            return_value=12,
        ) as output_count, patch.object(
            self.service,
            "_trello_content_review_list_id",
            return_value="review-list",
        ), patch.object(
            self.service,
            "_trello_move_card_to_list",
            return_value={"id": "abc123", "idList": "review-list", "url": "https://trello.example/c/abc123"},
        ) as move_card:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, artifacts))

        image_card.assert_called_once_with("key", "token", "abc123")
        output_count.assert_not_called()
        move_card.assert_called_once_with("key", "token", "abc123", "review-list")
        self.assertEqual(4, result["sent"])
        self.assertTrue(result["content_review"]["moved"])

    def test_trello_card_flow_output_count_excludes_original_source_image(self) -> None:
        attachments = [
            {"id": "source", "name": "original-source.png", "mimeType": "image/png"},
            *[
                {"id": f"flow-{index}", "name": f"flow-job123-{index}.jpg", "mimeType": "image/jpeg"}
                for index in range(1, 13)
            ],
        ]

        with patch.object(self.service, "_trello_get_json", return_value=attachments):
            output_count = self.service._trello_card_flow_output_count("key", "token", "abc123")

        self.assertEqual(12, output_count)

    def test_trello_move_card_to_list_places_card_at_top(self) -> None:
        with patch.object(
            self.service,
            "_trello_put_json",
            return_value={"id": "abc123", "idList": "review-list", "pos": 1},
        ) as put_card:
            result = self.service._trello_move_card_to_list("key", "token", "abc123", "review-list")

        put_card.assert_called_once_with(
            "cards/abc123",
            "key",
            "token",
            fields={"idList": "review-list", "pos": "top"},
        )
        self.assertEqual("abc123", result["id"])

    def test_trello_archive_does_not_create_new_card_when_source_attachment_has_no_card(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="cat",
            trello_list_id="ready-list",
            trello_attachment_ids=["source-att"],
        )
        artifact = JobArtifact(label="Ảnh 1", media_name="media", url="https://example.com/cat.jpg", mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.dict(
            os.environ,
            {
                "TRELLO_API_KEY": "key",
                "TRELLO_TOKEN": "token",
                "TRELLO_CARD_ID": "",
                "TRELLO_LIST_ID": "",
                "TRELLO_UPLOAD_MODE": "url",
            },
            clear=False,
        ), patch.object(
            self.service,
            "_trello_create_card",
        ) as create_card, patch.object(
            self.service,
            "_trello_attach_url",
        ) as attach_url:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        create_card.assert_not_called()
        attach_url.assert_not_called()
        self.assertEqual("source_card_missing", result["error"])
        self.assertEqual(0, result["sent"])
        self.assertEqual(1, result["failed"])

    def test_trello_archive_with_source_module_does_not_fallback_to_config_card(self) -> None:
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    card_id="https://trello.com/c/configcard/default-card",
                    list_id="ready-list",
                    upload_mode="url",
                )
            )
        )
        request = CreateJobRequest(
            type="image",
            prompt="cat",
            trello_list_id="ready-list",
            automation_graph={
                "modules": [
                    {"id": "trello-source-1", "type": "trello_source", "title": "Trello Image Source"},
                    {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    {"id": "trello-1", "type": "trello", "title": "Trello Archive"},
                ]
            },
        )
        artifact = JobArtifact(label="Anh 1", media_name="media", url="https://example.com/cat.jpg", mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.object(self.service, "_trello_create_card") as create_card, patch.object(
            self.service,
            "_trello_attach_url",
        ) as attach_url:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        create_card.assert_not_called()
        attach_url.assert_not_called()
        self.assertEqual("source_card_missing", result["error"])
        self.assertEqual(0, result["sent"])
        self.assertEqual(1, result["failed"])

    def test_trello_archive_blocks_upload_when_source_validation_fails(self) -> None:
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    card_id="https://trello.com/c/source123/source-card",
                    upload_mode="url",
                )
            )
        )
        request = CreateJobRequest(
            type="image",
            prompt="cat",
            trello_card_id="https://trello.com/c/source123/source-card",
            reference_image_paths=[str(self.uploads_dir / "source.jpg")],
            automation_graph={
                "modules": [
                    {"id": "trello-source-1", "type": "trello_source", "title": "Trello Image Source"},
                    {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    {"id": "trello-1", "type": "trello", "title": "Trello Archive"},
                ]
            },
        )
        artifact = JobArtifact(label="Anh 1", media_name="media", url="https://example.com/wrong.jpg", mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.object(
            self.service,
            "_validate_trello_source_artifacts_before_upload",
            new=AsyncMock(side_effect=RuntimeError("source mismatch")),
        ) as validate, patch.object(
            self.service,
            "_trello_attach_url",
        ) as attach_url:
            with self.assertRaisesRegex(RuntimeError, "source mismatch"):
                asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        validate.assert_awaited_once()
        attach_url.assert_not_called()

    def test_trello_archive_validates_source_before_uploading_generated_images(self) -> None:
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    card_id="https://trello.com/c/source123/source-card",
                    upload_mode="url",
                )
            )
        )
        request = CreateJobRequest(
            type="image",
            prompt="cat",
            trello_card_id="https://trello.com/c/source123/source-card",
            reference_image_paths=[str(self.uploads_dir / "source.jpg")],
            automation_graph={
                "modules": [
                    {"id": "trello-source-1", "type": "trello_source", "title": "Trello Image Source"},
                    {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    {"id": "trello-1", "type": "trello", "title": "Trello Archive"},
                ]
            },
        )
        artifact = JobArtifact(label="Anh 1", media_name="media", url="https://example.com/right.jpg", mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.object(
            self.service,
            "_validate_trello_source_artifacts_before_upload",
            new=AsyncMock(return_value=None),
        ) as validate, patch.object(
            self.service,
            "_trello_attach_url",
            return_value={"id": "att-1", "name": "flow-cat.jpg", "url": "https://trello.example/att-1"},
        ) as attach_url:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        validate.assert_awaited_once()
        attach_url.assert_called_once()
        self.assertEqual(1, result["sent"])

    def test_trello_archive_uses_locked_source_card_over_stale_target(self) -> None:
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    card_id="wrong-card",
                    upload_mode="file",
                    upscale_to_2k=False,
                )
            )
        )
        generated = self.downloads_dir / "generated.jpg"
        generated.write_bytes(b"generated-bytes")
        request = CreateJobRequest(
            type="image",
            prompt="cat",
            trello_card_id="wrong-card",
            trello_source_card_id="source-card",
            trello_source_attachment_ids=["source-att"],
        )
        artifact = JobArtifact(label="Anh 1", media_name="media", local_path=str(generated), mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.object(
            self.service,
            "_trello_attach_file_bytes",
            return_value={"id": "att-1", "name": "flow-cat.jpg", "url": "https://trello.example/att-1"},
        ) as attach_bytes:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        attach_bytes.assert_called_once()
        self.assertEqual("source-card", attach_bytes.call_args.args[2])
        self.assertEqual("source-card", result["card_id"])
        self.assertEqual("source-card", result["source_card_id"])
        self.assertEqual(["source-att"], result["source_attachment_ids"])

    def test_flow_upsample_payload_requests_2k_resolution(self) -> None:
        from PIL import Image

        calls: list[tuple[str, str, dict[str, Any]]] = []
        output_image = io.BytesIO()
        Image.new("RGB", (2048, 2048), (120, 160, 200)).save(output_image, format="JPEG")
        flow_2k_bytes = output_image.getvalue()
        encoded_output = base64.b64encode(flow_2k_bytes).decode("ascii")

        class FakeApi:
            async def _client_context(self) -> dict[str, Any]:
                return {
                    "projectId": "pid",
                    "tool": "PINHOLE",
                    "sessionId": ";123",
                    "recaptchaContext": {"token": "abc", "applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB"},
                }

            async def _fetch(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, str]:
                calls.append((method, path, payload))
                return {"encodedImage": encoded_output}

        client = SimpleNamespace(_api=FakeApi())
        result = asyncio.run(
            self.service._upsample_image_via_flow(
                client,
                b"source-bytes",
                media_generation_id="00000000-1111-2222-3333-444444444444",
                workflow_id="workflow-456",
                prompt="product prompt",
            )
        )

        self.assertEqual(flow_2k_bytes, result)
        self.assertEqual(1, len(calls))
        method, path, payload = calls[0]
        self.assertEqual("POST", method)
        self.assertEqual("flow/upsampleImage", path)
        self.assertEqual("00000000-1111-2222-3333-444444444444", payload["mediaId"])
        self.assertEqual("UPSAMPLE_IMAGE_RESOLUTION_2K", payload["targetResolution"])
        self.assertEqual("pid", payload["clientContext"]["projectId"])
        self.assertEqual("PINHOLE", payload["clientContext"]["tool"])
        self.assertEqual("abc", payload["clientContext"]["recaptchaContext"]["token"])

    def test_flow_upsample_downloads_media_response_when_no_encoded_bytes(self) -> None:
        from PIL import Image

        source_image = io.BytesIO()
        Image.new("RGB", (1024, 1024), (210, 180, 140)).save(source_image, format="JPEG")
        source_bytes = source_image.getvalue()
        flow_image = io.BytesIO()
        Image.new("RGB", (2048, 2048), (120, 160, 200)).save(flow_image, format="JPEG")
        flow_2k_bytes = flow_image.getvalue()
        calls: list[dict[str, Any]] = []
        downloads: list[str] = []

        class FakeApi:
            async def _client_context(self) -> dict[str, Any]:
                return {"projectId": "pid"}

            async def _fetch(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
                calls.append(payload)
                return {"media": {"name": "11111111-2222-3333-4444-555555555555"}}

        class FakeResponse:
            status = 200
            headers = {"content-type": "image/jpeg"}

            async def body(self) -> bytes:
                return flow_2k_bytes

        class FakeRequest:
            async def get(self, url: str) -> FakeResponse:
                downloads.append(url)
                return FakeResponse()

        client = SimpleNamespace(_api=FakeApi(), _bm=SimpleNamespace(context=SimpleNamespace(request=FakeRequest())))
        result = asyncio.run(
            self.service._upsample_image_via_flow(
                client,
                source_bytes,
                media_generation_id="00000000-1111-2222-3333-444444444444",
            )
        )

        self.assertEqual(1, len(calls))
        self.assertEqual(flow_2k_bytes, result)
        self.assertEqual(
            ["https://labs.google/fx/api/trpc/media.getMediaUrlRedirect?name=11111111-2222-3333-4444-555555555555"],
            downloads,
        )

    def test_flow_upsample_uses_ui_download_when_direct_api_returns_original(self) -> None:
        from PIL import Image

        source_image = io.BytesIO()
        Image.new("RGB", (1024, 1024), (210, 180, 140)).save(source_image, format="JPEG")
        source_bytes = source_image.getvalue()
        flow_image = io.BytesIO()
        Image.new("RGB", (2048, 2048), (120, 160, 200)).save(flow_image, format="JPEG")
        flow_2k_bytes = flow_image.getvalue()
        encoded_source = base64.b64encode(source_bytes).decode("ascii")

        class FakeApi:
            async def _client_context(self) -> dict[str, Any]:
                return {"projectId": "pid"}

            async def _fetch(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, str]:
                return {"encodedImage": encoded_source}

        client = SimpleNamespace(_api=FakeApi())

        with patch.object(
            self.service,
            "_upsample_image_via_flow_ui_download",
            new=AsyncMock(return_value=flow_2k_bytes),
        ) as ui_download:
            result = asyncio.run(
                self.service._upsample_image_via_flow(
                    client,
                    source_bytes,
                    media_generation_id="00000000-1111-2222-3333-444444444444",
                )
            )

        self.assertEqual(flow_2k_bytes, result)
        ui_download.assert_awaited_once_with(client, "00000000-1111-2222-3333-444444444444")

    def test_trello_archive_upsamples_image_to_2k_before_file_upload(self) -> None:
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    card_id="https://trello.com/c/abc123/demo-card",
                    upload_mode="file",
                    upscale_to_2k=True,
                )
            )
        )
        request = CreateJobRequest(type="image", prompt="cat")
        artifact = JobArtifact(label="Ảnh 1", media_name="media", url="https://example.com/cat.jpg", mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.dict(
            os.environ,
            {
                "TRELLO_API_KEY": "",
                "TRELLO_TOKEN": "",
                "TRELLO_CARD_ID": "",
                "TRELLO_LIST_ID": "",
                "TRELLO_UPLOAD_MODE": "file",
            },
            clear=False,
        ), patch.object(
            self.service,
            "_upsample_artifact_bytes",
            new=AsyncMock(
                return_value=ImageUpscaleResult(
                    bytes=b"upscaled-jpeg-bytes",
                    mime_type="image/jpeg",
                    source="flow_2k",
                    source_size=(1024, 1024),
                    target_size=(2048, 2048),
                    used_flow=True,
                )
            ),
        ) as upsample, patch.object(
            self.service,
            "_trello_attach_file_bytes",
            return_value={"id": "att-1", "name": "flow-cat.jpg", "url": "https://trello.example/att-1"},
        ) as attach_bytes, patch.object(
            self.service,
            "_trello_attach_file_from_url",
        ) as attach_from_url:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        upsample.assert_awaited_once()
        attach_bytes.assert_called_once()
        attach_from_url.assert_not_called()
        # Positional args: key, token, card_id, file_bytes, mime, name, set_cover
        self.assertEqual(b"upscaled-jpeg-bytes", attach_bytes.call_args.args[3])
        self.assertEqual("image/jpeg", attach_bytes.call_args.args[4])
        self.assertEqual("abc123", attach_bytes.call_args.args[2])
        self.assertFalse(attach_bytes.call_args.args[6])
        self.assertTrue(result["configured"])
        self.assertEqual(1, result["sent"])
        self.assertEqual(0, result["failed"])

    def test_trello_archive_keeps_original_when_flow_upsample_keeps_original(self) -> None:
        from PIL import Image

        source_image = io.BytesIO()
        Image.new("RGB", (512, 512), (210, 180, 140)).save(source_image, format="JPEG", quality=90)
        source_bytes = source_image.getvalue()
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    card_id="https://trello.com/c/abc123/demo-card",
                    upload_mode="file",
                    upscale_to_2k=True,
                )
            )
        )
        request = CreateJobRequest(type="image", prompt="cat")
        artifact = JobArtifact(label="Ảnh 1", media_name="media", url="https://example.com/cat.jpg", mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.dict(os.environ, {"FLOW_UPSAMPLE_API_ENABLED": "1"}, clear=False), patch.object(
            self.service,
            "_read_remote_file",
            return_value=(source_bytes, "image/jpeg"),
        ), patch.object(
            self.service,
            "_with_client",
            new=AsyncMock(return_value=source_bytes),
        ) as flow_upscale, patch.object(
            self.service,
            "_trello_attach_file_bytes",
            return_value={"id": "att-1", "name": "flow-cat.jpg", "url": "https://trello.example/att-1"},
        ) as attach_bytes:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        self.assertGreaterEqual(flow_upscale.await_count, 1)
        attach_bytes.assert_called_once()
        uploaded_bytes = attach_bytes.call_args.args[3]
        with Image.open(io.BytesIO(uploaded_bytes)) as uploaded:
            self.assertEqual((512, 512), uploaded.size)
        self.assertEqual("image/jpeg", attach_bytes.call_args.args[4])
        saved = self.store.get_job(job.id)
        self.assertTrue(any("khong resize gia 2K" in entry.message for entry in saved.logs))
        self.assertTrue(result["configured"])
        self.assertEqual(1, result["sent"])
        self.assertEqual(0, result["failed"])

    def test_trello_archive_keeps_original_after_flow_upsample_failure(self) -> None:
        from PIL import Image

        source_file = self.downloads_dir / "flow-small.jpg"
        Image.new("RGB", (640, 480), (120, 170, 210)).save(source_file, format="JPEG", quality=90)
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    card_id="https://trello.com/c/abc123/demo-card",
                    upload_mode="file",
                    upscale_to_2k=True,
                )
            )
        )
        request = CreateJobRequest(type="image", prompt="cat")
        artifact = JobArtifact(label="Ảnh 1", media_name="media", local_path=str(source_file), mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.object(
            self.service,
            "_upsample_artifact_bytes",
            new=AsyncMock(side_effect=RuntimeError("No session found")),
        ), patch.object(
            self.service,
            "_trello_attach_file_bytes",
            return_value={"id": "att-1", "name": "flow-cat.jpg", "url": "https://trello.example/att-1"},
        ) as attach_bytes:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        attach_bytes.assert_called_once()
        uploaded_bytes = attach_bytes.call_args.args[3]
        with Image.open(io.BytesIO(uploaded_bytes)) as uploaded:
            self.assertEqual((640, 480), uploaded.size)
        self.assertEqual("image/jpeg", attach_bytes.call_args.args[4])
        self.assertTrue(result["configured"])
        self.assertEqual(1, result["sent"])
        self.assertEqual(0, result["failed"])

    def test_trello_archive_materializes_flow_url_before_file_upload(self) -> None:
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    card_id="https://trello.com/c/abc123/demo-card",
                    upload_mode="file",
                    upscale_to_2k=False,
                )
            )
        )
        local_file = self.downloads_dir / "flow-image.jpg"
        local_file.write_bytes(b"flow-image-bytes")
        request = CreateJobRequest(type="image", prompt="cat")
        artifact = JobArtifact(
            label="Ảnh 1",
            media_name="media",
            url="https://labs.google/fx/api/trpc/media.getMediaUrlRedirect?name=media",
            mime_type="image/jpeg",
        )
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.object(
            self.service,
            "_materialize_artifact_file",
            new=AsyncMock(return_value=str(local_file)),
        ) as materialize, patch.object(
            self.service,
            "_trello_attach_file_bytes",
            return_value={"id": "att-1", "name": "flow-cat.jpg", "url": "https://trello.example/att-1"},
        ) as attach_bytes, patch.object(
            self.service,
            "_trello_attach_url",
        ) as attach_url:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        materialize.assert_awaited_once()
        attach_bytes.assert_called_once()
        self.assertEqual(b"flow-image-bytes", attach_bytes.call_args.args[3])
        attach_url.assert_not_called()
        self.assertEqual(1, result["sent"])
        self.assertEqual(0, result["failed"])

    def test_trello_archive_file_upload_does_not_set_cover(self) -> None:
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    card_id="https://trello.com/c/abc123/demo-card",
                    upload_mode="file",
                    upscale_to_2k=False,
                )
            )
        )
        local_file = self.downloads_dir / "flow-image.jpg"
        local_file.write_bytes(b"flow-image-bytes")
        request = CreateJobRequest(type="image", prompt="cat")
        artifact = JobArtifact(label="Ảnh 1", media_name="media", local_path=str(local_file), mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.object(
            self.service,
            "_trello_attach_file_bytes",
            return_value={"id": "att-1", "name": "flow-cat.jpg", "url": "https://trello.example/att-1"},
        ) as attach_bytes, patch.object(
            self.service,
            "_trello_attach_url",
        ) as attach_url:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        attach_bytes.assert_called_once()
        self.assertFalse(attach_bytes.call_args.args[6])
        attach_url.assert_not_called()
        self.assertEqual(1, result["sent"])
        self.assertEqual(0, result["failed"])

    def test_trello_archive_skips_upsample_in_url_mode(self) -> None:
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    card_id="https://trello.com/c/abc123/demo-card",
                    upload_mode="url",
                    upscale_to_2k=True,
                )
            )
        )
        request = CreateJobRequest(type="image", prompt="cat")
        artifact = JobArtifact(label="Ảnh 1", media_name="media", url="https://example.com/cat.jpg", mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.object(
            self.service,
            "_upsample_artifact_bytes",
            new=AsyncMock(
                return_value=ImageUpscaleResult(
                    bytes=b"upscaled-jpeg-bytes",
                    mime_type="image/jpeg",
                    source="flow_2k",
                    source_size=(1024, 1024),
                    target_size=(2048, 2048),
                    used_flow=True,
                )
            ),
        ) as upsample, patch.object(
            self.service,
            "_trello_attach_url",
            return_value={"id": "att-1", "name": "flow-cat.jpg", "url": "https://trello.example/att-1"},
        ) as attach_url:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        # URL mode: respect the user's choice — no upsampling, no file upload.
        upsample.assert_not_called()
        attach_url.assert_called_once()
        self.assertTrue(result["configured"])
        self.assertEqual(1, result["sent"])

    def test_trello_archive_url_upload_does_not_set_cover(self) -> None:
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    card_id="https://trello.com/c/abc123/demo-card",
                    upload_mode="url",
                )
            )
        )
        request = CreateJobRequest(type="image", prompt="cat")
        artifact = JobArtifact(label="Ảnh 1", media_name="media", url="https://example.com/cat.jpg", mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.object(
            self.service,
            "_trello_attach_url",
            return_value={"id": "att-1", "name": "flow-cat.jpg", "url": "https://trello.example/att-1"},
        ) as attach_url:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        attach_url.assert_called_once()
        self.assertFalse(attach_url.call_args.args[5])
        self.assertEqual(1, result["sent"])
        self.assertEqual(0, result["failed"])

    def test_update_trello_config_saves_without_exposing_credentials(self) -> None:
        result = asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    board_id="https://trello.com/b/board123/demo-board",
                    card_id="https://trello.com/c/abc123/demo-card",
                    upload_mode="url",
                )
            )
        )

        self.assertTrue(result["configured"])
        self.assertTrue(result["credentials_saved"])
        self.assertNotIn("api_key", result)
        self.assertNotIn("token", result)
        self.assertEqual("board123", result["board_id"])
        self.assertEqual("abc123", result["card_id"])
        self.assertEqual("url", result["upload_mode"])

        saved = self.store.snapshot().trello_config
        self.assertEqual("key", saved.api_key)
        self.assertEqual("token", saved.token)
        self.assertEqual("board123", saved.board_id)
        self.assertEqual("abc123", saved.card_id)

    def test_update_trello_config_persists_creds_to_env_local_file(self) -> None:
        env_file = self.temp_root / ".env.local"
        with patch("flow_web.service.ENV_FILE", env_file) if False else patch(
            "flow_web.main.ENV_FILE", env_file
        ), patch.dict(
            os.environ,
            {
                "TRELLO_API_KEY": "",
                "TRELLO_TOKEN": "",
                "TRELLO_BOARD_ID": "",
                "TRELLO_CARD_ID": "",
                "TRELLO_LIST_ID": "",
            },
            clear=False,
        ):
            result = asyncio.run(
                self.service.update_trello_config(
                    TrelloConfigUpdateRequest(
                        api_key="wizard-key",
                        token="wizard-token",
                        board_id="https://trello.com/b/wizardboard/demo",
                        persist_to_env=True,
                    )
                )
            )
            self.assertTrue(result["persisted_to_env"])
            self.assertTrue(env_file.exists())
            contents = env_file.read_text(encoding="utf-8")
            self.assertIn("TRELLO_API_KEY=wizard-key", contents)
            self.assertIn("TRELLO_TOKEN=wizard-token", contents)
            self.assertIn("TRELLO_BOARD_ID=wizardboard", contents)
            # Process env is also updated so the running app picks it up without restart.
            self.assertEqual("wizard-key", os.environ.get("TRELLO_API_KEY", ""))

    def test_update_trello_config_persist_preserves_unrelated_env_lines(self) -> None:
        env_file = self.temp_root / ".env.local"
        env_file.write_text(
            "\n".join(
                [
                    "# preexisting comment",
                    "OTHER_SECRET=keep-me",
                    "TRELLO_API_KEY=old-key",
                    "",
                    "GEMINI_API_KEY=gem-keep",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        with patch("flow_web.main.ENV_FILE", env_file), patch.dict(
            os.environ,
            {"TRELLO_API_KEY": "", "TRELLO_TOKEN": ""},
            clear=False,
        ):
            result = asyncio.run(
                self.service.update_trello_config(
                    TrelloConfigUpdateRequest(
                        api_key="new-key",
                        token="new-token",
                        board_id="https://trello.com/b/newboard/demo",
                        persist_to_env=True,
                    )
                )
            )

        self.assertTrue(result["persisted_to_env"])
        contents = env_file.read_text(encoding="utf-8")
        # Existing unrelated lines must be preserved verbatim.
        self.assertIn("# preexisting comment", contents)
        self.assertIn("OTHER_SECRET=keep-me", contents)
        self.assertIn("GEMINI_API_KEY=gem-keep", contents)
        # The previously stored TRELLO_API_KEY is overwritten in place,
        # not duplicated at the end of the file.
        self.assertNotIn("TRELLO_API_KEY=old-key", contents)
        self.assertEqual(contents.count("TRELLO_API_KEY="), 1)
        self.assertIn("TRELLO_API_KEY=new-key", contents)
        # New keys that weren't in the file before are appended cleanly.
        self.assertIn("TRELLO_TOKEN=new-token", contents)
        self.assertIn("TRELLO_BOARD_ID=newboard", contents)

    def test_trello_config_snapshot_falls_back_to_env_vars(self) -> None:
        # Chủ nhân setup 1 lần qua .env.local: state.json rỗng nhưng env vars
        # phải đủ để UI báo "Đã lưu" thay vì "Cần thiết lập".
        empty_snapshot = self.service._trello_config_snapshot(self.store.snapshot().trello_config)
        self.assertFalse(empty_snapshot["credentials_saved"])
        self.assertEqual("", empty_snapshot["credentials_source"])

        with patch.dict(
            os.environ,
            {
                "TRELLO_API_KEY": "env-key",
                "TRELLO_TOKEN": "env-token",
                "TRELLO_BOARD_ID": "https://trello.com/b/envboard/demo",
                "TRELLO_CARD_ID": "https://trello.com/c/envcard/demo",
                "TRELLO_LIST_ID": "envlist",
                "TRELLO_UPLOAD_MODE": "url",
            },
            clear=False,
        ):
            envonly = self.service._trello_config_snapshot(self.store.snapshot().trello_config)

        self.assertTrue(envonly["configured"])
        self.assertTrue(envonly["credentials_saved"])
        self.assertEqual("env", envonly["credentials_source"])
        self.assertEqual("envboard", envonly["board_id"])
        self.assertEqual("envcard", envonly["card_id"])
        self.assertEqual("envlist", envonly["list_id"])
        # upload_mode trong state.json mặc định "file" — env chỉ override khi
        # state thực sự để trống, khớp với logic trong _archive_trello_artifacts.
        self.assertIn(envonly["upload_mode"], {"file", "url"})
        # Snapshot không bao giờ leak api_key/token raw
        self.assertNotIn("api_key", envonly)
        self.assertNotIn("token", envonly)

    def test_trello_config_snapshot_prefers_state_over_env(self) -> None:
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="state-key",
                    token="state-token",
                    board_id="https://trello.com/b/stateboard/demo",
                )
            )
        )
        with patch.dict(
            os.environ,
            {"TRELLO_API_KEY": "env-key", "TRELLO_TOKEN": "env-token"},
            clear=False,
        ):
            snap = self.service._trello_config_snapshot(self.store.snapshot().trello_config)

        # State vẫn ưu tiên trước env nên credentials_source = "state".
        self.assertEqual("state", snap["credentials_source"])
        self.assertTrue(snap["credentials_saved"])
        self.assertEqual("stateboard", snap["board_id"])

    def test_trello_archive_uses_app_saved_config(self) -> None:
        asyncio.run(
            self.service.update_trello_config(
                TrelloConfigUpdateRequest(
                    api_key="key",
                    token="token",
                    card_id="https://trello.com/c/abc123/demo-card",
                    upload_mode="url",
                )
            )
        )
        request = CreateJobRequest(type="image", prompt="cat")
        artifact = JobArtifact(label="Ảnh 1", media_name="media", url="https://example.com/cat.jpg", mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.dict(
            os.environ,
            {
                "TRELLO_API_KEY": "",
                "TRELLO_TOKEN": "",
                "TRELLO_CARD_ID": "",
                "TRELLO_LIST_ID": "",
                "TRELLO_UPLOAD_MODE": "file",
            },
            clear=False,
        ), patch.object(
            self.service,
            "_trello_attach_url",
            return_value={"id": "att-1", "name": "flow-cat.jpg", "url": "https://trello.example/att-1"},
        ) as attach_url:
            result = asyncio.run(self.service._archive_trello_artifacts(job.id, request, [artifact]))

        attach_url.assert_called_once()
        self.assertEqual("abc123", attach_url.call_args.args[2])
        self.assertEqual("https://example.com/cat.jpg", attach_url.call_args.args[3])
        self.assertTrue(result["configured"])
        self.assertEqual(1, result["sent"])

    def test_trello_resolve_board_list_id_defaults_to_ready_for_ai(self) -> None:
        lists = [
            {"id": "ideas-list", "name": "Ideas"},
            {"id": "ready-list", "name": "Ready for AI"},
        ]

        with patch.object(self.service, "_trello_board_lists", return_value=lists):
            self.assertEqual(
                "ready-list",
                self.service._trello_resolve_board_list_id("key", "token", "board123", ""),
            )
            self.assertEqual(
                "ideas-list",
                self.service._trello_resolve_board_list_id("key", "token", "board123", "Ideas"),
            )
            self.assertEqual(
                "ready-list",
                self.service._trello_resolve_board_list_id("key", "token", "board123", "ready-list"),
            )

    def test_trello_image_card_scan_requires_list_scope(self) -> None:
        with patch.object(self.service, "_trello_get_json") as get_json:
            cards = self.service._trello_image_cards_on_board("key", "token", "board123", "")

        self.assertEqual([], cards)
        get_json.assert_not_called()

    def test_trello_extra_source_lists_are_disabled_by_default(self) -> None:
        with patch.dict(
            os.environ,
            {"TRELLO_EXTRA_SOURCE_LIST_NAMES": "Ideas", "TRELLO_ALLOW_EXTRA_SOURCE_LISTS": ""},
            clear=False,
        ):
            self.assertEqual([], self.service._default_trello_extra_source_list_names())

        with patch.dict(
            os.environ,
            {"TRELLO_EXTRA_SOURCE_LIST_NAMES": "Ideas", "TRELLO_ALLOW_EXTRA_SOURCE_LISTS": "true"},
            clear=False,
        ):
            self.assertEqual(["Ideas"], self.service._default_trello_extra_source_list_names())

    def test_trello_image_card_scan_includes_complete_cards_for_fresh_rerun(self) -> None:
        cards_payload = [
            {"id": "done-card", "name": "Done", "idList": "ready-list"},
            {"id": "partial-card", "name": "Partial", "idList": "ready-list"},
            {"id": "fresh-card", "name": "Fresh", "idList": "ready-list"},
        ]
        done_attachments = [
            {"id": "source", "name": "source.png", "mimeType": "image/png"},
            {"id": "flow-output", "name": "flow-abc12345-1.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-output-2", "name": "flow-abc12345-2.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-output-3", "name": "flow-abc12345-3.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-output-4", "name": "flow-abc12345-4.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-output-5", "name": "flow-abc12345-5.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-output-6", "name": "flow-abc12345-6.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-output-7", "name": "flow-abc12345-7.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-output-8", "name": "flow-abc12345-8.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-output-9", "name": "flow-abc12345-9.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-output-10", "name": "flow-abc12345-10.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-output-11", "name": "flow-abc12345-11.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-output-12", "name": "flow-abc12345-12.jpg", "mimeType": "image/jpeg"},
        ]
        partial_attachments = [
            {"id": "partial-source", "name": "partial.png", "mimeType": "image/png"},
            {"id": "flow-partial", "name": "flow-def67890-1.jpg", "mimeType": "image/jpeg"},
        ]
        fresh_attachments = [{"id": "fresh-source", "name": "fresh.png", "mimeType": "image/png"}]

        with patch.object(
            self.service,
            "_trello_get_json",
            side_effect=[cards_payload, done_attachments, partial_attachments, fresh_attachments],
        ):
            cards = self.service._trello_image_cards_on_board("key", "token", "board123", "ready-list")

        self.assertEqual(["done-card", "partial-card", "fresh-card"], [card["id"] for card in cards])
        self.assertEqual("source", cards[0]["_image_attachments"][0]["id"])
        self.assertEqual(["source"], cards[0]["_selected_attachment_ids"])
        self.assertEqual(12, cards[0]["_flow_output_count"])
        self.assertEqual("partial-source", cards[1]["_image_attachments"][0]["id"])
        self.assertEqual(["partial-source"], cards[1]["_selected_attachment_ids"])
        self.assertEqual(1, cards[1]["_flow_output_count"])
        self.assertEqual("fresh-source", cards[2]["_image_attachments"][0]["id"])
        self.assertEqual(["fresh-source"], cards[2]["_selected_attachment_ids"])
        self.assertEqual(0, cards[2]["_flow_output_count"])

    def test_trello_image_card_scan_uses_single_generated_image_name_as_source(self) -> None:
        cards_payload = [{"id": "generated-card", "name": "Generated source", "idList": "ready-list"}]
        attachments = [
            {
                "id": "generated-source",
                "name": "Generated Image March 16, 2026 - 2_57PM.png",
                "mimeType": "image/png",
            }
        ]

        with patch.object(self.service, "_trello_get_json", side_effect=[cards_payload, attachments]):
            cards = self.service._trello_image_cards_on_board("key", "token", "board123", "ready-list")

        self.assertEqual(["generated-card"], [card["id"] for card in cards])
        self.assertEqual("generated-source", cards[0]["_image_attachments"][0]["id"])
        self.assertEqual(["generated-source"], cards[0]["_selected_attachment_ids"])
        self.assertEqual(0, cards[0]["_flow_output_count"])

    def test_trello_image_card_scan_prefers_oldest_source_attachment(self) -> None:
        cards_payload = [{"id": "card-1", "name": "Product", "idList": "ready-list"}]
        attachments = [
            {"id": "old-source", "name": "old-source.png", "mimeType": "image/png", "date": "2026-05-20T08:00:00.000Z"},
            {"id": "new-source", "name": "new-source.png", "mimeType": "image/png", "date": "2026-05-22T08:00:00.000Z"},
            {"id": "flow-output", "name": "flow-card-1.jpg", "mimeType": "image/jpeg", "date": "2026-05-22T09:00:00.000Z"},
        ]

        with patch.object(self.service, "_trello_get_json", side_effect=[cards_payload, attachments]):
            cards = self.service._trello_image_cards_on_board("key", "token", "board123", "ready-list")

        self.assertEqual(["card-1"], [card["id"] for card in cards])
        self.assertEqual("old-source", cards[0]["_image_attachments"][0]["id"])
        self.assertEqual(["old-source"], cards[0]["_selected_attachment_ids"])
        self.assertEqual(1, cards[0]["_flow_output_count"])

    def test_auto_trello_default_scope_uses_ready_list_only(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="",
            trello_board_id="board123",
            trello_list_id=self.service.DEFAULT_TRELLO_SOURCE_LIST_ID,
        )
        ready_card = {
            "id": "ready-card",
            "shortLink": "ready",
            "idList": "ready-list",
            "name": "baby_pillowcase ready product",
            "url": "https://trello.example/c/ready",
            "_image_attachments": [{"id": "ready-att", "name": "baby_pillowcase_ready.jpg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["ready-att"],
        }
        ideas_card = {
            "id": "ideas-card",
            "shortLink": "ideas",
            "idList": "ideas-list",
            "name": "ideas product",
            "url": "https://trello.example/c/ideas",
            "_image_attachments": [{"id": "ideas-att", "name": "ideas.jpg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["ideas-att"],
        }

        def resolve_list(_key: str, _token: str, _board_id: str, value: str = "") -> str:
            if value == self.service.DEFAULT_TRELLO_SOURCE_LIST_ID or self.service._compact_match_text(value) == "readyforai":
                return "ready-list"
            if self.service._compact_match_text(value) == "ideas":
                return "ideas-list"
            return ""

        def image_cards(_key: str, _token: str, _board_id: str, list_id: str = "") -> list[dict]:
            return {"ready-list": [ready_card], "ideas-list": [ideas_card]}.get(list_id, [])

        def list_name(_key: str, _token: str, list_id: str) -> str:
            return {"ready-list": "Ready for AI", "ideas-list": "Ideas"}.get(list_id, "")

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            side_effect=resolve_list,
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            side_effect=image_cards,
        ), patch.object(
            self.service,
            "_trello_list_name",
            side_effect=list_name,
        ):
            items, discovery = self.service._trello_prompt_items_for_image_cards(request, [], 0)

        self.assertEqual(["ready-card"], [item["trello_card_id"] for item in items])
        self.assertEqual(["ready-list"], discovery["list_ids"])
        self.assertEqual("Ready for AI", discovery["list_name"])

    def test_auto_trello_scan_skips_seen_cards_before_visual_analysis(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="",
            trello_board_id="board123",
            trello_list_id="ready-list",
        )
        seen_card = {
            "id": "seen-card",
            "shortLink": "seen",
            "idList": "ready-list",
            "name": "seen product",
            "url": "https://trello.example/c/seen",
            "_image_attachments": [{"id": "seen-att", "name": "seen.jpg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["seen-att"],
        }
        fresh_card = {
            "id": "fresh-card",
            "shortLink": "fresh",
            "idList": "ready-list",
            "name": "fresh baby_pillowcase product",
            "url": "https://trello.example/c/fresh",
            "_image_attachments": [{"id": "fresh-att", "name": "fresh_baby_pillowcase.jpg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["fresh-att"],
        }

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=[seen_card, fresh_card],
        ), patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ), patch.object(
            self.service,
            "_flow_operator_enrich_card_with_visual_product_rule",
        ) as enrich:
            items, discovery = self.service._trello_prompt_items_for_image_cards(request, [], 1, {"seen-card"})

        self.assertEqual(["fresh-card"], [item["trello_card_id"] for item in items])
        self.assertEqual(1, discovery["skipped_seen_cards"])
        enrich.assert_called_once()
        self.assertEqual("fresh-card", enrich.call_args.args[1]["id"])

    def test_auto_trello_explicit_card_ignores_stale_attachment_id_for_oldest_source(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="",
            trello_board_id="board123",
            trello_list_id="ready-list",
            trello_card_id="ready-card",
            trello_attachment_ids=["new-source"],
        )
        card = {
            "id": "ready-card",
            "shortLink": "ready",
            "idList": "ready-list",
            "name": "ready baby_pillowcase product",
            "url": "https://trello.example/c/ready",
            "_image_attachments": [
                {"id": "old-source", "name": "baby_pillowcase_old.jpg", "mimeType": "image/jpeg", "date": "2026-05-20T08:00:00.000Z"},
                {"id": "new-source", "name": "baby_pillowcase_new.jpg", "mimeType": "image/jpeg", "date": "2026-05-22T08:00:00.000Z"},
            ],
            "_selected_attachment_ids": ["old-source"],
            "_flow_output_count": 0,
        }

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_card_by_id",
            return_value=card,
        ), patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ):
            items, _discovery = self.service._trello_prompt_items_for_image_cards(request, [], 0)

        self.assertEqual(["old-source"], items[0]["trello_attachment_ids"])

    def test_trello_image_card_scan_counts_numbered_generated_series_as_outputs(self) -> None:
        cards_payload = [
            {"id": "partial-card", "name": "baby_pillowcase", "idList": "ready-list"},
            {"id": "done-card", "name": "done pillow", "idList": "ready-list"},
        ]
        partial_attachments = [
            {"id": "source", "name": "baby_pillowcase.png", "mimeType": "image/png", "date": "2026-05-21T10:00:00.000Z"},
            {"id": "old-output-1", "name": "baby_pillowcase_9.png", "mimeType": "image/png", "date": "2026-05-21T10:30:00.000Z"},
            {"id": "old-output-2", "name": "baby_pillowcase_10.png", "mimeType": "image/png", "date": "2026-05-21T10:31:00.000Z"},
        ]
        done_attachments = [
            {"id": "done-source", "name": "done_pillow.png", "mimeType": "image/png"},
            {"id": "done-output-1", "name": "done_pillow_1.png", "mimeType": "image/png"},
            {"id": "done-output-2", "name": "done_pillow_2.png", "mimeType": "image/png"},
            {"id": "done-output-3", "name": "done_pillow_3.png", "mimeType": "image/png"},
            {"id": "done-output-4", "name": "done_pillow_4.png", "mimeType": "image/png"},
            {"id": "done-output-5", "name": "done_pillow_5.png", "mimeType": "image/png"},
            {"id": "done-output-6", "name": "done_pillow_6.png", "mimeType": "image/png"},
            {"id": "done-output-7", "name": "done_pillow_7.png", "mimeType": "image/png"},
            {"id": "done-output-8", "name": "done_pillow_8.png", "mimeType": "image/png"},
            {"id": "done-output-9", "name": "done_pillow_9.png", "mimeType": "image/png"},
            {"id": "done-output-10", "name": "done_pillow_10.png", "mimeType": "image/png"},
            {"id": "done-output-11", "name": "done_pillow_11.png", "mimeType": "image/png"},
            {"id": "done-output-12", "name": "done_pillow_12.png", "mimeType": "image/png"},
        ]

        with patch.object(
            self.service,
            "_trello_get_json",
            side_effect=[cards_payload, partial_attachments, done_attachments],
        ):
            cards = self.service._trello_image_cards_on_board("key", "token", "board123", "ready-list")

        self.assertEqual(["partial-card", "done-card"], [card["id"] for card in cards])
        self.assertEqual(2, cards[0]["_flow_output_count"])
        self.assertEqual(12, cards[1]["_flow_output_count"])

    def test_trello_single_numbered_output_with_source_can_continue_missing_set(self) -> None:
        cards_payload = [{"id": "partial-card", "name": "baby_pillowcase", "idList": "ready-list"}]
        attachments = [
            {"id": "source", "name": "baby_pillowcase.png", "mimeType": "image/png", "date": "2026-05-21T10:00:00.000Z"},
            {"id": "old-output", "name": "baby_pillowcase_13.png", "mimeType": "image/png", "date": "2026-05-21T10:30:00.000Z"},
        ]

        with patch.object(self.service, "_trello_get_json", side_effect=[cards_payload, attachments]):
            cards = self.service._trello_image_cards_on_board("key", "token", "board123", "ready-list")

        self.assertEqual(["partial-card"], [card["id"] for card in cards])
        self.assertEqual(["source"], cards[0]["_selected_attachment_ids"])
        self.assertEqual(1, cards[0]["_flow_output_count"])

    def test_trello_image_card_scan_skips_when_only_generated_series_remains(self) -> None:
        cards_payload = [{"id": "output-only-card", "name": "baby_pillowcase", "idList": "ready-list"}]
        attachments = [
            {"id": "old-output-1", "name": "baby_pillowcase_9.png", "mimeType": "image/png"},
            {"id": "old-output-2", "name": "baby_pillowcase_10.png", "mimeType": "image/png"},
        ]

        with patch.object(
            self.service,
            "_trello_get_json",
            side_effect=[cards_payload, attachments],
        ):
            cards = self.service._trello_image_cards_on_board("key", "token", "board123", "ready-list")

        self.assertEqual([], cards)

    def test_auto_trello_ready_summary_explains_completed_ready_cards(self) -> None:
        request = CreateJobRequest(type="image", trello_board_id="board123", trello_list_id="ready-list")
        cards_payload = [
            {"id": "done-card", "name": "Done", "idList": "ready-list"},
            {"id": "first-batch-card", "name": "First batch", "idList": "ready-list"},
            {"id": "new-card", "name": "New", "idList": "ready-list"},
            {"id": "empty-card", "name": "Empty", "idList": "ready-list"},
        ]
        done_attachments = [
            {"id": "source", "name": "source.png", "mimeType": "image/png"},
            {"id": "flow-1", "name": "flow-done-1.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-2", "name": "flow-done-2.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-3", "name": "flow-done-3.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-4", "name": "flow-done-4.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-5", "name": "flow-done-5.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-6", "name": "flow-done-6.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-7", "name": "flow-done-7.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-8", "name": "flow-done-8.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-9", "name": "flow-done-9.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-10", "name": "flow-done-10.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-11", "name": "flow-done-11.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-12", "name": "flow-done-12.jpg", "mimeType": "image/jpeg"},
        ]
        first_batch_attachments = [
            {"id": "first-source", "name": "source.png", "mimeType": "image/png"},
            {"id": "first-flow-1", "name": "flow-first-1.jpg", "mimeType": "image/jpeg"},
            {"id": "first-flow-2", "name": "flow-first-2.jpg", "mimeType": "image/jpeg"},
            {"id": "first-flow-3", "name": "flow-first-3.jpg", "mimeType": "image/jpeg"},
            {"id": "first-flow-4", "name": "flow-first-4.jpg", "mimeType": "image/jpeg"},
        ]
        new_attachments = [{"id": "new-source", "name": "new-source.png", "mimeType": "image/png"}]
        empty_attachments: list[dict] = []

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_get_json",
            side_effect=[cards_payload, done_attachments, first_batch_attachments, new_attachments, empty_attachments],
        ):
            summary = self.service._auto_trello_ready_for_ai_summary(request)

        self.assertIn("Ready for AI co 4 card", summary)
        self.assertIn("1 card da co du anh output theo rule nen Auto se bo qua", summary)
        self.assertIn("2 card co anh nguon va khi chay se tao moi du bo theo rule", summary)
        self.assertIn("1 card chua co anh nguon", summary)

    def test_reset_ready_trello_outputs_deletes_only_generated_images(self) -> None:
        request = ResetReadyTrelloRequest(trello_board_id="board123", trello_list_id="ready-list")
        cards_payload = [
            {"id": "done-card", "name": "Done", "idList": "ready-list", "url": "https://trello.test/done"},
            {"id": "new-card", "name": "New", "idList": "ready-list", "url": "https://trello.test/new"},
        ]
        done_attachments = [
            {"id": "source", "name": "source.png", "mimeType": "image/png"},
            {"id": "flow-1", "name": "flow-done-1.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-2", "name": "flow-done-2.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-3", "name": "flow-done-3.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-4", "name": "flow-done-4.jpg", "mimeType": "image/jpeg"},
        ]
        new_attachments = [{"id": "new-source", "name": "new-source.png", "mimeType": "image/png"}]

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_get_json",
            side_effect=[cards_payload, done_attachments, new_attachments],
        ), patch.object(self.service, "_trello_delete_attachment", return_value={}) as delete_attachment:
            result = asyncio.run(self.service.reset_ready_trello_outputs(request))

        self.assertEqual(2, result["cards_seen"])
        self.assertEqual(1, result["cards_reset"])
        self.assertEqual(4, result["attachments_deleted"])
        self.assertEqual(1, result["already_unfinished"])
        deleted_ids = [call.args[3] for call in delete_attachment.call_args_list]
        self.assertEqual(["flow-1", "flow-2", "flow-3", "flow-4"], deleted_ids)
        self.assertNotIn("source", deleted_ids)

    def test_reset_ready_trello_outputs_is_locked_to_worker_env_list(self) -> None:
        request = ResetReadyTrelloRequest(
            trello_board_id="wrong-browser-board",
            trello_list_id="worker-1-list",
        )
        cards_payload = [
            {"id": "worker-1-card", "name": "Worker 1", "idList": "worker-1-list"},
            {"id": "worker-3-card", "name": "Worker 3", "idList": "worker-3-list"},
        ]
        worker_3_attachments = [
            {"id": "source-3", "name": "source.png", "mimeType": "image/png"},
            {"id": "output-3", "name": "flow-worker3-1.jpg", "mimeType": "image/jpeg"},
        ]

        with patch.dict(
            os.environ,
            {"TRELLO_BOARD_ID": "worker-board", "TRELLO_LIST_ID": "worker-3-list"},
        ), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="worker-3-list",
        ) as resolve_list, patch.object(
            self.service,
            "_trello_auto_source_list_ids",
        ) as expand_lists, patch.object(
            self.service,
            "_trello_get_json",
            side_effect=[cards_payload, worker_3_attachments],
        ), patch.object(
            self.service,
            "_trello_delete_attachment",
            return_value={},
        ) as delete_attachment:
            result = asyncio.run(self.service.reset_ready_trello_outputs(request))

        self.assertEqual("worker-board", result["board_id"])
        self.assertEqual(["worker-3-list"], result["list_ids"])
        self.assertEqual(1, result["cards_seen"])
        resolve_list.assert_called_once_with("key", "token", "worker-board", "worker-3-list")
        expand_lists.assert_not_called()
        delete_attachment.assert_called_once_with("key", "token", "worker-3-card", "output-3")

    def test_ready_trello_status_reports_completed_and_runnable_cards(self) -> None:
        request = ResetReadyTrelloRequest(trello_board_id="board123", trello_list_id="ready-list")
        cards_payload = [
            {"id": "done-card", "name": "Done", "idList": "ready-list", "url": "https://trello.test/done"},
            {"id": "new-card", "name": "New", "idList": "ready-list", "url": "https://trello.test/new"},
            {"id": "empty-card", "name": "Empty", "idList": "ready-list", "url": "https://trello.test/empty"},
        ]
        done_attachments = [
            {"id": "source", "name": "source.png", "mimeType": "image/png"},
            {"id": "flow-1", "name": "flow-done-1.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-2", "name": "flow-done-2.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-3", "name": "flow-done-3.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-4", "name": "flow-done-4.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-5", "name": "flow-done-5.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-6", "name": "flow-done-6.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-7", "name": "flow-done-7.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-8", "name": "flow-done-8.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-9", "name": "flow-done-9.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-10", "name": "flow-done-10.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-11", "name": "flow-done-11.jpg", "mimeType": "image/jpeg"},
            {"id": "flow-12", "name": "flow-done-12.jpg", "mimeType": "image/jpeg"},
        ]
        new_attachments = [{"id": "new-source", "name": "new-source.png", "mimeType": "image/png"}]
        empty_attachments: list[dict] = []

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_get_json",
            side_effect=[cards_payload, done_attachments, new_attachments, empty_attachments],
        ):
            result = asyncio.run(self.service.ready_trello_status(request))

        self.assertEqual(3, result["cards_seen"])
        self.assertEqual(1, result["complete"])
        self.assertEqual(1, result["eligible"])
        self.assertEqual(1, result["without_source"])
        self.assertEqual(12, result["target_output_count"])
        card_statuses = {card["id"]: card["status"] for card in result["cards"]}
        self.assertEqual("complete", card_statuses["done-card"])
        self.assertEqual("eligible", card_statuses["new-card"])
        self.assertEqual("no_source", card_statuses["empty-card"])
        missing_counts = {card["id"]: card["missing_count"] for card in result["cards"]}
        self.assertEqual(0, missing_counts["done-card"])
        self.assertEqual(12, missing_counts["new-card"])

    def test_ready_trello_status_uses_board_card_attachments_when_available(self) -> None:
        request = ResetReadyTrelloRequest(trello_board_id="board123", trello_list_id="ready-list")
        cards_payload = [
            {
                "id": "done-card",
                "name": "Done",
                "idList": "ready-list",
                "url": "https://trello.test/done",
                "attachments": [
                    {"id": "source", "name": "source.png", "mimeType": "image/png"},
                    {"id": "flow-1", "name": "flow-done-1.jpg", "mimeType": "image/jpeg"},
                    {"id": "flow-2", "name": "flow-done-2.jpg", "mimeType": "image/jpeg"},
                    {"id": "flow-3", "name": "flow-done-3.jpg", "mimeType": "image/jpeg"},
                    {"id": "flow-4", "name": "flow-done-4.jpg", "mimeType": "image/jpeg"},
                    {"id": "flow-5", "name": "flow-done-5.jpg", "mimeType": "image/jpeg"},
                    {"id": "flow-6", "name": "flow-done-6.jpg", "mimeType": "image/jpeg"},
                    {"id": "flow-7", "name": "flow-done-7.jpg", "mimeType": "image/jpeg"},
                    {"id": "flow-8", "name": "flow-done-8.jpg", "mimeType": "image/jpeg"},
                    {"id": "flow-9", "name": "flow-done-9.jpg", "mimeType": "image/jpeg"},
                    {"id": "flow-10", "name": "flow-done-10.jpg", "mimeType": "image/jpeg"},
                    {"id": "flow-11", "name": "flow-done-11.jpg", "mimeType": "image/jpeg"},
                    {"id": "flow-12", "name": "flow-done-12.jpg", "mimeType": "image/jpeg"},
                ],
            },
            {
                "id": "new-card",
                "name": "New",
                "idList": "ready-list",
                "url": "https://trello.test/new",
                "attachments": [{"id": "new-source", "name": "new-source.png", "mimeType": "image/png"}],
            },
        ]

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_get_json",
            return_value=cards_payload,
        ) as get_json:
            result = asyncio.run(self.service.ready_trello_status(request))

        self.assertEqual(2, result["cards_seen"])
        self.assertEqual(1, result["complete"])
        self.assertEqual(1, result["eligible"])
        self.assertEqual(1, get_json.call_count)

    def test_ready_trello_status_treats_single_generated_image_name_as_source(self) -> None:
        request = ResetReadyTrelloRequest(trello_board_id="board123", trello_list_id="ready-list")
        cards_payload = [
            {
                "id": "generated-card",
                "name": "Generated source",
                "idList": "ready-list",
                "url": "https://trello.test/generated",
                "attachments": [
                    {
                        "id": "generated-source",
                        "name": "Generated Image March 16, 2026 - 2_57PM.png",
                        "mimeType": "image/png",
                    }
                ],
            }
        ]

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_get_json",
            return_value=cards_payload,
        ):
            result = asyncio.run(self.service.ready_trello_status(request))

        self.assertEqual(1, result["cards_seen"])
        self.assertEqual(0, result["complete"])
        self.assertEqual(1, result["eligible"])
        self.assertEqual(0, result["without_source"])
        self.assertEqual("eligible", result["cards"][0]["status"])
        self.assertEqual(1, result["cards"][0]["source_count"])
        self.assertEqual(0, result["cards"][0]["output_count"])

    def test_trello_candidate_previews_hide_raw_attachment_url(self) -> None:
        previews = self.service._trello_candidate_image_previews(
            "card-1",
            [{"id": "att-1", "name": "source.png", "url": "https://trello.local/source.png", "mimeType": "image/png"}],
        )

        self.assertEqual("/api/trello/cards/card-1/attachments/att-1/preview", previews[0]["preview_url"])
        self.assertNotIn("url", previews[0])

    def test_trello_secret_redaction_masks_query_tokens(self) -> None:
        message = "failed: https://api.trello.com/1/cards?key=mykey&token=mytoken token=mytoken"

        redacted = self.service._redact_trello_secret(message, "mykey", "mytoken")

        self.assertNotIn("mykey", redacted)
        self.assertNotIn("mytoken", redacted)
        self.assertIn("[redacted]", redacted)

    def test_download_trello_card_image_attachments_uses_selected_attachment_only(self) -> None:
        attachments = [
            {"id": "att-wrong", "name": "wrong.png", "url": "https://trello.local/wrong.png", "mimeType": "image/png"},
            {"id": "att-right", "name": "right.png", "url": "https://trello.local/right.png", "mimeType": "image/png"},
        ]
        downloaded: list[str] = []

        def fake_download(key: str, token: str, card_id: str, attachment: dict) -> tuple[bytes, str]:
            downloaded.append(str(attachment.get("id") or ""))
            return b"image", "image/png"

        with patch.object(self.service, "_trello_get_json", return_value=attachments), patch.object(
            self.service,
            "_trello_download_attachment_bytes",
            side_effect=fake_download,
        ):
            paths = self.service._download_trello_card_image_attachments(
                "key",
                "token",
                "card-1",
                "job12345",
                4,
                ["att-right"],
            )

        self.assertEqual(["att-right"], downloaded)
        self.assertEqual(1, len(paths))
        self.assertTrue(Path(paths[0]).exists())
        self.assertEqual("card-1", self.service._trello_source_downloads["job12345"]["card_id"])
        self.assertEqual(["att-right"], self.service._trello_source_downloads["job12345"]["attachment_ids"])

    def test_download_trello_card_image_attachments_uses_oldest_source_by_default(self) -> None:
        attachments = [
            {"id": "old-source", "name": "old.png", "url": "https://trello.local/old.png", "mimeType": "image/png", "date": "2026-05-20T08:00:00.000Z"},
            {"id": "new-source", "name": "new.png", "url": "https://trello.local/new.png", "mimeType": "image/png", "date": "2026-05-22T08:00:00.000Z"},
            {"id": "flow-output", "name": "flow-job-1.jpg", "url": "https://trello.local/flow.jpg", "mimeType": "image/jpeg", "date": "2026-05-22T09:00:00.000Z"},
        ]
        downloaded: list[str] = []

        def fake_download(key: str, token: str, card_id: str, attachment: dict) -> tuple[bytes, str]:
            downloaded.append(str(attachment.get("id") or ""))
            return b"image", "image/png"

        with patch.object(self.service, "_trello_get_json", return_value=attachments), patch.object(
            self.service,
            "_trello_download_attachment_bytes",
            side_effect=fake_download,
        ):
            paths = self.service._download_trello_card_image_attachments(
                "key",
                "token",
                "card-1",
                "job12345",
                4,
            )

        self.assertEqual(["old-source"], downloaded)
        self.assertEqual(1, len(paths))
        self.assertTrue(Path(paths[0]).exists())
        self.assertEqual("card-1", self.service._trello_source_downloads["job12345"]["card_id"])
        self.assertEqual(["old-source"], self.service._trello_source_downloads["job12345"]["attachment_ids"])

    def test_download_trello_card_image_attachments_rejects_selected_flow_output(self) -> None:
        attachments = [
            {"id": "source", "name": "source.png", "url": "https://trello.local/source.png", "mimeType": "image/png"},
            {"id": "flow-output", "name": "flow-job-1.jpg", "url": "https://trello.local/flow.jpg", "mimeType": "image/jpeg"},
        ]

        with patch.object(self.service, "_trello_get_json", return_value=attachments):
            with self.assertRaisesRegex(RuntimeError, "ảnh output cũ"):
                self.service._download_trello_card_image_attachments(
                    "key",
                    "token",
                    "card-1",
                    "job12345",
                    1,
                    ["flow-output"],
                )

    def test_trello_matching_hint_defaults_to_ready_list(self) -> None:
        request = CreateJobRequest(type="image", prompt="", trello_board_id="https://trello.com/b/board123/demo")
        items = [{"product_key": "shirt", "product": "Shirt", "prompt": "prompt"}]
        card = {"id": "ready-card", "name": "shirt", "shortLink": "ready", "url": "https://trello.com/c/ready", "idList": "ready-list"}

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_board_lists",
            return_value=[
                {"id": "ideas-list", "name": "Ideas"},
                {"id": "ready-list", "name": "Ready for AI"},
            ],
        ), patch.object(
            self.service,
            "_trello_matching_image_card_on_board",
            return_value=card,
        ) as match_card, patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ):
            hint = self.service._trello_matching_image_card_hint(request, items)

        match_card.assert_called_once_with("key", "token", "board123", items, "ready-list")
        self.assertEqual("ready-card", hint["card_id"])
        self.assertEqual("ready-list", hint["list_id"])
        self.assertEqual("Ready for AI", hint["list_name"])

    def test_trello_source_card_hint_ignores_explicit_card_outside_ready_list(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="",
            trello_board_id="https://trello.com/b/board123/demo",
            trello_card_id="wrong-card",
        )

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_board_lists",
            return_value=[
                {"id": "other-list", "name": "Done"},
                {"id": "ready-list", "name": "Ready for AI"},
            ],
        ), patch.object(
            self.service,
            "_trello_card_hint_by_id",
            return_value={"card_id": "wrong-card", "card_name": "wrong", "list_id": "other-list"},
        ):
            hint = self.service._trello_source_card_hint(request)

        self.assertEqual({}, hint)

    def test_update_integration_config_saves_without_exposing_credentials(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            result = asyncio.run(
                self.service.update_integration_config(
                    IntegrationConfigUpdateRequest(
                        gemini_api_key="gem-key",
                        gemini_model="gemini-2.5-flash",
                        telegram_bot_token="telegram-token",
                        telegram_chat_id="@review_channel",
                        playwright_browsers_path="/tmp/pw-browsers",
                    )
                )
            )

            self.assertTrue(result["gemini"]["configured"])
            self.assertTrue(result["telegram"]["configured"])
            self.assertTrue(result["runtime"]["playwright_browsers_path_set"])
            self.assertNotIn("gemini_api_key", result["gemini"])
            self.assertNotIn("telegram_bot_token", result["telegram"])
            self.assertEqual("gemini-2.5-flash", result["gemini"]["model"])
            self.assertEqual("@review_channel", result["telegram"]["chat_id"])
            self.assertEqual("/tmp/pw-browsers", os.environ.get("PLAYWRIGHT_BROWSERS_PATH"))

        saved = self.store.snapshot().integration_config
        self.assertEqual("gem-key", saved.gemini_api_key)
        self.assertEqual("telegram-token", saved.telegram_bot_token)
        self.assertEqual("/tmp/pw-browsers", saved.playwright_browsers_path)

    def test_prompt_assistant_uses_app_saved_gemini_settings(self) -> None:
        asyncio.run(
            self.service.update_integration_config(
                IntegrationConfigUpdateRequest(
                    gemini_api_key="gem-key",
                    gemini_model="gemini-2.5-pro",
                )
            )
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GEMINI_MODEL": ""}, clear=False):
            engine = self.service._prompt_ai_engine()

        self.assertTrue(engine["configured"])
        self.assertEqual("gemini", engine["engine"])
        self.assertEqual("gemini-2.5-pro", engine["model"])

    def test_user_assistant_local_answer_explains_trello_ready_flow(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False):
            result = asyncio.run(
                self.service.answer_user_assistant(
                    UserAssistantRequest(question="Trello đang lấy nhầm ảnh từ card khác thì xử lý sao?")
                )
            )

        self.assertEqual("local", result["engine"])
        self.assertIn("Ready for AI", result["answer"])
        self.assertIn("attachment", result["answer"].lower())
        self.assertTrue(result["suggested_actions"])
        self.assertNotIn("gem-key", result["context_summary"])

    def test_user_assistant_returns_executable_actions_for_auto_trello_request(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False):
            result = asyncio.run(
                self.service.answer_user_assistant(
                    UserAssistantRequest(question="tìm trên trello ảnh về gấu cho tôi rồi chạy auto trello")
                )
            )

        actions = result["suggested_actions"]
        action_names = [action.get("action") for action in actions]
        self.assertIn("apply_product_filter", action_names)
        self.assertIn("run_auto_trello", action_names)
        run_action = next(action for action in actions if action.get("action") == "run_auto_trello")
        self.assertTrue(run_action["requires_confirmation"])
        filter_action = next(action for action in actions if action.get("action") == "apply_product_filter")
        self.assertEqual("gấu", filter_action["payload"]["value"])
        self.assertIn("Ready for AI", result["context_summary"])

    def test_user_assistant_limits_auto_trello_when_user_asks_for_test(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False):
            result = asyncio.run(
                self.service.answer_user_assistant(
                    UserAssistantRequest(question="test trên trello ảnh về hoops_with_photos rồi chạy auto trello")
                )
            )

        run_action = next(action for action in result["suggested_actions"] if action.get("action") == "run_auto_trello")
        self.assertEqual(1, run_action["payload"]["limit"])
        self.assertTrue(run_action["payload"]["test_mode"])
        self.assertIn("chỉ chạy 1", run_action["detail"])

    def test_user_assistant_sets_requested_auto_trello_batch_limit(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False):
            result = asyncio.run(
                self.service.answer_user_assistant(
                    UserAssistantRequest(question="tạo 3 ảnh búp bê rồi chạy auto trello")
                )
            )

        filter_action = next(action for action in result["suggested_actions"] if action.get("action") == "apply_product_filter")
        self.assertEqual("búp bê", filter_action["payload"]["value"])
        run_action = next(action for action in result["suggested_actions"] if action.get("action") == "run_auto_trello")
        self.assertEqual(3, run_action["payload"]["limit"])
        self.assertNotIn("test_mode", run_action["payload"])

    def test_user_assistant_can_pin_explicit_trello_card_url(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False):
            result = asyncio.run(
                self.service.answer_user_assistant(
                    UserAssistantRequest(question="lấy ảnh đúng card https://trello.com/c/abc12345/ten-card rồi chạy auto")
                )
            )

        card_action = next(action for action in result["suggested_actions"] if action.get("action") == "set_trello_card")
        self.assertEqual("abc12345", card_action["payload"]["value"])
        self.assertIn("không tự chọn card khác", card_action["detail"])

    def test_user_assistant_reports_trello_candidate_outside_ready(self) -> None:
        asyncio.run(
            self.store.replace_trello_config(
                TrelloConfig(api_key="key", token="token", board_id="board123", list_id="ready-list")
            )
        )
        cards_payload = [
            {
                "id": "card-bear",
                "name": "gau_bong",
                "shortLink": "bear",
                "url": "https://trello.com/c/bear",
                "idList": "ideas-list",
                "attachments": [{"id": "att-bear", "name": "gau-bong.png", "url": "https://trello.local/bear.png", "mimeType": "image/png"}],
            }
        ]

        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""},
            clear=False,
        ), patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_board_lists",
            return_value=[
                {"id": "ideas-list", "name": "Ideas"},
                {"id": "ready-list", "name": "Ready for AI"},
            ],
        ), patch.object(
            self.service,
            "_trello_get_json",
            return_value=cards_payload,
        ):
            result = asyncio.run(
                self.service.answer_user_assistant(UserAssistantRequest(question="tôi muốn làm ảnh về gấu bông"))
            )

        self.assertEqual(1, len(result["trello_candidates"]))
        candidate = result["trello_candidates"][0]
        self.assertEqual("Ideas", candidate["list_name"])
        self.assertFalse(candidate["in_ready_list"])
        self.assertEqual("/api/trello/cards/card-bear/attachments/att-bear/preview", candidate["image_previews"][0]["preview_url"])
        self.assertIn("bấm đúng thumbnail ảnh", result["answer"])
        action_names = [action.get("action") for action in result["suggested_actions"]]
        self.assertNotIn("run_auto_trello", action_names)
        self.assertIn("set_trello_card", action_names)
        pin_action = next(action for action in result["suggested_actions"] if action.get("action") == "set_trello_card")
        self.assertEqual("att-bear", pin_action["payload"]["attachment_id"])
        self.assertTrue(pin_action["payload"]["run_after_select"])
        self.assertTrue(pin_action["label"].startswith("Chọn & chạy"))
        self.assertIn("Trello scan theo", result["context_summary"])

    def test_user_assistant_can_pin_ready_trello_candidate(self) -> None:
        asyncio.run(
            self.store.replace_trello_config(
                TrelloConfig(api_key="key", token="token", board_id="board123", list_id="ready-list")
            )
        )
        cards_payload = [
            {
                "id": "card-bear",
                "name": "gau_bong",
                "shortLink": "bear",
                "url": "https://trello.com/c/bear",
                "idList": "ready-list",
                "attachments": [{"id": "att-bear", "name": "gau-bong.png", "mimeType": "image/png"}],
            }
        ]

        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""},
            clear=False,
        ), patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_board_lists",
            return_value=[
                {"id": "ideas-list", "name": "Ideas"},
                {"id": "ready-list", "name": "Ready for AI"},
            ],
        ), patch.object(
            self.service,
            "_trello_get_json",
            return_value=cards_payload,
        ):
            result = asyncio.run(
                self.service.answer_user_assistant(UserAssistantRequest(question="tôi muốn làm ảnh về gấu bông"))
            )

        self.assertTrue(result["trello_candidates"][0]["in_ready_list"])
        action_names = [action.get("action") for action in result["suggested_actions"]]
        self.assertIn("run_auto_trello", action_names)
        pin_action = next(
            action
            for action in result["suggested_actions"]
            if action.get("action") == "set_trello_card" and action.get("payload", {}).get("value") == "bear"
        )
        self.assertEqual("att-bear", pin_action["payload"]["attachment_id"])
        self.assertTrue(pin_action["payload"]["run_after_select"])
        self.assertTrue(pin_action["label"].startswith("Chọn & chạy"))
        self.assertIn("ảnh attachment cũ nhất", pin_action["detail"])

    def test_user_assistant_searches_child_shirt_candidates_by_synonym(self) -> None:
        asyncio.run(
            self.store.replace_trello_config(
                TrelloConfig(api_key="key", token="token", board_id="board123", list_id="ready-list")
            )
        )
        cards_payload = [
            {
                "id": "card-shirt",
                "name": "T_050421_C1_010_D3_L1_4",
                "shortLink": "shirt1",
                "url": "https://trello.com/c/shirt1",
                "idList": "shirt-list",
                "attachments": [{"name": "youth-model.jpg", "mimeType": "image/jpeg"}],
            }
        ]

        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""},
            clear=False,
        ), patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_board_lists",
            return_value=[
                {"id": "shirt-list", "name": "T-Shirt"},
                {"id": "ready-list", "name": "Ready for AI"},
            ],
        ), patch.object(
            self.service,
            "_trello_get_json",
            return_value=cards_payload,
        ):
            result = asyncio.run(
                self.service.answer_user_assistant(UserAssistantRequest(question="tôi muốn làm ảnh về áo trẻ em"))
            )

        self.assertEqual(1, len(result["trello_candidates"]))
        self.assertEqual("T-Shirt", result["trello_candidates"][0]["list_name"])
        action_names = [action.get("action") for action in result["suggested_actions"]]
        self.assertIn("apply_product_filter", action_names)
        self.assertNotIn("run_auto_trello", action_names)
        self.assertIn("chưa ở Ready for AI", result["answer"])

    def test_user_assistant_searches_doll_candidates_by_vietnamese_alias(self) -> None:
        asyncio.run(
            self.store.replace_trello_config(
                TrelloConfig(api_key="key", token="token", board_id="board123", list_id="ready-list")
            )
        )
        cards_payload = [
            {
                "id": "card-doll",
                "name": "BDA_02",
                "shortLink": "doll1",
                "url": "https://trello.com/c/doll1",
                "idList": "baby-doll-list",
                "attachments": [{"id": "att-doll", "name": "front.jpg", "mimeType": "image/jpeg"}],
            }
        ]

        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""},
            clear=False,
        ), patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_board_lists",
            return_value=[
                {"id": "baby-doll-list", "name": "Baby Doll"},
                {"id": "ready-list", "name": "Ready for AI"},
            ],
        ), patch.object(
            self.service,
            "_trello_get_json",
            return_value=cards_payload,
        ):
            result = asyncio.run(
                self.service.answer_user_assistant(UserAssistantRequest(question="tôi muốn làm ảnh về búp bê"))
            )

        self.assertEqual(1, len(result["trello_candidates"]))
        candidate = result["trello_candidates"][0]
        self.assertEqual("Baby Doll", candidate["list_name"])
        self.assertEqual("att-doll", candidate["image_previews"][0]["id"])
        action_names = [action.get("action") for action in result["suggested_actions"]]
        self.assertIn("set_trello_card", action_names)
        self.assertNotIn("run_auto_trello", action_names)

    def test_user_assistant_does_not_match_generic_shirt_for_child_shirt_query(self) -> None:
        asyncio.run(
            self.store.replace_trello_config(
                TrelloConfig(api_key="key", token="token", board_id="board123", list_id="ready-list")
            )
        )
        cards_payload = [
            {
                "id": "card-shirt",
                "name": "Adult T-Shirt Mockup",
                "shortLink": "shirt1",
                "url": "https://trello.com/c/shirt1",
                "idList": "shirt-list",
                "attachments": [{"name": "black-shirt.jpg", "mimeType": "image/jpeg"}],
            }
        ]

        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""},
            clear=False,
        ), patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_board_lists",
            return_value=[
                {"id": "shirt-list", "name": "T-Shirt"},
                {"id": "ready-list", "name": "Ready for AI"},
            ],
        ), patch.object(
            self.service,
            "_trello_get_json",
            return_value=cards_payload,
        ):
            result = asyncio.run(
                self.service.answer_user_assistant(UserAssistantRequest(question="tôi muốn làm ảnh về áo trẻ em"))
            )

        self.assertEqual([], result["trello_candidates"])
        action_names = [action.get("action") for action in result["suggested_actions"]]
        self.assertNotIn("run_auto_trello", action_names)
        self.assertIn("chưa tìm thấy card", result["answer"])

    def test_auto_trello_keyword_prompt_match_ignores_prompt_body(self) -> None:
        item = {
            "product_key": "adult_shirt",
            "product": "Adult Shirt",
            "notes": "",
            "prompt": "Create a kids shirt scene but this row is not tagged as child shirt.",
        }

        self.assertFalse(self.service._prompt_batch_item_matches_query(item, "áo trẻ em"))

    def test_user_assistant_removes_run_auto_when_no_trello_candidate(self) -> None:
        asyncio.run(
            self.store.replace_trello_config(
                TrelloConfig(api_key="key", token="token", board_id="board123", list_id="ready-list")
            )
        )

        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""},
            clear=False,
        ), patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_board_lists",
            return_value=[{"id": "ready-list", "name": "Ready for AI"}],
        ), patch.object(
            self.service,
            "_trello_get_json",
            return_value=[],
        ):
            result = asyncio.run(
                self.service.answer_user_assistant(UserAssistantRequest(question="tôi muốn làm ảnh về đồ chơi gỗ"))
            )

        action_names = [action.get("action") for action in result["suggested_actions"]]
        self.assertIn("apply_product_filter", action_names)
        self.assertNotIn("run_auto_trello", action_names)
        self.assertIn("chưa tìm thấy card", result["answer"])
        self.assertIn("chưa thấy card", result["context_summary"])

    def test_user_assistant_uses_gemini_when_configured(self) -> None:
        asyncio.run(
            self.service.update_integration_config(
                IntegrationConfigUpdateRequest(
                    gemini_api_key="gem-key",
                    gemini_model="gemini-2.5-flash",
                )
            )
        )

        with patch.object(self.service, "_generate_user_assistant_with_gemini", return_value="Gemini hướng dẫn trong app."):
            result = asyncio.run(
                self.service.answer_user_assistant(
                    UserAssistantRequest(question="Sheet prompt cần điền như nào?", context="đang ở Auto Trello")
                )
            )

        self.assertEqual("gemini", result["engine"])
        self.assertEqual("Gemini", result["engine_label"])
        self.assertEqual("gemini-2.5-flash", result["model"])
        self.assertEqual("Gemini hướng dẫn trong app.", result["answer"])

    def test_flow_operator_plan_builds_actionable_automation_plan(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False):
            result = asyncio.run(
                self.service.plan_flow_operator(
                    FlowOperatorRequest(
                        instruction="Dùng AI của Flow làm automation tạo ảnh về áo trẻ em rồi gửi Telegram duyệt",
                        run_mode="auto",
                    )
                )
            )

        self.assertEqual("local", result["engine"])
        self.assertEqual("áo trẻ em", result["product_filter"])
        self.assertIn("Trello", result["summary"])
        self.assertIn("Google Flow Agent", result["flow_prompt"])
        self.assertIn("generate exactly 12", result["flow_prompt"])
        self.assertIn("selected Trello attachment", result["flow_prompt"])
        action_names = [action.get("action") for action in result["suggested_actions"]]
        self.assertIn("apply_product_filter", action_names)
        self.assertIn("apply_flow_ai_prompt", action_names)
        self.assertIn("open_flow_project", action_names)
        self.assertIn("run_auto_trello", action_names)
        run_action = next(action for action in result["suggested_actions"] if action.get("action") == "run_auto_trello")
        self.assertTrue(run_action["requires_confirmation"])
        self.assertNotIn("gem-key", result["context_summary"])

    def test_user_assistant_attaches_flow_operator_plan_when_requested(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False):
            result = asyncio.run(
                self.service.answer_user_assistant(
                    UserAssistantRequest(question="Tích hợp AI của Flow để tự thao tác thành hệ thống automation")
                )
            )

        self.assertIn("Flow AI Operator", result["answer"])
        self.assertTrue(result["flow_operator_plan"])
        self.assertEqual("Flow AI Operator", result["flow_operator_plan"]["title"])
        action_names = [action.get("action") for action in result["suggested_actions"]]
        self.assertIn("apply_flow_ai_prompt", action_names)
        self.assertIn("plan_flow_ai_operator", action_names)
        self.assertEqual("", result["flow_operator_plan"]["product_filter"])

    def test_user_assistant_does_not_extract_shirt_from_thao_tac_or_automation(self) -> None:
        product = self.service._extract_user_assistant_product_filter(
            "Tích hợp AI của Flow để tự thao tác thành hệ thống automation"
        )

        self.assertEqual("", product)

    def test_user_assistant_extracts_doll_from_short_test_request(self) -> None:
        product = self.service._extract_user_assistant_product_filter("test một ảnh búp bê")

        self.assertEqual("búp bê", product)

    def test_user_assistant_extracts_product_after_numeric_batch_count(self) -> None:
        product = self.service._extract_user_assistant_product_filter("tạo 3 ảnh búp bê rồi chạy auto")

        self.assertEqual("búp bê", product)

    def test_user_assistant_does_not_extract_generic_trello_status_text(self) -> None:
        product = self.service._extract_user_assistant_product_filter(
            "kiểm tra Trello Ready for AI và cho biết app sẽ lấy ảnh nào, không chạy tạo ảnh"
        )

        self.assertEqual("", product)

    def test_flow_operator_sanitizes_generic_gemini_product_filter(self) -> None:
        local_plan = {"product_filter": "", "flow_prompt": "x" * 200, "steps": []}
        raw_plan = {"product_filter": "tạo ảnh", "flow_prompt": "y" * 200, "steps": []}

        plan = self.service._normalize_flow_operator_plan(raw_plan, local_plan, "kiểm tra Ready for AI")

        self.assertEqual("", plan["product_filter"])

    def test_flow_operator_uses_gemini_json_when_configured(self) -> None:
        asyncio.run(
            self.service.update_integration_config(
                IntegrationConfigUpdateRequest(
                    gemini_api_key="gem-key",
                    gemini_model="gemini-2.5-flash",
                )
            )
        )
        gemini_plan = {
            "title": "Flow AI Gemini",
            "summary": "Gemini đã lập kế hoạch operator.",
            "product_filter": "gấu bông",
            "flow_prompt": "Use Google Flow Agent as the prompt writer and image-generation operator. Use the selected Trello attachment as the exact teddy bear product reference, analyze the product first, then write internal prompts and generate exactly 12 commercial product images with coherent teddy bear styling, clean white daylight, clean composition, realistic fabric texture, pastel fabric colorway variants, and no extra text or watermark.",
            "steps": [{"label": "Tìm ảnh", "detail": "Dùng card Ready for AI.", "status": "sẵn sàng"}],
            "safety_notes": ["Không chạy nếu chưa thấy card đúng."],
        }

        with patch.object(self.service, "_generate_flow_operator_plan_with_gemini", return_value=gemini_plan):
            result = asyncio.run(
                self.service.plan_flow_operator(
                    FlowOperatorRequest(instruction="Dùng Flow AI tạo ảnh về gấu bông")
                )
            )

        self.assertEqual("gemini", result["engine"])
        self.assertEqual("Flow AI Gemini", result["title"])
        self.assertEqual("gấu bông", result["product_filter"])
        self.assertIn("Google Flow Agent", result["flow_prompt"])
        self.assertIn("generate exactly 12", result["flow_prompt"])
        self.assertIn("apply_flow_ai_prompt", [action.get("action") for action in result["suggested_actions"]])

    def test_flow_module_setting_can_disable_flow_agent(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="cat",
            flow_agent_enabled=True,
            automation_graph={
                "modules": [
                    {
                        "id": "flow",
                        "type": "flow",
                        "settings": {
                            "flowAgentEnabled": False,
                            "flowAgentAutoApprove": False,
                            "imageCount": 3,
                            "imageAspect": "square",
                        },
                    }
                ]
            },
        )

        resolved = self.service._request_with_automation_module_settings(
            request,
            {
                "id": "flow",
                "type": "flow",
                "settings": {
                    "flowAgentEnabled": False,
                    "flowAgentAutoApprove": False,
                    "imageCount": 3,
                    "imageAspect": "square",
                },
            },
        )

        self.assertFalse(resolved.flow_agent_enabled)
        self.assertFalse(resolved.flow_agent_auto_approve)
        self.assertEqual(3, resolved.count)
        self.assertEqual("square", resolved.aspect)

    def test_telegram_review_pack_uses_app_saved_config(self) -> None:
        asyncio.run(
            self.service.update_integration_config(
                IntegrationConfigUpdateRequest(
                    telegram_bot_token="telegram-token",
                    telegram_chat_id="@review_channel",
                )
            )
        )
        request = CreateJobRequest(type="image", prompt="cat")
        artifact = JobArtifact(label="Ảnh 1", url="https://example.com/cat.jpg", mime_type="image/jpeg")
        job = JobRecord(type="image", status="running", title="test")
        asyncio.run(self.store.add_job(job))

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}, clear=False), patch.object(
            self.service,
            "_send_telegram_photo",
        ) as send_photo:
            result = asyncio.run(self.service._send_telegram_review_pack(job.id, request, [artifact]))

        send_photo.assert_called_once()
        self.assertEqual("telegram-token", send_photo.call_args.args[0])
        self.assertEqual("@review_channel", send_photo.call_args.args[1])
        reply_markup = send_photo.call_args.args[4]
        callback_values = [
            button["callback_data"]
            for row in reply_markup["inline_keyboard"]
            for button in row
        ]
        self.assertIn(f"fw:approve:{job.id}:0", callback_values)
        self.assertIn(f"fw:reject:{job.id}:0", callback_values)
        self.assertTrue(result["configured"])
        self.assertEqual(1, result["sent"])
        self.assertEqual(1, result["pending_approvals"])

    def test_sync_telegram_approvals_updates_job_and_approval_node(self) -> None:
        asyncio.run(
            self.service.update_integration_config(
                IntegrationConfigUpdateRequest(
                    telegram_bot_token="telegram-token",
                    telegram_chat_id="@review_channel",
                )
            )
        )
        job = JobRecord(
            type="image",
            status="completed",
            title="test",
            result={
                "automation_execution": {
                    "mode": "graph",
                    "nodes": [
                        {"id": "flow-1", "type": "flow", "status": "completed", "output": {}},
                        {"id": "approval-1", "type": "approval", "status": "running", "output": {}},
                    ],
                    "edges": [],
                    "current_module_id": "approval-1",
                    "completed": False,
                }
            },
            artifacts=[JobArtifact(label="Ảnh 1", url="https://example.com/cat.jpg", mime_type="image/jpeg")],
        )
        asyncio.run(self.store.add_job(job))
        updates = [
            {
                "update_id": 100,
                "callback_query": {
                    "id": "callback-1",
                    "from": {"id": 7, "first_name": "Ellyn", "username": "ellyn"},
                    "message": {"message_id": 42, "chat": {"id": -100}},
                    "data": f"fw:approve:{job.id}:0",
                },
            }
        ]

        with patch.object(self.service, "_telegram_get_updates", side_effect=[updates, []]) as get_updates, patch.object(
            self.service,
            "_telegram_answer_callback_query",
        ) as answer:
            result = asyncio.run(self.service.sync_telegram_approvals())

        self.assertTrue(result["configured"])
        self.assertEqual(1, result["processed"])
        get_updates.assert_any_call("telegram-token")
        get_updates.assert_any_call("telegram-token", 101)
        answer.assert_called_once()
        saved = self.store.get_job(job.id)
        self.assertEqual("approved", saved.result["telegram_approvals"]["0"]["status"])
        self.assertEqual(1, saved.result["telegram_approval_summary"]["approved"])
        approval_node = next(node for node in saved.result["automation_execution"]["nodes"] if node["type"] == "approval")
        self.assertEqual("completed", approval_node["status"])
        self.assertTrue(saved.result["automation_execution"]["completed"])

    def test_telegram_approval_sync_loop_polls_until_cancelled(self) -> None:
        calls = 0

        async def fake_sync() -> dict[str, object]:
            nonlocal calls
            calls += 1
            return {"configured": True, "processed": 0, "approvals": []}

        async def run_loop() -> None:
            task = asyncio.create_task(self.service.run_telegram_approval_sync_loop(interval_s=0.01))
            with patch.object(self.service, "sync_telegram_approvals", side_effect=fake_sync):
                while calls < 2:
                    await asyncio.sleep(0.02)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task

        asyncio.run(run_loop())
        self.assertGreaterEqual(calls, 2)

    def test_prompt_source_preview_reads_pasted_google_sheet_rows(self) -> None:
        table = "\n".join(
            [
                "Product_Key\tProduct_Name\tPrompt_Index\tPrompt_Content\tActive\tNotes",
                "wedding_hoop\tWedding Hoop\t1\tinactive prompt\tFALSE\told",
                "hoops_with_photos\tHoops With Photos\t1\tThe product image showcases a personalized embroidery frame.\tTRUE\tNursery shelf decor",
            ]
        )

        result = asyncio.run(self.service.preview_prompt_source(text=table))

        self.assertEqual(2, result["prompt_count"])
        self.assertEqual(1, result["active_count"])
        self.assertIn("personalized embroidery frame", result["prompt"])
        self.assertEqual("Hoops With Photos", result["selected"]["product"])
        self.assertEqual(1, len(result["items"]))
        self.assertIn("personalized embroidery frame", result["items"][0]["prompt"])

    def test_prompt_source_preview_skips_rows_marked_used(self) -> None:
        table = "\n".join(
            [
                "Product_Key\tProduct_Name\tPrompt_Index\tPrompt_Content\tActive\tUsed\tNotes",
                "hoops_with_photos\tHoops With Photos\t1\told prompt should not run\tTRUE\tTRUE\talready done",
                "hoops_with_photos\tHoops With Photos\t2\tfresh prompt should run\tTRUE\tFALSE\tnew",
            ]
        )

        result = asyncio.run(self.service.preview_prompt_source(text=table))

        self.assertEqual(2, result["prompt_count"])
        self.assertEqual(1, result["used_count"])
        self.assertEqual(1, result["active_count"])
        self.assertEqual("fresh prompt should run", result["prompt"])
        self.assertEqual(3, result["selected"]["row"])
        self.assertEqual("fresh prompt should run", result["items"][0]["prompt"])

    def test_prompt_source_preview_reads_xlsx_upload(self) -> None:
        workbook = io.BytesIO()
        with zipfile.ZipFile(workbook, "w") as archive:
            archive.writestr(
                "xl/workbook.xml",
                """<?xml version="1.0" encoding="UTF-8"?>
                <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
                  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
                  <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
                </workbook>""",
            )
            archive.writestr(
                "xl/_rels/workbook.xml.rels",
                """<?xml version="1.0" encoding="UTF-8"?>
                <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                  <Relationship Id="rId1" Target="worksheets/sheet1.xml"
                    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/>
                </Relationships>""",
            )
            archive.writestr(
                "xl/worksheets/sheet1.xml",
                """<?xml version="1.0" encoding="UTF-8"?>
                <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                  <sheetData>
                    <row r="1">
                      <c r="A1" t="inlineStr"><is><t>Product_Key</t></is></c>
                      <c r="B1" t="inlineStr"><is><t>Prompt_Content</t></is></c>
                      <c r="C1" t="inlineStr"><is><t>Active</t></is></c>
                    </row>
                    <row r="2">
                      <c r="A2" t="inlineStr"><is><t>hoops_with_photos</t></is></c>
                      <c r="B2" t="inlineStr"><is><t>Flow should create the product photo from this prompt.</t></is></c>
                      <c r="C2" t="inlineStr"><is><t>TRUE</t></is></c>
                    </row>
                  </sheetData>
                </worksheet>""",
            )
        upload = UploadFile(filename="prompts.xlsx", file=io.BytesIO(workbook.getvalue()))

        result = asyncio.run(self.service.preview_prompt_source(file=upload))

        self.assertEqual(1, result["prompt_count"])
        self.assertEqual(1, result["active_count"])
        self.assertIn("product photo", result["prompt"])
        self.assertEqual("Flow should create the product photo from this prompt.", result["items"][0]["prompt"])

    def test_prompt_source_preview_reports_sheet_timeout_as_bad_request(self) -> None:
        with patch("flow_web.service.urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(self.service.preview_prompt_source(source_url="https://docs.google.com/spreadsheets/d/sheet-id/edit?gid=0"))

        self.assertEqual(400, ctx.exception.status_code)
        self.assertIn("quá lâu", str(ctx.exception.detail))

    def test_get_auth_status_uses_network_cookies_fallback(self) -> None:
        with patch.object(self.service, "_flow_modules", return_value=(None, lambda: False, None, None, None)), patch.object(
            self.service,
            "_flow_profile_has_auth_cookies",
            return_value=True,
        ):
            status = self.service.get_auth_status()

        self.assertTrue(status.authenticated)

    def test_start_image_search_terms_include_file_stem(self) -> None:
        terms = self.service._start_image_search_terms(r"D:\flow\data\uploads\OIP-2.jfif")

        self.assertIn("D:\\flow\\data\\uploads\\OIP-2.jfif", terms)
        self.assertIn("OIP-2.jfif", terms)
        self.assertIn("OIP-2", terms)
        self.assertIn("oip 2", [item.lower() for item in terms])

    def test_resolve_job_request_assigns_reference_image_roles(self) -> None:
        config = AppConfig(project_id="pid", generation_timeout_s=420)
        request = CreateJobRequest(
            type="image",
            prompt="ghép logo lên áo",
            reference_image_paths=["/tmp/model.jpg", "/tmp/logo.png", "/tmp/tag.png"],
            reference_image_roles=["logo", "base", "reference"],
        )

        resolved = self.service._resolve_job_request(request, config)

        self.assertEqual(["logo", "base", "reference"], resolved.reference_image_roles)

    def test_ordered_reference_media_names_keeps_base_first(self) -> None:
        ordered = self.service._ordered_reference_media_names(
            [
                {"role": "logo", "media_name": "media-logo"},
                {"role": "base", "media_name": "media-model"},
                {"role": "product", "media_name": "media-shirt"},
            ]
        )

        self.assertEqual(["media-model", "media-shirt", "media-logo"], ordered)

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

    def test_video_status_failure_detail_prefers_audio_failure_hint(self) -> None:
        status = SimpleNamespace(
            _raw={
                "media": [
                    {
                        "mediaMetadata": {
                            "mediaStatus": {
                                "mediaGenerationStatus": "MEDIA_GENERATION_STATUS_FAILED",
                                "errorMessage": "Audio generation failed. Please try a different prompt or send feedback.",
                                "userFacingMessage": "You can update your settings to return silent videos.",
                            }
                        }
                    }
                ]
            }
        )

        detail = self.service._video_status_failure_detail(status)

        self.assertIn("Audio generation failed", detail)
        self.assertIn("silent videos", detail)

    def test_humanize_flow_error_maps_audio_generation_failure(self) -> None:
        message = humanize_flow_error(
            "Audio generation failed. Please try a different prompt or send feedback. "
            "You can update your settings to return silent videos."
        )

        self.assertIn("phần tạo audio bị lỗi", message)
        self.assertIn("video im lặng", message)

    def test_classify_job_error_maps_audio_generation_failure(self) -> None:
        snapshot = classify_job_error(
            "Audio generation failed. Please try a different prompt or send feedback. "
            "You can update your settings to return silent videos.",
            job_type="video",
        )

        self.assertEqual("audio", snapshot.category)
        self.assertEqual("Lỗi audio", snapshot.label)

    def test_policy_preflight_notice_warns_for_minor_fashion_edit(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="ghép logo lên áo cho học sinh tuổi teen này và làm đẹp hơn",
            reference_image_paths=["/tmp/model.jpg"],
            reference_image_roles=["base"],
        )

        notice = self.service._policy_preflight_notice(request)

        self.assertIn("người chưa đủ tuổi", notice)
        self.assertIn("mannequin", notice)

    def test_policy_preflight_notice_warns_for_product_video_with_reference_images(self) -> None:
        request = CreateJobRequest(
            type="video",
            prompt="cho logo này lên áo và làm người mẫu đẹp hơn",
            reference_image_paths=["/tmp/shirt.png"],
            reference_image_roles=["product"],
        )

        notice = self.service._policy_preflight_notice(request)

        self.assertIn("ảnh tham chiếu", notice)
        self.assertIn("người mẫu trưởng thành", notice)

    def test_default_title_marks_video_from_image(self) -> None:
        request = CreateJobRequest(
            type="video",
            prompt="samurai",
            start_image_path="/tmp/source.jpg",
        )

        title = self.service._default_title(request)

        self.assertEqual("Tạo video từ ảnh", title)

    def test_default_title_marks_video_with_references_as_auto_video(self) -> None:
        request = CreateJobRequest(
            type="video",
            prompt="quảng cáo áo này",
            reference_image_paths=["/tmp/shirt.png"],
        )

        title = self.service._default_title(request)

        self.assertEqual("Tạo video từ ảnh tham chiếu", title)

    def test_default_title_marks_image_with_references_as_edit(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="ghép logo lên áo",
            reference_image_paths=["/tmp/model.jpg", "/tmp/logo.png"],
        )

        title = self.service._default_title(request)

        self.assertEqual("Chỉnh ảnh từ ảnh tham chiếu", title)

    def test_video_start_frame_prompt_adds_model_and_product_guidance(self) -> None:
        request = CreateJobRequest(
            type="video",
            prompt="quảng cáo chiếc áo hoodie này theo phong cách cinematic",
            reference_image_paths=["/tmp/hoodie.png"],
            reference_image_roles=["product"],
            aspect="landscape",
        )

        prompt = self.service._video_start_frame_prompt(request)

        self.assertIn("photoreal human model", prompt.lower())
        self.assertIn("exact product design", prompt.lower())
        self.assertIn("start frame", prompt.lower())

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

    def test_storyboard_scene_count_prefers_explicit_request(self) -> None:
        count = self.service._storyboard_scene_count("Cảnh 1. Cảnh 2. Cảnh 3.", 6)

        self.assertEqual(6, count)

    def test_local_storyboard_plan_builds_scene_prompts(self) -> None:
        request = StoryboardPlanRequest(
            script=(
                "Cảnh 1: Một kiếm sĩ samurai đứng trong mưa trước cổng đền cổ.\n\n"
                "Cảnh 2: Anh ta rút kiếm và lao về phía đối thủ giữa sân đá.\n\n"
                "Cảnh 3: Hai người khóa kiếm, nước mưa bắn tung và đèn lồng rung mạnh."
            ),
            style="cinematic dramatic",
            must_include="mưa lớn, đèn lồng đỏ, giáp samurai",
            avoid="text, watermark",
            aspect="landscape",
        )

        scenes = self.service._local_storyboard_plan(request, 3, [])

        self.assertEqual(3, len(scenes))
        self.assertEqual(1, scenes[0].index)
        self.assertIn("storyboard keyframe", scenes[0].image_prompt.lower())
        self.assertIn("same subject identity", scenes[0].image_prompt.lower())
        self.assertIn("Giữ cùng nhân vật chính", scenes[0].continuity)
        self.assertIn("mưa lớn", scenes[0].continuity)

    def test_local_storyboard_plan_honors_explicit_count_for_short_script(self) -> None:
        request = StoryboardPlanRequest(
            script="Một shop online nhận ảnh từ Trello, tạo ảnh bằng Flow, duyệt Telegram rồi lưu lại đúng card.",
            style="software explainer",
            must_include="Trello, Flow, Telegram",
            aspect="landscape",
            scene_count=3,
        )

        scenes = self.service._local_storyboard_plan(request, 3, [])

        self.assertEqual(3, len(scenes))
        self.assertEqual([1, 2, 3], [scene.index for scene in scenes])
        self.assertIn("Mở đầu", scenes[0].beat)
        self.assertIn("Phát triển", scenes[1].beat)
        self.assertIn("Cao trào", scenes[2].beat)

    def test_gemini_storyboard_request_allows_large_json_outputs(self) -> None:
        request = StoryboardPlanRequest(script="Một shop online chạy automation Trello, Flow và Telegram.", scene_count=3)

        payload = self.service._gemini_storyboard_request(request, [], 3)

        self.assertGreaterEqual(payload["generationConfig"]["maxOutputTokens"], 4096)

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
        self._batch_pause_env = patch.dict(
            os.environ,
            {
                "FLOW_AGENT_BATCH_PAUSE_MIN_S": "0",
                "FLOW_AGENT_BATCH_PAUSE_MAX_S": "0",
            },
            clear=False,
        )
        self._batch_pause_env.start()
        self.addCleanup(self._batch_pause_env.stop)
        # Keep the Gemini design-inventory step offline in tests; individual tests re-patch it on the instance.
        self._design_inventory_patch = patch.object(
            FlowWebService,
            "_gemini_describe_trello_source_design",
            return_value={"inventory": ""},
        )
        self._design_inventory_patch.start()
        self.addCleanup(self._design_inventory_patch.stop)
        self.store = StateStore()
        self.service = FlowWebService(self.store)

    async def test_flow_agent_quota_check_ignores_stale_pre_submit_message(self) -> None:
        class FakePage:
            async def evaluate(self, *_args: object, **_kwargs: object) -> str:
                return "Bạn đã dùng hết hạn mức về số lượt tạo đối với Nano Banana 2. Hãy thử dùng một mô hình khác. Tác nhân Flow"

        stale_message = "Bạn đã dùng hết hạn mức về số lượt tạo đối với Nano Banana 2. Hãy thử dùng một mô hình khác."

        await self.service._raise_flow_agent_quota_if_visible(FakePage(), ignore_message=stale_message)

    async def test_flow_agent_quota_check_still_raises_for_new_message(self) -> None:
        class FakePage:
            async def evaluate(self, *_args: object, **_kwargs: object) -> str:
                return "Bạn đã dùng hết hạn mức về số lượt tạo đối với Nano Banana 2. Hãy thử dùng một mô hình khác. Tác nhân Flow"

        with self.assertRaises(FlowAgentQuotaError):
            await self.service._raise_flow_agent_quota_if_visible(FakePage(), ignore_message="")

    async def test_flow_agent_try_again_error_retries_via_ui(self) -> None:
        detail = "Đã xảy ra lỗi. Hãy thử lại."

        self.assertTrue(self.service._is_retryable_flow_agent_ui_error(detail))
        self.assertEqual(8.0, self.service._flow_agent_ui_retry_delay_s(detail))

    async def test_generate_images_with_retry_falls_back_to_ui_when_image_model_rejected(self) -> None:
        request = CreateJobRequest(type="image", prompt="run", model="Nano Banana Pro", count=1)
        fake_client = SimpleNamespace()
        fake_images = [SimpleNamespace(media_name="img-1")]
        job = JobRecord(type="image", status="running", title="test")
        await self.store.add_job(job)

        with patch.object(
            self.service,
            "_generate_images_once",
            AsyncMock(side_effect=RuntimeError("invalid imageModelName GEMINI_3_PRO_IMAGE")),
        ) as generate_once, patch.object(
            self.service,
            "_reload_flow_project_page",
            AsyncMock(),
        ) as reload_page, patch.object(
            self.service,
            "_generate_images_via_ui",
            AsyncMock(return_value=fake_images),
        ) as via_ui:
            result = await self.service._generate_images_with_retry(fake_client, job.id, request, [])

        self.assertEqual(fake_images, result)
        generate_once.assert_awaited_once_with(fake_client, request, [])
        reload_page.assert_awaited_once_with(fake_client)
        via_ui.assert_awaited_once_with(fake_client, request, [], job_id=job.id)

    async def test_wait_for_flow_agent_source_attachment_accepts_replaced_chip_count(self) -> None:
        class FakePage:
            async def evaluate(self, *_args: object, **_kwargs: object) -> dict:
                return {
                    "visible": True,
                    "count": 9,
                    "ready_count": 9,
                    "busy_count": 0,
                    "media_count": 4,
                    "chip_count": 5,
                    "ready_labels": ["source-card-new"],
                    "detail": "attachments=9 media=4 chips=5",
                }

        ok, detail = await self.service._wait_for_flow_agent_source_attachment(
            FakePage(),
            {"visible": True, "count": 11, "ready_count": 11, "ready_labels": ["source-card-old"], "detail": "attachments=11 media=6 chips=5"},
            timeout_s=1,
        )

        self.assertTrue(ok)
        self.assertIn("ready attachment changed", detail)

    async def test_wait_for_flow_agent_source_attachment_accepts_new_composer_thumbnail(self) -> None:
        class FakePage:
            async def evaluate(self, *_args: object, **_kwargs: object) -> dict:
                return {
                    "visible": True,
                    "count": 14,
                    "ready_count": 14,
                    "busy_count": 0,
                    "composer_ready_count": 1,
                    "composer_busy_count": 0,
                    "media_count": 7,
                    "chip_count": 0,
                    "ready_labels": ["old-gallery-thumb"],
                    "composer_ready_labels": ["composer image preview"],
                    "detail": "attachments=14 ready=14 busy=0 composerReady=1 composerBusy=0 media=7 chips=0 files=0 cards=7 allMedia=23",
                }

        ok, detail = await self.service._wait_for_flow_agent_source_attachment(
            FakePage(),
            {
                "visible": True,
                "count": 14,
                "ready_count": 14,
                "busy_count": 0,
                "composer_ready_count": 0,
                "composer_busy_count": 0,
                "ready_labels": ["old-gallery-thumb"],
                "composer_ready_labels": [],
                "detail": "attachments=14 ready=14 busy=0 composerReady=0 composerBusy=0",
            },
            timeout_s=1,
        )

        self.assertTrue(ok)
        self.assertIn("composer attachment ready", detail)

    async def test_wait_for_flow_agent_source_attachment_accepts_stable_ready_after_file_attach(self) -> None:
        class FakePage:
            async def evaluate(self, *_args: object, **_kwargs: object) -> dict:
                return {
                    "visible": True,
                    "count": 16,
                    "ready_count": 16,
                    "busy_count": 0,
                    "composer_ready_count": 0,
                    "composer_busy_count": 0,
                    "media_count": 8,
                    "chip_count": 0,
                    "file_input_count": 0,
                    "card_count": 8,
                    "ready_labels": ["flow-agent-ready-gallery"],
                    "composer_ready_labels": [],
                    "detail": "attachments=16 ready=16 busy=0 composerReady=0 composerBusy=0 media=8 chips=0 files=0 cards=8 allMedia=23",
                }

        ok, detail = await self.service._wait_for_flow_agent_source_attachment(
            FakePage(),
            {
                "visible": True,
                "count": 16,
                "ready_count": 16,
                "busy_count": 0,
                "composer_ready_count": 0,
                "composer_busy_count": 0,
                "ready_labels": ["flow-agent-ready-gallery"],
                "composer_ready_labels": [],
            },
            timeout_s=1,
            accept_stable_ready_after_attach=True,
        )

        self.assertTrue(ok)
        self.assertIn("stable after file attach", detail)

    async def test_wait_for_flow_agent_source_attachment_rejects_selected_file_input_until_ready(self) -> None:
        class FakePage:
            async def evaluate(self, *_args: object, **_kwargs: object) -> dict:
                return {
                    "visible": True,
                    "count": 1,
                    "ready_count": 0,
                    "busy_count": 0,
                    "media_count": 0,
                    "chip_count": 0,
                    "file_input_count": 1,
                    "composer_ready_count": 0,
                    "composer_busy_count": 0,
                    "detail": "attachments=1 ready=0 media=0 chips=0 files=1",
                }

        ok, detail = await self.service._wait_for_flow_agent_source_attachment(
            FakePage(),
            {"visible": True, "count": 0, "detail": "attachments=0 media=0 chips=0 files=0"},
            timeout_s=1,
        )

        self.assertFalse(ok)
        self.assertIn("no new ready attachment visible", detail)

    async def test_flow_agent_attachment_snapshot_scans_shadow_dom_and_file_inputs(self) -> None:
        class FakePage:
            def __init__(self) -> None:
                self.scripts: list[str] = []

            @property
            def script(self) -> str:
                return "\n".join(self.scripts)

            async def evaluate(self, script: str) -> dict:
                self.scripts.append(script)
                if "composer-chip-probe" in script:
                    return {"composer_chip_count": 0, "composer_chip_labels": [], "composer_chip_detail": "composerChips=0 chipRemove=0 chipMedia=0"}
                return {
                    "visible": True,
                    "count": 1,
                    "ready_count": 0,
                    "busy_count": 0,
                    "composer_ready_count": 0,
                    "composer_busy_count": 0,
                    "media_count": 0,
                    "chip_count": 0,
                    "file_input_count": 1,
                    "ready_labels": [],
                    "composer_ready_labels": [],
                    "detail": "attachments=1 media=0 chips=0 files=1 cards=0 allMedia=0",
                }

        page = FakePage()
        snapshot = await self.service._flow_agent_panel_attachment_snapshot(page)

        self.assertEqual(1, snapshot["count"])
        self.assertEqual(0, snapshot["ready_count"])
        self.assertIn("deepQuery", page.script)
        self.assertIn("shadowRoot", page.script)
        self.assertIn("fileInputsWithFiles", page.script)
        self.assertIn("inPanelAttachmentArea", page.script)
        self.assertIn("composerReady", page.script)
        self.assertIn("inCurrentComposer", page.script)
        self.assertIn("allMedia", page.script)
        self.assertIn("composer-chip-probe", page.script)
        self.assertEqual(0, snapshot["composer_chip_count"])
        self.assertIn("composerChips=0", snapshot["detail"])

    async def test_flow_agent_source_attachment_accepts_new_composer_chip(self) -> None:
        class FakePage:
            async def evaluate(self, script: str, *_args: object) -> dict:
                if "composer-chip-probe" in script:
                    return {"composer_chip_count": 1, "composer_chip_labels": ["cancel close"], "composer_chip_detail": "composerChips=1 chipRemove=1 chipMedia=1"}
                return {
                    "visible": True,
                    "count": 0,
                    "ready_count": 0,
                    "busy_count": 0,
                    "composer_ready_count": 0,
                    "composer_busy_count": 0,
                    "ready_labels": [],
                    "composer_ready_labels": [],
                    "detail": "attachments=0 ready=0 media=0 chips=0 files=0 cards=0 allMedia=0",
                }

        ok, detail = await self.service._wait_for_flow_agent_source_attachment(
            FakePage(),
            {"visible": True, "count": 0, "ready_count": 0, "composer_chip_count": 0, "detail": "attachments=0"},
            timeout_s=2,
            source_file_name="trello-abc12345-1.jpeg",
        )

        self.assertTrue(ok)
        self.assertIn("composer chip added 0->1", detail)

    async def test_acquire_isolated_flow_agent_page_opens_fresh_agent_tab_each_time(self) -> None:
        class FakePage:
            def __init__(self) -> None:
                self.front_count = 0

            def is_closed(self) -> bool:
                return False

            async def bring_to_front(self) -> None:
                self.front_count += 1

        class FakeContext:
            def __init__(self) -> None:
                self.new_page_count = 0

            async def new_page(self) -> FakePage:
                self.new_page_count += 1
                return FakePage()

        context = FakeContext()
        browser = SimpleNamespace(context=context)
        client = SimpleNamespace(_bm=browser)

        with patch.object(self.service, "_ensure_valid_flow_project_page", new=AsyncMock(return_value=None)) as ensure_page:
            first_page, first_detail = await self.service._acquire_isolated_flow_agent_page(client, "https://labs.google/fx/tools/flow/project/pid")
            second_page, second_detail = await self.service._acquire_isolated_flow_agent_page(client, "https://labs.google/fx/tools/flow/project/pid")

        self.assertEqual(2, context.new_page_count)
        self.assertIsNot(first_page, second_page)
        self.assertEqual("new isolated project tab", first_detail)
        self.assertEqual("new isolated project tab", second_detail)
        self.assertEqual(2, ensure_page.await_count)

    async def test_trello_source_validation_retries_transient_gemini_json_failure(self) -> None:
        source = self.uploads_dir / "source.jpg"
        source.write_bytes(b"source")
        artifact = JobArtifact(label="Ảnh 1", media_name="media", local_path=str(self.downloads_dir / "out.jpg"), mime_type="image/jpeg")
        Path(artifact.local_path).write_bytes(b"generated")
        request = CreateJobRequest(
            type="image",
            prompt="cat",
            trello_enabled=True,
            trello_card_id="source-card",
            reference_image_paths=[str(source)],
            automation_graph={
                "modules": [
                    {"id": "trello_source", "type": "trello_source", "enabled": True},
                    {"id": "flow", "type": "flow", "enabled": True},
                    {"id": "trello", "type": "trello", "enabled": True},
                ]
            },
        )
        job = JobRecord(type="image", status="running", title="test")
        await self.store.add_job(job)

        with patch.object(
            self.service,
            "_artifact_validation_image_bytes",
            new=AsyncMock(return_value=(b"generated", "image/jpeg")),
        ), patch.object(
            self.service,
            "_gemini_validate_trello_source_artifacts",
            side_effect=[
                RuntimeError("Gemini không trả về JSON kiểm tra ảnh hợp lệ."),
                {"ok": True, "reason": "matches", "bad_indexes": [], "confidence": 0.9},
            ],
        ) as validate:
            await self.service._validate_trello_source_artifacts_before_upload(job.id, request, [artifact])

        self.assertEqual(2, validate.call_count)
        saved = self.store.get_job(job.id)
        self.assertTrue(any("thử lại lần 2" in entry.message for entry in saved.logs))

    async def test_trello_source_validation_blocks_upload_on_gemini_json_outage(self) -> None:
        source = self.uploads_dir / "source.jpg"
        source.write_bytes(b"source")
        artifact = JobArtifact(label="Ảnh 1", media_name="media", local_path=str(self.downloads_dir / "out.jpg"), mime_type="image/jpeg")
        Path(artifact.local_path).write_bytes(b"generated")
        request = CreateJobRequest(
            type="image",
            prompt="cat",
            trello_enabled=True,
            trello_card_id="source-card",
            reference_image_paths=[str(source)],
            automation_graph={
                "modules": [
                    {"id": "trello_source", "type": "trello_source", "enabled": True},
                    {"id": "flow", "type": "flow", "enabled": True},
                    {"id": "trello", "type": "trello", "enabled": True},
                ]
            },
        )
        job = JobRecord(type="image", status="running", title="test")
        await self.store.add_job(job)

        with patch.object(
            self.service,
            "_artifact_validation_image_bytes",
            new=AsyncMock(return_value=(b"generated", "image/jpeg")),
        ), patch.object(
            self.service,
            "_gemini_validate_trello_source_artifacts",
            side_effect=RuntimeError("Gemini không trả về JSON kiểm tra ảnh hợp lệ."),
        ) as validate:
            with self.assertRaises(RuntimeError) as ctx:
                await self.service._validate_trello_source_artifacts_before_upload(job.id, request, [artifact])

        # The QA outage is retried once, then the upload is held instead of shipping unverified designs.
        self.assertEqual(2, validate.call_count)
        self.assertIn("Gemini QA không chạy được", str(ctx.exception))
        self.assertTrue(self.service._auto_trello_is_design_qa_unavailable(str(ctx.exception)))
        self.assertFalse(self.service._auto_trello_is_design_qa_rejection(str(ctx.exception)))
        self.assertFalse(self.service._auto_trello_should_stop_on_child_error(str(ctx.exception)))
        saved = self.store.get_job(job.id)
        messages = [entry.message for entry in saved.logs]
        self.assertTrue(any("không upload Trello khi chưa kiểm tra được thiết kế" in message for message in messages))
        self.assertFalse(any("vẫn upload" in message for message in messages))

    def _trello_source_request(self, source: Path) -> CreateJobRequest:
        return CreateJobRequest(
            type="image",
            prompt="cat",
            trello_enabled=True,
            trello_card_id="source-card",
            reference_image_paths=[str(source)],
            automation_graph={
                "modules": [
                    {"id": "trello_source", "type": "trello_source", "enabled": True},
                    {"id": "flow", "type": "flow", "enabled": True},
                    {"id": "trello", "type": "trello", "enabled": True},
                ]
            },
        )

    async def test_trello_source_validation_splits_into_smaller_chunks_on_bad_json(self) -> None:
        source = self.uploads_dir / "source.jpg"
        source.write_bytes(b"source")
        artifacts = []
        for index in range(8):
            path = self.downloads_dir / f"out-{index}.jpg"
            path.write_bytes(b"generated")
            artifacts.append(JobArtifact(label=f"Ảnh {index + 1}", media_name=f"media-{index}", local_path=str(path), mime_type="image/jpeg"))
        request = self._trello_source_request(source)
        job = JobRecord(type="image", status="running", title="test")
        await self.store.add_job(job)

        calls: list[int] = []

        def _validate(_request: Any, _source: str, chunk: list[Any]) -> dict[str, Any]:
            calls.append(len(chunk))
            if len(chunk) > 4:
                raise RuntimeError("Gemini cắt phản hồi kiểm tra ảnh vì MAX_TOKENS nên JSON không hợp lệ.")
            return {"ok": True, "reason": "", "bad_indexes": [], "confidence": 0.9}

        with patch.object(
            self.service,
            "_artifact_validation_image_bytes",
            new=AsyncMock(return_value=(b"generated", "image/jpeg")),
        ), patch.object(self.service, "_gemini_validate_trello_source_artifacts", side_effect=_validate):
            accepted = await self.service._validate_trello_source_artifacts_before_upload(job.id, request, artifacts)

        # 8 images: full-set call fails twice, then two 4-image chunks succeed.
        self.assertEqual([8, 8, 4, 4], calls)
        self.assertEqual(artifacts, accepted)
        messages = [entry.message for entry in self.store.get_job(job.id).logs]
        self.assertTrue(any("chia nhỏ 4 ảnh/lần" in message for message in messages))
        self.assertTrue(any("đã xác nhận ảnh generated khớp thiết kế" in message for message in messages))

    async def test_trello_source_validation_merges_rejections_across_chunks(self) -> None:
        source = self.uploads_dir / "source.jpg"
        source.write_bytes(b"source")
        artifacts = []
        for index in range(8):
            path = self.downloads_dir / f"out-{index}.jpg"
            path.write_bytes(b"generated")
            artifacts.append(JobArtifact(label=f"Ảnh {index + 1}", media_name=f"media-{index}", local_path=str(path), mime_type="image/jpeg"))
        request = self._trello_source_request(source)
        job = JobRecord(type="image", status="running", title="test")
        await self.store.add_job(job)

        def _validate(_request: Any, _source: str, chunk: list[Any]) -> dict[str, Any]:
            if len(chunk) > 4:
                raise RuntimeError("Gemini không trả về JSON kiểm tra ảnh hợp lệ.")
            first_index = chunk[0][0]
            if first_index == 4:
                return {"ok": False, "reason": "Index 5 has an invented wooden tag", "bad_indexes": [5], "confidence": 0.9}
            return {"ok": True, "reason": "", "bad_indexes": [], "confidence": 0.9}

        with patch.object(
            self.service,
            "_artifact_validation_image_bytes",
            new=AsyncMock(return_value=(b"generated", "image/jpeg")),
        ), patch.object(self.service, "_gemini_validate_trello_source_artifacts", side_effect=_validate):
            accepted = await self.service._validate_trello_source_artifacts_before_upload(job.id, request, artifacts)

        # One flagged image (index 5) is dropped, the other seven are uploaded as-is.
        self.assertEqual(7, len(accepted))
        self.assertNotIn(artifacts[5], accepted)
        messages = [entry.message for entry in self.store.get_job(job.id).logs]
        self.assertTrue(any("loại 1/8 ảnh lệch thiết kế (ảnh 6)" in message and "invented wooden tag" in message for message in messages))
        self.assertTrue(any("không tạo bù phần thiếu" in message for message in messages))

    async def test_trello_source_validation_rejects_set_when_too_few_images_pass(self) -> None:
        source = self.uploads_dir / "source.jpg"
        source.write_bytes(b"source")
        artifacts = []
        for index in range(4):
            path = self.downloads_dir / f"out-{index}.jpg"
            path.write_bytes(b"generated")
            artifacts.append(JobArtifact(label=f"Ảnh {index + 1}", media_name=f"media-{index}", local_path=str(path), mime_type="image/jpeg"))
        request = self._trello_source_request(source)
        job = JobRecord(type="image", status="running", title="test")
        await self.store.add_job(job)

        with patch.object(
            self.service,
            "_artifact_validation_image_bytes",
            new=AsyncMock(return_value=(b"generated", "image/jpeg")),
        ), patch.object(
            self.service,
            "_gemini_validate_trello_source_artifacts",
            return_value={"ok": False, "reason": "different dinosaur design", "bad_indexes": [0, 1, 3], "confidence": 0.9},
        ):
            with self.assertRaises(RuntimeError) as ctx:
                await self.service._validate_trello_source_artifacts_before_upload(job.id, request, artifacts)

        self.assertIn("ảnh lỗi: 1, 2, 4", str(ctx.exception))
        self.assertIn("chỉ còn 1/4 ảnh đạt", str(ctx.exception))
        self.assertTrue(self.service._auto_trello_is_design_qa_rejection(str(ctx.exception)))

        with patch.object(
            self.service,
            "_artifact_validation_image_bytes",
            new=AsyncMock(return_value=(b"generated", "image/jpeg")),
        ), patch.object(
            self.service,
            "_gemini_validate_trello_source_artifacts",
            return_value={"ok": False, "reason": "another product entirely", "bad_indexes": [], "confidence": 0.9},
        ):
            with self.assertRaises(RuntimeError):
                await self.service._validate_trello_source_artifacts_before_upload(job.id, request, artifacts)

    async def test_content_review_move_accepts_partial_sets_above_minimum(self) -> None:
        job = JobRecord(type="image", status="running", title="test")
        await self.store.add_job(job)
        cards = [
            {"id": "card-1", "_flow_output_count": 2, "name": "Christmas Dress Baby"},
            {"id": "card-1", "_flow_output_count": 9, "name": "Christmas Dress Baby"},
            {"id": "card-1", "_flow_output_count": 11, "name": "Christmas Dress Baby"},
        ]
        with patch.object(self.service, "_trello_image_card_by_id", side_effect=cards), patch.object(
            self.service, "_flow_operator_target_count_for_card", return_value=12
        ), patch.object(self.service, "_trello_content_review_list_id", return_value="list-review"), patch.object(
            self.service, "_trello_move_card_to_list", return_value={"id": "card-1", "url": "https://trello.example/c/card-1"}
        ) as move:
            blocked = await self.service._move_trello_card_to_content_review_if_complete(job.id, "k", "t", "board", "card-1")
            trimmed = await self.service._move_trello_card_to_content_review_if_complete(job.id, "k", "t", "board", "card-1", qa_dropped=3)
            short = await self.service._move_trello_card_to_content_review_if_complete(job.id, "k", "t", "board", "card-1")

        self.assertFalse(blocked["moved"])
        self.assertEqual("not_enough_outputs", blocked["reason"])
        self.assertTrue(trimmed["moved"])
        self.assertTrue(short["moved"])
        self.assertEqual(2, move.call_count)
        messages = [entry.message for entry in self.store.get_job(job.id).logs]
        self.assertTrue(any("9/12 anh (3 anh bi QA loai, khong tao bu)" in message for message in messages))
        self.assertTrue(any("11/12 anh (Flow tra thieu anh, khong tao bu)" in message for message in messages))

    def test_auto_trello_scan_moves_partial_cards_to_review_instead_of_regenerating(self) -> None:
        request = CreateJobRequest(type="image", title="Auto image from Trello card", count=12, trello_board_id="board-1")
        card = {
            "id": "card-partial",
            "shortLink": "partial",
            "idList": "ready",
            "idBoard": "board-1",
            "name": "advent_calendar",
            "desc": "",
            "url": "https://trello.example/c/partial",
            "_image_attachments": [{"id": "att-p", "name": "calendar.jpeg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["att-p"],
            "_flow_output_count": 11,
        }
        with patch.object(self.service, "_trello_credentials", return_value=("trello-key", "trello-token")), patch.object(
            self.service, "_trello_content_review_list_id", return_value="list-review"
        ), patch.object(self.service, "_trello_move_card_to_list", return_value={"id": "card-partial"}) as move:
            items = self.service._trello_ai_prompt_items_for_image_cards([card], request, 40)

        self.assertEqual([], items)
        self.assertEqual("complete_output_set", card["_auto_trello_skip_code"])
        self.assertIn("11/12 anh output", card["_auto_trello_skip_reason"])
        self.assertTrue(card["_auto_trello_moved_to_review"])
        move.assert_called_once_with("trello-key", "trello-token", "card-partial", "list-review")

    async def test_retry_trello_upload_refetches_images_from_flow_urls(self) -> None:
        source = self.uploads_dir / "source.jpg"
        source.write_bytes(b"source")
        stale = self.downloads_dir / "visible-flow-1.jpg.jpg"
        stale.write_bytes(b"another-jobs-image")
        request = self._trello_source_request(source)
        job = JobRecord(
            type="image",
            status="failed",
            title="held",
            input=_model_dump_for_test(request),
            error="Gemini QA không chạy được nên app chưa upload Trello",
            artifacts=[
                JobArtifact(label="Ảnh 1", media_name="m1", url="https://flow-content.example/1", local_path=str(stale), mime_type="image/jpeg"),
                JobArtifact(label="Ảnh 2", media_name="m2", url="https://flow-content.example/2", local_path=str(stale), mime_type="image/jpeg"),
            ],
        )
        await self.store.add_job(job)

        archived: dict[str, Any] = {}

        async def _archive(job_id: str, _request: CreateJobRequest, artifacts: list[JobArtifact]) -> dict[str, Any]:
            archived["paths"] = [artifact.local_path for artifact in artifacts]
            archived["bytes"] = [Path(artifact.local_path).read_bytes() for artifact in artifacts]
            return {"configured": True, "sent": len(artifacts), "failed": 0, "card_id": "source-card"}

        with patch.object(self.service, "_read_remote_file", return_value=(b"fresh-image", "image/jpeg")) as fetch, patch.object(
            self.service, "_archive_trello_artifacts", side_effect=_archive
        ):
            payload = await self.service.retry_trello_upload(job.id)

        self.assertEqual("completed", payload["status"])
        self.assertEqual(2, payload["sent"])
        self.assertEqual(2, fetch.call_count)
        self.assertTrue(all(f"retry-{job.id[:8]}-" in path for path in archived["paths"]))
        self.assertEqual([b"fresh-image", b"fresh-image"], archived["bytes"])
        saved = self.store.get_job(job.id)
        self.assertEqual("completed", saved.status)
        self.assertEqual("", saved.error)
        self.assertTrue(saved.result.get("trello_retry_upload"))
        self.assertEqual(b"another-jobs-image", stale.read_bytes())

    async def test_retry_trello_upload_rejects_running_jobs_and_missing_urls(self) -> None:
        source = self.uploads_dir / "source.jpg"
        source.write_bytes(b"source")
        request = self._trello_source_request(source)
        running = JobRecord(type="image", status="running", title="busy", input=_model_dump_for_test(request), artifacts=[JobArtifact(label="Ảnh 1", url="https://x/1")])
        await self.store.add_job(running)
        with self.assertRaises(HTTPException) as ctx:
            await self.service.retry_trello_upload(running.id)
        self.assertEqual(409, ctx.exception.status_code)

        no_url = JobRecord(type="image", status="failed", title="no-url", input=_model_dump_for_test(request), artifacts=[JobArtifact(label="Ảnh 1", local_path="C:/missing.jpg")])
        await self.store.add_job(no_url)
        with self.assertRaises(HTTPException) as ctx:
            await self.service.retry_trello_upload(no_url.id)
        self.assertEqual(400, ctx.exception.status_code)
        self.assertIn("không còn URL Flow", ctx.exception.detail)
        self.assertEqual("failed", self.store.get_job(no_url.id).status)

    async def test_plan_storyboard_returns_local_scenes_when_gemini_is_not_configured(self) -> None:
        with patch.object(self.service, "ensure_media_skill_library", AsyncMock(return_value={})), patch.object(
            self.service,
            "_gemini_api_key",
            return_value="",
        ):
            payload = await self.service.plan_storyboard(
                StoryboardPlanRequest(
                    script=(
                        "Mở đầu là cảnh một cô gái đứng trước cửa hàng nhạc cụ vào buổi tối.\n\n"
                        "Sau đó cô bước vào trong, chạm tay vào cây đàn piano đen bóng dưới ánh đèn ấm.\n\n"
                        "Cuối cùng cô ngồi xuống chơi một đoạn ngắn, căn phòng phản chiếu ánh sáng vàng."
                    ),
                    style="cinematic luxury",
                    must_include="đàn piano đen, ánh sáng vàng",
                    aspect="landscape",
                    scene_count=3,
                )
            )

        self.assertEqual("local", payload["engine"])
        self.assertEqual(3, payload["scene_count"])
        self.assertEqual(3, len(payload["items"]))
        self.assertIn("storyboard", payload["items"][0]["image_prompt"].lower())
        self.assertIn("cảnh", payload["items"][0]["continuity"].lower())

    async def test_prepare_video_start_image_from_references_downloads_intermediate_frame(self) -> None:
        job = JobRecord(type="video", status="running", title="test")
        await self.store.add_job(job)
        request = CreateJobRequest(
            type="video",
            prompt="quảng cáo chiếc áo này với người mẫu",
            reference_image_paths=["/tmp/shirt.png"],
            reference_image_roles=["product"],
            aspect="landscape",
            timeout_s=300,
        )
        generated_image = SimpleNamespace(fife_url="https://example.com/frame.jpg")
        client = SimpleNamespace(download=AsyncMock(return_value=str(self.uploads_dir / "job-start.jpg")))

        with patch.object(
            self.service,
            "_resolve_image_reference_media",
            AsyncMock(return_value=["media-shirt"]),
        ) as resolve_media, patch.object(
            self.service,
            "_generate_images_with_retry",
            AsyncMock(return_value=[generated_image]),
        ) as generate_images, patch.object(
            self.service,
            "_set_job_progress",
            AsyncMock(),
        ), patch.object(
            self.service.store,
            "append_log",
            AsyncMock(),
        ):
            local_path, prompt = await self.service._prepare_video_start_image_from_references(client, job.id, request)

        resolve_media.assert_awaited_once()
        generate_images.assert_awaited_once()
        client.download.assert_awaited_once()
        self.assertTrue(local_path.endswith("job-start.jpg"))
        self.assertIn("photoreal human model", prompt.lower())
        saved_job = self.store.get_job(job.id)
        self.assertIsNotNone(saved_job)
        self.assertEqual(local_path, saved_job.result.get("auto_start_frame_path"))
        self.assertEqual("/files/uploads/job-start.jpg", saved_job.result.get("auto_start_frame_public_url"))
        self.assertEqual(prompt, saved_job.result.get("auto_start_frame_prompt"))

    async def test_wait_for_new_project_images_polls_project_data(self) -> None:
        empty_project = {"projectContents": {"workflows": []}}
        ready_project = {
            "projectContents": {
                "workflows": [
                    {
                        "name": "wf-new",
                        "projectId": "pid",
                        "metadata": {"displayName": "Prompt title", "createTime": "2026-05-15T08:01:00Z"},
                        "medias": [
                            {
                                "name": "media-new",
                                "projectId": "pid",
                                "image": {"generatedImage": {"fifeUrl": "https://example.com/new.jpg"}},
                            }
                        ],
                    }
                ]
            }
        }
        client = SimpleNamespace(
            _api=SimpleNamespace(get_project_data=AsyncMock(side_effect=[empty_project, ready_project]))
        )

        images = await self.service._wait_for_new_project_images(
            client,
            {"media-old"},
            prompt="Prompt fallback",
            target_count=1,
            timeout_s=5,
        )

        self.assertEqual(1, len(images))
        self.assertEqual("media-new", images[0].media_name)
        self.assertEqual("https://example.com/new.jpg", images[0].fife_url)
        self.assertEqual(2, client._api.get_project_data.await_count)

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

    async def test_with_client_switches_to_next_profile_on_flow_agent_quota(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", headless=False, generation_timeout_s=300))
        profiles = [
            FlowBrowserProfile(index=0, label="Main", path=self.temp_root / "main-profile"),
            FlowBrowserProfile(index=1, label="Backup", path=self.temp_root / "backup-profile"),
        ]
        browsers = [SimpleNamespace(name="browser-1"), SimpleNamespace(name="browser-2")]
        clients = [SimpleNamespace(name="client-1"), SimpleNamespace(name="client-2")]
        calls: list[str] = []

        async def use_client(client: Any) -> str:
            calls.append(client.name)
            if client.name == "client-1":
                raise FlowAgentQuotaError("You've reached your Tools Agent quota limit. Come back tomorrow.")
            return client.name

        with patch.object(self.service, "_flow_profile_specs", return_value=profiles), patch.object(
            self.service,
            "_ensure_shared_browser",
            AsyncMock(side_effect=browsers),
        ) as ensure_shared_browser, patch.object(
            self.service,
            "_build_client_from_shared_browser",
            AsyncMock(side_effect=clients),
        ) as build_client:
            result = await self.service._with_client(use_client)

        self.assertEqual("client-2", result)
        self.assertEqual(["client-1", "client-2"], calls)
        self.assertEqual(2, ensure_shared_browser.await_count)
        self.assertEqual(2, build_client.await_count)
        self.assertTrue(self.service._flow_profile_is_quota_blocked(profiles[0]))
        self.assertFalse(self.service._flow_profile_is_quota_blocked(profiles[1]))

    async def test_with_client_switches_profile_when_source_attachment_is_not_visible(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", headless=False, generation_timeout_s=300))
        profiles = [
            FlowBrowserProfile(index=0, label="Main", path=self.temp_root / "main-profile"),
            FlowBrowserProfile(index=1, label="Backup", path=self.temp_root / "backup-profile"),
        ]
        clients = [SimpleNamespace(name="client-1"), SimpleNamespace(name="client-2")]
        calls: list[str] = []

        async def use_client(client: Any) -> str:
            calls.append(client.name)
            if client.name == "client-1":
                raise RuntimeError(
                    "Auto AI Trello chua keo/upload duoc anh Trello vao Tac nhan Flow. "
                    "no new ready attachment visible 0->0"
                )
            return client.name

        with patch.object(self.service, "_flow_profile_specs", return_value=profiles), patch.object(
            self.service,
            "_ensure_shared_browser",
            AsyncMock(side_effect=[SimpleNamespace(name="browser-1"), SimpleNamespace(name="browser-2")]),
        ), patch.object(
            self.service,
            "_build_client_from_shared_browser",
            AsyncMock(side_effect=clients),
        ):
            result = await self.service._with_client(use_client)

        self.assertEqual("client-2", result)
        self.assertEqual(["client-1", "client-2"], calls)
        self.assertEqual(1, self.service._active_flow_profile_index)
        self.assertFalse(self.service._flow_profile_is_quota_blocked(profiles[0]))

    async def test_with_client_tries_backup_profile_on_flow_agent_try_again_error(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", headless=False, generation_timeout_s=300))
        profiles = [
            FlowBrowserProfile(index=0, label="Main", path=self.temp_root / "main-profile"),
            FlowBrowserProfile(index=1, label="Backup", path=self.temp_root / "backup-profile"),
        ]
        calls: list[str] = []

        async def use_client(client: Any) -> str:
            calls.append(client.name)
            if client.name == "client-1":
                raise RuntimeError("Đã xảy ra lỗi. Hãy thử lại.")
            return client.name

        clients = [SimpleNamespace(name="client-1"), SimpleNamespace(name="client-2")]
        with patch.object(self.service, "_flow_profile_specs", return_value=profiles), patch.object(
            self.service,
            "_flow_agent_try_again_threshold",
            return_value=2,
        ), patch.object(
            self.service,
            "_ensure_shared_browser",
            AsyncMock(side_effect=[SimpleNamespace(name="browser-1"), SimpleNamespace(name="browser-2")]),
        ), patch.object(
            self.service,
            "_build_client_from_shared_browser",
            AsyncMock(side_effect=clients),
        ):
            result = await self.service._with_client(use_client)

        self.assertEqual("client-2", result)
        self.assertEqual(["client-1", "client-2"], calls)
        self.assertFalse(self.service._flow_profile_is_quota_blocked(profiles[0]))
        self.assertFalse(self.service._flow_profile_is_quota_blocked(profiles[1]))
        self.assertEqual(1, self.store.snapshot().flow_profile_agent_retry_error_counts[profiles[0].key])

    async def test_with_client_resets_flow_agent_try_again_counter_after_success(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", headless=False, generation_timeout_s=300))
        profile = FlowBrowserProfile(index=0, label="Main", path=self.temp_root / "main-profile")

        with patch.object(self.service, "_flow_profile_specs", return_value=[profile]), patch.object(
            self.service,
            "_flow_agent_try_again_threshold",
            return_value=10,
        ), patch.object(
            self.service,
            "_ensure_shared_browser",
            AsyncMock(return_value=SimpleNamespace(name="browser-1")),
        ), patch.object(
            self.service,
            "_build_client_from_shared_browser",
            AsyncMock(return_value=SimpleNamespace(name="client-1")),
        ):
            with self.assertRaises(HTTPException):
                await self.service._with_client(lambda client: asyncio.sleep(0, result=(_ for _ in ()).throw(RuntimeError("Đã xảy ra lỗi. Hãy thử lại."))))

        self.assertEqual(1, self.store.snapshot().flow_profile_agent_retry_error_counts[profile.key])

        with patch.object(self.service, "_flow_profile_specs", return_value=[profile]), patch.object(
            self.service,
            "_ensure_shared_browser",
            AsyncMock(return_value=SimpleNamespace(name="browser-1")),
        ), patch.object(
            self.service,
            "_build_client_from_shared_browser",
            AsyncMock(return_value=SimpleNamespace(name="client-1")),
        ):
            result = await self.service._with_client(lambda client: asyncio.sleep(0, result="ok"))

        self.assertEqual("ok", result)
        self.assertNotIn(profile.key, self.store.snapshot().flow_profile_agent_retry_error_counts)

    async def test_with_client_stops_after_last_profile_quota_without_wrapping_to_first(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", headless=False, generation_timeout_s=300))
        profiles = [
            FlowBrowserProfile(index=0, label="Acc1", path=self.temp_root / "acc1-profile"),
            FlowBrowserProfile(index=1, label="Acc2", path=self.temp_root / "acc2-profile"),
        ]
        browsers = [SimpleNamespace(name="browser-1"), SimpleNamespace(name="browser-2")]
        clients = [SimpleNamespace(name="client-1"), SimpleNamespace(name="client-2")]
        calls: list[str] = []

        async def use_client(client: Any) -> str:
            calls.append(client.name)
            raise FlowAgentQuotaError("You've reached your Tools Agent quota limit. Come back tomorrow.")

        with patch.object(self.service, "_flow_profile_specs", return_value=profiles), patch.object(
            self.service,
            "_ensure_shared_browser",
            AsyncMock(side_effect=browsers),
        ) as ensure_shared_browser, patch.object(
            self.service,
            "_build_client_from_shared_browser",
            AsyncMock(side_effect=clients),
        ) as build_client:
            with self.assertRaises(HTTPException) as ctx:
                await self.service._with_client(use_client)

        self.assertEqual(429, ctx.exception.status_code)
        self.assertIn("Tat ca Chrome profile Flow da het quota", str(ctx.exception.detail))
        self.assertEqual(["client-1", "client-2"], calls)
        self.assertEqual(2, ensure_shared_browser.await_count)
        self.assertEqual(2, build_client.await_count)
        self.assertTrue(self.service._flow_profile_is_quota_blocked(profiles[0]))
        self.assertTrue(self.service._flow_profile_is_quota_blocked(profiles[1]))

        with patch.object(self.service, "_flow_profile_specs", return_value=profiles), patch.object(
            self.service,
            "_ensure_shared_browser",
            AsyncMock(),
        ) as ensure_again:
            with self.assertRaises(HTTPException) as second_ctx:
                await self.service._with_client(lambda client: asyncio.sleep(0, result=client.name))

        self.assertEqual(429, second_ctx.exception.status_code)
        ensure_again.assert_not_awaited()

    async def test_with_client_persists_quota_block_across_service_instances(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", headless=False, generation_timeout_s=300))
        profiles = [
            FlowBrowserProfile(index=0, label="Acc1", path=self.temp_root / "acc1-profile"),
            FlowBrowserProfile(index=1, label="Acc2", path=self.temp_root / "acc2-profile"),
        ]

        await self.service._mark_flow_profile_quota_limited(
            profiles[0],
            FlowAgentQuotaError("You've reached your Tools Agent quota limit. Come back tomorrow."),
        )
        reloaded_service = FlowWebService(self.store)
        fake_browser = SimpleNamespace()
        fake_client = SimpleNamespace(name="client-2")

        with patch.object(reloaded_service, "_flow_profile_specs", return_value=profiles), patch.object(
            reloaded_service,
            "_ensure_shared_browser",
            AsyncMock(return_value=fake_browser),
        ) as ensure_shared_browser, patch.object(
            reloaded_service,
            "_build_client_from_shared_browser",
            AsyncMock(return_value=fake_client),
        ):
            result = await reloaded_service._with_client(lambda client: asyncio.sleep(0, result=client.name))

        self.assertEqual("client-2", result)
        ensure_shared_browser.assert_awaited_once()
        self.assertEqual(profiles[1], ensure_shared_browser.await_args.args[0])

    async def test_with_client_uses_profile_specific_project_id(self) -> None:
        await self.store.replace_config(AppConfig(project_id="default-project", headless=False, generation_timeout_s=300))
        profile = FlowBrowserProfile(
            index=0,
            label="Acc2",
            path=self.temp_root / "acc2-profile",
            project_id="4671337a-b32d-468a-a47a-bac90541ca2e",
        )
        fake_browser = SimpleNamespace()
        fake_client = SimpleNamespace(name="profile-client")

        with patch.object(self.service, "_flow_profile_specs", return_value=[profile]), patch.object(
            self.service,
            "_ensure_shared_browser",
            AsyncMock(return_value=fake_browser),
        ), patch.object(
            self.service,
            "_build_client_from_shared_browser",
            AsyncMock(return_value=fake_client),
        ) as build_client:
            result = await self.service._with_client(lambda client: asyncio.sleep(0, result=client.name))

        self.assertEqual("profile-client", result)
        self.assertEqual("4671337a-b32d-468a-a47a-bac90541ca2e", build_client.await_args.kwargs["project_id"])

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

    async def test_open_flow_login_surface_uses_login_page(self) -> None:
        page = SimpleNamespace(url="https://labs.google/fx/vi/tools/flow")
        browser = SimpleNamespace()

        with patch.object(self.service, "_ensure_shared_browser", AsyncMock(return_value=browser)) as ensure_browser, patch.object(
            self.service,
            "_open_login_flow_page",
            AsyncMock(return_value=page),
        ) as open_login_page:
            payload = await self.service.open_flow_login_surface()

        ensure_browser.assert_awaited_once()
        open_login_page.assert_awaited_once_with(browser)
        self.assertTrue(payload["ok"])
        self.assertEqual("https://labs.google/fx/vi/tools/flow", payload["url"])

    async def test_open_flow_login_surface_fails_in_windows_session_zero(self) -> None:
        with patch("flow_web.service.os.name", "nt"), patch.object(
            self.service,
            "_current_windows_session_id",
            return_value=0,
        ), patch.object(self.service, "_ensure_shared_browser", AsyncMock()) as ensure_browser:
            with self.assertRaises(HTTPException) as ctx:
                await self.service.open_flow_login_surface()

        ensure_browser.assert_not_awaited()
        self.assertEqual(400, ctx.exception.status_code)
        self.assertIn("session nền của windows", str(ctx.exception.detail).lower())

    async def test_open_flow_project_surface_opens_saved_project_page(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid-demo"))
        page = SimpleNamespace(url="https://labs.google/fx/vi/tools/flow/project/pid-demo", bring_to_front=AsyncMock())
        browser = SimpleNamespace()

        with patch.object(self.service, "_ensure_shared_browser", AsyncMock(return_value=browser)) as ensure_browser, patch.object(
            self.service,
            "_repair_placeholder_flow_tabs",
            AsyncMock(),
        ) as repair_tabs, patch.object(
            self.service,
            "_acquire_fresh_flow_page",
            AsyncMock(return_value=page),
        ) as acquire_page, patch.object(
            self.service,
            "_ensure_valid_flow_project_page",
            AsyncMock(),
        ) as ensure_project, patch.object(
            self.service,
            "_foreground_native_flow_window",
            AsyncMock(),
        ) as focus_window:
            payload = await self.service.open_flow_project_surface()

        ensure_browser.assert_awaited_once()
        repair_tabs.assert_awaited_once()
        acquire_page.assert_awaited_once()
        ensure_project.assert_awaited_once()
        page.bring_to_front.assert_awaited_once()
        focus_window.assert_awaited_once()
        self.assertTrue(payload["ok"])
        self.assertEqual("https://labs.google/fx/vi/tools/flow/project/pid-demo", payload["url"])

    async def test_open_flow_project_surface_fails_in_windows_session_zero(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid-demo"))
        with patch("flow_web.service.os.name", "nt"), patch.object(
            self.service,
            "_current_windows_session_id",
            return_value=0,
        ), patch.object(self.service, "_ensure_shared_browser", AsyncMock()) as ensure_browser:
            with self.assertRaises(HTTPException) as ctx:
                await self.service.open_flow_project_surface()

        ensure_browser.assert_not_awaited()
        self.assertEqual(400, ctx.exception.status_code)
        self.assertIn("session nền của windows", str(ctx.exception.detail).lower())

    async def test_launch_login_browser_fails_in_windows_session_zero(self) -> None:
        job = JobRecord(type="login", status="queued", title="Đăng nhập Google Flow")
        await self.store.add_job(job)

        with patch("flow_web.service.os.name", "nt"), patch.object(
            self.service,
            "_current_windows_session_id",
            return_value=0,
        ), patch.object(self.service, "_ensure_shared_browser", AsyncMock()) as ensure_browser:
            with self.assertRaises(HTTPException) as ctx:
                await self.service._launch_login_browser(job.id)

        ensure_browser.assert_not_awaited()
        self.assertEqual(400, ctx.exception.status_code)
        self.assertIn("session nền của windows", str(ctx.exception.detail).lower())

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

    async def test_enqueue_job_logs_policy_preflight_notice(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = CreateJobRequest(
            type="image",
            prompt="ghép logo lên áo cho học sinh tuổi teen này và làm đẹp hơn",
            reference_image_paths=["/tmp/model.jpg"],
            reference_image_roles=["base"],
        )

        started = asyncio.Event()

        async def fake_run_flow_job(*args, **kwargs):
            started.set()
            await asyncio.sleep(60)

        with patch.object(self.service, "get_auth_status", return_value=AuthStatus(authenticated=True)), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ):
            job = await self.service.enqueue_job(request)

        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertTrue(any("Cảnh báo an toàn" in log.message for log in saved.logs))
        task = self.service._tasks.get(job.id)
        self.assertIsNotNone(task)
        await started.wait()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

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

    async def test_run_flow_job_retries_audio_failure_with_no_audio_model(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = CreateJobRequest(type="video", prompt="cat cinematic", count=1, model="Veo 3.1 - Fast")
        job = JobRecord(
            type="video",
            status="queued",
            title=self.service._default_title(request),
            input=request.model_dump(mode="json"),
        )
        await self.store.add_job(job)

        video_job = SimpleNamespace(media_name="media-123", workflow_id="wf-123")
        success_status = SimpleNamespace(
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
            AsyncMock(
                side_effect=[
                    RuntimeError(
                        "Audio generation failed. Please try a different prompt or send feedback. "
                        "You can update your settings to return silent videos."
                    ),
                    success_status,
                ]
            ),
        ):
            await self.service._run_flow_job(job.id, request)

        self.assertEqual(2, fake_client.generate_video.await_count)
        first_call = fake_client.generate_video.await_args_list[0]
        second_call = fake_client.generate_video.await_args_list[1]
        self.assertEqual("Veo 3.1 - Fast", first_call.kwargs["model"])
        self.assertEqual("Veo 2 - Fast", second_call.kwargs["model"])

        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertEqual("completed", saved.status)
        self.assertEqual("Veo 2 - Fast", saved.result.get("model"))
        self.assertEqual("Veo 3.1 - Fast", saved.result.get("fallback_from_model"))

    async def test_wait_for_video_with_progress_surfaces_audio_failure_detail(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        job = JobRecord(type="video", status="queued", title="test audio fail")
        await self.store.add_job(job)

        status = SimpleNamespace(
            status="MEDIA_GENERATION_STATUS_FAILED",
            complete=False,
            failed=True,
            media_name="media-123",
            _raw={
                "media": [
                    {
                        "mediaMetadata": {
                            "mediaStatus": {
                                "mediaGenerationStatus": "MEDIA_GENERATION_STATUS_FAILED",
                                "errorMessage": "Audio generation failed. Please try a different prompt or send feedback.",
                                "userFacingMessage": "You can update your settings to return silent videos.",
                            }
                        }
                    }
                ]
            },
        )
        client = SimpleNamespace(poll_video=AsyncMock(return_value=status))
        video_job = SimpleNamespace(media_name="media-123")

        with self.assertRaises(RuntimeError) as ctx:
            await self.service._wait_for_video_with_progress(
                client,
                job.id,
                video_job,
                "Video 1",
                poll_s=0.01,
                timeout_s=30,
            )

        self.assertIn("phần tạo audio bị lỗi", str(ctx.exception))

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

    async def test_run_flow_job_applies_flow_module_image_count(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = CreateJobRequest(
            type="image",
            prompt="meo de thuong",
            count=1,
            aspect="square",
            model="IMAGEN_3",
            automation_graph={
                "modules": [
                    {
                        "id": "flow",
                        "type": "flow",
                        "settings": {
                            "imageCount": 4,
                            "flowAgentEnabled": True,
                        },
                    }
                ]
            },
        )
        job = JobRecord(
            type="image",
            status="queued",
            title=self.service._default_title(request),
            input=request.model_dump(mode="json"),
        )
        await self.store.add_job(job)

        fake_images = [
            SimpleNamespace(
                media_name=f"img-{index}",
                workflow_id="wf-1",
                fife_url=f"https://example.com/img-{index}.jpg",
                prompt=request.prompt,
                dimensions={"width": 1024, "height": 1024},
            )
            for index in range(1, 5)
        ]
        fake_client = SimpleNamespace(
            _api=SimpleNamespace(generate_image=AsyncMock(return_value=fake_images)),
        )

        async def fake_with_client(fn, workflow_id="", timeout_s=0):
            return await fn(fake_client)

        with patch.object(self.service, "_with_client", side_effect=fake_with_client):
            await self.service._run_flow_job(job.id, request)

        kwargs = fake_client._api.generate_image.await_args.kwargs
        self.assertEqual(4, kwargs["count"])
        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertEqual(4, saved.input["count"])
        self.assertEqual(4, len(saved.artifacts))

    async def test_run_flow_job_records_make_style_automation_modules(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = CreateJobRequest(
            type="image",
            prompt="cat",
            count=1,
            automation_graph={
                "modules": [
                    {"id": "source-1", "type": "source", "title": "Prompt Source", "settings": {"sourceType": "sheets"}},
                    {"id": "normalize-1", "type": "normalize", "title": "Normalize Prompt"},
                    {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    {"id": "trello-1", "type": "trello", "title": "Trello Archive", "settings": {"trelloCard": "card-1"}},
                    {"id": "telegram-1", "type": "telegram", "title": "Telegram Review", "settings": {"telegramChat": "chat-1"}},
                    {"id": "approval-1", "type": "approval", "title": "Approval"},
                ]
            },
        )
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
            )
        ]
        calls: list[str] = []

        async def fake_with_client(fn, workflow_id="", timeout_s=0):
            return await fn(SimpleNamespace())

        async def fake_archive(job_id, module_request, artifacts):
            calls.append("trello")
            return {"configured": True, "sent": len(artifacts), "card_id": module_request.trello_card_id}

        async def fake_telegram(job_id, module_request, artifacts):
            calls.append("telegram")
            return {"configured": True, "sent": len(artifacts), "chat_id": module_request.telegram_chat_id}

        with patch.object(self.service, "_with_client", side_effect=fake_with_client), patch.object(
            self.service,
            "_generate_images_with_retry",
            AsyncMock(return_value=fake_images),
        ), patch.object(
            self.service,
            "_archive_trello_artifacts",
            side_effect=fake_archive,
        ), patch.object(
            self.service,
            "_send_telegram_review_pack",
            side_effect=fake_telegram,
        ):
            await self.service._run_flow_job(job.id, request)

        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertEqual("completed", saved.status)
        self.assertEqual(["trello", "telegram"], calls)
        execution = saved.result["automation_execution"]
        self.assertEqual("graph", execution["mode"])
        self.assertFalse(execution["completed"])
        self.assertEqual(
            ["source", "normalize", "flow", "trello", "telegram", "approval"],
            [node["type"] for node in execution["nodes"]],
        )
        self.assertTrue(all(node["status"] == "completed" for node in execution["nodes"] if node["type"] != "approval"))
        approval_node = next(node for node in execution["nodes"] if node["type"] == "approval")
        self.assertEqual("running", approval_node["status"])
        self.assertTrue(approval_node["output"]["awaiting_user_approval"])
        flow_node = next(node for node in execution["nodes"] if node["type"] == "flow")
        self.assertEqual(1, flow_node["output"]["artifact_count"])
        telegram_node = next(node for node in execution["nodes"] if node["type"] == "telegram")
        self.assertEqual("chat-1", telegram_node["output"]["chat_id"])
        trello_node = next(node for node in execution["nodes"] if node["type"] == "trello")
        self.assertEqual("card-1", trello_node["output"]["card_id"])

    async def test_trello_source_feeds_flow_and_archives_to_same_card_directly(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        source_image = self.uploads_dir / "trello-source.jpg"
        source_image.write_bytes(b"source-image")
        request = CreateJobRequest(
            type="image",
            prompt="turn the Trello product photo into an Etsy lifestyle image",
            count=1,
            telegram_enabled=True,
            trello_enabled=True,
            automation_graph={
                "modules": [
                    {"id": "source-1", "type": "source", "title": "Prompt Source"},
                    {
                        "id": "trello-source-1",
                        "type": "trello_source",
                        "title": "Trello Image Source",
                        "settings": {
                            "trelloCard": "https://trello.com/c/abc123/product-card",
                            "trelloAttachmentLimit": 2,
                        },
                    },
                    {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    {"id": "telegram-1", "type": "telegram", "title": "Telegram Review"},
                    {"id": "approval-1", "type": "approval", "title": "Approval"},
                    {"id": "trello-1", "type": "trello", "title": "Trello Archive", "settings": {"trelloCard": "wrong-card"}},
                ]
            },
        )
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
            fife_url="https://example.com/generated.jpg",
            prompt=request.prompt,
            dimensions={"width": 1024, "height": 1024},
        )
        captured: dict[str, object] = {}

        async def fake_with_client(fn, workflow_id="", timeout_s=0):
            return await fn(SimpleNamespace())

        async def fake_generate_images(client, job_id, module_request, reference_media_names):
            captured["request"] = module_request
            captured["reference_media_names"] = list(reference_media_names)
            return [fake_image]

        async def fake_telegram(job_id, module_request, artifacts):
            return {"configured": True, "sent": len(artifacts), "chat_id": module_request.telegram_chat_id}

        archive_cards: list[str] = []

        async def fake_archive(job_id, module_request, artifacts):
            archive_cards.append(module_request.trello_card_id)
            return {"configured": True, "sent": len(artifacts), "card_id": module_request.trello_card_id}

        with patch.object(self.service, "_with_client", side_effect=fake_with_client), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_download_trello_card_image_attachments",
            return_value=[str(source_image)],
        ), patch.object(
            self.service,
            "_resolve_image_reference_media",
            AsyncMock(return_value=["trello-media"]),
        ), patch.object(
            self.service,
            "_generate_images_with_retry",
            side_effect=fake_generate_images,
        ), patch.object(
            self.service,
            "_send_telegram_review_pack",
            side_effect=fake_telegram,
        ), patch.object(
            self.service,
            "_archive_trello_artifacts",
            side_effect=fake_archive,
        ):
            await self.service._run_flow_job(job.id, request)

        generated_request = captured["request"]
        self.assertEqual("abc123", generated_request.trello_card_id)
        self.assertEqual([str(source_image)], generated_request.reference_image_paths)
        self.assertEqual(["base"], generated_request.reference_image_roles)
        self.assertEqual(["trello-media"], captured["reference_media_names"])

        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertEqual("abc123", saved.input["trello_card_id"])
        execution = saved.result["automation_execution"]
        trello_source_node = next(node for node in execution["nodes"] if node["id"] == "trello-source-1")
        self.assertEqual("completed", trello_source_node["status"])
        self.assertEqual(1, trello_source_node["output"]["reference_image_count"])
        telegram_node = next(node for node in execution["nodes"] if node["id"] == "telegram-1")
        self.assertEqual("skipped", telegram_node["status"])
        self.assertEqual("trello_direct_review", telegram_node["output"]["reason"])
        approval_node = next(node for node in execution["nodes"] if node["id"] == "approval-1")
        self.assertEqual("completed", approval_node["status"])
        self.assertTrue(approval_node["output"]["trello_direct_review"])
        trello_node = next(node for node in execution["nodes"] if node["id"] == "trello-1")
        self.assertEqual("completed", trello_node["status"])
        self.assertEqual("abc123", trello_node["output"]["card_id"])
        self.assertEqual(["abc123"], archive_cards)
        self.assertEqual("abc123", saved.result["trello_direct_review"]["card_id"])

    async def test_trello_source_overrides_stale_request_card_before_archive(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        source_image = self.uploads_dir / "trello-source-stale.jpg"
        source_image.write_bytes(b"source-image")
        request = CreateJobRequest(
            type="image",
            prompt="turn the Trello product photo into an Etsy lifestyle image",
            count=1,
            trello_card_id="wrong-card",
            trello_enabled=True,
            automation_graph={
                "modules": [
                    {
                        "id": "trello-source-1",
                        "type": "trello_source",
                        "title": "Trello Image Source",
                        "settings": {
                            "trelloBoard": "https://trello.com/b/board123/demo-board",
                            "trelloList": "ready-list",
                            "trelloCard": "https://trello.com/c/source123/source-card",
                        },
                    },
                    {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    {"id": "trello-1", "type": "trello", "title": "Trello Archive", "settings": {"trelloCard": "wrong-card"}},
                ]
            },
        )
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
            fife_url="https://example.com/generated.jpg",
            prompt=request.prompt,
            dimensions={"width": 1024, "height": 1024},
        )
        captured: dict[str, object] = {}

        async def fake_with_client(fn, workflow_id="", timeout_s=0):
            return await fn(SimpleNamespace())

        async def fake_generate_images(client, job_id, module_request, reference_media_names):
            captured["flow_card"] = module_request.trello_card_id
            return [fake_image]

        async def fake_archive(job_id, module_request, artifacts):
            captured["archive_card"] = module_request.trello_card_id
            return {"configured": True, "sent": len(artifacts), "card_id": module_request.trello_card_id}

        with patch.object(self.service, "_with_client", side_effect=fake_with_client), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_card_hint_by_id",
            return_value={"card_id": "source123", "list_id": "ready-list", "list_name": "Ready for AI"},
        ), patch.object(
            self.service,
            "_download_trello_card_image_attachments",
            return_value=[str(source_image)],
        ) as download_images, patch.object(
            self.service,
            "_resolve_image_reference_media",
            AsyncMock(return_value=["trello-media"]),
        ), patch.object(
            self.service,
            "_generate_images_with_retry",
            side_effect=fake_generate_images,
        ), patch.object(
            self.service,
            "_archive_trello_artifacts",
            side_effect=fake_archive,
        ):
            await self.service._run_flow_job(job.id, request)

        self.assertEqual("source123", download_images.call_args.args[2])
        self.assertEqual("source123", captured["flow_card"])
        self.assertEqual("source123", captured["archive_card"])
        saved = self.store.get_job(job.id)
        self.assertEqual("source123", saved.input["trello_card_id"])
        self.assertEqual("source123", saved.input["trello_source_card_id"])
        trello_modules = [
            module
            for module in saved.input["automation_graph"]["modules"]
            if module["type"] in {"trello_source", "trello"}
        ]
        self.assertTrue(all(module["settings"]["trelloCard"] == "source123" for module in trello_modules))

    async def test_trello_source_request_locks_downloaded_card_and_attachment(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = CreateJobRequest(
            type="image",
            prompt="make a product image from Trello",
            count=1,
            trello_card_id="source-card",
            trello_enabled=True,
            automation_graph={
                "modules": [
                    {"id": "trello-source-1", "type": "trello_source", "title": "Trello Image Source"},
                    {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    {"id": "trello-1", "type": "trello", "title": "Trello Archive"},
                ]
            },
        )
        job = JobRecord(
            type="image",
            status="queued",
            title=self.service._default_title(request),
            input=request.model_dump(mode="json"),
        )
        await self.store.add_job(job)
        attachments = [
            {
                "id": "source-att",
                "name": "source.jpg",
                "url": "https://trello.local/source.jpg",
                "mimeType": "image/jpeg",
                "date": "2026-05-20T08:00:00.000Z",
            },
            {
                "id": "flow-old",
                "name": "flow-old-1.jpg",
                "url": "https://trello.local/flow.jpg",
                "mimeType": "image/jpeg",
                "date": "2026-05-22T08:00:00.000Z",
            },
        ]

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_get_json",
            return_value=attachments,
        ), patch.object(
            self.service,
            "_trello_download_attachment_bytes",
            return_value=(b"source-image", "image/jpeg"),
        ):
            updated = await self.service._request_with_trello_source_images(job.id, request)

        self.assertEqual("source-card", updated.trello_card_id)
        self.assertEqual("source-card", updated.trello_source_card_id)
        self.assertEqual(["source-att"], updated.trello_attachment_ids)
        self.assertEqual(["source-att"], updated.trello_source_attachment_ids)
        self.assertEqual(1, len(updated.reference_image_paths))
        execution = self.store.get_job(job.id).result["automation_execution"]
        trello_source_node = next(node for node in execution["nodes"] if node["id"] == "trello-source-1")
        self.assertEqual("source-card", trello_source_node["output"]["source_card_id"])
        self.assertEqual(["source-att"], trello_source_node["output"]["source_attachment_ids"])

    async def test_trello_source_resolves_board_link_to_image_card(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        source_image = self.uploads_dir / "trello-board-source.jpg"
        source_image.write_bytes(b"source-image")
        request = CreateJobRequest(
            type="image",
            prompt="make a product image from the Trello board card",
            count=1,
            telegram_enabled=False,
            trello_enabled=True,
            automation_graph={
                "modules": [
                    {
                        "id": "trello-source-1",
                        "type": "trello_source",
                        "title": "Trello Image Source",
                        "settings": {
                            "trelloBoard": "https://trello.com/b/board123/demo-board",
                            "trelloList": "list-1",
                        },
                    },
                    {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    {"id": "trello-1", "type": "trello", "title": "Trello Archive"},
                ]
            },
        )
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
            fife_url="https://example.com/generated.jpg",
            prompt=request.prompt,
            dimensions={"width": 1024, "height": 1024},
        )
        captured: dict[str, object] = {}

        async def fake_with_client(fn, workflow_id="", timeout_s=0):
            return await fn(SimpleNamespace())

        async def fake_generate_images(client, job_id, module_request, reference_media_names):
            captured["request"] = module_request
            return [fake_image]

        async def fake_archive(job_id, module_request, artifacts):
            captured["archive_card"] = module_request.trello_card_id
            return {"configured": True, "sent": len(artifacts), "card_id": module_request.trello_card_id}

        with patch.object(self.service, "_with_client", side_effect=fake_with_client), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="list-1",
        ), patch.object(
            self.service,
            "_trello_first_image_card_id_on_board",
            return_value="card-from-board",
        ) as find_card, patch.object(
            self.service,
            "_download_trello_card_image_attachments",
            return_value=[str(source_image)],
        ) as download_images, patch.object(
            self.service,
            "_resolve_image_reference_media",
            AsyncMock(return_value=["trello-media"]),
        ), patch.object(
            self.service,
            "_generate_images_with_retry",
            side_effect=fake_generate_images,
        ), patch.object(
            self.service,
            "_archive_trello_artifacts",
            side_effect=fake_archive,
        ):
            await self.service._run_flow_job(job.id, request)

        find_card.assert_called_once_with("key", "token", "board123", "list-1")
        download_images.assert_called_once()
        self.assertEqual("card-from-board", download_images.call_args.args[2])
        generated_request = captured["request"]
        self.assertEqual("board123", generated_request.trello_board_id)
        self.assertEqual("card-from-board", generated_request.trello_card_id)
        self.assertEqual("card-from-board", generated_request.trello_source_card_id)
        self.assertEqual("card-from-board", captured["archive_card"])
        saved = self.store.get_job(job.id)
        self.assertEqual("card-from-board", saved.input["trello_card_id"])
        self.assertEqual("card-from-board", saved.input["trello_source_card_id"])
        trello_source_node = next(node for node in saved.result["automation_execution"]["nodes"] if node["id"] == "trello-source-1")
        self.assertEqual("board123", trello_source_node["output"]["board_id"])
        self.assertEqual("card-from-board", trello_source_node["output"]["card_id"])

    async def test_trello_source_rejects_explicit_card_outside_ready_list(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = CreateJobRequest(
            type="image",
            prompt="make a product image from Trello",
            count=1,
            trello_board_id="https://trello.com/b/board123/demo-board",
            trello_card_id="wrong-card",
            automation_graph={
                "modules": [
                    {
                        "id": "trello-source-1",
                        "type": "trello_source",
                        "title": "Trello Image Source",
                        "settings": {
                            "trelloBoard": "https://trello.com/b/board123/demo-board",
                            "trelloCard": "https://trello.com/c/wrong-card/wrong",
                        },
                    },
                    {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                ]
            },
        )
        job = JobRecord(type="image", status="running", title="test", input=request.model_dump(mode="json"))
        await self.store.add_job(job)

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_board_lists",
            return_value=[
                {"id": "other-list", "name": "Done"},
                {"id": "ready-list", "name": "Ready for AI"},
            ],
        ), patch.object(
            self.service,
            "_trello_card_hint_by_id",
            return_value={"card_id": "wrong-card", "card_name": "wrong", "list_id": "other-list"},
        ), patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ), patch.object(
            self.service,
            "_download_trello_card_image_attachments",
        ) as download_images:
            with self.assertRaises(RuntimeError) as ctx:
                await self.service._request_with_trello_source_images(job.id, request)

        self.assertIn("không nằm trong cột Ready for AI", str(ctx.exception))
        download_images.assert_not_called()

    async def test_approval_module_pauses_and_resumes_downstream_modules(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = CreateJobRequest(
            type="image",
            prompt="cat",
            count=1,
            telegram_enabled=True,
            trello_enabled=True,
            automation_graph={
                "modules": [
                    {"id": "source-1", "type": "source", "title": "Prompt Source"},
                    {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    {"id": "telegram-1", "type": "telegram", "title": "Telegram Review", "settings": {"telegramChat": "chat-1"}},
                    {"id": "approval-1", "type": "approval", "title": "Approval"},
                    {"id": "trello-1", "type": "trello", "title": "Trello Archive", "settings": {"trelloCard": "card-1"}},
                ]
            },
        )
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
            )
        ]
        calls: list[str] = []

        async def fake_with_client(fn, workflow_id="", timeout_s=0):
            return await fn(SimpleNamespace())

        async def fake_archive(job_id, module_request, artifacts):
            calls.append("trello")
            return {"configured": True, "sent": len(artifacts), "card_id": module_request.trello_card_id}

        async def fake_telegram(job_id, module_request, artifacts):
            calls.append("telegram")
            return {"configured": True, "sent": len(artifacts), "chat_id": module_request.telegram_chat_id}

        with patch.object(self.service, "_with_client", side_effect=fake_with_client), patch.object(
            self.service,
            "_generate_images_with_retry",
            AsyncMock(return_value=fake_images),
        ), patch.object(
            self.service,
            "_archive_trello_artifacts",
            side_effect=fake_archive,
        ), patch.object(
            self.service,
            "_send_telegram_review_pack",
            side_effect=fake_telegram,
        ):
            await self.service._run_flow_job(job.id, request)

            saved = self.store.get_job(job.id)
            self.assertIsNotNone(saved)
            self.assertEqual(["telegram"], calls)
            execution = saved.result["automation_execution"]
            approval_node = next(node for node in execution["nodes"] if node["id"] == "approval-1")
            trello_node = next(node for node in execution["nodes"] if node["id"] == "trello-1")
            self.assertEqual("running", approval_node["status"])
            self.assertEqual("pending", trello_node["status"])
            self.assertFalse(execution["completed"])

            await self.service._apply_telegram_approval(
                job.id,
                0,
                "approved",
                {
                    "id": "callback-1",
                    "from": {"first_name": "Reviewer"},
                    "message": {"message_id": 42, "chat": {"id": "chat-1"}},
                },
            )

        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertEqual(["telegram", "trello"], calls)
        execution = saved.result["automation_execution"]
        approval_node = next(node for node in execution["nodes"] if node["id"] == "approval-1")
        trello_node = next(node for node in execution["nodes"] if node["id"] == "trello-1")
        self.assertEqual("completed", approval_node["status"])
        self.assertEqual("completed", trello_node["status"])
        self.assertTrue(execution["completed"])
        self.assertEqual(1, saved.result["telegram_approval_summary"]["approved"])
        self.assertEqual("card-1", saved.result["trello"]["card_id"])

    async def test_late_telegram_reaction_does_not_flip_completed_approval(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="cat",
            count=1,
            telegram_enabled=True,
            trello_enabled=True,
            automation_graph={
                "modules": [
                    {"id": "source-1", "type": "source", "title": "Prompt Source"},
                    {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    {"id": "telegram-1", "type": "telegram", "title": "Telegram Review"},
                    {"id": "approval-1", "type": "approval", "title": "Approval"},
                    {"id": "trello-1", "type": "trello", "title": "Trello Archive"},
                ]
            },
        )
        job = JobRecord(
            type="image",
            status="completed",
            title="approved job",
            input=request.model_dump(mode="json"),
            result={
                "telegram_approvals": {"0": {"artifact_index": 0, "status": "approved"}},
                "telegram_approval_summary": {
                    "total": 1,
                    "approved": 1,
                    "rejected": 0,
                    "pending": 0,
                    "resolved": 1,
                    "status": "completed",
                },
                "trello": {"configured": True, "sent": 1, "failed": 0, "card_id": "card-1"},
                "automation_execution": {
                    "mode": "graph",
                    "nodes": [
                        {"id": "approval-1", "type": "approval", "status": "completed", "output": {}},
                        {"id": "trello-1", "type": "trello", "status": "completed", "output": {"sent": 1}},
                    ],
                    "edges": [],
                    "current_module_id": "",
                    "completed": True,
                },
            },
            artifacts=[JobArtifact(label="Ảnh 1", url="https://example.com/img.jpg", mime_type="image/jpeg")],
        )
        await self.store.add_job(job)

        with patch.object(self.service, "_archive_trello_artifacts", AsyncMock()) as archive:
            approval = await self.service._apply_telegram_approval(
                job.id,
                0,
                "rejected",
                {"id": "late-callback", "from": {"first_name": "Reviewer"}},
            )

        saved = self.store.get_job(job.id)
        self.assertEqual("approved", approval["status"])
        self.assertEqual("approved", saved.result["telegram_approvals"]["0"]["status"])
        self.assertEqual(1, saved.result["telegram_approval_summary"]["approved"])
        self.assertEqual(0, saved.result["telegram_approval_summary"]["rejected"])
        self.assertEqual("completed", saved.result["automation_execution"]["nodes"][1]["status"])
        self.assertEqual(1, saved.result["trello"]["sent"])
        archive.assert_not_called()
        self.assertIn("Bỏ qua phản hồi Telegram", saved.logs[-1].message)

    async def test_custom_module_runs_user_configured_webhook(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = CreateJobRequest(
            type="image",
            prompt="custom prompt",
            title="Webhook demo",
            count=1,
            automation_graph={
                "modules": [
                    {"id": "source-1", "type": "source", "title": "Prompt Source"},
                    {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    {
                        "id": "custom-1",
                        "type": "custom",
                        "title": "Webhook Custom",
                        "settings": {
                            "customWebhookUrl": "https://hooks.example/run?api_key=secret&job={{job_id}}",
                            "customWebhookMethod": "POST",
                            "customWebhookHeaders": "X-Flow-Job: {{job_id}}\nAuthorization: Bearer demo",
                            "customWebhookBody": '{"id":"{{job_id}}","prompt":"{{prompt}}","url":"{{first_artifact_url}}","artifacts":{{artifacts}}}',
                        },
                    },
                ]
            },
        )
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
            )
        ]
        captured: dict[str, object] = {}

        async def fake_with_client(fn, workflow_id="", timeout_s=0):
            return await fn(SimpleNamespace())

        def fake_webhook(method, url, headers, body, timeout_s):
            captured["method"] = method
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = body
            captured["timeout_s"] = timeout_s
            return {"status_code": 200, "body": {"ok": True}}

        with patch.object(self.service, "_with_client", side_effect=fake_with_client), patch.object(
            self.service,
            "_generate_images_with_retry",
            AsyncMock(return_value=fake_images),
        ), patch.object(
            self.service,
            "_custom_webhook_request",
            side_effect=fake_webhook,
        ):
            await self.service._run_flow_job(job.id, request)

        saved = self.store.get_job(job.id)
        self.assertIsNotNone(saved)
        self.assertEqual("completed", saved.status)
        self.assertEqual("POST", captured["method"])
        self.assertIn(f"job={job.id}", captured["url"])
        self.assertEqual(job.id, captured["headers"]["X-Flow-Job"])
        body_payload = json.loads(captured["body"].decode("utf-8"))
        self.assertEqual(job.id, body_payload["id"])
        self.assertEqual("custom prompt", body_payload["prompt"])
        self.assertEqual("https://example.com/img-1.jpg", body_payload["url"])
        self.assertEqual("img-1", body_payload["artifacts"][0]["media_name"])
        custom_result = saved.result["custom_modules"]["custom-1"]
        self.assertTrue(custom_result["configured"])
        self.assertEqual(200, custom_result["status_code"])
        self.assertIn("api_key=***", custom_result["url"])
        custom_node = next(node for node in saved.result["automation_execution"]["nodes"] if node["id"] == "custom-1")
        self.assertEqual("completed", custom_node["status"])

    async def test_prompt_batch_runs_active_sheet_prompts_sequentially(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="",
                count=1,
                telegram_enabled=True,
                telegram_chat_id="1234567890",
                automation_graph={
                    "modules": [
                        {"id": "source-1", "type": "source", "title": "Prompt Source", "settings": {"sourceType": "sheets"}},
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                        {"id": "telegram-1", "type": "telegram", "title": "Telegram Review"},
                        {"id": "approval-1", "type": "approval", "title": "Approval"},
                    ]
                },
            ),
            items=[
                {"row": 2, "prompt": "first product prompt", "product": "Hoop", "index": "1", "active": True},
                {"row": 3, "prompt": "inactive prompt", "product": "Hoop", "index": "2", "active": False},
                {"row": 4, "prompt": "used prompt", "product": "Blanket", "index": "1", "active": True, "used": True},
                {"row": 5, "prompt": "second product prompt", "product": "Blanket", "index": "2", "active": True},
            ],
        )
        seen_prompts: list[str] = []

        async def fake_run_flow_job(job_id, child_request):
            seen_prompts.append(child_request.prompt)
            await self.store.replace_artifacts(
                job_id,
                [JobArtifact(label="Ảnh 1", url="https://example.com/image.jpg", mime_type="image/jpeg", prompt=child_request.prompt)],
            )
            await self.store.patch_job(job_id, status="completed", result={"count": 1, "mode": "image"})

        with patch.object(self.service, "get_auth_status", return_value=AuthStatus(authenticated=True)), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ):
            batch = await self.service.enqueue_prompt_batch(request)
            await self.service._tasks[batch.id]

        saved = self.store.get_job(batch.id)
        self.assertIsNotNone(saved)
        self.assertEqual("completed", saved.status)
        self.assertEqual(["first product prompt", "second product prompt"], seen_prompts)
        self.assertEqual(2, saved.result["total"])
        self.assertEqual(2, saved.result["completed"])
        self.assertEqual(0, saved.result["failed"])
        child_jobs = [self.store.get_job(job_id) for job_id in saved.result["child_job_ids"]]
        self.assertEqual(["Sheet 1/2 · Hoop #1", "Sheet 2/2 · Blanket #2"], [job.title for job in child_jobs])

    async def test_flow_agent_batch_waits_between_image_sets(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        base = CreateJobRequest(type="image", prompt="", count=8)
        items = [
            {
                "prompt": "first card",
                "product": "First",
                "trello_card_id": "card-1",
                "flow_agent_instruction": True,
                "flow_agent_image_count": 8,
            },
            {
                "prompt": "second card",
                "product": "Second",
                "trello_card_id": "card-2",
                "flow_agent_instruction": True,
                "flow_agent_image_count": 8,
            },
        ]
        batch = JobRecord(type="batch_image", status="queued", title="batch", input=base.model_dump(mode="json"))
        await self.store.add_job(batch)
        seen_prompts: list[str] = []

        async def fake_run_flow_job(job_id, child_request):
            seen_prompts.append(child_request.prompt)
            await self.store.patch_job(job_id, status="completed", result={"count": 8, "mode": "image"})

        with patch.object(self.service, "get_auth_status", return_value=AuthStatus(authenticated=True)), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ), patch.object(
            self.service,
            "_sleep_between_flow_agent_batches",
            new=AsyncMock(),
        ) as pause:
            await self.service._run_prompt_batch(batch.id, base, items)

        self.assertEqual(["first card", "second card"], seen_prompts)
        pause.assert_awaited_once_with(batch.id, 2, 2)

    async def test_auto_trello_batch_stops_after_successful_trello_upload(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        base = CreateJobRequest(type="image", prompt="", count=12, flow_agent_enabled=True, trello_enabled=True)
        items = [
            {
                "prompt": "first card",
                "product": "First",
                "trello_card_id": "card-1",
                "flow_agent_instruction": True,
                "flow_agent_image_count": 12,
            },
            {
                "prompt": "second card",
                "product": "Second",
                "trello_card_id": "card-2",
                "flow_agent_instruction": True,
                "flow_agent_image_count": 12,
            },
        ]
        batch = JobRecord(
            type="batch_image",
            status="queued",
            title="batch",
            input={"trello_source_hint": {"mode": "auto_trello"}, "batch_key": "auto"},
            result={"trello_source_hint": {"mode": "auto_trello"}, "batch_key": "auto"},
        )
        await self.store.add_job(batch)
        seen_prompts: list[str] = []
        live_scan_calls = 0

        async def fake_next_live_item(batch_id, base_request, seed_items, attempted_card_ids):
            nonlocal live_scan_calls
            live_scan_calls += 1
            if live_scan_calls > 1:
                raise AssertionError("Auto Trello scanned for another card after Trello upload completed")
            return base_request, items[0], {"mode": "auto_trello"}

        async def fake_run_flow_job(job_id, child_request):
            seen_prompts.append(child_request.prompt)
            await self.store.patch_job(
                job_id,
                status="completed",
                result={
                    "count": 12,
                    "mode": "image",
                    "trello": {"configured": True, "sent": 12, "failed": 0},
                },
            )

        with patch.object(self.service, "get_auth_status", return_value=AuthStatus(authenticated=True)), patch.object(
            self.service,
            "_next_live_auto_trello_prompt_item",
            side_effect=fake_next_live_item,
        ), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ), patch.object(
            self.service,
            "_sleep_between_flow_agent_batches",
            new=AsyncMock(),
        ) as pause:
            await self.service._run_prompt_batch(batch.id, base, items)

        saved = self.store.get_job(batch.id)
        self.assertIsNotNone(saved)
        self.assertEqual("completed", saved.status)
        self.assertEqual(["first card"], seen_prompts)
        self.assertEqual(1, live_scan_calls)
        self.assertTrue(saved.result["stop_requested"])
        self.assertEqual(1, saved.result["completed"])
        self.assertEqual(0, saved.result["failed"])
        self.assertEqual(1, len(saved.result["child_job_ids"]))
        pause.assert_not_awaited()

    async def test_trello_prompt_batch_runs_one_matching_prompt_and_dedupes_active_batch(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="",
                count=1,
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {"trelloCard": "https://trello.com/c/card123/wedding-hoop"},
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    ]
                },
            ),
            limit=40,
            items=[
                {"row": 108, "prompt": "prompt 1", "product_key": "wedding_hoop", "product": "Wedding Hoop", "index": "1", "active": True},
                {"row": 109, "prompt": "prompt 2", "product_key": "wedding_hoop", "product": "Wedding Hoop", "index": "2", "active": True},
                {"row": 110, "prompt": "prompt 3", "product_key": "other", "product": "Other", "index": "1", "active": True},
            ],
        )
        started = asyncio.Event()
        release = asyncio.Event()
        seen_prompts: list[str] = []

        async def fake_run_flow_job(job_id, child_request):
            seen_prompts.append(child_request.prompt)
            started.set()
            await release.wait()
            await self.store.patch_job(job_id, status="completed", result={"count": 1, "mode": "image"})

        source_hint = {
            "card_id": "card123",
            "card_name": "wedding_hoop",
            "card_url": "https://trello.com/c/card123/wedding-hoop",
            "list_id": "list-ready",
            "list_name": "Ready for AI",
        }

        with patch.object(self.service, "get_auth_status", return_value=AuthStatus(authenticated=True)), patch.object(
            self.service,
            "_trello_source_card_hint",
            return_value=source_hint,
        ), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ):
            batch = await self.service.enqueue_prompt_batch(request)
            await asyncio.wait_for(started.wait(), timeout=1)
            duplicate = await self.service.enqueue_prompt_batch(request)
            release.set()
            await self.service._tasks[batch.id]

        self.assertEqual(batch.id, duplicate.id)
        self.assertEqual(["prompt 1"], seen_prompts)
        saved = self.store.get_job(batch.id)
        self.assertEqual("completed", saved.status)
        self.assertEqual(1, saved.result["total"])
        self.assertEqual("card123", saved.result["trello_source_hint"]["card_id"])
        child_job = self.store.get_job(saved.result["child_job_ids"][0])
        self.assertEqual("card123", child_job.input["trello_card_id"])

    async def test_trello_prompt_batch_finds_matching_card_in_ready_list(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="",
                count=1,
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {
                                "trelloBoard": "https://trello.com/b/board123/demo-board",
                                "trelloList": "empty-ready-list",
                            },
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    ]
                },
            ),
            limit=40,
            items=[
                {"row": 2, "prompt": "bear prompt", "product_key": "gau_bong", "product": "Gấu bông", "index": "1", "active": True},
                {"row": 3, "prompt": "hoop prompt", "product_key": "wedding_hoop", "product": "Wedding Hoop", "index": "1", "active": True},
            ],
        )
        seen_prompts: list[str] = []
        matched_hint = {
            "card_id": "matched-card",
            "card_name": "gau_bong",
            "card_url": "https://trello.com/c/matched/gau-bong",
            "list_id": "ready-list",
            "list_name": "Ready for AI",
        }

        async def fake_run_flow_job(job_id, child_request):
            seen_prompts.append(child_request.prompt)
            await self.store.patch_job(job_id, status="completed", result={"count": 1, "mode": "image"})

        with patch.object(self.service, "get_auth_status", return_value=AuthStatus(authenticated=True)), patch.object(
            self.service,
            "_trello_source_card_hint",
            return_value={},
        ), patch.object(
            self.service,
            "_trello_matching_image_card_hint",
            return_value=matched_hint,
        ), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ):
            batch = await self.service.enqueue_prompt_batch(request)
            await self.service._tasks[batch.id]

        saved = self.store.get_job(batch.id)
        self.assertEqual("completed", saved.status)
        self.assertEqual(["bear prompt"], seen_prompts)
        self.assertEqual(1, saved.result["total"])
        self.assertEqual("matched-card", saved.result["trello_source_hint"]["card_id"])
        child_job = self.store.get_job(saved.result["child_job_ids"][0])
        self.assertEqual("matched-card", child_job.input["trello_card_id"])
        self.assertEqual("ready-list", child_job.input["trello_list_id"])

    async def test_auto_trello_prompt_batch_discovers_multiple_image_cards(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="",
                count=1,
                trello_board_id="https://trello.com/b/board123/demo-board",
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {"trelloBoard": "https://trello.com/b/board123/demo-board"},
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    ]
                },
            ),
            limit=10,
            auto_trello=True,
            items=[
                {"row": 2, "prompt": "bear prompt", "product_key": "gau_bong", "product": "Gấu bông", "index": "1", "active": True},
                {"row": 3, "prompt": "hoop prompt", "product_key": "wedding_hoop", "product": "Wedding Hoop", "index": "1", "active": True},
            ],
        )
        seen: list[tuple[str, str]] = []
        cards = [
            {"id": "card-bear", "name": "gau_bong", "shortLink": "bear", "url": "https://trello.com/c/bear", "idList": "ready-list"},
            {"id": "card-hoop", "name": "wedding_hoop", "shortLink": "hoop", "url": "https://trello.com/c/hoop", "idList": "ready-list"},
        ]

        async def fake_run_flow_job(job_id, child_request):
            seen.append((child_request.prompt, child_request.trello_card_id))
            await self.store.patch_job(job_id, status="completed", result={"count": 1, "mode": "image"})

        with patch.object(self.service, "get_auth_status", return_value=AuthStatus(authenticated=True)), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=cards,
        ) as image_cards, patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ):
            batch = await self.service.enqueue_prompt_batch(request)
            await self.service._tasks[batch.id]

        self.assertEqual(
            [("key", "token", "board123", "ready-list")] * 3,
            [call.args for call in image_cards.call_args_list],
        )
        self.assertEqual([("bear prompt", "card-bear"), ("hoop prompt", "card-hoop")], seen)
        saved = self.store.get_job(batch.id)
        self.assertEqual("completed", saved.status)
        self.assertEqual(2, saved.result["total"])
        self.assertEqual(2, saved.result["completed"])
        self.assertEqual("auto_trello", saved.result["trello_source_hint"]["mode"])
        self.assertEqual("ready-list", saved.result["trello_source_hint"]["list_id"])
        child_jobs = [self.store.get_job(job_id) for job_id in saved.result["child_job_ids"]]
        self.assertEqual(["card-bear", "card-hoop"], [job.input["trello_card_id"] for job in child_jobs])

    async def test_auto_trello_run_until_empty_processes_all_ready_cards(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="",
                count=1,
                trello_board_id="https://trello.com/b/board123/demo-board",
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {"trelloBoard": "https://trello.com/b/board123/demo-board"},
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                        {"id": "trello-1", "type": "trello", "title": "Trello Archive"},
                    ]
                },
            ),
            limit=0,
            auto_trello=True,
            run_until_empty=True,
        )
        cards = [
            {
                "id": f"card-{index}",
                "name": f"Ready baby_pillowcase product {index}",
                "shortLink": f"short-{index}",
                "url": f"https://trello.com/c/card-{index}",
                "idList": "ready-list",
                "_image_attachments": [{"id": f"att-{index}", "name": f"baby_pillowcase-{index}.jpg", "mimeType": "image/jpeg"}],
            }
            for index in range(45)
        ]
        seen_cards: list[str] = []

        async def fake_run_flow_job(job_id, child_request):
            seen_cards.append(child_request.trello_card_id)
            await self.store.patch_job(
                job_id,
                status="completed",
                result={
                    "count": child_request.count,
                    "mode": "image",
                    "trello": {"configured": True, "sent": child_request.count, "failed": 0},
                },
            )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False), patch.object(
            self.service,
            "get_auth_status",
            return_value=AuthStatus(authenticated=True),
        ), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=cards,
        ), patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ):
            batch = await self.service.enqueue_prompt_batch(request)
            await self.service._tasks[batch.id]

        saved = self.store.get_job(batch.id)
        self.assertEqual("completed", saved.status)
        self.assertTrue(saved.input["run_until_empty"])
        self.assertTrue(saved.result["run_until_empty"])
        self.assertEqual(45, saved.input["limit"])
        self.assertEqual(45, saved.result["total"])
        self.assertEqual(45, saved.result["completed"])
        self.assertEqual([f"card-{index}" for index in range(45)], seen_cards)

    async def test_auto_trello_flow_agent_rescans_ready_before_each_card(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="",
                count=1,
                trello_board_id="https://trello.com/b/board123/demo-board",
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {"trelloBoard": "https://trello.com/b/board123/demo-board"},
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                        {"id": "trello-1", "type": "trello", "title": "Trello Archive"},
                    ]
                },
            ),
            limit=2,
            auto_trello=True,
            items=[],
        )
        stale_card = {
            "id": "stale-card",
            "name": "Moved baby_pillowcase product",
            "shortLink": "stale",
            "url": "https://trello.com/c/stale",
            "idList": "ready-list",
            "_image_attachments": [{"id": "stale-att", "name": "stale_baby_pillowcase.jpg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["stale-att"],
        }
        live_card = {
            "id": "live-card",
            "name": "Live baby_pillowcase product",
            "shortLink": "live",
            "url": "https://trello.com/c/live",
            "idList": "ready-list",
            "_image_attachments": [{"id": "live-att", "name": "live_baby_pillowcase.jpg", "mimeType": "image/jpeg"}],
            "_selected_attachment_ids": ["live-att"],
        }
        scans = [[stale_card, live_card], [live_card], []]
        seen: list[tuple[str, list[str]]] = []

        def fake_image_cards(*_args: object) -> list[dict[str, Any]]:
            return scans.pop(0) if scans else []

        async def fake_run_flow_job(job_id, child_request):
            seen.append((child_request.trello_card_id, list(child_request.trello_source_attachment_ids)))
            await self.store.patch_job(job_id, status="completed", result={"count": child_request.count, "mode": "image"})

        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False), patch.object(
            self.service,
            "get_auth_status",
            return_value=AuthStatus(authenticated=True),
        ), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            side_effect=fake_image_cards,
        ) as image_cards, patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ):
            batch = await self.service.enqueue_prompt_batch(request)
            await self.service._tasks[batch.id]

        self.assertGreaterEqual(image_cards.call_count, 3)
        self.assertEqual([("live-card", ["live-att"])], seen)
        saved = self.store.get_job(batch.id)
        self.assertEqual("completed", saved.status)
        self.assertEqual(1, saved.result["total"])
        self.assertEqual(1, saved.result["completed"])
        self.assertEqual(0, saved.result["failed"])
        self.assertEqual(["live-card"], saved.result["seen_card_ids"])
        child_job = self.store.get_job(saved.result["child_job_ids"][0])
        self.assertEqual("live-card", child_job.input["trello_card_id"])
        self.assertEqual("live-card", child_job.input["trello_source_card_id"])
        self.assertEqual(["live-att"], child_job.input["trello_source_attachment_ids"])

    async def test_continuous_auto_trello_waits_until_user_stops(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="",
                count=1,
                trello_board_id="https://trello.com/b/board123/demo-board",
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {"trelloBoard": "https://trello.com/b/board123/demo-board"},
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                        {"id": "trello-1", "type": "trello", "title": "Trello Archive"},
                    ]
                },
            ),
            limit=0,
            auto_trello=True,
            run_until_empty=True,
            continuous=True,
            poll_interval_s=1,
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False), patch.object(
            self.service,
            "get_auth_status",
            return_value=AuthStatus(authenticated=True),
        ), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=[],
        ), patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ):
            batch = await self.service.enqueue_prompt_batch(request)
            await asyncio.sleep(0.05)
            running = self.store.get_job(batch.id)
            self.assertEqual("running", running.status)
            self.assertTrue(running.result["continuous"])
            await self.service.request_stop_prompt_batch(batch.id)
            await self.service._tasks[batch.id]

        saved = self.store.get_job(batch.id)
        self.assertEqual("completed", saved.status)
        self.assertTrue(saved.result["continuous"])
        self.assertTrue(saved.result["stop_requested"])
        self.assertEqual(0, saved.result["completed"])
        self.assertEqual(0, saved.result["failed"])

    async def test_continuous_auto_trello_does_not_retry_same_card_in_one_session(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="",
                count=1,
                trello_board_id="https://trello.com/b/board123/demo-board",
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {"trelloBoard": "https://trello.com/b/board123/demo-board"},
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                        {"id": "trello-1", "type": "trello", "title": "Trello Archive"},
                    ]
                },
            ),
            limit=0,
            auto_trello=True,
            run_until_empty=True,
            continuous=True,
            poll_interval_s=1,
        )
        cards = [
            {
                "id": "repeat-card",
                "name": "Repeat baby_pillowcase product",
                "shortLink": "repeat",
                "url": "https://trello.com/c/repeat",
                "idList": "ready-list",
                "_image_attachments": [{"id": "repeat-att", "name": "repeat_baby_pillowcase.jpg", "mimeType": "image/jpeg"}],
                "_selected_attachment_ids": ["repeat-att"],
            }
        ]
        seen_cards: list[str] = []
        sleep_calls = 0

        async def fake_run_flow_job(job_id, child_request):
            seen_cards.append(child_request.trello_card_id)
            await self.store.patch_job(job_id, status="completed", result={"count": child_request.count, "mode": "image"})

        async def fake_sleep(batch_id, poll_interval_s):
            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls >= 2:
                await self.service.request_stop_prompt_batch(batch_id)

        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False), patch.object(
            self.service,
            "get_auth_status",
            return_value=AuthStatus(authenticated=True),
        ), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=cards,
        ), patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ), patch.object(
            self.service,
            "_sleep_continuous_auto_trello",
            side_effect=fake_sleep,
        ):
            batch = await self.service.enqueue_prompt_batch(request)
            await self.service._tasks[batch.id]

        saved = self.store.get_job(batch.id)
        self.assertEqual("completed", saved.status)
        self.assertEqual(["repeat-card"], seen_cards)
        self.assertEqual(["repeat-card"], saved.result["seen_card_ids"])
        self.assertEqual(1, saved.result["completed"])
        self.assertEqual(2, sleep_calls)

    async def test_continuous_auto_trello_forces_configured_ready_list_over_stale_graph(self) -> None:
        await self.store.replace_trello_config(
            TrelloConfig(api_key="key", token="token", board_id="board123", list_id="ready-list")
        )
        request = CreateJobRequest(
            type="image",
            prompt="",
            trello_board_id="board123",
            trello_card_id="shirt-card",
            trello_list_id="shirt-list",
            trello_attachment_ids=["old-att"],
            automation_graph={
                "modules": [
                    {
                        "id": "trello-source",
                        "type": "trello_source",
                        "settings": {
                            "trelloBoard": "board123",
                            "trelloCard": "shirt-card",
                            "trelloList": "shirt-list",
                            "trelloAttachmentIds": ["old-att"],
                        },
                    },
                    {
                        "id": "flow",
                        "type": "flow",
                        "settings": {
                            "flowAgentEnabled": False,
                            "flowAgentAutoApprove": False,
                            "imageAspect": "landscape",
                            "imageCount": 1,
                        },
                    },
                    {
                        "id": "trello-log",
                        "type": "trello",
                        "settings": {
                            "trelloBoard": "board123",
                            "trelloCard": "shirt-card",
                            "trelloList": "shirt-list",
                            "trelloAttachmentIds": ["old-att"],
                        },
                    },
                ]
            },
        )

        with patch.object(self.service, "_trello_credentials", return_value=("key", "token")), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ) as resolve_list, patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ):
            base, hint = await self.service._continuous_auto_trello_base_request(request)

        resolve_list.assert_called_once_with("key", "token", "board123", "ready-list")
        self.assertEqual("ready-list", hint["list_id"])
        self.assertEqual("Ready for AI", hint["list_name"])
        self.assertEqual("ready-list", base.trello_list_id)
        self.assertEqual("", base.trello_card_id)
        self.assertEqual([], base.trello_attachment_ids)
        self.assertEqual("square", base.aspect)
        self.assertEqual(12, base.count)
        self.assertTrue(base.flow_agent_enabled)
        self.assertTrue(base.flow_agent_auto_approve)
        graph = base.automation_graph.model_dump(mode="json")
        trello_modules = [module for module in graph["modules"] if module["type"] in {"trello_source", "trello"}]
        self.assertEqual(2, len(trello_modules))
        for module in trello_modules:
            self.assertEqual("ready-list", module["settings"]["trelloList"])
            self.assertEqual("", module["settings"]["trelloCard"])
            self.assertEqual([], module["settings"]["trelloAttachmentIds"])
        flow_module = next(module for module in graph["modules"] if module["type"] == "flow")
        self.assertEqual("square", flow_module["settings"]["imageAspect"])
        self.assertEqual(12, flow_module["settings"]["imageCount"])
        self.assertTrue(flow_module["settings"]["flowAgentEnabled"])
        self.assertTrue(flow_module["settings"]["flowAgentAutoApprove"])

    async def test_auto_trello_uses_flow_agent_instruction_without_sheet_items(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="Tạo ảnh sản phẩm thương mại để gửi Telegram duyệt",
                count=1,
                aspect="landscape",
                flow_agent_enabled=False,
                flow_agent_auto_approve=False,
                prompt_product="gấu bông",
                prompt_product_key="gấu bông",
                trello_board_id="https://trello.com/b/board123/demo-board",
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {"trelloBoard": "https://trello.com/b/board123/demo-board"},
                        },
                        {
                            "id": "flow-1",
                            "type": "flow",
                            "title": "Google Flow",
                            "settings": {
                                "flowAgentEnabled": False,
                                "flowAgentAutoApprove": False,
                                "imageAspect": "landscape",
                                "imageCount": 1,
                            },
                        },
                    ]
                },
            ),
            limit=10,
            auto_trello=True,
            items=[],
        )
        seen: list[tuple[str, str, str, int, bool, bool]] = []
        cards = [
            {
                "id": "card-bear",
                "name": "Gấu bông dễ thương",
                "shortLink": "bear",
                "url": "https://trello.com/c/bear",
                "idList": "ready-list",
                "_image_attachments": [{"name": "gau-bong.png", "mimeType": "image/png"}],
            }
        ]

        async def fake_run_flow_job(job_id, child_request):
            seen.append(
                (
                    child_request.prompt,
                    child_request.trello_card_id,
                    child_request.aspect,
                    child_request.count,
                    child_request.flow_agent_enabled,
                    child_request.flow_agent_auto_approve,
                )
            )
            await self.store.patch_job(job_id, status="completed", result={"count": child_request.count, "mode": "image"})

        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False), patch.object(
            self.service,
            "get_auth_status",
            return_value=AuthStatus(authenticated=True),
        ), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=cards,
        ), patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ):
            batch = await self.service.enqueue_prompt_batch(request)
            await self.service._tasks[batch.id]

        saved = self.store.get_job(batch.id)
        self.assertEqual("completed", saved.status)
        self.assertEqual("flow_agent", saved.result["trello_source_hint"]["prompt_mode"])
        self.assertEqual(1, saved.result["total"])
        self.assertEqual("card-bear", saved.input["items"][0]["trello_card_id"])
        self.assertTrue(saved.input["items"][0]["flow_agent_instruction"])
        self.assertTrue(saved.input["items"][0]["generated_by_flow_agent"])
        self.assertFalse(saved.input["items"][0]["generated_by_ai"])
        self.assertEqual(12, saved.input["items"][0]["flow_agent_image_count"])
        self.assertEqual(
            [
                "Gấu bông image 1 Product display",
                "Gấu bông image 2 Baby hug",
                "Gấu bông image 3 Baby sleep",
                "Gấu bông image 4 Mẹ & bé trên sofa",
                "Gấu bông image 5 Nursery cot",
                "Gấu bông image 6 Gift box",
                "Gấu bông image 7 Cận thêu tay",
                "Gấu bông image 8 Bé ôm trên chăn muslin",
                "Gấu bông image 9 Flat lay baby shower",
                "Gấu bông image 10 Vintage floral",
                "Gấu bông image 11 Editorial — Grid quy trình",
                "Gấu bông image 12 Supplemental full product hero",
            ],
            saved.input["items"][0]["shot_labels"],
        )
        self.assertEqual("card-bear", seen[0][1])
        self.assertEqual("square", seen[0][2])
        self.assertEqual(12, seen[0][3])
        self.assertTrue(seen[0][4])
        self.assertTrue(seen[0][5])
        self.assertIn("Google Flow Agent", seen[0][0])
        self.assertIn("generate exactly 12", seen[0][0])
        self.assertIn("clean clear white neutral daylight", seen[0][0])
        self.assertIn("selected Trello attachment", seen[0][0])
        self.assertIn("sticker", seen[0][0])
        self.assertIn("price tag", seen[0][0])
        self.assertIn("barcode", seen[0][0])
        self.assertIn("Do not attach any new physical tag to the product itself", seen[0][0])
        self.assertIn("no paper hang tag tied to a strap", seen[0][0])
        self.assertIn("no sewn-in or woven brand label", seen[0][0])
        self.assertIn("no tag, card, or label may touch, cover, hang from", seen[0][0])
        self.assertNotIn("name tag", seen[0][0])

    async def test_auto_trello_rejects_explicit_card_outside_ready(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        await self.store.replace_trello_config(TrelloConfig(api_key="key", token="token", board_id="board123", list_id="ready-list"))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="làm một bộ ảnh sản phẩm này",
                count=1,
                trello_board_id="https://trello.com/b/board123/demo-board",
                trello_list_id="ideas-list",
                trello_card_id="outside-card",
                trello_attachment_ids=["att-1"],
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {"trelloBoard": "https://trello.com/b/board123/demo-board", "trelloList": "ideas-list"},
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    ]
                },
            ),
            limit=10,
            auto_trello=True,
            items=[],
        )
        selected_card = {
            "id": "outside-card",
            "name": "Apron outside ready",
            "shortLink": "outside",
            "url": "https://trello.com/c/outside",
            "idList": "ideas-list",
            "_image_attachments": [
                {"id": "att-1", "name": "chosen-apron.png", "mimeType": "image/png"},
                {"id": "att-2", "name": "wrong-apron.png", "mimeType": "image/png"},
            ],
        }
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False), patch.object(
            self.service,
            "get_auth_status",
            return_value=AuthStatus(authenticated=True),
        ), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_card_by_id",
            return_value=selected_card,
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=[],
        ) as image_cards, patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ideas",
        ):
            with self.assertRaises(HTTPException) as ctx:
                await self.service.enqueue_prompt_batch(request)

        image_cards.assert_not_called()
        self.assertEqual(400, ctx.exception.status_code)
        self.assertIn("Ready for AI", str(ctx.exception.detail))

    async def test_auto_trello_ai_suite_for_apron_includes_hand_embroidery_shot(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="làm một bộ ảnh cho chiếc tạp dề này, trước khi làm hãy phân tích thiết kế, bắt buộc có 1 ảnh thể hiện đây là sản phẩm thêu tay",
                count=1,
                prompt_product="tạp dề thêu tay",
                prompt_product_key="tạp dề thêu tay",
                trello_board_id="https://trello.com/b/board123/demo-board",
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {"trelloBoard": "https://trello.com/b/board123/demo-board"},
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    ]
                },
            ),
            limit=10,
            auto_trello=True,
            items=[],
        )
        seen_prompts: list[str] = []
        cards = [
            {
                "id": "card-apron",
                "name": "Hand-Embroidered Baking Apron",
                "shortLink": "apron",
                "url": "https://trello.com/c/apron",
                "idList": "ready-list",
                "_image_attachments": [{"name": "white-ruffled-apron-embroidery.png", "mimeType": "image/png"}],
            }
        ]

        async def fake_run_flow_job(job_id, child_request):
            seen_prompts.append(child_request.prompt)
            await self.store.patch_job(job_id, status="completed", result={"count": 1, "mode": "image"})

        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False), patch.object(
            self.service,
            "get_auth_status",
            return_value=AuthStatus(authenticated=True),
        ), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=cards,
        ), patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ):
            batch = await self.service.enqueue_prompt_batch(request)
            await self.service._tasks[batch.id]

        saved = self.store.get_job(batch.id)
        self.assertEqual("completed", saved.status)
        self.assertEqual(1, saved.result["total"])
        self.assertEqual(
            [
                "Hand embroidery detail",
                "Full front hero",
                "Lifestyle baking action",
                "Back tie fit",
                "Flat lay styling",
                "Gift artisan scene",
                "Hands embroidering apron",
                "Prep table detail",
                "Pastel fabric colorway lineup",
                "Soft room colorway trio",
                "Pastel swatch flat lay",
                "Color option display",
            ],
            saved.input["items"][0]["shot_labels"],
        )
        self.assertTrue(saved.input["items"][0]["flow_agent_instruction"])
        self.assertEqual(12, saved.input["items"][0]["flow_agent_image_count"])
        self.assertIn("hand-embroidered", seen_prompts[0])
        self.assertIn("Extreme macro close-up", seen_prompts[0])
        self.assertIn("generate exactly 12", seen_prompts[0])
        self.assertIn("clean clear white neutral daylight", seen_prompts[0])
        self.assertTrue(all("Before creating images, carefully analyze" in prompt for prompt in seen_prompts))
        self.assertIn("apron silhouette", saved.input["items"][0]["design_analysis"])

    async def test_auto_trello_flow_agent_uses_learned_product_prompt_style_for_pillowcase(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="tạo bộ ảnh giống phong cách prompt mẫu, mỗi ảnh riêng biệt, có ảnh chứng minh thêu tay",
                count=1,
                prompt_product="vỏ gối em bé thêu tay",
                prompt_product_key="vỏ gối em bé thêu tay",
                trello_board_id="https://trello.com/b/board123/demo-board",
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {"trelloBoard": "https://trello.com/b/board123/demo-board"},
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    ]
                },
            ),
            limit=10,
            auto_trello=True,
            items=[],
        )
        cards = [
            {
                "id": "card-pillow",
                "name": "Embroidered Baby Pillow Collection",
                "shortLink": "pillow",
                "url": "https://trello.com/c/pillow",
                "idList": "ready-list",
                "_image_attachments": [{"name": "baby_pillowcase_fox_bunny_embroidery.png", "mimeType": "image/png"}],
            }
        ]
        seen_prompts: list[str] = []

        async def fake_run_flow_job(job_id, child_request):
            seen_prompts.append(child_request.prompt)
            await self.store.patch_job(job_id, status="completed", result={"count": 1, "mode": "image"})

        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False), patch.object(
            self.service,
            "get_auth_status",
            return_value=AuthStatus(authenticated=True),
        ), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=cards,
        ), patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ):
            batch = await self.service.enqueue_prompt_batch(request)
            await self.service._tasks[batch.id]

        saved = self.store.get_job(batch.id)
        self.assertEqual("completed", saved.status)
        self.assertEqual(
            [
                "Baby Pillowcase image 1 Mẹ bế bé + gối thêu tên",
                "Baby Pillowcase image 2 Hero — gối trên giường nursery",
                "Baby Pillowcase image 3 2 gối cùng màu — khác tên",
                "Baby Pillowcase image 4 4 gối stack dọc",
                "Baby Pillowcase image 5 3 gối 3 màu",
                "Baby Pillowcase image 6 Cận thêu — collage",
                "Baby Pillowcase image 7 Bé nằm trên gối",
                "Baby Pillowcase image 8 3 gối tổng hợp",
                "Baby Pillowcase image 9 Quy trình thêu",
                "Baby Pillowcase image 10 Standalone đơn",
                "Baby Pillowcase image 11 2 trẻ nằm — 2 tên khác",
                "Baby Pillowcase image 12 Gift box — quà sinh nhật",
            ],
            saved.input["items"][0]["shot_labels"],
        )
        self.assertIn("Baby Pillowcase category", saved.input["items"][0]["design_analysis"])
        prompt = seen_prompts[0]
        self.assertIn("learned product-prompt style", prompt)
        self.assertIn("numbered shot brief", prompt)
        self.assertIn("separate standalone 1:1 images", prompt)
        self.assertIn("never make a collage", prompt)
        self.assertIn("fabric texture", prompt)

    async def test_auto_trello_ai_suite_does_not_reuse_apron_template_for_doll_query(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="làm một bộ ảnh cho chiếc tạp dề này, trước khi làm hãy phân tích thiết kế, bắt buộc có 1 ảnh thể hiện đây là sản phẩm thêu tay",
                count=1,
                prompt_product="búp bê",
                prompt_product_key="búp bê",
                trello_board_id="https://trello.com/b/board123/demo-board",
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {
                                "trelloBoard": "https://trello.com/b/board123/demo-board",
                                "trelloCard": "BDA_05",
                                "trelloAttachmentIds": ["att-doll"],
                            },
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    ]
                },
                trello_card_id="BDA_05",
                trello_attachment_ids=["att-doll"],
            ),
            limit=6,
            auto_trello=True,
            items=[],
        )
        card = {
            "id": "card-doll",
            "name": "BDA_05",
            "shortLink": "BDA_05",
            "url": "https://trello.com/c/BDA05",
            "idList": "ready-list",
            "_image_attachments": [{"id": "att-doll", "name": "baby-doll-reference.png", "mimeType": "image/png"}],
        }
        seen_prompts: list[str] = []

        async def fake_run_flow_job(job_id, child_request):
            seen_prompts.append(child_request.prompt)
            await self.store.patch_job(job_id, status="completed", result={"count": 1, "mode": "image"})

        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False), patch.object(
            self.service,
            "get_auth_status",
            return_value=AuthStatus(authenticated=True),
        ), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_card_by_id",
            return_value=card,
        ), patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ):
            batch = await self.service.enqueue_prompt_batch(request)
            await self.service._tasks[batch.id]

        saved = self.store.get_job(batch.id)
        self.assertEqual("completed", saved.status)
        self.assertEqual(1, saved.result["total"])
        self.assertEqual(
            [
                "Craft detail proof",
                "Full collection hero",
                "Lifestyle nursery scene",
                "Angle and scale",
                "Flat lay styling",
                "Gift ready scene",
                "Hands sewing doll detail",
                "Handheld scale detail",
                "Pastel fabric colorway lineup",
                "Soft room colorway trio",
                "Pastel swatch flat lay",
                "Color option display",
            ],
            saved.input["items"][0]["shot_labels"],
        )
        self.assertTrue(saved.input["items"][0]["flow_agent_instruction"])
        self.assertEqual(12, saved.input["items"][0]["flow_agent_image_count"])
        combined = "\n".join([*seen_prompts, saved.input["items"][0]["design_analysis"]]).lower()
        self.assertIn("doll", combined)
        self.assertNotIn("apron silhouette", combined)
        self.assertNotIn("selected apron", combined)

    async def test_auto_trello_does_not_match_short_alias_inside_attachment_urls(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="tạo ảnh búp bê",
                count=1,
                prompt_product="búp bê",
                prompt_product_key="búp bê",
                trello_board_id="https://trello.com/b/board123/demo-board",
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {"trelloBoard": "https://trello.com/b/board123/demo-board"},
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    ]
                },
            ),
            limit=6,
            auto_trello=True,
            items=[],
        )
        cards = [
            {
                "id": "wrong-card",
                "name": "WHA_11",
                "shortLink": "wrong",
                "url": "https://trello.com/c/wrong",
                "idList": "ready-list",
                "_image_attachments": [
                    {
                        "id": "att-wrong",
                        "name": "Generated Image May 08.jpg",
                        "url": "https://trello.local/random-bda-token.png",
                        "mimeType": "image/png",
                    }
                ],
            },
            {
                "id": "card-doll",
                "name": "BDA_05",
                "shortLink": "doll",
                "url": "https://trello.com/c/doll",
                "idList": "ready-list",
                "_image_attachments": [{"id": "att-doll", "name": "front.jpg", "mimeType": "image/png"}],
            },
        ]
        seen_cards: list[str] = []

        async def fake_run_flow_job(job_id, child_request):
            seen_cards.append(child_request.trello_card_id)
            await self.store.patch_job(job_id, status="completed", result={"count": 1, "mode": "image"})

        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "GOOGLE_GENAI_API_KEY": ""}, clear=False), patch.object(
            self.service,
            "get_auth_status",
            return_value=AuthStatus(authenticated=True),
        ), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=cards,
        ), patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ):
            batch = await self.service.enqueue_prompt_batch(request)
            await self.service._tasks[batch.id]

        saved = self.store.get_job(batch.id)
        self.assertEqual("completed", saved.status)
        self.assertTrue(seen_cards)
        self.assertTrue(all(card_id == "card-doll" for card_id in seen_cards))

    async def test_auto_trello_prompt_batch_can_search_card_by_user_keyword(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="",
                count=1,
                prompt_product="gấu",
                prompt_product_key="gấu",
                trello_board_id="https://trello.com/b/board123/demo-board",
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {"trelloBoard": "https://trello.com/b/board123/demo-board"},
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    ]
                },
            ),
            limit=10,
            auto_trello=True,
            items=[
                {"row": 2, "prompt": "bear plush product prompt", "product_key": "gau_bong", "product": "Gấu bông", "index": "1", "active": True},
            ],
        )
        seen: list[tuple[str, str]] = []
        cards = [
            {
                "id": "card-bear",
                "name": "Bear plush product card",
                "shortLink": "bear",
                "url": "https://trello.com/c/bear",
                "idList": "ready-list",
                "_image_attachments": [{"name": "gau-bong.png", "mimeType": "image/png"}],
            }
        ]

        async def fake_run_flow_job(job_id, child_request):
            seen.append((child_request.prompt, child_request.trello_card_id))
            await self.store.patch_job(job_id, status="completed", result={"count": 1, "mode": "image"})

        with patch.object(self.service, "get_auth_status", return_value=AuthStatus(authenticated=True)), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=cards,
        ), patch.object(
            self.service,
            "_trello_list_name",
            return_value="Ready for AI",
        ), patch.object(
            self.service,
            "_run_flow_job",
            side_effect=fake_run_flow_job,
        ):
            batch = await self.service.enqueue_prompt_batch(request)
            await self.service._tasks[batch.id]

        self.assertEqual([("bear plush product prompt", "card-bear")], seen)
        saved = self.store.get_job(batch.id)
        self.assertEqual("completed", saved.status)
        self.assertEqual("keyword", saved.result["trello_source_hint"]["match_mode"])
        self.assertEqual("gấu", saved.input["items"][0]["trello_search_query"])
        child_jobs = [self.store.get_job(job_id) for job_id in saved.result["child_job_ids"]]
        self.assertEqual(["card-bear"], [job.input["trello_card_id"] for job in child_jobs])

    async def test_auto_trello_keyword_search_does_not_use_unrelated_prompt(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="",
                count=1,
                prompt_product="gấu",
                prompt_product_key="gấu",
                trello_board_id="https://trello.com/b/board123/demo-board",
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {"trelloBoard": "https://trello.com/b/board123/demo-board"},
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    ]
                },
            ),
            limit=10,
            auto_trello=True,
            items=[
                {"row": 2, "prompt": "unrelated toy prompt", "product_key": "toy", "product": "Toy", "index": "1", "active": True},
            ],
        )
        cards = [
            {
                "id": "card-bear",
                "name": "Gấu bông dễ thương",
                "shortLink": "bear",
                "url": "https://trello.com/c/bear",
                "idList": "ready-list",
                "_image_attachments": [{"name": "gau-bong.png", "mimeType": "image/png"}],
            }
        ]

        with patch.object(self.service, "get_auth_status", return_value=AuthStatus(authenticated=True)), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=cards,
        ):
            with self.assertRaises(HTTPException) as ctx:
                await self.service.enqueue_prompt_batch(request)

        self.assertEqual(400, ctx.exception.status_code)
        self.assertIn("chưa tìm thấy prompt Active khớp", str(ctx.exception.detail))

    async def test_auto_trello_keyword_search_rejects_ambiguous_cards(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = PromptBatchRequest(
            job=CreateJobRequest(
                type="image",
                prompt="",
                count=1,
                prompt_product="gấu",
                prompt_product_key="gấu",
                trello_board_id="https://trello.com/b/board123/demo-board",
                automation_graph={
                    "modules": [
                        {
                            "id": "trello-source-1",
                            "type": "trello_source",
                            "title": "Trello Image Source",
                            "settings": {"trelloBoard": "https://trello.com/b/board123/demo-board"},
                        },
                        {"id": "flow-1", "type": "flow", "title": "Google Flow"},
                    ]
                },
            ),
            limit=10,
            auto_trello=True,
            items=[
                {"row": 2, "prompt": "bear plush product prompt", "product_key": "gau_bong", "product": "Gấu bông", "index": "1", "active": True},
            ],
        )
        cards = [
            {
                "id": "card-bear-1",
                "name": "Cream plush product card",
                "shortLink": "bear1",
                "url": "https://trello.com/c/bear1",
                "idList": "ready-list",
                "_image_attachments": [{"name": "gau-1.png", "mimeType": "image/png"}],
            },
            {
                "id": "card-bear-2",
                "name": "Brown plush product card",
                "shortLink": "bear2",
                "url": "https://trello.com/c/bear2",
                "idList": "ready-list",
                "_image_attachments": [{"name": "gau-2.png", "mimeType": "image/png"}],
            },
        ]

        with patch.object(self.service, "get_auth_status", return_value=AuthStatus(authenticated=True)), patch.object(
            self.service,
            "_trello_credentials",
            return_value=("key", "token"),
        ), patch.object(
            self.service,
            "_trello_resolve_board_list_id",
            return_value="ready-list",
        ), patch.object(
            self.service,
            "_trello_image_cards_on_board",
            return_value=cards,
        ):
            with self.assertRaises(HTTPException) as ctx:
                await self.service.enqueue_prompt_batch(request)

        self.assertEqual(400, ctx.exception.status_code)
        self.assertIn("nhiều card cùng khớp", str(ctx.exception.detail))

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
        generate_via_ui.assert_awaited_once_with(fake_client, request, [], job_id=job.id)

    async def test_generate_images_with_retry_uses_flow_agent_ui_for_trello_reference(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        request = CreateJobRequest(
            type="image",
            prompt="Use Google Flow Agent as the prompt writer and image-generation operator.",
            count=4,
            trello_card_id="card-123",
            flow_agent_enabled=True,
        )
        job = JobRecord(
            type="image",
            status="queued",
            title=self.service._default_title(request),
            input=request.model_dump(mode="json"),
        )
        await self.store.add_job(job)
        fake_client = SimpleNamespace()
        fake_image = SimpleNamespace(media_name="img-1")

        with patch.object(self.service, "_generate_images_once", AsyncMock()) as generate_once, patch.object(
            self.service,
            "_generate_images_via_ui",
            AsyncMock(return_value=[fake_image]),
        ) as generate_via_ui:
            result = await self.service._generate_images_with_retry(fake_client, job.id, request, ["source-media"])

        self.assertEqual([fake_image], result)
        generate_once.assert_not_awaited()
        generate_via_ui.assert_awaited_once_with(fake_client, request, ["source-media"], job_id=job.id)

    async def test_generate_images_with_retry_uses_flow_agent_ui_for_local_trello_source(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        source = self.uploads_dir / "trello-source.jpg"
        source.write_bytes(b"source")
        request = CreateJobRequest(
            type="image",
            prompt="Use Google Flow Agent as the prompt writer and image-generation operator.",
            count=4,
            trello_card_id="card-123",
            flow_agent_enabled=True,
            reference_image_paths=[str(source)],
        )
        job = JobRecord(
            type="image",
            status="queued",
            title=self.service._default_title(request),
            input=request.model_dump(mode="json"),
        )
        await self.store.add_job(job)
        fake_client = SimpleNamespace()
        fake_image = SimpleNamespace(media_name="img-1")

        with patch.object(self.service, "_generate_images_once", AsyncMock()) as generate_once, patch.object(
            self.service,
            "_generate_images_via_ui",
            AsyncMock(return_value=[fake_image]),
        ) as generate_via_ui:
            result = await self.service._generate_images_with_retry(fake_client, job.id, request, [])

        self.assertEqual([fake_image], result)
        generate_once.assert_not_awaited()
        generate_via_ui.assert_awaited_once_with(fake_client, request, [], job_id=job.id)

    async def test_generate_images_via_ui_uses_single_reference_fallback(self) -> None:
        request = CreateJobRequest(type="image", prompt="them kinh", count=1, aspect="portrait", flow_agent_enabled=False)
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

    async def test_generate_images_via_ui_passes_flow_agent_flag(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="them kinh",
            count=1,
            flow_agent_enabled=False,
            flow_agent_auto_approve=False,
            reference_image_paths=["/tmp/source.jpg"],
        )
        fake_image = SimpleNamespace(media_name="img-1")
        fake_client = SimpleNamespace()

        with patch.object(
            self.service,
            "_generate_single_reference_image_via_ui",
            AsyncMock(return_value=[fake_image]),
        ) as single_ref:
            result = await self.service._generate_images_via_ui(fake_client, request, ["base-media"])

        self.assertEqual([fake_image], result)
        self.assertFalse(single_ref.await_args.kwargs["flow_agent_enabled"])
        self.assertFalse(single_ref.await_args.kwargs["flow_agent_auto_approve"])
        self.assertEqual("/tmp/source.jpg", single_ref.await_args.kwargs["reference_image_path"])

    async def test_generate_images_via_ui_uses_local_source_when_reference_media_missing(self) -> None:
        source = self.uploads_dir / "trello-source.jpg"
        source.write_bytes(b"source")
        request = CreateJobRequest(
            type="image",
            prompt="Use Google Flow Agent as the prompt writer and image-generation operator.",
            count=4,
            flow_agent_enabled=True,
            flow_agent_auto_approve=True,
            reference_image_paths=[str(source)],
        )
        fake_images = [SimpleNamespace(media_name=f"img-{index}") for index in range(4)]
        fake_client = SimpleNamespace()

        with patch.object(
            self.service,
            "_find_workflow_id_for_media",
            AsyncMock(return_value=""),
        ) as find_workflow, patch.object(
            self.service,
            "_generate_single_reference_image_via_ui",
            AsyncMock(return_value=fake_images),
        ) as single_ref:
            result = await self.service._generate_images_via_ui(fake_client, request, [])

        self.assertEqual(fake_images, result)
        find_workflow.assert_not_awaited()
        single_ref.assert_awaited_once()
        self.assertEqual("", single_ref.await_args.kwargs["reference_media_name"])
        self.assertEqual("", single_ref.await_args.kwargs["workflow_id"])
        self.assertEqual(str(source.resolve()), single_ref.await_args.kwargs["reference_image_path"])

    async def test_generate_images_via_ui_uses_flow_agent_x8_single_pass(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="tao bo anh san pham",
            count=8,
            flow_agent_enabled=True,
            flow_agent_auto_approve=True,
            reference_image_paths=["/tmp/source.jpg"],
            workflow_id="stale-active-workflow",
        )
        fake_images = [SimpleNamespace(media_name=f"img-{index}") for index in range(8)]
        fake_client = SimpleNamespace()

        with patch.object(
            self.service,
            "_find_workflow_id_for_media",
            AsyncMock(return_value="source-workflow"),
        ) as find_workflow, patch.object(
            self.service,
            "_generate_single_reference_image_via_ui",
            AsyncMock(return_value=fake_images),
        ) as single_ref:
            result = await self.service._generate_images_via_ui(fake_client, request, ["base-media"])

        self.assertEqual(fake_images, result)
        find_workflow.assert_awaited_once_with(fake_client, "base-media")
        single_ref.assert_awaited_once()
        self.assertEqual(8, single_ref.await_args.kwargs["count"])
        self.assertEqual("source-workflow", single_ref.await_args.kwargs["workflow_id"])
        prompt = single_ref.await_args.args[1]
        self.assertTrue(prompt.startswith("Create exactly 8 separate standalone images now in ONE Flow Agent run."))
        self.assertIn("Use the x8 image setting when available", prompt)
        self.assertIn("Do NOT create a 8-frame grid", prompt)
        self.assertIn("Fresh-task isolation", prompt)
        self.assertIn("Ignore every previous Flow Agent chat message", prompt)
        self.assertIn("HARD REFERENCE LOCK", prompt)
        self.assertIn("ignore other Flow project thumbnails", prompt)
        self.assertIn("do not infer apparel from 'tao_hinh...'", prompt)
        self.assertIn("same pennant/banner shape", prompt)
        self.assertIn("1:1 square image file", prompt)
        self.assertIn("detail/craft proof macro image", prompt)
        self.assertIn("full front hero ecommerce image", prompt)
        self.assertIn("lifestyle use-context image", prompt)
        self.assertIn("flat lay, or gift-ready merchandising image", prompt)
        self.assertIn("hands sewing or embroidering image", prompt)
        self.assertIn("visibly different from each other", prompt)
        self.assertIn("real hand embroidery", prompt)
        self.assertIn("never count the source image as one of the generated outputs", prompt)
        self.assertIn("if the source has no name, do not invent names", prompt)
        self.assertIn("Colorway text/name rule", prompt)
        self.assertIn("each differently colored product variant must use a different plausible name/text", prompt)
        self.assertIn("sticker", prompt)
        self.assertIn("price tag", prompt)
        self.assertIn("barcode", prompt)
        self.assertIn("Do not attach any new physical tag to the product itself", prompt)
        self.assertIn("no paper hang tag tied to a strap", prompt)
        self.assertIn("no sewn-in or woven brand label", prompt)
        self.assertIn("no tag, card, or label may touch, cover, hang from", prompt)
        self.assertNotIn("name tag", prompt)

    async def test_generate_images_via_ui_retries_stale_agent_context_once(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="tao bo anh san pham",
            count=4,
            flow_agent_enabled=True,
            flow_agent_auto_approve=True,
            reference_image_paths=["/tmp/source.jpg"],
            workflow_id="source-workflow",
        )
        fake_images = [SimpleNamespace(media_name=f"img-{index}") for index in range(4)]
        fake_client = SimpleNamespace()
        job = JobRecord(type="image", status="running", title="test")
        await self.store.add_job(job)
        stale_error = RuntimeError(
            "Tac nhan Flow dang mo lai hoi thoai cu hoac ngu canh project cu. "
            "Chi tiet: old context still visible after reset"
        )

        with patch.object(
            self.service,
            "_find_workflow_id_for_media",
            AsyncMock(return_value="source-workflow"),
        ), patch.object(
            self.service,
            "_generate_single_reference_image_via_ui",
            AsyncMock(side_effect=[stale_error, fake_images]),
        ) as single_ref, patch("flow_web.service.asyncio.sleep", new=AsyncMock()) as sleep_mock:
            result = await self.service._generate_images_via_ui(fake_client, request, ["base-media"], job_id=job.id)

        self.assertEqual(fake_images, result)
        self.assertEqual(2, single_ref.await_count)
        sleep_mock.assert_any_await(4.0)
        updated = self.store.get_job(job.id)
        self.assertTrue(any("hội thoại/ngữ cảnh cũ" in entry.message for entry in (updated.logs if updated else [])))

    async def test_generate_images_via_ui_uses_flow_agent_x12_single_pass(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="tao bo anh san pham",
            count=12,
            flow_agent_enabled=True,
            flow_agent_auto_approve=True,
            reference_image_paths=["/tmp/source.jpg"],
        )
        fake_images = [SimpleNamespace(media_name=f"img-{index}") for index in range(12)]
        fake_client = SimpleNamespace()
        job = JobRecord(type="image", status="running", title="test")
        await self.store.add_job(job)

        with patch.object(
            self.service,
            "_find_workflow_id_for_media",
            AsyncMock(return_value="source-workflow"),
        ), patch.object(
            self.service,
            "_generate_single_reference_image_via_ui",
            AsyncMock(return_value=fake_images),
        ) as single_ref, patch.object(
            self.service,
            "_sleep_between_flow_agent_batches",
            new=AsyncMock(),
        ) as pause:
            result = await self.service._generate_images_via_ui(fake_client, request, ["base-media"], job_id=job.id)

        self.assertEqual(fake_images, result)
        single_ref.assert_awaited_once()
        self.assertEqual(12, single_ref.await_args.kwargs["count"])
        prompt = single_ref.await_args.args[1]
        self.assertTrue(prompt.startswith("Create exactly 12 separate standalone images now in ONE Flow Agent run."))
        self.assertIn("Use the x12 image setting when available", prompt)
        self.assertIn("This run must produce the full image set.", prompt)
        self.assertIn("Fresh-task isolation", prompt)
        self.assertIn("HARD REFERENCE LOCK", prompt)
        self.assertIn("not landscape, not portrait", prompt)
        self.assertIn("pastel fabric colorway lineup image", prompt)
        self.assertIn("no yellow, orange, golden-hour", prompt)
        self.assertIn("real hand embroidery", prompt)
        self.assertIn("tack-sharp around the embroidered areas", prompt)
        self.assertIn("never count the source image as one of the generated outputs", prompt)
        self.assertIn("if the source has no name, do not invent names", prompt)
        self.assertIn("Colorway text/name rule", prompt)
        self.assertIn("never repeat the exact same readable name/text across all color variants", prompt)
        pause.assert_not_awaited()

    async def test_generate_images_via_ui_uploads_partial_flow_agent_outputs(self) -> None:
        request = CreateJobRequest(
            type="image",
            prompt="tao bo anh san pham",
            count=12,
            flow_agent_enabled=True,
            flow_agent_auto_approve=True,
            reference_image_paths=["/tmp/source.jpg"],
        )
        fake_images = [SimpleNamespace(media_name=f"img-{index}") for index in range(9)]
        fake_client = SimpleNamespace()
        job = JobRecord(type="image", status="running", title="test")
        await self.store.add_job(job)

        with patch.object(
            self.service,
            "_find_workflow_id_for_media",
            AsyncMock(return_value="source-workflow"),
        ), patch.object(
            self.service,
            "_generate_single_reference_image_via_ui",
            AsyncMock(return_value=fake_images),
        ) as single_ref:
            result = await self.service._generate_images_via_ui(fake_client, request, ["base-media"], job_id=job.id)

        self.assertEqual(fake_images, result)
        single_ref.assert_awaited_once()
        updated = self.store.get_job(job.id)
        messages = [entry.message for entry in (updated.logs if updated else [])]
        self.assertTrue(any("9/12" in message and "upload 9 anh" in message for message in messages))

    async def test_single_reference_ui_requires_flow_agent_mode_when_enabled(self) -> None:
        events: list[str] = []

        class FakePage:
            url = "https://labs.google/fx/tools/flow/project/pid/edit/wf-source"

            async def goto(self, *_args: object, **_kwargs: object) -> None:
                events.append("goto")

        class FakeBrowserManager:
            async def page(self) -> FakePage:
                return FakePage()

        class FakeFlowUI:
            async def open_settings_panel(self, _page: FakePage) -> None:
                events.append("settings")

            async def select_image_model(self, _page: FakePage, _model: str) -> None:
                events.append("model")

            async def set_aspect_ratio(self, _page: FakePage, _ratio: object) -> None:
                events.append("aspect")

            async def set_count(self, _page: FakePage, _count: int) -> None:
                events.append("count")

            async def fill_prompt(self, _page: FakePage, _prompt: str) -> bool:
                events.append("fill_prompt")
                return True

        class FakeInterceptor:
            def attach(self, _page: FakePage) -> None:
                events.append("interceptor")

            def clear(self) -> None:
                events.append("clear")

        fake_client = SimpleNamespace(
            project_id="pid",
            _bm=FakeBrowserManager(),
            _ui=FakeFlowUI(),
        )

        with patch("flow._ui_interceptor.UIInterceptor", return_value=FakeInterceptor()), patch.object(
            self.service,
            "_find_workflow_id_for_media",
            AsyncMock(return_value="wf-source"),
        ), patch.object(
            self.service,
            "_select_flow_edit_target_image",
            AsyncMock(return_value=(True, "selected source")),
        ) as select_image, patch.object(
            self.service,
            "_enable_flow_agent_mode",
            AsyncMock(return_value=(False, "no visible Tac nhan/Agent button")),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                await self.service._generate_single_reference_image_via_ui(
                    fake_client,
                    "tao 4 anh san pham tu anh goc",
                    model="NARWHAL",
                    reference_media_name="source-media",
                    count=4,
                    flow_agent_enabled=True,
                    flow_agent_auto_approve=True,
                )

        self.assertIn("bắt buộc dùng Tác nhân Flow", str(ctx.exception))
        self.assertNotIn("fill_prompt", events)
        select_image.assert_not_awaited()

    async def test_single_reference_ui_drags_source_into_agent_panel_before_send(self) -> None:
        events: list[str] = []
        fake_image = SimpleNamespace(media_name="generated-1")

        class FakePage:
            url = "https://labs.google/fx/tools/flow/project/pid"

            async def goto(self, *_args: object, **_kwargs: object) -> None:
                events.append("goto")

        class FakeBrowserManager:
            async def page(self) -> FakePage:
                return FakePage()

        class FakeFlowUI:
            async def open_settings_panel(self, _page: FakePage) -> None:
                events.append("settings")

            async def select_image_model(self, _page: FakePage, _model: str) -> None:
                events.append("model")

            async def set_aspect_ratio(self, _page: FakePage, _ratio: object) -> None:
                events.append("aspect")

            async def set_count(self, _page: FakePage, _count: int) -> None:
                events.append("count")

        class FakeFlowAPI:
            async def get_project_data(self) -> dict:
                events.append("project_data")
                return {"projectContents": {"media": []}}

        class FakeInterceptor:
            def attach(self, _page: FakePage) -> None:
                events.append("interceptor")

            def clear(self) -> None:
                events.append("clear")

            async def wait_for(self, *_args: object, **_kwargs: object) -> SimpleNamespace:
                events.append("wait")
                return SimpleNamespace(req={"requests": []}, resp={"media": []})

        fake_client = SimpleNamespace(
            project_id="pid",
            _bm=FakeBrowserManager(),
            _ui=FakeFlowUI(),
            _api=FakeFlowAPI(),
        )

        async def select_source(*_args: object, **kwargs: object) -> tuple[bool, str]:
            events.append("drag")
            self.assertTrue(kwargs.get("require_agent_panel"))
            return True, "drag source into agent panel"

        with patch("flow._ui_interceptor.UIInterceptor", return_value=FakeInterceptor()), patch.object(
            self.service,
            "_find_workflow_id_for_media",
            AsyncMock(return_value="wf-source"),
        ), patch.object(
            self.service,
            "_enable_flow_agent_mode",
            AsyncMock(side_effect=lambda *_args, **_kwargs: events.append("agent") or (True, "Tác nhân")),
        ), patch.object(
            self.service,
            "_open_flow_agent_panel",
            AsyncMock(side_effect=lambda *_args, **_kwargs: events.append("panel") or (True, "agent panel visible")),
        ), patch.object(
            self.service,
            "_fill_flow_agent_panel_instruction",
            AsyncMock(side_effect=lambda *_args, **_kwargs: events.append("fill_panel") or (True, "panel textbox")),
        ), patch.object(
            self.service,
            "_select_flow_edit_target_image",
            AsyncMock(side_effect=select_source),
        ) as select_image, patch.object(
            self.service,
            "_wait_for_flow_agent_source_attachment",
            AsyncMock(side_effect=lambda *_args, **_kwargs: events.append("verify") or (True, "new attachment visible 0->1")),
        ) as verify_source, patch.object(
            self.service,
            "_attach_flow_agent_source_file",
            AsyncMock(return_value=(True, "upload fallback")),
        ) as attach_file, patch.object(
            self.service,
            "_click_flow_agent_panel_send",
            AsyncMock(side_effect=lambda *_args, **_kwargs: events.append("send") or (True, "send arrow")),
        ), patch.object(
            self.service,
            "_ensure_flow_agent_panel_submitted",
            AsyncMock(side_effect=lambda *_args, **_kwargs: events.append("ensure") or (True, "prompt already submitted", False)),
        ) as ensure_panel, patch.object(
            self.service,
            "_approve_flow_agent_generation",
            AsyncMock(side_effect=lambda *_args, **_kwargs: events.append("approve") or (True, "approved")),
        ), patch.object(
            self.service,
            "_flow_image_call_uses_selected_image",
            return_value=True,
        ), patch.object(
            self.service,
            "_parse_images_from_flow_payload",
            return_value=[fake_image],
        ):
            result = await self.service._generate_single_reference_image_via_ui(
                fake_client,
                "tao 4 anh san pham tu anh goc",
                model="NARWHAL",
                reference_media_name="source-media",
                reference_image_path="/tmp/source.jpg",
                count=1,
                flow_agent_enabled=True,
                flow_agent_auto_approve=True,
            )

        self.assertEqual([fake_image], result)
        select_image.assert_awaited_once()
        verify_source.assert_awaited_once()
        attach_file.assert_not_awaited()
        self.assertFalse(ensure_panel.await_args.kwargs["submit_if_needed"])
        self.assertLess(events.index("model"), events.index("aspect"))
        self.assertLess(events.index("aspect"), events.index("count"))
        self.assertLess(events.index("panel"), events.index("fill_panel"))
        self.assertLess(events.index("fill_panel"), events.index("drag"))
        self.assertLess(events.index("drag"), events.index("verify"))
        self.assertLess(events.index("verify"), events.index("send"))
        self.assertLess(events.index("drag"), events.index("send"))
        self.assertLess(events.index("send"), events.index("approve"))

    async def test_single_reference_ui_discards_cached_agent_tab_when_context_stale(self) -> None:
        events: list[str] = []

        class FakePage:
            url = "https://labs.google/fx/tools/flow/project/pid"
            closed = False

            async def goto(self, *_args: object, **_kwargs: object) -> None:
                events.append("goto")

            def is_closed(self) -> bool:
                return self.closed

            async def close(self) -> None:
                self.closed = True
                events.append("close")

        class FakeFlowUI:
            async def open_settings_panel(self, _page: FakePage) -> None:
                events.append("settings")

            async def select_image_model(self, _page: FakePage, _model: str) -> None:
                events.append("model")

            async def set_aspect_ratio(self, _page: FakePage, _ratio: object) -> None:
                events.append("aspect")

            async def set_count(self, _page: FakePage, _count: int) -> None:
                events.append("count")

        class FakeInterceptor:
            def attach(self, _page: FakePage) -> None:
                events.append("interceptor")

            def clear(self) -> None:
                events.append("clear")

        page = FakePage()
        fake_browser = SimpleNamespace(_flow_agent_page=page, _page=page)
        fake_client = SimpleNamespace(project_id="pid", _bm=fake_browser, _ui=FakeFlowUI())
        job = JobRecord(type="image", status="running", title="test")
        await self.store.add_job(job)

        with patch("flow._ui_interceptor.UIInterceptor", return_value=FakeInterceptor()), patch.object(
            self.service,
            "_acquire_isolated_flow_agent_page",
            AsyncMock(return_value=(page, "reused isolated project tab")),
        ), patch.object(
            self.service,
            "_enable_flow_agent_mode",
            AsyncMock(return_value=(True, "Tác nhân")),
        ), patch.object(
            self.service,
            "_open_flow_agent_panel",
            AsyncMock(return_value=(True, "agent panel visible")),
        ), patch.object(
            self.service,
            "_ensure_fresh_flow_agent_panel",
            AsyncMock(return_value=(False, "old context still visible after reset")),
        ), patch("flow_web.service.asyncio.sleep", new=AsyncMock()):
            with self.assertRaisesRegex(RuntimeError, "hoi thoai cu"):
                await self.service._generate_single_reference_image_via_ui(
                    fake_client,
                    "tao 4 anh san pham tu anh goc",
                    model="NARWHAL",
                    reference_media_name="source-media",
                    reference_image_path="/tmp/source.jpg",
                    workflow_id="wf-source",
                    count=1,
                    flow_agent_enabled=True,
                    flow_agent_auto_approve=True,
                    job_id=job.id,
                )

        self.assertTrue(page.closed)
        self.assertIsNone(fake_browser._flow_agent_page)
        self.assertIsNone(fake_browser._page)
        self.assertIn("close", events)

    async def test_single_reference_ui_stops_when_agent_source_not_verified(self) -> None:
        events: list[str] = []

        class FakePage:
            url = "https://labs.google/fx/tools/flow/project/pid"

            async def goto(self, *_args: object, **_kwargs: object) -> None:
                events.append("goto")

        class FakeBrowserManager:
            async def page(self) -> FakePage:
                return FakePage()

        class FakeFlowUI:
            async def open_settings_panel(self, _page: FakePage) -> None:
                events.append("settings")

            async def select_image_model(self, _page: FakePage, _model: str) -> None:
                events.append("model")

            async def set_aspect_ratio(self, _page: FakePage, _ratio: object) -> None:
                events.append("aspect")

            async def set_count(self, _page: FakePage, _count: int) -> None:
                events.append("count")

        class FakeInterceptor:
            def attach(self, _page: FakePage) -> None:
                events.append("interceptor")

            def clear(self) -> None:
                events.append("clear")

        fake_client = SimpleNamespace(
            project_id="pid",
            _bm=FakeBrowserManager(),
            _ui=FakeFlowUI(),
        )

        with patch("flow._ui_interceptor.UIInterceptor", return_value=FakeInterceptor()), patch.object(
            self.service,
            "_find_workflow_id_for_media",
            AsyncMock(return_value="wf-source"),
        ), patch.object(
            self.service,
            "_enable_flow_agent_mode",
            AsyncMock(return_value=(True, "Tac nhan")),
        ), patch.object(
            self.service,
            "_open_flow_agent_panel",
            AsyncMock(return_value=(True, "agent panel visible")),
        ), patch.object(
            self.service,
            "_fill_flow_agent_panel_instruction",
            AsyncMock(return_value=(True, "panel textbox")),
        ), patch.object(
            self.service,
            "_select_flow_edit_target_image",
            AsyncMock(side_effect=lambda *_args, **_kwargs: events.append("drag") or (True, "drag source into agent panel")),
        ), patch.object(
            self.service,
            "_wait_for_flow_agent_source_attachment",
            AsyncMock(side_effect=lambda *_args, **_kwargs: events.append("verify") or (False, "no new attachment visible 0->0")),
        ), patch.object(
            self.service,
            "_attach_flow_agent_source_file",
            AsyncMock(return_value=(True, "should not upload without local source")),
        ) as attach_file, patch.object(
            self.service,
            "_click_flow_agent_panel_send",
            AsyncMock(),
        ) as send:
            with self.assertRaisesRegex(RuntimeError, "chua xac minh duoc anh nguon"):
                await self.service._generate_single_reference_image_via_ui(
                    fake_client,
                    "tao 4 anh san pham tu anh goc",
                    model="NARWHAL",
                    reference_media_name="source-media",
                    count=1,
                    flow_agent_enabled=True,
                    flow_agent_auto_approve=True,
                )

        self.assertIn("drag", events)
        self.assertIn("verify", events)
        attach_file.assert_not_awaited()
        send.assert_not_awaited()

    async def test_single_reference_ui_requires_project_media_baseline_for_trello_source(self) -> None:
        events: list[str] = []

        class FakePage:
            url = "https://labs.google/fx/tools/flow/project/pid"

            async def goto(self, *_args: object, **_kwargs: object) -> None:
                events.append("goto")

        class FakeBrowserManager:
            async def page(self) -> FakePage:
                return FakePage()

        class FakeFlowUI:
            async def open_settings_panel(self, _page: FakePage) -> None:
                events.append("settings")

            async def select_image_model(self, _page: FakePage, _model: str) -> None:
                events.append("model")

            async def set_aspect_ratio(self, _page: FakePage, _ratio: object) -> None:
                events.append("aspect")

            async def set_count(self, _page: FakePage, _count: int) -> None:
                events.append("count")

        class FakeFlowAPI:
            async def get_project_data(self) -> dict:
                events.append("project_data")
                raise RuntimeError("project data unavailable")

        class FakeInterceptor:
            def attach(self, _page: FakePage) -> None:
                events.append("interceptor")

            def clear(self) -> None:
                events.append("clear")

        fake_client = SimpleNamespace(
            project_id="pid",
            _bm=FakeBrowserManager(),
            _ui=FakeFlowUI(),
            _api=FakeFlowAPI(),
        )

        with patch("flow._ui_interceptor.UIInterceptor", return_value=FakeInterceptor()), patch.object(
            self.service,
            "_find_workflow_id_for_media",
            AsyncMock(return_value="wf-source"),
        ), patch.object(
            self.service,
            "_enable_flow_agent_mode",
            AsyncMock(side_effect=lambda *_args, **_kwargs: events.append("agent") or (True, "Tác nhân")),
        ), patch.object(
            self.service,
            "_open_flow_agent_panel",
            AsyncMock(side_effect=lambda *_args, **_kwargs: events.append("panel") or (True, "agent panel visible")),
        ), patch.object(
            self.service,
            "_fill_flow_agent_panel_instruction",
            AsyncMock(side_effect=lambda *_args, **_kwargs: events.append("fill_panel") or (True, "panel textbox")),
        ), patch.object(
            self.service,
            "_select_flow_edit_target_image",
            AsyncMock(side_effect=lambda *_args, **_kwargs: events.append("drag") or (True, "drag source into agent panel")),
        ), patch.object(
            self.service,
            "_wait_for_flow_agent_source_attachment",
            AsyncMock(side_effect=lambda *_args, **_kwargs: events.append("verify") or (True, "new attachment visible 0->1")),
        ), patch.object(
            self.service,
            "_click_flow_agent_panel_send",
            AsyncMock(),
        ) as send:
            with self.assertRaisesRegex(RuntimeError, "tránh lấy nhầm ảnh cũ"):
                await self.service._generate_single_reference_image_via_ui(
                    fake_client,
                    "tao 4 anh san pham tu anh goc",
                    model="NARWHAL",
                    reference_media_name="source-media",
                    reference_image_path="/tmp/source.jpg",
                    count=1,
                    flow_agent_enabled=True,
                    flow_agent_auto_approve=True,
                    require_project_media_baseline=True,
                )

        send.assert_not_awaited()
        self.assertIn("project_data", events)
        self.assertNotIn("send", events)

    async def test_enable_flow_agent_mode_clicks_visible_tac_nhan_button(self) -> None:
        events: list[tuple[str, float, float]] = []

        class FakeMouse:
            async def click(self, x: float, y: float) -> None:
                events.append(("click", x, y))

        class FakePage:
            mouse = FakeMouse()

            async def evaluate(self, script: str) -> dict:
                self.script = script
                return {"ok": True, "x": 160, "y": 720, "detail": "Tác nhân"}

        page = FakePage()
        ok, detail = await self.service._enable_flow_agent_mode(page)

        self.assertTrue(ok)
        self.assertIn("Tác nhân", detail)
        self.assertEqual([("click", 160, 720)], events)

    async def test_ensure_fresh_flow_agent_panel_resets_old_context(self) -> None:
        events: list[str] = []

        class FakePage:
            context_checks = 0

            async def evaluate(self, script: str, *_args: object) -> dict:
                if "has_prior_context" in script:
                    self.context_checks += 1
                    events.append(f"context-{self.context_checks}")
                    return {
                        "visible": True,
                        "has_prior_context": self.context_checks == 1,
                        "detail": "old Flow Agent conversation text is visible" if self.context_checks == 1 else "agent panel looks fresh",
                    }
                if "no start-new-session button" in script:
                    return {"ok": False, "detail": "no start-new-session button"}
                if "agent panel not found for reset" in script:
                    events.append("menu")
                    return {"ok": True, "detail": "agent menu button"}
                events.append("new-chat")
                return {"ok": True, "detail": "New chat"}

        ok, detail = await self.service._ensure_fresh_flow_agent_panel(FakePage())

        self.assertTrue(ok)
        self.assertIn("reset old Agent context", detail)
        self.assertEqual(["context-1", "menu", "new-chat", "context-2"], events[:4])
        self.assertTrue(all(event.startswith("context-") for event in events[4:]))

    async def test_ensure_fresh_flow_agent_panel_blocks_when_old_context_cannot_reset(self) -> None:
        events: list[str] = []

        class FakePage:
            async def evaluate(self, script: str, *_args: object) -> dict:
                if "has_prior_context" in script:
                    events.append("context")
                    return {"visible": True, "has_prior_context": True, "detail": "old Flow Agent conversation text is visible"}
                if "no start-new-session button" in script:
                    return {"ok": False, "detail": "no start-new-session button"}
                events.append("reset")
                return {"ok": False, "detail": "no new chat/session item"}

        ok, detail = await self.service._ensure_fresh_flow_agent_panel(FakePage())

        self.assertFalse(ok)
        self.assertIn("old context visible", detail)
        self.assertEqual(["context", "reset"], events)

    async def test_ensure_fresh_flow_agent_panel_starts_new_session_when_button_exists(self) -> None:
        events: list[str] = []

        class FakeMouse:
            async def click(self, x: float, y: float) -> None:
                events.append(f"click-{int(x)}-{int(y)}")

        class FakePage:
            mouse = FakeMouse()

            async def evaluate(self, script: str, *_args: object) -> object:
                if "has_prior_context" in script:
                    events.append("context")
                    return {"visible": True, "has_prior_context": False, "detail": "agent panel looks fresh"}
                if "no start-new-session button" in script:
                    events.append("new-session-lookup")
                    return {"ok": True, "x": 1361.0, "y": 100.0, "label": "edit_square Start new session"}
                if "elementFromPoint" in script:
                    return "edit_square Start new session"
                raise AssertionError(f"unexpected script: {script[:60]}")

        ok, detail = await self.service._ensure_fresh_flow_agent_panel(FakePage())

        self.assertTrue(ok)
        self.assertIn("start-new-session", detail)
        self.assertIn("click-1361-100", events)
        self.assertEqual("context", events[0])
        self.assertIn("new-session-lookup", events)

    async def test_acquire_isolated_flow_agent_page_opens_new_project_tab(self) -> None:
        events: list[str] = []

        class FakePage:
            url = "about:blank"

            async def goto(self, url: str, *_args: object, **_kwargs: object) -> None:
                events.append(f"goto:{url}")
                self.url = url

            async def bring_to_front(self) -> None:
                events.append("front")

        class FakeContext:
            async def new_page(self) -> FakePage:
                events.append("new_page")
                return FakePage()

        class FakeBrowser:
            context = FakeContext()
            _page = None

            async def page(self) -> FakePage:
                events.append("existing_page")
                return FakePage()

        browser = FakeBrowser()
        client = SimpleNamespace(_bm=browser)

        page, detail = await self.service._acquire_isolated_flow_agent_page(client, "https://labs.google/fx/tools/flow/project/pid")

        self.assertIs(page, browser._page)
        self.assertEqual("new isolated project tab", detail)
        self.assertEqual(["new_page", "goto:https://labs.google/fx/tools/flow/project/pid", "front"], events)

    async def test_approve_flow_agent_generation_clicks_remember_and_approve(self) -> None:
        events: list[tuple[str, float, float]] = []

        class FakeMouse:
            async def click(self, x: float, y: float) -> None:
                events.append(("click", x, y))

        class FakePage:
            mouse = FakeMouse()

            async def evaluate(self, script: str) -> dict:
                self.script = script
                return {
                    "ok": True,
                    "hasRemember": True,
                    "rememberX": 90,
                    "rememberY": 430,
                    "approveX": 720,
                    "approveY": 330,
                    "detail": "Phê duyệt",
                }

        page = FakePage()
        ok, detail = await self.service._approve_flow_agent_generation(page, timeout_s=2)

        self.assertTrue(ok)
        self.assertIn("Phê duyệt", detail)
        self.assertEqual([("click", 90, 430), ("click", 720, 330)], events)
        self.assertIn("Cho\\s*ph", page.script)
        self.assertIn("dialogFallbackButtons", page.script)
        self.assertIn("approvalDialogRoots", page.script)
        self.assertIn("approvalTextRoots", page.script)
        self.assertIn("bodyMentionsApproval", page.script)
        self.assertNotIn("const waiting = approvalTextPattern.test(bodyText)", page.script)
        self.assertIn("isApprovalActionLabel", page.script)
        self.assertIn("Create|Generate|Submit|Send|Go", page.script)
        self.assertIn("delete_forever", page.script)
        self.assertNotIn("document.body.getBoundingClientRect", page.script)

    async def test_open_flow_agent_panel_clicks_unlabeled_bottom_right_arrow(self) -> None:
        events: list[tuple[str, float, float]] = []

        class FakeMouse:
            async def click(self, x: float, y: float) -> None:
                events.append(("click", x, y))

        class FakePage:
            mouse = FakeMouse()

            async def evaluate(self, script: str) -> dict:
                self.script = script
                return {"ok": True, "x": 612, "y": 760, "detail": "agent panel opener"}

        page = FakePage()

        with patch.object(
            self.service,
            "_flow_agent_panel_state",
            AsyncMock(side_effect=[{"visible": False, "detail": "not yet"}, {"visible": True, "detail": "Phiên không có tiêu đề"}]),
        ):
            ok, detail = await self.service._open_flow_agent_panel(page, timeout_s=2)

        self.assertTrue(ok)
        self.assertIn("Phiên", detail)
        self.assertEqual([("click", 612, 760)], events)

    async def test_flow_agent_panel_state_excludes_composer_text_from_submitted_prompt(self) -> None:
        class FakePage:
            async def evaluate(self, script: str, _payload: dict) -> dict:
                self.script = script
                return {
                    "visible": True,
                    "has_textbox": True,
                    "has_prompt": False,
                    "has_prompt_in_textbox": True,
                    "detail": "agent panel visible",
                }

        page = FakePage()
        state = await self.service._flow_agent_panel_state(page, "a sufficiently long prompt probe")

        self.assertFalse(state["has_prompt"])
        self.assertTrue(state["has_prompt_in_textbox"])
        self.assertIn("cloneNode", page.script)
        self.assertIn("has_prompt_in_textbox", page.script)

    async def test_ensure_flow_agent_panel_submitted_reclicks_prompt_left_in_composer(self) -> None:
        states = [
            {
                "visible": True,
                "has_textbox": True,
                "has_prompt": False,
                "has_prompt_in_textbox": True,
                "detail": "agent panel visible",
            },
            {
                "visible": True,
                "has_textbox": True,
                "has_prompt": True,
                "has_prompt_in_textbox": False,
                "detail": "agent panel visible",
            },
        ]
        with patch.object(
            self.service,
            "_flow_agent_panel_state",
            AsyncMock(side_effect=states),
        ), patch.object(
            self.service,
            "_click_flow_agent_panel_send",
            AsyncMock(return_value=(True, "send arrow")),
        ) as send:
            ok, detail, needs_prompt = await self.service._ensure_flow_agent_panel_submitted(
                object(),
                "a sufficiently long prompt probe",
                submit_if_needed=False,
            )

        self.assertTrue(ok)
        self.assertFalse(needs_prompt)
        self.assertIn("send arrow", detail)
        send.assert_awaited_once()

    async def test_flow_agent_send_selector_targets_composer_bottom_right_and_excludes_controls(self) -> None:
        events: list[tuple[float, float]] = []

        class FakeMouse:
            async def click(self, x: float, y: float) -> None:
                events.append((x, y))

        class FakePage:
            mouse = FakeMouse()

            async def evaluate(self, script: str) -> dict:
                self.script = script
                return {"ok": True, "x": 1736, "y": 1165, "detail": "arrow_forward"}

        page = FakePage()
        ok, detail = await self.service._click_flow_agent_panel_send(page)

        self.assertTrue(ok)
        self.assertIn("arrow_forward", detail)
        self.assertEqual([(1736, 1165)], events)
        self.assertIn("nearComposerBottom", page.script)
        self.assertIn("rightZone", page.script)
        self.assertIn("explicitSendButtons", page.script)
        self.assertIn("settings|tune|menu", page.script)

    async def test_wait_for_flow_agent_upload_ready_requires_completed_upload_response(self) -> None:
        interceptor = SimpleNamespace(
            _calls=[
                SimpleNamespace(
                    tail="uploadImage",
                    resp={"media": {"name": "uploaded-source"}},
                    status=200,
                )
            ]
        )

        ok, detail = await self.service._wait_for_flow_agent_upload_ready(interceptor, 0, timeout_s=2)

        self.assertTrue(ok)
        self.assertIn("uploadImage completed [200]", detail)

    async def test_wait_for_flow_agent_upload_ready_rejects_failed_upload_response(self) -> None:
        interceptor = SimpleNamespace(
            _calls=[
                SimpleNamespace(
                    tail="uploadImage",
                    resp={"error": {"message": "upload failed"}},
                    status=500,
                )
            ]
        )

        ok, detail = await self.service._wait_for_flow_agent_upload_ready(interceptor, 0, timeout_s=2)

        self.assertFalse(ok)
        self.assertIn("uploadImage failed [500]", detail)

    async def test_select_flow_edit_target_image_drags_source_into_prompt(self) -> None:
        events: list[tuple[str, float | None, float | None]] = []

        class FakeMouse:
            async def move(self, x: float, y: float) -> None:
                events.append(("move", x, y))

            async def down(self) -> None:
                events.append(("down", None, None))

            async def up(self) -> None:
                events.append(("up", None, None))

            async def click(self, x: float, y: float) -> None:
                events.append(("click", x, y))

        class FakePage:
            mouse = FakeMouse()

            async def evaluate(self, script: str, payload: dict) -> dict:
                self.media_token = payload.get("mediaToken")
                self.workflow_id = payload.get("workflowId")
                self.allow_visible_fallback = payload.get("allowVisibleFallback")
                return {
                    "ok": True,
                    "sourceX": 120,
                    "sourceY": 140,
                    "targetX": 420,
                    "targetY": 820,
                    "detail": "drag div 84,84 -> prompt 431,798",
                }

        page = FakePage()
        ok, detail = await self.service._select_flow_edit_target_image(page, "media-source")

        self.assertTrue(ok)
        self.assertEqual("media-source", page.media_token)
        self.assertEqual("", page.workflow_id)
        self.assertFalse(page.allow_visible_fallback)
        self.assertIn("drag", detail)
        self.assertIn(("down", None, None), events)
        self.assertIn(("up", None, None), events)
        self.assertEqual(("click", 420, 820), events[-1])

    async def test_select_flow_edit_target_image_allows_visible_edit_fallback(self) -> None:
        events: list[tuple[str, float | None, float | None]] = []

        class FakeMouse:
            async def move(self, x: float, y: float) -> None:
                events.append(("move", x, y))

            async def down(self) -> None:
                events.append(("down", None, None))

            async def up(self) -> None:
                events.append(("up", None, None))

            async def click(self, x: float, y: float) -> None:
                events.append(("click", x, y))

        class FakePage:
            mouse = FakeMouse()

            async def evaluate(self, script: str, payload: dict) -> dict:
                self.payload = payload
                return {
                    "ok": True,
                    "sourceX": 210,
                    "sourceY": 180,
                    "targetX": 510,
                    "targetY": 780,
                    "detail": "fallback visible edit image: drag img 110,80 -> prompt 500,760",
                }

        page = FakePage()
        ok, detail = await self.service._select_flow_edit_target_image(
            page,
            "media-not-in-dom",
            workflow_id="workflow-123",
            allow_visible_fallback=True,
        )

        self.assertTrue(ok)
        self.assertTrue(page.payload["allowVisibleFallback"])
        self.assertEqual("media-not-in-dom", page.payload["mediaToken"])
        self.assertEqual("workflow-123", page.payload["workflowId"])
        self.assertIn("fallback visible edit image", detail)
        self.assertEqual(("click", 510, 780), events[-1])

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

    async def test_resolve_image_reference_media_allows_flow_agent_local_fallback_when_upload_fails(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        source = self.uploads_dir / "trello-source.jpg"
        source.write_bytes(b"source")
        job = JobRecord(type="image", status="queued", title="test")
        await self.store.add_job(job)

        request = CreateJobRequest(
            type="image",
            prompt="Use Google Flow Agent as the prompt writer and image-generation operator.",
            count=4,
            trello_card_id="card-123",
            flow_agent_enabled=True,
            reference_image_paths=[str(source)],
        )
        fake_client = SimpleNamespace()

        with patch.object(
            self.service,
            "_upload_project_image_robust",
            AsyncMock(side_effect=RuntimeError("Failed to upload")),
        ) as upload_project_image:
            result = await self.service._resolve_image_reference_media(fake_client, job.id, request)

        self.assertEqual([], result)
        upload_project_image.assert_awaited_once_with(fake_client, str(source.resolve()))
        saved = self.store.get_job(job.id)
        self.assertTrue(any("local source file directly inside Flow Agent" in item.message for item in saved.logs))

    async def test_resolve_image_reference_media_still_fails_without_flow_agent_fallback(self) -> None:
        await self.store.replace_config(AppConfig(project_id="pid", generation_timeout_s=300, poll_interval_s=1.0))
        source = self.uploads_dir / "plain-source.jpg"
        source.write_bytes(b"source")
        job = JobRecord(type="image", status="queued", title="test")
        await self.store.add_job(job)

        request = CreateJobRequest(
            type="image",
            prompt="normal image edit",
            count=1,
            flow_agent_enabled=False,
            reference_image_paths=[str(source)],
        )
        fake_client = SimpleNamespace()

        with patch.object(
            self.service,
            "_upload_project_image_robust",
            AsyncMock(side_effect=RuntimeError("Failed to upload")),
        ):
            with self.assertRaises(RuntimeError):
                await self.service._resolve_image_reference_media(fake_client, job.id, request)


if __name__ == "__main__":
    unittest.main(verbosity=2)
