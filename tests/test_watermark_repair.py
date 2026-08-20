from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from flow_web import watermark_repair
from flow_web.schemas import JobArtifact, JobRecord
from flow_web.service import FlowWebService, RemoveLogoNoWatermarkError
from flow_web.store import StateStore

from tests.test_flow_web_smoke import TempAppPathsMixin


def _cv2():
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
    except Exception:  # pragma: no cover - only on a machine without the stack
        return None
    return cv2


HAS_STACK = _cv2() is not None
SKIP_REASON = "opencv/numpy chưa được cài trên máy này"


def _synthetic(background_value: int = 150, size: int = 1024, strength: float = 1.0):
    """A flat picture with the shipped Gemini overlay blended onto it.

    Building the input with the exact model the repair inverts is the only way
    to check the arithmetic without shipping a client photo into the repo.
    """
    import numpy as np

    kit = watermark_repair._kit_or_none()
    image = np.full((size, size, 3), background_value, dtype="float32")
    alpha = watermark_repair._template(kit, strength, *watermark_repair.NEUTRAL_PROFILE)
    scale = size / watermark_repair.REFERENCE_SIZE
    x0 = int(round(watermark_repair.WINDOW_X * scale))
    y0 = int(round(watermark_repair.WINDOW_Y * scale))
    if scale != 1.0:
        size_x = int(round(kit.width * scale))
        size_y = int(round(kit.height * scale))
        alpha = kit.cv2.resize(alpha, (size_x, size_y), interpolation=kit.cv2.INTER_LINEAR)
    height, width = alpha.shape
    patch = image[y0:y0 + height, x0:x0 + width]
    image[y0:y0 + height, x0:x0 + width] = patch * (1 - alpha[:, :, None]) + 255.0 * alpha[:, :, None]
    return np.clip(image, 0, 255).astype("uint8")


def _encode(image) -> bytes:
    import cv2

    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def _decode(data: bytes):
    import cv2
    import numpy as np

    return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)


@unittest.skipUnless(HAS_STACK, SKIP_REASON)
class WatermarkRepairTest(unittest.TestCase):
    def test_removes_a_synthetic_watermark(self) -> None:
        import numpy as np

        watermarked = _synthetic()
        result = watermark_repair.repair_image_bytes(_encode(watermarked))
        self.assertTrue(result.repaired, result.reason)
        self.assertGreater(result.strength, watermark_repair.MIN_STRENGTH)

        repaired = _decode(result.image)
        kit = watermark_repair._kit_or_none()
        window = repaired[
            watermark_repair.WINDOW_Y:watermark_repair.WINDOW_Y + kit.height,
            watermark_repair.WINDOW_X:watermark_repair.WINDOW_X + kit.width,
        ].astype("float32")
        # The background was flat at 150, so a correct inverse blend puts it
        # back; anything above a couple of levels is a leftover mark.
        self.assertLess(float(np.abs(window - 150.0).max()), 4.0)

    def test_leaves_a_clean_photo_alone(self) -> None:
        import numpy as np

        rng = np.random.default_rng(7)
        photo = rng.integers(90, 190, size=(1024, 1024, 3), dtype=np.uint8)
        result = watermark_repair.repair_image_bytes(_encode(photo))
        self.assertFalse(result.repaired)
        self.assertIsNone(result.image)
        self.assertLess(result.strength, watermark_repair.MIN_STRENGTH)

    def test_measured_strength_tracks_the_overlay(self) -> None:
        kit = watermark_repair._kit_or_none()
        for expected in (0.6, 1.0, 1.4):
            with self.subTest(expected=expected):
                measured = watermark_repair.measure_strength(kit, _synthetic(strength=expected))
                self.assertAlmostEqual(measured, expected, delta=0.15)

    def test_handles_a_2048px_export(self) -> None:
        result = watermark_repair.repair_image_bytes(_encode(_synthetic(size=2048)))
        self.assertTrue(result.repaired, result.reason)
        repaired = _decode(result.image)
        # The photo must come back at its own resolution, never resampled to the
        # reference size the template happens to be measured in.
        self.assertEqual(repaired.shape[:2], (2048, 2048))

    def test_rejects_a_non_square_image(self) -> None:
        import numpy as np

        wide = np.full((600, 1024, 3), 120, dtype=np.uint8)
        result = watermark_repair.repair_image_bytes(_encode(wide))
        self.assertFalse(result.repaired)
        self.assertIn("vuông", result.reason)

    def test_rejects_an_unsupported_export_size(self) -> None:
        import numpy as np

        small = np.full((512, 512, 3), 120, dtype=np.uint8)
        result = watermark_repair.repair_image_bytes(_encode(small))
        self.assertFalse(result.repaired)
        self.assertIn("dải export", result.reason)

    def test_reports_a_reason_for_undecodable_input(self) -> None:
        result = watermark_repair.repair_image_bytes(b"not an image")
        self.assertFalse(result.repaired)
        self.assertIn("giải mã", result.reason)

    def test_reports_a_reason_for_empty_input(self) -> None:
        result = watermark_repair.repair_image_bytes(b"")
        self.assertFalse(result.repaired)
        self.assertIn("Không có dữ liệu ảnh", result.reason)



@unittest.skipUnless(HAS_STACK, SKIP_REASON)
class RetryWatermarkServiceTest(TempAppPathsMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.start_temp_paths()
        self.store = StateStore()
        self.service = FlowWebService(self.store)

    def _job_with_flagged_image(self) -> JobRecord:
        original = self.downloads_dir / "demo.png"
        original.write_bytes(_encode(_synthetic()))
        # removelogo's metadata-only outcome: a -clean.png holding the same
        # pixels as the download it came from.
        flagged = self.downloads_dir / "demo-clean.png"
        flagged.write_bytes(original.read_bytes())
        # A genuinely clean picture, so the "leave clean images alone" case is
        # tested against a file that really has no mark on it.
        spotless = self.downloads_dir / "spotless.png"
        spotless.write_bytes(_encode(_synthetic(strength=0.0)))
        job = JobRecord(
            id="job-retry",
            type="image",
            status="completed",
            artifacts=[
                JobArtifact(
                    local_path=str(flagged),
                    mime_type="image/png",
                    watermark_status="metadata_only",
                    watermark_error="Bộ xử lý chỉ gỡ được metadata AI.",
                ),
                JobArtifact(local_path=str(spotless), mime_type="image/png", watermark_status="cleaned"),
            ],
        )
        return asyncio.run(self.store.add_job(job))

    def test_retry_cleans_a_flagged_image(self) -> None:
        self._job_with_flagged_image()

        summary = asyncio.run(self.service.retry_job_watermarks("job-retry"))

        self.assertEqual(summary["retried"], 1)
        self.assertEqual(summary["cleaned"], 1)
        self.assertEqual(summary["remaining"], 0)
        job = self.store.get_job("job-retry")
        self.assertEqual(job.artifacts[0].watermark_status, "cleaned")
        self.assertEqual(job.artifacts[0].watermark_error, "")
        self.assertIn("bộ vá cục bộ", job.artifacts[0].watermark_repair)
        # The already-clean image must not be touched by a retry.
        self.assertEqual(job.artifacts[1].watermark_status, "cleaned")

    def test_retry_believes_the_file_not_the_cleaned_label(self) -> None:
        # An earlier run marked this image cleaned without measuring what came
        # back, and it shipped to the client still carrying the mark. The retry
        # has to catch that, or "đã sạch" means nothing.
        marked = self.downloads_dir / "mislabelled.png"
        marked.write_bytes(_encode(_synthetic()))
        asyncio.run(
            self.store.add_job(
                JobRecord(
                    id="job-mislabelled",
                    type="image",
                    status="completed",
                    artifacts=[
                        JobArtifact(local_path=str(marked), mime_type="image/png", watermark_status="cleaned")
                    ],
                )
            )
        )

        summary = asyncio.run(self.service.retry_job_watermarks("job-mislabelled"))

        self.assertEqual(1, summary["retried"])
        self.assertEqual(1, summary["cleaned"])
        job = self.store.get_job("job-mislabelled")
        data = Path(job.artifacts[0].local_path).read_bytes()
        self.assertLess(watermark_repair.measure_image_bytes(data), watermark_repair.MIN_STRENGTH)

    def test_the_upload_door_cleans_an_image_the_2k_pass_re_marked(self) -> None:
        # The 2K upscale sends the picture back through Google, which stamps the
        # sparkle onto the result. A file cleaned on disk can therefore arrive at
        # the ERP card marked again, so the bytes are measured at the door.
        asyncio.run(
            self.store.add_job(JobRecord(id="job-door", type="image", status="completed", artifacts=[]))
        )
        marked = _encode(_synthetic())

        data, mime = asyncio.run(self.service._erp_unmarked_bytes("job-door", 0, marked, "image/png"))

        self.assertEqual("image/png", mime)
        self.assertLess(watermark_repair.measure_image_bytes(data), watermark_repair.MIN_STRENGTH)

    def test_the_upload_door_sends_the_2k_bytes_through_removelogo(self) -> None:
        # The strong cleaner used to see only the pre-upscale file, so the
        # sparkle Google stamps back on during the 2K pass was left to the
        # local patcher alone - and stayed visible on the pictures that
        # actually reached the card.
        asyncio.run(
            self.store.add_job(JobRecord(id="job-door-3", type="image", status="completed", artifacts=[]))
        )
        marked = _encode(_synthetic())
        cleaned = _encode(_synthetic(strength=0.0))
        seen: list[bytes] = []

        def _process(_base_url, image_bytes, _mime, _name):
            seen.append(image_bytes)
            return cleaned

        with patch.object(self.service, "_removelogo_enabled", return_value=True), patch.object(
            self.service, "_removelogo_base_url", return_value="http://127.0.0.1:8788"
        ), patch.object(self.service, "_removelogo_process_bytes", side_effect=_process):
            data, mime = asyncio.run(self.service._erp_unmarked_bytes("job-door-3", 0, marked, "image/png"))

        self.assertEqual([marked], seen)
        self.assertEqual(cleaned, data)
        self.assertEqual("image/png", mime)
        job = self.store.get_job("job-door-3")
        self.assertIn("removelogo", job.logs[-1].message)

    def test_the_upload_door_cleans_what_the_local_detector_cannot_see(self) -> None:
        # The local reading used to decide whether removelogo got to look at
        # the file at all. On wood grain and linen it comes back around 0.1 -
        # under the threshold - while the sparkle sits plainly visible in the
        # corner, so a whole card's worth of pictures shipped marked.
        asyncio.run(
            self.store.add_job(JobRecord(id="job-door-5", type="image", status="completed", artifacts=[]))
        )
        faint = _encode(_synthetic(strength=0.05))
        self.assertLess(watermark_repair.measure_image_bytes(faint), watermark_repair.MIN_STRENGTH)
        cleaned = _encode(_synthetic(strength=0.0))
        seen: list[bytes] = []

        def _process(_base_url, image_bytes, _mime, _name):
            seen.append(image_bytes)
            return cleaned

        with patch.object(self.service, "_removelogo_enabled", return_value=True), patch.object(
            self.service, "_removelogo_base_url", return_value="http://127.0.0.1:8788"
        ), patch.object(self.service, "_removelogo_process_bytes", side_effect=_process):
            data, _mime = asyncio.run(self.service._erp_unmarked_bytes("job-door-5", 0, faint, "image/png"))

        self.assertEqual([faint], seen)
        self.assertEqual(cleaned, data)

    def test_the_upload_door_falls_back_when_removelogo_cannot_help(self) -> None:
        # removelogo answers 422 on linen and flat walls it cannot see the mark
        # on. Our own measurement already said the mark is there, so the local
        # patcher still gets its turn instead of the file going out marked.
        asyncio.run(
            self.store.add_job(JobRecord(id="job-door-4", type="image", status="completed", artifacts=[]))
        )
        marked = _encode(_synthetic())

        with patch.object(self.service, "_removelogo_enabled", return_value=True), patch.object(
            self.service, "_removelogo_base_url", return_value="http://127.0.0.1:8788"
        ), patch.object(
            self.service,
            "_removelogo_process_bytes",
            side_effect=RemoveLogoNoWatermarkError("no watermark"),
        ):
            data, _mime = asyncio.run(self.service._erp_unmarked_bytes("job-door-4", 0, marked, "image/png"))

        self.assertLess(watermark_repair.measure_image_bytes(data), watermark_repair.MIN_STRENGTH)

    def test_the_upload_door_leaves_a_clean_image_byte_for_byte(self) -> None:
        asyncio.run(
            self.store.add_job(JobRecord(id="job-door-2", type="image", status="completed", artifacts=[]))
        )
        clean = _encode(_synthetic(strength=0.0))

        data, mime = asyncio.run(self.service._erp_unmarked_bytes("job-door-2", 0, clean, "image/jpeg"))

        self.assertEqual(clean, data)
        self.assertEqual("image/jpeg", mime)

    def test_retry_is_a_no_op_when_nothing_is_flagged(self) -> None:
        job = JobRecord(
            id="job-clean",
            type="image",
            status="completed",
            artifacts=[JobArtifact(local_path="", watermark_status="cleaned")],
        )
        asyncio.run(self.store.add_job(job))

        summary = asyncio.run(self.service.retry_job_watermarks("job-clean"))

        self.assertEqual(summary, {"job_id": "job-clean", "retried": 0, "cleaned": 0, "remaining": 0})

    def test_retry_keeps_the_flag_when_no_watermark_is_measured(self) -> None:
        import numpy as np

        rng = np.random.default_rng(3)
        path = self.downloads_dir / "noise.png"
        path.write_bytes(_encode(rng.integers(90, 190, size=(1024, 1024, 3), dtype=np.uint8)))
        asyncio.run(
            self.store.add_job(
                JobRecord(
                    id="job-noise",
                    type="image",
                    status="completed",
                    artifacts=[JobArtifact(local_path=str(path), watermark_status="metadata_only")],
                )
            )
        )

        summary = asyncio.run(self.service.retry_job_watermarks("job-noise"))

        self.assertEqual(summary["cleaned"], 0)
        self.assertEqual(summary["remaining"], 1)
        job = self.store.get_job("job-noise")
        self.assertEqual(job.artifacts[0].watermark_status, "metadata_only")
        self.assertIn("Không đo được", job.artifacts[0].watermark_error)

    def test_retry_rejects_an_unknown_job(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(self.service.retry_job_watermarks("missing"))
        self.assertEqual(caught.exception.status_code, 404)
if __name__ == "__main__":
    unittest.main()
