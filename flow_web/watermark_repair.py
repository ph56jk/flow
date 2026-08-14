"""Local fallback repair for the Gemini sparkle removelogo leaves behind.

removelogo is the primary cleaner. On roughly a third of Flow exports its
template detector does not fire - the sparkle sits on linen, knitted fabric, or
a flat wall where the template score never clears the threshold - and it answers
with a metadata-only file whose visible mark is untouched. Lowering that
threshold was tried and rejected: it starts inpainting clean client product
photography.

This module attacks the same images from the other side. The Gemini mark is a
constant white alpha overlay at a fixed anchor::

    observed = (1 - alpha) * background + alpha * 255

so it is removable exactly by inverse blending once ``alpha`` is known. The
shipped template was estimated from images removelogo did repair, and only its
strength and edge profile are fitted per image. That turns detection into a
measurement of overlay strength rather than a shape score, which separates
cleanly: Flow exports carrying the mark fit 0.86-1.62, while ERP product photos
that never went near Gemini fit 0.04-0.06. ``MIN_STRENGTH`` sits far above the
latter, so a clean photo is returned untouched rather than smeared.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple

TEMPLATE_PATH = Path(__file__).with_name("data") / "gemini_watermark_alpha.npy"

# Working resolution the template was measured in, and the top-left corner of
# the 100x100 window it covers.
REFERENCE_SIZE = 1024
WINDOW_X = 875
WINDOW_Y = 875
# Ring of background kept around the window when a local background has to be
# estimated. Large enough that the median filter sees real background.
MARGIN = 60

# Fitted strength below this is treated as "no Gemini watermark here". Controls
# measured at 0.04-0.06, real marks at 0.86 and up, so there is a wide gap.
MIN_STRENGTH = 0.25
# A neighbourhood flatter than this (median high-frequency energy, grey levels)
# is smooth enough that the low-frequency flattening pass cannot destroy detail.
SMOOTH_TEXTURE = 1.2
# Square exports only, within the export sizes Flow and Trello actually produce.
MIN_SOURCE_SCALE = 0.75
MAX_SOURCE_SCALE = 2.25


@dataclass
class RepairResult:
    """Outcome of one repair attempt. ``image`` is None unless repaired."""

    repaired: bool
    strength: float
    reason: str
    image: bytes | None = None


class _Kit:
    """Lazily built numpy/cv2 handles plus everything derived from the template.

    Kept out of module import so flow_web still starts when the optional image
    stack is missing; the caller then simply gets ``repaired=False``.
    """

    def __init__(self, cv2: Any, numpy: Any) -> None:
        self.cv2 = cv2
        self.np = numpy
        alpha = numpy.load(TEMPLATE_PATH).astype("float32")
        self.height, self.width = alpha.shape
        self.peak = float(alpha.max())
        shape = alpha / max(self.peak, 1e-6)
        self.shape = shape
        support = shape > 0.08
        self.support = support
        # Zero-mean sparkle profile: correlating a residual against it answers
        # "is there still a bright four-point mark here", sign included.
        unit = numpy.where(support, shape - shape[support].mean(), 0.0)
        self.unit = unit / (numpy.linalg.norm(unit) + 1e-6)
        # The mark plus a couple of pixels of rim - the only area any pass here
        # is allowed to touch.
        weight = cv2.dilate(support.astype("float32"), numpy.ones((9, 9), "uint8"))
        self.weight = numpy.clip(cv2.GaussianBlur(weight, (0, 0), 2.0), 0, 1)
        self.ring = cv2.dilate(support.astype("uint8"), numpy.ones((25, 25), "uint8")) - cv2.dilate(
            support.astype("uint8"), numpy.ones((11, 11), "uint8")
        )


_kit: _Kit | None = None
_kit_failed = False


def _kit_or_none() -> _Kit | None:
    global _kit, _kit_failed
    if _kit is not None or _kit_failed:
        return _kit
    try:
        import cv2
        import numpy
    except Exception:
        _kit_failed = True
        return None
    try:
        _kit = _Kit(cv2, numpy)
    except Exception:
        _kit_failed = True
        return None
    return _kit


def available() -> bool:
    """True when the repair can run at all (image stack + template present)."""
    return _kit_or_none() is not None


def _template(kit: _Kit, strength: float, hardness: float, centre: float, sigma: float):
    """The alpha map for one candidate fit, in the 1024px reference frame.

    ``hardness`` steepens the rim around ``centre`` without moving the interior
    or the surroundings. The shipped template is a median over many marks, so
    its rim is softer than any single one; unblending with a rim that is too
    soft is exactly what leaves a bright outline tracing the star.
    """
    shape = kit.np.clip((kit.shape - centre) * hardness + centre, 0, 1)
    if sigma > 0.05:
        shape = kit.cv2.GaussianBlur(shape, (0, 0), sigma)
    return kit.np.clip(shape * kit.peak * strength, 0.0, 0.97)


def _window(kit: _Kit, image, alpha_map):
    """Coordinates and a matching alpha map for ``image``'s own resolution."""
    size = image.shape[0]
    scale = size / REFERENCE_SIZE
    x0 = int(round(WINDOW_X * scale))
    y0 = int(round(WINDOW_Y * scale))
    width = max(1, int(round(kit.width * scale)))
    height = max(1, int(round(kit.height * scale)))
    x0 = min(x0, size - width)
    y0 = min(y0, size - height)
    if (width, height) != (kit.width, kit.height):
        alpha_map = kit.cv2.resize(alpha_map, (width, height), interpolation=kit.cv2.INTER_LINEAR)
    return x0, y0, width, height, alpha_map


def _unblend(kit: _Kit, image, alpha_map):
    """Invert ``obs = (1 - a) * bg + a * 255`` over the mark."""
    x0, y0, width, height, alpha_map = _window(kit, image, alpha_map)
    out = image.astype("float32").copy()
    patch = out[y0:y0 + height, x0:x0 + width]
    alpha = alpha_map[:, :, None]
    out[y0:y0 + height, x0:x0 + width] = kit.np.clip((patch - alpha * 255.0) / (1.0 - alpha), 0, 255)
    return out


def _sparkle_score(kit: _Kit, image) -> float:
    """Correlation of the leftover detail with the sparkle profile.

    The background is estimated with a wide *median*, not a blur, so a hard
    scene edge crossing the mark does not masquerade as watermark energy.
    """
    region = kit.np.clip(image, 0, 255).astype("uint8")[
        WINDOW_Y - MARGIN:WINDOW_Y + kit.height + MARGIN,
        WINDOW_X - MARGIN:WINDOW_X + kit.width + MARGIN,
    ]
    gray = kit.cv2.cvtColor(region, kit.cv2.COLOR_BGR2GRAY)
    residual = gray.astype("float32") - kit.cv2.medianBlur(gray, 81).astype("float32")
    inner = residual[MARGIN:MARGIN + kit.height, MARGIN:MARGIN + kit.width]
    return float((inner * kit.unit).sum())


def _low_frequency_energy(kit: _Kit, image) -> float:
    """Smooth energy still sitting inside the mark; texture is blurred away."""
    region = kit.np.clip(image, 0, 255).astype("uint8")[
        WINDOW_Y - MARGIN:WINDOW_Y + kit.height + MARGIN,
        WINDOW_X - MARGIN:WINDOW_X + kit.width + MARGIN,
    ]
    gray = kit.cv2.cvtColor(region, kit.cv2.COLOR_BGR2GRAY).astype("float32")
    background = kit.cv2.cvtColor(kit.cv2.medianBlur(region, 61), kit.cv2.COLOR_BGR2GRAY).astype("float32")
    smooth = kit.cv2.GaussianBlur(gray - background, (0, 0), 2.5)
    inner = smooth[MARGIN:MARGIN + kit.height, MARGIN:MARGIN + kit.width]
    return float((kit.np.abs(inner) * kit.weight).sum())


def measure_strength(kit: _Kit, work) -> float:
    """Overlay strength, as a multiple of the shipped template.

    Bisection on the sign of the sparkle score: over-correcting flips the
    correlation negative, so the crossing point is the strength that removes it.
    """
    if _sparkle_score(kit, work.astype("float32")) <= 0:
        return 0.0
    low, high = 0.0, 2.5
    for _ in range(24):
        middle = (low + high) / 2
        if _sparkle_score(kit, _unblend(kit, work, _template(kit, middle, *NEUTRAL_PROFILE))) > 0:
            low = middle
        else:
            high = middle
    return (low + high) / 2


# Hardness 1.0 / centre 0.5 / sigma 0.0 is the shipped template unchanged - the
# shape the strength measurement is defined against.
NEUTRAL_PROFILE = (1.0, 0.5, 0.0)


def _best_profile(kit: _Kit, work, strength: float) -> Tuple[float, float, float, float]:
    """Refine strength and fit the rim profile of this particular mark.

    Scored by how much smooth energy survives inside the mark, which is what a
    reviewer actually sees.
    """
    best: Tuple[float, Tuple[float, float, float, float]] | None = None
    for hardness in (1.0, 1.6, 2.5, 4.0):
        for centre in (0.35, 0.5):
            for sigma in (0.0, 0.8, 1.6):
                for factor in (0.7, 0.8, 0.9, 1.0, 1.1, 1.25):
                    candidate = (strength * factor, hardness, centre, sigma)
                    energy = _low_frequency_energy(kit, _unblend(kit, work, _template(kit, *candidate)))
                    if best is None or energy < best[0]:
                        best = (energy, candidate)
    assert best is not None
    return best[1]


def _neighbour_texture(kit: _Kit, work) -> float:
    """High-frequency energy of the ring around the mark, in grey levels.

    Median rather than mean: one hard scene edge crossing the ring must not make
    a flat wall look like linen.
    """
    region = kit.np.clip(work, 0, 255).astype("uint8")[
        WINDOW_Y:WINDOW_Y + kit.height, WINDOW_X:WINDOW_X + kit.width
    ]
    gray = kit.cv2.cvtColor(region, kit.cv2.COLOR_BGR2GRAY).astype("float32")
    detail = gray - kit.cv2.GaussianBlur(gray, (0, 0), 2.0)
    return float(kit.np.median(kit.np.abs(detail[kit.ring > 0])))


def _flatten(kit: _Kit, image, alpha_map):
    """Subtract the smooth error the template could not match.

    Only run on a provably flat neighbourhood, where the leftover is by
    definition low frequency. The guide is a median filter so a hard edge - a
    table line crossing the mark - survives it.
    """
    x0, y0, width, height, _ = _window(kit, image, alpha_map)
    guide = kit.cv2.medianBlur(kit.np.clip(image, 0, 255).astype("uint8"), 41).astype("float32")
    low = kit.cv2.GaussianBlur(image.astype("float32") - guide, (0, 0), 3.0)
    weight = kit.weight
    if (width, height) != (kit.width, kit.height):
        weight = kit.cv2.resize(weight, (width, height), interpolation=kit.cv2.INTER_LINEAR)
    out = image.astype("float32").copy()
    out[y0:y0 + height, x0:x0 + width] -= weight[:, :, None] * low[y0:y0 + height, x0:x0 + width]
    return kit.np.clip(out, 0, 255)


def _dering(kit: _Kit, image, alpha_map):
    """Damp JPEG ringing along the mark's own rim.

    Flow exports arrive as JPEG, so the watermark's high-contrast edge carries
    ringing, and dividing by (1 - alpha) amplifies it into a visible crinkle.
    It lives only where alpha changes fast, so a bilateral pass weighted by the
    alpha gradient clears it without touching the interior or the surroundings.
    """
    x0, y0, width, height, alpha_map = _window(kit, image, alpha_map)
    gradient = kit.np.abs(kit.cv2.Sobel(alpha_map, kit.cv2.CV_32F, 1, 0, ksize=3)) + kit.np.abs(
        kit.cv2.Sobel(alpha_map, kit.cv2.CV_32F, 0, 1, ksize=3)
    )
    band = kit.cv2.GaussianBlur(gradient, (0, 0), 2.0)
    peak = float(band.max())
    if peak <= 1e-6:
        return image
    band = kit.np.clip(band / peak, 0, 1)[:, :, None]
    patch = kit.np.clip(image[y0:y0 + height, x0:x0 + width], 0, 255).astype("uint8")
    smoothed = kit.cv2.bilateralFilter(patch, 9, 30, 9).astype("float32")
    out = image.astype("float32").copy()
    out[y0:y0 + height, x0:x0 + width] = patch.astype("float32") * (1 - band) + smoothed * band
    return kit.np.clip(out, 0, 255)


def repair_image_bytes(data: bytes) -> RepairResult:
    """Remove the Gemini sparkle from one encoded image.

    Returns ``repaired=False`` with a reason for anything it will not touch -
    an unsupported export, a missing image stack, or a picture whose measured
    overlay strength says there is no watermark there.
    """
    kit = _kit_or_none()
    if kit is None:
        return RepairResult(False, 0.0, "Máy chưa cài opencv/numpy nên bỏ qua bước vá watermark cục bộ.")
    if not data:
        return RepairResult(False, 0.0, "Không có dữ liệu ảnh để vá watermark.")

    array = kit.np.frombuffer(data, dtype=kit.np.uint8)
    image = kit.cv2.imdecode(array, kit.cv2.IMREAD_COLOR)
    if image is None:
        return RepairResult(False, 0.0, "Không giải mã được ảnh để vá watermark.")

    height, width = image.shape[:2]
    if abs(width - height) > max(width, height) * 0.02:
        return RepairResult(False, 0.0, "Ảnh không vuông nên không thuộc dạng export Gemini đã kiểm chứng.")
    source_scale = min(width, height) / REFERENCE_SIZE
    if not MIN_SOURCE_SCALE <= source_scale <= MAX_SOURCE_SCALE:
        return RepairResult(False, 0.0, "Kích thước ảnh nằm ngoài dải export Gemini đã kiểm chứng.")

    work = image
    if (width, height) != (REFERENCE_SIZE, REFERENCE_SIZE):
        work = kit.cv2.resize(image, (REFERENCE_SIZE, REFERENCE_SIZE), interpolation=kit.cv2.INTER_AREA)

    strength = measure_strength(kit, work)
    if strength < MIN_STRENGTH:
        return RepairResult(
            False,
            strength,
            f"Không đo được watermark Gemini (cường độ {strength:.2f} < {MIN_STRENGTH:.2f}).",
        )

    profile = _best_profile(kit, work, strength)
    alpha_map = _template(kit, *profile)
    fixed = _unblend(kit, image, alpha_map)
    if _neighbour_texture(kit, work) < SMOOTH_TEXTURE:
        fixed = _flatten(kit, fixed, alpha_map)
    fixed = _dering(kit, fixed, alpha_map)

    ok, encoded = kit.cv2.imencode(".png", kit.np.clip(fixed, 0, 255).astype("uint8"))
    if not ok:
        return RepairResult(False, strength, "Không mã hóa được ảnh sau khi vá watermark.")
    return RepairResult(
        True,
        profile[0],
        f"Đã vá watermark Gemini bằng bộ vá cục bộ (cường độ {profile[0]:.2f}).",
        encoded.tobytes(),
    )
