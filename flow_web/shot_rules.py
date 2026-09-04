from __future__ import annotations

from typing import Any, Dict, Tuple


ShotTuple = Tuple[str, str, str]


# Generated from C:/Users/HAVI GROUP/Downloads/HAVI_Shot_Types_All_Products ok.xlsx.
# Keep only active workbook rows; rows marked '(inactive)' are intentionally omitted.
PRODUCT_SHOT_RULE_PRIORITY: Tuple[str, ...] = ('ring_bearer_pillow',
 'wedding_pillowcase',
 'tooth_fairy_pillow',
 'christmas_pillowcase',
 'halloween_pillow',
 'baby_pillowcase',
 'linen_pillowcase',
 'hoops_with_photos',
 'wedding_hoop',
 'bride_handkerchief',
 'halloween_notebook',
 'vows_book',
 'baby_christmas_album',
 'christmas_album',
 'baby_album',
 'album',
 'notebook',
 'guest_book',
 'bouquet_ribbon',
 'christmas_sash',
 'family_halloween_sash',
 'halloween_wreath_sash',
 'wreath_sash',
 'hair_bow',
 'passport_cover',
 'pc_stocks',
 'pn_ornament',
 'ornament_round',
 'jewelry_box',
 'napkin_set',
 'advent_calendar',
 'halloween_bag',
 'drawstring_bag',
 'christmas_banner',
 'halloween_banner',
 'banner',
 'birthday_hat',
 'crown',
 'christmas_fabric_cross',
 'fabric_cross',
 'christmas_dress_baby',
 'halloween_dress_baby',
 'dress_baby',
 'plush')

_TOOTH_FAIRY_PILLOW_LOCK = (
    "Keep the original product design 100% unchanged in every image: same tooth shape, same cream linen fabric "
    "texture, same soft stuffed form, same white ribbon, same hand-embroidered name/text, same floral or decorative "
    "motifs, same thread colors, same stitch placement, same embroidery scale, and same handmade details. Do not "
    "redesign the pillow, do not change the embroidered text, do not add or remove embroidery, do not change the "
    "fabric color, and do not cover the embroidery."
)

_TOOTH_FAIRY_PILLOW_STYLE = (
    "Overall style: bright clean white natural daylight, soft shadows, airy premium nursery aesthetic, realistic "
    "handmade product photography, soft neutral colors, cozy baby keepsake mood, high-detail linen texture, visible "
    "raised hand embroidery stitches, elegant Etsy listing quality, no harsh yellow light, no dark background, no "
    "clutter, no CGI look, no watermark, no logo, no duplicate pillows in one image, no random text on the product."
)


def _tooth_fairy_pillow_brief(scene: str) -> str:
    return (
        "Use the uploaded product reference image as the exact product. Create one separate square 1:1 high-end "
        f"handmade Etsy product photo: {scene} {_TOOTH_FAIRY_PILLOW_LOCK} {_TOOTH_FAIRY_PILLOW_STYLE}"
    )


_HALLOWEEN_PILLOW_LOCK = (
    "Keep the original handmade Halloween baby pillow or pillowcase design 100% unchanged: same pillow shape, "
    "same soft stuffed volume or pillowcase edges, same fabric material, same base fabric color or gingham/checkered "
    "fabric, same embroidery motif, same wool/yarn embroidery thread colors, same raised hooked wool-stitch texture, "
    "same embroidery placement, same embroidery scale, same seams, proportions, handmade wrinkles, and nursery pillow "
    "identity. Do not redesign, redraw, simplify, move, resize, or cover the embroidery; do not change the fabric or "
    "turn the product into a blanket, plush toy, hoop, banner, bag, shirt, costume, generic Halloween prop, or a "
    "different pillow design."
)

_HALLOWEEN_PILLOW_STYLE = (
    "Overall style: realistic bright airy premium Etsy handmade product photography, clean white balanced daylight, "
    "sunny nursery or home feeling, soft tasteful Halloween decor, visible fabric texture, visible raised wool "
    "embroidery stitches, natural soft shadows, uncluttered composition, no harsh yellow light, no dark spooky "
    "lighting, no studio glare, no text overlay, no logo, no watermark."
)


_CHRISTMAS_PILLOWCASE_LOCK = (
    "Keep the original handmade Christmas pillow or pillowcase 100% unchanged: same pillow silhouette, dimensions, "
    "soft volume or flat pillowcase construction shown by the source, fabric material, exact base color, seams, edge "
    "finish, embroidery motif, readable embroidered name when present, embroidery placement, embroidery scale, wool "
    "thread colors, raised hooked or punch-needle stitch texture, proportions, and premium handmade identity. If the "
    "source has a personalized embroidered name, coordinated multi-product shots may use different plausible names "
    "while keeping the exact source lettering position, scale, font style, and stitch method; if the source has no name, "
    "never add one. Pompom lock: if the source pillow has pompoms, preserve exactly four corner pompoms on each pillow, "
    "all four pompoms on one pillow must be the same color, while separate colorway pillows may use different pompom "
    "colors; if the source has no pompoms, never add any pompoms. Never redesign, redraw, simplify, move, resize, "
    "recolor, replace, or cover the embroidery; never change the physical construction or turn the product into a "
    "blanket, plush toy, hoop, banner, bag, garment, printed cushion, machine-embroidered item, or another product."
)

_CHRISTMAS_PILLOWCASE_STYLE = (
    "Overall style for every output: realistic premium Etsy handmade Christmas pillow photography, true square 1:1 "
    "composition, bright clear airy white-balanced natural daylight, soft clean shadows, beautiful refined Christmas "
    "decor, spacious uncluttered styling, shallow depth of field where useful, sharp pillow focus, visible fabric weave, "
    "and unmistakable raised wool hand-embroidery with individual loops, fibers, and stitch direction. Keep every scene "
    "bright and airy with no yellow, amber, dark, tungsten, or harsh studio cast. Avoid distracting props, plastic or "
    "mass-produced fabric, printed or machine-flat embroidery, malformed bodies or hands, extra fingers, unrealistic "
    "needle placement, blurry stitching, spelling errors, missing source lettering, AI defects, text overlays, logos, "
    "and watermarks."
)


def _christmas_pillowcase_brief(scene: str) -> str:
    return (
        "Use the uploaded Christmas Pillowcase reference image as the exact product. Create one separate square 1:1 "
        f"high-end handmade Etsy Christmas product photo: {scene} {_CHRISTMAS_PILLOWCASE_LOCK} "
        f"{_CHRISTMAS_PILLOWCASE_STYLE}"
    )


def _halloween_pillow_brief(scene: str) -> str:
    return (
        "Use the uploaded Halloween pillow reference image as the exact product. Create one separate square 1:1 "
        f"high-end handmade Etsy product photo: {scene} {_HALLOWEEN_PILLOW_LOCK} {_HALLOWEEN_PILLOW_STYLE}"
    )


_HALLOWEEN_BANNER_LOCK = (
    "Keep the original handmade Halloween linen fabric banner 100% unchanged: same small wall-banner silhouette, "
    "same fabric cut and lower edge shape, same wooden hanging rod, same hanging cord or tie construction, same linen "
    "material and exact base color, same seams, embroidery motif, readable personalized name or lettering when present, "
    "embroidery placement, embroidery scale, thread colors, raised hand-stitch texture, linen weave, natural wrinkles, "
    "proportions, and premium handmade identity. The source image is authoritative for every design detail. Never "
    "redesign, redraw, simplify, move, resize, recolor, replace, or cover the embroidery; never change the rod, cord, "
    "fabric, product shape, or physical construction; and never turn the banner into a bag, pillow, book, flag set, "
    "garment, framed print, machine-embroidered item, or another product. Keep the banner realistically small relative "
    "to doors, wardrobes, cribs, shelves, adults, and children."
)

_HALLOWEEN_BANNER_STYLE = (
    "Overall style for every output: realistic premium Etsy handmade Halloween product photography, true square 1:1 "
    "composition, bright clear airy white daylight, clean white-balanced natural light, soft natural shadows, tasteful "
    "refined Halloween decor, uncluttered styling, sharp product focus, visible linen weave, and unmistakable raised "
    "hand-embroidered thread with individual stitch direction and fibers. Never use yellow, amber, dark, tungsten, or "
    "harsh studio lighting; no nylon or plastic-looking fabric, machine-flat embroidery, distorted hands, extra fingers, "
    "AI defects, random text, logo, or watermark. The only permitted added wording is the exact gift-tag text "
    "\"Happy Halloween\" in image 10."
)


def _halloween_banner_brief(scene: str) -> str:
    return (
        "Use the uploaded Halloween Banner reference image as the exact product. Create one separate square 1:1 "
        f"high-end handmade Etsy Halloween product photo: {scene} {_HALLOWEEN_BANNER_LOCK} {_HALLOWEEN_BANNER_STYLE}"
    )


_CHRISTMAS_BANNER_LOCK = (
    "Keep the original handmade Christmas linen fabric banner 100% unchanged: same small wall-banner silhouette, "
    "same fabric cut and lower edge shape, same wooden hanging rod, same hanging cord or tie construction, same linen "
    "material and exact base color, same seams, embroidery motif, readable personalized name or lettering when present, "
    "embroidery placement, embroidery scale, thread colors, raised hand-stitch texture, linen weave, natural wrinkles, "
    "proportions, and premium handmade identity. The source image is authoritative for every design detail. Never "
    "redesign, redraw, simplify, move, resize, recolor, replace, or cover the embroidery; never change the rod, cord, "
    "fabric, product shape, or physical construction; and never turn the banner into a bag, pillow, book, flag set, "
    "garment, framed print, machine-embroidered item, or another product. Keep the banner realistically small relative "
    "to doors, wardrobes, cribs, mantles, shelves, adults, and children. If a personalized name is visible in the source, "
    "preserve it exactly in every single-product shot; only an explicitly planned colorway shot may use different "
    "plausible names in the exact same lettering position, scale, stitch style, and thread treatment."
)

_CHRISTMAS_BANNER_STYLE = (
    "Overall style for every output: realistic premium Etsy handmade Christmas product photography, true square 1:1 "
    "composition, bright clear airy white daylight, clean white-balanced natural light, soft natural shadows, tasteful "
    "refined Christmas and Noel decor, uncluttered styling, sharp product focus, visible linen weave, and unmistakable "
    "raised hand-embroidered thread with individual stitch direction and fibers. Never use yellow, amber, dark, tungsten, "
    "or harsh studio lighting; no Halloween props, pumpkins, ghosts, bats, spiders, nylon or plastic-looking fabric, "
    "machine-flat embroidery, distorted hands, extra fingers, AI defects, random text, logo, or watermark. The only "
    "permitted added wording is the explicitly requested decor wording Merry Christmas or Happy Christmas in the "
    "specified shots; never add text onto the product itself."
)


def _christmas_banner_brief(scene: str) -> str:
    return (
        "Use the uploaded Christmas Banner reference image as the exact product. Create one separate square 1:1 "
        f"high-end handmade Etsy Christmas product photo: {scene} {_CHRISTMAS_BANNER_LOCK} "
        f"{_CHRISTMAS_BANNER_STYLE}"
    )


_CHRISTMAS_SASH_LOCK = (
    "Keep the original handmade Christmas linen sash 100% unchanged in every image: same two-tail construction, "
    "same total length, tail width, pointed tail ends, knot size, linen material and source base color, weave, seams, "
    "edge finish, natural wrinkles, soft drape, embroidery motif, readable source lettering when present, embroidery "
    "placement and scale, thread colors, raised individual hand stitches, and premium handmade identity. Preserve the "
    "source left-tail and right-tail layout exactly; never swap the motif and lettering between tails. Never redesign, "
    "redraw, simplify, move, resize, recolor, replace, cover, print, or machine-embroider the source design. Never turn "
    "the sash into a bow, scarf, banner, stocking, ribbon roll, bag, pillow, or another product. In every tied scene, use "
    "one physically plausible soft simple knot, never a decorative bow, and keep both embroidered tails flat, untwisted, "
    "fully visible, correctly scaled, and unobstructed. Keep the sash realistically small and never enlarge or lengthen "
    "it relative to a door, wreath, book stack, basket, banister, adult, or child. Only the explicit color-comparison "
    "images 7 and 11 may vary the linen base color within subtle neutral source-compatible shades; even there, preserve "
    "the exact source embroidery design, lettering, thread colors, stitch placement, dimensions, and knot construction. "
    "When tied to a wreath, the sash must be tied at the bottom center "
    "at the 6 o'clock position, with the knot on the lower rim and both tails hanging completely below the wreath."
)

_CHRISTMAS_SASH_STYLE = (
    "Overall style for every output: one separate true square 1:1 realistic premium Etsy handmade Christmas product "
    "photograph, professional composition, crisp product focus, visible linen weave, and unmistakable raised hand-"
    "embroidery with individual thread fibers and stitch direction. Follow the requested lighting for each numbered "
    "scene exactly: bright scenes use clean balanced white daylight or even white studio light, while explicitly warm "
    "afternoon or evening scenes may use refined warm natural light without muddying the source fabric or thread colors. "
    "Keep Christmas props tasteful, secondary, and clear of both embroidered tails. No distorted fabric, twisted tails, "
    "hidden embroidery, printed or machine-flat stitches, malformed hands, extra fingers, AI defects, random text, text "
    "overlay, logo, or watermark. Only image 6 may be a four-panel 2x2 collage; every other image is one standalone scene."
)


def _christmas_sash_brief(scene: str) -> str:
    return (
        "Use the uploaded Christmas Sash reference image as the exact product. Create one separate square 1:1 high-end "
        f"handmade Etsy Christmas product photo: {scene} {_CHRISTMAS_SASH_LOCK} {_CHRISTMAS_SASH_STYLE}"
    )


_HALLOWEEN_DRESS_BABY_LOCK = (
    "Keep the original handmade baby or toddler dress 100% unchanged: same garment silhouette, neckline, bodice, "
    "sleeves or shoulder ruffles, gathers, skirt volume, hem, pleats, ties if present, seams, stitching, exact linen or "
    "cotton-linen fabric texture, source fabric color, embroidery motif, readable embroidered name when present, "
    "embroidery placement, embroidery scale, thread colors, raised hand-stitch texture, proportions, and premium "
    "handmade construction. In every back-facing view, preserve exactly two small natural wooden buttons on the back "
    "placket, vertically aligned and evenly spaced like the reference, with no third button, extra button row, snaps, "
    "zipper, or bow closure. Never redesign, redraw, simplify, move, enlarge, recolor, replace, or cover the source "
    "embroidery; never add a new motif or name; and never turn the dress into a shirt, romper, apron, costume, skirt, "
    "pillow, banner, or mass-produced garment. Colorway collection shots may change only the base fabric color while "
    "keeping the source dress form, construction, embroidery design, thread colors, and proportions identical."
)

_HALLOWEEN_DRESS_BABY_STYLE = (
    "Overall style for every output: realistic premium Etsy handmade Halloween children's clothing photography, true "
    "square 1:1 composition, bright clear airy white-balanced natural daylight, soft clean shadows, refined tasteful "
    "Halloween decorations, spacious minimalist styling, shallow depth of field where appropriate, sharp garment focus, "
    "visible natural linen or cotton-linen weave, and obvious raised hand-embroidery stitches. Keep every scene bright "
    "and airy with no yellow, amber, dark, tungsten, or harsh studio cast. Avoid clutter, distracting props, plastic or "
    "mass-produced fabric, distorted garment structure, malformed bodies or hands, extra fingers, unrealistic needle "
    "placement, blurry embroidery, spelling errors, missing source lettering, AI defects, text overlays, logos, and "
    "watermarks."
)


def _halloween_dress_baby_brief(scene: str) -> str:
    return (
        "Use the uploaded Halloween Dress Baby reference image as the exact product. Create one separate square 1:1 "
        f"high-end handmade Etsy Halloween product photo: {scene} {_HALLOWEEN_DRESS_BABY_LOCK} "
        f"{_HALLOWEEN_DRESS_BABY_STYLE}"
    )


_CHRISTMAS_DRESS_BABY_LOCK = (
    "Keep the original handmade baby or toddler dress 100% unchanged: same garment silhouette, neckline, bodice, "
    "collar if present, sleeves or shoulder ruffles, gathers, skirt volume, hem, pleats, ties if present, seams, "
    "stitching, exact linen or cotton-linen fabric texture, source fabric color, embroidery motif, readable embroidered "
    "name when present, embroidery placement, embroidery scale, thread colors, raised hand-stitch texture, proportions, "
    "and premium handmade construction. If the source dress has a collar, the collar must remain clean white in every "
    "colorway and must never be recolored to match the dress body; if the source has no collar, never invent one. In "
    "every back-facing view, preserve exactly two small natural wooden buttons on the back placket, vertically aligned "
    "and evenly spaced like the reference, with no third button, extra button row, snaps, zipper, or bow closure. Never "
    "redesign, redraw, simplify, move, enlarge, recolor, replace, or cover the source embroidery; never add a new motif "
    "or name; and never turn the dress into a shirt, romper, apron, costume, skirt, pillow, banner, or mass-produced "
    "garment. Colorway collection shots may change only the base dress-body fabric color while keeping the source dress "
    "form, white collar when present, construction, embroidery design, thread colors, and proportions identical."
)

_CHRISTMAS_DRESS_BABY_STYLE = (
    "Overall style for every output: realistic premium Etsy handmade Christmas children's clothing photography, true "
    "square 1:1 composition, bright clear airy white-balanced natural daylight, soft clean shadows, refined tasteful "
    "Christmas decorations, spacious minimalist styling, shallow depth of field where appropriate, sharp garment focus, "
    "visible natural linen or cotton-linen weave, and obvious raised hand-embroidery stitches. Keep every scene bright "
    "and airy with no yellow, amber, dark, tungsten, or harsh studio cast. Avoid clutter, distracting props, plastic or "
    "mass-produced fabric, distorted garment structure, malformed bodies or hands, extra fingers, unrealistic needle "
    "placement, blurry embroidery, spelling errors, missing source lettering, AI defects, text overlays, logos, and "
    "watermarks."
)


def _christmas_dress_baby_brief(scene: str) -> str:
    return (
        "Use the uploaded Christmas Dress Baby reference image as the exact product. Create one separate square 1:1 "
        f"high-end handmade Etsy Christmas product photo: {scene} {_CHRISTMAS_DRESS_BABY_LOCK} "
        f"{_CHRISTMAS_DRESS_BABY_STYLE}"
    )


_ORNAMENT_ROUND_LOCK = (
    "Keep the original round Christmas embroidered linen ornament 100% unchanged: same small round silhouette, "
    "same wooden hoop/frame and metal clasp or fastener if visible, same linen fabric and base color, same hanging "
    "cord or ribbon, same embroidery motif, placement, scale, thread colors, raised hand-stitch texture, fabric "
    "weave, natural wrinkles, proportions, and premium handmade finish. Do not redesign, redraw, simplify, move, "
    "resize, or replace the embroidery; do not change the frame, clasp, hanging construction, material, or product "
    "scale; and do not turn the ornament into a large wall hoop, bag, pillow, banner, coaster, plaque, or printed item."
)

_ORNAMENT_ROUND_STYLE = (
    "Overall style: realistic premium Etsy handmade Christmas product photography, square 1:1 composition, bright "
    "clear airy white-balanced natural daylight, accurate linen and thread colors, soft clean shadows, refined sparse "
    "Christmas or Noel decor, visible linen weave, and obvious raised hand-embroidery stitches with individual thread "
    "fibers and stitch direction. No harsh studio glare, yellow or dark lighting, clutter, machine-flat embroidery, "
    "printed artwork, AI defects, text overlay, logo, or watermark."
)


def _ornament_round_brief(scene: str) -> str:
    return (
        "Use the uploaded Ornament_Round reference image as the exact product. Create one separate square 1:1 "
        f"high-end handmade Etsy Christmas product photo: {scene} {_ORNAMENT_ROUND_LOCK} {_ORNAMENT_ROUND_STYLE}"
    )


_PN_ORNAMENT_LOCK = (
    "Keep the original handmade Punch Needle Christmas ornament 100% unchanged: same small ornament silhouette and "
    "proportions, same wooden hoop or frame and metal clasp or fastener when visible, same linen material and exact base "
    "color, same hanging cord or ribbon, same natural fabric tension and wrinkles, and the exact source motif. Preserve "
    "every motif element, readable personalized name when present, placement, scale, spacing, outline, wool-yarn color, "
    "and thick raised punch-needle loop-pile texture. The embroidery must visibly consist of dense tactile handmade wool "
    "loops and fibers, never flat floss stitches, machine embroidery, print, paint, applique, or tufted carpet. Never "
    "redesign, redraw, simplify, move, resize, recolor, replace, mirror, or cover the motif; never alter the frame, clasp, "
    "hanging construction, linen, or product scale; and never turn the ornament into a large wall hoop, pillow, bag, "
    "banner, coaster, plaque, stocking, plush, or another product."
)

_PN_ORNAMENT_STYLE = (
    "Overall style for every output: one separate true square 1:1 realistic premium Etsy handmade Christmas photograph, "
    "bright clear airy white-balanced natural daylight, clean whites, soft natural shadows, refined sparse Christmas "
    "decor, sharp product focus, visible linen weave, and unmistakable thick raised handmade punch-needle wool loops with "
    "individual yarn fibers. Keep the ornament realistically small. No yellow or dark cast, harsh studio glare, clutter, "
    "flat embroidery floss, printed or machine-made motif, distorted hands, extra fingers, impossible needle position, "
    "misspelled names, random text, text overlay, logo, watermark, or AI defects. Only images 8 and 14 may be four-panel "
    "collages; every other output must be one standalone scene. The only permitted added prop wording is Merry "
    "Christmas on the separate greeting card in image 5; never add wording to the ornament itself."
)


def _pn_ornament_brief(scene: str) -> str:
    return (
        "Use the uploaded PN Ornament reference image as the exact product. Create one separate square 1:1 high-end "
        f"handmade Etsy Christmas product photo: {scene} {_PN_ORNAMENT_LOCK} {_PN_ORNAMENT_STYLE}"
    )


_PC_STOCKS_LOCK = (
    "Keep the original Punch Needle Christmas stocking design 100% unchanged: same stocking silhouette, compact size, "
    "cuff shape and width, toe direction, heel curve, hanging loop or hanger construction, base fabric material and "
    "exact color, white cuff material when present, seams, edge finish, embroidery motif, motif placement, motif scale, "
    "wool yarn colors, and thick raised punch-needle loop texture. The motif must be copied only from the uploaded "
    "reference and must never be redrawn, simplified, moved, resized, recolored, printed, or made machine-flat. Do not "
    "turn the stocking into a sock worn on a foot, a bag, pillow, ornament hoop, banner, plush, or another product. "
    "Construction lock: this is a flat, one-sided decorative stocking panel, not a wearable or fillable stocking. It "
    "has no open storage cavity, interior pocket, usable opening, or capacity to hold gifts. Never place any object "
    "inside it or show contents emerging from it."
)

_PC_STOCKS_STYLE = (
    "Overall style for every output: realistic premium Etsy handmade Christmas product photography, true square 1:1 "
    "composition, bright clear airy white-balanced natural daylight, crisp festive colors, soft natural shadows, sharp "
    "product focus, visible fabric weave, and unmistakable raised wool punch-needle loops. Never use a yellow, amber, "
    "dark, tungsten, or moody cast; no harsh studio glare, malformed hands, extra fingers, fake needle placement, "
    "printed-looking embroidery, random text, logo, or watermark."
)


def _pc_stocks_brief(scene: str) -> str:
    return (
        "Use the uploaded PC Stocks reference image as the exact product. Create one separate square 1:1 high-end "
        f"handmade Etsy Punch Needle Christmas stocking product photo: {scene} {_PC_STOCKS_LOCK} {_PC_STOCKS_STYLE}"
    )


_BABY_ALBUM_LOCK = (
    "Keep the original baby photo album design 100% unchanged: same rectangular album/book shape, same cotton linen "
    "cover fabric and color family, same spine and edge construction, same cover embroidery motif, stitched name or "
    "lettering placement if present, same thread colors, same stitch scale, same handmade texture, and the same baby "
    "keepsake identity. The album may be shown closed, partly open, or open to clear plastic photo-pocket pages, but "
    "do not redesign the cover, change the embroidery layout, change the material, or turn it into a wedding guest "
    "book, vow book, hoop, pillow, banner, dress, or generic scrapbook."
)

_BABY_ALBUM_STYLE = (
    "Overall style for every output: bright clear airy natural daylight, clean white balanced tones, soft shadows, "
    "premium handmade Etsy product photography, visible cotton linen texture, visible raised hand-embroidery stitches, "
    "gentle first-birthday baby keepsake mood, uncluttered props, no watermark, no logo, no UI text, no random tags, "
    "no harsh yellow/orange cast."
)


def _baby_album_brief(scene: str) -> str:
    return (
        "Use the uploaded baby album reference image as the exact product. Create one separate square 1:1 high-end "
        f"handmade Etsy product photo: {scene} {_BABY_ALBUM_LOCK} {_BABY_ALBUM_STYLE}"
    )


_BABY_CHRISTMAS_ALBUM_LOCK = (
    "Keep the original baby Christmas photo album design 100% unchanged: same rectangular album/book shape, same "
    "cotton linen cover fabric and exact base color, same spine, binding, edges, thickness, cover embroidery motif, "
    "stitched name or lettering when visible, thread colors, stitch placement, stitch scale, raised hand-embroidery "
    "texture, and premium handmade identity. When the album is open, preserve realistic clear glossy plastic pocket "
    "sleeves with exactly two horizontal photos per visible page. Do not redesign or simplify the cover, change the "
    "embroidery, invent cover text, replace the material, or turn the album into a notebook, guest book, vow book, "
    "scrapbook, pillow, hoop, banner, or another product."
)

_BABY_CHRISTMAS_ALBUM_STYLE = (
    "Overall style for every output: realistic premium Etsy handmade baby Christmas product photography, true square "
    "1:1 composition, bright clear airy white-balanced natural daylight, clean whites, soft natural shadows, visible "
    "cotton linen weave, obvious raised hand stitches, tasteful baby-safe Christmas decor, balanced uncluttered styling, "
    "and sharp product focus. Never use a yellow, amber, dark, or moody cast; no harsh studio glare, printed-looking "
    "embroidery, malformed hands, extra fingers, fake needle placement, random readable text, logo, or watermark."
)


def _baby_christmas_album_brief(scene: str) -> str:
    return (
        "Use the uploaded Baby Christmas Album reference image as the exact product. Create one separate square 1:1 "
        f"high-end handmade Etsy Christmas product photo: {scene} {_BABY_CHRISTMAS_ALBUM_LOCK} "
        f"{_BABY_CHRISTMAS_ALBUM_STYLE}"
    )


_CHRISTMAS_ALBUM_LOCK = (
    "Keep the original Christmas photo album design 100% unchanged: same compact rectangular album shape and "
    "proportions, same cotton linen cover fabric and exact base color, same spine, binding, edges, thickness, cover "
    "embroidery motif, stitched lettering when present, thread colors, stitch placement, stitch scale, raised "
    "hand-embroidery texture, and premium handmade identity. The album must not become unusually long. When the album "
    "is open and photo pockets are requested, preserve realistic clear glossy plastic pocket sleeves with exactly two "
    "horizontal photos per visible page. Do not redesign or simplify the cover, change the embroidery, invent cover "
    "text, replace the material, or turn the album into a baby album, notebook, guest book, vow book, scrapbook, "
    "pillow, hoop, banner, or another product."
)

_CHRISTMAS_ALBUM_STYLE = (
    "Overall style for every output: realistic premium Etsy handmade Christmas product photography, true square 1:1 "
    "composition, bright clear airy white-balanced natural daylight, clean whites, soft natural shadows, visible "
    "cotton linen weave, obvious raised hand stitches, refined uncluttered Christmas decor, and sharp album focus. "
    "Never use a yellow, amber, dark, or moody cast; no harsh studio glare, printed-looking embroidery, malformed hands, "
    "extra fingers, fake needle placement, random readable text, logo, or watermark."
)


def _christmas_album_brief(scene: str) -> str:
    return (
        "Use the uploaded Christmas Album reference image as the exact product. Create one separate square 1:1 "
        f"high-end handmade Etsy Christmas product photo: {scene} {_CHRISTMAS_ALBUM_LOCK} "
        f"{_CHRISTMAS_ALBUM_STYLE}"
    )


_JEWELRY_BOX_COLLECTION_LOCK = (
    "Treat every jewelry box visible in the uploaded reference as one member of a fixed collection. Every output must "
    "show the complete source collection together, preserving each box's identity and its one-to-one association with "
    "its own embroidery design. Keep every box 100% unchanged: same small rounded-rectangle proportions, thickness, "
    "silver metal frame, hinge and front clasp positions, white linen cover, woven texture, edge finish, and exact "
    "hand-embroidered design. Preserve every source flower, leaf, mushroom, stem, berry, letter, name, shape, count, "
    "orientation, spacing, stitch direction, raised thread texture, placement, scale, and thread color. Never mix parts "
    "between boxes, omit a source design, make every box use one repeated motif, invent a similar motif, redraw, simplify, "
    "mirror, move, resize, recolor, print, machine-embroider, or cover the source designs. A foreground box may receive "
    "extra emphasis, but all remaining source designs must still be identifiable in the same frame. Only the explicit "
    "nine-name personalization shot may duplicate complete unmodified source motifs when more boxes are needed; it must "
    "still include every distinct source design at least once. In that shot use exactly Anita, Mom, Alice, Maria, Chloe, "
    "Jessie, Crystal, Eloise, and Jenna, one correctly spelled hand-embroidered name per box, changing only the name in "
    "the source lettering position and never shifting or shrinking the decorative motif."
)

_JEWELRY_BOX_TWO_COMPARTMENT_LOCK = (
    "Whenever any product box is open, its base must have exactly two shallow side-by-side rectangular compartments and "
    "nothing else: one single straight divider running continuously from the front wall to the back wall, producing one "
    "left compartment and one right compartment of nearly equal size. Each compartment is one uninterrupted open space "
    "lined in light cream or pale beige fabric. The inside lid is one plain flat clean fabric-lined surface. Never add a "
    "third or fourth compartment, cross divider, subdivision, drawer, tier, removable tray, ring roll, ring pillow, ring "
    "slot, necklace hook, lid pocket, retaining strap, mirror, or interior embroidery. Jewelry rests loose and naturally "
    "inside the two open compartments. Frame the scene so the single divider and both complete compartments are clearly "
    "visible."
)

_JEWELRY_BOX_STYLE = (
    "Overall style for every output: one separate true square 1:1 realistic premium Etsy handmade product photograph, "
    "professional composition, bright clear airy white-balanced natural daylight, clean whites, soft natural shadows, "
    "accurate silver metal and thread colors, visible linen weave, and unmistakable raised hand stitches. Keep wedding, "
    "vanity, gift, and craft props refined, sparse, and secondary. No yellow or amber cast, dark scene, harsh studio glare, "
    "clutter, oversized boxes, gold frames, plastic-looking linen, flat machine embroidery, malformed hands, extra "
    "fingers, misspelled names, digital text, random text, logo, watermark, or AI artifacts."
)


def _jewelry_box_brief(scene: str) -> str:
    return (
        "Use the uploaded personalized hand-embroidered linen Jewelry Box collection as the exact product reference. "
        f"Create one separate square 1:1 high-end handmade Etsy product photo: {scene} "
        f"{_JEWELRY_BOX_COLLECTION_LOCK} {_JEWELRY_BOX_TWO_COMPARTMENT_LOCK} {_JEWELRY_BOX_STYLE}"
    )


_NAPKIN_SET_LOCK = (
    "Keep the original set of exactly six handmade white linen dinner napkins 100% unchanged: same square napkin "
    "dimensions and proportions, white natural linen color, woven linen texture, thickness, hems, edge stitching, "
    "soft folds, and premium handmade finish. Preserve the six distinct source autumn embroidery motifs exactly, one "
    "original motif per napkin, including every flower, leaf, stem, acorn, shape, stitch direction, raised thread "
    "texture, placement, scale, and thread color. Never repeat one motif across several napkins, swap motifs between "
    "napkins, invent a seventh motif, add names or lettering, simplify, recolor, resize, move, cover, print, or replace "
    "the embroidery. In complete-set scenes show exactly six napkins and all six different source motifs."
)

_NAPKIN_SET_STYLE = (
    "Overall style for every output: one separate true square 1:1 realistic premium Etsy handmade product photograph, "
    "professional composition, bright clear airy white-balanced natural daylight, neutral clean whites, soft natural "
    "shadows, accurate thread colors, visible linen weave, crisp hems, and unmistakable raised hand-embroidery stitches. "
    "Use restrained elegant autumn table decor that never covers the product. No collage, contact sheet, grid, yellow or "
    "amber cast, harsh studio glare, dark scene, clutter, plastic or polyester-looking fabric, machine-flat embroidery, "
    "malformed hands, extra fingers, unrealistic needle position, random text, logo, or watermark."
)


def _napkin_set_brief(scene: str) -> str:
    return (
        "Use the uploaded Napkin Set reference image as the exact product. Create one separate square 1:1 high-end "
        f"handmade Etsy autumn product photo: {scene} {_NAPKIN_SET_LOCK} {_NAPKIN_SET_STYLE}"
    )


_ADVENT_CALENDAR_LOCK = (
    "Keep the original handmade linen Christmas wall-hanging advent countdown calendar 100% unchanged: same tall "
    "rectangular silhouette and proportions, exact fabric color and linen weave, thickness, seams, hems, natural "
    "wrinkles, top wooden dowel, dowel length, hanging cord, knots, and attachment construction. Preserve the exact "
    "source pocket count, row count, column count, pocket dimensions, spacing, borders, stitching, and placement. "
    "Preserve every visible pocket number in its exact source order and position with no missing, duplicated, swapped, "
    "invented, or reordered number. Preserve any personalized name, phrase, lettering style, Christmas motif, icon, "
    "thread color, stitch direction, raised hand-stitch texture, placement, scale, and spacing exactly as the source. "
    "Do not combine designs from other reference calendars. The selected source image is the only authoritative design. "
    "Small gifts may protrude slightly from pockets only when the shot requires them, but they must never cover a number "
    "or embroidery. Never turn the product into a generic banner, printed poster, paper calendar, organizer, or bag."
)

_ADVENT_CALENDAR_STYLE = (
    "Overall style for every output: one separate true square 1:1 realistic premium Etsy handmade Christmas product "
    "photograph, professionally composed in bright clear airy white-balanced natural daylight with clean whites, soft "
    "natural shadows, accurate fabric and thread colors, visible linen weave, crisp pocket seams, and unmistakable "
    "raised hand embroidery rather than print or machine-flat stitching. Fit the complete tall calendar inside the square "
    "frame with breathing room; never crop the cord, dowel, fabric edges, or final pocket row, and never stretch, widen, "
    "shorten, distort, or enlarge it unnaturally. Christmas props remain sparse and secondary. No yellow or amber cast, "
    "dark scene, harsh studio glare, clutter, plastic-looking fabric, malformed hands, extra fingers, misspelled text, "
    "random text, logo, watermark, UI, or AI artifacts. Only the explicitly requested four-panel detail image may be a "
    "collage; every other output is one standalone scene. Only image 6 may be a four-panel collage; images 1-5 and "
    "7-12 must each remain one standalone photograph."
)


def _advent_calendar_brief(scene: str) -> str:
    return (
        "Use the uploaded Advent Calendar reference image as the exact and only product reference. Create one separate "
        f"square 1:1 high-end handmade Etsy Christmas product photo: {scene} "
        f"{_ADVENT_CALENDAR_LOCK} {_ADVENT_CALENDAR_STYLE}"
    )


_CHRISTMAS_FABRIC_CROSS_LOCK = (
    "Keep the original soft handmade Christmas fabric cross 100% unchanged: same exact cross silhouette, arm width, "
    "height-to-width ratio, thickness, soft volume, size, proportions, fabric material and base color, linen weave, "
    "edge seams, natural wrinkles, embroidery motif, personalized text if present, thread colors, stitch direction, "
    "raised hand-stitch texture, embroidery placement and scale, hanging cord or ribbon material, loop length, and loop "
    "attachment position. Never redraw, simplify, mirror, recolor, move, enlarge, hide, print, or machine-embroider the "
    "source design, and never turn the cross into a pillow, plush toy, ornament of another shape, wooden cross, metal "
    "cross, wreath, banner, or mass-produced object. Only the surrounding scene and explicitly requested fabric-color "
    "variants may change."
)

_CHRISTMAS_FABRIC_CROSS_STYLE = (
    "Overall style for every output: one separate true square 1:1 premium Etsy handmade Christmas product photograph, "
    "professional editorial composition, clear airy bright white-balanced natural daylight, clean whites, soft natural "
    "shadows, accurate fabric and thread colors, visible linen fibers, crisp seams, and tack-sharp raised hand embroidery. "
    "Use refined restrained Christmas props that remain secondary and never obscure the cross. No yellow, amber, orange, "
    "golden-hour, tungsten, sepia, beige, or warm color cast; no harsh studio glare, dark scene, clutter, plastic-looking "
    "fabric, altered embroidery, mass-produced appearance, malformed hands or bodies, extra fingers, random text, logo, "
    "watermark, UI, blur, or AI artifacts. Only image 7 may be one four-panel 2x2 process collage; images 1-6 and 8-12 "
    "must each remain one standalone photograph."
)


def _christmas_fabric_cross_brief(scene: str) -> str:
    return (
        "Use the uploaded Christmas Fabric Cross reference image as the exact and only product reference. Create one "
        f"separate square 1:1 high-end handmade Etsy Christmas product photo: {scene} "
        f"{_CHRISTMAS_FABRIC_CROSS_LOCK} {_CHRISTMAS_FABRIC_CROSS_STYLE}"
    )


PRODUCT_SHOT_RULES: Dict[str, Dict[str, Any]] = {'tooth_fairy_pillow': {'display_name': 'Tooth Fairy Pillow',
                         'aliases': ('Tooth Fairy Pillow',
                                     'tooth fairy pillow',
                                     'tooth pillow',
                                     'tooth shaped pillow',
                                     'tooth-shaped pillow',
                                     'tooth fairy cushion',
                                     'first tooth pillow',
                                     'my first tooth pillow',
                                     'goi rang',
                                     'goi hinh rang',
                                     'goi tien rang',
                                     'goi tooth fairy'),
                         'target_count': 10,
                         'lock': 'the main product must remain the same hand-embroidered tooth fairy pillow with the exact tooth-shaped silhouette, cream linen fabric texture, soft stuffed form, white ribbon hanger, hand-embroidered name/text, floral or decorative motifs, thread colors, stitch placement, embroidery scale, seams, and handmade details from the source image',
                         'shots': (('Hero flat lay',
                                    'Clean hero flat lay on beige linen',
                                    _tooth_fairy_pillow_brief('a clean hero flat lay on natural beige linen fabric, with the tooth fairy pillow centered and the white ribbon tied neatly above. Decorate around the pillow with dried baby\'s breath, small dried pink rosebuds, and one small wooden star charm. Keep the embroidery fully visible and uncovered.')),
                                   ('Nursery lifestyle',
                                    'Bright nursery bed lifestyle',
                                    _tooth_fairy_pillow_brief('a bright nursery bed lifestyle scene with the tooth fairy pillow placed on a soft cream linen bed. Add a children\'s bedtime book and a pastel wooden stacking toy nearby, with a light wooden bed frame and soft curtains in the softly blurred background. Keep the embroidery facing forward, sharp, readable, and uncovered.')),
                                   ('Cozy close-up',
                                    'Upright close-up on quilt',
                                    _tooth_fairy_pillow_brief('a cozy close-up on a cream quilted blanket, with the tooth fairy pillow standing upright and slightly leaning. Place a soft knitted blanket beside it, small metallic star confetti around the pillow, and softly blurred fairy lights in the background. Keep the embroidery sharply focused, readable, and uncovered.')),
                                   ('Angled lifestyle',
                                    'Angled quilted bed lifestyle',
                                    _tooth_fairy_pillow_brief('an angled lifestyle shot on a cream quilted bed, with the tooth fairy pillow placed slightly off-center and leaning naturally. Put a chunky cream knit blanket in the foreground, with a pastel wooden toy and dried baby\'s breath softly blurred in the background. Keep the embroidery visible, sharp, and uncovered.')),
                                   ('Keepsake flat lay',
                                    'My First Tooth flat lay',
                                    _tooth_fairy_pillow_brief('a newborn keepsake flat lay on beige linen cloth, with the tooth fairy pillow centered. Place a round wooden milestone disc engraved "My First Tooth" on the left and small knitted baby socks on the right, with the socks color matching the embroidery thread color on the pillow, styled as a clean minimal gift set. Do not let props touch or cover the embroidery.')),
                                   ('Hanging lifestyle',
                                    'Hanging from brass door knob',
                                    _tooth_fairy_pillow_brief('the tooth fairy pillow hanging naturally by its white ribbon from a vintage brass door knob on a white wooden door near a bright window. The embroidery must face forward clearly, with a minimal airy interior background and soft depth of field. Keep the ribbon shape and product scale realistic.')),
                                   ('Tooth Fairy card flat lay',
                                    'Card and tiny bottle flat lay',
                                    _tooth_fairy_pillow_brief('a flat lay on a cream chunky knitted blanket, with the tooth fairy pillow placed on the right side. On the left, include a small Tooth Fairy themed card with cute tooth, moon, star, and pastel fairy illustration, plus a tiny clear glass bottle and white baby\'s breath. Keep the card as a separate prop only; no new text or mark may appear on the product itself. Keep the embroidery fully visible and uncovered.')),
                                   ('Close-up lifestyle',
                                    'Letter card close-up',
                                    _tooth_fairy_pillow_brief('a close-up lifestyle photo on a soft cream knitted blanket, with the tooth fairy pillow large in frame and slightly angled. Keep the embroidery tack-sharp and readable. Add a small Tooth Fairy letter card standing beside it as a secondary prop, with a soft blurred background. The card must not touch or cover the pillow embroidery.')),
                                   ('Crib hanging',
                                    'Hanging from crib rail',
                                    _tooth_fairy_pillow_brief('the tooth fairy pillow hanging from a white crib rail or white bedpost using its ribbon. Keep the embroidery centered, facing forward, sharp, visible, and uncovered. The softly blurred background includes teddy bears, pastel bedding, and subtle fairy lights.')),
                                   ('Gift packaging',
                                    'Open kraft gift box',
                                    _tooth_fairy_pillow_brief('a premium gift packaging shot with the tooth fairy pillow placed inside an open kraft cardboard gift box lined with white tissue paper. Arrange the white ribbon neatly and place small white baby\'s breath stems around the pillow without covering the embroidery. Use a clean white tabletop background.')))},
 'plush': {'display_name': 'Gấu bông',
           'aliases': ('Gấu bông',
                       'gau bong',
                       'gaubong',
                       'teddy bear',
                       'stuffed bear',
                       'stuffed toy',
                       'plush toy',
                       'plush'),
           'lock': 'the main product must remain the same soft plush/stuffed toy with the exact silhouette, fabric '
                   'pile, seams, face/features, embroidered name or motif placement, proportions, and cuddly scale '
                   'from the source image',
           'shots': (('Product display',
                      'Product display',
                      'Product photos of stuffed animals are taken from reference images. Three stuffed animals are '
                      "placed on a clean, light-colored oak table, decorated with a few children's toys (each stuffed "
                      'animal is embroidered with a different English name). Soft natural light shines from the window '
                      'above and to the left, the background is a minimalist, slightly blurred cream color, the '
                      'objects are centered with ample space, and the shallow depth of field creates a gentle bokeh '
                      'effect. A standout product photo on Etsy. \n'
                      '\n'
                      'IMPORTANT: Maintain the EXACT shape of the stuffed animals from the reference image. Keep the '
                      'fabric, color palette, facial features, embroidery details, and proportions. Do not edit the '
                      'animals themselves – only create a new background around them. \n'
                      '\n'
                      "STYLE: Handmade product photography, soft natural lighting, editorial quality, Etsy's modern "
                      'minimalist aesthetic, 1:1 square aspect ratio. \n'
                      '\n'
                      'AVOID: the appearance of the product. Mass production, studio lighting, overly harsh '
                      'background, clutter, errors. AI, text overlays, watermarks.'),
                     ('Lifestyle',
                      'Baby hug',
                      "Lifestyle photography: a baby's small hands and arms dressed in a soft cream knit romper, "
                      'gently holding the stuffed animal from the reference image close to their chest. CRITICAL: NO '
                      "face or head visible — frame must be cropped at the baby's shoulders/collar level, showing only "
                      'the torso area and small hands wrapped tenderly around the bear. Soft morning window light, '
                      "creamy warm neutral tones, emotional intimate warmth, slight motion in baby's fingers.\n"
                      '\n'
                      'IMPORTANT: Maintain the EXACT appearance of the stuffed animal from the reference image. Keep '
                      'identical fabric texture, color palette, facial features, embroidered details, and proportions. '
                      'Do not modify the animal itself — only create the new scene around it.\n'
                      '\n'
                      'STYLE: Artisan handcrafted product photography, soft natural lighting, editorial quality, '
                      'minimal modern Etsy aesthetic, 1:1 square aspect ratio. \n'
                      'AVOID: plush mass-produced look, harsh studio lighting, cluttered backgrounds, AI artifacts, '
                      'text overlays, watermarks, any visible baby face or facial features.'),
                     ('Lifestyle',
                      'Baby sleep',
                      'A lifestyle shot from a slightly elevated angle: a baby sleeping soundly on a soft '
                      "cream-colored linen blanket, cuddling a stuffed animal. Both the baby's face and the teddy bear "
                      'are visible. Soft, dreamy morning light filters through the thin curtains, creating a gentle '
                      'pastel tone and a peaceful, tranquil atmosphere.\n'
                      '\n'
                      'IMPORTANT: Maintain the EXACT shape of the stuffed animal from the reference photo. Keep the '
                      'fabric, color palette, facial features, embroidery details, and proportions unchanged. Do not '
                      'edit the animal itself—only create a new setting around it.\n'
                      '\n'
                      'STYLE: Handmade product photography, soft natural light, editorial quality, modern minimalist '
                      'Etsy-style aesthetic, 1:1 square aspect ratio. AVOID: mass-produced luxury look, harsh studio '
                      "lighting, cluttered background, AI errors, text overlays, watermarks, any baby's face or facial "
                      'features clearly visible.'),
                     ('Lifestyle',
                      'Mẹ & bé trên sofa',
                      'Lifestyle photo: A mother and child sit on a sofa, the mother holding the child in her lap, the '
                      "baby's face turned outwards, in a bright, cozy nursery or in a softly lit home, while the baby "
                      'smiles, clutching the stuffed animal from the reference image to their chest. The stuffed '
                      "animal should look small and cute in the baby's arms, with compact dimensions of approximately "
                      "50 x 27 x 14 cm, clearly proportionate to the baby. The mother's presence should convey warmth "
                      'and protection, with only her upper body and arms visible, keeping the emotional focus on the '
                      'bond between mother, baby, and the stuffed animal. Soft natural light from the window, warm '
                      'neutral tones, a minimalist, clean background with soft fabric, and a shallow depth of field '
                      'create a gentle blurring effect, giving the feeling of a delicate handcrafted keepsake – a '
                      'high-end lifestyle photo for Etsy.\n'
                      '\n'
                      'IMPORTANT: Maintain the EXACT shape of the stuffed animal from the reference image. Preserve '
                      'the original fabric, color palette, facial features, embroidery details, proportions, and '
                      'craftsmanship. Do not edit the stuffed animal in any way – only create a new context around it. '
                      'The stuffed animal must always be clearly visible. Easily recognizable and small enough to look '
                      'natural, as if being held by a baby.\n'
                      '\n'
                      'STYLE: Handmade product photography in a lifestyle style, soft natural lighting, editorial '
                      'quality, modern minimalist Etsy aesthetic, 1:1 square aspect ratio.\n'
                      '\n'
                      'AVOID: Harsh studio lighting, cluttered backgrounds, unrealistic mother-baby images, oversized '
                      'stuffed animals, excessive posing interactions, mass-produced stuffed animal images, AI errors, '
                      'text overlays, watermarks.'),
                     ('Lifestyle',
                      'Nursery cot',
                      'Lifestyle photography: the stuffed animal from the reference image sitting inside a white '
                      'wooden baby cot, surrounded by a cream knitted blanket with waffle texture and two small '
                      'embroidered floral cushions in dusty pink and sage green, soft morning light streaming through '
                      'sheer white curtains creating gentle highlights, cozy Scandinavian nursery aesthetic, shallow '
                      'depth of field with the bear in sharp focus.\n'
                      '\n'
                      'IMPORTANT: Maintain the EXACT appearance of the stuffed animal from the reference image. Keep '
                      'identical fabric texture, color palette, facial features, embroidered details, and proportions. '
                      'Do not modify the animal itself — only create the new scene around it.\n'
                      '\n'
                      'STYLE: Artisan handcrafted product photography, soft natural lighting, editorial quality, '
                      'minimal modern Etsy aesthetic, 1:1 square aspect ratio. AVOID: plush mass-produced look, harsh '
                      'studio lighting, cluttered backgrounds, AI artifacts, text overlays, watermarks.'),
                     ('Gift box',
                      'Gift box',
                      'Product photography: the stuffed animal from the reference image nestled inside an open kraft '
                      'paper gift box lined with cream crinkle tissue paper, a small handwritten gift tag attached '
                      'with natural jute twine (tag blank, no readable text), a single dried eucalyptus sprig placed '
                      'beside the box, flat lay composition on pale linen surface, soft even diffused daylight, '
                      'minimal artisan packaging aesthetic, romantic gift-giving mood.\n'
                      '\n'
                      'IMPORTANT: Maintain the EXACT appearance of the stuffed animal from the reference image. Keep '
                      'identical fabric texture, color palette, facial features, embroidered details, and proportions. '
                      'Do not modify the animal itself — only create the new scene around it.\n'
                      '\n'
                      'STYLE: Artisan handcrafted product photography, soft natural lighting, editorial quality, '
                      'minimal modern Etsy aesthetic, 1:1 square aspect ratio. AVOID: plush mass-produced look, harsh '
                      'studio lighting, cluttered backgrounds, AI artifacts, text overlays, watermarks, any readable '
                      'text on the gift tag.'),
                     ('Cận thêu tay',
                      'Cận thêu tay',
                      'Close-up product photography: detailed close-ups focusing on the hand-embroidery details and '
                      'fabric texture (close-up shots of the hand-embroidery) of the plush toy from the reference '
                      'image, illuminated from the side with soft natural light to highlight each stitch and '
                      'handcrafted texture, extremely shallow depth of field with only the embroidery area in sharp '
                      'focus, showcasing the exquisite craftsmanship worthy of the high price.\n'
                      '\n'
                      'IMPORTANT: Maintain the EXACT shape of the plush toy from the reference image. Preserve the '
                      'fabric texture, color palette, embroidery design, thread color, and stitch style. Do not create '
                      'new embroidery styles or alter existing details—only enlarge what already exists.\n'
                      '\n'
                      'STYLE: Handcrafted product photography, soft natural light, editorial quality, modern '
                      'minimalist Etsy-style aesthetics, 1:1 square aspect ratio. AVOID: mass-produced look, harsh '
                      'studio lighting, cluttered background, AI errors, overlays.The image is blurry and produces '
                      'embroidery details not present in the reference photo.'),
                     ('Lifestyle',
                      'Bé ôm trên chăn muslin',
                      'Lifestyle Photo: A baby lying in a soft, light pink muslin blanket is gently clutching a '
                      'stuffed animal from the reference photo with both hands, creating a cozy and natural nursery '
                      "atmosphere. Only the baby's tummy, chest, and arms are visible, with the stuffed animal "
                      'standing out as the main emotional focal point. Soft natural light from the window, warm '
                      'neutral tones, a minimalist, clean composition with soft materials, and a shallow depth of '
                      'field create a hazy effect, giving the image a light, handcrafted feel – a perfect high-end '
                      'lifestyle photo for Etsy.\n'
                      '\n'
                      'IMPORTANT: Keep the EXACT shape of the stuffed animal from the reference photo. Keep the '
                      'material, color palette, facial features, embroidery details, proportions, and craftsmanship. '
                      'Do not edit the stuffed animal in any way – just create a new background around it. Keep the '
                      'stuffed animal clearly visible and easily recognizable, with the baby naturally holding it '
                      'without obscuring too many details.\n'
                      '\n'
                      'STYLE: Handmade lifestyle product photography, soft natural lighting, editorial quality, modern '
                      'minimalist Etsy aesthetic, 1:1 square aspect ratio.\n'
                      '\n'
                      'AVOID: Overly harsh studio lighting, cluttered nursery background, unrealistic baby anatomy, '
                      'excessive posing interaction, mass-produced toy images, AI errors, text overlays, watermarks.'),
                     ('Flat lay',
                      'Flat lay baby shower',
                      'The product photo is taken in a flat, top-down composition: the stuffed animal from the '
                      'reference photo is placed in a round wicker basket, covered with a thin layer of voile fabric, '
                      'positioned in the center, surrounded by carefully arranged baby shower decorations — a pair of '
                      'small woolen baby shoes in the upper left, a wooden teething ring with natural beads in the '
                      "upper right, a small cluster of dried baby's breath flowers in the lower left, toys, and a "
                      'neatly folded and gently draped cream-colored muslin baby swaddle in the lower right. Soft '
                      'daylight, an editorial-style composition, and an asymmetrical arrangement create a sense of '
                      'balance and naturalness.\n'
                      '\n'
                      'IMPORTANT: Maintain the EXACT shape of the stuffed animal from the reference photo. Preserve '
                      'the fabric texture, color palette, facial features, embroidery details, and proportions. Do not '
                      'edit the animal itself — only create a new background around it.\n'
                      '\n'
                      'STYLE: Photographic Hand-drawn artwork. Soft, subtle natural lighting, high-quality editing, '
                      'modern minimalist Etsy-style aesthetics, and a 1:1 square aspect ratio. AVOID: Mass-produced '
                      'images, harsh studio lighting, cluttered backgrounds, AI errors, text overlays, and '
                      'watermarks.'),
                     ('Bối cảnh đặc biệt',
                      'Vintage floral',
                      'Lifestyle photography: the stuffed animal from the reference image resting on a vintage floral '
                      'quilted blanket featuring soft pastel rose, dusty pink, and cream floral patterns in '
                      "grandmother's heirloom style, a small antique brass vase with wildflowers (baby's breath, small "
                      'pink roses, lavender sprigs) placed softly beside, warm golden afternoon sunlight filtering in, '
                      'romantic Pinterest-worthy composition, slight film grain aesthetic, nostalgic heritage mood.\n'
                      '\n'
                      'IMPORTANT: Maintain the EXACT appearance of the stuffed animal from the reference image. Keep '
                      'identical fabric texture, color palette, facial features, embroidered details, and proportions. '
                      'Do not modify the animal itself — only create the new scene around it.\n'
                      '\n'
                      'STYLE: Artisan handcrafted product photography, soft natural lighting, editorial quality, '
                      'minimal modern Etsy aesthetic, 1:1 square aspect ratio. AVOID: plush mass-produced look, harsh '
                      'studio lighting, cluttered backgrounds, AI artifacts, text overlays, watermarks.'),
                     ('Editorial/Grid',
                      'Editorial — Grid quy trình',
                      'Create a unified image illustrating the process of making a stuffed animal from the reference '
                      'image, arranged in a high-quality, editorial-style 6-square grid layout (3 columns × 2 rows), '
                      'with thin, soft cream-colored spacing between the squares (no sharp edges, clean grid layout, '
                      'Pinterest style).\n'
                      '\n'
                      '6 SQUARES IN ORDER:\n'
                      '\n'
                      'Square 1 (top left): A flat image of natural cotton linen and textured boucle fabric samples '
                      'neatly arranged on a warm wooden work surface, colors matching the reference bear image, next '
                      'to a wooden embroidery hoop and spools of cream-colored thread.\n'
                      '\n'
                      'Square 2 (top middle): A hand sketching an embroidery pattern (the embroidery part shown in the '
                      'Macro detail image) onto stretched fabric held in a wooden embroidery hoop using white chalk, '
                      'with visible chalk marks.\n'
                      '\n'
                      'Image 3 (top right): A close-up macro shot of a needle pulling the correct colored thread for '
                      'the embroidery pattern on a wooden frame, showing the individual stitches. The shallow depth of '
                      'field highlights the texture of the thread.\n'
                      '\n'
                      "Image 4 (bottom left): Two hands sewing the bear's body pieces together. The soft yellow "
                      'afternoon light clearly highlights the tension of the needle and thread. The cut fabric pieces '
                      'lie next to the sewing machine.\n'
                      '\n'
                      "Image 5 (bottom center): Hands gently stuffing the bear's body with soft cotton (the bear's "
                      'color matches the pattern). The wrinkles in the fabric are being smoothed out, creating a warm '
                      'and intimate close-up.\n'
                      '\n'
                      'Image 6 (bottom right): The finished bear (EXACTLY LIKE the reference image) stands upright '
                      'against a neutral beige linen background. The soft light creates a beautiful image of the '
                      'finished product.\n'
                      '\n'
                      'ENVIRONMENT: A cozy Vietnamese craft workshop, wooden workbenches, warm neutral beige and cream '
                      'tones throughout the images, minimal tools visible (scissors, cream-colored thread spool, '
                      'wooden embroidery hoop), no human faces shown — only hands and tools.\n'
                      '\n'
                      'LIGHTING: Soft, natural side lighting, warm and consistent across all 6 images, cinematic feel, '
                      'the warmth of golden hour.\n'
                      '\n'
                      'IMPORTANT: In image 6, the finished bear MUST be EXACTLY LIKE the reference image — same '
                      'materials, color palette, facial features, embroidery details, and proportions. In the other '
                      'images, the materials and embroidery design must match what will make up the reference bear. No '
                      'changes to the final product design are permitted.\n'
                      '\n'
                      'STYLE: Artistic storytelling, emotionally warm, pleasant, high-end Etsy editorial aesthetics, '
                      'rich fabrics and embroidery, with a particular emphasis on close-up embroidery details.\n'
                      '\n'
                      'AVOID: Overlapping text, logos, watermarks, human faces, edited product designs, cluttered '
                      'backgrounds, harsh studio lighting, AI errors, plastic-looking fabrics, overly saturated '
                      'colors.'))},
 'crown': {'display_name': 'Crown',
           'aliases': ('Crown',
                       'linen crown',
                       'fabric crown',
                       'birthday crown',
                       'baby crown',
                       'child crown',
                       'children crown',
                       'kids crown',
                       'party crown',
                       'embroidered crown',
                       'crown with pom-poms',
                       'pom pom crown',
                       'pompom crown',
                       'vương miện',
                       'vuong mien',
                       'vương miện vải',
                       'vuong mien vai'),
           'lock': 'the main product must remain the same soft fabric birthday crown with the exact pointed crown '
                   'silhouette, upright fabric band, pom-pom or felt-ball tips, linen/fabric texture, embroidery '
                   'placement, thread colors, proportions, scale, and handcrafted birthday accessory identity from '
                   'the source image',
           'shots': (('Product display',
                      'Crown upright on wood birthday table',
                      'The crown stands upright on a wood-grained table. Mini pine cones and a small cake are placed '
                      'around it, with a muted pastel birthday background behind the product. Shoot from a slightly '
                      'horizontal angle with soft clean window sunlight, keeping the scene fresh, bright, and birthday '
                      'themed. Do not add specific characters, names, or new embroidery motifs; keep the embroidery '
                      'versatile for any occasion. 1:1 square aspect ratio. Avoid clutter, harsh studio lighting, '
                      'plastic-looking fabric, flat machine embroidery, AI errors, text overlays, logos, and '
                      'watermarks.'),
                     ('Lifestyle',
                      'Crown on white muslin blanket',
                      'The crown rests slightly off-center on a white muslin blanket with plenty of breathing space. '
                      'Decorate with a teddy bear, fabric book, small pillows, and soft cream or beige nursery tones. '
                      'Use a low frontal view of the crown and natural light through thin curtains for a soft airy '
                      'birthday lifestyle photo. Do not add specific characters, names, or new embroidery motifs. 1:1 '
                      'square aspect ratio. Avoid clutter, harsh lighting, distorted fabric, blurry embroidery, '
                      'text overlays, logos, and watermarks.'),
                     ('Cận thêu tay',
                      'Collage 4 close-ups embroidery and pom-pom',
                      'Create one square composite image made of four small close-up photos. Each small photo focuses '
                      'on close-up details of the crown embroidery, linen fabric texture, pom-pom or felt-ball tips, '
                      'stitches, seams, and handcrafted construction. Keep the details sharp, tactile, and premium. '
                      'Do not redesign the crown or add new embroidery motifs. This is a detail collage only, not a '
                      'multi-output grid. Use clean soft natural white window light. Avoid blurry close-ups, flat '
                      'machine embroidery, text overlays, logos, and watermarks.'),
                     ('Product display',
                      'Five crowns triangular pyramid colorways',
                      'Keep the embroidery intact and show five fabric crowns arranged in a triangular pyramid shape '
                      'on a white wood-grained table beside a window. Use different fabric colors; only if the source '
                      'visibly has an embroidered name may the crowns use different plausible embroidered names while '
                      'keeping the embroidery style and thread colors unchanged. Decorate with a few small '
                      "wildflowers, dried pine cones, and children's wooden toys. Shoot from a low frontal angle in "
                      'clean white window light. Avoid new motifs, character embroidery, clutter, text overlays, '
                      'logos, and watermarks.'),
                     ('Product display',
                      'Crown on high shelf by window',
                      'Place the crown on a high shelf next to a window without changing the embroidery or pattern. '
                      'Turn the embroidered face toward the light so the stitching is clearly visible. Add a simple '
                      'vase of fresh flowers, a few English storybooks, and a baby bracelet as secondary props. Shoot '
                      'from a low horizontal or close 3/4 angle with gentle slanted morning window light and soft '
                      'shadows. Do not add specific embroidery patterns or text. 1:1 square aspect ratio.'),
                     ('Product display',
                      'Three crowns on gray shelf with daffodils',
                      'Show three crowns on a gray wooden shelf by a window, with different fabric colors but the same '
                      'embroidery layout and thread colors. Only if the source visibly has an embroidered name may the '
                      'crowns use different plausible names. Place a vase of yellow daffodils nearby and let clean '
                      'white sunlight stream in from the window. Preserve the crown construction, pom-poms, fabric, '
                      'and stitch quality. Avoid new motifs, clutter, harsh lighting, text overlays, logos, and '
                      'watermarks.'),
                     ('Lifestyle',
                      'Mother hand holding crown',
                      "A mother's hand holds the crown in front of a bright window to show the true size and delicate "
                      'craftsmanship. The person holding the crown wears neutral knit or linen sleeves, and the '
                      'background is softly blurred. The product should look soft, light, and meticulously crafted, '
                      'with embroidery and pom-poms visible. Do not redesign the crown or add motifs. 1:1 square '
                      'aspect ratio. Avoid distorted hands, extra fingers, harsh lighting, clutter, text overlays, '
                      'logos, and watermarks.'),
                     ('Quy trình',
                      'Four-panel crown making process',
                      'Create one square process collage with four small photos: 1) a hand picking white fabric from '
                      'many rolls of multicolored linen; 2) sketching the embroidery design onto a large piece of '
                      'fabric; 3) colorful embroidery being completed on fabric in a round embroidery hoop, one hand '
                      'holding the hoop and the other holding a threaded needle, with embroidery thread and '
                      'multicolored pompoms nearby; 4) sewing the crown shape with a sewing machine. Use soft clean '
                      'window light. The hoop is only a process tool, not the final product. Avoid distorted hands, '
                      'unrealistic needle placement, new motifs, text overlays, logos, and watermarks.'),
                     ('Lifestyle',
                      'Baby wearing crown outdoor birthday',
                      'A baby wearing the crown stands at an outdoor birthday celebration with a happy bright birthday '
                      'tone, holding a piece of cake in hand. Use a full-body shot of the baby while clearly showing '
                      'the embroidery and crown shape. Keep the crown design, fabric color family, pom-poms, and '
                      'stitch texture faithful to the source. Do not add new character embroidery or text. Use soft '
                      'natural daylight, 1:1 square aspect ratio. Avoid distorted baby anatomy, clutter, harsh light, '
                      'text overlays, logos, and watermarks.'),
                     ('Lifestyle',
                      'Baby wearing crown blowing candles',
                      'A baby wearing the crown sits in front of a cake and blows out candles, surrounded by happy '
                      'bright birthday decorations with a small amount of confetti. The embroidery on the crown must '
                      'be clearly visible and sharp. Keep the crown exact in silhouette, fabric, pom-poms, embroidery '
                      'placement, and handmade texture. Do not add new motifs, names, or readable text. Use soft '
                      'natural white window light, 1:1 square aspect ratio. Avoid distorted hands or face, clutter, '
                      'logos, watermarks, and text overlays.'),
                     ('Product display',
                      'Crown on cake stand',
                      'Place the crown on a small cake stand so it sits higher than the tabletop. Put the cake slightly '
                      'behind and off to one side, with cupcakes, pampas grass, and wooden toys as secondary birthday '
                      'props. Shoot from a low frontal angle for an elegant product look. Use window light or '
                      'simulated window studio light that is soft, clear, and neutral. Do not redesign the crown or '
                      'add specific embroidery motifs. 1:1 square aspect ratio. Avoid clutter, harsh lighting, text '
                      'overlays, logos, and watermarks.'))},
 'birthday_hat': {'display_name': 'Birthday Hat',
           'aliases': ('Birthday Hat',
                       'birthday hat',
                       'linen birthday hat',
                       'fabric birthday hat',
                       'embroidered birthday hat',
                       'hand embroidered birthday hat',
                       'baby birthday hat',
                       'child birthday hat',
                       'kids birthday hat',
                       'party hat',
                       'linen party hat',
                       'fabric party hat',
                       'embroidered party hat',
                       'birthday hat with pom-poms',
                       'pom pom birthday hat',
                       'pompom birthday hat',
                       'mũ sinh nhật',
                       'mu sinh nhat',
                       'mũ sinh nhật linen',
                       'mu sinh nhat linen',
                       'mũ sinh nhật thêu tay',
                       'mu sinh nhat theu tay'),
           'target_count': 12,
           'allow_planned_multi_panel_shots': True,
           'allow_planned_infographic_text': True,
           'lock': 'the main product must remain the exact same hand-embroidered linen birthday hat from the source '
                   'image: same hat silhouette, fabric band or cone shape if present, ruffle trim if present, tie '
                   'strings, pom-pom or felt-ball details, linen fabric weave, base fabric color, embroidery '
                   'placement, motif scale, thread colors, raised stitch texture, natural wrinkles, proportions, and '
                   'premium handmade birthday accessory identity; never redesign it, simplify the embroidery, move '
                   'the motif, change the birthday hat shape, turn it into a baby crown, book, pillow, banner, hoop, '
                   'plastic party hat, or mass-produced accessory',
           'shots': (('Product display',
                      'White wood birthday tabletop',
                      'Place one hand-embroidered linen birthday hat on a white wood-grain tabletop, with the '
                      'embroidered face fully visible and the full birthday hat shape not zoomed too close. Use a softly '
                      'blurred pastel birthday background, high-key even white light, and a frontal or slight angled '
                      'view. Add one small cake slice, a few fresh fruits or berries, and tiny confetti pieces as '
                      'minimal decor. Preserve the exact source birthday hat silhouette, linen texture, tie strings, '
                      'pompoms, ruffle trim if present, embroidery placement, thread colors, stitch relief, natural '
                      'wrinkles, and handmade proportions.'),
                     ('Colorway display',
                      'Three to five birthday hats colorway fan',
                      'Arrange three to five linen birthday hats in a neat horizontal row or gentle fan on a white '
                      'wood-grain table. Each variant may use a different linen base color, and only if the source '
                      'visibly contains a personalized embroidered name may the variants use different plausible baby '
                      'names while keeping the same lettering placement, stitch style, scale, and thread colors. The '
                      'embroidery motif, ruffle trim, pom-poms, tie strings, fabric texture, birthday hat proportions, and '
                      'handmade construction must match the source. Shoot top-down 90 degrees or from a 60-degree '
                      'overhead angle with very even white daylight. Add a small birthday cake, pastel banner, and '
                      'soft balloons as secondary birthday props.'),
                     ('Lifestyle flat lay',
                      'Birthday hat beside baby birthday outfit',
                      'Place the birthday hat beside a baby birthday outfit such as a white romper, bib, or small white shirt '
                      'on a bright table near a window. Use a straight frontal product view with soft white daylight '
                      'so no fabric area falls dark. Add tiny soft shoes, small socks, a wooden age number, and a '
                      'simple wooden toy as neat secondary props. Keep the birthday hat front embroidery sharp and uncovered '
                      'and preserve the exact source linen weave, stitch relief, pom-poms, tie strings, ruffle trim, '
                      'wrinkles, and scale.'),
                     ('Nursery shelf',
                      'Birthday hat on light wood nursery shelf',
                      'Place the birthday hat on a light wood shelf in a baby room, with the embroidered face turned outward '
                      'toward the camera. Shoot from a 45-degree front angle with soft even white daylight and no dark '
                      'room corners. Add one small plush toy, baby books, and simple wooden baby-name blocks with no '
                      'legible extra text unless the same name appears on the source product. Keep the shelf styling '
                      'airy, tidy, and premium while preserving the birthday hat shape, linen texture, tie strings, '
                      'pompoms, embroidery placement, stitch colors, ruffle trim, and handmade details exactly.'),
                     ('Craft table',
                      'Birthday hat with embroidery tools',
                      'Place the birthday hat on a bright handmade table beside a small embroidery hoop, blue-beige thread '
                      'spools, small scissors, and a few linen fabric scraps arranged at the edge of the frame. Shoot '
                      'from a 45-60 degree overhead angle with clean white daylight, never yellow sewing-lamp light. '
                      'Use the tools only as refined handmade context; they must not cover the birthday hat embroidery, '
                      'pompoms, tie strings, ruffle trim, or linen texture. Preserve the exact source product and '
                      'make the raised hand stitches and fabric weave crisp.'),
                     ('Infographic detail',
                      'Square close-up detail infographic',
                      'Create one premium square 1:1 product infographic for the linen birthday hat. Left side: show '
                      'the main birthday hat placed slightly angled on soft lace fabric, with the exact source embroidery, '
                      'linen weave, pom-poms, tie strings, ruffle trim, and handmade shape preserved. Top left text '
                      'for this infographic shot only: "Chi tiet can canh" in an elegant serif style, dark brown, '
                      'with a tiny heart icon and thin decorative line underneath. Right side: stack three rounded '
                      'rectangle detail panels with soft white borders and subtle shadows. Panel 1 is a macro of the '
                      'raised hand embroidery and linen texture, captioned "Hand-Embroidered". Panel 2 is a macro of '
                      'the birthday hat pom-pom, captioned "Cute Pom-Pom". Panel 3 is a macro of the ruffle edge, captioned '
                      '"Ruffle Trim". This text exception applies only to image 6; add no logos, watermark, price '
                      'labels, brand tags, or extra text elsewhere. Use bright soft white daylight, clean spacing, '
                      'premium Etsy handmade styling, realistic product photography, and no dark/yellow cast.'),
                     ('Process lifestyle',
                      'Woman hand-embroidering birthday hat fabric',
                      'Show an adult woman sitting at a clean handmade table, one hand holding a small embroidery hoop '
                      'and the other hand carefully embroidering the same motif onto linen fabric matching the birthday hat '
                      'color with a real threaded needle. Include small scissors, thread spools, folded linen fabric, '
                      'and beautiful white window light. Hands must be anatomically natural, with realistic needle '
                      'placement and a genuine hand-embroidery action. This is a making-process scene only; it must '
                      'clearly support the finished linen birthday hat and must not turn the product into a hoop.'),
                     ('Process collage',
                      'Four-panel birthday hat making process',
                      'Create one square 1:1 process collage made of four small photos with soft white light. Panel 1: '
                      'a hand selecting white fabric among many rolls of colored linen. Panel 2: the embroidery motif '
                      'being sketched onto a large linen piece. Panel 3: the colored embroidery finished on fabric in '
                      'a small embroidery hoop, one hand holding the hoop and the other hand holding a threaded needle '
                      'placed realistically on the hoop, with embroidery threads as decor. Panel 4: the finished linen '
                      'birthday hat completed and matching the exact source product shape, embroidery placement, '
                      'pompoms, tie strings, ruffle trim, linen texture, and handmade proportions. This is one process '
                      'collage image only, not a multi-output grid.'),
                     ('Baby lifestyle',
                      'Baby wearing birthday hat front portrait',
                      'Show a baby wearing the birthday hat, sitting or standing in a clean pastel birthday setting, with the '
                      'baby face and birthday hat centered in the frame. The birthday hat must be correctly scaled to the baby head, '
                      'not oversized, with the embroidered face visible and sharp. Use soft white light with no harsh '
                      'shadows on the baby face, a frontal camera angle, and one or two softly blurred balloons in the '
                      'background. Preserve the exact source birthday hat fabric color, linen texture, pom-poms, tie strings, '
                      'ruffle trim, embroidery placement, thread colors, stitch relief, and handmade irregularities.'),
                     ('Baby lifestyle',
                      'Baby holding birthday hat with cake',
                      'Show a baby sitting on a light-colored rug, holding the linen birthday hat gently while a '
                      'small birthday cake sits nearby. Shoot from a 30-45 degree angled view that clearly shows the '
                      'front of the birthday hat, embroidery, pom-poms, ruffle trim, and tie strings. Use a soft pastel '
                      'birthday party background with neutral balloons, a small banner, light confetti, and bright '
                      'clear white daylight. Keep the birthday hat natural in the baby hands and do not distort the product '
                      'or baby anatomy.'),
                     ('Pedestal display',
                      'Birthday hat on cake pedestal beside cake',
                      'Place the birthday hat on a small pedestal cake stand so it sits higher than the tabletop. Set a small '
                      'cake behind it, slightly offset to one side, and add cupcakes, candles, and star-shaped cookies '
                      'as refined birthday props. Shoot from a low frontal angle so the product looks elevated and '
                      'premium. Use soft window light or simulated window studio light that is clean, white, and clear. '
                      'Keep the birthday hat full front visible, with exact source embroidery, linen texture, pom-poms, tie '
                      'strings, ruffle trim, wrinkles, stitch relief, and proportions unchanged.'),
                     ('Rustic premium display',
                      'Birthday hat on round wood pedestal with linen drape',
                      'Place the birthday hat centered on a low round wooden pedestal. Behind it, use a soft beige linen '
                      'drape that flows naturally with the product; near the base add one small cluster of wildflowers '
                      'and several dried pine cones in varied sizes. Shoot straight-on at product height with soft '
                      'natural light from the left and a gentle shadow that enhances the linen texture. Preserve the '
                      'exact source birthday hat shape, embroidery placement, thread colors, pom-poms, tie strings, ruffle '
                      'trim, fabric weave, natural wrinkles, raised hand stitches, and handmade premium identity.'))},
 'halloween_bag': {'display_name': 'Halloween Treat Bag',
                   'aliases': ('Halloween Treat Bag',
                               'halloween treat bag',
                               'halloween bag',
                               'trick or treat bag',
                               'trick-or-treat bag',
                               'treat or trick bag',
                               'treat-or-trick bag',
                               'candy bag',
                               'halloween candy bag',
                               'linen halloween bag',
                               'embroidered halloween bag',
                               'embroidered trick or treat bag',
                               'halloween drawstring bag',
                               'halloween treat pouch',
                               'tui dung keo halloween',
                               'tui keo halloween',
                               'tui trick or treat',
                               'tui treat or trick'),
                   'target_count': 14,
                   'allow_planned_multi_panel_shots': True,
                   'lock': 'the main product must remain the exact same hand-embroidered linen Halloween trick-or-treat candy bag from the source image, with the same small bag silhouette, fabric material, fabric color, single handle or tie/strap construction if visible, drawstring or closure if present, embroidery placement, embroidery motif, embroidery scale, thread colors, raised hand-stitch texture, natural wrinkles, seams, proportions, and premium handmade Halloween identity; never enlarge the bag unnaturally, add extra handles or straps, redesign the embroidery, change the linen into nylon/plastic, or turn it into a tote, pillow, costume, basket, bucket, pouch of another type, banner, shirt, or generic Halloween decoration',
                   'shots': (('Hanging hero',
                              'Bag hanging on light wood peg rail',
                              'Keep the exact bag form and the exact embroidery from the source image. Hang one small linen trick-or-treat candy bag straight on a light wooden hook, peg rail, or hanger, with the bag filling about 70-80 percent of the square frame and the embroidered front facing camera. Use soft clear white window daylight, evenly lighting the entire bag. Shoot straight-on at bag height. Add one mini Halloween bunting or garland beside the bag and tasteful Halloween decor, but do not cover the embroidery, strap, tie, seams, or linen texture.'),
                             ('Child doorway lifestyle',
                              'Child holding bag at bright Halloween door',
                              'Keep the exact bag form, source embroidery, fabric, color, handle or tie, and small realistic scale. A child stands in front of a white door or light wood door with Halloween decor, holding the bag so the embroidered front faces the camera. Use white outdoor shade light with no harsh yellow sun. Shoot at child height from knees upward. Place two or three pumpkins on the doorstep as secondary decor. The bag must stay small and natural in the child hand, never enlarged.'),
                             ('Candy bowl tabletop',
                              'Bag with small candy bowl and mini ghost',
                              'Place the bag in the center beside one small bowl of candy, with only a modest amount of wrapped candy outside the bowl. Use clean bright white daylight so any white or pale linen does not look gray. Shoot from a 45-degree overhead angle. Decorate with orange, black, and purple wrapped candy, a few mini pumpkins, and one small ceramic ghost. Keep the exact source bag form, embroidery placement, thread colors, fabric weave, closure, and small handmade scale.'),
                             ('Porch step lifestyle',
                              'Bag leaning on pumpkin at bright porch',
                              'Keep the exact bag form and exact source embroidery. Place the small Halloween bag on a light-colored porch step, gently leaning against a large pumpkin. Use white outdoor shade light, not warm golden light. Shoot from a low angle at bag height for a real lifestyle feeling. Decorate with white pumpkins, orange pumpkins, dry maple leaves, and one small lantern that is not glowing yellow. The bag must remain small and correctly scaled, not oversized.'),
                             ('Open use flat lay',
                              'Open bag with candy on white wood table',
                              'Keep the exact bag form and embroidery from the source. Lay the bag on a white wood-grain table near a bright window, with the mouth slightly open and a small amount of candy falling out onto the table to show its use. Use even clear white daylight with a little soft sun highlight. Shoot from 60-75 degrees overhead. Add a few candies, mini pumpkins, and a small witch hat as Halloween props, with airy clean spacing and no clutter.'),
                             ('Colorway collection',
                              'Three to five small bags by window',
                              'Keep the source bag construction exactly, especially the one single handle/strap or tie construction; do not add a second strap or extra cords. Arrange three to five bags of the same style but different linen colors on a table beside a window, with the bag straps or ties falling naturally as in real life. If the source visibly has an embroidered name, each bag may use a different plausible name while keeping the same lettering placement and stitch style. Use clear white daylight for accurate fabric colors. Shoot top-down or from a 45-degree angle. Decorate with colorful pumpkins, a toy spider, and a small ghost for a premium Halloween mood.'),
                             ('Process lifestyle',
                              'Woman hand-embroidering Halloween motif',
                              'Show an adult woman sitting at a clean handmade table. One hand holds a small embroidery hoop and the other hand carefully embroiders the same Halloween motif onto linen fabric matching the product color, using a real threaded needle. Include small scissors, thread spools, neatly folded linen, and beautiful white window light. Hands must be anatomically natural, with realistic needle placement and a genuine hand-embroidery action. Add subtle Halloween decor around the craft table without making the scene dark or cluttered.'),
                             ('Process collage',
                              'Four-panel Halloween bag making process',
                              'Create one square 1:1 process collage made of four small photos with soft white light and Halloween mood. Panel 1: a hand selecting fabric in the same product color from many linen rolls. Panel 2: the embroidery design being sketched onto a large linen piece. Panel 3: the colored embroidery finished on fabric inside a small embroidery hoop, with one hand holding the hoop and the other hand holding a threaded needle placed realistically on the hoop, plus embroidery threads as decor. Panel 4: the finished Halloween candy bag matching the exact source product shape, embroidery placement, fabric color, handle or tie, closure, linen texture, handmade wrinkles, and small proportions.'),
                             ('Candy bar setup',
                              'Bag beside airy mini candy bar',
                              'Place the small bag beside a mini candy bar setup, with glass candy jars in the background. Use clean white light and avoid dark reflections on the glass. Shoot from a 45-degree angle. Decorate with two candy jars, two or three mini pumpkins, and one small separate board reading Trick or Treat; the board is a prop only and no new text may appear on the bag. Keep the layout airy, the bag small, and the exact source form, embroidery, linen texture, strap or tie, and scale unchanged.'),
                             ('Walking child lifestyle',
                              'Child walking with bag on bright path',
                              'Keep the exact bag form and source embroidery. A child in a simple Halloween outfit holds the small bag while walking on a light-colored path. The bag is in the foreground and the child face does not need to be clear. Use white daytime shade light. Shoot from a low angle at bag height so the bag looks genuinely in use. Add a few pumpkins near a porch in the blurred background. The bag must not be enlarged or exaggerated.'),
                             ('Three children doorway',
                              'Three children knocking on door with bags',
                              'Do not change the bag form or design. Show three children in simple Halloween outfits, each holding a small bag in the same exact source style, with different linen colors and different embroidered names only if the source contains a personalized name. The three children are knocking on a house door. Use white daytime shade light. Shoot around bag height so the bags look genuinely used. Add a few pumpkins near the porch and keep the background softly blurred. Every bag must stay small, not oversized, and preserve the source embroidery layout and handmade construction.'),
                             ('Sibling set lifestyle',
                              'Two or three personalized bags in living room',
                              'Keep the correct bag form and source design. Photograph two or three small personalized Halloween bags held by children sitting together in a bright living room with tasteful Halloween decor. Use even fresh white daylight. Shoot straight-on, or top-down if focusing mainly on the bags. Decorate with mini pumpkins, a small amount of candy, and a clean white background. The concept should suggest buying matching bags for siblings. Bags must stay very small and natural, not enlarged.'),
                             ('Costume flat lay',
                              'Bag beside child costume on bed',
                              'Place the small bag beside a child Halloween costume laid on a bed. Use even white overhead light. Shoot a close 90-degree flat lay near the product. Add one small magic wand or bat-ear headband, mini pumpkins, and a toy spider around the scene for a Halloween mood. The bag must be smaller than the costume and must not look as large as the clothing. Preserve the exact source embroidery, fabric color, handle or tie, seams, wrinkles, and small handmade scale.'),
                             ('Embroidery detail collage',
                              'Four-panel macro close-up of embroidery',
                             'Create one square 1:1 detail collage made of four close-up photos of the embroidery on the same Halloween bag. Each panel must prove the source embroidery is preserved: raised hand stitches, thread direction, thread color, motif edges, linen weave, seam or tie detail where useful, natural wrinkles, and handmade texture. The collage must match the source motif and fabric exactly; do not redesign the embroidery, add new icons, add text, or show a different product.'))},
 'pc_stocks': {
     'display_name': 'PC Stocks',
     'aliases': (
         'PC Stocks',
         'pc stocks',
         'PC Stock',
         'pc stock',
         'PC Stocking',
         'pc stocking',
         'Punch Needle Stocking',
         'punch needle stocking',
         'Punch Needle Christmas Stocking',
         'punch needle christmas stocking',
         'Christmas Punch Needle Stocking',
         'embroidered Christmas stocking',
         'Christmas embroidered stocking',
         'Christmas stocking punch needle',
         'tat noel punch needle',
         'tat giang sinh punch needle',
     ),
     'target_count': 12,
     'lock': (
         'the main product must remain the exact same compact Punch Needle Christmas stocking from the source image, '
         'with the same stocking silhouette, cuff, toe direction, heel curve, hanging loop, fabric and color, seams, '
         'embroidery motif and placement, yarn colors, and thick raised wool punch-needle loop texture. It is a flat '
         'one-sided decorative stocking panel with no storage cavity, pocket, usable opening, or ability to hold objects'
     ),
     'shots': (
         ('Christmas tree hero',
          'Stocking hanging on real Christmas tree branch',
          _pc_stocks_brief(
              'hang the exact stocking from a real Christmas tree branch beside silver baubles and a red bow. Use bright '
              'natural window light that feels clear and airy with no yellow cast. Create a vivid festive atmosphere '
              'while keeping the complete stocking silhouette and the exact source motif sharply visible.'
          )),
         ('Process lifestyle',
          'Woman punch-needling matching motif in round hoop',
          _pc_stocks_brief(
              'create an Etsy-style handmade process scene with an adult woman seated at a light wooden table, carefully '
              'using a large punch needle with a wooden handle to stitch the exact source stocking motif onto matching '
              'fabric stretched in a round embroidery hoop. The punch needle must visibly carry wool yarn at its working '
              'end, and the yarn color must match the precise area being stitched. Show natural anatomically correct '
              'hands, realistic tool contact, bright crystal-clear natural light, and a few small Christmas accessories.'
          )),
         ('Hanging lifestyle',
          'Hand hanging stocking on elegant wooden wall hook',
          _pc_stocks_brief(
              'show one natural hand hanging the exact stocking from an elegant wooden wall hook. Arrange vivid '
              'Christmas accessories on nearby hooks without covering the product. Use clear airy natural daylight with '
              'no yellow cast and keep the source punch-needle motif crisp, raised, and fully visible.'
          )),
         ('Staircase lifestyle',
          'Stocking on white wooden staircase garland',
          _pc_stocks_brief(
              'hang the exact stocking from a white wooden staircase banister wrapped with a lush evergreen garland, '
              'large red velvet bows, and restrained sparkling white lights. Create a luxurious lifestyle composition '
              'with clean bright white-balanced light, no yellow cast, and sharp focus on the unchanged source motif.'
          )),
         ('Gift presentation',
          'Stocking inside premium white Christmas gift box',
          _pc_stocks_brief(
              'place the exact Christmas stocking neatly inside a premium white Christmas gift box, surrounded by vivid '
              'but refined festive accessories. Keep the whole stocking shape, cuff, hanging loop, and source motif '
              'visible rather than buried under tissue. Use crystal-clear airy light with no yellow tone.'
          )),
         ('Mantel lifestyle',
          'Stocking hanging from small fireplace mantel hook',
          _pc_stocks_brief(
              'hang the exact Punch Needle stocking from a small discreet hook attached to a fireplace mantel. Decorate '
              'the mantel with lush green pine garland, red and gold baubles, and sparkling white LED lights. Keep the '
              'lighting bright, clean, airy, and neutral without a yellow cast, with the stocking as the sharp focal point.'
          )),
         ('Flat lay',
          'Festive flat lay with pinecones ribbon and candy cane',
          _pc_stocks_brief(
              'create a top-down flat lay of the exact stocking among a restrained basket-style arrangement of festive '
              'accessories: gold pinecones, green pine branches, red ribbon, and candy canes. Use clear airy neutral '
              'daylight with no yellow tone and emphasize the thick raised punch-needle texture from the source.'
          )),
         ('Room lifestyle',
          'Premium modern Christmas living room',
          _pc_stocks_brief(
              'feature the exact stocking prominently in a modern, vivid, elaborately decorated Christmas living room. '
              'Use premium lifestyle photography, a spacious composition, crystal-clear white-balanced daylight, and no '
              'yellow cast. Keep the stocking larger and sharper than the surrounding decor without changing its real size.'
          )),
         ('Door lifestyle',
          'Stocking hanging from white bedroom door handle',
          _pc_stocks_brief(
              'hang the exact embroidered Christmas stocking from the handle of a white bedroom door. Let clean natural '
              'hallway light enter the scene and add gentle restrained Christmas decorations. Keep the setting bright, '
              'airy, and free of yellow tones, with the complete stocking and source motif in sharp focus.'
          )),
         ('Colorway collection',
          'Three colorways on elegant wooden wall hooks',
          _pc_stocks_brief(
              'show exactly three stockings hanging side by side on elegant wooden wall hooks against a cream-white wall. '
              'Use one navy stocking, one forest-green stocking, and one deep-red stocking. All three must preserve the '
              'identical source silhouette, construction, embroidery motif, motif placement, scale, and yarn colors; only '
              'the base stocking fabric color changes. Add minimal premium Christmas decor and one-sided crystal-clear '
              'light with soft shadows, absolutely no yellow cast.'
          )),
         ('Multi-piece collection',
          'Five stocking colorways in festive flat lay',
          _pc_stocks_brief(
              'create a premium top-down collection photograph of exactly five flat one-sided decorative stockings '
              'arranged in a clean fan-shaped composition on a light neutral wooden surface. Use five visibly different '
              'base fabric colorways: natural ivory, dusty pink, soft sage green, navy blue, and deep Christmas red. Every '
              'stocking must keep the exact same source silhouette, compact dimensions, white cuff construction, toe '
              'direction, heel curve, hanging loop, seams, embroidery motif, motif placement, yarn colors, and thick '
              'raised punch-needle texture; only the base fabric color may differ. Add restrained pine sprigs, red ribbon, '
              'and a few matte baubles around the outer edges without covering any stocking. Use bright clear airy '
              'white-balanced daylight, no yellow cast, no text, no measurement arrows, and no infographic elements.'
          )),
         ('Flat construction detail',
          'Hand-held close-up showing flat one-sided construction',
          _pc_stocks_brief(
              'create a close product-inspection photograph with one natural hand holding the exact decorative stocking '
              'by its hanging loop while a second hand lightly supports the toe edge. Keep the embroidered front facing '
              'the camera and use a slight side angle that clearly proves the product is a thin, flat, one-sided '
              'decorative panel with stitched edges and no opening, pocket, interior cavity, or storage function. Place '
              'small wrapped gifts and candy canes only on a table in the softly blurred background, never inside or '
              'touching the stocking. Use bright clear airy natural daylight, absolutely no yellow cast, and tack-sharp '
              'focus on the cuff, edge seams, fabric weave, and raised punch-needle loops.'
          )),
     ),
 },
 'ornament_round': {'display_name': 'Ornament Round',
                    'aliases': ('Ornament_Round',
                                'Ornament Round',
                                'ornament round',
                                'round ornament',
                                'Christmas ornament',
                                'Christmas embroidered ornament',
                                'embroidered Christmas ornament',
                                'linen Christmas ornament',
                                'round Christmas ornament',
                                'hand embroidered ornament',
                                'embroidery hoop ornament',
                                'mini hoop ornament',
                                'Noel ornament',
                                'Christmas tree ornament',
                                'do treo cay thong',
                                'do trang tri giang sinh tron',
                                'ornament giang sinh'),
                    'target_count': 14,
                    'allow_planned_multi_panel_shots': True,
                    'allow_planned_prop_text': True,
                    'lock': 'the main product must remain the exact same small round hand-embroidered Christmas linen ornament from the source image, with the same round wooden hoop/frame, metal clasp or fastener if visible, linen fabric and color, hanging cord or ribbon, embroidery motif, embroidery placement, embroidery scale, thread colors, raised hand-stitch texture, fabric weave, natural wrinkles, proportions, and premium handmade Christmas identity; never enlarge it into a wall hoop, redesign or simplify the embroidery, change the frame or hanging construction, make the stitches look printed or machine-flat, or turn it into a bag, pillow, banner, coaster, plaque, or generic Christmas decoration',
                    'shots': (('White wood flat lay',
                               'Round ornament on white wood table with pine branch',
                               _ornament_round_brief('lay the ornament flat at the center of a white wood-grain tabletop, with its hanging cord curving naturally to one side. Shoot top-down at exactly 90 degrees with even white overhead daylight. Place one small evergreen branch in the lower-left or lower-right corner, a few white wooden snowflakes, and a restrained strand of softly blurred warm fairy lights as secondary Christmas props. Keep the composition airy and make the hand-stitched thread texture unmistakable, never printed or machine embroidered.')),
                              ('Christmas tree hero',
                               'Ornament hanging on fresh Christmas tree branch',
                               _ornament_round_brief('hang the ornament at the center of a fresh Christmas tree branch so it stands out clearly among the pine needles. Use soft white balanced daylight and keep tree lights from becoming strongly yellow. Shoot at ornament height from a 30-45 degree angle. Add a few baubles and softly blurred fairy lights in the background while keeping the complete round frame, hanging cord, clasp, linen face, and embroidery sharply visible.')),
                              ('Open gift box',
                               'Ornament presented inside open Christmas gift box',
                               _ornament_round_brief('present the ornament inside an open Christmas-toned gift box lined with clean tissue paper. Use bright clean luxurious white daylight and shoot from a 35-45 degree angle. Add deep red or champagne ribbon, a few small pine sprigs, dried orange slices, cinnamon sticks, and several softly blurred gift boxes in the background. Do not hide the frame, clasp, cord, linen, or embroidery beneath the packaging.')),
                              ('Minimal Christmas table',
                               'Ornament in refined candle and pinecone setting',
                               _ornament_round_brief('place the ornament lying flat or standing securely at the center of a minimal Christmas tabletop scene. Use soft even white daylight rather than candle-yellow light and shoot from a frontal 45-degree angle. Decorate with two low unlit or neutrally lit candles, a few small pinecones, several pastel matte baubles, and one evergreen sprig. Keep every prop secondary and the embroidery crisp and tactile.')),
                              ('Christmas card flat lay',
                               'Ornament beside neutral Merry Christmas card',
                               _ornament_round_brief('place the ornament as the main focal point beside one neutral-toned greeting card whose only readable prop text is Merry Christmas, on a white wood-grain tabletop. Shoot top-down from 75-90 degrees with clean even white daylight. Add a thin ribbon, one small gnome, and a small evergreen branch in the upper-left corner. The greeting card is a separate prop and must not touch or cover the ornament; add no other writing, label, tag, logo, or text overlay.')),
                              ('Baby keepsake shelf',
                               'Ornament with folded baby clothes by bright window',
                               _ornament_round_brief('place the ornament on a white wood-grain shelf or tabletop beside several neatly folded baby outfits near a bright window. Use soft clear white daylight and shoot top-down or at 45 degrees. Keep a softly blurred Christmas background and add one small gnome teddy, a Christmas stocking, and a small reindeer figure in a very tidy arrangement. Keep the ornament small and correctly scaled relative to the clothing.')),
                              ('Hand embroidery process',
                               'Woman stitching ornament motif at craft table',
                               _ornament_round_brief('show an adult woman seated at a clean handmade craft table. One anatomically natural hand holds a small embroidery hoop containing linen that matches the product color, while the other hand carefully stitches the exact source motif with a realistically threaded embroidery needle at a believable contact point. Add small scissors, thread spools, neatly folded linen, beautiful window light, and subtle Christmas decor. The finished source ornament may sit nearby as a clear reference product, but do not change its design.')),
                              ('Making process collage',
                               'Four-panel Christmas ornament making process',
                               _ornament_round_brief('create one square 1:1 four-panel process collage with soft clean light and a Christmas atmosphere. Panel 1: a hand selects fabric matching the source product color from several linen rolls. Panel 2: the exact embroidery motif is sketched but not yet stitched on a large linen piece. Panel 3: the motif is stitched in color inside a small hoop, with one hand holding the hoop and the other holding a realistically threaded needle at the stitch point, plus embroidery threads nearby. Panel 4: the completed ornament matches the exact source round frame, clasp, hanging cord, linen color, motif, placement, scale, and raised handmade stitches.')),
                              ('Personalized collection',
                               'Three to five round ornaments arranged as a set',
                               _ornament_round_brief('arrange three to five ornaments of the exact same physical style in a horizontal row or gentle fan on a white wood-grain tabletop. If the source visibly contains a personalized name, use a different plausible name on each ornament while preserving the exact lettering position, scale, thread style, motif, frame, clasp, and hanging construction; if the source has no name, invent no text. Use very even white daylight and shoot top-down at 90 degrees or from a light 60-degree angle. Add one long thin pine sprig, dried orange slices, and a few holly branches with a softly blurred Christmas background.')),
                              ('Gift wrapping flat lay',
                               'Ornament beside organized Noel gift wrapping',
                               _ornament_round_brief('place the ornament beside a neat Noel gift-wrapping setup on a clean surface. Use crisp white daylight and shoot top-down from 60-75 degrees or at a slight angle. Include white or cream wrapping paper, scissors, ribbon, and one plain textless gift tag as secondary props. Keep the layout orderly and ensure the ornament embroidery, frame, clasp, linen weave, and cord remain fully visible.')),
                              ('Mini tree lifestyle',
                               'Ornament foreground with fresh mini tree behind',
                               _ornament_round_brief('place the ornament prominently in the foreground with a fresh mini Christmas tree in the left or right background. Use bright white daylight so both remain clear while the ornament stays the sharper subject. Shoot straight-on or from a 30-degree angle. Add two or three tiny bells, red berries, and a small amount of softly blurred fairy light. Keep the product small, complete, and correctly proportioned.')),
                              ('One-year-old Christmas lifestyle',
                               'One-year-old baby holding small ornament by tree',
                               _ornament_round_brief('show a roughly one-year-old baby wearing a Christmas outfit and Santa hat, seated beside a Christmas tree and naturally holding the ornament. Use cozy but white-balanced soft daylight with tasteful Christmas decor. The ornament must remain genuinely small relative to the baby hand and body, never enlarged, and its embroidered front should face the camera without being covered. Keep baby hands anatomically natural.')),
                              ('Bookshelf lifestyle',
                               'Ornament resting on neutral books with pine and orange',
                               _ornament_round_brief('rest the ornament against one or two white or pale neutral hardcover books for a warm premium Christmas lifestyle scene. Use soft clean white daylight reflecting naturally from the paper and shoot from a 30-45 degree angle. Add one frosted glass bauble, one evergreen sprig, dried orange slices, and cinnamon sticks. Keep the ornament as the dominant sharp subject and do not use beige or yellow color grading.')),
                              ('Construction detail collage',
                               'Four-panel macro of embroidery frame and clasp',
                               _ornament_round_brief('create one square 1:1 collage containing exactly four macro close-up photos of the same source ornament: raised embroidery and individual thread fibers, linen weave and stitch edges, wooden hoop/frame material and edge finish, and the metal clasp or fastener plus hanging-cord attachment. Every panel must match the original product exactly and prove genuine hand embroidery rather than print or machine-flat stitching. Do not add new motifs, text, hardware, or a different ornament.')))},
 'drawstring_bag': {'display_name': 'Drawstring Bag',
                    'aliases': ('Drawstring Bag',
                                'drawstring bag',
                                'drawstring pouch',
                                'linen drawstring bag',
                                'cotton linen drawstring bag',
                                'embroidered drawstring bag',
                                'embroidered pouch',
                                'linen pouch',
                                'cotton pouch',
                                'jewelry pouch',
                                'gift pouch',
                                'túi rút dây',
                                'tui rut day',
                                'túi dây rút',
                                'tui day rut',
                                'túi rút',
                                'tui rut',
                                'túi vải rút',
                                'tui vai rut'),
                    'lock': 'the main product must remain the same cotton linen drawstring bag/pouch with the exact '
                            'soft rectangular pouch silhouette, gathered drawstring top, cotton rope cords and knots, '
                            'linen weave, fabric color, front embroidery placement, embroidery scale, thread colors, '
                            'natural wrinkles, seams, soft volume, and premium handmade identity from the source image; '
                            'the drawstring cord color must match the source reference',
                    'shots': (('Kitchen product display',
                               'Túi đứng trong giỏ gia vị',
                               'Show one single cotton linen drawstring bag standing naturally in the center of a '
                               'beautiful spice basket on a clean kitchen cooking table. Use refined kitchen decor such '
                               'as small spice jars, wooden spoons, pale wood, linen cloth, and dried herbs. The front '
                               'embroidery must face the camera clearly, with the drawstring top, cotton cords, knots, '
                               'linen texture, soft pouch volume, and natural wrinkles preserved exactly from the '
                               'reference. Use clean bright white daylight and premium Etsy handmade styling.'),
                              ('Jewelry use scene',
                               'Miệng túi mở nhẹ có trang sức',
                               'Place one drawstring bag in the center with the mouth gently opened just enough to show '
                               'a few small jewelry pieces inside, such as a bracelet, ring, or pearl necklace. Use a '
                               'white or cream linen background and a small handmade ceramic tray to suggest function. '
                               'Shoot from a soft 45-60 degree overhead angle with clear white daylight. Keep the same '
                               'bag shape, cord color, gathered top, embroidery position, fabric weave, and thread colors '
                               'from the source image; jewelry is secondary and must not cover the embroidery.'),
                              ('Flat lay',
                               'Túi xẹp tự nhiên trên khăn linen',
                               'Lay one drawstring bag naturally flattened on a light linen cloth in a premium flat lay. '
                               'Let the cotton drawstrings fall softly and visibly. Add tasteful craft props such as '
                               'small scissors, embroidery needle, fabric-covered notebook, dried flowers, and cotton '
                               'cord. The camera must show the fabric texture, hand embroidery relief, seams, and natural '
                               'soft wrinkles clearly. Do not redesign the bag or move the embroidery.'),
                              ('Colorway pair',
                               'Hai túi trên khay trang sức gỗ',
                               'Show two drawstring bags with the same form as the reference, placed side by side on a '
                               'wooden jewelry tray on a dressing table. The two bags may use different linen base colors, '
                               'but the embroidery motif, thread colors, embroidery layout, cord color, drawstring '
                               'construction, seams, and pouch proportions must stay the same as the source. Add refined '
                               'skincare props, flowers, and a clean vanity setting without clutter.'),
                              ('Tabletop storage set',
                               'Ba túi đứng trong khay gỗ sáng',
                               'Show three drawstring bags standing upright together in a shallow light wooden tray on a '
                               'clean bright kitchen or craft table. Do not hang the bags from any hook, rail, peg, wall, '
                               'or drawstring cord. Use soft fabric color variety only for the base fabric while '
                               'preserving the source embroidery, cord color, cord thickness, knots, gathered top, seam '
                               'construction, and pouch proportions. Include folded linen, small dried flowers, wicker '
                               'texture, and soft window light; every bag must rest naturally on the tray or tabletop.'),
                              ('Colorway group',
                               'Bốn túi trên bàn trắng vân gỗ',
                               'Arrange four drawstring bags as a natural group on a white wood-grain table. Each bag may '
                               'have a different fabric color, but all must keep the exact source pouch form, same '
                               'embroidery motif and thread palette, same drawstring cord color, same gathered top, and '
                               'same handmade linen texture. Decorate lightly with a white ceramic vase, linen cloth, '
                               'craft book, and dried branches.'),
                              ('Detail collage',
                               'Bốn ảnh nhỏ cận cảnh thêu',
                               'Create one square detail collage made of four small close-up photos, each showing a '
                               'different macro angle of the embroidery and cotton linen texture on the same drawstring '
                               'bag. The panels must show raised hand stitches, thread direction, tactile thread fibers, '
                               'linen weave, seam or drawstring-channel detail where useful, and natural fabric texture. '
                               'This is a detail-proof collage only; do not create a product colorway grid or redesign '
                               'the embroidery.'),
                              ('Process lifestyle',
                               'Tay thêu trên khung thêu nhỏ',
                               'Show an adult woman sitting at a handmade craft table, carefully embroidering the same '
                               'motif onto a piece of fabric matching the drawstring bag color, using a small embroidery '
                               'hoop, needle with thread, small scissors, thread spools, folded linen, and beautiful '
                               'window light. Hands must be natural and anatomically correct, with a realistic needle '
                               'position. This is a making-process scene; the finished product must still be understood '
                               'as a cotton linen drawstring bag, not a hoop product.'),
                              ('Basket lifestyle',
                               'Túi trong giỏ mây nhỏ',
                               'Place one drawstring bag in a small wicker basket on a light wood table. Use refined '
                               'decor such as linen cloth, small ceramic vase, white candle, dried flowers, and a '
                               'fabric-covered book. The front embroidery must be visible and sharp, with clean white '
                               'daylight and a soft premium handmade mood. Preserve the source bag shape, cords, fabric, '
                               'embroidery scale, and natural wrinkles.'),
                              ('Family lifestyle',
                               'Em bé đưa túi cho mẹ',
                               'Create a bright living-room lifestyle photo where a baby or young child hands the '
                               'drawstring bag to the mother, with small items inside so the pouch has gentle natural '
                               'volume. Keep the scene safe, clean, airy, and premium. Faces can be cropped or secondary. '
                               'The bag must remain the focal product, with its front embroidery visible and not covered '
                               'by hands; preserve cord color, gathered top, pouch form, and stitch texture.'),
                              ('Use detail',
                               'Tay phụ nữ bỏ đồ nhỏ vào túi',
                               'Show an adult woman hand placing small items into the drawstring bag. Use airy premium '
                               'light, soft neutral tabletop styling, and focus on the bag opening, cords, and embroidery. '
                               'The bag may look slightly fuller from the contents, but the source shape, fabric weave, '
                               'drawstring color, embroidery placement, and thread details must not change. Hands must '
                               'be natural with no extra fingers.'),
                              ('Gift presentation',
                               'Túi xẹp nhẹ trong hộp quà mở',
                               'Place one drawstring bag neatly inside a small open paper gift box. The bag should be '
                               'slightly flattened or gently folded, not overly inflated, with the embroidered front '
                               'facing upward and clearly visible. Use a small minimal light-colored box and very light '
                               'decor such as linen cloth or pale paper background. Do not place anything on top of the '
                               'bag or cover the embroidery; preserve the source fabric, cords, stitches, and handmade '
                               'identity.'))},
 'fabric_cross': {'display_name': 'Fabric Cross',
                  'aliases': ('Fabric Cross',
                              'fabric cross',
                              'soft cross',
                              'linen cross',
                              'baby cross',
                              'cross keepsake',
                              'thánh giá vải',
                              'thanh gia vai'),
                  'lock': 'the main product must remain the same soft fabric cross keepsake with the exact cross '
                          'shape, stitched edge, fabric texture, embroidery/name placement, scale, and gentle baby '
                          'keepsake identity from the source image',
                  'shots': (('Lifestyle',
                             'Baby cầm 2 tay',
                             'Life photography: A baby gently cradles the fabric cross from the reference image with '
                             'both hands, while relaxing in a cozy, neutral-toned nursery or soft home space. The warm '
                             'and natural interaction makes the fabric cross the primary emotional focal point. Soft '
                             'natural light from the window, warm cream and beige tones, a clean, minimalist '
                             'background with soft blankets, knitwear, and subtle details of the nursery create a '
                             'slightly blurred effect. The shallow depth of field gives a gentle, ethereal feel, '
                             'evoking a sense of delicate handcrafted keepsake—a high-end life photography perfect for '
                             'Etsy.\n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of the fabric cross from the reference image. Keep '
                             'the shape, size, proportions, fabric material, embroidery design, thread color, '
                             'stitching details, loop placement, and craftsmanship characteristics. Do not modify the '
                             'fabric cross in any way—only create a new context around it. Keep the fabric cross '
                             'clearly visible and easily recognizable, with the baby holding it naturally without '
                             'obscuring too much detail.\n'
                             '\n'
                             'STYLE: Handmade lifestyle product photography, soft natural lighting, editorial quality, '
                             'modern minimalist Etsy aesthetic, 1:1 square aspect ratio.\n'
                             '\n'
                             'AVOID: overly harsh studio lighting, cluttered background, unrealistic baby anatomy, '
                             'excessive posing interaction, mass-produced images, AI errors, text overlays, '
                             'watermarks.'),
                            ('Product display',
                             'Tựa gấu teddy + chăn len',
                             'The fabric cross, taken from a reference image, is positioned upright and gently resting '
                             'against a soft teddy bear in a cozy nursery setting, on a cream-colored wool blanket '
                             'with a few dried flowers or delicate botanical details scattered naturally around. Warm '
                             'natural light diffuses from the window, the gentle beige and ivory tones, the slightly '
                             'muted minimalist background, the central composition with the fabric cross as the clear '
                             'focal point, and the shallow depth of field create a soft, hazy effect, giving it a '
                             'delicate, handcrafted keepsake feel—a high-end product photo for Etsy.\n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of the fabric cross from the reference image. Keep '
                             'the shape, size, proportions, fabric material, embroidery design, thread color, '
                             'stitching details, loop placement, any personalized text, and handcrafted '
                             'characteristics. Do not modify the fabric cross in any way—only create a new setting '
                             'around it. The teddy bear and surrounding props should support the composition without '
                             'obscuring the fabric cross too much.\n'
                             '\n'
                             'STYLE: Handmade product photography, soft natural lighting, editorial quality, modern '
                             'minimalist Etsy aesthetic, 1:1 square aspect ratio.\n'
                             '\n'
                             'AVOID: overly harsh studio lighting, cluttered background, retouched embroidery, '
                             'mass-produced look, unrealistic textures, AI errors, text overlays, watermarks.'),
                            ('Product display',
                             'Treo mobile cũi gỗ',
                             'Product photo of the fabric cross, taken from a reference image, hanging on a natural '
                             'wood crib mobile in a bright, cozy nursery, displayed above a soft, neutral-colored crib '
                             'with cream-colored bedding and a light pastel duvet. The minimalist, clean layout '
                             'features the fabric cross as the main focal point, soft natural light from the side '
                             'window, warm ivory and beige tones, a slightly blurred nursery background, a few dried '
                             'grasses or soft natural decorations nearby, and a shallow depth of field creating a '
                             'soft, ethereal effect, giving the image a gentle, handcrafted keepsake feel – a high-end '
                             'product photo for Etsy.\n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of the fabric cross from the reference image. Keep '
                             'the shape, size, proportions, fabric material, embroidery design, thread color, '
                             'stitching details, hanging loop placement, any personalized text, and handcrafted '
                             'characteristics intact. Do not modify the fabric cross in any way—only create a new '
                             'context around it. Crib mobiles and other elements in the nursery should support the '
                             'layout without obscuring or distracting attention from the fabric cross.\n'
                             '\n'
                             'STYLE: Handmade product photography, soft natural lighting, editorial photo quality, '
                             'modern minimalist Etsy-style aesthetic, 1:1 square aspect ratio.\n'
                             '\n'
                             'AVOID: Harsh studio lighting, cluttered nursery backgrounds, edited embroidery, '
                             'unrealistic crib proportions, mass-produced look, AI errors, text overlays, watermarks.'),
                            ('Product display',
                             'Trên tay nắm cửa gỗ',
                             'This product photo of a fabric cross, taken from a reference image, hangs neatly on a '
                             "round wooden doorknob in a bright, quiet children's room or a lightly decorated home "
                             'interior. The fabric cross is displayed naturally against a light oak door frame, with a '
                             "minimalist children's room backdrop that is subtly blurred, such as a white wardrobe, "
                             'neutral-colored wall art, or sheer curtains in the distance. The soft natural light from '
                             'the window, the warm ivory, beige, and light wood tones, the neat composition with the '
                             'fabric cross as the clear focal point, and the shallow depth of field create a gentle, '
                             'hazy effect, giving it a delicate, handcrafted feel—a high-end product photo for Etsy. \n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of the fabric cross from the reference image. Keep '
                             'the shape, size, proportions, fabric material, embroidery design, thread color, '
                             'stitching details, hanging loop placement, any personalized text, and handcrafted '
                             'characteristics intact. Do not modify the fabric cross itself in any way — just create a '
                             'new background around it. This guide applies to any fabric cross design, so keep the '
                             'embroidery, colors, and personalization as they are in the reference image. \n'
                             '\n'
                             'STYLE: Handcrafted product photography, soft natural lighting, editorial image quality, '
                             'modern minimalist Etsy-style aesthetic, 1:1 square aspect ratio. \n'
                             '\n'
                             'AVOID: Harsh studio lighting, cluttered background, edited embroidery, unrealistic door '
                             'or room proportions, mass-produced look, AI errors, text overlays, watermarks.'),
                            ('Product display',
                             '2 cross trên chăn dệt',
                             'The product image displays two fabric crosses from the reference photo, elegantly '
                             'arranged on a richly textured knitted blanket, topped with a soft linen overlay, '
                             'surrounded by a small bundle of dried eucalyptus leaves and scattered eucalyptus '
                             'branches arranged naturally. The two fabric crosses are placed side-by-side in a '
                             'balanced composition, gently illuminated by warm sunlight to create a tranquil, '
                             'handcrafted atmosphere. The image is clean, cozy, artistic with a shallow depth of field '
                             'and soft, natural shadows – a high-quality product photo on Etsy. \n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of both fabric crosses from the reference photo. '
                             'Preserve the shape, size, proportions, fabric texture, embroidery style, thread color, '
                             'stitching details, ribbon placement, and handcrafted characteristics. \n'
                             '\n'
                             'STYLE: Handcrafted product photography, soft natural lighting, edited image quality, '
                             'modern minimalist aesthetic in the Etsy style, 1:1 square aspect ratio. \n'
                             '\n'
                             'AVOID: Harsh studio lighting, cluttered backgrounds, embroidery editing, unrealistic '
                             'materials, mass-produced look, AI errors, text overlays, watermarks.'),
                            ('Lifestyle',
                             'Candid bé cầm 1 tay',
                             'A candid photo of a baby holding a fabric cross from the reference image in one hand, '
                             'while gently holding a bouquet of flowers in the other. The baby is wearing a simple, '
                             'light-colored dress and standing in a church. The fabric cross is clearly visible, with '
                             'its prominent hand-embroidered details. Soft natural light from the window creates a '
                             'quiet, warm atmosphere, with a shallow depth of field that subtly blurs the background, '
                             "emphasizing the fabric cross as the main focal point. The baby's face is not visible, "
                             'and the composition conveys a gentle, sentimental mood of a handcrafted gift, perfect '
                             'for a high-quality photo on Etsy.\n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of the fabric cross from the reference image. Keep '
                             'the shape, size, proportions, fabric material, embroidery style, thread color, stitching '
                             'details, hook placement, any personalized text, and handcrafted characteristics. Do not '
                             'modify the fabric cross itself in any way—only create a new setting around it. The baby '
                             'should interact naturally with the fabric cross, without obscuring any of its details.\n'
                             '\n'
                             'STYLE: Lifestyle-inspired handcrafted product photography, soft natural lighting, '
                             'editorial quality, modern minimalist Etsy-style aesthetic, 1:1 square aspect ratio.\n'
                             '\n'
                             'AVOID: Harsh studio lighting, cluttered backgrounds, unrealistic baby anatomy, excessive '
                             'posing, mass-produced stuffed toy appearance, AI errors, text overlays, watermarks.'),
                            ('Quy trình',
                             'Quy trình — 4 ảnh nhỏ',
                             'This set of four small photos documents the process of creating a fabric cross:\n'
                             '\n'
                             'The first image shows a pencil sketch of the cross on linen fabric the same color as the '
                             'sample cross, with the pattern and embroidery clearly visible in the background.\n'
                             '\n'
                             'The second image shows the embroidery thread being threaded through the needle, '
                             'preparing for embroidery.\n'
                             '\n'
                             'The third image shows the embroidery process on an embroidery frame, with the details of '
                             'the meticulous embroidery design clearly visible.\n'
                             '\n'
                             'The fourth image shows the finished fabric cross hanging on a soft ribbon, with the '
                             'perfect embroidery and the finished product prominently displayed, gently placed on a '
                             'soft surface with dried reeds and a clean backdrop.\n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of the fabric cross as in the reference images. '
                             'Preserve the shape, size, proportions, fabric material, embroidery pattern, thread '
                             'color, embroidery details, loop placement, and any personalized text. What are the '
                             'details and craftsmanship? Do not modify the fabric cross itself in any way—only '
                             'describe the creation process and the new context surrounding it.\n'
                             '\n'
                             'STYLE: Handcrafted product photography, soft natural lighting, editorial image quality, '
                             'modern minimalist Etsy style. Beautiful images, 1:1 square aspect ratio.\n'
                             '\n'
                             'AVOID: Incorrect embroidery placement, overly forced hand posture, blurry embroidery, '
                             'disproportionate proportions, overly cluttered background, AI errors, text overlapping '
                             'the image, blurry images.'),
                            ('Product display',
                             'Product — Khung cảnh nursery',
                             'This product photo of a fabric cross, based on a reference image, is shown standing '
                             'upright on a rustic wooden table with several classic wooden letter blocks surrounding '
                             'it. The fabric cross stands out as the main focal point, with its embroidered motif. '
                             'Nearby, a small potted succulent, some natural wool yarn, and a soft woven basket can be '
                             'seen in the background, creating a cozy and rustic atmosphere. Warm, gentle natural '
                             'sunlight shines from the side, creating soft shadows and highlighting the handcrafted '
                             'texture of the fabric cross. The minimalist composition and shallow depth of field '
                             'create a subtle blurring effect in the background, making it a high-quality product '
                             'photo for Etsy.\n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of the fabric cross from the reference image. Keep '
                             'the shape, size, proportions, fabric texture, embroidery design, thread color, stitching '
                             'details, hook placement, any personalized text, and handcrafted characteristics intact. '
                             'Do not modify the fabric cross itself in any way—only create a new context around it. '
                             'The surrounding items should highlight the natural beauty and handcrafted quality of the '
                             'cross without obscuring or distracting from it.\n'
                             '\n'
                             'STYLE: Handcrafted product photography, soft natural lighting, editorial quality, modern '
                             'minimalist Etsy-style aesthetic, 1:1 square aspect ratio.\n'
                             '\n'
                             'AVOID: Harsh studio lighting, cluttered backgrounds, heavily edited embroidery, '
                             'mass-produced look, unrealistic textures, AI errors, text overlays, watermarks.'),
                            ('Cận thêu tay',
                             'Cận thêu tay',
                             'Take a close-up photograph of the fabric cross from the reference image, focusing on the '
                             'exquisite hand-embroidered details, with clearly defined threads and beautiful '
                             'stitching. The fabric cross should be the main focal point, highlighting the embroidery '
                             'and stitching. Soft, natural light from the side will emphasize the depth of the '
                             'embroidery, with a shallow depth of field to create a hazy effect around the fabric. The '
                             'fabric should be neutral and clean, and the handcrafted details must be clearly visible, '
                             'emphasizing the quality of the product.\n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of the fabric cross from the reference image. '
                             'Preserve the fabric, embroidery details, thread color, stitching, proportions, and '
                             'handcrafted characteristics. Do not alter the cross in any way—only enlarge the existing '
                             'embroidery details.\n'
                             '\n'
                             'STYLE: Close-up photos of handcrafted products, soft natural lighting, high-quality '
                             'editing, modern minimalist Etsy-style aesthetics, 1:1 square aspect ratio.\n'
                             '\n'
                             'AVOID: blurry seams, images that look like they were created by machines, edited '
                             'embroidery patterns, harsh lighting, overexposed highlights, AI errors, text overlaid on '
                             'images, watermarks.'),
                            ('Lifestyle',
                             'Candid bé + cross #2',
                             'A candid photograph of a fabric cross from a reference image, gently cradled in the '
                             'hands of an adult beside a sleeping baby in a cozy, softly lit nursery. The exquisitely '
                             "embroidered fabric cross stands out in the adult's hands, its delicate stitching "
                             'highlighting the intricate details. The soft crib and bedding in the background are '
                             'subtly blurred, creating a tranquil and peaceful atmosphere. Gentle natural light from '
                             'the window illuminates the fabric cross, creating a warm, tender mood perfect for a '
                             'handcrafted commemorative photograph.\n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of the fabric cross from the reference image. Keep '
                             'the shape, size, proportions, fabric material, embroidery style, thread color, stitching '
                             'details, placement of the loops, any personalized text, and handcrafted characteristics. '
                             'Do not modify the fabric cross itself in any way—only create a new setting around it. '
                             'The fabric cross should be the main focal point with the baby sleeping peacefully in the '
                             'background.\n'
                             '\n'
                             'STYLE: Lifestyle-inspired handcrafted product photography, soft natural lighting, edited '
                             'image quality, modern minimalist Etsy-style aesthetics, 1:1 square aspect ratio.\n'
                             '\n'
                             'AVOID: Harsh studio lighting, cluttered backgrounds, heavily edited embroidery, '
                             'unrealistic baby anatomy images, mass-produced appearance, AI errors, text overlapping '
                             'images, blurry images.'),
                            ('Product display',
                             'Product display đơn',
                             'Product photo of the fabric cross, taken from a reference image, is gently draped over '
                             'the handle of a stroller in a sun-drenched park setting. The delicately embroidered '
                             'fabric cross stands out against the neutral-colored stroller fabric and the soft blanket '
                             'inside. The backdrop is filled with natural greenery and soft daylight, creating a '
                             'peaceful and tranquil outdoor atmosphere. The composition focuses on the fabric cross as '
                             'the main focal point, with a shallow depth of field creating a subtle blur in the '
                             'background, highlighting the handcrafted details. The soft ribbon adds a delicate charm '
                             'to the overall design, ideal for a high-end Etsy product.\n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of the fabric cross from the reference image. Keep '
                             'the shape, size, proportions, fabric material, embroidery style, thread color, stitching '
                             'details, ribbon placement, any personalized text, and handcrafted features. Do not '
                             'modify the fabric cross itself in any way—only create a new context around it. The cart '
                             'and surrounding items should complement the cross without overshadowing it.\n'
                             '\n'
                             'STYLE: Handcrafted product photography, soft natural lighting, editorial quality, modern '
                             'minimalist Etsy-style aesthetic, 1:1 square aspect ratio.\n'
                             '\n'
                             'AVOID: Harsh studio lighting, cluttered backgrounds, heavily edited embroidery, '
                             'unrealistic cart proportions, mass-produced look, AI errors, text overlays, watermarks.'),
                            ('Product display',
                             'Composite layout',
                             'The product image shows a fabric cross inspired by a reference image. Three fabric '
                             'crosses in three different colors (three different colors but the same embroidery style '
                             'and thread color) are prominently displayed inside a wicker basket. The basket is placed '
                             'on a table, further decorated with a few flower petals, such as pastel wildflowers, '
                             'along with soft green plants and moss, creating a rustic, natural look. The arrangement '
                             'is set outdoors, with gentle sunlight shining through, creating a warm and pleasant '
                             'atmosphere. The fabric crosses should be the main focal point, with the natural beauty '
                             'of the flowers and soft ribbons adding elegance.\n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of the fabric crosses from the reference image. '
                             'Preserve the shape, size, proportions, fabric material, embroidery style, thread color, '
                             'stitching details, ribbon placement, any personal lettering, and handcrafted features. '
                             'Do not modify the fabric cross itself in any way—simply create a new composition around '
                             'it. The basket should contain fresh spring flowers to highlight the natural beauty '
                             'without overshadowing the fabric cross.\n'
                             '\n'
                             'STYLE: Handmade product photography, soft natural lighting, editorial quality, modern '
                             'minimalist Etsy aesthetic, 1:1 square aspect ratio.\n'
                             '\n'
                             'AVOID: Harsh studio lighting, cluttered backgrounds, over-edited embroidery, unrealistic '
                             'materials, mass-produced look, AI errors, text overlays, watermarks.'),
                            ('Editorial/Grid',
                             'Editorial — Grid layout',
                             'Product photos of handcrafted fabric crosses are taken from a reference image. A fabric '
                             'cross is displayed hanging on a wooden hook in a quiet and elegant interior space. '
                             'Beside it, a ceramic vase filled with fresh flowers sits on a wooden surface covered '
                             'with soft, neutral-colored linen, creating a warm and peaceful atmosphere. Gentle '
                             'natural light shines in from the left, illuminating the scene with a delicate and airy '
                             'feel. The fabric cross is the central focal point of the photo, while the surrounding '
                             'decorations add balance and tell a subtle story. The clean, minimalist, and lightly '
                             'styled background contributes to a refined editorial look. A standout product photo on '
                             'Etsy.\n'
                             '\n'
                             'IMPORTANT: The EXACT shape of the fabric cross is retained from the reference image. The '
                             'fabric texture, color palette, embroidery style, proportions, hanging ribbon details, '
                             'and overall handcrafted appearance are also preserved. Do not edit the fabric cross '
                             'itself – only recreate the surrounding background and the life scene around it.\n'
                             '\n'
                             'STYLE: Handmade product photography, soft natural lighting, editorial quality, modern '
                             'minimalist Etsy aesthetic, 1:1 square aspect ratio.\n'
                             '\n'
                             'AVOID: altering the cross design on the fabric, changing the embroidery, creating a '
                             'mass-produced look, overly harsh studio lighting, cluttered background, distracting '
                             'props, AI errors, text overlays, watermarks.'))},
 'bride_handkerchief': {'display_name': 'Bride Handkerchief',
                        'aliases': ('Bride Handkerchief',
                                    'bride handkerchief',
                                    'bridal handkerchief',
                                    'wedding handkerchief',
                                    'embroidered handkerchief',
                                    'khăn tay cô dâu',
                                    'khan tay co dau'),
                        'lock': 'the main product must remain the same embroidered wedding handkerchief or soft cloth '
                                'square with the exact fabric, edge finish, fold/open shape, motif placement, stitch '
                                'colors, and elegant keepsake scale from the source image',
                        'shots': (('Lifestyle',
                                   '2 khăn 2 màu cạnh nhau',
                                   'A lifestyle-style photograph of two hand-embroidered wedding handkerchiefs, taken '
                                   'from a reference image, shows two handkerchiefs in two different colors (with the '
                                   'same embroidery style) gently cradled in two hands, bathed in soft natural light. '
                                   'The handkerchiefs are elegantly displayed with their exquisite embroidery. Behind '
                                   "them is the bride's bridal room, with her wedding dress and suit hanging. The "
                                   'background is suddenly blurred, focusing attention on the handkerchiefs, while the '
                                   'overall scene conveys warmth, elegance, and timeless beauty.\n'
                                   'IMPORTANT: Maintain the EXACT shape of the handkerchiefs from the reference image. '
                                   'Preserve the fabric texture, embroidery details, proportions, and overall '
                                   'aesthetic. Do not alter the handkerchiefs in any way—simply create a new setting '
                                   'around them. The handkerchiefs should be the main focal point, with surrounding '
                                   'props highlighting their beauty.\n'
                                   'STYLE: Handcrafted product photography, soft natural light. Lightweight, '
                                   'high-quality editing, modern minimalist aesthetic. Etsy style, 1:1 square aspect '
                                   'ratio.\n'
                                   '\n'
                                   'AVOID: Overly harsh studio lighting, cluttered composition, altered backgrounds '
                                   'and embroidery patterns, unrealistic textures, mass-produced images, AI errors, '
                                   'text overlays, watermarks.'),
                                  ('Product display',
                                   'Flat display đơn',
                                   'This product image of a handmade wedding handkerchief is taken from a reference '
                                   'photo. The image shows a baby handing the handkerchief to the bride (only the '
                                   "bride's hand and the baby handing the handkerchief are visible) during a simple "
                                   'wedding ceremony. The handkerchief is the focal point of the photo, clearly '
                                   'showing the embroidery. The soft, natural light of the outdoor setting creates a '
                                   'stunning product photo on Etsy. \n'
                                   '\n'
                                   'IMPORTANT: The EXACT shape of the wedding handkerchief is retained from the '
                                   'reference photo. The fabric texture, color palette, embroidery style, proportions, '
                                   'edging details, and overall handcrafted look are preserved. The handkerchief '
                                   'itself has not been edited – only the surrounding background and the lifelike '
                                   'setting have been recreated. \n'
                                   '\n'
                                   'STYLE: Handmade product photography, romantic wedding style, soft natural light, '
                                   "high-quality editing, Etsy's modern minimalist aesthetic, 1:1 square aspect "
                                   'ratio. \n'
                                   '\n'
                                   'AVOID: editing the handkerchief design, changing the embroidery pattern, creating '
                                   'a mass-produced look, overly harsh studio lighting, cluttered backgrounds, '
                                   'distracting props, AI errors, text overlays, and watermarks.'),
                                  ('Gift box',
                                   'Gift box',
                                   'This product image shows a hand-embroidered wedding handkerchief, neatly placed in '
                                   'an elegant gift box lined with ivory silk paper. The handkerchief is perfectly '
                                   'folded to highlight the delicate beauty of the embroidery. The box is gently '
                                   'opened, revealing the handkerchief, and soft natural light accentuates the subtle '
                                   'details of the fabric and embroidery. Placed on a white table, surrounded by two '
                                   'wedding rings and a large bridal bouquet, it adds a romantic touch to the scene. '
                                   'The minimalist, clean background emphasizes the elegance, making it a perfect '
                                   'commemorative gift for the bride.\n'
                                   '\n'
                                   'IMPORTANT: Maintain the EXACT shape of the handkerchief as in the reference image. '
                                   'Keep the fabric, embroidery details, thread color, proportions, and overall '
                                   'aesthetic unchanged. Do not alter the handkerchief in any way—simply create a new '
                                   'setting around it. The gift box should highlight the beauty of the handkerchief '
                                   'without overshadowing it. STYLE: Handcrafted product photography, soft natural '
                                   'lighting, edited image quality, modern minimalist Etsy-style aesthetics, 1:1 '
                                   'square aspect ratio.\n'
                                   '\n'
                                   'AVOID: Overly elaborate packaging, harsh studio lighting, excessively retouched '
                                   'embroidery, cluttered composition, mass-produced appearance, AI errors, text '
                                   'overlays, watermarks.'),
                                  ('Product display',
                                   '3 khăn 3 màu',
                                   'The product image shows three hand-embroidered wedding handkerchiefs (different '
                                   'colors but the same embroidery style), elegantly arranged on a natural wood tray, '
                                   'with soft pastel colors and delicate floral patterns. The handkerchiefs are neatly '
                                   'folded, the embroidery clearly visible. A large bouquet of fresh wedding flowers, '
                                   'matching the embroidery on the handkerchiefs, and two wedding rings are gently '
                                   'arranged beside them, highlighting a tender, romantic feel. The scene is softly '
                                   'illuminated by warm natural light, creating a refined and intimate atmosphere. The '
                                   'soft material and exquisite embroidery are highlighted, making it a perfect '
                                   'keepsake for special occasions.\n'
                                   '\n'
                                   'IMPORTANT: Maintain the EXACT shape of the handkerchiefs as shown in the reference '
                                   'image. Keep the fabric, embroidery details, proportions, and overall aesthetic '
                                   'unchanged. Do not alter the handkerchiefs in any way—simply create a new layout '
                                   'around them. The handkerchief should be the main focal point, with surrounding '
                                   'items highlighting its beauty.\n'
                                   '\n'
                                   'STYLE: Handmade product photography, soft natural lighting, edited image quality, '
                                   'modern minimalist aesthetic in the Etsy style, 1:1 square aspect ratio.\n'
                                   '\n'
                                   'AVOID: Harsh studio lighting, cluttered backgrounds, over-edited embroidery, '
                                   'unrealistic textures, mass-produced look, AI errors, text overlays, watermarks.'),
                                  ('Product display',
                                   'Trên vải mềm + decor',
                                   'This photo shows an embroidered wedding handkerchief, taken from a reference '
                                   'image, placed on a soft white veil, surrounded by wedding invitations, two rings, '
                                   'and a large wedding bouquet. The handkerchief is positioned in the center of the '
                                   'photo to highlight the delicate embroidery. Soft natural light from a nearby '
                                   'window accentuates the fabric and embroidery, creating a romantic and elegant '
                                   'atmosphere for this wedding gift.\n'
                                   '\n'
                                   'IMPORTANT: Maintain the EXACT shape of the handkerchief from the reference image. '
                                   'Keep the fabric, embroidery details, and personalized text unchanged. Do not alter '
                                   'the handkerchief in any way—only create a new setting around it.\n'
                                   '\n'
                                   'STYLE: Handmade product photography, soft natural light, high-quality editing, '
                                   'modern minimalist Etsy-style aesthetic, 1:1 square aspect ratio.\n'
                                   '\n'
                                   'AVOID: cluttered layouts, harsh lighting, altered embroidery patterns, fake '
                                   'materials, AI errors, text overlays, and watermarks.'),
                                  ('Lifestyle',
                                   'Chú rể cầm khăn',
                                   'This lifestyle-style photo shows the groom holding a hand-embroidered handkerchief '
                                   "from the reference image, gently placed in the bride's hand. The handkerchief, "
                                   "with its exquisite embroidery is clearly visible, and the groom's hands are subtly "
                                   'positioned to highlight the delicate details. Soft natural light illuminates the '
                                   'handkerchief and the meticulous embroidery, creating a warm and tender moment. The '
                                   'background is a light, neutral-toned interior space with a cozy, minimalist '
                                   'atmosphere, highlighting the handcrafted quality of the handkerchief.\n'
                                   'IMPORTANT: Maintain the EXACT shape of the handkerchief from the reference image. '
                                   'Keep the fabric, embroidery details, proportions, and overall aesthetic unchanged. '
                                   'Do not alter the handkerchief in any way—simply create a new context around it. '
                                   "The bride's hands should interact naturally with the handkerchief, and the context "
                                   'should maintain a soft and focused feel.\n'
                                   'STYLE: Photograph handcrafted products in a lifestyle style, with soft, natural '
                                   'lighting, high-quality editing, a modern minimalist Etsy aesthetic, and a 1:1 '
                                   'square aspect ratio.\n'
                                   'AVOID: overly harsh studio lighting, cluttered backgrounds, digitally altered '
                                   'embroidery, unrealistic hand poses, overly stylized interactions, AI errors, text '
                                   'overlays, and watermarks.'),
                                  ('Product display',
                                   'Tổng hợp nhiều góc',
                                   'This product photo set includes four close-up shots of the embroidery on the '
                                   'handkerchief to highlight the delicate details of the hand-embroidered wedding '
                                   'handkerchief.\n'
                                   '\n'
                                   'All photos should be taken with soft, natural light to create depth, and with a '
                                   'blurred background to focus on the embroidery details and fabric texture.\n'
                                   '\n'
                                   'IMPORTANT: Maintain the EXACT shape of the handkerchief in the reference photos. '
                                   'Keep the fabric material, embroidery style, thread color, stitching style, and '
                                   'proportions unchanged. Do not edit the handkerchief in any way—simply create a new '
                                   'context around it.\n'
                                   '\n'
                                   'STYLE: Handmade product photography, soft natural light, editorial quality, modern '
                                   'minimalist Etsy-style aesthetic, 1:1 square aspect ratio.\n'
                                   '\n'
                                   'AVOID: Blurry stitching, a machine-like appearance, altered embroidery style, '
                                   'harsh lighting, overexposed highlights, AI errors, text overlays, watermarks.'),
                                  ('Product display',
                                   'Flat display #3',
                                   "This lifestyle photograph captures a close-up of a woman's hands carefully "
                                   'embroidering a scarf pattern on a circular embroidery hoop. The image focuses on '
                                   'the delicate, precise embroidery process, showing the thread being pulled through '
                                   'the fabric. The hands are depicted in a natural, relaxed posture, highlighting the '
                                   'skill and meticulousness. The surrounding space is decorated in a minimalist and '
                                   'handcrafted style, including neutral-colored embroidery thread, a small pair of '
                                   'scissors, and a few dried flowers. Soft natural light from the side accentuates '
                                   'the texture of the fabric and thread, creating a warm, artistic atmosphere.\n'
                                   '\n'
                                   'IMPORTANT: Maintain the EXACT shape of the embroidery pattern from the reference '
                                   'photograph. Keep the fabric texture, embroidery pattern, thread color, needle '
                                   'placement, and proportions unchanged. Do not modify the embroidery pattern or '
                                   'stitch details—simply create a new context around it.\n'
                                   '\n'
                                   'STYLE: Handcrafted product photography, soft natural lighting, high-quality '
                                   'editing, modern minimalist aesthetics in the Etsy style, 1:1 square aspect ratio.\n'
                                   '\n'
                                   'AVOID: Incorrect needle placement, unthreaded needles, blurry stitching, overly '
                                   'stylized hands, cluttered backgrounds, AI errors, text overlapping images, blurry '
                                   'images.'))},
 'vows_book': {'display_name': 'Vows Book',
               'aliases': ('Vows Book',
                           'vow book',
                           'vows book',
                           'vows notebook',
                           'vow notebook',
                           'wedding vows',
                           'bride vows',
                           'groom vows',
                           'sổ vows',
                           'so vows'),
               'lock': 'the main product must remain the same fabric-covered vow book/booklet with the exact book '
                       'cover shape, spine/edge construction, embroidered cover layout, lettering placement, fabric '
                       'texture, and wedding keepsake identity from the source image',
               'shots': (('Lifestyle',
                          'Đôi uyên ương cùng đọc',
                          'This product image of a handmade wedding vow book is taken from a reference photo. The '
                          'bride and groom are photographed from behind in an outdoor wedding setting, each holding a '
                          'vow book pointing towards the sky. The couple stands under a clear blue sky with soft '
                          'natural sunlight, creating a romantic and elegant atmosphere. The vow books are the main '
                          "focus of the photo, while the couple's wedding attire and the greenery in the distance "
                          'below add context and emotion. The background is clean, airy, and slightly blurred, with '
                          'ample open space and a soft depth of field, creating a sophisticated, almost edited look. A '
                          'standout product photo on Etsy.\n'
                          '\n'
                          'IMPORTANT: The EXACT shape of the vow books from the reference photo is preserved. The '
                          'linen texture, color palette, embroidery style, cover layout, proportions, and overall '
                          'handmade appearance are also retained. The vow books themselves are not edited – only the '
                          'surrounding background and the life-like setting are recreated.\n'
                          '\n'
                          'IMPORTANT: The exact shape of the vow books is preserved from the reference photo. The '
                          'linen texture, color palette, embroidery style, cover layout, proportions, and overall '
                          'handmade look are retained. No editing of the vow books themselves is done – only the '
                          'surrounding background and the life-like setting is reproduced.\n'
                          '\n'
                          'STYLE: Handmade product photography, romantic wedding lifestyle, soft natural lighting, '
                          'editorial quality, modern minimalist Etsy aesthetic, 1:1 square aspect ratio.\n'
                          '\n'
                          'AVOID: altering vow book design, changing embroidery, mass production style, harsh studio '
                          'lighting, cluttered background, distracting props, AI errors, text overlays, watermarks.'),
                         ('Product display',
                          '2 cuốn windowsill (active)',
                          'This product photo of a handmade wedding vow book is taken from a reference image. Two vow '
                          'books are displayed upright on a clean white table in an elegant interior space. A white '
                          'ceramic vase filled with fresh flowers sits between the two books, while several delicate '
                          'wedding-themed decorative items such as candlesticks, rings, and a small camera are '
                          'arranged around them. Soft natural light creates a romantic and intimate atmosphere. The '
                          'two vow books are the main focus of the photo, with the surrounding items adding balance '
                          'and telling the story. The clean, minimalist, and slightly blurred background, with plenty '
                          'of empty space and a soft depth of field, creates a professional, editorial look. A '
                          'standout product photo on Etsy.\n'
                          '\n'
                          'IMPORTANT: The EXACT shape of the vow books from the reference image is preserved. The '
                          'linen texture, color palette, embroidery style, cover layout, proportions, and overall '
                          'handcrafted look are also retained. Do not edit the vow books themselves – only recreate '
                          'the background and surrounding scenery.\n'
                          '\n'
                          'STYLE: Handcrafted product photography, romantic wedding table decorations, soft natural '
                          'lighting, professional image quality, modern minimalist Etsy aesthetic, 1:1 square aspect '
                          'ratio.\n'
                          '\n'
                          'AVOID: altering the vow book design, changing embroidery patterns, mass production style, '
                          'harsh studio lighting, cluttered backgrounds, distracting props, AI errors, text overlays, '
                          'watermarks.'),
                         ('Flat lay',
                          'Flat lay — vow books + props',
                          'This product image of a handmade wedding vow book is taken from a reference photo. Two vow '
                          'books are displayed upright on a small wooden stand on a pristine white table in an elegant '
                          'outdoor wedding setting. Surrounding the books are romantic wedding-themed details such as '
                          'white bouquets, soft greenery, a wooden Welcome sign, and a few small photos, creating a '
                          'beautifully decorated wedding scene. Warm natural sunlight gently illuminates the scene, '
                          'creating a romantic and timeless atmosphere. The vow books are the central focus of the '
                          'photo, while the surrounding decorations add balance and tell a story. The backdrop is an '
                          'outdoor garden with soft greenery and a natural bokeh effect, subtly blurred to focus '
                          'attention on the books. A standout product photo on Etsy.\n'
                          '\n'
                          'IMPORTANT: The EXACT shape of the vow books from the reference photo is preserved. Maintain '
                          'the original linen texture, color palette, embroidery style, cover layout, proportions, and '
                          'overall handcrafted look. Do not edit the vow books themselves – only recreate the '
                          'background and surrounding scenery.\n'
                          '\n'
                          'STYLE: Handcrafted product photography, romantic wedding table setting, soft natural '
                          "lighting, professional image quality, Etsy's modern minimalist aesthetic, 1:1 square aspect "
                          'ratio.\n'
                          '\n'
                          'AVOID: altering the vow book design, changing the embroidery patterns, mass production '
                          'style, harsh studio lighting, cluttered backgrounds, distracting props, AI errors, text '
                          'overlays, watermarks.'),
                         ('Cận thêu tay',
                          'Cận thêu tay',
                          'This product image of the handmade wedding vow book is taken from a reference photo. The '
                          'bride and groom stand side-by-side in a stunning outdoor wedding setting in a garden, '
                          'smiling at the camera while each holds the vow book aloft above their heads. The couple are '
                          'dressed in elegant wedding attire, creating a joyful and romantic atmosphere. The vow book '
                          'is clearly visible and is the main focus of the photo, while the lush greenery, soft '
                          'flowers, and natural garden backdrop add background and warmth. Bright natural daylight '
                          'illuminates the scene, and the background is gently blurred with subtle depth of field to '
                          'create a professional, editor-quality look. A standout product photo on Etsy.\n'
                          '\n'
                          'IMPORTANT: The EXACT shape of the vow book is retained from the reference photo. The linen '
                          'texture, color palette, embroidery style, cover layout, proportions, and overall '
                          'handcrafted look are also preserved. Do not edit the vow book itself – only recreate the '
                          'surrounding background and the life-related scenes around it.\n'
                          '\n'
                          'STYLE: Handmade product photography, romantic wedding lifestyle, soft natural lighting, '
                          'editorial quality, modern minimalist Etsy aesthetic, 1:1 square aspect ratio.\n'
                          '\n'
                          'AVOID: altering the vow book design, changing the embroidery, mass production style, harsh '
                          'studio lighting, cluttered background, distracting props, AI errors, text overlays, '
                          'watermarks.'),
                         ('Gift box',
                          'Gift box',
                          'This product image of the handmade wedding vow book is taken from a reference photo. The '
                          'bride and groom are photographed in a close-up of a romantic wedding portrait, gently '
                          'kissing while each holds a vow book in front of them. The couple are dressed in elegant '
                          'wedding attire, creating an intimate and touching atmosphere. The vow books are prominently '
                          'displayed in the foreground and are the main focus of the photo, while the couple and the '
                          'wedding backdrop are subtly designed to add warmth and storytelling. Soft natural light '
                          'illuminates the scene, and the clean, airy, slightly blurred background with a gentle depth '
                          'of field creates a sophisticated, almost editorial look. A standout product image on Etsy.\n'
                          '\n'
                          'IMPORTANT: The EXACT shape of the vow book from the reference photo is preserved. The linen '
                          'texture, color palette, embroidery style, cover layout, proportions, and overall '
                          'handcrafted appearance are also retained. Do not edit the vow books themselves – only '
                          'recreate the surrounding background and the everyday life setting.\n'
                          '\n'
                          'STYLE: Handmade product photography, romantic wedding lifestyle, soft natural lighting, '
                          'editorial quality, modern minimalist Etsy aesthetic, 1:1 square aspect ratio.\n'
                          '\n'
                          'AVOID: altering the vow book design, changing the embroidery, mass production style, harsh '
                          'studio lighting, cluttered background, distracting props, AI errors, text overlays, '
                          'watermarks.'),
                         ('Product display',
                          '2 cuốn bìa rõ cả 2',
                          "This lifestyle photograph captures a close-up of a woman's hands meticulously embroidering "
                          "the Bride's Vow motif on a circular embroidery hoop. The image focuses on the delicate, "
                          'precise embroidery process, showing the thread being pulled through the fabric and the '
                          'needle holes threaded. The hands are depicted in a natural, relaxed posture, highlighting '
                          'the skill and meticulousness. The surrounding space is decorated in a minimalist and '
                          'handcrafted style, including neutral-colored embroidery thread, a small pair of scissors, '
                          'and a few dried flowers. Soft natural light from the side accentuates the texture of the '
                          'fabric and thread, creating a warm, artistic atmosphere.\n'
                          '\n'
                          'IMPORTANT: Maintain the EXACT shape of the embroidery motif from the reference image. Keep '
                          'the fabric texture, embroidery pattern, thread color, needle placement, and proportions '
                          'unchanged. Do not alter the embroidery motif or stitch details—simply create a new context '
                          'around it.\n'
                          '\n'
                          'STYLE: Handcrafted product photography, soft natural lighting, high-quality editing, modern '
                          'minimalist aesthetics in the Etsy style, 1:1 square aspect ratio.\n'
                          '\n'
                          'AVOID: Incorrect needle placement, unthreaded needles, blurry images. Errors such as uneven '
                          'stitching, overly stylized hands, cluttered backgrounds, AI errors, text overlapping '
                          'images, blurry images.'),
                         ('Lifestyle',
                          'Cầm tại bàn tiệc cưới',
                          'This product image of the handcrafted wedding vow book is taken from a reference photo. Two '
                          "vow books are placed in the center, between the bride's elegant high heels and the groom's "
                          'classic dress shoes, creating a sophisticated and romantic composition in the style of a '
                          'flat wedding photoshoot. Soft lace is styled around the scene, adding texture and the '
                          "bride's elegance. The image is taken from a low angle, creating depth in the composition "
                          'and highlighting the vow books. Soft, elegant lighting illuminates the entire scene, '
                          'highlighting the linen texture and the handcrafted quality of the books. The clean, '
                          'elegant, and subtly styled background, with its delicate depth of field, creates a '
                          'professional, editorial look. A standout product photo on Etsy. \n'
                          '\n'
                          'IMPORTANT: The EXACT shape of the vow books from the reference photo is preserved. The '
                          'linen texture, color palette, embroidery style, cover layout, proportions, and overall '
                          'handcrafted look are also preserved. Do not edit the vow books themselves – only recreate '
                          'the surrounding background and the everyday scenes around them. \n'
                          '\n'
                          'STYLE: Handmade product photography, romantic wedding style, soft and elegant lighting, '
                          'professional image quality, modern minimalist Etsy aesthetic, 1:1 square aspect ratio. \n'
                          '\n'
                          'AVOID: altering the vow book design, changing embroidery patterns, mass-produced images, '
                          'harsh studio lighting, cluttered backgrounds, distracting props, AI errors, text overlays, '
                          'watermarks.'))},
 'ring_bearer_pillow': {'display_name': 'Ring Bearer Pillow',
                        'aliases': ('Ring Bearer Pillow',
                                    'ring bearer pillow',
                                    'ring bearer cushion',
                                    'wedding ring pillow',
                                    'wedding ring cushion',
                                    'ring cushion',
                                    'ring holder pillow',
                                    'wedding ceremony pillow',
                                    'ring pillow',
                                    'gối nhẫn',
                                    'goi nhan',
                                    'goi dung nhan',
                                    'goi nhan cuoi',
                                    'goi de nhan'),
                        'lock': 'the main product must remain the same ring bearer pillow with the exact cushion '
                                'shape, fabric surface, embroidery/floral motif placement, ribbon/ring attachment area '
                                'if present, soft volume, seams, and wedding ceremony scale from the source image',
                        'shots': (('Product display',
                                   'Đứng trên gỗ sơn trắng',
                                   'This product image of a handcrafted wedding ring pillow is taken from a reference '
                                   'photo. The pillow is displayed standing on a clean white wooden surface in a soft '
                                   'and elegant interior space. It is decorated with delicate wedding-inspired details '
                                   'such as gentle flowers and foliage, soft linen fabric, and a few small stitches or '
                                   'decorative motifs arranged around it, with a white voile overlay behind, creating '
                                   'a romantic and handcrafted atmosphere. The ribbon and wedding rings are clearly '
                                   'visible, while the pillow remains the main focal point of the photo. Soft natural '
                                   'light illuminates the scene, highlighting the fabric texture and handcrafted '
                                   'quality. The clean, airy, and slightly blurred background with a gentle depth of '
                                   'field creates a sophisticated, editorial look. A standout product photo on Etsy. \n'
                                   '\n'
                                   'IMPORTANT: The EXACT shape of the ring pillow from the reference photo is '
                                   'retained. The fabric texture, color palette, embroidery style, ribbon details, '
                                   'proportions, and overall handcrafted look are preserved. No need to edit the ring '
                                   'cushion – just recreate the background and surrounding scenery. \n'
                                   '\n'
                                   'STYLE: Handcrafted product photography, romantic wedding style, soft natural '
                                   'lighting, professional image quality, modern minimalist Etsy aesthetic, 1:1 square '
                                   'aspect ratio. \n'
                                   '\n'
                                   'AVOID: altering the ring cushion design, changing embroidery patterns, '
                                   'mass-produced images, harsh studio lighting, cluttered backgrounds, distracting '
                                   'props, AI errors, text overlays, watermarks.'),
                                  ('Product display',
                                   'Kế hộp nhẫn gỗ mở',
                                   'This product image of a handcrafted wedding ring pillow is taken from a reference '
                                   'photo. A ring pillow sits upright on a clean table in an elegant and serene '
                                   'interior. Beside it is an open wooden wedding ring box containing two wedding '
                                   'rings, along with delicate natural decorations such as eucalyptus branches, dried '
                                   'flowers, and a few smooth stones arranged around it to create a tranquil, romantic '
                                   'atmosphere. Soft natural light from a nearby window highlights the fabric and the '
                                   'handcrafted beauty of the pillow. The ring pillow is the focal point of the photo, '
                                   'while the surrounding items add warmth and tell a subtle story. The clean, airy, '
                                   'and slightly blurred background with a gentle depth of field creates a '
                                   'professional, edited look. A standout product photo on Etsy. \n'
                                   '\n'
                                   'IMPORTANT: The EXACT shape of the ring pillow from the reference photo is '
                                   'preserved. Maintain the original fabric, color palette, embroidery style, ribbon '
                                   'details, proportions, and overall handcrafted look. Do not edit the ring pillow '
                                   'itself – only recreate the background and surrounding scenery. \n'
                                   '\n'
                                   'STYLE: Handcrafted product photography, romantic wedding style, soft natural '
                                   'lighting, professional image quality, modern minimalist Etsy aesthetic, 1:1 square '
                                   'aspect ratio. \n'
                                   '\n'
                                   'AVOID: altering the ring pillow design, changing the embroidery pattern, '
                                   'mass-produced images, harsh studio lighting, cluttered backgrounds, distracting '
                                   'props, AI errors, text overlays, watermarks.'),
                                  ('Product display',
                                   '3 chiếc trên kệ tường',
                                   'This product image of handcrafted wedding ring pillows is taken from a reference '
                                   'photo. Three ring pillows are displayed on three separate wall-mounted wooden '
                                   'shelves in an elegant interior space, with the middle pillow positioned slightly '
                                   'higher for a balanced composition. Each pillow shares the same embroidery style '
                                   'and overall design, but with different personalized names, and each is presented '
                                   'in a different color. Soft decorative details such as delicate dried flowers and '
                                   'sheer voile fabric are arranged around them, creating a warm, romantic, and '
                                   'sophisticated wedding atmosphere. The ring pillows are the main focal point in the '
                                   'center of the photo, while the surrounding decorations add balance and tell a '
                                   'subtle story. Gentle natural light illuminates the scene, highlighting the fabric '
                                   'texture, ribbon details, and handcrafted quality. The clean, warm, minimalist, and '
                                   'slightly muted background creates a professional, editorial look. A standout '
                                   'product photo on Etsy. \n'
                                   '\n'
                                   'IMPORTANT: Maintain the EXACT shape of the ring pillow from the reference image. '
                                   'Keep the fabric texture, embroidery style, ribbon details, proportions, and '
                                   'overall handcrafted look. Showcase three pillows with the same layout and '
                                   'embroidery, but in three different colors, each with a different personalized '
                                   'name. Do not alter the structure or style of the pillows – simply recreate the '
                                   'context and surrounding setting. \n'
                                   '\n'
                                   'STYLE: Handcrafted product photography, romantic wedding style, soft natural '
                                   'lighting, editorial quality, modern minimalist Etsy aesthetic, 1:1 square aspect '
                                   'ratio. \n'
                                   '\n'
                                   'AVOID: altering the pillow shape, changing the embroidery layout, changing the '
                                   'ribbon style, mass-produced look, harsh studio lighting, cluttered background, '
                                   'distracting props, AI errors, text overlays, watermarks.'),
                                  ('Product display',
                                   'Trên vải satin trắng',
                                   'This product image of the handmade wedding ring pillow is taken from a reference '
                                   'photo. The ring pillow is displayed on a soft white satin fabric in an elegant '
                                   'interior space. Alongside it are romantic wedding-inspired details such as a '
                                   'wedding bouquet (a bouquet of fresh flowers similar to the embroidered flowers on '
                                   'the ring pillow), a sealed envelope, and a few scattered petals or delicate floral '
                                   'accents, creating a graceful and emotional atmosphere. The ring pillow is the '
                                   'central focal point of the photo, while the surrounding items add warmth and tell '
                                   'a subtle story. Soft natural light illuminates the scene, highlighting the fabric '
                                   'texture, ribbon details, and handcrafted quality. The composition is styled like '
                                   'an elegant flat photograph with a clean, airy background and a light, editorial '
                                   'feel. A standout product photo on Etsy. \n'
                                   '\n'
                                   'IMPORTANT: The EXACT shape of the ring pillow from the reference photo is '
                                   'preserved. Maintain the original fabric texture, color palette, embroidery style, '
                                   'ribbon details, proportions, and overall handcrafted look. Do not edit the ring '
                                   'pillow itself – only recreate the surrounding background and the life-like '
                                   'setting. \n'
                                   '\n'
                                   'STYLE: Handcrafted product photography, romantic wedding style, soft natural '
                                   'lighting, professional image quality, modern minimalist Etsy aesthetic, 1:1 square '
                                   'aspect ratio. \n'
                                   '\n'
                                   'AVOID: altering the ring pillow design, changing the embroidery pattern, '
                                   'mass-produced images, harsh studio lighting, cluttered backgrounds, distracting '
                                   'props, AI errors, text overlays, watermarks.'),
                                  ('Product display',
                                   'Trên giá gỗ ngoài trời',
                                   'This product image of a handcrafted wedding ring pillow is taken from a reference '
                                   'photo. A ring pillow sits upright on a small wooden stand on a rustic wooden table '
                                   'in an elegant outdoor wedding setting. Surrounding the pillow are romantic '
                                   'wedding-inspired details such as a wedding bouquet matching the embroidery on the '
                                   'ring pillow, candles, a wedding cake, and a vow book, creating a warm and graceful '
                                   'atmosphere. Soft, natural sunset light illuminates the scene, highlighting the '
                                   'fabric texture, ribbon details, and the handcrafted quality of the pillow. The '
                                   'ring pillow is the central focal point of the photo, while the surrounding '
                                   'decorations add balance and tell a subtle story. The backdrop is an outdoor '
                                   'garden, gently blurred with just the right depth of field to create a '
                                   'professional, magazine-worthy look. A standout product photo on Etsy.\n'
                                   '\n'
                                   'IMPORTANT: The EXACT shape of the ring pillow from the reference photo is '
                                   'preserved. Maintain the original fabric texture, color palette, embroidery style, '
                                   'ribbon details, proportions, and overall handcrafted look. Do not edit the ring '
                                   'pillow itself – only recreate the background and surrounding scenery.\n'
                                   '\n'
                                   'STYLE: Handcrafted product photography, romantic wedding style, soft natural '
                                   'lighting, professional image quality, modern minimalist Etsy aesthetic, 1:1 square '
                                   'aspect ratio.\n'
                                   '\n'
                                   'AVOID: altering the ring pillow design, changing the embroidery pattern, '
                                   'mass-produced images, harsh studio lighting, cluttered backgrounds, distracting '
                                   'props, AI errors, text overlays, watermarks.'),
                                  ('Cận thêu tay',
                                   'Cận thêu hoa',
                                   'Take a close-up photograph of the embroidered floral pattern on the fabric ring '
                                   'cushion from the reference image, focusing on the exquisite hand-embroidered '
                                   'details, with clear threads and beautiful stitching, making the embroidery as '
                                   'visible as possible. The fabric ring cushion should be the main focal point, '
                                   'highlighting the embroidery and stitching. Soft, natural light from the side will '
                                   'emphasize the depth of the embroidery, with a shallow depth of field to create a '
                                   'hazy effect around the fabric. The fabric should be neutral and clean-colored, and '
                                   'the handcrafted details must be clearly visible, highlighting the quality of the '
                                   'product. \n'
                                   '\n'
                                   'IMPORTANT: Maintain the EXACT shape of the fabric ring cushion from the reference '
                                   'image. Preserve the fabric material, embroidery details, thread color, stitching, '
                                   'proportions, and handcrafted characteristics. Do not alter the ring cushion in any '
                                   'way—only enlarge the existing embroidery details. \n'
                                   '\n'
                                   'STYLE: Close-up photos of handcrafted products, soft natural lighting, '
                                   'high-quality editing, modern minimalist aesthetics in the Etsy style, 1:1 square '
                                   'aspect ratio. \n'
                                   '\n'
                                   'AVOID: blurry stitching, images that look like they were created by machines, '
                                   'edited embroidery patterns, harsh lighting, overexposed images, bright spots, AI '
                                   'errors, text overlapping images, blurry images.'),
                                  ('Gift box',
                                   'Gift box',
                                   'This product image of a handcrafted wedding ring pillow is taken from a reference '
                                   'photo. The ring pillow is displayed inside an elegant gift box in a soft and '
                                   'sophisticated interior setting. The gift box opens gently to reveal the pillow, '
                                   'creating a beautiful, thoughtful, romantic presentation suitable for gifting. Soft '
                                   'decorative details such as tissue paper, ribbons, or delicate wedding-inspired '
                                   'accents can surround the box, adding warmth and a charming handcrafted atmosphere. '
                                   'Gentle natural light illuminates the scene, highlighting the fabric texture, '
                                   'ribbon details, and overall handcrafted quality of the pillow. The ring pillow '
                                   'remains the main focus of the image, while the surrounding elements add balance '
                                   'and subtle storytelling. The clean, airy, and slightly blurred background with a '
                                   'gentle depth of field creates a professional, editorial look. A standout product '
                                   'photo on Etsy. \n'
                                   '\n'
                                   'IMPORTANT: Maintain the EXACT shape of the ring pillow from the reference image. '
                                   'Keep the fabric texture, color palette, embroidery style, ribbon details, '
                                   'proportions, and overall handcrafted look. Do not edit the ring pillow itself – '
                                   'only recreate the surrounding background and gift box presentation. \n'
                                   '\n'
                                   'STYLE: Handcrafted product photography, romantic wedding style, soft natural '
                                   'lighting, professional image quality, modern minimalist Etsy aesthetic, 1:1 square '
                                   'aspect ratio. \n'
                                   '\n'
                                   'AVOID: altering the ring pillow design, changing embroidery patterns, '
                                   'mass-produced images, harsh studio lighting, cluttered backgrounds, distracting '
                                   'props, AI errors, text overlays, watermarks.'),
                                  ('Lifestyle',
                                   'Cô dâu cầm nhẹ nhàng',
                                   'This product image of the handmade wedding ring pillow is taken from a reference '
                                   'photo. In the photo, the bride gently cradles the pillow with both hands in an '
                                   'elegant and tender wedding setting, the pillow fitting comfortably in her palms '
                                   '(not too large). The wedding dress and veil create a romantic and graceful '
                                   'atmosphere, while the pillow remains the focal point of the photo. The composition '
                                   "is intimate and delicate, with the bride's hands highlighting the pillow, "
                                   'emphasizing its handcrafted quality and sentimental significance. Soft natural '
                                   'light illuminates the scene, highlighting the fabric texture, ribbon details, and '
                                   'overall craftsmanship. The clean, airy, and slightly blurred background with just '
                                   'the right depth of field creates a professional look worthy of magazine coverage. '
                                   'A standout product photo on Etsy. \n'
                                   '\n'
                                   'IMPORTANT: The EXACT shape of the ring pillow from the reference photo is '
                                   'retained. The fabric texture, color palette, embroidery style, ribbon details, '
                                   'proportions, and overall handcrafted look are preserved. No editing of the ring '
                                   'cushion is required – only the background and surrounding scenery are recreated. \n'
                                   '\n'
                                   'STYLE: Handcrafted product photography, romantic wedding style, soft natural '
                                   'lighting, edited image quality, modern minimalist Etsy aesthetic, 1:1 square '
                                   'aspect ratio. \n'
                                   '\n'
                                   'AVOID: altering the ring cushion design, changing embroidery patterns, '
                                   'mass-produced photos, harsh studio lighting, cluttered backgrounds, distracting '
                                   'props, AI errors, text overlays, watermarks.'),
                                  ('Product display',
                                   'Trong xe ngựa gỗ miniature',
                                   'This product image of a handmade wedding ring pillow is taken from a reference '
                                   'photo. The ring pillow is displayed inside a small, rustic wooden carriage in an '
                                   'elegant and light interior space. The carriage is lined with light, airy voile '
                                   'fabric, and delicate dried flowers are arranged around the pillow to create a '
                                   'warm, romantic, and poetic wedding atmosphere. The ribbons and wedding rings are '
                                   'clearly visible, while the ring pillow remains the main focal point of the photo. '
                                   'Warm, soft natural light illuminates the scene, highlighting the fabric texture, '
                                   'ribbon details, and overall craftsmanship. The background is subtly styled with '
                                   'rustic wooden flooring and a moderate depth of field to create a professional, '
                                   'magazine-style look. A standout product photo on Etsy.\n'
                                   '\n'
                                   'IMPORTANT: The EXACT shape of the ring pillow from the reference photo is '
                                   'retained. The fabric texture, color palette, embroidery style, ribbon details, '
                                   'proportions, and overall handcrafted appearance are also preserved. Do not edit '
                                   'the ring pillow itself – only recreate the surrounding background and the '
                                   'surrounding scene.\n'
                                   '\n'
                                   'STYLE: Handmade product photography, romantic wedding style, soft natural '
                                   'lighting, professional image quality, modern minimalist Etsy aesthetic, 1:1 square '
                                   'aspect ratio.\n'
                                   '\n'
                                   'AVOID: altering the ring pillow design, changing the embroidery pattern, '
                                   'mass-produced images, harsh studio lighting, cluttered backgrounds, distracting '
                                   'props, AI errors, text overlays, watermarks.'),
                                  ('Lifestyle',
                                   'Đôi uyên ương cùng cầm',
                                   'This product image of a handcrafted wedding ring pillow is taken from a reference '
                                   'photo. The bride and groom are shown sitting next to each other in an elegant '
                                   'indoor wedding setting, gently holding the ring pillow between them (a small, not '
                                   'large, ring pillow). The couple are dressed in sophisticated wedding attire, '
                                   'creating a romantic and intimate atmosphere. The ring pillow is the central focal '
                                   "point of the photo, while the bride's lace dress, the groom's formal suit, and "
                                   'meticulously arranged wedding details such as the bouquet and classic furniture in '
                                   'the background add warmth and tell a story. Soft natural light illuminates the '
                                   'scene, highlighting the fabric texture, ribbon details, and overall craftsmanship '
                                   'of the pillow. The clean, airy background is prepared with just the right depth of '
                                   'field to create a professional look worthy of magazine coverage. A standout '
                                   'product photo on Etsy. \n'
                                   '\n'
                                   'IMPORTANT: The EXACT shape of the ring pillow from the reference image is '
                                   'preserved. Maintain the fabric texture, color palette, embroidery style, ribbon '
                                   'details, proportions, and overall handcrafted look. Do not edit the ring pillow '
                                   'itself – only recreate the surrounding background and scene as realistically as '
                                   'possible. \n'
                                   '\n'
                                   'STYLE: Handcrafted product photography, romantic wedding style, soft natural '
                                   'lighting, editorial quality, modern minimalist Etsy aesthetic, 1:1 square aspect '
                                   'ratio. \n'
                                   '\n'
                                   'AVOID: altering the ring pillow design, changing the embroidery pattern, '
                                   'mass-produced photos, harsh studio lighting, cluttered backgrounds, distracting '
                                   'props, AI errors, text overlays, watermarks.'),
                                  ('Lifestyle',
                                   'Cận đôi tay cầm gối',
                                   'This product image of the handmade wedding ring pillow is taken from a reference '
                                   'photo. A close-up shows the bride and groom gently cradling the ring pillow in '
                                   'both hands in an elegant wedding setting. The pillow is prominently placed in the '
                                   'center of the image, creating an intimate and meaningful composition. The ring '
                                   "pillow remains the main focus, while the couple's wedding attire and floral "
                                   'backdrop are subtly blurred, adding warmth, romance, and a delicate story. Soft '
                                   'natural light illuminates the scene, highlighting the fabric texture, ribbon '
                                   'details, and overall craftsmanship of the pillow. The clean, airy, and subtly '
                                   'blurred background with just the right depth of field creates a professional, '
                                   'magazine-worthy look. A standout product photo on Etsy. \n'
                                   '\n'
                                   'IMPORTANT: The EXACT shape of the ring pillow from the reference photo is '
                                   'preserved. The fabric texture, color palette, embroidery style, ribbon details, '
                                   'proportions, and overall handcrafted appearance are also retained. Do not edit the '
                                   'ring pillow itself – only recreate the surrounding background and the everyday '
                                   'scene around it. \n'
                                   '\n'
                                   'STYLE: Handmade product photography, romantic wedding style, soft natural '
                                   'lighting, editorial quality, modern minimalist Etsy aesthetic, 1:1 square aspect '
                                   'ratio. \n'
                                   '\n'
                                   'AVOID: altering the ring pillow design, changing the embroidery pattern, '
                                   'mass-produced images, harsh studio lighting, cluttered backgrounds, distracting '
                                   'props, AI errors, text overlays, watermarks.'),
                                  ('Quy trình',
                                   'Process — Tay thêu cận',
                                   'This product image of the handmade wedding ring pillow is taken from a reference '
                                   'photo. The close-up shows skilled hands embroidering on fabric in a circular '
                                   'embroidery hoop, with the same embroidery pattern as on the sample ring pillow. '
                                   'Surrounding the work area are delicate sewing materials such as embroidery thread, '
                                   'small scissors, fabric, and a few dried flowers arranged gently, creating a warm, '
                                   'handcrafted, and intimate atmosphere. Soft, natural yellow light illuminates the '
                                   'scene, highlighting the craftsmanship, fabric texture, and embroidery details. The '
                                   'embroidery remains the main focus of the photo, while the surrounding tools and '
                                   'decorations add context and story. The clean, warm, and slightly blurred '
                                   'background with depth of field creates a professional look. \n'
                                   '\n'
                                   'IMPORTANT: The exact shape and handcrafted appearance of the wedding ring pillow '
                                   'design from the reference photo is preserved. The fabric texture, embroidery '
                                   'style, color palette, proportions, and overall handcraft quality are maintained. '
                                   'Do not alter the embroidery layout to suit a different design concept – simply '
                                   'recreate the surrounding background and handcrafted setting. \n'
                                   '\n'
                                   'STYLE: Handcrafted product photography, detailed embroidery processing, soft '
                                   'natural lighting, professional image quality, modern minimalist Etsy style, 1:1 '
                                   'square aspect ratio. \n'
                                   '\n'
                                   'AVOID: Empty needle holes, misplaced embroidery stitches, inaccurate thread '
                                   'colors, altered ring pillow designs, altered embroidery patterns, mass-produced '
                                   'images, harsh studio lighting, cluttered backgrounds, distracting props, AI '
                                   'errors, text overlaying images, watermarks.'))},
 'christmas_album': {
     'display_name': 'Christmas Album',
     'aliases': (
         'Christmas Album',
         'christmas album',
         'Christmas Photo Album',
         'christmas photo album',
         'Christmas Memory Album',
         'christmas memory album',
         'Embroidered Christmas Album',
         'embroidered christmas album',
         'Linen Christmas Album',
         'linen christmas album',
         'hand embroidered Christmas album',
         'christmas keepsake album',
         'album giang sinh',
         'so album giang sinh',
     ),
     'target_count': 12,
     'lock': (
         'the main product must remain the exact same compact hand-embroidered Christmas Album from the source image, '
         'with the same rectangular cotton linen cover, fabric color and weave, spine, binding, edges, thickness, '
         'cover embroidery motif and lettering, thread colors, raised stitch texture, clear plastic photo-pocket '
         'pages when open, and premium handmade Christmas keepsake identity'
     ),
     'shots': (
         ('Lifestyle',
          'Dark coffee table with tea on Christmas morning',
          _christmas_album_brief(
              'place the exact embroidered album on a dark wooden coffee table beside a steaming cup of tea and only '
              'a few elegant festive decorations. Create a refined Christmas morning atmosphere with bright airy '
              'surroundings and soft natural window light. Keep the album sharply focused and the cover embroidery '
              'fully visible.'
          )),
         ('Lifestyle',
          'Hands holding album before Christmas tree bokeh',
          _christmas_album_brief(
              'show natural hands carefully holding the exact album in front of a beautifully decorated Christmas '
              'tree. Render the tree lights as soft restrained bokeh behind the product while keeping the cover, '
              'cotton linen texture, and raised embroidery bright, vivid, clean, and tack-sharp.'
          )),
         ('Close-up detail collage',
          'Four-panel embroidery detail collage',
          _christmas_album_brief(
              'create one square 2x2 collage containing exactly four professional macro photographs of different areas '
              'of the exact source embroidery. Show fine thread fibers, raised hand stitches, stitch direction, premium '
              'cotton linen weave, and cover craftsmanship. This explicitly numbered close-up detail collage is the '
              'only allowed four-panel image in the set.'
          )),
         ('Flat lay',
          'White textured flat lay with dried oranges',
          _christmas_album_brief(
              'create a top-down flat lay of the closed album on a white textured or white wood-grain surface, surrounded '
              'by a restrained arrangement of dried orange slices, pinecones, and elegant festive ribbons. Keep the '
              'Christmas styling refined and minimalist, the composition spacious, and the exact embroidery uncovered.'
          )),
         ('Lifestyle',
          'Two pairs of hands holding two albums',
          _christmas_album_brief(
              'show two pairs of natural hands lifting two copies of the exact embroidered album, one album held by each '
              'pair of hands. Use a softly blurred formal Christmas dinner table as the background. Keep both albums '
              'clean, bright, joyful, correctly proportioned, and clearly in focus.'
          )),
         ('Product display',
          'Two colorways on Christmas mantel',
          _christmas_album_brief(
              'place two copies of the linen album elegantly on a mantel decorated with a refined Christmas garland. '
              'Use two different cover fabric colors, but preserve exactly the same embroidery design, placement, scale, '
              'and thread colors on both albums. Keep one album closed and open the other slightly to reveal realistic '
              'clear photo-pocket pages. Use soft, bright, festive natural light without a yellow cast.'
          )),
         ('Lifestyle',
          'Mother and baby viewing inside photo pockets',
          _christmas_album_brief(
              'show a mother and baby looking through the album together in a cozy Christmas-decorated home. Do not show '
              'the embroidered cover in this shot; focus on the album interior. Each visible page must contain exactly '
              'two horizontal photos inserted inside its clear plastic pocket sleeve, showing Christmas moments with '
              'friends and family. Use soft clear natural light and realistic hands.'
          )),
         ('Product display',
          'Christmas welcome table with closed and open albums',
          _christmas_album_brief(
              'place two copies of the exact album on two small display stands on a Christmas party guest welcome table. '
              'Show one closed album with the source embroidery fully visible and one album fully open to reveal the '
              'inside pages. Each visible page must contain exactly two horizontal photos inside its clear plastic '
              'pocket sleeve, showing Christmas moments with friends and family. Add only a few Christmas decorations '
              'and a light sunbeam, keeping the whole scene bright, clear, airy, and album-focused.'
          )),
         ('Macro detail',
          'Christmas tree embroidery macro detail',
          _christmas_album_brief(
              'make a single close-up macro photograph of the exact source hand embroidery on the album. Highlight the '
              'premium cotton linen texture, individual raised stitches, and the fine threadwork of the Christmas tree '
              'and ornament details that are actually present in the reference. Use dreamy soft but bright natural light.'
          )),
         ('Process lifestyle',
          'Artisan embroidering matching motif in hoop',
          _christmas_album_brief(
              'show an artisan hands-only process scene embroidering the exact source album motif onto matching fabric '
              'stretched in a round embroidery hoop. Focus on realistic needlework and precise stitch placement in a '
              'professional workspace with restrained Christmas decor. The small needle eye must visibly contain '
              'thread, and the thread must pass naturally through the correct stitch position. Keep the scene bright '
              'and airy.'
          )),
         ('Product display',
          'Leaf-shadow sunlight on embroidered cover',
          _christmas_album_brief(
              'place the closed album under clean natural sunlight so delicate leaf shadows fall across the exact '
              'embroidered cover. Arrange only a few Christmas decorations around it without covering the embroidery. '
              'Keep the light transparent, white-balanced, bright, airy, and completely free of a yellow cast, with '
              'sharp focus on the album.'
          )),
         ('Hero product',
          'Premium album on bright Christmas table',
          _christmas_album_brief(
              'place the exact hand-embroidered album on a tastefully Christmas-decorated table in a bright spacious '
              'holiday interior. Use soft natural daylight and premium high-end product photography, focus tightly on '
              'the album, keep the compact proportions realistic and not overly long, and leave the source embroidery '
              'fully visible.'
          )),
     ),
 },
 'baby_christmas_album': {
     'display_name': 'Baby Christmas Album',
     'aliases': (
          'Baby Christmas Album',
          'baby christmas album',
          'Christmas Baby Album',
          'christmas baby album',
          'baby christmas photo album',
         'christmas baby photo album',
         'baby christmas memory album',
         'embroidered baby christmas album',
         'embroidered christmas baby album',
         'baby noel album',
         'christmas album em be',
         'album em be christmas',
         'album em be giang sinh',
         'so album em be giang sinh',
     ),
     'target_count': 12,
     'lock': (
         'the main product must remain the exact same hand-embroidered Baby Christmas Album from the source image, '
         'with the same rectangular cotton linen cover, fabric color and weave, spine, binding, edges, thickness, '
         'cover embroidery motif and lettering, thread colors, raised stitch texture, clear plastic photo-pocket '
         'pages, and premium handmade baby keepsake identity; every visible open page must hold exactly two '
         'horizontal photos inside its clear pocket sleeve'
     ),
     'shots': (
         ('Product display',
          'Christmas welcome table with closed and open albums',
          _baby_christmas_album_brief(
              'place two copies of the exact album on two small display stands on a Christmas party guest welcome '
              'table. Show one album closed so the exact cover embroidery is fully visible and one album fully open '
              'so the inside photo pages are clear. Each visible page contains exactly two horizontal photos inserted '
              'inside one clear plastic pocket sleeve, showing Christmas moments with the baby, friends, and family. '
              'Add only a few refined Christmas decorations and a soft sunbeam, keeping the display airy and focused '
              'on the albums.'
          )),
         ('Product display',
          'Leaf-shadow sunlight with baby Christmas decor',
          _baby_christmas_album_brief(
              'place the closed album under clean natural sunlight so delicate leaf shadows fall across the exact '
              'embroidered cover. Arrange a few baby-safe Christmas decorations around it without covering the '
              'embroidery. Keep the light transparent, bright, white-balanced, and spacious.'
          )),
         ('Flat lay',
          'Wicker basket Christmas baby flat lay',
          _baby_christmas_album_brief(
              'create a balanced top-down flat lay with the album resting on a wicker basket over a thick white voile '
              'fabric base. Style it with a Santa hat, a folded baby Christmas outfit, one ornament, a small evergreen '
              'branch, and a gingerbread cookie. Use a cohesive Christmas palette and leave the exact cover embroidery '
              'fully visible.'
          )),
         ('Lifestyle',
          'Christmas nursery crib with baby photos',
          _baby_christmas_album_brief(
              'place the album on a baby crib bed surrounded by pastel animal-shaped pillows, a soft cotton blanket, '
              'and a few printed baby photos. Add restrained Christmas nursery decorations to the crib. Use clear '
              'white-balanced early-morning window light with a gentle airy feeling and no yellow cast.'
          )),
         ('Close-up detail collage',
          'Four-panel hand embroidery macro proof',
          _baby_christmas_album_brief(
              'Create one square 2x2 detail collage made of four small close-up photos, each showing a different macro '
              'area of the exact cover embroidery. Show raised hand stitches, individual thread fibers, cotton linen '
              'weave, stitch direction, edge construction, and handmade depth. This is one single 1:1 detail-proof '
              'collage image only.'
          )),
         ('Product display',
          'Two albums standing on a wooden chair',
          _baby_christmas_album_brief(
              'place two copies of the exact album upright on a wooden chair: one closed with the cover embroidery '
              'facing the camera and one opened slightly so baby photos are visible inside clear glossy plastic pocket '
              'sleeves. Use tasteful Noel decorations around the chair, a softly angled product-focused camera, and '
              'soft clean natural daylight.'
          )),
         ('Product display',
          'Loose baby photos beside open pocket pages',
          _baby_christmas_album_brief(
              'compose a tabletop scene with loose printed baby photos scattered casually on the left and the album '
              'fully open on the right, with no cover visible. Show two open pages and exactly four horizontal photos '
              'total, two photos inserted inside the clear plastic pocket sleeve on each page. Add no writing anywhere '
              'on the open album. Use soft white daylight, a light sun touch, and restrained Christmas decor.'
          )),
         ('Lifestyle macro',
          'Hands holding cover before sleeping baby',
          _baby_christmas_album_brief(
              'create a close macro view of natural adult hands gently lifting the embroidered album in front of a '
              'sleeping baby who remains softly blurred in the background. Keep the exact cover embroidery sharply '
              'visible, with every stitch and the cotton linen texture clear. Use a dreamy but bright Christmas nursery '
              'setting and soft white-balanced light.'
          )),
         ('Lifestyle',
          'Mother and baby viewing embroidered cover',
          _baby_christmas_album_brief(
              'show a mother holding her baby while both hold and look at the album together in a Christmas-decorated '
              'room. Crop out both faces so only natural hands, arms, and torso details appear. Keep the embroidered '
              'cover facing the camera, sharply visible, and the main focal point under soft clear daylight.'
          )),
         ('Lifestyle',
          'Tummy-time baby behind embroidered album',
          _baby_christmas_album_brief(
              'show a baby lying on their tummy on a bed with the album immediately in front. Shoot from a low '
              'eye-level angle, focus sharply on the exact embroidered cover, and keep the baby softly blurred behind. '
              'Use natural white daylight, a soft pastel palette, and restrained Christmas bedroom decor.'
          )),
         ('Lifestyle',
          'Baby on sofa viewing inside pocket pages',
          _baby_christmas_album_brief(
              'show a baby sitting on a sofa and looking through the album interior in a Christmas-decorated room. The '
              'cover must not be visible. Focus on the clear glossy photo-pocket pages, with exactly two horizontal '
              'photos inserted in each visible page, realistic reflections, and soft bright white-balanced daylight.'
          )),
         ('Process lifestyle',
          'Woman hands embroidering matching cover motif',
          _baby_christmas_album_brief(
              'show a woman hands-only craft process scene embroidering the exact source cover motif onto matching '
              'cotton linen fabric stretched in a round embroidery hoop. The needle eye must visibly contain thread, '
              'and the threaded needle must pass through the correct stitch position. Add small scissors, matching '
              'thread, folded linen, and minimal handmade Christmas decor under clean natural window light.'
          )),
     ),
 },
 'baby_album': {'display_name': 'Baby Album',
                'aliases': ('Baby Album',
                            'baby album',
                            'baby photo album',
                            'baby memory album',
                            'baby keepsake album',
                            'first birthday album',
                            '1st birthday album',
                            'birthday photo album',
                            'embroidered baby album',
                            'fabric baby album',
                            'cotton linen baby album',
                            'so album be',
                            'so anh be',
                            'album em be',
                            'album sinh nhat',
                            'album thoi noi'),
                'lock': 'the main product must remain the same hand-embroidered baby photo album or first birthday '
                        'keepsake album with the exact rectangular album/book shape, cotton linen cover, spine and '
                        'edge construction, cover embroidery motif/name placement, stitch scale, thread colors, fabric '
                        'color family, clear plastic photo-pocket pages when open, and premium handmade baby keepsake '
                        'identity from the source image',
                'shots': (('Product display',
                           'Birthday welcome table with two display shelves',
                           _baby_album_brief('place the album on two small display shelves on a guest welcome table at a baby first birthday party. Show two copies of the same album: one closed or softly folded so the cover embroidery is fully visible, and one fully open so the inside photo pages are visible. Each open page holds two horizontal baby photos inside clear plastic pocket sleeves, showing sweet one-year-old baby moments with friends and family. Add a small faux goose figure, tiny star decorations, a few small neutral decorative pieces, and a soft sunbeam coming into the room. Keep the embroidery and the open photo pockets clear, with no prop covering the album.')),
                          ('Product display',
                           'Leaf-shadow sunlight on cover and open pages',
                           _baby_album_brief('place the album under clean natural sunlight so soft leaf shadows fall across the embroidered cover. Show one closed album with the cover embroidery clear, and one album fully open with inside pages visible. Each page holds two horizontal baby photos inside clear plastic pocket sleeves, showing one-year-old baby moments with friends and family. Highlight the raised hand embroidery, cotton linen texture, and artistic depth. Add a few loose baby photos on the table as secondary decor only, not overlapping or covering the album. Keep the light transparent, fresh, and airy.')),
                          ('Flat lay',
                           'White first-birthday keepsake flat lay',
                           _baby_album_brief('create a balanced flat lay with the album on a wicker basket over a thick white voile fabric base. Surround it with tasteful first-birthday props: a birthday hat, a baby bib or romper outfit, baby boy shoes, an embroidered crown, small toys, a birthday cake with a number 1 candle, and one small board reading "1st Birthday" as the only readable prop text allowed in this shot. Keep the palette white and close to the album color, clean and cohesive.')),
                          ('Lifestyle',
                           'Crib bed with pastel pillows and baby photos',
                           _baby_album_brief('place the album on a baby crib bed, surrounded by pastel animal-shaped pillows, a soft cotton blanket, and a few printed baby photos. Use warm early-morning window light, gentle shadows, and a soft airy nursery feeling. The cover embroidery, cotton linen texture, album shape, and handmade edges must remain visible and sharp.')),
                          ('Close-up detail collage',
                           'Four-panel hand embroidery macro proof',
                           _baby_album_brief('Create one square detail collage made of four small close-up photos, each showing a different macro angle of the album hand embroidery. Show raised hand stitches, cotton linen weave, thread relief, stitch direction, cover edge or lettering detail, and the handmade quality. This is one single 1:1 detail-proof collage image only; do not create a full product grid.')),
                          ('Product display',
                           'Picnic colorway pair opened fifteen degrees',
                           _baby_album_brief('place two albums in different fabric cover colors on a picnic blanket spread over grass. The two albums must keep the same embroidery layout, same source embroidery motif, same handmade construction, but use different personalized names only when the source album visibly has a stitched name. Each album stands upright and is opened slightly about 15 degrees so one photo per page is visible inside clear plastic pocket sleeves. Add a wicker basket, wildflowers, and fresh fruit around the blanket. Use soft clear golden sunlight without a heavy yellow cast, fresh cheerful air, and focus tightly on the albums.')),
                          ('Product display',
                           'Loose photos versus organized album',
                           _baby_album_brief('compose a left-versus-right tabletop story: on the left, loose printed baby photos are scattered casually; on the right, the hand-embroidered album is neat and organized, with photos inserted inside clear plastic pocket sleeves, two horizontal photos per page. Use soft natural light with a gentle sun touch. Add a small birthday cake and baby toys as secondary decor, keeping the album as the clean focal point.')),
                          ('Lifestyle macro',
                           'Hands holding album before sleeping baby',
                           _baby_album_brief('create a close-up of adult hands gently lifting the embroidered album in front of a sleeping baby. The baby is softly blurred in the background. Use a macro lens feeling to highlight every stitch of the exact source embroidery and any stitched lettering if present, with the cotton linen texture clearly visible. Keep the mood dreamy, tender, and bright.')),
                          ('Lifestyle macro',
                           'Baby hand touching album corner',
                           _baby_album_brief('make an emotional macro shot of a baby hand gently holding or touching one corner of the album. Put the exact embroidered area from the source cover at the sharp focus point, showing layered thread, raised stitches, and cotton linen fibers. The baby face is softly blurred in the background, and the baby wears a beautiful bib. Use soft clear daylight and a very tender first-birthday keepsake mood.')),
                          ('Lifestyle',
                           'Mother and baby hands viewing cover',
                           _baby_album_brief('show a mother holding a baby while they hold and look at the album together. Crop the scene so only hands, arms, and torso details are visible; do not show faces. The album cover embroidery must be clearly visible and the album must be the focal point. Use soft emotional daylight and a connected family feeling without clutter.')),
                          ('Lifestyle',
                           'Baby on sofa viewing inside photo pages',
                           _baby_album_brief('show a baby sitting on a sofa and looking through the album interior photo pages. The album cover is not visible in this shot; focus on the inside pages only. Each page holds two horizontal photos inside clear glossy plastic pocket sleeves. Use a neutral sofa, soft daylight, shallow depth of field, and a bright airy home feeling.')),
                          ('Process lifestyle',
                           'Woman hands embroidering matching cover motif',
                           _baby_album_brief('show a woman hands-only craft process scene embroidering the same cover motif onto matching cotton linen fabric stretched in an embroidery hoop. A realistic needle has thread through the needle eye and is passing through the correct stitch position. Include handmade decor such as thread spools, small scissors, folded linen, and soft natural window light. The stitching must match the album cover motif and feel authentically hand embroidered.')))},
 'guest_book': {'display_name': 'Guest Book',
                'aliases': ('Guest Book',
                            'guest book',
                            'wedding guest book',
                            'embroidered guest book',
                            'photo album',
                            'wedding photo album',
                            'fabric photo album',
                            'embroidered photo album',
                            'scrapbook',
                            'wedding scrapbook',
                            'memory book',
                            'sổ ký tên',
                            'so ky ten',
                            'sổ khách',
                            'so khach'),
                'lock': 'the main product must remain the same fabric-covered wedding guest book with the exact book '
                        'shape, cover material, embroidery placement, spine/edge construction, lettering/motif style, '
                        'and elegant keepsake scale from the source image',
                'shots': (('Product display',
                           'Trên vải trắng + props cưới',
                           'This product image of a handmade wedding scrapbook is taken from a reference photo. The '
                           'scrapbook is displayed on a soft white fabric in an elegant interior setting. Alongside it '
                           'are romantic wedding-inspired details such as a wedding bouquet, wedding rings, '
                           'invitations, and scattered flower petals, creating a charming and emotional atmosphere. '
                           'The scrapbook is the central focal point of the image, while the surrounding items add '
                           'warmth and tell a subtle story. Soft natural light illuminates the scene, highlighting the '
                           'fabric texture, craftsmanship, and elegant cover presentation. The composition is styled '
                           'like an elegant flat photograph with a clean, airy background and a light, editorial feel. '
                           'A standout product image on Etsy.\n'
                           '\n'
                           'IMPORTANT: The EXACT shape of the scrapbook from the reference photo is preserved. The '
                           'linen texture, color palette, embroidery style, cover layout, proportions, and overall '
                           'handcrafted look are also retained. Do not edit the scrapbook – only recreate the '
                           'surrounding background and the life-like setting.\n'
                           '\n'
                           'STYLE: Handmade product photography, romantic wedding style, soft natural lighting, '
                           'editorial quality, modern minimalist Etsy aesthetic, 1:1 square aspect ratio.\n'
                           '\n'
                           'AVOID: altering the scrapbook design, changing the embroidery, mass-production style, '
                           'harsh studio lighting, cluttered background, distracting props, AI errors, text overlays, '
                           'watermarks.'),
                          ('Cận thêu tay',
                           'Cận thêu tay',
                           'Take a close-up photo of the fabric notebook from the reference image, focusing on the '
                           'exquisite hand-embroidered details, with clear threads and beautiful stitching. The fabric '
                           'notebook should be the main focal point, highlighting the embroidery and stitching. Soft, '
                           'natural light from the side will emphasize the depth of the embroidery, with a shallow '
                           'depth of field to create a hazy effect around the fabric. The fabric should be neutral and '
                           'clean-colored, and the handcrafted details must be clearly visible, highlighting the '
                           'quality of the product.\n'
                           '\n'
                           'IMPORTANT: Maintain the EXACT shape of the fabric notebook from the reference image. '
                           'Preserve the fabric material, embroidery details, thread color, stitching, proportions, '
                           'and handcrafted characteristics. Do not alter the notebook in any way—only enlarge the '
                           'existing embroidery details.\n'
                           '\n'
                           'STYLE: Close-up of the handcrafted product, soft natural light, high-quality editing, '
                           'modern minimalist Etsy-style aesthetic, square aspect ratio. 1:1.\n'
                           '\n'
                           'AVOID: blurry seams, images that look machine-generated, altered embroidery patterns, '
                           'harsh lighting, overexposed images, highlights, AI errors, text overlaid on images, '
                           'watermarks.'),
                          ('Product display',
                           'Dựng trên giá gỗ nhỏ',
                           'This product photo of a handmade wedding scrapbook is taken from a reference image. The '
                           'scrapbook is placed upright on a small wooden stand on a clean white table in an elegant '
                           'wedding setting. Surrounding the scrapbook are romantic wedding-inspired details such as a '
                           'soft bouquet resembling the embroidered flowers on the scrapbook, an open wooden ring box, '
                           'candles, and delicate lace accents, creating a graceful and sophisticated atmosphere. The '
                           'scrapbook is the main focus of the photo, while the surrounding decorations add warmth and '
                           'tell a subtle story. Soft natural light illuminates the scene, highlighting the linen '
                           'texture, the craftsmanship, and the elegant presentation of the cover. The clean, airy, '
                           'and slightly blurred background with just the right depth of field creates a professional, '
                           'magazine-style look. A standout product photo on Etsy. \n'
                           '\n'
                           'IMPORTANT: The EXACT shape of the scrapbook from the reference image is preserved. '
                           'Maintain the original linen texture, color palette, embroidery style, cover layout, '
                           'proportions, and overall handcrafted look. Do not edit the scrapbook – only recreate the '
                           'surrounding background and the life-like setting. \n'
                           '\n'
                           'STYLE: Handcrafted product photography, romantic wedding style, soft natural lighting, '
                           'professional image quality, modern minimalist Etsy aesthetic, 1:1 square aspect ratio. \n'
                           '\n'
                           'AVOID: altering the scrapbook design, changing embroidery patterns, mass production style, '
                           'harsh studio lighting, cluttered backgrounds, distracting props, AI errors, text overlays, '
                           'watermarks.'),
                          ('Lifestyle',
                           'Cô dâu cầm gracefully',
                           'This product photo of a handcrafted wedding scrapbook is taken from a reference image. In '
                           'a gentle and elegant wedding setting, the bride is shown holding the scrapbook gracefully. '
                           'She wears a romantic off-the-shoulder wedding dress, creating a charming and sophisticated '
                           'atmosphere, while the scrapbook remains the focal point of the photo. The composition is '
                           'intimate and refined, with the bride clearly displaying the scrapbook to emphasize its '
                           'handcrafted quality and sentimental value. Delicate floral decorations in the background '
                           'add warmth and a refined wedding ambiance. Soft natural light illuminates the scene, '
                           'highlighting the fabric texture, craftsmanship, and elegant presentation of the cover. The '
                           'clean, airy, and subtly blurred background with just the right depth of field creates a '
                           'professional, magazine-style look. A standout product photo on Etsy.\n'
                           '\n'
                           'IMPORTANT: The EXACT shape of the scrapbook from the reference image is preserved. '
                           'Maintain the original fabric texture, color palette, embroidery style, cover layout, '
                           'proportions, and overall handcrafted look. Do not edit the scrapbook – only recreate the '
                           'surrounding background and the life-like setting.\n'
                           '\n'
                           'STYLE: Handcrafted product photography, romantic wedding style, soft natural lighting, '
                           'editorial image quality, modern minimalist Etsy aesthetic, 1:1 square aspect ratio.\n'
                           '\n'
                           'AVOID: altering the scrapbook design, changing embroidery patterns, mass-produced images, '
                           'harsh studio lighting, cluttered backgrounds, distracting props, AI errors, text overlays, '
                           'watermarks.'),
                          ('Lifestyle',
                           'Đôi uyên ương ngồi ngoài trời',
                           'This product image is a handcrafted wedding photo album taken from a reference photo. The '
                           'bride and groom are shown sitting close together in a romantic outdoor wedding setting, '
                           'gently holding the album in front of them. The album is the main focus of the photo, while '
                           "the couple's elegant wedding attire and the hazy flower garden background create a warm, "
                           'intimate, and sophisticated atmosphere. Soft natural sunlight illuminates the scene, '
                           'highlighting the linen fabric, the craftsmanship, and the elegant presentation of the '
                           'cover. The composition evokes a romantic and refined feel, with a soft depth of field that '
                           'focuses attention on the album while adding charm to the wedding story. A featured product '
                           'image on Etsy. \n'
                           '\n'
                           'IMPORTANT: The EXACT shape of the album from the reference photo is preserved. The linen '
                           'fabric, color palette, embroidery style, cover layout, proportions, and overall '
                           'handcrafted appearance are also preserved. Do not edit the album – only recreate the '
                           'surrounding background and scenes related to life. \n'
                           '\n'
                           'STYLE: Handmade product photography, romantic wedding lifestyle, soft natural lighting, '
                           'editorial quality, modern minimalist Etsy aesthetic, 1:1 square aspect ratio. \n'
                           '\n'
                           'AVOID: altering the album design, changing embroidery, mass production style, overly harsh '
                           'studio lighting, cluttered background, distracting props, AI errors, text overlays, '
                           'watermarks.'),
                          ('Product display',
                           'Trên bàn gỗ sáng + décor',
                           'The product image of this handcrafted wedding photo album is taken from a reference photo. '
                           'The album is placed on a light-colored wooden table in an elegant layout, either flat or '
                           'tilted, with one hand gently opening the cover, creating a natural feel. The album remains '
                           'the main focal point, prominently positioned at the center of the composition. Surrounding '
                           "it are delicate wedding-inspired decorative elements such as white roses, baby's breath, "
                           'eucalyptus leaves, voile ribbon, and a few scattered pearls, creating a romantic and '
                           'sophisticated atmosphere. The minimalist, clean, and bright background highlights the '
                           'handcrafted beauty of the album without distraction. \n'
                           '\n'
                           'Soft natural light illuminates the scene, highlighting the linen texture, delicate '
                           "embroidery, and the quality of the album's craftsmanship. The bright, airy, and elegant "
                           'background, with its serene wedding-inspired beauty, perfectly suits a high-end product on '
                           'Etsy. The composition creates a feeling of sophistication, femininity, romance, and '
                           'luxury. A featured product photo on Etsy. \n'
                           '\n'
                           'IMPORTANT: Maintain the EXACT shape of the album. Based on the reference photo. Keep the '
                           'linen fabric, color palette, embroidery style, cover layout, proportions, and overall look '
                           'of the handmade product. Do not edit the photo album or the detailed embroidery '
                           'description. Simply recreate the background and surrounding environment in a new style. \n'
                           '\n'
                           'STYLE: Handmade product photography, romantic wedding style, soft natural lighting, '
                           'editorial quality, modern minimalist Etsy aesthetic, 1:1 square aspect ratio. \n'
                           '\n'
                           'AVOID: Writing detailed embroidery instructions, changing the photo album design, changing '
                           'the photo album shape, harsh studio lighting, cluttered background, distracting props, '
                           'mass-produced look, AI errors, text overlays, watermarks.'),
                          ('Lifestyle',
                           'Đôi uyên ương đứng ngoài trời',
                           'This product photo of a handcrafted wedding scrapbook is taken from a reference image. The '
                           'bride and groom stand close together outdoors in a romantic garden wedding setting, softly '
                           'illuminated by warm natural sunlight. They hold the scrapbook together, holding it towards '
                           'the camera at chest level, making it the focal point of the photo. The bride wears an '
                           'elegant white lace wedding dress, while the groom wears a meticulously tailored light gray '
                           'suit with a boutonnière. Their faces are partially visible, but the main focus remains on '
                           'the scrapbook and its handcrafted beauty. \n'
                           '\n'
                           'The backdrop evokes a dreamy garden wedding atmosphere with soft greenery, subtle floral '
                           'details, and elegant wooden chairs, creating a refined and romantic wedding mood. The '
                           'composition looks natural, polished, and editorial, with the scrapbook placed prominently '
                           "in the couple's hands. The setting should evoke intimacy, love, and the high-end aesthetic "
                           'of a handcrafted wedding. \n'
                           '\n'
                           'The soft, natural yellow light highlights the linen texture, the delicate embroidery, and '
                           'the overall craftsmanship of the scrapbook. The background should be slightly blurred to '
                           'maintain focus on the product while preserving the elegant outdoor wedding setting. A '
                           'standout lifestyle product photo on Etsy. \n'
                           '\n'
                           'IMPORTANT: Keep the EXACT shape of the scrapbook as in the reference photo. Maintain the '
                           'linen material, color palette, embroidery style, cover layout, proportions, and overall '
                           'handcrafted look. Do not edit the scrapbook or detail the embroidery. Simply recreate a '
                           'new lifestyle setting and environment. \n'
                           '\n'
                           'STYLE: Handcrafted product photography, romantic wedding photo, soft natural light, '
                           'editorial quality, elegant garden setting, modern Etsy aesthetic, 1:1 square aspect '
                           'ratio. \n'
                           '\n'
                           'AVOID: Writing detailed embroidery instructions, changing scrapbook design, changing '
                           'scrapbook shape, harsh lighting, cluttered background, distracting props, stiff posing, '
                           'mass-produced look, AI errors, text overlays, watermarks.'),
                          ('Product display',
                           '3 cuốn flat lay trên tulle',
                           'Product photos of three handcrafted wedding scrapbooks are taken from reference images. '
                           'The three scrapbooks are arranged in a flat, elegant layout on a thin white tulle '
                           'background. One scrapbook is placed in the middle at the top, and the other two below, '
                           'forming a balanced triangle. Each scrapbook shares the same embroidery style and overall '
                           'layout, but each has a different linen cover color and personalized names and wedding '
                           'dates. The embroidery pattern should be kept general and not overly detailed, so this '
                           'suggestion can be used for many different scrapbook designs. \n'
                           '\n'
                           'Soft natural light illuminates the scene, highlighting the linen texture of each scrapbook '
                           'cover and the delicate handcrafted embroidery. The lighting should feel bright, clean, and '
                           'gentle, with minimal harsh shadows. The layout ensures that all three scrapbooks are '
                           'clearly visible and equally prominent, while decorative elements play only a secondary and '
                           'supporting role. \n'
                           '\n'
                           'IMPORTANT: Maintain the EXACT shape of the scrapbooks from the reference image. Keep the '
                           'linen fabric, embroidery style, handcrafted look, and overall cover proportions and '
                           'layout. Do not describe the embroidery details. Simply mention that the scrapbooks feature '
                           'personalized embroidery and handcrafted designs. The three scrapbooks should have '
                           'different cover colors and names, but maintain a consistent visual style and product '
                           'presentation. \n'
                           '\n'
                           'STYLE: Handcrafted product photography, romantic flat layout for weddings, soft natural '
                           'lighting, elegant Etsy aesthetic, clean editorial style, airy layout, high-end handcrafted '
                           'look, 1:1 square aspect ratio. \n'
                           '\n'
                           'AVOID: Writing detailed embroidery instructions, altering the scrapbook shape, changing '
                           'the overall scrapbook proportions, cluttered styling, dark lighting, harsh shadows, '
                           'distracting props, text overlays, watermarks, AI errors.'),
                          ('Gift box',
                           'Gift box',
                           'Create a high-quality, handcrafted product photo of a personalized wedding guest book as a '
                           'reference, neatly placed in an elegant gift box. The guest book is the main focus, resting '
                           'on soft silk paper or delicate tulle, with the box opened to showcase the product. The '
                           'cover is made of linen with hand-embroidered motifs. Surround the box with a few romantic '
                           "wedding accessories such as silk ribbons, baby's breath flowers, pearls, or a small "
                           'bouquet. Use soft, natural lighting, a clean, airy background, and a subtly romantic style '
                           'to highlight the linen material, the handcrafted feel, and the high-end look of the gift. '
                           'Keep the layout elegant, minimalist, and suitable for Etsy product photography.'))},
 'bouquet_ribbon': {'display_name': 'Bouquet Ribbon',
                    'aliases': ('Bouquet Ribbon',
                                'bouquet ribbon',
                                'bridal bouquet ribbon',
                                'wedding ribbon',
                                'embroidered ribbon',
                                'ribbon cưới',
                                'ribbon cuoi',
                                'dải ruy băng',
                                'dai ruy bang'),
                    'lock': 'the main product must remain the same long embroidered bouquet ribbon with the exact '
                            'ribbon width, fabric drape, stitched lettering or motif placement, edge finish, color, '
                            'and wedding accessory scale from the source image',
                    'shots': (('Lifestyle',
                               'Ribbon trong bó hoa cưới',
                               'Create a high-quality, handcrafted product image featuring a vibrant wedding bouquet '
                               'incorporating various flowers in similar or matching colors to the embroidered ribbon. '
                               'The bouquet is tied with a personalized embroidered ribbon bow and placed on a dark '
                               'tray covered with soft, elegant white voile fabric. Keep the embroidered ribbon as the '
                               'main focal point, clearly visible and not obscured, with the embroidery identical to '
                               'the original image, surrounded by a minimalist wedding backdrop. Add delicate '
                               'decorative details such as soft petals, greeting cards, wax-sealed kraft paper '
                               'envelopes, and sheer voile fabric. The setting should evoke a romantic, gentle, and '
                               'handcrafted feel with soft lighting and a harmonious pastel color palette. \n'
                               '\n'
                               'Use soft natural light from a window shining from the upper left to create subtle '
                               'shadows and highlight the fabric texture, ribbon weave, floral details, and '
                               'embroidery. The backdrop should be slightly muted and have warm tones, accentuating '
                               "the embroidered ribbon and the bouquet. The flowers don't distract attention from the "
                               'handcrafted details. \n'
                               '\n'
                               'Layout: A neat, balanced layout with ample space around the bouquet and ribbon. This '
                               'creates a high-end, handcrafted look, suitable for weddings, bridal gifts, wedding or '
                               'engagement photos, emphasizing softness, elegance, personalization, and love. \n'
                               '\n'
                               'IMPORTANT: The ribbon design must be EXACTLY as in the reference image. Do not change '
                               'anything. Keep the linen material, embroidery style, floral pattern, proportions, and '
                               'overall handcrafted look the same. Do not change the shape of the ribbon or the '
                               'embroidery placement. Only copy the surrounding wedding decorations and delicate '
                               'background. Clearly display the name and date embroidered at both ends of the '
                               'ribbon. \n'
                               '\n'
                               'STYLE: Close-up shots of handcrafted products, soft natural lighting, editorial '
                               'quality, modern minimalist Etsy-style aesthetics, romantic flat layout for weddings, '
                               '1:1 square aspect ratio. \n'
                               '\n'
                               'AVOID: blurry stitching, mechanical appearance, altered embroidery style, distorted '
                               'ribbon shapes, harsh lighting, overexposed highlights, cluttered layout, AI-generated '
                               'noise, text overlays, watermarks. Keep the background simple and elegant, focusing on '
                               'the embroidered ribbon and the delicate wedding setting.'),
                              ('Product display',
                               '2 ribbon song song',
                               'This image showcases handcrafted wedding ribbon products, taken from a reference '
                               'photograph. Two wedding vow books are beautifully displayed on a wooden tray, each '
                               'tied with delicate hand-embroidered ribbon bows. Embroidered names and wedding dates '
                               'are featured on the ribbons at their outermost ends. The ribbons, adorned with '
                               'delicate embroidered floral motifs and personalized inscriptions, gently hold the two '
                               'books together, adding a romantic touch to the composition. Surrounding the books are '
                               'wedding-inspired decorations, including a fresh wedding bouquet in colors matching the '
                               'embroidered flowers on the ribbons, a small wedding ring box with rings inside, and a '
                               'light, flowing veil.\n'
                               '\n'
                               'The composition is warm, refined, and elegant, evoking the romantic atmosphere of a '
                               'wedding. Soft natural light envelops the scene, highlighting the texture of the linen, '
                               'the embroidered ribbons, and the overall craftsmanship. The background remains clean, '
                               'bright, and Spacious and professional, this design showcases vow books and ribbons as '
                               'high-end handcrafted wedding accessories.\n'
                               '\n'
                               'IMPORTANT: The ribbon design is EXACTLY as shown in the reference image. The linen '
                               'material, embroidery style, floral pattern, proportions, and overall handcrafted look '
                               'are preserved. The shape of the ribbon or the embroidery placement remain unchanged. '
                               'Only the surrounding wedding decorations and soft backdrop are reproduced. The names '
                               'and dates embroidered at both ends of the ribbon are clearly visible.\n'
                               '\n'
                               'STYLE: Handcrafted product photography, romantic wedding style, soft natural lighting, '
                               'elegant decoration, editorial quality, refined Etsy aesthetics, 1:1 square aspect '
                               'ratio.\n'
                               '\n'
                               'AVOID: Ribbon design changes, vow book design changes, harsh studio lighting, '
                               'cluttered backdrops, distracting props, mass-produced look, AI errors, text overlays, '
                               'watermarks.'),
                              ('Product display',
                               'Ribbon đơn — dựng/cuộn',
                               'Product photos of handmade wedding ribbons are taken from reference images. The ribbon '
                               "is elegantly tied into a bow at the back of a bride's hair, showcasing the delicate "
                               'hand-embroidered floral design and personalized text. The ribbon is crafted from soft '
                               "linen fabric with embroidered flowers and a subtle heart symbol between the couple's "
                               'names and wedding date. The bow sits gracefully, adding a romantic touch to the bridal '
                               'hairstyle.\n'
                               '\n'
                               'The background is soft, airy, and minimal, allowing the focus to remain on the '
                               'beautifully embroidered ribbon and the fine details of the design. Soft natural light '
                               'highlights the fabric texture and intricate embroidery, creating a refined and elegant '
                               'atmosphere. The overall scene evokes a feminine, romantic wedding mood suitable for '
                               'premium handmade wedding accessories.\n'
                               '\n'
                               'IMPORTANT: The EXACT design of the ribbon from the reference photo is retained. '
                               'Maintain the linen texture, embroidery style, floral design, proportions, and overall '
                               'handcrafted look. Do not alter the shape of the ribbon or the placement of the '
                               'embroidery. Only reproduce the surrounding wedding decorations and soft background. '
                               'Clearly show the names and dates embroidery at both ends of the ribbon.\n'
                               '\n'
                               'STYLE: Handmade product photography, romantic bridal styling, soft natural lighting, '
                               'editorial quality, refined Etsy aesthetic, 1:1 square aspect ratio.\n'
                               '\n'
                               'AVOID: changing the ribbon design, changing the embroidery artwork, mass production '
                               'look, harsh studio lighting, cluttered background, distracting props, AI artifacts, '
                               'text overlays, watermarks.'),
                              ('Product display',
                               'Ribbon quanh hoa cô dâu',
                               'This product image of handcrafted wedding ribbons is taken from a reference photo. A '
                               'stunning wedding bouquet, tied with a delicately embroidered ribbon, sits on a soft '
                               'wooden table. The embroidered names and wedding date on the ribbons at the outermost '
                               'ends are clearly visible. The ribbons, adorned with embroidered floral motifs and '
                               'personalized lettering, add a romantic touch to the bouquet. Surrounding the bouquet '
                               'are delicate wedding-inspired details such as a classic pearl jewelry box, a perfume '
                               'bottle, and an elegantly sealed wedding envelope.\n'
                               '\n'
                               'The composition should evoke a sense of sophistication and romance, highlighting the '
                               'exquisite embroidery of the ribbons, the soft material, and the elegant wedding '
                               'decorations. Soft natural light envelops the scene, accentuating the details of the '
                               'ribbons and the bouquet. The backdrop is kept clean and gently blurred, creating an '
                               'elegant, cozy wedding atmosphere that emphasizes the handcrafted quality of the ribbon '
                               "and its connection to the couple's special day.\n"
                               '\n'
                               'IMPORTANT: The EXACT design of the ribbon from the reference photo must be preserved. '
                               'Maintain the linen fabric, embroidery style, floral design, proportions, and overall '
                               'handcrafted look. Do not change the shape of the ribbon or the placement of the '
                               'embroidery. Only copy the surrounding wedding decorations and the soft backdrop. Keep '
                               'EXACTLY the name and date embroidered at both ends of the ribbon.\n'
                               '\n'
                               'STYLE: Handcrafted product photography, romantic wedding style, soft natural lighting, '
                               'editorial photo quality, refined Etsy aesthetics, 1:1 square aspect ratio.\n'
                               '\n'
                               'AVOID: ribbon design changes, bouquet shape changes, harsh studio lighting, cluttered '
                               'backdrops, distracting props, AI errors, text overlays, watermarks.'),
                              ('Product display',
                               'Bộ ribbon thêu',
                               'Product photos of handmade wedding ribbons are taken from reference images. A set of '
                               'embroidered wedding ribbons is arranged gracefully on soft satin fabric, featuring '
                               'with personalized text and delicate floral embroidery. The ribbon is carefully placed '
                               'next to a pair of wedding rings, an elegant wedding invitation with a wax seal, and '
                               'soft flower petals, creating a romantic and sophisticated scene. The composition is '
                               'polished and refined, with a soft and clean aesthetic that highlights the beauty of '
                               'the ribbons and the elegance of the surrounding wedding decor. The ribbons are '
                               'slightly curled at the edges, adding texture and depth to the image.\n'
                               '\n'
                               'Soft natural light gently illuminates the scene, bringing out the fine details of the '
                               'embroidery and fabric texture. The background remains clean, bright, and softly '
                               'blurred, evoking an intimate wedding atmosphere suitable for premium handmade '
                               'accessories. \n'
                               '\n'
                               'IMPORTANT: The EXACT design of the ribbon from the reference photo is retained. '
                               'Maintain the linen texture, embroidery style, floral design, proportions, and overall '
                               'handcrafted look. Do not alter the shape of the ribbon or the placement of the '
                               'embroidery. Only reproduce the surrounding wedding decorations and soft background. '
                               'Clearly show the names and dates embroidery at both ends of the ribbon.\n'
                               '\n'
                               'STYLE: Handmade product photography, romantic wedding styling, soft natural lighting, '
                               'editorial quality, refined Etsy aesthetic, 1:1 square aspect ratio.\n'
                               '\n'
                               'AVOID: changing the ribbon design, changing the floral embroidery, harsh studio '
                               'lighting, cluttered background, distracting props, AI artifacts, text overlays, '
                               'watermarks.'),
                              ('Product display',
                               'Trang trí chai rượu cưới',
                               'This product photo of handcrafted wedding ribbons is taken from a reference image. A '
                               'wedding wine bottle is adorned with an exquisitely hand-embroidered ribbon bow, '
                               'creating a romantic and formal atmosphere. The ribbon, embellished with personalized '
                               'floral embroidery and lettering, is carefully tied around the neck of the bottle. The '
                               'scene includes a champagne glass, a multi-tiered wedding cake, a cake plate, and a '
                               'fresh wedding bouquet in the same color tone as the embroidered flowers on the ribbon, '
                               'elegantly placed nearby, adding to the wedding ambiance.\n'
                               '\n'
                               'Soft natural light envelops the scene, highlighting the delicate details of the '
                               'ribbon, the fabric quality, and the overall craftsmanship. The background remains '
                               'clean and soft, with elements blurred, creating an intimate and elegant wedding '
                               'atmosphere. The ribbon is the main focal point, while the surrounding decorative '
                               'elements add depth and story to the photograph.\n'
                               '\n'
                               'IMPORTANT: The EXACT design of the ribbon from the reference photo is retained. '
                               'Maintain the linen texture, embroidery style, floral design, proportions, and overall '
                               'handcrafted look. Do not alter the shape of the ribbon or the placement of the '
                               'embroidery. Only reproduce the surrounding wedding decorations and soft background. '
                               'Clearly show the names and dates embroidery at both ends of the ribbon. \n'
                               '\n'
                               'STYLE: Handmade product photography, romantic wedding style, soft natural lighting, '
                               'elegant decorations, editorial photo quality, refined Etsy aesthetics, 1:1 square '
                               'aspect ratio.\n'
                               '\n'
                               'AVOID: Changing ribbon designs, altering embroidery patterns, harsh studio lighting, '
                               'cluttered backgrounds, distracting props, AI errors, text overlays, watermarks.'),
                              ('Product display',
                               'Trong giỏ cưới',
                               'Product photos of handmade wedding ribbons are taken from reference images. A wedding '
                               'basket is elegantly decorated with a hand-embroidered ribbon bow, with personalized '
                               'text and floral embroidery. The ribbon is carefully tied around the handle of the '
                               'basket, which is filled with soft pink rose petals, creating a romantic and whimsical '
                               'atmosphere. The basket is placed on a wooden table, surrounded by soft wedding decor '
                               'elements like delicate flowers, candles, and lace accents, all evoking a refined and '
                               'charming wedding scene.\n'
                               '\n'
                               'Soft natural light gently illuminates the scene, highlighting the embroidered ribbon, '
                               'the soft texture of the linen fabric, and the overall handmade quality. The background '
                               'remains clean and soft, with blurred floral details and wedding table elements, '
                               'ensuring the focus stays on the ribbon and basket. The composition is polished, '
                               'elegant, and perfectly suited for a wedding celebration.\n'
                               '\n'
                               'IMPORTANT: The EXACT design of the ribbon from the reference photo is retained. '
                               'Maintain the linen texture, embroidery style, floral design, proportions, and overall '
                               'handcrafted look. Do not alter the shape of the ribbon or the placement of the '
                               'embroidery. Only reproduce the surrounding wedding decorations and soft background. '
                               'Clearly show the names and dates embroidery at both ends of the ribbon. \n'
                               '\n'
                               'STYLE: Handmade product photography, romantic wedding styling, soft natural light, '
                               'editorial quality, refined Etsy aesthetic, 1:1 square aspect ratio.\n'
                               '\n'
                               'AVOID: changing the ribbon design, changing the floral embroidery, harsh studio '
                               'lighting, cluttered background, distracting props, AI artifacts, text overlays, '
                               'watermarks.'),
                              ('Lifestyle',
                               'Cô dâu cầm ribbon',
                               'This image of the handcrafted wedding ribbon is taken from a reference photo. In the '
                               'photo, the bride holds a wedding bouquet in the same color tone as the flowers '
                               'embroidered on the ribbon, delicately tied with a hand-embroidered ribbon bow, in an '
                               'outdoor wedding setting. The ribbon is decorated with embroidered floral motifs and '
                               'personalized lettering, the names and date at both ends of the ribbon remain '
                               'unchanged, adding to the charm and romance of the bouquet. The bride smiles radiantly, '
                               'and the scene captures her happy moment with the groom, surrounded by gently falling '
                               'flower petals.\n'
                               '\n'
                               'Soft natural light floods the scene, highlighting the delicate embroidery on the '
                               "ribbon, the fresh lilies in the bouquet, and the bride's elegant wedding dress. The "
                               'background is softened by a gentle green and the romantic outdoor wedding atmosphere, '
                               'focusing on the bride, the bouquet, and the ribbon.\n'
                               '\n'
                               'IMPORTANT: The EXACT design of the ribbon from the reference photo is retained. '
                               'Maintain the linen material, embroidery style, floral design, proportions, and overall '
                               'handcrafted look. Do not change the shape of the ribbon or the placement of the '
                               'embroidery. Only reproduce the surrounding wedding decorations and the soft '
                               'background. Clearly show the name and date embroidered at both ends of the ribbon.\n'
                               '\n'
                               'STYLE: Handcrafted product photography, romantic wedding style, soft natural lighting, '
                               'editorial photo quality, refined Etsy aesthetic, 1:1 square aspect ratio.\n'
                               '\n'
                               'AVOID: Changing the ribbon design, altering the shape of the bouquet, harsh studio '
                               'lighting, cluttered background, distracting props, AI errors, text overlays, '
                               'watermarks.'),
                              ('Lifestyle',
                               'Ribbon trên trang phục cô dâu',
                               'This image of the handcrafted wedding ribbon is taken from a reference photo. A '
                               'delicate wedding ribbon, with embroidered floral motifs and personalized lettering, is '
                               'elegantly tied around the wedding bouquet. The bouquet is a beautiful combination of '
                               'fresh flowers in the same color tone as the flowers embroidered on the ribbon, '
                               'creating a soft and romantic look. The ribbon is carefully tied into a bow at the base '
                               'of the bouquet, with personalized lettering clearly visible at both ends. The '
                               'composition captures the image of the bride gently holding the fresh flowers with the '
                               'prominent ribbon draped across her waist, seated on a wooden chair in an outdoor '
                               'wedding setting, evoking a peaceful and romantic wedding moment.\n'
                               '\n'
                               'Soft natural light floods the scene, highlighting the fabric texture and delicate '
                               'embroidery of the ribbon, while also emphasizing the gentle lavender purple and the '
                               'rustic, elegant beauty of the entire wedding decoration. The backdrop is softened by '
                               'light green foliage, creating an intimate atmosphere and focusing on the wedding. The '
                               'overall effect should be romantic, graceful, and sophisticated.\n'
                               '\n'
                               'IMPORTANT: The EXACT design of the ribbon from the reference image is retained. '
                               'Maintain the linen texture, embroidery style, floral design, proportions, and overall '
                               'handcrafted style. Do not change the shape of the ribbon or the embroidery placement. '
                               'Only reproduce the surrounding wedding decorations and the soft backdrop. Clearly '
                               'display the names and dates embroidered at both ends of the ribbon.\n'
                               '\n'
                               'STYLE: Handcrafted product photography, romantic wedding style, soft natural lighting, '
                               'edited image quality, refined Etsy aesthetics, 1:1 square aspect ratio.\n'
                               '\n'
                               'AVOID: Changing the ribbon design, altering the floral embroidery pattern, harsh '
                               'studio lighting, cluttered backdrop, distracting props, AI errors, text overlays, '
                               'watermarks.'),
                              ('Lifestyle',
                               'Chú rể với ribbon #1',
                               'The product image for this handmade wedding ribbon is taken from a reference photo. In '
                               'the photo, the bride holds a bouquet of fresh flowers, matching or similar in color to '
                               'the flowers embroidered on the ribbon, tied with soft linen ribbon, the bouquet is '
                               'decorated with embroidered flowers and personalized lettering. The ribbon is tied into '
                               'a delicate bow at the base of the fresh bouquet, matching the color of the embroidered '
                               "flowers on the ribbon, highlighting the couple's names and wedding date (the names and "
                               'date are embroidered at both ends of the ribbon). The bride smiles radiantly, holding '
                               'the bouquet close to her chest, in an outdoor wedding setting, capturing a genuine and '
                               'happy wedding moment.\n'
                               '\n'
                               'The backdrop is a lush, vibrant garden with gently falling colored paper scraps, '
                               'creating a festive and romantic atmosphere. Natural light highlights the delicate '
                               'embroidery on the ribbon and fabric, while the focus remains on the bride, the '
                               'bouquet, and the beautifully tied ribbon. A cozy, cheerful, and romantic setting, '
                               'perfect for showcasing high-end handcrafted wedding accessories.\n'
                               '\n'
                               'IMPORTANT: The EXACT design of the ribbon from the reference photo is retained. '
                               'Maintain the linen texture, embroidery style, floral design, proportions, and overall '
                               'handcrafted look. Do not change the shape of the ribbon or the placement of the '
                               'embroidery. Only copy the surrounding wedding decorations and the soft material. '
                               'Background. Clearly display the name and date embroidered at both ends of the ribbon.\n'
                               '\n'
                               'STYLE: Handcrafted product photography, romantic wedding style, soft natural lighting, '
                               'editorial photo quality, refined Etsy aesthetics, 1:1 square aspect ratio.\n'
                               '\n'
                               'AVOID: Changing the ribbon design, altering the floral embroidery, harsh studio '
                               'lighting, cluttered background, distracting props, AI errors, text overlays, '
                               'watermarks.'),
                              ('Lifestyle',
                               'Chú rể với ribbon #2',
                               'The product image for this handmade wedding ribbon is taken from a reference photo. In '
                               'the photo, the bride holds a bouquet of fresh flowers, matching or similar in color to '
                               'the flowers embroidered on the ribbon, tied with soft linen ribbon, decorated with '
                               'embroidered flowers and personalized lettering. The ribbon is tied into a delicate bow '
                               'at the base of the fresh bouquet, matching the color of the embroidered flowers on the '
                               "ribbon, highlighting the couple's names and wedding date (the names and date are "
                               'embroidered at both ends of the ribbon). The bride smiles radiantly, holding the '
                               'bouquet close to her chest, in an outdoor wedding setting, capturing a genuine and '
                               'happy wedding moment.\n'
                               '\n'
                               'The backdrop is a lush, vibrant garden with gently falling colored paper scraps, '
                               'creating a festive and romantic atmosphere. Natural light highlights the delicate '
                               'embroidery on the ribbon and fabric, while the focus remains on the bride, the '
                               'bouquet, and the beautifully tied ribbon. A cozy, cheerful, and romantic setting, '
                               'perfect for showcasing high-end handcrafted wedding accessories.\n'
                               '\n'
                               'IMPORTANT: The EXACT design of the ribbon from the reference photo is retained. '
                               'Maintain the linen texture, embroidery style, floral design, proportions, and overall '
                               'handcrafted look. Do not change the shape of the ribbon or the placement of the '
                               'embroidery. Only copy the surrounding wedding decorations and the soft material. '
                               'Background. Clearly display the name and date embroidered at both ends of the ribbon.\n'
                               '\n'
                               'STYLE: Handcrafted product photography, romantic wedding style, soft natural lighting, '
                               'editorial photo quality, refined Etsy aesthetics, 1:1 square aspect ratio.\n'
                               '\n'
                               'AVOID: Changing the ribbon design, altering the floral embroidery, harsh studio '
                               'lighting, cluttered background, distracting props, AI errors, text overlays, '
                               'watermarks.'))},
 'wedding_hoop': {'display_name': 'Wedding Hoop',
                  'aliases': ('Wedding Hoop',
                              'wedding hoop',
                              'embroidery hoop wedding',
                              'embroidered hoop',
                              'hoop cưới',
                              'hoop cuoi',
                              'vòng thêu cưới',
                              'vong theu cuoi'),
                  'lock': 'the main product must remain the same circular embroidery hoop with the exact wooden hoop '
                          'frame, stretched fabric, embroidered floral/name layout, stitch colors, hanging/display '
                          'scale, and wedding keepsake identity from the source image',
                  'shots': (('Product display',
                             'Flat display — thêu hoa',
                             'This image of the handcrafted wedding ring is taken from a reference photo. The wedding '
                             'ring is displayed elegantly and flat, highlighting the delicate floral embroidery with '
                             'personalized names and wedding dates. The ring rests gently on a soft white satin '
                             'background, surrounded by romantic wedding-inspired decorative elements such as a '
                             'bouquet of fresh flowers matching the embroidery on the ring stand, wedding invitations, '
                             'and a pair of intertwined wedding rings. The ring is the main focal point, with its '
                             'delicate embroidery clearly and elegantly displayed. \n'
                             '\n'
                             'Soft natural light floods the scene, highlighting the fabric texture, embroidery, and '
                             'craftsmanship of the ring. The clean, soft, and slightly frosted background creates a '
                             'warm and elegant wedding atmosphere. The composition conveys a sense of sophistication, '
                             'romance, and is perfectly suited to showcasing a high-end wedding accessory. \n'
                             '\n'
                             'IMPORTANT: The EXACT design of the wedding ring from the reference photo is retained. '
                             'Maintain the fabric texture, embroidery style, floral design, proportions, and overall '
                             'handcrafted look. Do not alter the shape of the rings or embroidery patterns. Only '
                             'recreate the surrounding wedding decorations and soft background. \n'
                             '\n'
                             'STYLE: Handcrafted product photography, romantic wedding style, soft natural lighting, '
                             'editorial photo quality, refined Etsy aesthetics, 1:1 square aspect ratio. \n'
                             '\n'
                             'AVOID: editing wedding photo frame designs, changing embroidery patterns, harsh studio '
                             'lighting, cluttered backgrounds, distracting props, AI errors, text overlays, '
                             'watermarks.'),
                            ('Cận thêu tay',
                             'Cận thêu tay',
                             'Take a close-up photo of the fabric ring ornament from the reference image, focusing on '
                             'the exquisite hand-embroidered details, with clear threads and beautiful stitching. The '
                             'fabric ring frame should be the main focal point, highlighting the embroidery and '
                             'stitching. Soft, natural light from the side will emphasize the depth of the embroidery, '
                             'with a shallow depth of field to create a hazy effect around the fabric. The fabric '
                             'should be neutral and clean-colored, and the handcrafted details must be clearly '
                             'visible, highlighting the quality of the product.\n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of the fabric ring ornament from the reference '
                             'image. Preserve the fabric material, embroidery details, thread color, stitching, '
                             'proportions, and handcrafted characteristics. Do not alter the ring ornament in any '
                             'way—only enlarge the existing embroidery details.\n'
                             '\n'
                             'STYLE: Close-up of the handcrafted product, soft natural light, high-quality editing, '
                             'modern minimalist Etsy aesthetic, proportions. Square 1:1.\n'
                             '\n'
                             'AVOID: blurry seams, images that look machine-generated, edited embroidery patterns, '
                             'harsh lighting, overexposed images, highlights, AI errors, text overlaid on images, '
                             'watermarks.'),
                            ('Product display',
                             'Giữa vest chú rể & áo cô dâu',
                             'Product photos of these handcrafted wedding rings are taken from a reference image. A '
                             "wedding ring with delicate embroidery is placed between the groom's suit and the bride's "
                             'wedding dress (the dress gently drapes over the suit), surrounded by elegant wedding '
                             'accessories, soft petals, and a fresh bouquet, all cleverly arranged to create a '
                             'romantic and sophisticated wedding scene. \n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT design of the wedding wreath from the reference image. '
                             'Keep the fabric, embroidery style, proportions, and overall handcrafted look. Do not '
                             'change the design of the wreath or the embroidery. Only recreate the surrounding wedding '
                             'decorations and the soft background environment. \n'
                             '\n'
                             'STYLE: Handcrafted product photography, romantic wedding style, soft natural lighting, '
                             'edited image quality, refined Etsy aesthetics, 1:1 square aspect ratio. \n'
                             '\n'
                             'AVOID: Changing the wedding wreath design, editing embroidery details, studio lighting. '
                             'Harsh, distracting background, distracting props, AI errors, text overlays, watermarks.'),
                            ('Lifestyle',
                             'Cô dâu đứng cầm showcase',
                             'This image of a handcrafted wedding ring is taken from a reference photo. The bride is '
                             'standing and holding the exquisitely embroidered wedding ring, showcasing the soft linen '
                             'fabric with hand-embroidered floral motifs (a small ring ornament, only 25 cm). She is '
                             'wearing a romantic, off-the-shoulder wedding dress with natural lace accents. The bride '
                             'is standing in the setting of a beach wedding. \n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT design of the wedding wreath from the reference photo. '
                             'Keep the fabric, embroidery style, floral motifs, proportions, and overall handcrafted '
                             'look. Do not change the wreath design or the embroidered lettering. \n'
                             '\n'
                             'STYLE: Handcrafted product photography, natural wedding style, soft natural lighting, '
                             'edited image quality, refined Etsy aesthetics, 1:1 square aspect ratio. \n'
                             '\n'
                             'AVOID: Changing the wedding wreath design, adjusting embroidery details, overly harsh '
                             'studio lighting, cluttered background, distracting props, AI errors, text overlays." The '
                             'copy is blurry, the image is too dramatic.'),
                            ('Product display',
                             '4 vòng trên voile trắng',
                             'These handcrafted wedding ring product photos are taken from reference images. Four '
                             'wedding rings are elegantly displayed on a soft white voile fabric, adorned with '
                             'delicate embroidered flowers. Each ring is personalized with a DIFFERENT name and date, '
                             'while other embroidery motifs are the same. The rings are arranged symmetrically, each '
                             'clearly displayed to highlight the delicate details of the fabric, embroidery, and '
                             'personalized inscription. \n'
                             '\n'
                             'The surrounding setting includes soft rose petals, fresh flowers, and elegant greenery, '
                             'adding to the romantic and luxurious atmosphere of the wedding. The soft, airy, and '
                             'natural backdrop creates a warm and elegant space. Gentle natural light highlights the '
                             'texture of the fabric and embroidery, emphasizing the exquisite quality and '
                             'craftsmanship of each wedding ring. \n'
                             '\n'
                             'IMPORTANT: The EXACT design of the wedding rings from the reference image is retained. '
                             'Linen fabric texture, style...The embroidery, floral patterns, and proportions are all '
                             'preserved. The overall handcrafted look is retained. The wreath or embroidery design '
                             'remains unchanged. Only the surrounding wedding decorations and the soft background '
                             'environment are recreated. \n'
                             '\n'
                             'STYLE: Handcrafted product photography, romantic wedding style, \n'
                             'Soft natural lighting, editorial photo quality, sophisticated Etsy style. 1:1 square '
                             'aspect ratio. \n'
                             '\n'
                             'AVOID: Changing the wedding photo frame design, changing the embroidery patterns, overly '
                             'harsh studio lighting, cluttered background, distracting props, AI errors, text '
                             'overlays, watermarks.'),
                            ('Gift box',
                             'Gift box',
                             'This image of the handcrafted wedding ring is taken from a reference photo. The ring '
                             'ornament is elegantly displayed inside a soft gift box lined with delicate silk paper. '
                             'The ring, crafted from soft linen with exquisite embroidery, is surrounded by delicate '
                             'wedding ornaments, such as small green leaves, flowers, and elegant ribbons, '
                             'contributing to a romantic and thoughtful appearance. \n'
                             '\n'
                             'The gift box is tilted to highlight the ring ornament, allowing the delicate details of '
                             'the embroidery and fabric to become the focal point. The scene is softly illuminated by '
                             'natural light, highlighting the handcrafted quality of the ring and the thoughtful '
                             'wedding gift atmosphere. The background remains clean, soft, and hazy, evoking a refined '
                             'and intimate mood, perfect for showcasing high-end handcrafted wedding accessories. \n'
                             '\n'
                             'IMPORTANT: The EXACT design of the ring ornament from the reference photo is preserved. '
                             'The fabric, embroidery style, floral design, proportions, and overall handcrafted '
                             'appearance are maintained. Do not change the wreath design or embroidery details. Simply '
                             'recreate the surrounding wedding decorations and a soft backdrop. \n'
                             '\n'
                             'STYLE: Handmade product photography, romantic wedding style, soft natural lighting, \n'
                             'Elegant gift presentation, sophisticated Etsy style, 1:1 square aspect ratio. \n'
                             '\n'
                             'AVOID: Changing the wedding wreath design, altering embroidery details, overly harsh '
                             'studio lighting, cluttered backdrop, distracting props, mass-produced look, AI errors, '
                             'text overlays, watermarks.'),
                            ('Lifestyle',
                             'Tay thêu — process lifestyle',
                             'Lifestyle Product Photo: Handmade Wedding Anniversary Embroidery Frame. A pair of '
                             'delicate hands manipulate the embroidery frame with needle and thread (needle eyelets '
                             'are threaded), while the frame remains the main focus and is clearly displayed (frame '
                             'not shown in the photo). Soft natural light shines from the upper left window, the '
                             'background is gently blurred with warm neutral tones, and the shallow depth of field '
                             'creates a delicate, authentic feel of the handmade product on Etsy. \n'
                             '\n'
                             'IMPORTANT: Keep the EXACT shape of the embroidery frame from the reference photo. Keep '
                             'the wooden frame, fabric, color palette, photo location, embroidery details, and '
                             'proportions. Do not edit the embroidery frame – simply create a new process scene around '
                             'it. \n'
                             '\n'
                             "STYLE: Handmade product photography, soft natural light, editorial quality, Etsy's "
                             'modern minimalist aesthetic, 1:1 square aspect ratio. \n'
                             '\n'
                             'AVOID: altering the product, Unrealistic hand gestures, cluttered workspace, harsh '
                             'lighting, AI errors, text overlays, watermarks.'),
                            ('Lifestyle',
                             'Đôi uyên ương cầm #1',
                             'This product image is a photograph of a handcrafted wedding ring taken from a reference '
                             'photo. The bride and groom are standing next to each other, holding the ring at waist '
                             'level (the ring size is exactly the same as in the reference photo, only 22 cm). The '
                             'bride and groom are wearing wedding attire, and their faces are not visible in the '
                             'photo. The ring is clearly photographed, with the delicate details of the fabric and '
                             'embroidery clearly visible. The couple are standing close together, and the soft '
                             'lighting highlights the ring. \n'
                             '\n'
                             'IMPORTANT: The EXACT design of the wedding ring from the reference photo is preserved. '
                             'The fabric texture, embroidery style, proportions, and overall handcrafted appearance '
                             'are maintained. The ring design or embroidery details are not altered. \n'
                             '\n'
                             'STYLE: Handcrafted product photography, romantic wedding style, soft natural lighting, '
                             'edited image quality, refined Etsy aesthetics, 1:1 square aspect ratio. \n'
                             '\n'
                             'AVOID: Changing the wedding photo frame design, altering details... Embroidery details, '
                             'harsh studio lighting, distracting backdrops, distracting props, AI errors, text '
                             'overlays, watermarks.'),
                            ('Product display',
                             '2 vòng tên khác — trên gỗ',
                             'These two product images are taken from a reference photo. Two identical rings with '
                             'different names are displayed on a rustic wooden surface, surrounded by antique books, '
                             'spools of thread, and dried flowers, evoking a fresh, handcrafted, and romantic '
                             'atmosphere. The ring with its delicate embroidery is the focal point of the composition. '
                             'The names and wedding date are clearly embroidered, adding intimacy and sentiment to the '
                             'design. Soft natural light floods the scene, highlighting the fabric texture and the '
                             'exquisite embroidery details. The background includes natural light streaming in from '
                             'the window, creating a gentle, shimmering glow. \n'
                             '\n'
                             'IMPORTANT: The wedding ring design from the reference photo is kept exactly as shown. '
                             'The fabric texture, embroidery style, floral design, proportions, and overall '
                             'handcrafted look are preserved. The design of the ring or the embroidery is not altered. '
                             'Only the surrounding decorations and the soft background environment are reproduced. \n'
                             '\n'
                             'STYLE: Handmade product photography, rustic wedding style, soft natural lighting, edited '
                             'image quality, refined Etsy aesthetics, 1:1 square aspect ratio. \n'
                             '\n'
                             'AVOID: Changing the wedding ring embroidery design, changing the photo frame design, '
                             'using overly harsh studio lighting. Poor lighting, cluttered background, distracting '
                             'props, AI errors, text overlapping images, blurry images.'),
                            ('Product display',
                             'Treo trên móc tường',
                             'This product image of a handmade wedding wreath is taken from a reference photo. An '
                             'elegantly displayed wedding wreath, tied with string and hung on a hook on the wall in '
                             'the wedding space. The wreath, with its delicate embroidery and personalized '
                             'inscription, is the highlight of the composition, adding to the wedding atmosphere. It '
                             'is framed in a wooden hoop with soft linen fabric, carefully crafted to accentuate the '
                             'delicate details of the design. \n'
                             '\n'
                             'IMPORTANT: The wedding wreath design from the reference photo is kept exactly as shown '
                             'in the image. The linen material, embroidery style, floral design, proportions, and '
                             'overall handmade appearance are preserved. The wreath design or embroidery is not '
                             'altered. Only the surrounding wedding decorations and the soft background environment '
                             'are reproduced. \n'
                             '\n'
                             'STYLE: Handmade product photography, romantic wedding style, soft natural lighting, '
                             'edited image quality, refined Etsy aesthetics, 1:1 square aspect ratio. \n'
                             '\n'
                             'AVOID: alterations Wedding frame design, embroidery pattern changes, harsh studio '
                             'lighting, distracting backdrop, distracting props, AI errors, text overlays, '
                             'watermarks.'),
                            ('Product display',
                             'Flat — cận chi tiết thêu #2',
                             'This product photo of a handmade wedding ring is taken from a reference image. The ring '
                             'is displayed elegantly and flat, focusing on the exquisite embroidery technique. The '
                             'ring is placed on a soft linen surface, surrounded by sewing tools such as embroidery '
                             'thread, needles with thread already threaded, a sewing mat, and a small pair of '
                             'scissors. The wedding ring is placed nearby, adding symbolic meaning to the scene. The '
                             'image captures the delicate details of the fabric, the embroidery stitches, and the '
                             'quality of the handmade ring. The background is a handmade work table. \n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT design of the wedding ring from the reference image. '
                             'Preserve the fabric texture, embroidery style, proportions, and overall handmade '
                             'appearance. Do not alter the design of the ring or the embroidery. Only copy the '
                             'surrounding sewing tools and the soft background environment. \n'
                             '\n'
                             'STYLE: Handmade product photography, romantic wedding style, soft natural lighting, '
                             'high-quality editing, refined Etsy aesthetics, 1:1 square aspect ratio. \n'
                             '\n'
                             'AVOID: Changing the wedding embroidery frame design, altering the embroidery artwork, '
                             'harsh studio lighting, cluttered backgrounds, distracting props, AI errors, text '
                             'overlays, watermarks.'),
                            ('Lifestyle',
                             'Đôi uyên ương cầm #2',
                             'This product photo of a handcrafted wedding ring is taken from a reference image. The '
                             'bride and groom are holding their wedding rings in a wedding setting. The ring is the '
                             'main focal point, with personalized names, dates, and a stunning floral design. Soft '
                             'natural light highlights the fabric and embroidery, while surrounding decorations add a '
                             'natural feel to the outdoor setting. \n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT design of the wedding ring. Preserve the fabric texture, '
                             'embroidery style, proportions, and overall handcrafted look. \n'
                             '\n'
                             'STYLE: Handcrafted product photography, romantic wedding style, soft natural light, '
                             'refined Etsy aesthetic, 1:1 square aspect ratio. \n'
                             '\n'
                             'AVOID: altering the wedding ring design, harsh lighting, cluttered background, '
                             'distracting props, AI errors, text overlays, watermarks.'),
                            ('Lifestyle',
                             'Đôi từ phía sau — outdoor',
                             'This product photo of a handcrafted wedding ring was taken from a reference image. The '
                             'bride and groom are photographed from behind in an outdoor wedding setting, both holding '
                             'the ring ornament in their hands and raising it towards the clear blue sky. The couple '
                             'stands close together in elegant wedding attire, creating a romantic and joyful '
                             'atmosphere. The ring ornament is the main focal point of the photo (a small, not overly '
                             'large, ring), while the couple, the open sky, and the distant greenery create an '
                             'emotional love story. \n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of the wedding ring from the reference image. Keep '
                             'the material, embroidery style, color palette, proportions, and overall handcrafted '
                             'appearance unchanged. Do not edit the embroidery details. Do not edit the wedding '
                             'ring. \n'
                             '\n'
                             'STYLE: Handcrafted product photography, romantic wedding style, soft natural lighting, '
                             'editorial quality, refined Etsy aesthetics, 1:1 square aspect ratio. \n'
                             '\n'
                             'AVOID: changing the wedding ring design, editing "Correct embroidery details, harsh '
                             'studio lighting, cluttered background, distracting props, AI errors, text overlays, '
                             'watermarks.'),
                            ('Product display',
                             'Kệ nhỏ ngoài trời — reception',
                             'The embroidery frame, photographed from the reference image, is displayed on a small '
                             'shelf on an outdoor reception table at a sunny wedding. The frame is positioned upright '
                             'on a small wooden stand, neatly arranged on the reception table. Surrounding the frame '
                             'are delicate wedding decorations such as linen tablecloths, a few candles, delicate '
                             'dried flowers, and other romantic details in light tones, along with a large wedding '
                             'bouquet that highlights the embroidery on the frame. \n'
                             '\n'
                             'IMPORTANT: Maintain the EXACT shape of the embroidery frame from the reference image. '
                             'Keep the wooden frame, fabric material, ribbon placement, embroidery details, color '
                             'palette, typography, and proportions the same. Do not alter the embroidery frame – '
                             'simply create a new backdrop and arrange the display around it. \n'
                             '\n'
                             'STYLE: Handcrafted product photography, soft natural lighting, edited image quality, '
                             'modern minimalist Etsy-style aesthetic, elegant wedding decorations, square frame '
                             'proportions. 1:1. \n'
                             '\n'
                             'AVOID: altering product appearance, mass production feel, harsh studio lighting, overly '
                             'cluttered or messy backgrounds, AI errors, text overlays, watermarks.'))},
 'hoops_with_photos': {'display_name': 'Hoops With Photos',
                       'aliases': ('Hoops With Photos',
                                   'hoops with photos',
                                   'photo hoop',
                                   'baby photo hoop',
                                   'baby photo frame',
                                   'baby picture frame',
                                   'personalized baby photo frame',
                                   'baby embroidery frame',
                                   'embroidery hoop photo',
                                   'khung thêu ảnh',
                                   'khung theu anh',
                                   'khung dung anh baby',
                                   'khung anh baby',
                                   'khung dung anh',
                                   'vòng thêu ảnh',
                                   'vong theu anh'),
                       'lock': 'the main product must remain the same baby/nursery embroidery hoop or frame with '
                               'photo/name/date elements exactly as in the source image, preserving hoop/frame shape, '
                               'photo placement, stitched name/date layout, fabric texture, and keepsake wall decor '
                               'scale',
                       'shots': (('Product display',
                                  'Kệ gỗ nursery — 2 khung',
                                  'The product image showcases a personalized embroidery frame with a baby theme, as '
                                  'shown in the reference photo. Two picture frames with two different names and two '
                                  'different photos are placed upright against a stack of books on a light-colored '
                                  'wooden shelf, surrounded by soft baby items such as stuffed animals, a small stack '
                                  "of children's books, and a ceramic vase with delicate dried flowers. Soft natural "
                                  'light streams in from the window above and to the left, the background is a '
                                  'minimalist, slightly dark baby room with bright white tones, the items are placed '
                                  'in the center with ample space, and the shallow depth of field creates a gentle '
                                  'bokeh effect. A standout product image for Etsy.\n'
                                  '\n'
                                  'IMPORTANT: Keep the EXACT shape of the embroidery frame from the reference photo. '
                                  'Keep the wooden frame, fabric, color palette, embroidery thread colors, photo '
                                  'placement, embroidery details, and proportions. Do not modify the embroidery frame '
                                  '– only create a new background and style around it. photorealistic, natural '
                                  'lighting, linen texture visible, high detail, product photography style\n'
                                  '\n'
                                  'STYLE: Handcrafted product photography, soft natural lighting, high-quality '
                                  'editing, minimalist modern Etsy aesthetic, 1:1 square aspect ratio.\n'
                                  '\n'
                                  'AVOID: altering product appearance, mass production feel, overly harsh studio '
                                  'lighting, cluttered backgrounds, visually distracting images, AI errors, text '
                                  'overlays, watermarks.'),
                                 ('Lifestyle',
                                  'Trong cũi gỗ — buổi sáng',
                                  'Lifestyle photography: the embroidery frame from the reference image sits in a '
                                  'white wooden cradle, surrounded by small teddy bears, soft morning light filtering '
                                  'through thin white curtains creating gentle accents, a cozy Scandinavian-style '
                                  "children's room, shallow depth of field with the embroidery frame in sharp focus.\n"
                                  '\n'
                                  'IMPORTANT: Maintain the EXACT shape of the embroidery frame from the reference '
                                  'image. Keep the fabric, color palette, facial features, embroidery details, and '
                                  'proportions. Do not edit the embroidery frame – only create a new scene around it. '
                                  'photorealistic, natural lighting, linen texture visible, high detail, product '
                                  'photography style\n'
                                  '\n'
                                  'STYLE: Handmade product photography, soft natural light, editorial quality, modern '
                                  'minimalist Etsy style, 1:1 square aspect ratio. AVOID: mass production look, harsh '
                                  'studio lighting, cluttered background, AI errors, text overlays, watermarks.'),
                                 ('Flat lay',
                                  'Flat lay — chăn kem + decor bé',
                                  'The product image features a personalized, birthday-themed embroidery frame '
                                  'arranged in a flat layout on a soft, cream-colored baby blanket. The scene is '
                                  'decorated with a few baby mementos such as hats, tiny socks, muslin scarves, and '
                                  'baby toys in various pastel tones. Soft natural light shines from the window above '
                                  'and to the left, the background is clean, airy, and subtly blurred where necessary, '
                                  'the embroidery frame is centrally placed with ample space, and the image conveys a '
                                  'soft, peaceful, handcrafted feel. A standout product photo for Etsy.\n'
                                  '\n'
                                  'IMPORTANT: Maintain the EXACT shape of the embroidery frame from the reference '
                                  'image. Keep the wooden frame, fabric texture, color palette, photo placement, '
                                  'embroidery details, and proportions. Do not edit the embroidery frame – only create '
                                  'a new flat background and surrounding props. photorealistic, natural lighting, '
                                  'linen texture visible, high detail, product photography style\n'
                                  '\n'
                                  'STYLE: Handcrafted product photography, soft natural lighting, editorial quality, '
                                  "aesthetics. Etsy's modern minimalist style, 1:1 square aspect ratio.\n"
                                  '\n'
                                  'AVOID: product alterations, harsh shadows, heavy props, clutter, highly distracting '
                                  'colors, AI errors, text overlays, watermarks.'),
                                 ('Product display',
                                  'Treo tường nursery',
                                  "The product image shows a personalized commemorative embroidery frame for a baby's "
                                  'birthday, displayed as a wall decoration in a nursery with soft, neutral tones. The '
                                  'frame is tied with string and hung on a nail on a white wall above a light-colored '
                                  'wooden shelf, below which are delicate decorations such as teddy bears, small '
                                  'books, and dried flowers. Strong natural light shines from the window above and to '
                                  'the left, the minimalist and slightly soft background highlights the embroidery '
                                  'frame, and the shallow depth of field creates a gentle bokeh effect. A standout '
                                  'handcrafted product image for Etsy. \n'
                                  '\n'
                                  'IMPORTANT: Keep the EXACT shape of the embroidery frame from the reference image. '
                                  'Keep the wooden frame, fabric, color palette, image placement, embroidery details, '
                                  'and proportions the same. Do not modify the embroidery frame – simply create a new '
                                  'environment around it. \n'
                                  '\n'
                                  'STYLE: Handcrafted product photography, soft natural lighting, high-quality '
                                  'editing, modern minimalist Etsy aesthetic, 1:1 square aspect ratio. \n'
                                  '\n'
                                  'AVOID: Product alterations, dark walls, harsh lighting, excessive wall decorations, '
                                  'clutter, AI errors, text overlays, watermarks.'),
                                 ('Lifestyle',
                                  'Mẹ cầm khung — linen dress',
                                  'The product photo features a personalized, gently held, commemorative embroidery '
                                  "frame for a baby's birthday, held by a woman in a white or beige linen dress. The "
                                  "woman's face is not visible in the shot. Soft, natural light streams in from a "
                                  'window in the upper left, the background is a warm, minimalist cream-colored '
                                  'interior with a subtle blurring effect, and the shallow depth of field creates a '
                                  'soft, emotionally rich atmosphere in the Etsy style. A standout lifestyle product '
                                  'photo.\n'
                                  '\n'
                                  'IMPORTANT: Maintain the EXACT shape of the embroidery frame from the reference '
                                  'photo. Keep the wooden frame, fabric, color palette, photo placement, embroidery '
                                  'details, and proportions. Do not edit the embroidery frame – simply create a new '
                                  'lifestyle context around it. photorealistic, natural lighting, linen texture '
                                  'visible, high detail, product photography style\n'
                                  '\n'
                                  'STYLE: Handmade product photography, soft natural light, editorial quality, modern '
                                  'minimalist Etsy aesthetic, 1:1 square aspect ratio.\n'
                                  '\n'
                                  "AVOID: altering the product's appearance, displaying distracting facial details, "
                                  'awkward or cluttered poses, AI errors, text overlays, and watermarks.'),
                                 ('Cận thêu tay',
                                  'Macro — thêu tên + ngày',
                                  'Take a close-up photo of the embroidery frame from the reference image, focusing on '
                                  'the exquisite hand-embroidery details, with clear threads and beautiful stitching. '
                                  'The fabric embroidery frame should be the main focal point, highlighting the '
                                  'embroidery and stitching. Soft, natural light from the side will emphasize the '
                                  'depth of the embroidery, with a shallow depth of field to create a hazy effect '
                                  'around the fabric. The fabric should be neutral and clean-colored, and the '
                                  'handcrafted details must be clearly visible, highlighting the quality of the '
                                  'product. \n'
                                  '\n'
                                  'IMPORTANT: Maintain the EXACT shape of the fabric embroidery frame from the '
                                  'reference image. Preserve the fabric material, embroidery details, thread color, '
                                  'stitching, proportions, and handcrafted characteristics. Do not alter the '
                                  'embroidery frame in any way—only enlarge the existing embroidery details. \n'
                                  '\n'
                                  'STYLE: Close-up of the handcrafted product, soft natural light, high-quality '
                                  'editing, modern minimalist Etsy-style aesthetic, square aspect ratio.1:1. \n'
                                  '\n'
                                  'AVOID: blurry seams, images that look machine-generated, altered embroidery '
                                  'patterns, harsh lighting, overexposed images, highlights, AI errors, text overlaid '
                                  'on images, watermarks.'),
                                 ('Product display',
                                  'Trên giỏ mây + decor bé',
                                  "The product image is a personalized commemorative embroidery frame for a baby's "
                                  'birthday, placed on a ONE-PIECE WICKER BASKET. INSIDE THE BASKET, THERE ARE '
                                  'ADDITIONAL BABY TOYS DECORATED ON AN OUTDOOR TABLE. The soft, bright, balanced, and '
                                  'focused natural light, with a shallow depth of field, creates a tranquil, '
                                  'Etsy-style atmosphere.\n'
                                  '\n'
                                  'IMPORTANT: Maintain the EXACT shape of the embroidery frame from the reference '
                                  'image. Keep the wooden frame, fabric material, color palette, image placement, '
                                  'embroidery details, and proportions. Do not edit the embroidery frame – simply '
                                  'create a new background around it. photorealistic, natural lighting, linen texture '
                                  'visible, high detail, product photography style\n'
                                  '\n'
                                  'STYLE: Handmade product photography, soft natural light, editorial quality, modern '
                                  'minimalist Etsy-style aesthetic, 1:1 square aspect ratio.\n'
                                  '\n'
                                  'AVOID: Editing the product. Products, props with strong colors, overly elaborate '
                                  'backdrops, stiff studio appearance, AI errors, text overlays, watermarks.'),
                                 ('Gift box',
                                  'Gift box — quà tặng bé',
                                  'The product image is a personalized, beautifully presented commemorative embroidery '
                                  "frame for a baby's birthday, housed in an open gift box. The box is lined with soft "
                                  'silk paper and decorated with satin ribbon, delicate dried flowers in neutral '
                                  'pastel tones. Soft natural light streams in from the upper left window, the '
                                  'background is minimalist and slightly muted with white tones, and the embroidery '
                                  'frame remains the main focal point. A stunning Etsy product photo, ready to be '
                                  'given as a gift.\n'
                                  '\n'
                                  'IMPORTANT: Maintain the EXACT shape of the embroidery frame from the reference '
                                  'image. Keep the wooden frame, fabric, color palette, photo placement, embroidery '
                                  'details, and proportions. Do not edit the embroidery frame – simply create a new '
                                  'gift frame around it.\n'
                                  '\n'
                                  'STYLE: Handmade product photography, soft natural lighting, editorial quality, '
                                  "Etsy's modern minimalist aesthetic, 1:1 square aspect ratio.\n"
                                  '\n'
                                  'AVOID: product changes, flashy gift packaging, bold colors, clutter, harsh '
                                  'lighting, AI errors, text overlays, watermarks.'),
                                 ('Quy trình',
                                  'Process — tay thêu',
                                  'Product Photo in Lifestyle Style: A personalized birthday commemorative embroidery '
                                  'frame showcasing the hand-embroidery process. A pair of hands gently manipulate the '
                                  'embroidery frame with needle and thread (thread threaded through the needle eye), '
                                  'while the frame remains the main focus and is clearly displayed (the frame is not '
                                  'shown in the photo). Soft natural light shines from the upper left window, the '
                                  'background is gently blurred with warm neutral tones, and the shallow depth of '
                                  'field creates a delicate, authentic feel of the handcrafted product on Etsy.\n'
                                  '\n'
                                  'IMPORTANT: Maintain the EXACT shape of the embroidery frame from the reference '
                                  'photo. Keep the wooden frame, fabric, color palette, photo placement, embroidery '
                                  'details, and proportions. Do not edit the embroidery frame – simply create a new '
                                  'process scene around it. photorealistic, natural lighting, linen texture visible, '
                                  'high detail, product photography style\n'
                                  '\n'
                                  'STYLE: Handcrafted product photography, soft natural light, editorial quality, '
                                  "Etsy's modern minimalist aesthetic, 1:1 square aspect ratio.\n"
                                  '\n'
                                  'AVOID: product changes, unrealistic hand positions, cluttered workspace, harsh '
                                  'lighting, AI errors, text overlays, watermarks.'),
                                 ('Product display',
                                  '3 khung grouped — tên khác',
                                  'The product image shows three personalized commemorative embroidery frames with the '
                                  "baby's name and birth date, displayed together as a unified commemorative "
                                  'collection. Each frame features a different baby photo and a different English '
                                  'name, but retains the same handcrafted style, soft fabric, wooden frame, delicate '
                                  'embroidery details, and personalized birthday celebration layout. The three frames '
                                  'are placed LAYING on a clean, light-colored oak table, slightly overlapping '
                                  'naturally. Decorate the scene with a few soft items for the nursery such as stuffed '
                                  'animals, small baby shoes, muslin cloths, and delicate dried flowers.\n'
                                  '\n'
                                  'IMPORTANT: Maintain the EXACT handcrafted shape and appearance of the embroidery '
                                  'frames from the reference image. Keep the wooden frame, linen fabric, color '
                                  'palette, photo placement, embroidery details and proportions, and thread colors for '
                                  'each detail. Each frame should have its own unique touch by using a different baby '
                                  'photo and a different English name. Do not edit or distort the embroidery frame '
                                  'style – simply create a new background and arrange three personalized versions '
                                  'side-by-side.\n'
                                  '\n'
                                  'STYLE: Handmade product photography, soft natural lighting, editorial quality, '
                                  "modern minimalist Etsy style. Warm, aesthetically pleasing children's room decor, "
                                  '1:1 square aspect ratio.\n'
                                  '\n'
                                  'AVOID: altering product styles, making all names or photos look identical, '
                                  'mass-produced look, harsh studio lighting, overly cluttered backgrounds, AI errors, '
                                  'illegible personalization, text overlays, watermarks.'),
                                 ('Lifestyle',
                                  'Bé chạm tay vào khung',
                                  "The product image is a personalized commemorative embroidery frame for a baby's "
                                  'birthday, featuring a baby gently holding or touching the embroidery frame in a '
                                  'natural, tranquil scene. The baby, dressed in a pastel-toned bib, is seated on a '
                                  'sofa in the living room, with the embroidery frame clearly displayed as the main '
                                  "focal point. The baby's hands gently and naturally hold the frame, creating a "
                                  'heartwarming commemorative gift. Soft natural light shines from the window above '
                                  'and to the left, centering the composition.\n'
                                  '\n'
                                  'IMPORTANT: Maintain the EXACT shape of the embroidery frame from the reference '
                                  'image. Keep the wooden frame, fabric, color palette, photo placement, embroidery '
                                  'details, and proportions unchanged. Do not alter the embroidery frame – simply '
                                  'create a new background and a new scene around it. The baby should interact '
                                  'naturally with the embroidery frame, but the product must be fully and unchanged. '
                                  'photorealistic, natural lighting, linen texture visible, high detail, product '
                                  'photography style\n'
                                  '\n'
                                  'STYLE: Handcrafted product photography, soft natural lighting, edited image '
                                  "quality, modern minimalist Etsy aesthetic, warm children's room decor style, 1:1 "
                                  'square aspect ratio.\n'
                                  '\n'
                                  'AVOID: altering product appearance, unrealistic baby poses, obscuring too much of '
                                  'the frame, harsh studio lighting, cluttered background, mass production feel, AI '
                                  'errors, text overlays, watermarks.'),
                                 ('Lifestyle',
                                  'Mẹ bế bé — bé ôm khung',
                                  "The product image is a personalized commemorative embroidery frame for a baby's "
                                  'birthday, featuring a mother holding her child, with the baby gently hugging or '
                                  'touching the frame. The mother is wearing a white lace dress, her face not visible. '
                                  'The baby is wearing a simple bib in neutral and natural tones, gently hugging the '
                                  'frame, creating a tender and memorable moment. The frame is clearly positioned in '
                                  'the center, with the mother and baby naturally surrounding it.\n'
                                  '\n'
                                  'IMPORTANT: Maintain the EXACT shape of the embroidery frame from the reference '
                                  'image. Keep the wooden frame, fabric, color palette, photo placement, embroidery '
                                  'details, and proportions the same. Do not alter the frame – simply create a new '
                                  'background and a vibrant setting around it. Mother and baby should interact '
                                  'naturally with the frame, but the product must be fully displayed, unchanged, and '
                                  'easily recognizable. photorealistic, natural lighting, linen texture visible, high '
                                  'detail, product photography style\n'
                                  '\n'
                                  'STYLE: Handcrafted product photography, soft natural lighting, high-quality '
                                  "editing, modern minimalist Etsy-style aesthetics, warm children's room decor, 1:1 "
                                  'square aspect ratio.\n'
                                  '\n'
                                  'AVOID: altering product appearance, unrealistic mother or child poses, obscuring '
                                  'too much embroidery, harsh studio lighting, cluttered backgrounds, mass production '
                                  'feel, AI errors, text overlays, watermarks.'),
                                 ('Product display',
                                  'Kệ bàn tiệc sinh nhật bé',
                                  'Product photos of the embroidery frame, taken from a reference image, are displayed '
                                  'on a small shelf placed on a birthday party table. The embroidery frame stands '
                                  'upright on a small, elegant wooden or light-colored stand, neatly placed on the '
                                  'birthday table as a centerpiece. Surrounding the scene are delicate birthday '
                                  'decorations such as a tablecloth with pastel-colored balloons in the background, a '
                                  'few wrapped gift boxes, delicate flowers, small candles, and subtle party details '
                                  'in soft neutral and pastel tones.\n'
                                  '\n'
                                  'IMPORTANT: Maintain the EXACT shape of the embroidery frame from the reference '
                                  'image. Keep the wooden frame, fabric material, photo location, embroidery details, '
                                  'color palette, typography, and proportions the same. Do not edit the embroidery '
                                  'frame – only create a new background and set up the display around it. '
                                  'photorealistic, natural lighting, linen texture visible, high detail, product '
                                  'photography style\n'
                                  '\n'
                                  'STYLE: Handcrafted product photography, soft natural lighting, high-quality '
                                  "editing, Etsy's modern minimalist aesthetic, elegant birthday party decorations, "
                                  '1:1 square aspect ratio.\n'
                                  '\n'
                                  'AVOID: altering product appearance, mass production feel, harsh studio lighting, '
                                  'overly cluttered or messy backgrounds, AI errors, text overlays, watermarks.'))},
 'christmas_dress_baby': {
     'display_name': 'Christmas Dress Baby',
     'aliases': (
         'Christmas Dress Baby',
         'christmas dress baby',
         'Christmas Baby Dress',
         'christmas baby dress',
         'Christmas Toddler Dress',
         'christmas toddler dress',
         'Christmas Kids Dress',
         'christmas kids dress',
         'Christmas Child Dress',
         'christmas child dress',
         'Christmas Girls Dress',
         'christmas girls dress',
         'Christmas Linen Dress',
         'christmas linen dress',
         'Christmas Embroidered Dress',
         'christmas embroidered dress',
         'Noel Dress Baby',
         'noel dress baby',
         'Noel Baby Dress',
         'noel baby dress',
         'dress baby christmas',
         'baby dress christmas',
         'vay be christmas',
         'vay em be christmas',
         'vay be noel',
         'vay em be noel',
     ),
     'target_count': 12,
     'allow_planned_multi_panel_shots': True,
     'lock': (
         'the main product must remain the exact same handmade baby or toddler dress from the source image, with the '
         'same silhouette, neckline, white collar when present, bodice, sleeves or shoulder ruffles, gathers, skirt, '
         'hem, pleats, ties, seams, linen or cotton-linen fabric, embroidery motif and readable source name, embroidery '
         'placement and scale, thread colors, proportions, and premium handmade identity; never invent a collar, and '
         'every back view must retain exactly two vertically aligned natural wooden buttons and no other closure'
     ),
     'shots': (
         ('Four mannequin colorways',
          'Four pastel Christmas dresses on child mannequins in two rows',
          _christmas_dress_baby_brief(
              'display exactly four child-size mannequins in a spacious two-by-two arrangement inside a minimalist white '
              'room, each wearing the exact same source dress construction in a different gentle pastel base fabric '
              'color. If the source dress has a collar, every collar must remain white rather than matching the dress '
              'body; if no collar exists, add none. Preserve the identical silhouette, ruffles, seams, embroidery design, '
              'placement, thread colors, and proportions; only the dress-body fabric color may differ. Add a few refined '
              'Christmas decorations. Use soft above-left window light, ample spacing, and subtle festive bokeh.'
          )),
         ('Three-dress Christmas flat lay',
          'Three pastel dresses in triangular Christmas flat lay',
          _christmas_dress_baby_brief(
              'arrange exactly three dresses of the same source design in three gentle pastel dress-body colorways on a '
              'white tabletop, lightly overlapping in a balanced triangular composition without covering embroidery or '
              'construction details. Shoot directly top-down with soft above-left natural daylight and widely spaced '
              'Christmas ornaments around the outer edges. Preserve the exact dress form, fabric texture, source '
              'embroidery, seams, scale, and white collar on every colorway when the source has one.'
          )),
         ('Front and back Christmas garden',
          'Two child mannequins showing dress front and two-button back',
          _christmas_dress_baby_brief(
              'display two matching dresses on child-size mannequins in a bright garden decorated for Christmas: the '
              'front mannequin clearly shows the exact embroidered front, while the second clearly shows the back. The '
              'back placket must have exactly two small natural wooden buttons, vertically aligned and evenly spaced, '
              'with no additional closure. Use clean soft natural daylight and a premium Etsy product composition. '
              'Preserve all source colors, white collar when present, materials, ruffles, seams, embroidery, and proportions.'
          )),
         ('Christmas gift box',
          'Dress folded neatly inside bright Christmas gift box',
          _christmas_dress_baby_brief(
              'place the exact dress neatly folded inside an open premium paper gift box, with its embroidery, ruffled '
              'shoulder detail, white collar when present, fabric texture, and handmade seams clearly visible. Shoot '
              'top-down with soft natural light from above-left and a lightly blurred bright background. Add restrained '
              'natural Christmas decorations around the box without clutter or obstruction. Keep the product centered, '
              'spacious, realistic, and gift-ready.'
          )),
         ('Christmas clothesline colorways',
          'Two dresses on wooden hangers with Christmas decor',
          _christmas_dress_baby_brief(
              'hang exactly two dresses of the same source design in two different gentle dress-body colors from wooden '
              'hangers on a clothesline. Preserve the identical silhouette, material, ruffles, seams, embroidery design, '
              'placement, thread colors, white collar when present, and proportions; only the body fabric color may '
              'differ. Add minimal Christmas decor in a bright airy setting, use soft above-left natural daylight and '
              'subtle background bokeh, and leave ample negative space around both complete garments.'
          )),
         ('Christmas tree decorating',
          'Child wearing dress while decorating tree with friends',
          _christmas_dress_baby_brief(
              'show a child safely wearing the exact source dress while decorating a Christmas tree with friends. Center '
              'the child wearing the product and keep the complete dress shape, white collar when present, ruffles, '
              'embroidery, seams, material, color, and proportions visible while friends remain secondary. Use soft '
              'above-left natural daylight, an airy minimalist room, restrained tree decorations, and gentle background '
              'bokeh. Children and hands must be anatomically natural.'
          )),
         ('Christmas sofa lifestyle',
          'Child wearing dress naturally on neutral sofa',
          _christmas_dress_baby_brief(
              'show a child wearing the exact source dress while sitting naturally on a neutral sofa, playing a simple '
              'game or eating small pieces of fruit in a beautifully but minimally Christmas-decorated room. Capture a '
              'genuine expression and pose. Use bright soft side-window daylight, a slightly blurred background, and '
              'generous spacing. Keep the dress central and preserve its exact form, white collar when present, fabric, '
              'color, source embroidery, ruffles, seams, and handmade details.'
          )),
         ('Embroidery process macro',
          'Macro hand-embroidery detail matching the dress motif',
          _christmas_dress_baby_brief(
              'create a realistic macro process photograph showing only the embroidery area matching the exact source '
              'dress motif, not the whole dress. Show matching linen held in a small wooden hoop, one anatomically natural '
              'hand supporting the hoop and another using a realistically threaded needle at the correct stitch position. '
              'Use soft above-left window light, shallow depth of field, and sharp focus on the linen weave, raised hand '
              'stitches, thread fibers, needle, and precise handmade technique. Do not redesign the motif or show machine '
              'embroidery.'
          )),
         ('Eight-step making process',
          'Eight-panel handmade Christmas dress process collage',
          _christmas_dress_baby_brief(
              'create one clean premium square collage with exactly eight distinct process panels and no captions: '
              '1) selecting linen or cotton-linen matching the exact source fabric color; 2) sketching the exact source '
              'embroidery layout with tailor chalk; 3) hand-embroidering the motif in a wooden hoop; 4) macro detail of '
              'the threaded needle, linen, and precise hand stitches; 5) cutting separate dress pattern pieces on a '
              'rustic wooden table; 6) a Vietnamese seamstress assembling the dress with a sewing machine in a clean '
              'craft studio; 7) gently pressing the completed dress while preserving natural linen texture; 8) the '
              'completed exact dress folded inside a kraft paper gift box beside a matching hair tie and restrained '
              'neutral craft props. Keep fabric color, white collar when present, and dress construction consistent '
              'across all panels. Use bright white-balanced window light, realistic hands and tools, and no text.'
          )),
         ('Family Christmas portrait',
          'Three-year-old wearing dress with parents by Christmas tree',
          _christmas_dress_baby_brief(
              'create a realistic bright family Christmas portrait with a three-year-old girl wearing the exact source '
              'dress while posing naturally with her parents. Place a decorated Christmas tree and wrapped gifts in the '
              'softly blurred background, with the child and dress as the sharp primary subject. Use clear airy '
              'white-balanced natural daylight rather than yellow light. Preserve the exact garment silhouette, white '
              'collar when present, fabric, color, seams, sleeve folds, ruffles, skirt construction, source embroidery, '
              'proportions, and handmade softness.'
          )),
         ('Four-panel garment details',
          'Four close-ups of collar embroidery ruffles seams and hem',
          _christmas_dress_baby_brief(
              'create one clean square 2x2 Etsy detail collage with exactly four high-resolution close-up photographs of '
              'the same source dress: 1) embroidered neckline and white collar when present; 2) shoulder ruffle '
              'construction; 3) bodice or skirt seam and stitch quality; 4) pleated or gathered hem finish. Preserve the '
              'exact source fabric color, dress design, embroidery placement, thread colors, collar construction, '
              'ruffles, seams, proportions, and handmade appearance. Use soft window light and no text or labels.'
          )),
         ('Children opening gifts',
          'Two four-year-old children wearing dresses under Christmas tree',
          _christmas_dress_baby_brief(
              'show exactly two four-year-old children sitting under a decorated Christmas tree and happily opening '
              'wrapped gifts, each wearing a dress of the exact same source construction in a coordinated gentle '
              'colorway. Keep both dresses clearly visible and product-focused. Preserve the exact silhouette, white '
              'collar when present, material, source embroidery design and placement, thread colors, seams, sleeve folds, '
              'ruffles, skirt structure, scale, and handmade details. Use bright airy white-balanced natural daylight, '
              'natural child movement, realistic anatomy, shallow depth of field, and refined festive decor.'
          )),
     ),
 },
 'halloween_dress_baby': {
     'display_name': 'Halloween Dress Baby',
     'aliases': (
         'Halloween Dress Baby',
         'halloween dress baby',
         'Halloween Baby Dress',
         'halloween baby dress',
         'Halloween Toddler Dress',
         'halloween toddler dress',
         'Halloween Kids Dress',
         'halloween kids dress',
         'Halloween Child Dress',
         'halloween child dress',
         'Halloween Girls Dress',
         'halloween girls dress',
         'Halloween Linen Dress',
         'halloween linen dress',
         'Halloween Embroidered Dress',
         'halloween embroidered dress',
         'dress baby halloween',
         'baby dress halloween',
         'vay be halloween',
         'vay em be halloween',
     ),
     'target_count': 12,
     'allow_planned_multi_panel_shots': True,
     'lock': (
         'the main product must remain the exact same handmade baby or toddler dress from the source image, with the '
         'same silhouette, neckline, bodice, sleeves or shoulder ruffles, gathers, skirt, hem, pleats, ties, seams, '
         'linen or cotton-linen fabric, embroidery motif and readable source name, embroidery placement and scale, '
         'thread colors, proportions, and premium handmade identity; every back view must retain exactly two vertically '
         'aligned natural wooden buttons and no other closure'
     ),
     'shots': (
         ('Four mannequin colorways',
          'Four pastel dresses on child mannequins in two rows',
          _halloween_dress_baby_brief(
              'display exactly four child-size mannequins in a spacious two-by-two arrangement inside a minimalist white '
              'room, each wearing the exact same source dress construction in a different gentle pastel base fabric '
              'color. Preserve the identical source silhouette, ruffles, seams, embroidery design, placement, thread '
              'colors, and proportions on all four dresses; only the base fabric color may differ. Add a few restrained '
              'Halloween decorations around the room. Use soft natural window light from above-left, ample spacing, a '
              'centered editorial composition, and subtle background bokeh.'
          )),
         ('Three-dress flat lay',
          'Three pastel dresses in triangular top-down arrangement',
          _halloween_dress_baby_brief(
              'arrange exactly three dresses of the same source design in three gentle pastel base fabric colorways on a '
              'white tabletop, lightly overlapping in a balanced triangular composition without covering any embroidery '
              'or important construction detail. Shoot directly top-down. Use soft natural daylight from above-left and '
              'widely spaced premium Halloween accents around the outer edges. Preserve the exact dress form, fabric '
              'texture, source embroidery, seams, scale, and handmade proportions on every dress.'
          )),
         ('Front and back mannequins',
          'Two child mannequins showing dress front and two-button back',
          _halloween_dress_baby_brief(
              'display two matching dresses on child-size mannequins in a bright Halloween-decorated garden: the front '
              'mannequin clearly shows the exact embroidered front, while the second mannequin clearly shows the back. '
              'The back placket must have exactly two small natural wooden buttons, vertically aligned and evenly spaced, '
              'with no additional closure. Use clean soft natural daylight and a realistic premium Etsy product '
              'composition. Preserve all source colors, materials, ruffles, seams, embroidery, and proportions.'
          )),
         ('Gift box presentation',
          'Dress folded neatly inside bright paper gift box',
          _halloween_dress_baby_brief(
              'place the exact dress neatly folded inside an open premium paper gift box, with the embroidered section, '
              'ruffled shoulder detail, fabric texture, and handmade seams clearly visible. Shoot top-down with soft '
              'natural light from above-left and a lightly blurred bright background. Add small pumpkins, a tiny wooden '
              'ghost, miniature bats, and a few refined Halloween objects around the box without clutter or obstruction. '
              'Keep the product centered, spacious, natural, and gift-ready.'
          )),
         ('Clothesline colorways',
          'Two dresses on wooden hangers along bright clothesline',
          _halloween_dress_baby_brief(
              'hang exactly two dresses of the same source design in two different gentle base fabric colors from wooden '
              'hangers on a clothesline. Preserve the identical silhouette, material, ruffles, seams, embroidery design, '
              'placement, thread colors, and proportions; only the base fabric color may differ. Add minimal Halloween '
              'decor in a bright airy setting, use soft above-left natural daylight and subtle background bokeh, and leave '
              'ample negative space around both complete garments.'
          )),
         ('Friends playtime',
          'Baby wearing exact dress while playing with friends',
          _halloween_dress_baby_brief(
              'show a baby safely wearing the exact source dress while seated and playing naturally with friends on an '
              'indoor rug in a bright Halloween-decorated room. Center the child wearing the product, keep the full dress '
              'shape, ruffles, embroidery, seams, material, color, and proportions visible, and let the friends remain '
              'secondary. Use soft above-left natural daylight, airy minimalist styling, and gentle background bokeh. '
              'Children and hands must be anatomically natural.'
          )),
         ('Sofa lifestyle',
          'Baby wearing dress naturally on neutral sofa',
          _halloween_dress_baby_brief(
              'show a baby wearing the exact source dress while sitting naturally on a neutral sofa, playing a simple '
              'game or eating small pieces of fruit in a beautifully but minimally Halloween-decorated room. Capture a '
              'genuine child expression and pose. Use bright soft side-window daylight, a slightly blurred background, '
              'and generous spacing. Keep the dress central and preserve its exact form, fabric, color, source '
              'embroidery, ruffles, seams, and handmade details.'
          )),
         ('Embroidery process macro',
          'Macro hand-embroidery detail matching the dress motif',
          _halloween_dress_baby_brief(
              'create a realistic macro process photograph showing only the embroidery area matching the exact source '
              'dress motif, not the whole dress. Show matching linen held in a small wooden hoop, one anatomically natural '
              'hand supporting the hoop and another using a realistically threaded needle at the correct stitch position. '
              'Use soft above-left window light, shallow depth of field, and sharp focus on the linen weave, raised hand '
              'stitches, thread fibers, needle, and precise handmade technique. Do not redesign the motif or show machine '
              'embroidery.'
          )),
         ('Eight-step making process',
          'Eight-panel handmade dress process collage',
          _halloween_dress_baby_brief(
              'create one clean premium square collage with exactly eight distinct process panels and no captions: '
              '1) selecting linen or cotton-linen matching the exact source fabric color from neatly folded fabric; '
              '2) sketching the exact source embroidery layout with tailor chalk; 3) hand-embroidering the motif in a '
              'wooden hoop; 4) macro detail of the threaded needle, linen, and precise hand stitches; 5) cutting separate '
              'dress pattern pieces on a rustic wooden table; 6) a Vietnamese seamstress assembling the dress with a '
              'sewing machine in a clean craft studio; 7) gently pressing the completed dress while preserving natural '
              'linen texture; 8) the completed exact dress folded inside a kraft paper gift box beside a matching hair '
              'tie and restrained neutral craft props. Keep fabric color and dress construction consistent across all '
              'panels. Use bright white-balanced window light, orderly spacing, realistic hands and tools, and no text, '
              'labels, logos, or watermarks.'
          )),
         ('Trick-or-treat lifestyle',
          'Child wearing dress during American trick-or-treat visit',
          _halloween_dress_baby_brief(
              'create a realistic American Halloween trick-or-treat scene outside a decorated home. The child wearing the '
              'exact source dress stands with friends at the front door while collecting candy, with the dress as the '
              'sharp primary subject. Use bright clear airy daytime shade light rather than yellow evening light. '
              'Preserve the exact garment silhouette, fabric, color, seams, sleeve folds, ruffles, skirt construction, '
              'source embroidery, proportions, and handmade softness. Keep friends and porch decor secondary and softly '
              'blurred.'
          )),
         ('Four-panel garment details',
          'Four close-ups of embroidery ruffles seams and hem',
          _halloween_dress_baby_brief(
              'create one clean square 2x2 Etsy detail collage with exactly four high-resolution close-up photographs of '
              'the same source dress: 1) embroidered neckline and linen weave; 2) shoulder ruffle construction; 3) bodice '
              'or skirt seam and stitch quality; 4) pleated or gathered hem finish. Preserve the exact source fabric color, '
              'dress design, embroidery placement, thread colors, ruffles, seams, proportions, and handmade appearance. '
              'Use soft natural window light, a neutral linen background, consistent scale, and no text or labels.'
          )),
         ('Halloween party lifestyle',
          'Three-year-old wearing dress at bright Halloween party',
          _halloween_dress_baby_brief(
              'show a three-year-old child happily wearing the exact source dress during a bright tasteful Halloween '
              'party. Capture a natural candid pose and gentle movement while keeping the complete garment readable and '
              'sharply prioritized. Use clear airy white-balanced natural daylight, shallow depth of field, and refined '
              'Halloween decorations in the softly blurred background. Preserve the exact dress silhouette, material, '
              'color, seams, sleeve folds, ruffles, skirt structure, source embroidery, scale, and handmade details.'
          )),
     ),
 },
 'dress_baby': {'display_name': 'Dress Baby',
                'aliases': ('Dress Baby',
                            'baby dress',
                            'toddler dress',
                            'kids dress',
                            'children dress',
                            'child dress',
                            "child's dress",
                            "children's dress",
                            'girls dress',
                            'girl dress',
                            'linen dress',
                            'white linen dress',
                            'sleeveless dress',
                            'ruffled dress',
                            'ruffle sleeve dress',
                            'flutter sleeve dress',
                            'pinafore dress',
                            'embroidered dress',
                            'váy bé',
                            'vay be',
                            'váy em bé',
                            'vay em be'),
                'lock': 'the main product must remain the same baby/child dress with the exact dress silhouette, '
                        'sleeves/ruffles/ties/hem, fabric color, embroidery placement, garment scale, and construction '
                        'from the source image; in every back-facing view, the back placket must show exactly two '
                        'small natural wooden buttons, vertically aligned and evenly spaced like the reference photo, '
                        'with no third button, no extra button row, no snaps, no zipper, no bow closure, and no added '
                        'decorative back closures',
                'shots': (('Product display',
                           '4 con manocanh',
                           'The product photos feature four dresses in different colors, based on the provided '
                           'reference image. The four dresses are displayed on mannequins standing side-by-side, '
                           'arranged in two rows. Each dress has a soft color. Gentle natural light shines from the '
                           'window above and to the left, creating a shimmering effect on the dresses. The background '
                           'is minimalist, white, and the objects are centrally positioned with ample space between '
                           'them. The shallow depth of field creates a soft bokeh effect. \n'
                           '\n'
                           'IMPORTANT: Maintain the EXACT shape, proportions, and color palette of the dresses as in '
                           'the reference image. Preserve the fabric texture, embroidery details, and proportions. Do '
                           'not edit or alter the dresses themselves – only create a new background around them. \n'
                           '\n'
                           'STYLE: Handcrafted product photography, soft natural lighting, editorial quality, modern '
                           'minimalist Etsy-style aesthetic, 1:1 square aspect ratio. \n'
                           '\n'
                           "AVOID: altering the dress's appearance or the product's form. Mass production. Consecutive "
                           'shots, harsh studio lighting, cluttered backgrounds, distracting props, distorted '
                           'embroidery, spelling errors, missing names, AI-generated errors, overlapping text, blurry '
                           'images.'),
                          ('Product display',
                           '3 chiếc trên bàn',
                           'Product photos of three dresses in three different colors are based on the provided '
                           'reference image. The three dresses are placed side-by-side on a white table, stacked '
                           'lightly to form a triangle, decorated with small flowers and a few playful props, '
                           "including children's shoes. Each dress is a soft pastel color. Gentle natural light shines "
                           'from above and from the left, highlighting the dresses and creating an inviting scene. The '
                           'minimalist background features a rough wooden tabletop, and the items are arranged with '
                           'ample spacing to create balance. The shallow depth of field creates a soft bokeh effect, '
                           'highlighting the dresses. The photo was taken directly from above, focusing on the '
                           'dresses.\n'
                           '\n'
                           'IMPORTANT: Maintain the EXACT shape, proportions, and color palette of the dresses as in '
                           'the reference image. Preserve the fabric texture, embroidery details, and proportions. Do '
                           'not edit or alter the dresses themselves – only create a new background around them. '
                           'them.\n'
                           '\n'
                           'STYLE: Handmade product photography, soft natural lighting, editorial quality, minimalist '
                           "modern Etsy aesthetic, warm and rustic style inspired by children's rooms, 1:1 square "
                           'aspect ratio.\n'
                           '\n'
                           "AVOID: Altering the dress's appearance, mass-produced look, harsh studio lighting, "
                           'cluttered background, distracting props, distorted embroidery, missing name, AI-generated '
                           'errors, overlapping text, blurry images.'),
                          ('Product display',
                           '2 váy',
                           "The product image shows two children's dresses based on the provided reference image. Two "
                           'dresses, in different colors but the same pattern, are laid flat on a wooden table, '
                           'photographed from a straight, top-down perspective. Surrounding the dresses are several '
                           "fresh fruits, green leaves, small decorative flowers, and some children's room-style "
                           "decorative items placed naturally around the layout. A pair of children's shoes is added "
                           'near the bottom right corner. The layout is balanced, airy, and visually pleasing, with '
                           'the dresses as the main focal point.\n'
                           '\n'
                           'IMPORTANT: Maintain EXACTLY the shape, proportions, neckline, sleeve style, bow placement, '
                           'fabric, embroidery placement, and overall style of the dresses from the reference image. '
                           'Maintain the overall embroidery style and original design; do not redraw or over-detail '
                           'the embroidery details, so that the pattern can be reused for other embroidered dresses. '
                           'Design. Do not alter the dress itself. Recreate only the background, surrounding '
                           'accessories, and overall composition.\n'
                           '\n'
                           'STYLE: Handmade product photography, soft natural lighting, editorial quality, warm and '
                           'charming Etsy style, clean silhouettes, gentle shadows, realistic fabric details, flat '
                           'top-down composition, 1:1 square aspect ratio.\n'
                           '\n'
                           'AVOID: altering dress designs, changing embroidery styles, mass-produced look, harsh '
                           'studio lighting, cluttered styling, distracting accessories, distorted garment shapes, AI '
                           'errors, text overlays, watermarks, or unrealistic colors.'),
                          ('Product display',
                           'manocanh 2 mặt',
                           'Use the dress in the reference image as the main product. Create a neat, Etsy-style '
                           "product photo, displaying two dresses on a child's mannequin, one in the front and one in "
                           'the back. The back-facing dress must show exactly two small natural wooden buttons, '
                           'vertically aligned and evenly spaced on the back placket; do not add a third button, extra '
                           'button row, snaps, zipper, bow closure, or decorative back closures. Place the dress in an '
                           'outdoor garden setting with soft, natural flowers and greenery in the background. Ensure '
                           'the dress retains its shape, color, texture, and details as in the reference image. Do not '
                           'edit, redesign, or alter the dress itself.\n'
                           '\n'
                           'IMPORTANT: Maintain the exact shape, proportions, and color palette of the dress as in the '
                           'reference image. Preserve the fabric texture, embroidery details, and proportions. Do not '
                           'edit or alter the dress itself – only create a new background around it.\n'
                           '\n'
                           'STYLE: Handcrafted product photography, soft natural lighting, professional quality, '
                           'modern minimalist Etsy aesthetic, realistic product photos, 1:1 square aspect ratio.\n'
                           '\n'
                           'AVOID: altering clothing styles, mass-produced looks, harsh studio lighting, cluttered '
                           'props, text overlays, logos, watermarks, and AI-generated errors.'),
                          ('Gift box',
                           'hộp quà',
                           'Use the dress in the reference photo as the main product. Display the dress neatly in a '
                           'paper gift box. Place the gift box containing the dress in a bright, airy, minimalist '
                           'space with natural decorations such as dried flowers, eucalyptus leaves, and small, '
                           'neutral ornaments. \n'
                           '\n'
                           'Soft natural light should shine from above and slightly to the left. The background should '
                           'be slightly blurred to create a subtle bokeh effect. Place the product in the center with '
                           'ample space. Shoot from above, focusing on the dress in the gift box. The final image '
                           'should convey a natural, high-end, and professional feel, suitable for making a strong '
                           'impression on Etsy. \n'
                           '\n'
                           "STYLE: Handmade product photography, soft natural lighting, high-quality editing, Etsy's "
                           'modern minimalist aesthetic, realistic product photography, 1:1 square aspect ratio. \n'
                           '\n'
                           'AVOID: product appearance editing, mass-produced look, harsh studio lighting, cluttered '
                           'decorations, overlays. The original, logo, watermark, and AI details.'),
                          ('Product display',
                           '',
                           'Use the two dresses in the reference photos, in two different colors, as the main '
                           'products. Display the dresses neatly, hanging two dresses of different colors on wooden '
                           'hangers on a clothesline. Place the dresses in a bright, airy, minimalist space with '
                           'natural items such as dried flowers, eucalyptus leaves, and small neutral-colored '
                           'decorative items. Maintain the original shape, material, color, and details of the '
                           'dresses. Do not alter, redesign, or add embroidery or patterns. \n'
                           '\n'
                           'Soft natural light should shine from above and slightly to the left. The background should '
                           'be slightly blurred to create a subtle bokeh effect. Place the products in the center with '
                           'ample space. \n'
                           '\n'
                           'IMPORTANT: Maintain the EXACT shape, material, color, and details of each dress. Do not '
                           'modify, repaint, distort, or redesign the dresses. Only create a background and style '
                           'around them. \n'
                           '\n'
                           'STYLE: Handcrafted product photography, soft natural light, high-quality editing, '
                           'minimalist aesthetic. Etsy-style photos, realistic product images, 1:1 square aspect '
                           'ratio. \n'
                           '\n'
                           'AVOID: altered product appearance, mass-produced look, harsh studio lighting, cluttered '
                           'objects, text, overlays, logos, watermarks, AI-generated image noise.'),
                          ('Lifestyle',
                           'em bé công viên',
                           'Use the dress in the reference photo as the main product. Photograph the baby wearing that '
                           'dress sitting and playing with friends on a picnic mat in an outdoor park setting, '
                           'capturing natural, authentic moments like walking or running. Use soft, natural light from '
                           'above, slightly tilted to the left. The background should be slightly blurred to create a '
                           'subtle bokeh effect, focusing on the baby and the dress, while keeping the scene bright, '
                           'airy, and minimalist. Place the subject in the center with ample space. \n'
                           '\n'
                           'IMPORTANT: Maintain the EXACT shape, material, color, and details of the dress. Do not '
                           'edit, redraw, distort, or redesign the dress. Only create the background and style around '
                           'the baby wearing it. \n'
                           '\n'
                           'STYLE: Handmade product photography, soft natural light, professional image quality, '
                           'modern minimalist aesthetic in the Etsy style, authentic product photography, square '
                           'aspect ratio. 1:1. \n'
                           '\n'
                           'AVOID: image editing. Product appearance, mass production look, harsh studio lighting, '
                           'cluttered props, text overlays, logos, watermarks, and AI-generated image noise.'),
                          ('Lifestyle',
                           'sofa',
                           'Use the dress in the reference photo as the main product. Dress the child in the dress, '
                           'have them sit on a neutral-colored sofa playing games or eating fruit, and capture their '
                           'natural, authentic expressions and poses. Keep the dress exactly as it is in shape, '
                           'material, color, and details. Do not edit, redesign, add embroidery, or patterns. Use '
                           'soft, natural light from a window on one side. The background should be slightly blurred '
                           'to create a subtle bokeh effect, keeping the scene bright, airy, and minimalist. Place the '
                           'subject in the center with ample space. \n'
                           '\n'
                           'IMPORTANT: Keep the EXACT shape, material, color, and details of the dress. Do not edit, '
                           'redraw, distort, or redesign the dress. Only create a background and style around the '
                           'child wearing the dress. \n'
                           '\n'
                           'STYLE: Handmade product photography, soft natural light, professional image quality, '
                           'modern minimalist aesthetic in the Etsy style, product photography. Authentic product, 1:1 '
                           'square aspect ratio. \n'
                           '\n'
                           'AVOID: altering product appearance, mass production look, harsh studio lighting, cluttered '
                           'props, text overlays, logos, watermarks, and AI-generated image noise.'),
                          ('Lifestyle',
                           'em bé',
                           'Use the dresses in the reference photos as the main product. Photograph the children '
                           'wearing the dresses against a white background: one child facing forward, one child facing '
                           'backward. The back-facing dress must show exactly two small natural wooden buttons, '
                           'vertically aligned and evenly spaced on the back placket, matching the reference detail; '
                           'do not add a third button, extra button row, snaps, zipper, bow closure, or decorative back '
                           'closures. Do not add any text overlay or caption to the image. Maintain the original shape, '
                           'material, color, and details of each dress. Do not alter, redesign, embroider, or add any '
                           'decorative details. \n'
                           '\n'
                           'IMPORTANT: Maintain EXACTLY the shape, material, color, and details of each dress. Do not '
                           'alter, redraw, distort, or redesign the dress. Create only a background and styling around '
                           'the babies in dresses. \n'
                           '\n'
                           'STYLE: Handmade product photography, soft natural lighting, professional image quality, '
                           'modern minimalist aesthetics in the Etsy style, realistic product photography, 1:1 square '
                           'aspect ratio. \n'
                           '\n'
                           'AVOID: altering product appearance, mass production look, harsh studio lighting, cluttered '
                           'props, text overlays, logos, watermarks, and AI-generated image noise.'),
                          ('Cận thêu tay',
                           'thêu tay',
                           'Take a realistic, close-up photo of the embroidery on the dress, similar to the embroidery '
                           'pattern on the dress in the reference photo. The close-up should clearly show the '
                           'hand-embroidered details. The photo should only show the embroidery, not the entire '
                           'dress. \n'
                           '\n'
                           'Soft natural light from the window above and to the left creates gentle shadows and '
                           'highlights the texture of the linen fabric, the stitches, the thread details, and the '
                           'handcrafted process. Use a shallow depth of field with a slightly blurred background. The '
                           'focus should be on the hands, needle, embroidery frame, linen fabric, and the '
                           'hand-embroidery process. \n'
                           '\n'
                           'STYLE: Photographing the hand-embroidery process, soft natural light from the window, '
                           'realistic product photography, editorial quality, modern minimalist aesthetics in the Etsy '
                           'style, rustic workspace, natural linen fabric, 1:1 square aspect ratio. \n'
                           '\n'
                           'AVOID: Harsh studio lighting, cluttered background, plastic-looking fabric, mass-produced '
                           'appearance, smudged hands, distorted fingers. Misaligned stitches, incorrect needle '
                           'placement, unrealistic embroidery lines, AI errors, text overlays, logos, watermarks.'),
                          ('Quy trình',
                           'quy trình',
                           "Create a realistic mosaic of the crafting process for a children's embroidered dress, "
                           'inspired by the reference image. The final image should showcase the entire crafting '
                           'process in seven clear frames, arranged like a high-end product workflow chart on Etsy, '
                           'with soft rounded corners, natural lighting, and a clean workshop space. \n'
                           '\n'
                           'Frame 1: A woman carefully selecting linen or cotton-linen blend fabric in the exact same '
                           'color as the dress in the reference image. Show the fabric pieces neatly folded on a '
                           'wooden table or shelf, with spools of thread, dried flowers, and simple sewing tools '
                           'nearby. \n'
                           '\n'
                           'Frame 2: Close-up of a craftsman sketching the overall embroidery layout onto the fabric '
                           "using tailor's chalk. The details of the embroidery should accurately match the dress in "
                           'the reference image. \n'
                           '\n'
                           'Frame 3: Close-up of hands hand-embroidering the sketched design onto the fabric inside a '
                           'wooden embroidery frame. Figure 4: Showing the needle, thread, linen fabric, and '
                           'meticulous hand-stitching, accurately reflecting the design in the reference image. \n'
                           '\n'
                           'Figure 5: A seamstress cuts the fabric into separate parts of the dress on a rustic wooden '
                           'table. Showing scissors, pattern pieces, sleeves, bodice, skirt pieces, and soft linen '
                           'fabric. Maintaining consistent fabric colors with the reference product image. \n'
                           '\n'
                           'Figure 6: A Vietnamese seamstress sews the parts of the dress together using a sewing '
                           "machine, creating a complete children's dress. Showing the craft workshop space with "
                           'natural light, sewing tools, thread, and fabric scraps around the work area. \n'
                           '\n'
                           'Figure 7: The completed dress is being gently ironed on an ironing board or linen-covered '
                           'table. Showing the fabric becoming smooth and neat while retaining its handcrafted texture '
                           'and natural softness. \n'
                           '\n'
                           "Figure 8: The completed children's dress is neatly folded inside a kraft paper gift box, "
                           'placed alongside a matching hair tie. Add a few dried flowers, eucalyptus leaves, a spool '
                           'of thread, and other neutral crafting items around the box. The presentation should feel '
                           'upscale, warm, and ready to be given as a gift to customers on Etsy. \n'
                           '\n'
                           'IMPORTANT: Always choose fabric colors that exactly match the product in the reference '
                           'image. Keep the dress looking handmade, soft, natural, and high-end. The embroidery '
                           'process must look authentic, not mass-produced. Do not alter the dress style to resemble a '
                           'different product. Do not add text overlays, labels, logos, or watermarks. \n'
                           '\n'
                           'STYLE: Photograph the handcrafted embroidery process, photograph the product in an Etsy '
                           'editorial style, bright natural light from a window, a rustic wooden table, a soft '
                           'cream-colored studio background, authentic linen texture, delicate hand stitching, a '
                           'high-end handmade gift presentation, a neat collage layout, and a 1:1 square aspect '
                           'ratio. \n'
                           '\n'
                           'AVOID: Harsh studio lighting, overly yellow lighting, cluttered workspace, plastic-looking '
                           'fabric, machine embroidery appearance, distorted hands, extra fingers, incorrect needle '
                           'placement, inaccurate fabric color, messy dress structure, unrealistic sewing details, AI '
                           'errors, text overlays, logos, watermarks.'))},
 'linen_pillowcase': {'display_name': 'Linen Pillowcase',
                      'aliases': ('Linen Pillowcase',
                                  'linen pillowcase',
                                  'linen pillow',
                                  'embroidered linen pillow',
                                  'vỏ gối linen',
                                  'vo goi linen',
                                  'gối linen',
                                  'goi linen'),
                      'lock': 'the main product must remain the same linen pillowcase/cushion with the exact '
                              'rectangular pillow shape, soft volume, linen weave, embroidered name or motif '
                              'placement, seam/edge finish, fabric color, and home decor scale from the source image',
                      'shots': (('Lifestyle',
                                 'Phụ nữ cầm/ôm gối',
                                 'Use the pillow in the reference image as the main product. Create a realistic '
                                 'product photo depicting everyday life, showing a middle-aged or young woman '
                                 'comfortably seated in a living room (face obscured, only the nose and lower body '
                                 'visible), holding the handcrafted decorative pillow as in the reference image, '
                                 'resting it on her lap. The pillow should be the focal point of the photo, '
                                 'highlighting the fabric, the raised embroidery details, and the high-end finish of '
                                 'the handcrafted product. Soft natural light from a nearby window creates a bright, '
                                 'airy, and natural feel. Use a shallow depth of field to highlight the pillow while '
                                 'maintaining the gentle authenticity of the woman and the living room. \n'
                                 '\n'
                                 'IMPORTANT: Maintain the shape, fabric, color palette, raised embroidery texture, '
                                 'proportions, and handcrafted look of the pillow from the reference image. Do not '
                                 'redesign, redraw, distort, or alter the pillow. Do not add specific embroidery '
                                 'patterns. The embroidery pattern must maintain its overall quality and Versatile for '
                                 'any application. Pillow design. Background only. Landscape and lifestyle surrounding '
                                 'the person holding the pillow. \n'
                                 '\n'
                                 'STYLE: Authentic. Handmade product photos. Lifestyle photos edited in the Etsy '
                                 'style. Home. Beautiful interior spaces, soft natural light from windows, living '
                                 'rooms with neutral tones, shallow depth of field, high-end handmade pillows, raised '
                                 'embroidery, 1:1 square aspect ratio. \n'
                                 '\n'
                                 'AVOID: altering pillow designs, oversized embroidery, embroidering specific '
                                 'characters or names, harsh studio lighting, cluttered backgrounds, plastic-looking '
                                 'fabrics, flat machine embroidery, distorted hands, added fingers, blurry pillow '
                                 'details, mass-produced look, AI errors, text overlays, logos, watermarks.'),
                                ('Product display',
                                 'Hero — 1 gối trên giường',
                                 'Use the pillow in the reference image as the main product. Create an authentic '
                                 'Etsy-style product photo showcasing the handcrafted decorative pillow neatly placed '
                                 'on a cozy bed in a bright, neutral bedroom. The pillow should be the centerpiece, '
                                 'complemented by soft white bedding, neutral linen pillows, a light-colored '
                                 'headboard, a bedside lamp, small potted plants, and minimalist home decor. Soft '
                                 'natural light from the side window creates a clean, warm, and airy feel. Use a '
                                 'shallow depth of field with a slightly blurred background while keeping the pillow '
                                 'sharp and detailed. Highlight the fabric texture, embroidery, stitching, edging, and '
                                 'handcrafted finish. \n'
                                 '\n'
                                 'IMPORTANT: Maintain EXACTLY the shape, fabric texture, color palette, edging '
                                 'details, stitching, embroidery texture, proportions, and handcrafted look of the '
                                 'pillow from the reference image. Do not redesign, redraw, distort, or alter the '
                                 'pillow. Only create a bedroom backdrop and decorative style around the pillow. \n'
                                 '\n'
                                 'STYLE: Authentic handcrafted product photography, Etsy lifestyle photos, cozy '
                                 'bedroom with neutral tones, soft natural light from the window, high-end handcrafted '
                                 'pillow, warm minimalist home decor, shallow depth of field, 1:1 square aspect '
                                 'ratio. \n'
                                 '\n'
                                 'AVOID: altering the pillow design, specific embroidery patterns, harsh studio '
                                 'lighting, cluttered backgrounds, plastic-looking fabric, flat machine embroidery, '
                                 'blurry pillow details, mass-produced appearance, AI errors, text overlays, logos, '
                                 'watermarks.'),
                                ('Product display',
                                 '2 gối cạnh nhau',
                                 'Use the two pillows in the reference photo as the main product. Create an authentic '
                                 'Etsy-style product photo showcasing the two pillows neatly arranged on a '
                                 'light-colored sofa in a bright living room. Decorate the scene with minimalist '
                                 'cream-colored furniture, soft window curtains, a vase of fresh flowers, and light, '
                                 'romantic decorative items. Use a shallow depth of field with a slightly blurred '
                                 'background while keeping the pillows sharp and detailed. \n'
                                 '\n'
                                 'IMPORTANT: Keep the pillow shape, material, color palette, embroidery placement, '
                                 'proportions, and handcrafted look of the pillows EXACTLY as in the reference photo. '
                                 'Do not redesign, repaint, distort, or alter the pillows. Only create the background '
                                 'and decorate the living room around the pillows. \n'
                                 '\n'
                                 'STYLE: Authentic handcrafted product photography, Etsy-style lifestyle photos, cozy '
                                 'and romantic home decor, soft natural light from windows, pastel color palette, '
                                 'high-end personalized pillows, shallow depth of field, 1:1 square aspect ratio. \n'
                                 '\n'
                                 'AVOID: altering pillow shapes, inaccurate embroidered names or lettering, overly '
                                 'harsh studio lighting, cluttered backgrounds, plastic-looking fabrics, flat machine '
                                 'embroidery, blurry pillow details, distorted heart shapes, mass-produced appearance, '
                                 'AI errors, text overlays, logos, watermarks.'),
                                ('Product display',
                                 '4 gối stack dọc',
                                 'Use the four pillows in the reference photo as the main product. Create an authentic '
                                 'Etsy-style product photo, showcasing three neatly arranged handmade pillows on a '
                                 'light-colored wooden bench, with one standing upright to highlight the embroidery. '
                                 'Use a clean cream or white background with minimalist decor to accentuate the colors '
                                 'and textures. \n'
                                 '\n'
                                 'IMPORTANT: Maintain the pillow shape, color palette, embroidery placement, '
                                 'proportions, and handcrafted look as in the reference photo. Do not redesign, '
                                 'redraw, distort, or alter the pillows. Only improve the background, lighting, and '
                                 'product style. \n'
                                 '\n'
                                 'STYLE: Authentic handcrafted product photography, Etsy editorial style product '
                                 'photo, soft natural light from a window, cozy cottage style, minimalist background, '
                                 'high-quality handmade pillows, 1:1 square aspect ratio. \n'
                                 '\n'
                                 'AVOID: changing colors. Altering pillows, embroidery designs, or specific embroidery '
                                 'patterns. Example: Harsh studio lighting, cluttered background, flat machine '
                                 'embroidery, blurry fabric details, distorted folded edges, mass-produced appearance, '
                                 'AI errors, text overlays, logos, watermarks.'),
                                ('Product display',
                                 '3 gối 3 màu',
                                 'Using three pillows as shown in the reference image as the main product, three '
                                 'pillows in three different colors (but with the same embroidery style, the same '
                                 'color of eyelet embroidery thread, and different pillowcase colors), arrange them '
                                 'neatly on a white crib or baby bed, one in the crib, one on the bed. Decorate the '
                                 'scene with clean white bedding, soft cloud-shaped pillows in the background, and a '
                                 'bright, minimalist nursery space. Keep the layout clean, focusing on the product. \n'
                                 '\n'
                                 'IMPORTANT: Maintain the pillow shape, fabric, color palette, embroidery placement, '
                                 'proportions, and handcrafted look from the reference image. Do not redesign, '
                                 'repaint, distort, or alter the pillows. Only improve the nursery background, '
                                 'lighting, and product style. \n'
                                 '\n'
                                 'STYLE: Authentic handcrafted product photos, Etsy-style editorial product photos, '
                                 'soft natural light from the window, bright white nursery, cozy nursery aesthetics, '
                                 'high-end personalized pillows, backdrop. Minimalist, clean, balanced. 1:1 square '
                                 'ratio. \n'
                                 '\n'
                                 'AVOID: changing pillow colors, changing pillow shapes, embroidering specific names, '
                                 'harsh studio lighting, cluttered backdrops, blurred or distorted fabric details, '
                                 'flat machine embroidery, mass-produced patterns, AI errors, text overlays, logos, '
                                 'watermarks.'),
                                ('Cận thêu tay',
                                 'Cận thêu — collage',
                                 'Use the pillow in the reference image as the main product. Create a detailed collage '
                                 'in the Etsy style, showcasing the handcrafted pillow up close. Arrange the images '
                                 'into four neat frames with minimal white borders, similar to a high-end product '
                                 'detail sheet. Each small image shows a close-up of the raised embroidery on the '
                                 'pillow from different angles. \n'
                                 '\n'
                                 'IMPORTANT: Maintain the EXACT pillow shape, fabric material, color palette, '
                                 'embroidery placement, border or ruffle details, stitching, proportions, and '
                                 'handcrafted look from the reference image. Do not redesign, redraw, distort, or '
                                 'alter the pillow. Only improve the close-up composition, lighting, and product '
                                 'photography style. \n'
                                 '\n'
                                 'STYLE: Authentic handcrafted product photos, detailed collage in the Etsy editorial '
                                 'style, soft natural light from a window, neutral linen background, close-up of '
                                 'fabric texture, raised embroidery, high-end handcrafted pillow, 1:1 square aspect '
                                 'ratio. \n'
                                 '\n'
                                 'AVOID: changing the pillow design, altering colors, harsh lighting, distracting '
                                 'backgrounds, blurry stitching, fabric that looks like plastic, flat machine '
                                 'embroidery, distorted pillow shape, AI errors, text overlaying images, logos, and '
                                 'watermarks.'),
                                ('Product display',
                                 'Bé nằm trên gối',
                                 'Use the pillow in the reference photo as the main product. Create an authentic '
                                 'Etsy-style product photo showing a baby comfortably lying on a soft bed or sofa, '
                                 'gently hugging the pillow and sleeping, with the pillow as the focal point of the '
                                 'photo. Use a shallow depth of field so the baby and pillow are in focus while the '
                                 'background texture is slightly blurred. Highlight the fabric, soft stuffing, '
                                 'embroidery, stitching, and the handcrafted look of the pillow. \n'
                                 '\n'
                                 'IMPORTANT: Keep the shape, fabric texture, color palette, embroidery placement, '
                                 'proportions, and handcrafted look of the pillow from the reference photo. Do not '
                                 'redesign, redraw, distort, or alter the pillow. Only create the context and style of '
                                 'the photo showing the baby hugging the pillow. \n'
                                 '\n'
                                 'STYLE: Authentic handcrafted product photography, Etsy lifestyle, soft natural light '
                                 "from a window, baby's room or living room, warm neutral tones, high-quality "
                                 'handcrafted pillow, shallow depth of field. Shallow, 1:1 square aspect ratio. \n'
                                 '\n'
                                 'AVOID: pillow design editing, special embroidery, harsh studio lighting, cluttered '
                                 'background, distorted baby body images, added fingers, blurry pillow details, '
                                 'plastic-looking fabric, mass-produced appearance, AI errors, text overlays, logos, '
                                 'watermarks.'),
                                ('Product display',
                                 'Gối trên bàn/bề mặt + props',
                                 'Use the pillowcases from the reference image as the main product. Create an '
                                 'authentic Etsy-style product photo showcasing three handmade pillowcases in three '
                                 'different colors (three different pillowcase colors but the same yarn color and '
                                 'embroidery pattern), neatly arranged on a clean sofa. Arrange them side-by-side so '
                                 'that all three pillowcases are clearly visible.\n'
                                 '\n'
                                 'Keep the scene bright, clean, and minimalist. Use soft natural light from the side '
                                 'or a nearby window. The background should be simple and beautifully decorated.\n'
                                 '\n'
                                 'IMPORTANT: Maintain the EXACT shape, fabric, color palette, embroidery placement, '
                                 'proportions, and handmade look of the pillowcases from the reference image. Do not '
                                 'redesign, redraw, distort, or alter the product. Simply create a white table layout, '
                                 'lighting, and display the product around it.\n'
                                 '\n'
                                 'STYLE: Authentic handmade product photo, editorial style product photo Etsy, soft '
                                 'natural light from the window. Notebook, dark layout. Simple white desk, '
                                 'high-quality handmade pillowcase, 1:1 square aspect ratio.\n'
                                 '\n'
                                 'AVOID: changing pillowcase design, harsh studio lighting, cluttered background, '
                                 'blurred or distorted fabric details, flat machine embroidery, mass-produced images, '
                                 'AI errors, text overlays, logos, watermarks.'),
                                ('Quy trình',
                                 'Quy trình thêu',
                                 'Use the pillowcase from the reference image as the main product. Create an '
                                 'Etsy-style photo of the crafting process, showing a woman sitting at a table and '
                                 'carefully embroidering with a wool embroidery needle (wooden-handled wool embroidery '
                                 "needle, 1 large, sharp needle, with the yarn at the tip matching the needle's "
                                 'position), a pattern onto fabric in the same color as the pillowcase on the '
                                 "embroidery frame. Focus on the woman's hands, the embroidery frame or fabric area, "
                                 'the embroidery tools, the yarn, and the front of the pillowcase, keeping the product '
                                 'the main subject. Set the scene in a comfortable, handcrafted workspace with a '
                                 'wooden table, soft natural light from a window, and a backdrop of embroidery '
                                 'threads, scissors, and a few simple sewing tools nearby. Keep the scene clean, '
                                 'bright, and slightly dark. Highlight the fabric texture, stitching, embroidery '
                                 'texture, and the handcrafted quality of the pillowcase, marking the exact embroidery '
                                 'locations as in the reference image—just make sure to mark precisely. Color. \n'
                                 '\n'
                                 'IMPORTANT: Maintain the EXACT image. The shape, fabric texture, color palette, '
                                 'embroidery lines... The position, proportions, and handcrafted look of the '
                                 'pillowcase are taken from the reference image. Do not redesign, redraw, distort, or '
                                 'alter the pillowcase. The background and style should focus solely on the woman '
                                 'embroidering. \n'
                                 '\n'
                                 'STYLE: Authentic handcrafted product photography. Etsy-style editing process, soft '
                                 'natural light from a window. Window, cozy craft room space, minimalist style, '
                                 'high-end handcrafted pillowcase, shallow depth of field, 1:1 square aspect ratio. \n'
                                 '\n'
                                 'AVOID: altering the pillowcase design, harsh studio lighting, cluttered background, '
                                 'blurry embroidery details, distorted hands, added fingers, unrealistic needle '
                                 'placement, flat machine embroidery, mass-produced look, AI errors, text overlays, '
                                 'logos, watermarks.'),
                                ('Product display',
                                 'Standalone đơn #2',
                                 'Use the pillow in the reference image as the main product. Create an authentic '
                                 'Etsy-style product photo showcasing a handcrafted decorative pillow neatly placed on '
                                 'a cozy armchair in a bright living room. Decorate the scene with a neutral-colored '
                                 'upholstered chair, soft window lighting, a small wooden table, books, a ceramic mug, '
                                 'a potted plant, and minimalist home decor.\n'
                                 '\n'
                                 'IMPORTANT: Maintain EXACTLY the pillow shape, fabric texture, color palette, '
                                 'embroidery placement, proportions, stitching, and handcrafted look from the '
                                 'reference image. Do not redesign, redraw, distort, or alter the pillow. Only create '
                                 'the living room setting, lighting, and decorations around the pillow.\n'
                                 '\n'
                                 'STYLE: Authentic handcrafted product photography, Etsy-style lifestyle photos, cozy '
                                 'living room with neutral tones, soft natural light from the window, high-quality '
                                 'handcrafted pillows, warm minimalist home decor, shallow depth of field, 1:1 square '
                                 'aspect ratio.\n'
                                 '\n'
                                 'AVOID: pillow design alterations, harsh studio lighting, cluttered backgrounds, '
                                 'blurry embroidery, distorted pillow shapes, flat machine embroidery, plastic-looking '
                                 'fabric, mass-produced appearance, AI errors, text overlays, logos, watermarks.'),
                                ('Product display',
                                 '2 gối variant #2',
                                 'Use the two pillows in the reference photo as the main product. Create an authentic '
                                 'Etsy-style product photo showing two 3-year-old children comfortably seated on a '
                                 'soft bed or sofa, each gently holding a pillow (two pillows of different colors but '
                                 'with the same embroidery pattern). The two pillows should be the focal point of the '
                                 'photo. Use a shallow depth of field so the children and pillows are in focus while '
                                 'the background texture is slightly blurred. Highlight the fabric, soft stuffing, '
                                 'embroidery, stitching, and handcrafted look of the pillows.\n'
                                 '\n'
                                 'IMPORTANT: Keep the shape, fabric texture, color palette, embroidery placement, '
                                 'proportions, and handcrafted look of the pillows from the reference photo. Do not '
                                 'redesign, redraw, distort, or alter the pillows. Only create the context and style '
                                 'of the photo showing the children holding the pillows.\n'
                                 '\n'
                                 'STYLE: Handcrafted product photography. Authentic, lifestyle-inspired. Etsy, light. '
                                 "Gentle natural light from the window, a children's room. Bedroom. Or a cozy living "
                                 'room, warm neutral tones. High-quality handcrafted pillows, shallow depth of field, '
                                 '1:1 square aspect ratio.\n'
                                 '\n'
                                 'AVOID: pillow design editing, special embroidery, harsh studio lighting, cluttered '
                                 'background, distorted baby body images, added fingers, blurry pillow details, '
                                 'plastic-looking fabric, mass-produced appearance, AI errors, text overlays, logos, '
                                 'watermarks.'),
                                ('Gift box',
                                 'Gift box',
                                 'A beautifully wrapped pillowcase is placed in an open paper gift box, highlighting '
                                 "the delicate hand-embroidered pattern. The pillowcase is neatly folded (because it's "
                                 'a pillowcase, it will flatten and not puff up like a regular pillow), the embroidery '
                                 'stands out, and the material is soft and elegant. The background is minimalist and '
                                 'bright with natural light. Focus on the pillowcase. \n'
                                 '\n'
                                 'IMPORTANT: Do not alter the design of the pillowcase or the embroidery. Focus on how '
                                 'the pillowcase is presented in the gift box. Keep the embroidery clearly visible '
                                 'through the packaging. Highlight the material and the neat folding of the '
                                 'pillowcase. Natural light, a bright and clean layout. \n'
                                 '\n'
                                 'STYLE: Present the gift elegantly, with a minimalist aesthetic, soft natural light, '
                                 'subtle sheen to highlight the material, and a neutral background to highlight the '
                                 'gift box and embroidery. Close-up and medium shots show the details of the wrapping '
                                 'paper and embroidery. \n'
                                 '\n'
                                 'AVOID: Leaving the pillowcase exposed. box. Avoid cluttered backgrounds, harsh '
                                 'shadows, or artificial props that distract attention from the gift presentation. Do '
                                 'not distort the embroidery or the shape of the pillowcase.'))},
 'wedding_pillowcase': {'display_name': 'Wedding Pillowcase',
                        'aliases': ('Wedding Pillowcase',
                                    'wedding pillowcase',
                                    'wedding pillow',
                                    'bride groom pillow',
                                    'bride and groom pillow',
                                    'gối cưới',
                                    'goi cuoi',
                                    'vỏ gối cưới',
                                    'vo goi cuoi'),
                        'lock': 'the main product must remain the same wedding pillowcase/cushion with the exact '
                                'pillow shape, fabric surface, embroidered wedding lettering or motif placement, soft '
                                'volume, seam/edge finish, and romantic keepsake scale from the source image',
                        'shots': (('Lifestyle',
                                   'Cô dâu ôm/cầm gối',
                                   'Use the pillow in the reference image as the main product. Create a realistic '
                                   'product photo depicting everyday life, showing the bride comfortably seated in the '
                                   'bridal room (face not visible, only from the nose down), holding the handcrafted '
                                   'decorative pillow as in the reference image, placed on her lap. The pillow should '
                                   'be the focal point of the photo, highlighting the fabric, the raised hand '
                                   'embroidery details, and the high-end finish of the handcrafted product. Soft '
                                   'natural light from a nearby window creates a bright, airy, and natural feel. Use a '
                                   'shallow depth of field to highlight the pillow while maintaining the gentle '
                                   'authenticity of the bride and the bridal room.\n'
                                   '\n'
                                   'IMPORTANT: Maintain the shape, fabric, color palette, raised embroidery texture, '
                                   'proportions, and handcrafted look of the pillow from the reference image. Do not '
                                   'redesign, redraw, distort, or alter the pillow. Do not add specific embroidery '
                                   'patterns. The embroidery pattern must maintain its overall quality and versatility '
                                   'for all applications. Design Pillow. Only use as a backdrop. The scenery and '
                                   'lifestyle surrounding the person holding the pillow.\n'
                                   '\n'
                                   'STYLE: Authentic. Handmade product photos. Lifestyle photos edited in the Etsy '
                                   'style. Homes. Beautiful interior spaces, soft natural light from windows, wedding '
                                   'rooms with neutral tones, shallow depth of field, high-end handmade pillows, '
                                   'raised embroidery, 1:1 square aspect ratio.\n'
                                   '\n'
                                   'AVOID: altering pillow design, oversized embroidery, embroidering specific '
                                   'characters or names, harsh studio lighting, cluttered backgrounds, plastic-looking '
                                   'fabric, flat machine embroidery, distorted hands, added fingers, blurry pillow '
                                   'details, mass-produced look, AI errors, text overlays, logos, watermarks.'),
                                  ('Product display',
                                   'Hero — gối trên giường',
                                   'Use the pillow in the reference photo as the main product. Create an authentic '
                                   'Etsy-style product photo showcasing the handcrafted decorative pillow neatly '
                                   'placed on the wedding bed in a bright, neutral bedroom. The pillow should be the '
                                   'focal point, complemented by soft white bedding, neutral-colored linen pillows, a '
                                   'light-colored headboard, bedside lamp, a large wedding bouquet resting on the '
                                   'bedside table, and minimalist wedding decorations. Soft natural light from the '
                                   'side window creates a clean, warm, and airy feel. Use a shallow depth of field '
                                   'with a slightly blurred background while keeping the pillow sharp and detailed. '
                                   'Highlight the fabric texture, embroidery, stitching, edging, and handcrafted '
                                   'finish. \n'
                                   '\n'
                                   'IMPORTANT: Keep the shape, fabric texture, color palette, stitching, embroidery '
                                   'texture, proportions, and handcrafted look of the pillow from the reference photo. '
                                   'Do not redesign, redraw, distort, or alter the pillow. Only create the bedroom '
                                   'background and Surrounding decorations. The pillow. \n'
                                   '\n'
                                   'STYLE: Authentic handcrafted product photography, Etsy lifestyle photos, wedding '
                                   'room with neutral tones, soft natural light from the window, high-end handcrafted '
                                   'pillows, minimalist home decor, shallow depth of field, 1:1 square aspect ratio. \n'
                                   '\n'
                                   'AVOID: Pillow design editing, specific embroidery patterns, harsh studio lighting, '
                                   'cluttered backgrounds, plastic-looking fabrics, flat machine embroidery, blurry '
                                   'pillow details, mass-produced look, AI errors, text overlays, logos, watermarks.'),
                                  ('Product display',
                                   '2 gối — Bride & Groom',
                                   'Use the two pillows in the reference photo as the main product. Create an '
                                   'authentic Etsy-style product photo showcasing the two pillows neatly arranged on a '
                                   'light-colored sofa in a bright living room. Decorate the scene with minimalist '
                                   'cream-colored furniture, soft window curtains, and light, romantic wedding '
                                   'decorations. Use a shallow depth of field with a slightly blurred background while '
                                   'keeping the pillows sharp and detailed. \n'
                                   '\n'
                                   'IMPORTANT: Maintain the shape, material, color palette, embroidery placement, '
                                   'proportions, and handcrafted look of the pillows as in the reference photo. Do not '
                                   'redesign, repaint, distort, or alter the pillows. Only create the background and '
                                   'decorate the living room around the pillows. \n'
                                   '\n'
                                   'STYLE: Authentic handcrafted product photography, Etsy lifestyle photo, romantic '
                                   'home decor, soft natural light from the window, pastel color palette, highly '
                                   'personalized pillows, shallow depth of field, shallow angle, proportions. 1:1 '
                                   'square. \n'
                                   '\n'
                                   'AVOID: altering the pillow shape, the exact name or lettering embroidered, overly '
                                   'harsh studio lighting, cluttered layout, plastic-like material, flat machine '
                                   'embroidery, blurry pillow details, distorted heart shape, mass-produced '
                                   'appearance, AI errors, text overlays, logos, watermarks.'),
                                  ('Product display',
                                   '4 gối stack dọc',
                                   'Use the four pillows in the reference photo as the main product. Create an '
                                   'authentic Etsy-style product photo, showcasing three neatly arranged handmade '
                                   'pillows on a light-colored wooden bench, with one standing upright to highlight '
                                   'the embroidery. Use a clean cream or white background with minimalist decor to '
                                   'accentuate the colors and textures. \n'
                                   '\n'
                                   'IMPORTANT: Keep the pillow shape, color palette, embroidery placement, '
                                   'proportions, and handcrafted look as in the reference photo. Do not redesign, '
                                   'redraw, distort, or alter the pillows. Only improve the background, lighting, and '
                                   'product style. \n'
                                   '\n'
                                   'STYLE: Authentic handcrafted product photography, Etsy editorial style product '
                                   'photo, soft natural light from a window, cozy cottage style, minimalist '
                                   'background, high-quality handmade pillows, 1:1 square aspect ratio. \n'
                                   '\n'
                                   'AVOID: changing colors. Changing pillows, embroidery designs, or embroidery '
                                   'patterns. Specifically. For example: Harsh studio lighting, cluttered background, '
                                   'flat machine embroidery, blurry fabric details, distorted folded edges, '
                                   'mass-produced appearance, AI errors, text overlays, logos, watermarks.'),
                                  ('Product display',
                                   '3 gối 3 màu',
                                   'Using three pillows as shown in the reference image but in different colors as the '
                                   'main product, three pillows with three different colors (but with the same '
                                   'embroidery style, same thread color, and unique embroidery name), arrange them '
                                   'neatly on a white crib or baby bed, one in the crib, one on the bed. Decorate the '
                                   'scene with clean white bedding, soft cloud-shaped pillows, and a bright, '
                                   'minimalist nursery space. Keep the layout neat, focusing on the product. \n'
                                   '\n'
                                   'IMPORTANT: Maintain the pillow shape, fabric material, color palette, embroidery '
                                   'placement, proportions, and handcrafted look from the reference image. Do not '
                                   'redesign, repaint, distort, or alter the pillows. Only improve the nursery space, '
                                   'lighting, and product style. \n'
                                   '\n'
                                   'STYLE: Authentic handcrafted product photos, Etsy editorial style product photos, '
                                   'soft natural light from the window, bright white nursery room, nursery aesthetics, '
                                   'pillow-shaped pillows. Fish. Premium, personalized backdrop. Minimalist, clean, '
                                   'balanced. 1:1 ratio. \n'
                                   '\n'
                                   'AVOID: changing pillow colors, changing pillow shapes, embroidery. Specific names, '
                                   'harsh studio lighting, cluttered backdrops, blurred or distorted fabric details, '
                                   'warped edges, flat machine embroidery, mass-produced patterns, AI errors, text '
                                   'overlays, logos, watermarks.'),
                                  ('Cận thêu tay',
                                   'Cận thêu — collage',
                                   'Use the pillow in the reference image as the main product. Create a detailed '
                                   'collage in the Etsy style, showcasing the handcrafted pillow up close. Arrange the '
                                   'images into four neat frames with minimal white borders, similar to a high-end '
                                   'product detail sheet. Each small image shows a close-up of the raised embroidery '
                                   'on the pillow from different angles. \n'
                                   '\n'
                                   'IMPORTANT: Maintain the EXACT pillow shape, fabric material, color palette, '
                                   'embroidery placement, border or ruffle details, stitching, proportions, and '
                                   'handcrafted look from the reference image. Do not redesign, redraw, distort, or '
                                   'alter the pillow. Only improve the close-up composition, lighting, and product '
                                   'photography style. \n'
                                   '\n'
                                   'STYLE: Authentic handcrafted product photos, detailed collage in the Etsy '
                                   'editorial style, soft natural light from a window, neutral linen background, '
                                   'close-up of fabric texture, raised embroidery, high-end handcrafted pillow, 1:1 '
                                   'square aspect ratio. \n'
                                   '\n'
                                   'AVOID: changing the pillow design, altering colors, harsh lighting, distracting '
                                   'backgrounds, blurry stitching, fabric that looks like plastic, flat machine '
                                   'embroidery, distorted pillow shape, AI errors, text overlaying images, logos, and '
                                   'watermarks.'),
                                  ('Product display',
                                   'Standalone đơn',
                                   'Use the pillows from the reference image as the main product. Create an authentic '
                                   'Etsy-style product photo, showing a pillow, just like in the reference image, '
                                   'placed on a windowsill. Decorate the scene with soft natural light from the '
                                   'window, pastel-colored walls, linen curtains, a large wedding bouquet, books, '
                                   'candles, and minimalist, light wedding home decor. Keep the pillows in the center '
                                   'and easily visible. The background should feel airy, romantic, and elegant, '
                                   'matching the Etsy product image. \n'
                                   '\n'
                                   'IMPORTANT: Maintain the pillow shape, fabric, color palette, embroidery placement, '
                                   'proportions, and handcrafted look from the reference image. Do not redesign, '
                                   'redraw, distort, or alter the pillows. Create a background for the windowsill, '
                                   'lighting, and decorations surrounding the pillows. \n'
                                   '\n'
                                   'STYLE: Authentic handcrafted product photography, Etsy lifestyle photo, airy '
                                   'window scene, and Bright, soft, natural golden sunlight, minimalist home decor, '
                                   'high-end personalization. Pillows, shallow depth of field, 1:1 square aspect '
                                   'ratio. \n'
                                   '\n'
                                   'AVOID: changing pillow colors, changing pillow shapes, embroidering specific '
                                   'details. Names, overly harsh studio lighting, cluttered backgrounds, blurry '
                                   'embroidery, distorted borders, flat machine embroidery, mass-produced appearance, '
                                   'AI errors, overlapping text, logos, watermarks.'),
                                  ('Lifestyle',
                                   'Đôi uyên ương trên giường',
                                   'Use the pillow in the reference photo as the main product. Create an authentic '
                                   'Etsy-style product photo showing the bride and groom comfortably seated on a soft '
                                   "bed or sofa, gently holding the pillow in both hands. Don't capture the entire "
                                   'face of the bride and groom; only photograph from the nose down, and the pillow '
                                   'should be the focal point of the photo. Use a shallow depth of field so the bride, '
                                   'groom, and pillow are in focus while the background texture is slightly blurred. '
                                   'Highlight the fabric, soft stuffing, embroidery, stitching, and handcrafted look '
                                   'of the pillow. \n'
                                   '\n'
                                   'IMPORTANT: Maintain the shape, fabric texture, color palette, embroidery '
                                   'placement, proportions, and handcrafted look of the pillow from the reference '
                                   'photo. Do not redesign, redraw, distort, or alter the pillow. Only create the '
                                   'context and style of the photo showing the bride and groom holding the pillow. \n'
                                   '\n'
                                   'STYLE: Authentic handcrafted product photography, Etsy lifestyle, natural '
                                   'lighting. Gentle breeze from the window, wedding room. Or a cozy wedding room, '
                                   'warm neutral tones, high-quality handcrafted pillows, shallow depth of field, 1:1 '
                                   'square aspect ratio. \n'
                                   '\n'
                                   'AVOID: pillow design editing, special embroidery, harsh studio lighting, cluttered '
                                   'background, distorted baby body images, added fingers, blurry pillow details, '
                                   'plastic-looking fabric, mass-produced appearance, AI errors, text overlays, logos, '
                                   'watermarks.'),
                                  ('Product display',
                                   '3 gối tổng hợp',
                                   'Use the pillowcases from the reference image as the main product. Create an '
                                   'authentic Etsy-style product photo showcasing three handmade pillowcases in three '
                                   'different colors (each with a different pair of embroidered names), neatly '
                                   'arranged on a clean, soft sofa, complemented by a large, beautiful, and modern '
                                   'wedding bouquet. Arrange them side-by-side so that all three pillowcases are '
                                   'clearly visible.\n'
                                   '\n'
                                   'Keep the scene bright, clean, and minimalist. Use soft natural light from the side '
                                   'or a nearby window. The background should be simple and beautifully decorated.\n'
                                   '\n'
                                   'IMPORTANT: Maintain the EXACT shape, fabric, color palette, embroidery placement, '
                                   'proportions, and handcrafted look of the pillowcases from the reference image. Do '
                                   'not redesign, redraw, distort, or alter the product. Simply create a white table '
                                   'layout, lighting, and display the product around it.\n'
                                   '\n'
                                   'STYLE: Authentic handmade product photo, photo Etsy-style product, soft natural '
                                   'light. Window light, dark layout. Simple white table, high-quality handmade '
                                   'pillowcases, 1:1 square aspect ratio.\n'
                                   '\n'
                                   'AVOID: altering pillowcase designs, overly bright lighting. Studio lighting, '
                                   'cluttered background, blurry fabric details, distorted shapes, flat machine '
                                   'embroidery, mass-produced images, AI errors, text overlays, logos, watermarks.'),
                                  ('Quy trình',
                                   'Quy trình thêu',
                                   'Use the pillowcase from the reference image as the main product. Create an '
                                   'Etsy-style photo of the crafting process, showing a woman sitting at a table '
                                   'carefully embroidering a pattern onto fabric the same color as the pillowcase '
                                   'using a wool embroidery needle (a wooden-handled wool embroidery needle, one '
                                   "large, sharp needle, with the yarn at the tip matching the needle's position). "
                                   "Focus on the woman's hands, the embroidery frame or fabric area, the embroidery "
                                   'tools, the yarn, and the front of the pillowcase, keeping the product the main '
                                   'subject. Set the scene in a comfortable, handcrafted workspace with a wooden '
                                   'table, soft natural light from a window, and a backdrop of embroidery threads, '
                                   'scissors, and a few simple sewing tools nearby. Keep the scene clean and bright. '
                                   'Highlight the fabric texture, stitching, embroidery texture, and the handcrafted '
                                   'quality of the pillowcase, marking the correct embroidery placement as in the '
                                   'reference image, just make sure to use the correct colors. \n'
                                   'QUAN IMPORTANT: Maintain the image EXACTLY. Shape, fabric, color palette, '
                                   'embroidery placement, proportions, and... The illustrative image of the '
                                   'handcrafted style of the pillowcase is taken from a reference image. Do not '
                                   'redesign, redraw, distort, or alter the pillowcase. The background and style '
                                   'should focus solely on the woman embroidering. \n'
                                   '\n'
                                   'STYLE: Authentic handcrafted product photography. Editing process in the style of '
                                   'Etsy, soft natural light from a window. Window, cozy craft room space, minimalist '
                                   'style, high-end handcrafted pillowcase, shallow depth of field, 1:1 square aspect '
                                   'ratio. \n'
                                   '\n'
                                   'AVOID: altering the pillowcase design, harsh studio lighting, cluttered '
                                   'background, blurry embroidery details, distorted hands, added fingers, unrealistic '
                                   'needle placement, flat machine embroidery, mass-produced look, AI errors, text '
                                   'overlays, logos, watermarks.'),
                                  ('Product display',
                                   'Standalone #2',
                                   'Use the pillow in the reference photo as the main product. Create an authentic '
                                   'Etsy-style product photo showcasing a handcrafted decorative pillow neatly placed '
                                   'on a wedding chair in an outdoor wedding setting. Decorate the wedding scene with '
                                   'a wedding table, soft lighting, a small wooden table, flowers, wedding '
                                   'invitations, a large wedding bouquet, and minimalist home decor. \n'
                                   '\n'
                                   'IMPORTANT: Maintain the exact pillow shape, fabric, color palette, embroidery '
                                   'placement, proportions, stitching, and handcrafted look as in the reference photo. '
                                   'Do not redesign, redraw, distort, or alter the pillow. Only create the outdoor '
                                   'wedding setting, lighting, and decorations around the pillow. \n'
                                   '\n'
                                   'STYLE: Authentic handcrafted product photography, Etsy lifestyle photo, bright '
                                   'wedding setting, soft natural lighting, high-quality handcrafted pillow, shallow '
                                   'depth of field. 1:1 square aspect ratio. \n'
                                   '\n'
                                   'AVOID: altering the pillow design, lighting Harsh studio lighting, messy '
                                   'background, blurry embroidery, distorted pillow shape, flat machine embroidery, '
                                   'plastic-like material, mass production. Appearance, AI errors, text overlay, logo, '
                                   'watermark.'),
                                  ('Product display',
                                   '2 bé nằm trên 2 gối',
                                   'Use the two pillows in the reference image as the main product. Create an '
                                   'authentic Etsy-style product photo showing two babies comfortably seated on a soft '
                                   'bed or sofa, each gently holding a pillow with both hands (two pillows of '
                                   "different colors but with the same embroidery). Do not photograph the babies' "
                                   'entire faces, only from the nose down, and the pillows should be the focal point '
                                   'of the photo. Use a shallow depth of field so that the babies and pillows are in '
                                   'focus while the background texture is slightly blurred. Highlight the fabric, soft '
                                   'stuffing, embroidery, stitching, and the handcrafted look of the pillows.\n'
                                   '\n'
                                   'IMPORTANT: Maintain the shape, fabric texture, color palette, embroidery '
                                   'placement, proportions, and handcrafted look of the pillows from the reference '
                                   'image. Do not redesign, redraw, distort, or alter the pillows. Only create the '
                                   'context and style of the photo showing the babies holding the pillows.\n'
                                   '\n'
                                   'STYLE: Authentic handcrafted product photography, lifestyle style. Etsy, soft '
                                   "natural light from the window, a child's room. Or a cozy living room, warm neutral "
                                   'tones, high-quality handcrafted pillows, shallow depth of field, 1:1 square aspect '
                                   'ratio.\n'
                                   '\n'
                                   'AVOID: pillow design editing, special embroidery, harsh studio lighting, cluttered '
                                   'background, distorted baby body images, added fingers, blurry pillow details, '
                                   'plastic-looking fabric, mass-produced appearance, AI errors, text overlays, logos, '
                                   'watermarks.'),
                                  ('Product display',
                                   '2 gối realistic',
                                   'Use the pillowcases from the reference image as the main product. Create a '
                                   'realistic Etsy-style product photo showing two embroidered pillowcases, identical '
                                   'to the reference image, neatly placed side-by-side on a clean white bed. The '
                                   'setting should be a bright, modern bedroom with white bedding, a wooden headboard, '
                                   'simple bedside tables, soft pendant lights, and a framed wedding photo above the '
                                   'bed. Soft natural light streams in from the side window, creating a clean, airy, '
                                   'and romantic bedroom atmosphere. Keep the layout focused and minimalist, with the '
                                   'pillowcases clearly displayed as the main focal point. \n'
                                   '\n'
                                   'IMPORTANT: Maintain EXACTLY the shape of the pillowcases, fabric texture, color '
                                   'palette, embroidery placement, proportions, and handcrafted look from the '
                                   'reference image. Do not redesign, redraw, distort, or alter the pillowcases. '
                                   'Simply create a background, lighting, and bedroom decor style that complements the '
                                   'product. \n'
                                   '\n'
                                   'STYLE: Authentic handcrafted product photos, Etsy lifestyle photos, romantic '
                                   'modern bedroom, soft natural light from the window, pristine white bedding, '
                                   'personalized premium pillowcases, minimalist home decor, 1:1 square aspect '
                                   'ratio. \n'
                                   '\n'
                                   'AVOID: altered pillowcase shapes, specific embroidered names, harsh studio '
                                   'lighting, cluttered backgrounds, blurry embroidery, distorted pillows, '
                                   'plastic-like fabric, mass-produced appearance, AI errors, text overlays, logos, '
                                   'watermarks.'),
                                  ('Gift box',
                                   'Gift box — quà cưới',
                                   'A beautifully wrapped pillowcase is placed in an open paper gift box, highlighting '
                                   'the delicate hand-embroidered pattern. The pillowcase is neatly folded, the '
                                   'embroidery stands out, and the material is soft and elegant. The background is '
                                   "minimalist and bright with natural light. Focus on the pillowcase (it's just a "
                                   'pillowcase, so it will flatten, not puff up like the pillow in the picture).\n'
                                   '\n'
                                   'IMPORTANT: Do not alter the design of the pillowcase or the embroidery. Focus on '
                                   'how the pillowcase is presented in the gift box. Keep the embroidery clearly '
                                   'visible through the packaging. Highlight the material and the neat folding of the '
                                   'pillowcase. Natural light, bright and clean layout.\n'
                                   '\n'
                                   'STYLE: Present the gift elegantly, with a minimalist aesthetic, soft natural '
                                   'light, subtle sheen to highlight the material, and a neutral background to '
                                   'highlight the gift box and embroidery. Close-up and medium shots show the details '
                                   'of the wrapping paper and embroidery.\n'
                                   '\n'
                                   'AVOID: Leaving the pillowcase exposed outside the box. Avoid A cluttered '
                                   'background, harsh shadows, or artificial props distract attention from the '
                                   'presentation of the gift. Do not distort the embroidery or the shape of the '
                                   'pillowcase.'))},
 'christmas_pillowcase': {
     'display_name': 'Christmas Pillowcase',
     'aliases': (
         'Christmas Pillowcase',
         'christmas pillowcase',
         'Christmas Pillow Case',
         'christmas pillow case',
         'Christmas Pillow',
         'christmas pillow',
         'Christmas Baby Pillow',
         'christmas baby pillow',
         'Christmas Cushion',
         'christmas cushion',
         'Christmas Baby Cushion',
         'christmas baby cushion',
         'Christmas Nursery Pillow',
         'christmas nursery pillow',
         'Christmas Embroidered Pillow',
         'christmas embroidered pillow',
         'Christmas Punch Needle Pillow',
         'christmas punch needle pillow',
         'Noel Pillowcase',
         'noel pillowcase',
         'Noel Pillow',
         'noel pillow',
         'goi christmas',
         'vo goi christmas',
         'goi noel',
         'vo goi noel',
     ),
     'target_count': 12,
     'allow_planned_multi_panel_shots': True,
     'lock': (
         'the main product must remain the exact same handmade Christmas pillow or pillowcase from the source image, '
         'with the same silhouette, volume or flat-cover construction, fabric and base color, seams, embroidery motif '
         'and source name when present, embroidery placement and scale, wool thread colors, raised hand-worked texture, '
         'proportions, and premium handmade identity; preserve exactly four same-color corner pompoms per pillow only '
         'when the source has pompoms, and never add pompoms or a personalized name when absent from the source'
     ),
     'shots': (
         ('Two-pillow colorways',
          'Two coordinated Christmas pillows on soft white rug',
          _christmas_pillowcase_brief(
              'place exactly two pillows of the same source design in two different coordinated base fabric colors on a '
              'soft white rug inside a bright airy beautifully decorated Christmas room. Keep the embroidery motif and '
              'thread colors identical. If the source has an embroidered name, use two different plausible names while '
              'preserving its exact placement, scale, lettering style, and stitch method; if no source name exists, add '
              'none. If the source has corner pompoms, preserve exactly four same-color pompoms on each pillow and use a '
              'different coordinated pompom color for each pillow; if the source has no pompoms, add none. Focus closely '
              'on both pillows in clean natural daylight.'
          )),
         ('Christmas crib',
          'Pillow centered inside bright white baby crib',
          _christmas_pillowcase_brief(
              'place the exact pillow centered inside a white baby crib decorated with soft Christmas garlands and cute '
              'Christmas plush toys. Use a bright spacious nursery, clear white-balanced natural daylight, and a close '
              'product-focused composition. Keep all decor secondary and preserve the exact source fabric, embroidery, '
              'name when present, seams, volume, edge details, and conditional pompom construction.'
          )),
         ('Craft flat lay',
          'Top-down pillow with matching wool and embroidery hoop',
          _christmas_pillowcase_brief(
              'create a clean top-down photograph of the completed exact pillow beside wool yarn spools matching the '
              'source embroidery colors, one wooden embroidery hoop, and restrained Christmas craft decorations. Use '
              'bright natural daylight in a tidy workspace and keep the pillow as the dominant sharp subject. Emphasize '
              'the fabric weave and raised hand-worked wool texture without covering the motif or source lettering.'
          )),
         ('Embroidery detail grid',
          'Four-panel macro grid of raised wool embroidery',
          _christmas_pillowcase_brief(
              'create one high-quality square 2x2 grid containing exactly four macro photographs of different areas of '
              'the same source embroidery on the pillow. Show the exact motif, thread colors, individual wool loops, '
              'stitch direction, fabric weave, seam or edge detail, and pompom attachment only if the source has pompoms. '
              'Every embroidered element must look manually hooked or punch-needled with wool yarn, never printed or '
              'machine embroidered. Use bright natural light and keep every panel focused on the product.'
          )),
         ('Christmas sofa',
          'Pillow on white sofa in refined Christmas room',
          _christmas_pillowcase_brief(
              'place the exact pillow prominently on a white sofa in a bright airy room with beautiful restrained '
              'Christmas ornaments, a festive hanging garland, and one soft wool blanket. Use a clean editorial '
              'composition and clear natural daylight. Focus directly on the pillow and preserve every source design, '
              'embroidery, fabric, name, seam, volume, and conditional pompom detail.'
          )),
         ('Baby hugging pillow',
          'Baby hugging pillow in airy Christmas corner',
          _christmas_pillowcase_brief(
              'show a baby safely seated in a bright spacious corner while naturally hugging the exact pillow. Place '
              'subtle star-shaped string lights and a beautifully decorated Christmas tree in the softly blurred '
              'background. Use clear fresh morning daylight and keep the pillow, embroidery, and handmade fabric texture '
              'as the primary sharp subject. Preserve realistic anatomy and all exact source details.'
          )),
         ('Under Christmas tree',
          'Front-facing pillow beneath tree with wrapped gifts',
          _christmas_pillowcase_brief(
              'place the exact pillow directly beneath a decorated Christmas tree among several neatly wrapped gifts. '
              'Photograph the pillow straight-on and directly from the front in a bright spacious composition with '
              'natural white-balanced light. Keep the complete pillow face, embroidery motif, source name when present, '
              'fabric texture, seams, shape, and conditional pompoms unobstructed and sharply prioritized.'
          )),
         ('Mother and baby lifestyle',
          'Mother on sofa holding pillow and baby',
          _christmas_pillowcase_brief(
              'show a mother seated naturally on a sofa while holding the exact pillow and cuddling her baby in a home '
              'filled with tasteful Christmas atmosphere. Use wide airy morning light, realistic anatomy, and a gentle '
              'lifestyle composition while keeping the pillow facing the camera as the sharp primary product. Hands and '
              'arms must not cover the embroidery, source lettering, edges, or conditional pompoms.'
          )),
         ('Baby hand detail',
          'Small baby hands reaching for pillow embroidery',
          _christmas_pillowcase_brief(
              'capture a realistic close lifestyle moment of small baby hands gently reaching toward the raised '
              'embroidery on the exact source pillow. Use a bright sunlit room with refined Christmas details softly '
              'blurred behind. Focus on the pillow face, wool loops, linen weave, and natural hand interaction. Hands '
              'must be anatomically correct and must not distort or hide the source motif.'
          )),
         ('Woman hugging pillow',
          'Smiling woman holding pillow in bright Christmas room',
          _christmas_pillowcase_brief(
              'show an adult woman smiling naturally while hugging the exact pillow in a bright airy room with colorful '
              'but refined Christmas decorations behind her. Use clear white-balanced natural daylight with absolutely '
              'no yellow cast. Keep the embroidered pillow face turned toward the camera and sharply dominant, with '
              'natural hands that do not cover the motif, name, seams, or conditional pompoms.'
          )),
         ('Punch-needle process',
          'Woman hand-working matching wool motif in round hoop',
          _christmas_pillowcase_brief(
              'create an Etsy-style handmade process photograph of a woman seated at a clean wooden craft table, '
              'carefully working the exact source motif on fabric matching the pillowcase color inside a round wooden '
              'embroidery hoop. Use a large sharp wooden-handled punch needle with wool yarn visibly threaded through '
              'the rear or tail of the tool, and make the yarn color match the precise area being stitched. Focus on '
              'anatomically natural hands, realistic tool contact, the hoop, matching wool, simple scissors, fabric '
              'texture, raised stitches, and the completed exact pillow front nearby. Use soft bright window light and '
              'never show flat machine embroidery.'
          )),
         ('Santa sofa display',
          'Front-facing pillow on sofa with Santa decorations',
          _christmas_pillowcase_brief(
              'place the exact pillow on a sofa with small decorative Santa figurines and refined Christmas ornaments in '
              'a bright airy room. Photograph the pillow straight-on and directly from the front with clean natural '
              'white-balanced light and no yellow cast. Keep all decorations secondary and preserve the complete pillow '
              'shape, exact embroidery, source name when present, fabric, seams, volume, and conditional pompoms.'
          )),
     ),
 },
 'halloween_pillow': {'display_name': 'Halloween Pillow',
                      'aliases': ('Halloween Pillow',
                                  'halloween pillow',
                                  'halloween baby pillow',
                                  'halloween pillowcase',
                                  'halloween cushion',
                                  'halloween baby cushion',
                                  'embroidered halloween pillow',
                                  'wool embroidered halloween pillow',
                                  'hooked wool halloween pillow',
                                  'halloween nursery pillow',
                                  'halloween crib pillow',
                                  'gingham halloween pillow',
                                  'checkered halloween pillow',
                                  'goi halloween',
                                  'goi em be halloween',
                                  'vo goi halloween',
                                  'goi tre em halloween'),
                      'target_count': 12,
                      'allow_planned_multi_panel_shots': True,
                      'lock': 'the main product must remain the exact same handmade Halloween baby pillow or pillowcase from the source image, with the same pillow shape, stuffed volume or pillowcase edges, fabric material, fabric color or gingham/checkered pattern, embroidery motif, embroidery placement, embroidery scale, wool/yarn embroidery thread colors, raised hooked wool-stitch texture, seams, proportions, handmade wrinkles, and premium nursery Halloween identity; never redesign the pillow, flatten or distort it, change the fabric, move or simplify the embroidery, cover the embroidered area, or turn it into a bag, blanket, toy, hoop, banner, shirt, costume, or generic Halloween prop',
                      'shots': (('Colorway rug hero',
                                 'Two Halloween pillows on white rug with pumpkins',
                                 _halloween_pillow_brief('show two baby pillows matching the source reference product, arranged on a soft white rug in a bright sun-filled room with small decorative pumpkins. The two pillows use two different product colors while keeping the exact same pillow shape, embroidery placement, embroidery scale, wool thread colors, seam finish, and handmade construction. If the reference pillow is gingham or checkered, the only allowed colorways are pink gingham and blue gingham. Use a realistic product-photo composition focused tightly on the pillows, with a clean Halloween theme and no clutter.')),
                                ('White crib nursery',
                                 'Pillow in white crib with Halloween garland',
                                 _halloween_pillow_brief('place the pillow inside a white baby crib in a bright airy nursery. Decorate the crib area with soft Halloween garlands and cute Halloween stuffed toys as secondary props. Keep the pillow front and embroidery clearly visible, sharply focused, and dominant in the frame. Use clean natural daylight, spacious styling, and a gentle nursery Halloween feeling.')),
                                ('Maker flat lay',
                                 'Top-down pillow with yarn and pumpkins',
                                 _halloween_pillow_brief('shoot from directly overhead. Place the completed pillow beside yarn rolls matching the embroidery colors on the source pillow, one wooden embroidery hoop, and exactly three small orange pumpkins. Use a bright clean workspace with natural daylight. Focus on the pillow and the raised wool embroidery texture; craft tools are secondary and must not cover the embroidery.')),
                                ('Embroidery detail collage',
                                 '2x2 wool embroidery close-up grid',
                                 _halloween_pillow_brief('create one square 1:1 2x2 grid collage made of four high-quality close-up detail photos of different angles of the embroidery on the same pillow. All embroidery must look hooked or stitched with wool embroidery thread, with raised yarn texture, stitch direction, motif edges, fabric weave, seams, and handmade quality visible. Natural bright light. The collage must focus on the pillow embroidery only and must match the source motif exactly.')),
                                ('White sofa Halloween room',
                                 'Pillow on white sofa with pumpkins and garland',
                                 _halloween_pillow_brief('place the pillow on a white sofa in a clean Halloween-themed room. Add minimal orange pumpkins, Halloween hanging garlands, and a soft knitted blanket around the sofa. Use bright airy daylight, tidy composition, shallow depth of field, and premium Etsy handmade styling. Keep the pillow and embroidery as the clear focal point.')),
                                ('Baby cozy corner',
                                 'Baby hugging pillow in cozy Halloween corner',
                                 _halloween_pillow_brief('create an everyday lifestyle photo of a baby sitting in a cozy corner and hugging the pillow. Behind the baby, add subtle Halloween decor such as star string lights and small stuffed bats. Use clear bright morning natural light and a gentle home feeling. Focus on the pillow, its fabric, embroidery, and scale; the baby supports the lifestyle story without covering the embroidery.')),
                                ('Teepee nursery',
                                 'Pillow inside Halloween baby teepee',
                                 _halloween_pillow_brief('place the pillow inside a baby teepee. Decorate the teepee with bright Halloween garlands, tasteful Halloween objects, and a few small softly shimmering lanterns, while keeping the room spacious and naturally lit. The pillow must sit clearly in the teepee opening with the front embroidery visible and sharp.')),
                                ('Mother and baby sofa',
                                 'Mother holding pillow and baby on Halloween sofa',
                                 _halloween_pillow_brief('show a warm lifestyle moment with a mother sitting on a sofa, holding the pillow while cuddling a baby. The home corner is decorated with Halloween decor, but remains spacious and full of morning light. Crop naturally so the pillow stays prominent and the embroidery is visible. Keep the scene bright, realistic, and focused on the pillow rather than faces.')),
                                ('Baby hand macro',
                                 'Baby hands reaching for pillow embroidery',
                                 _halloween_pillow_brief('create a close lifestyle macro moment of small baby hands reaching toward the embroidered motif on the pillow. Put the embroidery at the sharp focus point, showing raised wool stitches and fabric texture. In the softly blurred background, include a friendly stuffed ghost and subtle Halloween details. Use a bright sunny room and keep the pillow as the main subject.')),
                                ('Toddler hug lifestyle',
                                 'Three-year-old hugging pillow in bright Halloween room',
                                 _halloween_pillow_brief('show a peaceful realistic image of a three-year-old child hugging the pillow and smiling in a bright room with soft colorful Halloween decorations in the background. Use gentle clear daylight and a happy nursery-home mood. Keep the pillow front visible, correctly scaled for a child, and focused so the source embroidery remains clear.')),
                                ('Hand embroidery process',
                                 'Woman embroidering pillow motif with wool needle',
                                 _halloween_pillow_brief('create an Etsy-style handmade process photo using the pillow or pillowcase from the reference as the main product. A woman sits at a wooden craft table and carefully embroiders the same motif onto same-color fabric stretched on a round embroidery hoop, using a large sharp wool embroidery needle with a wooden handle. The yarn at the needle tip must match the exact needle contact point on the fabric. Focus on the woman hands, hoop or fabric area, embroidery tools, yarn, and the front of the pillow nearby. Include soft natural window light, thread, scissors, simple sewing tools, and a clean cozy handmade workspace. Hands must be anatomically natural, with realistic needle placement; the stitching must match the source embroidery position and colors.')),
                                ('Airy sofa product',
                                 'Pillow on sofa with airy Halloween decor',
                                 _halloween_pillow_brief('create a realistic product photo of the baby pillow on a sofa with Halloween pumpkins and tasteful decorations in a clear bright airy room. Do not use yellow light. Keep the pillow centered and dominant, with the exact fabric, embroidery, raised wool texture, seams, shape, scale, and handmade finish preserved. Focus tightly on the pillow.')))},
 'baby_pillowcase': {'display_name': 'Baby Pillowcase',
                     'aliases': ('Baby Pillowcase',
                                 'baby pillowcase',
                                 'baby pillow',
                                 'nursery pillow',
                                 'children pillow',
                                 'gối em bé',
                                 'goi em be',
                                 'vỏ gối bé',
                                 'vo goi be',
                                 'gối bé',
                                 'goi be'),
                     'lock': 'the main product must remain the same baby/nursery pillowcase or cushion with the exact '
                             'pillow shape, soft volume, fabric weave, embroidered name/motif placement, seam/edge '
                             'finish, color, and baby-safe nursery scale from the source image',
                     'shots': (('Lifestyle',
                                'Mẹ bế bé + gối thêu tên',
                                'Use the pillow in the reference image as the main product. Create a realistic product '
                                'photo depicting everyday life, showing a mother and baby comfortably seated in the '
                                'living room (faces obscured, only noses and lower bodies visible), touching the '
                                'embroidery of the handcrafted decorative pillow as in the reference image. The pillow '
                                'should be the focal point of the photo, highlighting the fabric, the raised '
                                'embroidery details, and the high-quality finish of the handcrafted product. Soft '
                                'natural light from a nearby window creates a bright, airy, and natural feel. Use a '
                                'shallow depth of field to highlight the pillow while maintaining the gentle '
                                'authenticity of the woman and the living room.\n'
                                '\n'
                                'IMPORTANT: Keep the shape, fabric, color palette, embroidery texture, proportions, '
                                'and handcrafted look of the pillow from the reference image. Do not redesign, redraw, '
                                'distort, or alter the pillow. Do not add specific embroidery patterns. The embroidery '
                                'pattern must maintain its overall quality and versatility for all occasions. '
                                'Application. Pillow design. Background only. Landscape and life surrounding the '
                                'person holding the pillow.\n'
                                '\n'
                                'STYLE: Authentic. Handmade product photo. Lifestyle photo. Photo edited in Etsy '
                                'style. Theme: Home. Beautiful interior space, soft natural light from the window, '
                                'living room with neutral tones, shallow depth of field, high-end handmade pillow, '
                                'raised embroidery, 1:1 square aspect ratio.\n'
                                '\n'
                                'AVOID: pillow design editing, oversized embroidery, embroidery of specific characters '
                                'or names, harsh studio lighting, cluttered background, plastic-looking fabric, flat '
                                'machine embroidery, distorted hands, added fingers, blurry pillow details, '
                                'mass-produced look, AI errors, text overlays, logos, watermarks.'),
                               ('Product display',
                                'Hero — gối trên giường nursery',
                                'Use the pillow in the reference image as the main product. Create an authentic '
                                'Etsy-style product photo showcasing the handcrafted decorative pillow neatly placed '
                                'on a cozy bed in a bright, neutral bedroom. The pillow should be the centerpiece, '
                                'complemented by soft white bedding, neutral linen pillows, a light-colored headboard, '
                                'a bedside lamp, small potted plants, and minimalist home decor. Soft natural light '
                                'from the side window creates a clean, warm, and airy feel. Use a shallow depth of '
                                'field with a slightly blurred background while keeping the pillow sharp and detailed. '
                                'Highlight the fabric texture, embroidery, stitching, edging, and handcrafted '
                                'finish. \n'
                                '\n'
                                'IMPORTANT: Maintain EXACTLY the shape, fabric texture, color palette, edging details, '
                                'stitching, embroidery texture, proportions, and handcrafted look of the pillow from '
                                'the reference image. Do not redesign, redraw, distort, or alter the pillow. Only '
                                'create a bedroom backdrop and decorative style around the pillow. \n'
                                '\n'
                                'STYLE: Authentic handcrafted product photography, Etsy lifestyle photos, cozy bedroom '
                                'with neutral tones, soft natural light from the window, high-end handcrafted pillow, '
                                'warm minimalist home decor, shallow depth of field, 1:1 square aspect ratio. \n'
                                '\n'
                                'AVOID: altering the pillow design, specific embroidery patterns, harsh studio '
                                'lighting, cluttered backgrounds, plastic-looking fabric, flat machine embroidery, '
                                'blurry pillow details, mass-produced appearance, AI errors, text overlays, logos, '
                                'watermarks.'),
                               ('Product display',
                                '2 gối cùng màu — khác tên',
                                'Use the two pillows in the reference photo as the main product (two pillows of the '
                                'same color but different names). Create an authentic Etsy-style product photo, '
                                'showcasing the two pillows neatly arranged on a light-colored sofa in a bright living '
                                'room. Decorate the scene with minimalist cream-colored furniture, soft window '
                                'curtains, a vase of fresh flowers, and light, romantic decorative items. Use a '
                                'shallow depth of field with a slightly blurred background while keeping the pillows '
                                'sharp and detailed. \n'
                                '\n'
                                'IMPORTANT: Maintain the exact shape, material, color palette, embroidery placement, '
                                'proportions, and handcrafted look of the pillows as in the reference photo. Do not '
                                'redesign, repaint, distort, or alter the pillows. Only create the background and '
                                'decorate the living room around the pillows. \n'
                                '\n'
                                'STYLE: Authentic handcrafted product photography, Etsy lifestyle photography, cozy '
                                'and romantic home decor, soft natural light from the window, pastel color palette. '
                                'High-end personalized pillow, shallow depth of field, 1:1 square aspect ratio. \n'
                                '\n'
                                'AVOID: altering the pillow shape, inaccurate embroidered name or text, overly harsh '
                                'studio lighting, cluttered layout, plastic-like material, flat machine embroidery, '
                                'blurry pillow details, distorted heart shape, mass-produced appearance, AI errors, '
                                'text overlays, logos, watermarks.'),
                               ('Product display',
                                '4 gối stack dọc',
                                'Use the four pillows in the reference photo as the main product. Create an authentic '
                                'Etsy-style product photo, showcasing three neatly arranged handmade pillows on a '
                                'light-colored wooden bench, with one standing upright to highlight the embroidery. '
                                'Use a clean cream or white background with minimalist decor to accentuate the colors '
                                'and textures. \n'
                                '\n'
                                'IMPORTANT: Maintain the pillow shape, color palette, embroidery placement, '
                                'proportions, and handcrafted look as in the reference photo. Do not redesign, redraw, '
                                'distort, or alter the pillows. Only improve the background, lighting, and product '
                                'style. \n'
                                '\n'
                                'STYLE: Authentic handcrafted product photography, Etsy editorial style product photo, '
                                'soft natural light from a window, cozy cottage style, minimalist background, '
                                'high-quality handmade pillows, 1:1 square aspect ratio. \n'
                                '\n'
                                'AVOID: changing colors. Altering pillows, embroidery designs, or specific embroidery '
                                'patterns. Example: Harsh studio lighting, cluttered background, flat machine '
                                'embroidery, blurry fabric details, distorted folded edges, mass-produced appearance, '
                                'AI errors, text overlays, logos, watermarks.'),
                               ('Product display',
                                '3 gối 3 màu',
                                'Using three pillows as shown in the reference image as the main product, three '
                                'pillows in three different colors (but with the same embroidery style, the same '
                                'embroidery thread color, and different pillowcase colors and different personalized '
                                'names), arrange them neatly on a white crib or baby bed, one in the crib, one on the '
                                'bed. Decorate the scene with pristine white bedding, soft cloud-shaped pillows in the '
                                'background, and a bright, minimalist nursery space. Keep the layout clean, focusing '
                                'on the product. \n'
                                '\n'
                                'IMPORTANT: Maintain the pillow shape, fabric material, color palette, embroidery '
                                'placement, proportions, and handcrafted look from the reference image. Do not '
                                'redesign, repaint, distort, or alter the pillows. Only improve the nursery '
                                'background, lighting, and product style. \n'
                                '\n'
                                'STYLE: Authentic handcrafted product photos, Etsy editorial style product photos, '
                                'soft natural light from the window, bright white nursery room, room aesthetics. Cozy '
                                'newborn, premium personalized pillow, backdrop. Minimalist, clean, balanced. 1:1 '
                                'square ratio. \n'
                                '\n'
                                'AVOID: changing pillow color, changing pillow shape, embroidering specific names, '
                                'harsh studio lighting, cluttered backdrop, blurred or distorted fabric details, flat '
                                'machine embroidery, mass production patterns, AI errors, text overlays, logos, '
                                'watermarks.'),
                               ('Cận thêu tay',
                                'Cận thêu — collage',
                                'Use the pillow in the reference image as the main product. Create a detailed collage '
                                'in the Etsy style, showcasing the handcrafted pillow up close. Arrange the images '
                                'into four neat frames with minimal white borders, similar to a high-end product '
                                'detail sheet. Each small image shows a close-up of the raised embroidery on the '
                                'pillow from different angles. \n'
                                '\n'
                                'IMPORTANT: Maintain the EXACT pillow shape, fabric material, color palette, '
                                'embroidery placement, border or ruffle details, stitching, proportions, and '
                                'handcrafted look from the reference image. Do not redesign, redraw, distort, or alter '
                                'the pillow. Only improve the close-up composition, lighting, and product photography '
                                'style. \n'
                                '\n'
                                'STYLE: Authentic handcrafted product photos, detailed collage in the Etsy editorial '
                                'style, soft natural light from a window, neutral linen background, close-up of fabric '
                                'texture, raised embroidery, high-end handcrafted pillow, 1:1 square aspect ratio. \n'
                                '\n'
                                'AVOID: changing the pillow design, altering colors, harsh lighting, distracting '
                                'backgrounds, blurry stitching, fabric that looks like plastic, flat machine '
                                'embroidery, distorted pillow shape, AI errors, text overlaying images, logos, and '
                                'watermarks.'),
                               ('Product display',
                                'Bé nằm trên gối',
                                'Use the pillow in the reference photo as the main product. Create an authentic '
                                'Etsy-style product photo showing a baby comfortably lying on a soft bed or sofa, '
                                'gently hugging the pillow and sleeping, with the pillow as the focal point of the '
                                'photo. Use a shallow depth of field so the baby and pillow are in focus while the '
                                'background texture is slightly blurred. Highlight the fabric, soft stuffing, '
                                'embroidery, stitching, and the handcrafted look of the pillow. \n'
                                '\n'
                                'IMPORTANT: Keep the shape, fabric texture, color palette, embroidery placement, '
                                'proportions, and handcrafted look of the pillow from the reference photo. Do not '
                                'redesign, redraw, distort, or alter the pillow. Only create the context and style of '
                                'the photo showing the baby hugging the pillow. \n'
                                '\n'
                                'STYLE: Authentic handcrafted product photography, Etsy lifestyle, soft natural light '
                                "from a window, baby's room or living room, warm neutral tones, high-quality "
                                'handcrafted pillow, shallow depth of field. Shallow, 1:1 square aspect ratio. \n'
                                '\n'
                                'AVOID: pillow design editing, special embroidery, harsh studio lighting, cluttered '
                                'background, distorted baby body images, added fingers, blurry pillow details, '
                                'plastic-looking fabric, mass-produced appearance, AI errors, text overlays, logos, '
                                'watermarks.'),
                               ('Product display',
                                '3 gối tổng hợp',
                                'Use the pillowcases from the reference image as the main product. Create an authentic '
                                'Etsy-style product photo showcasing three handmade pillowcases in three different '
                                'colors (three different pillowcase colors, different names, but the same thread color '
                                'and embroidery style), neatly arranged on a clean sofa. Arrange them side-by-side so '
                                'that all three pillowcases are clearly visible (these are pillowcases, not pillows, '
                                "so they shouldn't be too puffy). \n"
                                '\n'
                                'Keep the scene bright, clean, and minimalist. Use soft natural light from the side or '
                                'a nearby window. The background should be simple and beautifully decorated. \n'
                                '\n'
                                'IMPORTANT: Maintain the EXACT shape, fabric, color palette, embroidery placement, '
                                'proportions, and handmade look of the pillowcases from the reference image. Do not '
                                'redesign, redraw, distort, or alter the product. Simply create a white table layout, '
                                'lighting, and display the product around it. \n'
                                '\n'
                                'STYLE: Product Photo Authentic handcrafted. Product photos in Etsy editorial style, '
                                'soft natural light from the window. Notebook, dark layout. Simple white table, '
                                'high-quality handmade pillowcase, 1:1 square aspect ratio. \n'
                                '\n'
                                'AVOID: heavily edited pillowcase designs, overly harsh studio lighting, cluttered '
                                'backgrounds, blurry or distorted fabric details, flat machine embroidery, '
                                'mass-produced images, AI errors, overlapping text, logos, watermarks.'),
                               ('Quy trình',
                                'Quy trình thêu',
                                'Use the pillowcase from the reference image as the main product. Create an Etsy-style '
                                'photo of the crafting process, showing a woman sitting at a table, carefully '
                                'embroidering a pattern onto fabric the same color as the pillowcase using a wool '
                                'embroidery needle (an embroidery needle with a wooden handle, a large, sharp needle '
                                "with the yarn at the tip matching the needle's position) ON A CIRCULAR EMBROIDERY "
                                "FRAME. Focus on the woman's hands, the embroidery frame or fabric area, the "
                                'embroidery tools, the yarn, and the front of the pillowcase, keeping the product the '
                                'main subject. Set the scene in a comfortable, handcrafted workspace with a wooden '
                                'table, soft natural light from a window, and a backdrop of embroidery threads, '
                                'scissors, and a few simple sewing tools nearby. Keep the scene clean and bright. '
                                'Highlight the fabric texture, stitching, embroidery texture, and the quality of the '
                                "pillowcase's craftsmanship, accurately marking the embroidery placement as in the "
                                'reference image, ensuring the correct colors are used. \n'
                                '\n'
                                'IMPORTANT: Maintain the image EXACTLY. Shape, fabric, color palette, embroidery '
                                'placement, proportions, and... Illustrative image. The illustrative image of the '
                                'handmade pillowcase is taken from a reference photo. Do not redesign, redraw, '
                                'distort, or alter the pillowcase. The background and style should focus solely on the '
                                'woman embroidering. \n'
                                '\n'
                                'STYLE: Authentic handmade product photography. Editing process in Etsy style, soft '
                                'natural light from a window. Window, cozy room space with handicrafts, minimalist '
                                'style, high-end handmade pillowcase, shallow depth of field, 1:1 square aspect '
                                'ratio. \n'
                                '\n'
                                'AVOID: altering the pillowcase design, harsh studio lighting, cluttered background, '
                                'blurry embroidery details, distorted hands, added fingers, unrealistic needle '
                                'placement, flat machine embroidery, mass-produced appearance. Mass production, AI '
                                'errors, text overlays, logos, watermarks.'),
                               ('Product display',
                                'Standalone đơn',
                                'Use the pillow in the reference image as the main product. Create an authentic '
                                'Etsy-style product photo showcasing a handcrafted decorative pillow neatly placed on '
                                'a cozy armchair in a bright living room. Decorate the scene with a neutral-colored '
                                'upholstered chair, soft window lighting, a small wooden table, books, a ceramic mug, '
                                'a potted plant, and minimalist home decor.\n'
                                '\n'
                                'IMPORTANT: Maintain EXACTLY the pillow shape, fabric texture, color palette, '
                                'embroidery placement, proportions, stitching, and handcrafted look from the reference '
                                'image. Do not redesign, redraw, distort, or alter the pillow. Only create the living '
                                'room setting, lighting, and decorations around the pillow.\n'
                                '\n'
                                'STYLE: Authentic handcrafted product photography, Etsy-style lifestyle photos, cozy '
                                'living room with neutral tones, soft natural light from the window, high-quality '
                                'handcrafted pillows, warm minimalist home decor, shallow depth of field, 1:1 square '
                                'aspect ratio.\n'
                                '\n'
                                'AVOID: pillow design alterations, harsh studio lighting, cluttered backgrounds, '
                                'blurry embroidery, distorted pillow shapes, flat machine embroidery, plastic-looking '
                                'fabric, mass-produced appearance, AI errors, text overlays, logos, watermarks.'),
                               ('Product display',
                                '2 trẻ nằm — 2 tên khác',
                                'Use the two pillows in the reference photo as the main product. Create an authentic '
                                'Etsy-style product photo showing two 3-year-old children comfortably seated on a soft '
                                'bed or sofa, each gently hugging a pillow (two pillows of different colors and names '
                                'but with the same embroidery pattern and thread color). The two pillows should be the '
                                'focal point of the photo. Use a shallow depth of field so the children and pillows '
                                'are in focus while the background has a slightly blurred texture. Highlight the '
                                'fabric, soft stuffing, embroidery, stitching, and handcrafted look of the pillows.\n'
                                '\n'
                                'IMPORTANT: Maintain the shape, fabric texture, color palette, embroidery placement, '
                                'proportions, and handcrafted look of the pillows from the reference photo. Do not '
                                'redesign, redraw, distort, or alter the pillows. Only create the context and style '
                                'for the photo showing the children hugging the pillows.\n'
                                '\n'
                                'STYLE: Handcrafted product photography. Authentic, inspired by the style. Living. '
                                "Etsy style, light. Soft natural light from the window, children's room. Bedroom. Or a "
                                'cozy living room, warm neutral tones. High-quality handmade pillows. Shallow depth of '
                                'field, 1:1 square aspect ratio.\n'
                                '\n'
                                'AVOID: pillow design editing, special embroidery, harsh studio lighting, cluttered '
                                'background, distorted baby body images, added fingers, blurry pillow details, '
                                'plastic-looking fabric, mass-produced appearance, AI errors, text overlays, logos, '
                                'watermarks.'),
                               ('Gift box',
                                'Gift box — quà sinh nhật',
                                'A beautifully wrapped pillowcase is placed in an open paper gift box, highlighting '
                                "the delicate hand-embroidered design. The pillowcase is neatly folded (because it's a "
                                'pillowcase, it will be flat, not puffy like a regular pillow), the embroidery stands '
                                'out, and the material is soft and elegant. The background is minimalist and bright '
                                'with natural light. Focus on the pillowcase; DO NOT ADD ANYTHING ELSE TO THE '
                                'PILLOWCASE IN THE GIFT BOX TO SHOW THE EMBROIDERY CLEARLY. \n'
                                '\n'
                                'IMPORTANT: Do not alter the design of the pillowcase or the embroidery. Focus on how '
                                'the pillowcase is presented in the gift box. Keep the embroidery clearly visible. '
                                'Highlight the material and the neat folding of the pillowcase. Natural light, a '
                                'bright and clean layout. \n'
                                '\n'
                                'STYLE: Present the gift elegantly, with a minimalist aesthetic, soft natural light, a '
                                'subtle sheen to highlight the material, and the background. Neutral colors are used '
                                'to highlight the gift box and embroidery. Close-up and medium shots show the details '
                                'of the wrapping paper and embroidery. \n'
                                '\n'
                                'AVOID: Showing the pillowcase. Avoid cluttered backgrounds, harsh shadows, or '
                                'artificial props that distract attention from the gift presentation. Do not distort '
                                'the embroidery or the shape of the pillowcase.'))},
 'halloween_banner': {
     'display_name': 'Halloween Banner',
     'aliases': (
         'Halloween Banner',
         'halloween banner',
         'Halloween Fabric Banner',
         'halloween fabric banner',
         'Halloween Babric Banner',
         'halloween babric banner',
         'Halloween Linen Banner',
         'halloween linen banner',
         'Halloween Embroidered Banner',
         'halloween embroidered banner',
         'Halloween Wall Banner',
         'halloween wall banner',
         'Halloween Wall Hanging',
         'halloween wall hanging',
         'Halloween Pennant',
         'halloween pennant',
         'banner halloween',
         'fabric banner halloween',
         'linen banner halloween',
     ),
     'target_count': 14,
     'allow_planned_multi_panel_shots': True,
     'allow_planned_infographic_text': True,
     'lock': (
         'the main product must remain the exact same small handmade Halloween linen fabric wall banner from the source '
         'image, with the same banner silhouette, lower edge shape, wooden rod, hanging cord, fabric material and color, '
         'seams, embroidery motif and readable source lettering, embroidery placement and scale, thread colors, raised '
         'hand-stitch texture, linen weave, natural wrinkles, proportions, and premium handmade identity; never redesign '
         'the embroidery, change its physical construction, enlarge it unnaturally, or turn it into another product'
     ),
     'shots': (
         ('Door hook lifestyle',
          'Small banner hanging from child-room door hook',
          _halloween_banner_brief(
              'hang the exact banner naturally from a clearly visible hook on a child-room door. Frame the complete '
              'product and part of the door from a 20-30 degree angle. Use soft clean white daylight with no yellow cast. '
              'Place one mini pumpkin on the floor and a few tiny ceramic stars or friendly ghosts softly in the '
              'background. Keep the banner realistically small and preserve the complete rod, cord, shape, source '
              'embroidery, readable source lettering, and handmade linen texture.'
          )),
         ('Nursery crib wall',
          'Small banner centered above decorated crib',
          _halloween_banner_brief(
              'hang the exact banner at the center of the wall above a baby crib, photographed straight-on or from a '
              '30-degree front angle with a close product-focused framing. Use even bright natural white light across '
              'both the banner and crib bedding. Add a restrained Halloween garland, a small friendly ghost cushion, and '
              'mini pumpkins. The banner must look very small relative to the crib and must never be enlarged.'
          )),
         ('Entryway lifestyle',
          'Small banner above entry console or wooden bench',
          _halloween_banner_brief(
              'hang the exact small banner in a home entryway above a compact console table or wooden bench. Shoot from '
              'a 45-60 degree angle, close enough to prioritize the product while still showing realistic use. Use clean '
              'natural white light without yellow cast. Style with white pumpkins, one vase of dark berry branches, and '
              'a white candle in a clear glass jar. Preserve the banner small scale and exact source design.'
          )),
         ('White wood flat lay',
          'Top-down banner with rod cord and autumn accents',
          _halloween_banner_brief(
              'lay the exact banner flat on a white wood surface with its hanging cord and wooden rod arranged neatly '
              'above it and completely visible. Shoot top-down at 90 degrees. Let gentle sunlight create a soft clean '
              'shadow across the product without obscuring the embroidery. Place a small orange pumpkin, a white pumpkin, '
              'a few tiny bat decorations, and several autumn leaves only near the lower corners.'
          )),
         ('Colorway flat lay',
          'Three or four personalized banner colorways',
          _halloween_banner_brief(
              'create a 90-degree flat lay of three or four banners of the exact same source style arranged in a clean row '
              'or fan. If personalized names are visibly part of the source design, use different plausible names while '
              'preserving the exact lettering position, scale, stitch style, motif, thread colors, rod, cord, seams, and '
              'shape. Only the linen base color may differ. Use even white daylight and add only a few tiny pumpkins and '
              'small toy spiders so the products remain dominant.'
          )),
         ('Detail collage',
          'Four-panel embroidery rod and hanging-cord details',
          _halloween_banner_brief(
              'create one square 2x2 collage containing exactly four macro photographs of the same source banner: a close '
              'detail of the raised hand embroidery, a second close detail of another embroidered section or readable '
              'source lettering, a close detail of the wooden hanging rod and top seam, and a close detail of the hanging '
              'cord attachment. Match the source exactly. Clearly show genuine hand-stitched thread relief and linen '
              'fibers, never printing or machine-flat embroidery.'
          )),
         ('Reading corner wall',
          'Small banner beside wall bookshelf and Halloween garland',
          _halloween_banner_brief(
              'hang the exact small banner on a wall beside a compact wall bookshelf and a small framed picture. Add a '
              'Halloween garland to the wall, one small plush ghost, mini pumpkins, and bright-covered children books. '
              'Shoot straight-on or at 30-45 degrees with soft sunlight and no dark room corners. Keep the banner small, '
              'sharp, fully visible, and clearly hand embroidered rather than printed or machine stitched.'
          )),
         ('Bright shelf mantle',
          'Banner above light wood shelf with minimal decor',
          _halloween_banner_brief(
              'hang the exact banner above a light wooden shelf or mini mantle while keeping it at the center of the '
              'composition. Shoot straight-on or at a slight 15-degree angle in bright white light that also illuminates '
              'the decor below. Add two or three small white and orange pumpkins, one ceramic ghost, and one light-covered '
              'book. Preserve crisp raised hand stitches and the exact source design.'
          )),
         ('Hand-held display',
          'Two hands holding banner by its hanging cord',
          _halloween_banner_brief(
              'show two anatomically natural adult hands holding the hanging cord so the exact banner floats naturally '
              'in a Halloween-decorated room. Use a straight-on close-medium composition and soft white light with the '
              'banner sharply prominent. Keep the background simple with only a few blurred pumpkins near the floor. '
              'Hands must not cover the rod, banner shape, embroidery, or source lettering.'
          )),
         ('Personalized gift presentation',
          'Banner beside open gift box and Happy Halloween tag',
          _halloween_banner_brief(
              'place the exact banner beside an open premium gift box or gift bag to emphasize a personalized handmade '
              'gift. Shoot from a 45-degree overhead angle with clean luxurious high-key white light. Add a thin black '
              'ribbon, one small pumpkin, and one tasteful gift tag carrying only the exact words "Happy Halloween". '
              'Do not add any other readable text, and keep the complete banner, rod, cord, and embroidery unobstructed.'
          )),
         ('Hand embroidery process',
          'Woman hand-embroidering matching linen in round hoop',
          _halloween_banner_brief(
              'show an adult woman seated at a clean handmade table, one hand supporting a round wooden embroidery hoop '
              'and the other carefully stitching the exact source motif onto linen matching the banner fabric color. The '
              'needle must be realistically threaded and contact the correct stitch position. Add small scissors, thread '
              'spools, folded linen, soft window light, and restrained Halloween decor. Hands must be anatomically '
              'correct and the stitches must look unmistakably handmade, not printed or machine embroidered.'
          )),
         ('Second mantle display',
          'Centered banner above bright mini mantle',
          _halloween_banner_brief(
              'create a second bright product-focused mantle composition with the exact banner centered above a light '
              'wood shelf or mini mantle. Shoot frontally or at a subtle 15-degree angle in clear white-balanced daylight. '
              'Arrange two or three small white and orange pumpkins, one ceramic ghost, and one bright-covered book below '
              'without making the lower decor dark or distracting. Keep the embroidery sharp and visibly hand stitched.'
          )),
         ('Baby lifestyle',
          'Baby seated on floor holding small banner',
          _halloween_banner_brief(
              'show a baby seated safely on the floor in a bright Halloween-decorated room, naturally holding the exact '
              'small banner with its embroidered front facing the camera. Shoot straight-on in a close-medium composition '
              'with soft white light. The banner must remain small relative to the baby, must not cover the child, and '
              'must preserve its exact rod, cord, shape, source embroidery, thread colors, and hand-stitched texture.'
          )),
         ('Wardrobe door display',
          'Small banner hanging naturally on wardrobe or room door',
          _halloween_banner_brief(
              'hang the exact banner naturally from a wardrobe door or room door, with the complete cord, wooden rod, and '
              'fabric body visible and hanging freely. Shoot from a gentle frontal angle in even clean white daylight. '
              'Add eye-catching but refined Halloween decor around the doorway without covering the product. Keep the '
              'banner realistically small relative to the door or wardrobe and clearly hand embroidered.'
          )),
     ),
 },
 'banner': {'display_name': 'Banner',
            'aliases': ('Banner',
                        'baby banner',
                        'embroidered banner',
                        'wall banner',
                        'wall hanging banner',
                        'nursery banner',
                        'pennant',
                        'pennant banner',
                        'nursery pennant',
                        'embroidered pennant',
                        'baby wall hanging',
                        'wall hanging',
                        'hanging flag',
                        'fabric flag',
                        'linen flag',
                        'cờ vải',
                        'co vai',
                        'cờ treo',
                        'co treo',
                        'lá cờ',
                        'la co',
                        'cờ thêu',
                        'co theu',
                        'cờ trang trí',
                        'co trang tri'),
            'lock': 'the main product must remain the same embroidered baby wall hanging banner/pennant with the exact '
                    'pointed V pennant shape, flat linen fabric panel, top wooden dowel/rod, rope cord hanger, side '
                    'seams, embroidery/name/motif placement, thread color palette, proportions, wall decor scale, and '
                    'premium handmade identity from the source image',
            'shots': (('Lifestyle',
                       'Mẹ và bé chạm vào cờ thêu tên',
                       'Use the embroidered baby wall hanging banner in the reference image as the main product. '
                       'Create a realistic lifestyle product photo showing a mother and baby together in a bright '
                       'nursery, gently touching the embroidered details on the banner. The mother may lightly hold '
                       'the banner or the banner may be hanging low enough for the baby to touch the embroidery. The '
                       'room should feel bright, white, airy, clean, and warm, with soft nursery decor in the '
                       'background.\n'
                       '\n'
                       'IMPORTANT: Maintain the EXACT shape, proportions, linen texture, pointed pennant form, wooden '
                       'rod, rope hanger, embroidery placement, and overall handcrafted look of the banner from the '
                       'reference image. Do not redesign, redraw, distort, or alter the banner itself. Only create a '
                       'new surrounding background and lifestyle scene.\n'
                       '\n'
                       'STYLE: Handmade lifestyle product photography, soft white natural lighting, editorial quality, '
                       'bright airy nursery aesthetic, modern minimalist Etsy style, 1:1 square aspect ratio.\n'
                       '\n'
                       'AVOID: altering the banner design, blurry embroidery, harsh studio lighting, cluttered '
                       'backgrounds, distorted hands, extra fingers, mass-produced look, AI errors, text overlays, '
                       'logos, watermarks.'),
                      ('Product display',
                       'Hero cờ treo trong nursery',
                       'Use the embroidered wall banner for babies shown in the reference image as the main product. '
                       'Create a striking product photo in authentic Etsy style, showcasing a single banner neatly '
                       'hung in a SPACIOUS nursery, positioned above the crib or baby bed. Add soft nursery '
                       'decorations such as teddy bears, folded baby blankets, and light, neutral-colored furniture. '
                       'The room should feel bright, airy, white, and elegant, with the banner as the main focal '
                       'point.\n'
                       '\n'
                       'IMPORTANT: Keep the shape, proportions, linen fabric, pointed flag shape, wooden rod, hanging '
                       'hooks, embroidery placement, and handcrafted look of the banner exactly as in the reference '
                       'image. Do not edit or alter the banner. Only create a new background and style around it.\n'
                       '\n'
                       'STYLE: Handcrafted product photography, soft white natural light, high-quality editing, '
                       'minimalist modern Etsy-style aesthetics, high-end nursery decor style, 1:1 square aspect '
                       'ratio.\n'
                       '\n'
                       'AVOID: Banner design changes, harsh studio lighting, cluttered props, distorted embroidery, '
                       'mass-produced look, AI errors, blurry images, overlays, logos, watermarks.'),
                      ('Product display',
                       '2 cờ cùng kiểu, khác tên, khác màu nền',
                       'Use two embroidered baby wall hanging banners based on the reference image as the main '
                       'products. Create an authentic Etsy-style product photo showing two banners hanging together in '
                       'a bright baby room. Add flavorful wall decor such as small framed photos or simple nursery '
                       'wall art behind them. The two banners must have the exact same shape and embroidery layout as '
                       'the reference image, but with different names and different fabric base colors. The embroidery '
                       'thread colors and style must remain the same as the reference image.\n'
                       '\n'
                       'IMPORTANT: Maintain the EXACT shape, proportions, pointed pennant form, linen texture, wooden '
                       'rod, rope hanger, embroidery placement, and handcrafted look of the banners. Only change the '
                       'names and the fabric base colors. Do not redesign or distort the banners.\n'
                       '\n'
                       'STYLE: Handmade product photography, soft white natural lighting, editorial quality, airy '
                       'nursery wall styling, modern Etsy aesthetic, 1:1 square aspect ratio.\n'
                       '\n'
                       'AVOID: altering the banner design, changing embroidery layout, harsh lighting, cluttered '
                       'walls, distorted banner shapes, blurry embroidery, mass-produced look, AI errors, overlays, '
                       'logos, watermarks.'),
                      ('Product display',
                       '2 cờ đặt trên bàn với đồ em bé',
                       'Use two embroidered baby wall hanging banners based on the reference image as the main '
                       'products. Create a product display photo showing two banners neatly placed on a table in a '
                       'bright airy room. Decorate the table with tasteful baby-related items such as a baby toy, soft '
                       'shoes, a folded baby blanket, or small nursery accessories. The two banners must keep the same '
                       'exact design structure as the reference image, but have different names and different fabric '
                       'base colors. The embroidery thread style and colors must remain the same as the reference '
                       'image.\n'
                       '\n'
                       'IMPORTANT: Maintain the EXACT shape, proportions, pointed pennant form, linen texture, wooden '
                       'rod, rope hanger, embroidery placement, and handcrafted appearance of the banners. Only change '
                       'the names and base fabric colors. Do not redesign or alter the banners themselves.\n'
                       '\n'
                       'STYLE: Handmade product photography, soft white natural lighting, editorial quality, bright '
                       'clean tabletop styling, modern minimalist Etsy aesthetic, 1:1 square aspect ratio.\n'
                       '\n'
                       'AVOID: altering banner design, cluttered props, harsh lighting, distorted product proportions, '
                       'blurry embroidery, mass-produced look, AI errors, overlays, logos, watermarks.'),
                      ('Product display',
                       '3 cờ, 3 màu nền',
                       'Use three embroidered baby wall hanging banners based on the reference image as the main '
                       'products. Create an authentic Etsy-style product photo showing three banners hanging together '
                       'in a bright baby nursery. The three banners should share the same exact style, shape, '
                       'embroidery layout, and handcrafted appearance as the reference image, but each banner should '
                       'have a different name and a different fabric base color. The embroidery style and colors must '
                       'remain the same as the reference image.\n'
                       '\n'
                       'IMPORTANT: Maintain the EXACT shape, proportions, pointed pennant form, linen texture, wooden '
                       'rod, rope hanger, embroidery placement, and handcrafted look of all three banners. Only change '
                       'the names and the fabric base colors. Do not redesign the product.\n'
                       '\n'
                       'STYLE: Handmade product photography, soft white natural lighting, editorial quality, airy '
                       'nursery interior, modern minimalist Etsy style, 1:1 square aspect ratio.\n'
                       '\n'
                       'AVOID: altering the banner design, harsh lighting, cluttered nursery background, distorted '
                       'product shapes, blurry embroidery, mass-produced appearance, AI errors, text overlays, logos, '
                       'watermarks.'),
                      ('Product display',
                       '4 cờ treo cùng nhau',
                       'Use four embroidered baby wall hanging banners based on the reference image as the main '
                       'products. Create an authentic Etsy-style product photo showing four banners hanging together '
                       'in a bright and airy baby room. All four banners must keep the same exact design structure, '
                       'shape, embroidery layout, and handcrafted look as the reference image, but each banner should '
                       'have a different name and a different fabric base color. The embroidery thread style and '
                       'colors must remain unchanged from the reference image.\n'
                       '\n'
                       'IMPORTANT: Maintain the EXACT shape, proportions, pointed pennant form, linen texture, wooden '
                       'rod, rope hanger, embroidery placement, and handcrafted appearance of the banners. Only vary '
                       'the names and base fabric colors. Do not redesign or distort the products.\n'
                       '\n'
                       'STYLE: Handmade product photography, soft white natural lighting, editorial quality, bright '
                       'airy nursery decor, modern Etsy aesthetic, 1:1 square aspect ratio.\n'
                       '\n'
                       'AVOID: altering the banner design, inconsistent embroidery style, harsh studio lighting, '
                       'cluttered background, blurry details, mass-produced look, AI errors, overlays, logos, '
                       'watermarks.'),
                      ('Cận thêu tay',
                       'Collage 4 ảnh nhỏ',
                       'Use the embroidered baby wall hanging banner in the reference image as the main product. '
                       'Create a realistic close-up collage made of four smaller images arranged neatly in one final '
                       'square image. Each panel should show a different close-up angle of the banner, focusing on the '
                       'embroidery texture, linen fabric texture, stitched edges, and handcrafted details. The four '
                       'close-up shots should be bright, sharp, elegant, and premium, like a high-end Etsy detail '
                       'collage.\n'
                       '\n'
                       'IMPORTANT: Maintain the EXACT embroidery texture, linen fabric texture, stitching, banner '
                       'shape, proportions, and handcrafted appearance of the banner from the reference image. Do not '
                       'redesign or alter the product. Only create a refined close-up collage presentation.\n'
                       '\n'
                       'STYLE: Handmade detail photography, close-up editorial collage, soft white natural lighting, '
                       'clean refined Etsy aesthetic, bright and airy presentation, 1:1 square aspect ratio.\n'
                       '\n'
                       'AVOID: blurry close-ups, harsh lighting, cluttered composition, distorted stitches, AI errors, '
                       'overlays, logos, watermarks.'),
                      ('Quy trình',
                       'Người phụ nữ đang thêu cờ',
                       'Use the embroidered baby wall hanging banner in the reference image as the main inspiration '
                       'for the crafting process. Create an Etsy-style process photo showing a woman sitting at a '
                       'clean craft table, carefully embroidering the design onto fabric of the same color as the '
                       'banner. The fabric is stretched in a round embroidery hoop. The needle must be realistically '
                       'placed at the exact point of stitching, and the eye of the needle must clearly contain thread. '
                       'Focus on the embroidery hoop, fabric, needle, thread, and the woman’s careful handwork. The '
                       'overall scene should look clean, bright, airy, and premium handmade.\n'
                       '\n'
                       'IMPORTANT: The needle placement must be realistic and aligned with the current stitch. The '
                       'thread must pass naturally through the needle eye. The embroidery must look genuinely '
                       'handmade, not machine flat. Keep the embroidered design style consistent with the reference '
                       'image.\n'
                       '\n'
                       'STYLE: Hand embroidery process photography, soft white natural lighting, realistic editorial '
                       'Etsy aesthetic, clean craft workspace, premium handmade atmosphere, 1:1 square aspect ratio.\n'
                       '\n'
                       'AVOID: distorted hands, extra fingers, unrealistic needle placement, disconnected thread, flat '
                       'machine-embroidery look, cluttered workspace, harsh studio light, AI errors, overlays, logos, '
                       'watermarks.'),
                      ('Lifestyle',
                       'Mẹ và bé cùng sờ hình thêu',
                       'Use the embroidered baby wall hanging banner in the reference image as the main product. '
                       'Create a lifestyle product photo showing a mother and baby in a bright nursery, both gently '
                       'touching the embroidered details on the banner. The banner may be hanging on the wall or held '
                       'lightly by the mother. The room should feel soft, white, airy, warm, and elegant, with the '
                       'banner clearly visible and the embroidery details easy to see.\n'
                       '\n'
                       'IMPORTANT: Maintain the EXACT shape, proportions, pointed pennant form, linen texture, wooden '
                       'rod, rope hanger, embroidery placement, and handcrafted appearance of the banner from the '
                       'reference image. Do not redesign, distort, or alter the banner itself.\n'
                       '\n'
                       'STYLE: Handmade lifestyle product photography, soft white natural lighting, editorial quality, '
                       'bright airy nursery aesthetic, modern minimalist Etsy style, 1:1 square aspect ratio.\n'
                       '\n'
                       'AVOID: altering the banner design, blurred embroidery, harsh lighting, cluttered background, '
                       'distorted hands, extra fingers, mass-produced look, AI errors, text overlays, logos, '
                       'watermarks.'),
                      ('Product display',
                       '2 bé với 2 cờ, không lộ mặt',
                       'Use two embroidered wall banners for babies based on the reference image as the main product. '
                       'Create a realistic Etsy-style photo showing two babies interacting with the two banners, both '
                       "gently touching the embroidered details. The babies' faces should not be visible; the two "
                       'banners should have different names but maintain the same embroidery style, EMBROIDERY THREAD '
                       'COLOR, layout, and overall design structure as the reference image. The background should feel '
                       'natural, cute, clean, and child-friendly.\n'
                       '\n'
                       'IMPORTANT: Maintain EXACTLY the shape, proportions, flag shape, linen material, wooden frame, '
                       'hanging string, embroidery placement, and handcrafted appearance of the banners from the '
                       'reference image. Only change the names if necessary. Do not redesign or distort the product.\n'
                       '\n'
                       'STYLE: Photograph handcrafted products in a lifestyle style, with soft white natural light, a '
                       "spacious children's room setting, authentic Etsy aesthetics, and a 1:1 square aspect ratio.\n"
                       '\n'
                       'AVOID: Showing the entire face, altering banner design, cluttered styling, harsh lighting, '
                       'distorted hands, adding fingers, blurry embroidery, AI errors, overlays, logos, and '
                       'watermarks.'),
                      ('Product display',
                       'Em bé ngủ, cờ treo gần nôi',
                       'Use the embroidered wall banner for babies shown in the reference image as the main product. '
                       'Create a peaceful Etsy-style photo, showing a baby sleeping in a crib or bassinet, with the '
                       'banner clearly displayed nearby on the wall. The composition should highlight the banner while '
                       "keeping the entire room soft, bright, airy, and tranquil. The children's room should feel "
                       'clean, pristine white, and elegant, with soft lighting.\n'
                       '\n'
                       'IMPORTANT: Maintain EXACTLY the shape, proportions, flag point shape, linen fabric, wooden '
                       'frame, hanging hooks, embroidery placement, and handcrafted appearance of the banner as shown '
                       'in the reference image. Do not redesign or alter the banner itself.\n'
                       '\n'
                       'STYLE: Handcrafted product photography in a lifestyle style, soft white natural lighting, '
                       "peaceful children's room aesthetic, Etsy editorial style, clean and airy composition, 1:1 "
                       'square aspect ratio.\n'
                       '\n'
                       'AVOID: obscuring the banner, harsh lighting, cluttered room decor, blurry embroidery, altered '
                       'design, mass-produced appearance, AI errors, overlays, logos, watermarks.'),
                      ('Gift box -',
                       'Cờ trong hộp quà mở',
                       'Use the embroidered baby wall hanging banner in the reference image as the main product. '
                       'Create a realistic gift presentation photo showing one banner neatly folded inside an open '
                       'paper gift box. Because it is a fabric wall banner, it must look flat and neatly folded, not '
                       'puffed up like a pillow. The embroidery design should remain clearly visible, highlighting the '
                       'fine handcrafted details and elegant linen texture. The scene should be minimal, bright, '
                       'clean, and softly lit with natural white light.\n'
                       '\n'
                       'IMPORTANT: Maintain the EXACT shape, proportions, pointed pennant form, linen texture, '
                       'embroidery placement, wooden rod if visible, rope hanger if visible, and handcrafted '
                       'appearance of the banner from the reference image. Do not redesign, redraw, distort, or alter '
                       'the product itself.\n'
                       '\n'
                       'STYLE: Handmade gift product photography, soft white natural lighting, editorial quality, '
                       'bright minimalist Etsy aesthetic, premium gift presentation, 1:1 square aspect ratio.\n'
                       '\n'
                       'AVOID: making the banner look puffy like a pillow, cluttered gift box styling, harsh lighting, '
                       'distracting objects covering the embroidery, AI errors, overlays, logos, watermarks.'))},
 'hair_bow': {'display_name': 'Hair Bow',
              'aliases': ('Hair Bow',
                          'hair bow',
                          'bow hair clip',
                          'hair bow clip',
                          'hair clip bow',
                          'barrette bow',
                          'bow barrette',
                          'hair tie bow',
                          'bow hair tie',
                          'hair bow scrunchie',
                          'bow scrunchie',
                          'scrunchie bow',
                          'scrunchie',
                          'embroidered hair bow',
                          'embroidered bow',
                          'linen hair bow',
                          'cotton linen hair bow',
                          'hair accessory bow',
                          'ribbon hair bow',
                          'long tail hair bow',
                          'no kep toc',
                          'kep toc no',
                          'no buoc toc',
                          'no cot toc',
                          'no chun buoc toc',
                          'chun buoc toc no',
                          'chun cot toc no'),
              'lock': 'the main product must remain the same hand-embroidered cotton linen hair bow, bow hair clip, '
                      'bow hair tie, or scrunchie-bow hair accessory from the source image, with the exact bow-loop '
                      'silhouette, center knot or wrap, long ribbon tails and pointed ends if present, elastic scrunchie '
                      'ring or clip/barrette/hair-tie hardware if visible, fabric weave, base fabric color, embroidery '
                      'placement, motif scale, thread colors, raised stitch texture, seams, natural wrinkles, soft drape, '
                      'and premium handmade identity; never turn it into a scarf, headband, bow tie, ribbon strip, dress, '
                      'pouch, generic decoration, or different hair accessory type',
              'shots': (('Flat lay product display',
                         'Bow in wooden tray with linen props',
                         'Place one hand-embroidered cotton linen hair bow naturally in a rectangular light wooden tray. '
                         'Let the bow loops, center knot, elastic scrunchie ring or clip/hair-tie construction, and long '
                         'ribbon tails rest softly without distortion. Add refined handmade props such as a wooden comb, '
                         'light linen cloth, dried flowers, and white art paper. The embroidery, fabric weave, seams, '
                         'tail points, and natural wrinkles must be crisp in clean white daylight.'),
                        ('Colorway pair',
                         'Two bows on bright vanity table',
                         'Show two hair bows with the same source construction and embroidery layout, each using a '
                         'different linen base color. Place them as a natural pair on a bright vanity table with a small '
                         'hand mirror, wooden comb, dried flowers, and pale linen ribbon as secondary decor. Preserve the '
                         'same bow-loop shape, center knot, tail length, elastic or clip hardware type, stitch placement, '
                         'thread colors, and handmade cotton linen texture from the source.'),
                        ('Tabletop colorway trio',
                         'Three bows arranged on vanity table',
                         'Arrange three coordinated hair bows flat on a bright light-wood vanity table or pale linen tabletop. '
                         'Every bow must rest fully on the table, not hang from a rack, hook, string, peg, or clothesline. Each '
                         'bow may have a different fabric color, but the embroidery motif, stitch colors, bow proportions, '
                         'center knot, tail drape, and scrunchie/clip construction must match the source. Use a clean feminine '
                         'handmade tabletop display with a wooden comb and dried flowers as secondary decor that does not cover the embroidery.'),
                        ('Tabletop colorway collection',
                         'Four bows laid on bright tabletop',
                         'Display four hair bows as a neat colorway collection laid flat or softly resting on a bright light-wood '
                         'tabletop in soft white daylight. Do not clip, pin, hang, peg, suspend, or attach the bows to any line, '
                         'rack, hook, wall, or clothesline. Keep every bow in the same source style with identical embroidery '
                         'placement, tail shape, bow-loop volume, center knot, hardware type, and cotton linen weave while '
                         'varying only the fabric base color. Use a clean airy tabletop composition with natural light and no busy background.'),
                        ('Lifestyle hair use',
                         'Bow worn on low ponytail from back',
                         'Show one hair bow worn on a low ponytail, photographed from the back or rear three-quarter angle '
                         'so the face is not the focus. The bow is the main subject, the embroidery faces the camera, and '
                         'the hair must not hide the stitches, center knot, tail drape, elastic/scrunchie ring, or clip '
                         'placement. Use soft window light, neat hair, and a bright minimal background.'),
                        ('Child hair lifestyle',
                         'Bow worn in child hair from back',
                         'Show one hair bow worn in the hair of a girl or female model, cropped from the back at a close '
                         'medium distance. Use a pale wall or white curtain background. Keep the bow fully visible and '
                         'correctly scaled, with embroidery sharp and not covered by hair. Preserve the exact source fabric '
                         'color family, stitch colors, bow shape, center knot, tail length, and elastic or clip construction.'),
                        ('Detail collage',
                         'Four-panel embroidery fabric hardware macro',
                         'Create one square detail collage made of four small close-up photos of the same hair bow. The '
                         'panels must show raised hand embroidery, cotton linen weave, the gathered scrunchie ring or '
                         'clip/barrette/hair-tie hardware if visible, seam finish, center knot wrap, and soft tail drape. '
                         'This is a detail-proof collage only; do not create a colorway grid or redesign the embroidery.'),
                        ('Process lifestyle',
                         'Hands embroidering matching bow fabric',
                         'Show an adult woman at a clean handmade craft table carefully embroidering the same motif onto '
                         'matching cotton linen fabric for the hair bow, using a small embroidery hoop, realistic needle '
                         'with thread, small scissors, thread spools, folded linen, and beautiful window light. Hands must '
                         'be anatomically natural with realistic needle placement. The scene should clearly suggest the '
                         'finished product is a hair bow or bow hair tie, not an embroidery hoop product.'),
                        ('Group lifestyle',
                         'Three girls wearing coordinated bows',
                         'Create a bright lifestyle photo of three girls or female models from the back or rear side, each '
                         'wearing one coordinated hair bow in a different linen base color. The bows must stay the focus, '
                         'with the same source embroidery layout, thread colors, bow shape, tail drape, and hair attachment '
                         'construction. Keep faces secondary or cropped and use clean white natural daylight.'),
                        ('Basket accessory scene',
                         'Bow in small wicker basket with hair props',
                         'Place one hair bow in a small wicker basket with a few simple secondary hair accessories, pale '
                         'linen cloth, and dried flowers. The embroidered face of the bow must point upward and remain '
                         'uncovered. Use a bright premium handmade Etsy composition and preserve the exact source bow '
                         'silhouette, center knot, tail ends, fabric texture, stitch relief, and elastic or clip hardware.'),
                        ('Handheld scale',
                         'Woman hand holding bow front visible',
                         'One adult woman hand holds the hair bow gently from the lower edge or center so the size is clear. '
                         'The embroidery, bow loops, tails, center knot, linen weave, and elastic/scrunchie ring or clip '
                         'detail must remain visible and not be hidden by fingers. Use soft white daylight, natural hand '
                         'anatomy, and a bright minimal background.'),
                        ('Gift presentation',
                         'Bow in small open gift box',
                         'Place one hair bow neatly inside a small open light-colored paper gift box that fits the product. '
                         'The bow should be arranged gently, not flattened too much, with embroidery facing upward and '
                         'visible. Do not place anything on top of the bow. Use very light decor such as linen cloth or '
                         'pale paper around the box, clean white daylight, and premium handmade gift styling.'))},
 'passport_cover': {'display_name': 'Passport Cover',
                    'aliases': ('Passport Cover',
                                'passport cover',
                                'passport holder',
                                'passport sleeve',
                                'passport case',
                                'travel document cover',
                                'linen passport cover',
                                'cotton linen passport cover',
                                'embroidered passport cover',
                                'hand embroidered passport cover',
                                'boc passport',
                                'bọc passport',
                                'vo passport',
                                'bia passport',
                                'boc ho chieu',
                                'vo boc ho chieu',
                                'bia ho chieu',
                                'vi ho chieu'),
                    'lock': 'the main product must remain the same hand-embroidered cotton linen passport cover or '
                            'passport holder from the source image, with the exact sleeve/pouch silhouette, fabric '
                            'weave, base fabric color, closure or drawstring/cord if present, seams or edges, '
                            'embroidery placement, motif scale, raised thread texture, natural wrinkles, and premium '
                            'handmade travel-accessory identity; never turn it into a book, generic pouch, tote, '
                            'wallet, passport booklet, or different travel accessory',
                    'shots': (('Travel flat lay',
                               'Travel desk with phone and boarding pass',
                               'Place the passport cover beside a phone, boarding pass, earbuds, and a small wallet on '
                               'a clean white tabletop. Add one white paper coffee cup, sunglasses, and a small keychain '
                               'as light travel props, but do not cover the embroidery. Shoot from a 45-degree overhead '
                               'angle with crisp modern white travel-lifestyle daylight. Keep the exact source cover '
                               'shape, fabric weave, base color, stitch relief, embroidery position, and any closure or '
                               'cord details unchanged.'),
                              ('Handheld scale',
                               'Hand holding cover front to camera',
                               'One adult hand holds the passport cover from the lower edge, with the embroidered front '
                               'facing the camera so the real size is clear. Use soft white natural light, natural skin '
                               'tone, and a lightly blurred airport, white curtain, or bright wall background. Shoot '
                               'straight-on at a close medium distance. The hand must not hide the embroidery, seams, '
                               'edges, cord, or fabric texture.'),
                              ('Airplane lifestyle',
                               'Cover by airplane window',
                               'Hold or place the passport cover beside an airplane window with a boarding pass as the '
                               'only secondary prop. The embroidery should be clear in the foreground, lit by white '
                               'natural window light without backlighting the product into darkness. Use a slight angled '
                               'view and keep the passport cover as the visual center. Do not add clutter or extra travel '
                               'items.'),
                              ('Travel prep flat lay',
                               'Checklist passport ticket phone charger',
                               'Place the passport cover on a bright table beside a simple travel checklist, pen, '
                               'passport, and small wallet. The checklist may contain short generic lines such as '
                               'passport, ticket, phone, and charger, but it must stay secondary and not make the image '
                               'busy. Shoot from a 60-75 degree overhead angle with clean white daylight, keeping the '
                               'cover embroidery and cotton linen texture sharp.'),
                              ('Colorway group',
                               'Three to five linen color covers on journal',
                               'Arrange three to five passport covers with the same embroidery layout and motif as the '
                               'source, but with different linen base colors, in a horizontal row or lightly layered on '
                               'an open travel journal over a white wood-grain table. Add a few small travel photos, '
                               'pale washi tape, blue-white postcard, and simple faux travel stamps. If the source '
                               'visibly contains a personalized name or initials, each color variant may use different '
                               'plausible names or initials while preserving the same lettering and stitch style; if the '
                               'source has no name, do not invent readable text.'),
                              ('Colorway pair',
                               'Two covers on bright balcony table',
                               'Place two passport covers on a white table near a bright balcony window, using different '
                               'linen base colors while keeping the embroidery motif, thread colors, cover shape, '
                               'construction, and any closure or cord details identical to the source. Add a baseball '
                               'cap, sunglasses, and linen tote as summer travel props. Use white natural shade light, '
                               'no harsh sun and no yellow cast, from a 30-45 degree angle.'),
                              ('Detail collage',
                               'Four-panel edge embroidery and name macro',
                               'Create one square detail collage made of four small close-up photos showing the passport '
                               'cover edge finish, embroidery motif, any stitched name or initials from the source, '
                               'fabric weave, raised thread texture, seams, corners, and closure or cord detail if '
                               'present. Use soft white light sharp enough to prove the cotton linen fibers and '
                               'handmade finish. No decor; this is a quality-proof close-up collage only.'),
                              ('Airport lifestyle',
                               'Traveler with cabin suitcase',
                               'Frame a person from shoulders down, one hand pulling a cabin suitcase and the other hand '
                               'holding the passport cover naturally at their side. Use a bright airport entrance or '
                               'airport hallway background, white outdoor shade or bright indoor light, and a slightly '
                               'low horizontal angle for a travel lifestyle feel. The passport cover must remain clear, '
                               'properly scaled, and not hidden by fingers or luggage.'),
                              ('Travel outfit lifestyle',
                               'Woman holding cover near suitcase',
                               'A woman in a minimal travel outfit stands near a bright window, holding the passport '
                               'cover in front of her chest or beside a suitcase. Use natural white light, soft '
                               'background blur, a light trench coat, tote bag, suitcase, and a white hotel or bright '
                               'room background. Shoot half-body from a three-quarter angle while keeping the embroidery '
                               'and product color bright and readable.'),
                              ('Couple travel cafe',
                               'Couple holding two cover colorways',
                               'A woman and a man in minimal travel outfits sit at a cafe table, each holding a passport '
                               'cover. The two covers may use different linen base colors, but the embroidery motif, '
                               'thread palette, product silhouette, closure, edges, and handmade texture must remain '
                               'consistent with the source. Shoot from the front so their faces and both product fronts '
                               'are visible, with coffee cups, phone, and earbuds on the table as secondary props.'),
                              ('Process lifestyle',
                               'Woman embroidering matching fabric',
                               'Show a woman sitting at a clean handmade craft table, holding the passport cover with '
                               'one hand while carefully embroidering the same motif onto fabric matching the product '
                               'color in a small embroidery hoop. Include a realistic threaded needle, small scissors, '
                               'thread spools, folded linen, and beautiful window light. Hands must be natural and '
                               'anatomically correct, with realistic needle placement and a genuine hand-embroidery '
                               'feel, not flat machine embroidery.'),
                              ('Gift presentation',
                               'Cover flattened in small open gift box',
                               'Place one passport cover neatly inside a small open light-colored paper gift box. The '
                               'cover should be slightly flattened or gently folded, not puffed up too large; if the '
                               'source is a soft pouch-style passport holder, let it sit naturally collapsed in the box. '
                               'The embroidered front faces upward and remains clearly visible. Use only very light decor '
                               'such as linen cloth or pale paper around the box, with nothing placed on top of the '
                               'product or covering the embroidery.'))}}


PRODUCT_SHOT_RULES["halloween_notebook"] = {
    "display_name": "Halloween Notebook",
    "aliases": (
        "Halloween Notebook",
        "halloween recipe notebook",
        "halloween recipe book",
        "embroidered halloween notebook",
        "embroidered halloween recipe book",
    ),
    "lock": (
        "the main product must remain the exact same fabric-covered hardbound Halloween notebook or recipe book "
        "from the source image, with the same rectangular book shape, cover thickness, spine and edge construction, "
        "linen fabric color and weave, embroidered wording, lettering placement, Halloween motif arrangement, thread "
        "colors, raised hand-stitch texture, proportions, and premium handmade identity; preserve every readable word "
        "visible on the source cover exactly and never turn the book into a vow book, wedding guest book, photo album, "
        "pillow, bag, hoop, loose fabric panel, or another product"
    ),
    "shots": (
        (
            "Hero flat lay",
            "Notebook on white wood table with Halloween accents",
            "Place the exact closed Halloween notebook flat at the center of a white wood-grain table, filling about "
            "65-75 percent of the square frame. Let the embroidered front cover face straight toward the camera. Add "
            "only a few small pumpkins, autumn leaves, a friendly miniature ghost, and a loose orange ribbon around the "
            "outer edges. Use clear white natural window light, an airy composition, and sharp focus on the linen weave, "
            "raised hand embroidery, cover edges, spine, and exact source lettering. Keep all decor secondary and never "
            "cover the embroidery.",
        ),
        (
            "Kitchen lifestyle",
            "Notebook upright on a bright kitchen counter",
            "Stand the exact closed Halloween notebook upright on a small wooden book stand on a clean bright kitchen "
            "counter. Style the background with a mixing bowl, wooden spoon, two mini pumpkins, and a softly blurred tray "
            "of autumn cookies. Use white daylight without a yellow cast, shoot at cover height from a slight 30-degree "
            "angle, and keep the embroidered cover as the clear focal point. Do not change the source wording or motif.",
        ),
        (
            "Recipe preparation",
            "Notebook beside autumn baking ingredients",
            "Place the exact closed notebook beside neatly arranged autumn baking ingredients: flour in a small ceramic "
            "bowl, cinnamon sticks, one apple, one mini pumpkin, and a whisk. Shoot from 60-75 degrees above in clean "
            "white natural light. Keep the setup spacious and premium, with the complete embroidered cover unobstructed "
            "and larger than every individual prop.",
        ),
        (
            "Shelf display",
            "Notebook on a bright kitchen shelf",
            "Display the exact Halloween notebook front-facing on a light kitchen shelf between a small white ceramic "
            "ghost and two tiny pumpkins. Add a folded neutral tea towel and one wooden spoon as subtle recipe-book cues. "
            "Use bright diffused window light and shallow depth of field while keeping the full cover, spine, fabric "
            "texture, exact lettering, and embroidery crisp and unchanged.",
        ),
        (
            "Hands lifestyle",
            "Adult holding notebook front toward camera",
            "Show an adult in a bright airy kitchen holding the exact closed Halloween notebook naturally with both "
            "hands, the embroidered front cover facing the camera. Frame from shoulders to waist so the book remains the "
            "main subject. Hands must be anatomically correct and must not cover the source wording, motifs, corners, or "
            "spine. Use clean white daylight and a softly blurred Halloween baking background.",
        ),
        (
            "Family lifestyle",
            "Parent and child choosing a Halloween recipe",
            "Create a realistic bright kitchen moment with a parent and child preparing Halloween cookies while the exact "
            "closed notebook stands prominently in the foreground with its embroidered cover facing the camera. Keep "
            "people and baking activity softly secondary. Use natural morning light, restrained pumpkin and friendly ghost "
            "decor, correct hands, and a clean premium Etsy handmade atmosphere.",
        ),
        (
            "Gift presentation",
            "Notebook inside an open Halloween gift box",
            "Place the exact closed Halloween notebook neatly inside an open light-colored gift box lined with white tissue "
            "paper. The embroidered front faces upward and remains fully visible. Add a narrow rust-orange ribbon, one mini "
            "pumpkin, a small gift tag with no readable text, and a few autumn leaves outside the box. Use bright white "
            "natural light and an elegant uncluttered composition.",
        ),
        (
            "Seasonal table",
            "Notebook with cider and pumpkin pie",
            "Place the exact closed notebook on a bright dining table beside a small slice of pumpkin pie and a clear glass "
            "of apple cider. Add two mini pumpkins and a few maple leaves, leaving generous negative space. Shoot at a "
            "45-degree angle in clean white daylight without dark orange or yellow lighting. The notebook must dominate "
            "the frame and its complete embroidery must remain sharp and unchanged.",
        ),
        (
            "Craft process",
            "Woman hand embroidering the matching cover motif",
            "Show a woman at a clean craft table hand-embroidering the same Halloween motif from the source cover onto "
            "matching linen fabric held in a round embroidery hoop. One hand supports the hoop and the other uses a "
            "realistically threaded needle at the correct stitch position. Place the completed exact notebook beside the "
            "hoop as the main reference product, front cover visible. Include small scissors, thread skeins matching the "
            "source colors, and subtle mini pumpkins under bright natural window light.",
        ),
        (
            "Process collage",
            "Four-panel handmade notebook process",
            "Create one clean square 2x2 collage: panel one selects linen matching the source cover; panel two sketches the "
            "exact cover motif on linen; panel three shows realistic hand embroidery in a hoop with a threaded needle; "
            "panel four shows the exact completed Halloween notebook. Keep lighting, colors, and scale consistent across "
            "all four panels. The final panel must preserve the exact source cover shape, wording, motif, and stitch layout.",
        ),
        (
            "Detail collage",
            "Four close-ups of embroidery fabric spine and corners",
            "Create one square 2x2 detail collage containing four macro photographs of the exact source notebook: raised "
            "embroidery and thread direction, linen weave and stitched wording, spine and cover edge construction, and a "
            "corner with the Halloween motif. Use bright soft white light, true source colors, and sharp handmade texture. "
            "Do not redesign, simplify, move, or replace any embroidery element.",
        ),
        (
            "Cozy kitchen hero",
            "Notebook near window with restrained Halloween decor",
            "Create a premium lifestyle hero photo of the exact closed Halloween notebook leaning slightly against a "
            "small wooden board near a bright kitchen window. Add a folded linen towel, one ceramic ghost, two mini "
            "pumpkins, and a softly blurred bowl of apples. Use clear airy white daylight, no dark moody lighting and no "
            "strong yellow cast. Keep the full embroidered cover unobstructed and preserve every source detail exactly.",
        ),
    ),
}


PRODUCT_SHOT_RULES["album"] = {
    "display_name": "Album",
    "aliases": (
        "Album",
        "photo album",
        "memory album",
        "keepsake album",
        "embroidered album",
        "hand embroidered album",
        "linen album",
        "fabric album",
    ),
    "target_count": 12,
    "lock": (
        "the main product must remain the exact same handmade fabric-covered hardbound album from the source image, "
        "with the same rectangular shape, cover dimensions, thickness, spine, binding, edge construction, linen or "
        "fabric color and weave, embroidery motif, embroidery placement and scale, readable stitched lettering, thread "
        "colors, raised hand-stitch texture, natural handmade details, and premium keepsake identity. Preserve every "
        "readable source character exactly. Never turn the album into a notebook, recipe book, vow book, guest book, "
        "pillow, bag, hoop, loose fabric panel, or another product. Do not invent photo-pocket pages, rings, closures, "
        "or internal page construction that is not visible in the source"
    ),
    "shots": (
        (
            "Hero flat lay",
            "Closed album hero with season-matched accents",
            "Place the exact closed album at the center of a clean light wood or neutral linen surface with its complete "
            "embroidered cover facing the camera. Add only two or three small props that match the season or occasion "
            "visible on the source cover. Use bright airy natural daylight and sharp focus on the embroidery, fabric "
            "weave, spine, edges, and exact source lettering.",
        ),
        (
            "Upright display",
            "Album upright on a small wooden stand",
            "Display the exact closed album upright on a small light wooden book stand. Use a bright uncluttered interior "
            "and a few restrained season-matched decorations behind it. Shoot near cover height from a slight angle while "
            "keeping the entire cover, spine, dimensions, embroidery, and source lettering sharp and unchanged.",
        ),
        (
            "Seasonal flat lay",
            "Album with coordinated handmade keepsake props",
            "Create a spacious top-down flat lay of the exact closed album with a narrow ribbon, matching embroidery "
            "thread, one small printed photograph placed beside the album, and tasteful props selected from the source "
            "season. Nothing may cover or touch the embroidered design. Use clean white-balanced daylight.",
        ),
        (
            "Shelf lifestyle",
            "Front-facing album on a bright shelf",
            "Place the exact album front-facing on a bright shelf or console with one small framed photograph and two "
            "subtle season-matched objects nearby. Keep the album as the largest and sharpest subject. Preserve the exact "
            "cover design, readable lettering, binding, thickness, fabric texture, and handmade proportions.",
        ),
        (
            "Hands lifestyle",
            "Adult holding album cover toward camera",
            "Show an adult naturally holding the exact closed album with both hands, embroidered front cover facing the "
            "camera. Frame from shoulders to waist and use anatomically correct hands that do not cover the motif, text, "
            "corners, or spine. Use bright natural window light and a softly blurred season-matched background.",
        ),
        (
            "Tabletop story",
            "Album beside loose photographs and ribbon",
            "Place the exact closed album on a clean tabletop beside three loose printed photographs, a narrow ribbon, "
            "and matching thread skeins. Keep all props outside the album and do not invent or expose internal pages. "
            "Shoot at a 45-degree angle in bright soft daylight with the embroidered cover dominant and unobstructed.",
        ),
        (
            "Gift presentation",
            "Album inside an open premium gift box",
            "Place the exact closed album neatly inside an open light-colored gift box lined with white tissue paper. "
            "Keep the embroidered cover fully visible and add a narrow season-matched ribbon plus one small decorative "
            "object outside the box. Use bright natural light and a clean premium handmade gift composition.",
        ),
        (
            "Window lifestyle",
            "Album near window with soft leaf shadow",
            "Place the exact closed album near a bright window so a very soft leaf shadow falls partly across the fabric "
            "without obscuring any embroidery or lettering. Add one small season-matched prop at the outer edge. Keep the "
            "album shape, spine, binding, cover texture, design placement, and colors unchanged.",
        ),
        (
            "Craft process",
            "Woman embroidering matching album cover linen",
            "Show a woman at a clean craft table hand-embroidering the exact source cover motif onto matching fabric in a "
            "round wooden hoop. One hand supports the hoop and the other uses a realistically threaded needle at the "
            "correct stitch position. Place the completed exact closed album beside the hoop with matching thread skeins "
            "and small scissors under bright natural window light.",
        ),
        (
            "Process collage",
            "Four-panel handmade album cover process",
            "Create one square 2x2 collage: selecting fabric matching the source album; sketching the exact source motif; "
            "hand-embroidering it in a hoop with a threaded needle; and the completed exact album. Preserve the source "
            "shape, cover dimensions, spine, motif, wording, colors, and handmade texture in every applicable panel.",
        ),
        (
            "Detail collage",
            "Four close-ups of embroidery fabric spine and edges",
            "Create one square 2x2 macro collage of the exact album showing raised hand stitches and thread direction, "
            "linen weave and source lettering, spine and binding construction, and one cover corner or finished edge. "
            "Use bright soft natural light, true source colors, and ultra-sharp premium handmade detail.",
        ),
        (
            "Premium hero",
            "Album on console with generous negative space",
            "Create a premium hero photograph of the exact closed album standing slightly angled on a light console near "
            "a bright window. Add only a few refined props that match the source season and leave generous negative "
            "space. Keep the entire embroidered cover unobstructed and preserve every source detail exactly.",
        ),
    ),
}


PRODUCT_SHOT_RULES["notebook"] = {
    "display_name": "Notebook",
    "aliases": (
        "Notebook",
        "embroidered notebook",
        "hand embroidered notebook",
        "linen notebook",
        "fabric notebook",
        "personalized notebook",
        "recipe notebook",
        "journal notebook",
    ),
    "target_count": 12,
    "lock": (
        "the main product must remain the exact same handmade fabric-covered hardbound notebook from the source image, "
        "with the same rectangular shape, cover dimensions, thickness, spine, binding, page block, edge construction, "
        "linen or fabric color and weave, embroidery motif, embroidery placement and scale, readable stitched lettering, "
        "thread colors, raised hand-stitch texture, natural handmade details, and premium notebook identity. Preserve "
        "every readable source character exactly. Never turn the notebook into a photo album, vow book, guest book, "
        "pillow, bag, hoop, loose fabric panel, or another product"
    ),
    "shots": (
        (
            "Hero flat lay",
            "Closed notebook hero with season-matched accents",
            "Place the exact closed notebook at the center of a clean light wood or neutral linen surface with the full "
            "embroidered cover facing the camera. Add only two or three small props matching the source season or "
            "occasion. Use bright airy natural daylight and sharp focus on the embroidery, fabric, spine, page block, "
            "edges, and exact source lettering.",
        ),
        (
            "Upright display",
            "Notebook upright on a small wooden stand",
            "Display the exact closed notebook upright on a small wooden stand in a bright uncluttered interior. Use "
            "restrained season-matched decor behind it and shoot near cover height, keeping the complete cover, spine, "
            "page block, embroidery, and wording sharp and unchanged.",
        ),
        (
            "Writing desk",
            "Notebook beside pen and coordinated stationery",
            "Place the exact closed notebook on a bright writing desk beside one elegant pen, a small stack of blank "
            "paper, and matching embroidery thread. Keep the embroidered front cover completely visible. Use a clean "
            "45-degree composition and soft white-balanced window light.",
        ),
        (
            "Shelf lifestyle",
            "Front-facing notebook on bright shelf",
            "Place the exact notebook front-facing on a bright shelf with one small cup holding pencils and two subtle "
            "season-matched decorations. Keep the notebook as the largest, sharpest subject and preserve its exact "
            "cover design, text, fabric, dimensions, spine, and handmade construction.",
        ),
        (
            "Hands lifestyle",
            "Adult holding notebook cover toward camera",
            "Show an adult naturally holding the exact closed notebook with both hands, cover facing the camera. Hands "
            "must be anatomically correct and must not cover the motif, wording, corners, or spine. Use bright natural "
            "window light and a softly blurred setting coordinated with the source season.",
        ),
        (
            "Desk lifestyle",
            "Notebook in a bright creative workspace",
            "Feature the exact closed notebook prominently in a clean creative workspace with a pen, folded linen, and "
            "one small season-matched object. Keep the complete embroidered cover unobstructed and sharply focused under "
            "bright soft daylight.",
        ),
        (
            "Gift presentation",
            "Notebook inside an open premium gift box",
            "Place the exact closed notebook inside an open light-colored gift box lined with white tissue paper. Keep "
            "the embroidered cover fully visible and add a narrow coordinated ribbon plus one small season-matched prop "
            "outside the box. Use bright natural light and an uncluttered premium handmade presentation.",
        ),
        (
            "Window lifestyle",
            "Notebook near window with soft leaf shadow",
            "Place the exact closed notebook near a bright window so a soft leaf shadow crosses a small part of the fabric "
            "without obscuring the embroidery or wording. Preserve the source shape, cover texture, page block, spine, "
            "motif placement, colors, and handmade proportions.",
        ),
        (
            "Craft process",
            "Woman embroidering matching notebook cover",
            "Show a woman at a clean craft table hand-embroidering the exact source motif onto matching fabric in a round "
            "wooden hoop. Use natural anatomically correct hands and a realistically threaded needle at the correct stitch "
            "position. Place the completed exact notebook beside the hoop with matching thread and small scissors.",
        ),
        (
            "Process collage",
            "Four-panel handmade notebook process",
            "Create one square 2x2 collage showing fabric selection, exact motif sketching, realistic hand embroidery in "
            "a hoop, and the completed exact notebook. Preserve the source notebook dimensions, spine, cover motif, "
            "wording, thread colors, and handmade texture throughout.",
        ),
        (
            "Detail collage",
            "Four close-ups of embroidery fabric spine and page block",
            "Create one square 2x2 macro collage showing raised embroidery and thread direction, fabric weave and exact "
            "source lettering, spine and binding, and page-block or cover-edge construction. Use bright soft daylight, "
            "true source colors, and ultra-sharp handmade detail.",
        ),
        (
            "Premium hero",
            "Notebook on console with negative space",
            "Create a premium hero photo of the exact closed notebook standing slightly angled on a light console near a "
            "bright window. Add only refined season-matched props and generous negative space. Keep the complete cover "
            "unobstructed and preserve every source detail exactly.",
        ),
    ),
}


PRODUCT_SHOT_RULES["christmas_sash"] = {
    "display_name": "Christmas Sash",
    "aliases": (
        "Christmas Sash",
        "christmas sash",
        "Christmas Wreath Sash",
        "christmas wreath sash",
        "Christmas Linen Sash",
        "christmas linen sash",
        "Embroidered Christmas Sash",
        "embroidered christmas sash",
        "Noel Sash",
        "noel sash",
        "Xmas Sash",
        "xmas sash",
    ),
    "target_count": 12,
    "lock": _CHRISTMAS_SASH_LOCK,
    "shots": (
        (
            "Wreath close-up",
            "Close front view of sash tied below evergreen wreath",
            _christmas_sash_brief(
                "tie the exact sash at the bottom center, exactly at 6 o'clock, of a fresh green evergreen wreath "
                "decorated with red berries and dried orange slices. Preserve the source orientation with the motif tail "
                "on the left and the lettering tail on the right, and keep both complete tails hanging below the wreath. "
                "Hide a few small bronze baubles within the greenery without letting them touch the sash. Shoot a tight "
                "straight-on close-up in refined warm afternoon sunlight, with tack-sharp focus on the raised embroidery."
            ),
        ),
        (
            "Gift presentation",
            "Sash folded in open cream gift box",
            _christmas_sash_brief(
                "fold the exact sash neatly inside an open cream gift box lined with white tissue paper, placing both "
                "embroidered tails side by side and face-up so the complete motif and source lettering are clearly "
                "readable. Curl a loose red tartan ribbon around the box and add one small evergreen sprig plus one "
                "cinnamon stick at a corner. Shoot an overhead unboxing composition on a light neutral surface in soft "
                "bright daylight, conveying a premium handmade Christmas gift."
            ),
        ),
        (
            "Staircase lifestyle",
            "Sash tied around dark wooden banister",
            _christmas_sash_brief(
                "tie the exact sash in a soft simple knot around a dark wooden staircase banister post, with both full "
                "embroidered tails draping naturally down along the railing. Shoot from a slight angle looking along the "
                "staircase with deep background blur. Decorate the railing with an evergreen garland, red baubles, and "
                "restrained warm string lights. Use a cozy warm indoor late-afternoon atmosphere while keeping the knot, "
                "linen color, and raised embroidery sharply focused."
            ),
        ),
        (
            "Front door lifestyle",
            "Christmas wreath sash on decorated front door",
            _christmas_sash_brief(
                "create a wide straight-on winter front-door scene with one very small evergreen wreath mounted flat at "
                "the center of the entrance door using a hidden hook. Tie the exact small sash at the wreath's bottom "
                "center at 6 o'clock, with both tails hanging flat against the door and fully visible below the wreath. "
                "The sash must remain short, narrow, and realistically small, never oversized or overlong. Style the steps with stacked "
                "kraft-paper gifts, one small wooden sled, a candle lantern, and two mini potted evergreens. Use crisp "
                "clear winter daylight, keep the sash as the visual center, and prevent every prop from covering either "
                "embroidered tail."
            ),
        ),
        (
            "Handmade flat lay",
            "Knotted sash lying on light wooden table",
            _christmas_sash_brief(
                "tie the exact sash in the same soft simple knot shown by the source and lay it flat at the center of a "
                "light wooden table, with both complete embroidered tails face-up, untwisted, and fully readable. Shoot "
                "top-down at exactly 90 degrees in bright even white studio light. Balance the edges with one evergreen "
                "sprig, a few small baubles, and restrained Christmas decorations without covering either embroidered tail."
            ),
        ),
        (
            "Detail grid",
            "Four-panel embroidery linen hem and wreath-knot details",
            _christmas_sash_brief(
                "create one square 2x2 macro collage containing exactly four panels: panels one and two show two different "
                "close sections of the exact raised hand-embroidery stitches on the white linen, including individual "
                "thread fibers, stitch direction, original colors, and exact motif details; panel three shows the pointed "
                "sash-tail hem and edge stitching; panel four shows the realistic fabric knot "
                "wrapped around the bottom rim of an evergreen wreath. Use soft natural light and ultra-high sharpness "
                "to emphasize authentic hand craftsmanship. This is the only collage in the set."
            ),
        ),
        (
            "Three-color comparison",
            "Three neutral linen sash colorways in flat lay",
            _christmas_sash_brief(
                "arrange exactly three identical sashes diagonally across a neutral-toned wooden table, each made in a "
                "different subtle neutral linen base color while preserving the same exact physical construction, knot "
                "style, embroidery design, source lettering, embroidery placement, thread colors, pointed ends, and "
                "dimensions. Shoot top-down as one flat-lay scene in bright even white studio light. Scatter a few pine "
                "cones, red berries, and restrained Christmas decorations around the edges without covering any tail."
            ),
        ),
        (
            "Book stack lifestyle",
            "Sash draped over vintage books by winter window",
            _christmas_sash_brief(
                "drape the exact sash diagonally over a stack of three vintage hardback books in brown and deep green "
                "beside a window, with both embroidered tails flowing toward the foreground. Place a steaming cup of "
                "cocoa softly blurred behind it, thin-frame reading glasses, and one candy cane on the books. Shoot from "
                "45 degrees overhead with shallow depth of field toward the window in clear warm slanting winter morning "
                "sunlight. Steam must remain subtle and never obscure the sash; the embroidery is the sharpest detail."
            ),
        ),
        (
            "Door-handle lifestyle",
            "Sash tied to antique brass door handle",
            _christmas_sash_brief(
                "tie the exact sash in a soft simple knot around an antique brass handle on a dark moss-green painted "
                "wooden door. Keep both embroidered tails flat, untwisted, and hanging straight against the door along "
                "the right third of the composition. Tuck one small mistletoe sprig above the knot without covering it. "
                "Shoot at eye level, nearly straight-on with a slight 15-degree angle, in gentle indoor daylight with a "
                "subtle highlight on the brass and crisp focus on both embroidered tails."
            ),
        ),
        (
            "Gift basket lifestyle",
            "Small sash tied to gift basket beside child",
            _christmas_sash_brief(
                "tie the exact small sash in a simple knot around the handle of a Christmas gift basket placed on the "
                "floor, with both embroidered tails hanging fully visible down the basket side. Show a child seated "
                "beside the basket naturally reaching one hand toward it without touching or covering the sash. Place a "
                "warm-lit Christmas tree softly blurred in the background of a festive room. Shoot straight-on in clean "
                "white studio-balanced light across the full image, with natural anatomy and sharp sash embroidery."
            ),
        ),
        (
            "Two-color comparison",
            "Two neutral linen sash colorways on wooden table",
            _christmas_sash_brief(
                "place exactly two identical sashes diagonally on a wooden table using two different neutral linen base "
                "colors drawn from the source palette. Preserve the same exact design, source lettering, thread colors, "
                "embroidery placement, construction, proportions, pointed ends, and simple knot style on both. Shoot "
                "from a 45-degree overhead angle in bright even white studio light. Scatter pine cones, red berries, and "
                "small Christmas decorations around the edges without covering either embroidered tail."
            ),
        ),
        (
            "Hand embroidery process",
            "Artisan hand-stitching exact Christmas sash motif",
            _christmas_sash_brief(
                "show a close 45-degree over-the-shoulder view of an artisan's anatomically natural hands hand-stitching "
                "the exact source Christmas motif onto matching sash linen stretched in a round wooden embroidery hoop. "
                "One hand supports the hoop and the other holds a realistic sewing needle at the true stitch position; "
                "the needle eye is visibly threaded and the thread color exactly matches the motif section being worked. "
                "Every completed portion must match the source motif, placement, scale, stitch direction, and original "
                "thread colors. Arrange red, evergreen-green, and bronze-gold thread spools, small embroidery scissors, "
                "and spare linen on the wooden table. Use clean white studio light and shallow depth of field while keeping "
                "the hand embroidery and needle contact point sharply focused."
            ),
        ),
    ),
}


PRODUCT_SHOT_RULES["family_halloween_sash"] = {
    "display_name": "Family Halloween Sash",
    "aliases": (
        "Family Halloween Sash",
        "family halloween sash",
        "Family Halloween Wreath Sash",
        "family halloween wreath sash",
        "Halloween Family Sash",
        "halloween family sash",
        "personalized family halloween sash",
        "family wreath sash halloween",
    ),
    "target_count": 12,
    "allow_planned_prop_text": True,
    "lock": (
        "the main product must remain the exact same cotton linen Halloween wreath sash from the source image: same "
        "linen weave, fabric color, embroidery placement, embroidery scale, source lettering, thread colors, natural "
        "wrinkles, seams, soft volume, and premium handmade identity; never redesign the sash, change the embroidery, "
        "move the motif, change the fabric, add tags, logos, or watermarks, or turn it into another product. Every motif "
        "and character must visibly be embroidered by hand with raised individual thread stitches, never printed, "
        "digitally applied, machine embroidered, or machine-flat. SIZE LOCK: "
        "the sash keeps the exact same physical dimensions in every image, including the same total length, tail width, "
        "and knot size. Its scale relative to every wreath is constant: the two tails are clearly longer than the wreath "
        "diameter and extend well below the wreath. GLOBAL WREATH SCENE LOCK: whenever the sash is tied to a wreath, it "
        "must be tied at the bottom center, exactly at the 6 o'clock position, with the knot sitting on the lower rim and "
        "both tails draping straight down below the wreath, fully visible and never overlapping the wreath body. Every "
        "wreath shown against a door or wall must be physically mounted flat against that surface with a hidden hook, no "
        "visible gap, never floating in mid-air, and never suspended loosely"
    ),
    "shots": (
        (
            "Handmade process",
            "Hands embroidering matching Halloween sash linen",
            "Create a close-up lifestyle photo of natural hands embroidering the exact source Halloween design onto white "
            "linen fabric stretched in a wooden embroidery hoop. Place the finished exact wreath sash and embroidery "
            "floss spools beside the hoop on a wooden table, with vintage stork scissors nearby. Use soft window light, a "
            "cozy crafting atmosphere, and sharp focus on the realistically threaded needle at the correct stitch "
            "position. Do not alter the linen fabric, sash design, embroidery placement, source lettering, or thread colors.",
        ),
        (
            "Flat lay",
            "Folded sash with pumpkins leaves ribbon and lantern",
            "Create an overhead flat lay of the exact folded white cotton linen wreath sash on a wooden table. Keep both "
            "embroidered tails visible enough to verify the source design. Surround it with mini pumpkins, dried autumn "
            "leaves, black ribbon, and one small lantern. Use soft diffused daylight and sharp focus on the raised hand "
            "embroidery and linen weave. Do not alter the sash construction, fabric, embroidery, or thread colors.",
        ),
        (
            "Indoor mantel",
            "Autumn leaf wreath on Halloween fireplace mantel",
            "Tie the exact white linen sash at the bottom center of a small autumn leaf wreath, exactly at 6 o'clock. Prop "
            "the wreath upright on a fireplace mantel leaning flat against the wall with no visible gap or floating "
            "appearance. The knot sits on the lower wreath rim and both full-length tails drape straight down below the "
            "wreath over the mantel edge without overlapping the wreath body. Style with black taper candles, dried "
            "pampas grass, and small white fabric ghost ornaments. Use cozy warm indoor light, soft shadows, and sharp "
            "unchanged embroidery detail.",
        ),
        (
            "Styled close-up",
            "Embroidered tails on dried autumn leaf wreath",
            "Create a close styled photo of the exact sash tied at the bottom center, exactly at 6 o'clock, of a wreath "
            "made of dried orange and burgundy autumn leaves with small fabric ghost ornaments tucked into the foliage. "
            "The knot sits on the lower rim and both full-length tails drape completely below the wreath without "
            "overlapping its body. Preserve the source layout exactly: the Halloween design remains on the same left tail "
            "and the source text remains on the same right tail. Use warm afternoon light and crisp focus on the linen "
            "weave and embroidery detail.",
        ),
        (
            "Indoor hands lifestyle",
            "Hands tying sash above rustic fireplace mantel",
            "Show two anatomically correct hands tying the exact wreath sash onto the bottom rim of a dark twig Halloween "
            "wreath at the 6 o'clock position. The wreath is already mounted completely flat against the wall above a "
            "rustic wooden fireplace mantel with a hidden hook, no visible gap, and no floating appearance. The knot sits "
            "on the lower rim and both full-length tails fall straight down below the wreath without overlapping its "
            "body. Style the mantel with orange and cream pumpkins, muted burgundy dried eucalyptus, and lit pillar "
            "candles on brass holders. Use soft warm interior light, shallow depth of field, and sharp focus on the hands "
            "and unchanged sash embroidery. This must be one standalone lifestyle photograph, never a collage.",
        ),
        (
            "Gift presentation",
            "Sash folded inside cream gift box",
            "Place the exact sash neatly folded inside an open cream gift box lined with white tissue paper, with both "
            "embroidered tails displayed side by side facing upward. Curl a burnt-orange grosgrain ribbon loosely around "
            "the sash and place one small real mini pumpkin in a corner of the box. Use bright soft daylight on a light "
            "neutral surface for a premium handmade gift presentation. Preserve the exact tail width, embroidery, linen "
            "weave, seams, source lettering, and thread colors.",
        ),
        (
            "Basket lifestyle",
            "Sash tied around pumpkin basket handle by door",
            "Show the versatility of the exact linen sash tied in a neat knot around the handle of a natural woven basket "
            "filled with orange and white mini pumpkins. Place the basket on a wooden floor beside a front door with "
            "Halloween styling. Both full-length embroidered tails drape down the side of the basket, fully visible and "
            "correctly scaled. Use soft warm daylight, a farmhouse Halloween atmosphere, and sharp focus on the unchanged "
            "embroidery, linen fabric, seams, and thread colors.",
        ),
        (
            "Front porch lifestyle",
            "Bright Halloween porch with bottom-center wreath sash",
            "Create a bright daytime front porch scene from a slight side angle that shows porch depth. Tie the exact sash "
            "at the bottom center, exactly at 6 o'clock, of a small maple leaf and miniature pumpkin wreath mounted "
            "completely flat against the front door using a hidden hook, with no visible gap or floating appearance. The "
            "knot rests on the lower rim and both full-length tails hang straight down against the door well below the "
            "wreath without overlapping its body. Style the porch with stacked vintage orange and white pumpkins, potted "
            "rust-colored daisies, one tasteful Halloween animal figurine, and a woven doormat whose only readable prop "
            "text is Welcome. Use clear autumn morning light and sharp focus on the unchanged sash.",
        ),
        (
            "Staircase lifestyle",
            "Sash tied around dark wooden banister post",
            "Show the versatility of the exact linen sash tied in a soft knot around a dark wooden staircase banister "
            "post. Both full-length embroidered tails drape down naturally along the railing, fully visible and correctly "
            "scaled. Decorate the staircase with an autumn leaf and mini pumpkin garland plus restrained warm string "
            "lights. Use a cozy Halloween home interior in soft evening light and sharp focus on the unchanged sash "
            "embroidery, linen weave, seams, source lettering, and thread colors.",
        ),
        (
            "Basket lifestyle",
            "Sash tied around basket handle beside front door",
            "Show the versatility of the exact linen sash tied in a neat knot around the handle of a natural woven basket "
            "filled with orange and white mini pumpkins. Place the basket on a wooden floor beside a front door with "
            "Halloween styling. Both full-length embroidered tails drape down the side of the basket, fully visible and "
            "correctly scaled. Use soft warm daylight, a farmhouse Halloween atmosphere, and sharp focus on the unchanged "
            "embroidery, linen fabric, seams, source lettering, and thread colors.",
        ),
        (
            "Colorway wreath display",
            "Three neutral sash colorways on side-by-side fall wreaths",
            "Create one standalone square photograph of exactly three fall leaf wreaths hanging side by side on a wide "
            "wooden door. Each wreath is mounted completely flat against the door with its own hidden hook, no visible "
            "gap, and no floating appearance. Tie one sash at the bottom center, exactly at 6 o'clock, of each wreath. "
            "Every knot rests on the lower rim and every pair of full-length tails drapes straight down well below its "
            "wreath without overlapping the wreath body; the tails remain clearly longer than the wreath diameter. Use "
            "three different neutral linen base colors, one color per sash, while preserving the exact same source sash "
            "dimensions, tail width, border and seam construction, embroidery design, embroidery placement, embroidery "
            "scale, source lettering, thread colors, raised hand-stitched texture, and knot style on all three. Add autumn "
            "pumpkins on the floor below, use warm natural light, and keep the color variety and handmade embroidery "
            "texture sharply focused. This is one single-scene photograph, not a collage or grid.",
        ),
        (
            "Color swatch flat lay",
            "Three neutral linen sash colorways on wooden table",
            "Create one top-down flat lay photograph of exactly three identical Halloween wreath sashes arranged "
            "diagonally on a neutral wooden table. Use three different neutral linen base colors, one per sash, while "
            "keeping the exact same physical dimensions, tail width, pointed ends, border and seam construction, "
            "embroidery design, embroidery placement, embroidery scale, source lettering, embroidery thread colors, "
            "raised hand-stitched texture, and Halloween knot style on all three. Do not change the motif design, motif "
            "colors, or sash borders. Use soft natural light and sharp focus to create a clean color-comparison "
            "composition, with a few small dried autumn leaves and small Halloween ornaments placed around the sashes. "
            "This is one single flat-lay photograph, not a collage or grid.",
        ),
    ),
}


PRODUCT_SHOT_RULES["halloween_wreath_sash"] = {
    "display_name": "Halloween Wreath Sash",
    "aliases": (
        "Halloween Wreath Sash",
        "halloween wreath sash",
        "Halloween Sash",
        "halloween sash",
        "embroidered halloween wreath sash",
        "hand embroidered halloween sash",
        "handmade halloween wreath sash",
    ),
    "target_count": 12,
    "lock": (
        "the main product must remain the exact same handmade cotton linen Halloween wreath sash from the source "
        "image, including the same linen weave, fabric color, embroidery motif, embroidery placement and scale, "
        "source lettering, thread colors, raised hand-stitched texture, natural wrinkles, seams, soft volume, and "
        "premium handmade identity. Every pattern must visibly be embroidered by hand, never printed, digitally "
        "applied, machine embroidered, or machine-flat. Never redesign the sash, change or move the embroidery, "
        "change the fabric, add tags, logos, or watermarks, or turn it into another product. SIZE LOCK: keep the exact "
        "same physical dimensions in every image, including total length, tail width, and knot size. Keep the same "
        "scale relative to the wreath: both tails are clearly longer than the wreath diameter and extend well below "
        "it. GLOBAL WREATH SCENE LOCK: whenever the sash is tied to a wreath, tie it at the bottom center, exactly at "
        "the 6 o'clock position, with the knot sitting on the lower rim and both tails draping straight down below "
        "the wreath, fully visible and never overlapping the wreath body. Every wreath shown on a door or wall must "
        "be mounted flat against that surface with a hidden hook, no visible gap, never floating in mid-air"
    ),
    "shots": (
        (
            "Handmade process",
            "Hands embroidering Halloween design on linen",
            "Create one close-up lifestyle photograph of natural hands embroidering the exact source Halloween design "
            "onto white linen stretched in a wooden embroidery hoop. Place the finished exact sash, matching embroidery "
            "floss spools, and vintage stork scissors beside the hoop on a wooden table. Use soft window light, a cozy "
            "crafting atmosphere, and sharp focus on the realistically threaded needle and raised hand stitches.",
        ),
        (
            "Flat lay",
            "Folded sash with pumpkins leaves ribbon and lantern",
            "Create one overhead flat lay of the exact folded sash on a wooden table, surrounded by mini pumpkins, dried "
            "autumn leaves, black ribbon, and one small lantern. Keep the source embroidery visible and unobstructed. "
            "Use soft diffused daylight and sharp focus on the raised hand-embroidery texture and linen weave.",
        ),
        (
            "Process grid",
            "Four-panel embroidery weave hem and knot macro collage",
            "Create one square 2x2 macro collage containing exactly four panels: panel one shows the exact "
            "hand-embroidered Halloween stitch detail on white linen; panel two shows the matching linen weave texture; "
            "panel three shows the exact pointed tail hem stitching; panel four shows the fabric knot fold where the "
            "sash ties around the bottom rim of a dark twig wreath. Use soft natural light and ultra-sharp focus on the "
            "handmade embroidery texture. This is the only output in the set that may be a collage.",
        ),
        (
            "Indoor mantel",
            "Sash tied around black candle on mantel",
            "Create one wide front-angle photograph of the exact sash tied in a simple knot around the body of a lighted "
            "cylindrical black candle standing upright on a fireplace mantel and close to the wall. Do not tie the sash "
            "into a bow. Both full-length embroidered tails drape down over the mantel edge, fully visible and at the "
            "exact source scale. Style the mantel with black taper candles, dried pampas grass, and small white fabric "
            "ghost ornaments. Use cozy warm indoor light, soft shadows, and sharp unchanged embroidery detail.",
        ),
        (
            "Color swatch flat lay",
            "Three neutral linen sash colorways on wooden table",
            "Create one top-down flat lay photograph of exactly three identical sashes placed diagonally on a neutral "
            "wooden table. Use three different neutral linen base colors, one per sash, while preserving the exact same "
            "physical dimensions, tail width, pointed ends, knot style, border and seam construction, embroidery design, "
            "embroidery placement and scale, source lettering, pattern colors, and raised hand-stitched texture. Scatter "
            "a few small dried autumn leaves and small Halloween ornaments around them. Use soft natural light and sharp "
            "focus for a clean color comparison. This is one single-scene photograph, not a collage or grid.",
        ),
        (
            "Styled close-up",
            "Bottom-center sash on dried autumn wreath",
            "Create one close-up photograph of the exact sash tied at the bottom center, exactly at 6 o'clock, of a "
            "wreath made from dried orange and burgundy autumn leaves with small fabric ghost ornaments tucked into the "
            "foliage. Keep the Halloween motif on the same left tail and the exact source text on the same right tail. "
            "The knot sits on the lower rim and both full-length tails hang completely below the wreath without "
            "overlapping its body. Use warm afternoon light and crisp embroidery focus.",
        ),
        (
            "Hands tying sash",
            "Hands tying bottom-center sash above mantel",
            "Create one standalone lifestyle photograph of two anatomically correct hands tying the exact sash in a "
            "simple knot, never a bow, onto the bottom rim of a dark twig wreath at exactly 6 o'clock. The wreath is "
            "mounted flat on the wall above a rustic mantel with a hidden hook and no visible gap. Both full-length "
            "tails fall straight down below the wreath without overlapping its body. Style the mantel with small orange "
            "and cream pumpkins, muted burgundy dried eucalyptus, and lit pillar candles on brass holders. Use soft warm "
            "interior light, shallow depth of field, and sharp focus on the hands and unchanged embroidery.",
        ),
        (
            "Gift box",
            "Sash folded in premium cream gift box",
            "Create one overhead unboxing photograph of the exact sash neatly folded inside an open cream gift box lined "
            "with white tissue paper. Display both embroidered tails side by side facing upward. Curl a burnt-orange "
            "grosgrain ribbon loosely around the sash and place one small real mini pumpkin in a corner. Use bright soft "
            "daylight on a light neutral surface for a premium handmade gift presentation.",
        ),
        (
            "Basket versatility",
            "Sash tied around pumpkin basket handle",
            "Create one cozy lifestyle photograph of the exact sash tied in a neat simple knot around the handle of a "
            "natural woven basket filled with orange and white mini pumpkins. Place the basket on a wooden floor beside "
            "a Halloween-styled front door. Both full-length embroidered tails drape down the basket side, fully visible "
            "and correctly scaled. Use soft warm daylight, a farmhouse Halloween atmosphere, and sharp embroidery focus.",
        ),
        (
            "Pumpkin display",
            "Sash tied around cream heirloom pumpkin stem",
            "Create one wide, slightly oblique photograph of the exact sash tied in a simple knot, never a bow, around "
            "the stem of one large cream-colored heirloom pumpkin. Both full-length embroidered tails hang clearly down "
            "the sides of the pumpkin at the exact source scale. Place the pumpkin on a dark wooden table with black "
            "candles in brass holders, delicate faux cobwebs, and scattered dried autumn leaves. Use soft dim warm "
            "candlelight against a dark wall for an elegant slightly spooky Halloween atmosphere, with sharp focus on "
            "the unchanged sash embroidery.",
        ),
        (
            "Front porch",
            "Bottom-center wreath sash on Halloween front door",
            "Create one frontal wide-angle photograph of a Halloween-styled front door. Tie the exact sash at the bottom "
            "center, exactly at 6 o'clock, of a small maple-leaf and miniature-pumpkin wreath mounted flat against the "
            "door with a hidden hook and no visible gap. The knot sits on the lower rim and both full-length tail ends "
            "hang straight down well below the wreath, flat against the door and never overlapping the wreath body. "
            "Style the porch with a stack of vintage orange and white pumpkins and one tasteful Halloween animal statue. "
            "Keep the sash embroidery clearly focused.",
        ),
        (
            "Staircase versatility",
            "Sash tied around dark wooden banister post",
            "Create one lifestyle photograph of the exact sash tied in a soft simple knot around a dark wooden staircase "
            "banister post. Both full-length embroidered tails drape naturally down along the railing, fully visible and "
            "correctly scaled. Decorate the staircase with an autumn-leaf and mini-pumpkin garland plus restrained warm "
            "string lights. Use a cozy Halloween interior, soft evening light, and sharp focus on the unchanged "
            "embroidery, linen weave, seams, source lettering, and thread colors.",
        ),
    ),
}


PRODUCT_SHOT_RULES["wreath_sash"] = {
    "display_name": "Wreath Sash",
    "aliases": (
        "Wreath Sash",
        "autumn wreath sash",
        "fall wreath sash",
        "embroidered wreath sash",
        "personalized wreath sash",
    ),
    "lock": (
        "the main product must remain the exact same handmade embroidered fabric wreath sash from the source image, "
        "with the same long two-tail sash construction, top knot or tie shape, pointed tail ends, linen fabric color "
        "and weave, tail length and width, embroidery motif, initial or name placement, thread colors, raised stitch "
        "texture, proportions, drape, and premium handmade identity; keep the motif on the same tail and the lettering "
        "on the same tail as the source, preserve every readable source character exactly, and never turn the sash into "
        "a hair bow, bouquet ribbon, banner, scarf, bag, pillow, or printed decoration"
    ),
    "shots": (
        (
            "Wreath hero",
            "Full wreath on bright front door",
            "Tie the exact embroidered wreath sash naturally at the top of a lush green wreath on a bright clean front "
            "door. Show the whole wreath and both pointed sash tails, with the complete embroidery and source lettering "
            "facing the camera. Match decor to the source season: restrained pumpkins, friendly ghosts, bats, and orange "
            "accents for Halloween; maple leaves, mini pumpkins, wheat, and warm fall accents for Autumn. Use clear white "
            "daylight without a dark or yellow cast and keep the sash as the focal product.",
        ),
        (
            "Product close-up",
            "Close front view tied on wreath",
            "Create a close front-facing product photo of the exact sash tied on a green wreath, filling 70-80 percent "
            "of the square frame. Keep the top knot, two long tails, pointed ends, embroidery motif, initial or name, linen "
            "weave, and raised stitches fully visible and unchanged. Use soft white outdoor shade light and only minimal "
            "seasonal decor around the outer wreath edge.",
        ),
        (
            "Indoor display",
            "Wreath sash on a bright interior wall",
            "Hang the wreath with the exact tied sash on a white or pale wall above a light console table. Add a few small "
            "season-matched decorations on the table while keeping the room bright, airy, uncluttered, and premium. Shoot "
            "straight on so both sash tails hang naturally and the source embroidery remains sharp and unobstructed.",
        ),
        (
            "Porch lifestyle",
            "Wreath on a bright decorated porch",
            "Show the exact wreath sash in real use on a front-door wreath within a bright porch scene. Add two or three "
            "small pumpkins and restrained seasonal accents near the doorway, using Halloween details only for Halloween "
            "sources and fall foliage only for Autumn sources. Use clean daylight in open shade, subtle background blur, "
            "and correct real-world sash scale.",
        ),
        (
            "Flat lay",
            "Untied sash on white wood table",
            "Lay the exact wreath sash untied and fully extended on a white wood-grain table so viewers can inspect its "
            "two-tail construction, pointed ends, fabric width, embroidery placement, and overall length. Arrange the two "
            "tails neatly without folding over the design. Add a small wreath section, thread spool, and two mini seasonal "
            "props at the edges. Shoot top-down in bright even white daylight.",
        ),
        (
            "Hands lifestyle",
            "Hands tying sash onto wreath",
            "Show natural adult hands carefully tying the exact sash around the top of a green wreath. The knot must be "
            "physically realistic, both pointed tails must remain visible, and hands must not cover the embroidered motif "
            "or source lettering. Use bright natural window light or outdoor shade, correct anatomy, and restrained decor "
            "matching the source season.",
        ),
        (
            "Personalized pair",
            "Two wreaths with coordinated sash variants",
            "Display two matching green wreaths side by side, each using the same exact sash construction and embroidery "
            "layout as the source. If the source visibly includes a personalized initial or name, the second sash may use "
            "a different plausible initial in the same lettering style and location; otherwise do not invent text. Keep "
            "the source color palette, motifs, tail proportions, and handmade texture consistent under bright white light.",
        ),
        (
            "Gift presentation",
            "Sash folded in an open gift box",
            "Place the exact wreath sash neatly folded inside an open light-colored gift box, with the embroidered motif "
            "and source lettering facing upward and both pointed ends still identifiable. Add white tissue paper, a narrow "
            "season-matched ribbon, one mini pumpkin or autumn leaf cluster, and no readable gift tag. Use clean bright "
            "natural light and an uncluttered Etsy gift presentation.",
        ),
        (
            "Craft process",
            "Woman embroidering matching sash fabric",
            "Show a woman at a clean craft table hand-embroidering the exact source motif onto linen matching the sash, "
            "held in a small round embroidery hoop. One hand supports the hoop and the other uses a realistically threaded "
            "needle at the correct stitch position. Place the completed exact sash beside the hoop with its two tails and "
            "pointed ends visible. Add matching thread skeins, small scissors, and soft white window light.",
        ),
        (
            "Process collage",
            "Four-panel sash making process",
            "Create one clean square 2x2 collage: selecting linen matching the source sash; cutting the two long pointed "
            "tails; hand-embroidering the exact motif and lettering with a threaded needle in a hoop; and the completed "
            "exact sash tied on a wreath. Preserve the source design, proportions, thread colors, fabric texture, and "
            "seasonal identity throughout all four panels.",
        ),
        (
            "Detail collage",
            "Four close-ups of motif lettering knot and fabric",
            "Create one square 2x2 macro collage showing four exact product details: raised embroidery and stitch direction, "
            "the source initial or name lettering, linen weave and pointed tail edge finish, and the tied knot with natural "
            "drape. Use bright soft white light, true source colors, and sharp premium handmade detail. Do not move, "
            "simplify, replace, or redesign any source element.",
        ),
        (
            "Seasonal entryway",
            "Wreath sash above a bright console vignette",
            "Create a premium entryway hero photo with the exact sash tied to a wreath above a light console. Style a few "
            "small props matching the card season, such as friendly Halloween ghosts and pumpkins or Autumn leaves and "
            "wheat, while leaving generous negative space. Use clear airy daylight, keep the full sash unobstructed, and "
            "preserve its exact knot, tails, motif, lettering, colors, scale, and hand-embroidered texture.",
        ),
    ),
}


PRODUCT_SHOT_RULES["christmas_banner"] = {
    "display_name": "Christmas Banner",
    "aliases": (
        "Christmas Banner",
        "christmas banner",
        "Christmas Fabric Banner",
        "christmas fabric banner",
        "Christmas Babric Banner",
        "christmas babric banner",
        "Christmas Linen Banner",
        "christmas linen banner",
        "Christmas Embroidered Banner",
        "christmas embroidered banner",
        "Christmas Wall Banner",
        "christmas wall banner",
        "Christmas Wall Hanging",
        "christmas wall hanging",
        "Christmas Pennant",
        "christmas pennant",
        "Noel Banner",
        "noel banner",
        "Xmas Banner",
        "xmas banner",
        "banner christmas",
        "fabric banner christmas",
        "linen banner christmas",
    ),
    "target_count": 13,
    "allow_planned_multi_panel_shots": True,
    "allow_planned_prop_text": True,
    "lock": (
        "the main product must remain the exact same small handmade Christmas linen fabric wall banner from the source "
        "image, with the same banner silhouette, lower edge shape, wooden rod, hanging cord, fabric material and color, "
        "seams, embroidery motif and readable source lettering, embroidery placement and scale, thread colors, raised "
        "hand-stitch texture, linen weave, natural wrinkles, proportions, and premium handmade identity; never redesign "
        "the embroidery, change its physical construction, enlarge it unnaturally, or turn it into another product"
    ),
    "shots": (
        (
            "Door hook lifestyle",
            "Small banner hanging from child-room door hook",
            _christmas_banner_brief(
                "hang the exact banner naturally from a clearly visible hook on a child-room door. Frame the complete "
                "product and part of the door from a 20-30 degree angle, close enough to prioritize the product. Use soft "
                "clean white daylight with no yellow cast. Hang one tasteful Merry Christmas garland above it; inside the "
                "room show a small fresh Christmas tree and a few wrapped gifts softly blurred. Keep the banner "
                "realistically small relative to the door and preserve its complete rod, cord, shape, source embroidery, "
                "readable source lettering, and handmade linen texture."
            ),
        ),
        (
            "Nursery crib wall",
            "Small banner centered above Christmas-decorated crib",
            _christmas_banner_brief(
                "hang the exact banner from a small visible wooden wall hook at the center above a baby crib. Photograph "
                "straight-on or from a 30-degree front angle with close product-focused framing and bright even natural "
                "white light across the banner and crib bedding. Add a restrained Merry Christmas garland above the "
                "banner, one small reindeer cushion, one cute gnome, and refined nursery Christmas decor. The banner must "
                "look very small relative to the crib and must never be enlarged."
            ),
        ),
        (
            "Entryway lifestyle",
            "Small banner above white or gray wood console",
            _christmas_banner_brief(
                "hang the exact small banner from a visible wall hook in a home entryway above a compact white or gray "
                "wood-grain console. Shoot from a 45-60 degree angle, close enough to prioritize the banner while showing "
                "realistic use. Use clean natural white light without yellow cast. Style the console with one vase of "
                "fresh evergreen branches or one tiny fresh Christmas tree, one white candle, and a few small gnomes. "
                "Keep the banner realistically small relative to the entryway."
            ),
        ),
        (
            "Christmas mantle",
            "Small banner above or on bright fireplace mantle",
            _christmas_banner_brief(
                "hang the exact banner from a visible hook above or on the front of a fireplace mantle as the clear main "
                "subject. Shoot straight-on or from a gentle three-quarter angle in bright white-balanced daylight with "
                "no yellow cast. Add a thin evergreen garland, a Merry Christmas bunting, a few miniature Christmas "
                "stockings, and several pine cones in a balanced uncluttered arrangement. Keep the banner physically "
                "small, close enough to inspect, fully visible, and never enlarged."
            ),
        ),
        (
            "Colorway flat lay",
            "Three or four personalized Christmas banner colorways",
            _christmas_banner_brief(
                "create a 90-degree flat lay of three or four banners of the exact same source style arranged in a clean "
                "row or fan. If personalized names are visibly part of the source design, use different plausible names "
                "while preserving the exact lettering position, scale, stitch style, motif, thread colors, rod, cord, "
                "seams, and shape. Only the linen base color may differ. Use even white daylight and add fresh evergreen "
                "sprigs with small pine cones and a few dried orange slices only around the frame edges."
            ),
        ),
        (
            "Detail collage",
            "Four-panel embroidery rod and hanging-cord details",
            _christmas_banner_brief(
                "create one square 2x2 collage containing exactly four macro photographs of the same source banner: one "
                "close detail of the raised hand embroidery, a second close detail of another embroidered section or "
                "readable source lettering, a close detail of the wooden hanging rod and top seam, and a close detail of "
                "the hanging-cord attachment. Match the source exactly and clearly show genuine hand-stitched thread "
                "relief, individual stitch direction, and linen fibers, never printing or machine-flat embroidery."
            ),
        ),
        (
            "Christmas tabletop",
            "Banner flat on white wood with card evergreen and gnome",
            _christmas_banner_brief(
                "lay the exact banner flat on a white wood-grain table with the complete rod and hanging cord neatly "
                "visible. Shoot top-down at 90 degrees in bright clean white daylight with no yellow cast. Add two fresh "
                "evergreen sprigs with pine cones, one elegant Merry Christmas card, and one small cute gnome, leaving "
                "generous negative space and never covering the source embroidery or lettering."
            ),
        ),
        (
            "Bright shelf mantle",
            "Banner above light shelf with evergreen vase plush Santa and candy",
            _christmas_banner_brief(
                "hang the exact banner from a visible hook above a light wooden shelf or mini mantle while keeping it at "
                "the center of the composition. Shoot straight-on or at a slight 15-degree angle in bright white light "
                "that also illuminates the decor below. Style the shelf with one vase of fresh evergreen branches, one "
                "small plush Santa Claus figure, and one plate of colorful Christmas candy. Keep every prop secondary, "
                "use Christmas decor only with no pumpkins or ghosts, and preserve crisp raised hand stitches and the "
                "exact source design."
            ),
        ),
        (
            "Hand-held display",
            "Two hands holding banner before elegant Christmas tree",
            _christmas_banner_brief(
                "show two anatomically natural adult hands holding the hanging cord so the exact banner floats naturally "
                "in a Christmas-decorated room. Use a straight-on close-medium composition and soft white light with no "
                "yellow cast. Behind it place an elegant fresh Christmas tree and softly blurred wrapped gifts. Keep the "
                "banner sharply prominent; hands must not cover the rod, product shape, embroidery, or source lettering."
            ),
        ),
        (
            "Gift presentation",
            "Banner beside open gift box and Happy Christmas tag",
            _christmas_banner_brief(
                "place the exact banner beside an open premium gift box or Christmas-patterned wrapping paper with the "
                "personalized name and embroidery facing the camera. Shoot from 45 degrees overhead in bright high-key "
                "white light. Add one thin deep-red or forest-green ribbon, one small tag bearing the exact words Happy "
                "Christmas, and one evergreen sprig. Do not add any other readable text, and keep the complete banner, "
                "rod, cord, source lettering, and embroidery unobstructed."
            ),
        ),
        (
            "Hand embroidery process",
            "Woman hand-stitching the exact banner motif",
            _christmas_banner_brief(
                "show a woman seated at a clean handmade craft table, one natural hand holding a round embroidery hoop "
                "and the other carefully hand-stitching the exact source motif onto linen matching the banner fabric "
                "color. Use a realistically threaded needle contacting the correct stitch position. Place small scissors, "
                "matching thread skeins, folded linen, and the completed source banner nearby. Use beautiful white window "
                "light and restrained Christmas workshop decor; hands and needle placement must be anatomically correct."
            ),
        ),
        (
            "Baby lifestyle",
            "Baby seated on floor holding small Christmas banner",
            _christmas_banner_brief(
                "preserve the banner design exactly and show a baby seated naturally on the floor holding the exact small "
                "banner with its embroidered front facing the camera. Shoot straight-on in a close-medium composition "
                "with soft white light and no yellow cast in a beautifully decorated Christmas room. The banner must "
                "remain small relative to the baby, must not cover the child, and must retain its rod, cord, source "
                "lettering, exact motif, proportions, and clearly raised hand-embroidered texture."
            ),
        ),
        (
            "Wardrobe or room door",
            "Small banner below a miniature Christmas wreath",
            _christmas_banner_brief(
                "hang the exact banner naturally from a visible hook on a wardrobe door or room door, directly below a "
                "small Christmas wreath. Shoot nearly straight-on in even clean white daylight. Add elegant eye-catching "
                "Christmas decor around the doorway without clutter or yellow light. Keep the complete cord, wooden rod, "
                "product shape, embroidery, and source lettering unobstructed, and keep the banner realistically small "
                "relative to the door or wardrobe."
            ),
        ),
    ),
}


PRODUCT_SHOT_RULES["pn_ornament"] = {
    "display_name": "PN Ornament",
    "aliases": (
        "PN Ornament",
        "PN Ornaments",
        "Punch Needle Ornament",
        "Punch Needle Ornaments",
        "Punch Needle Christmas Ornament",
        "Christmas Punch Needle Ornament",
        "Punch Needle Linen Ornament",
        "Embroidered Punch Needle Ornament",
        "PN Christmas Ornament",
        "PN Xmas Ornament",
        "ornament punch needle",
        "ornament pn",
        "do treo punch needle",
    ),
    "target_count": 14,
    "lock": (
        "the main product must remain the exact same small handmade Christmas linen Punch Needle ornament from the "
        "source, preserving its silhouette, frame, metal clasp, hanging cord, linen, motif, colors, placement, scale, "
        "and visibly thick raised handmade wool loop-pile texture; never substitute ordinary flat hand embroidery, "
        "machine embroidery, print, paint, or a different ornament construction"
    ),
    "shots": (
        (
            "White wood flat lay",
            "Punch Needle ornament on white wood table with pine branch",
            _pn_ornament_brief(
                "lay the exact ornament flat at the center of a white wood-grain tabletop, with its hanging cord curving "
                "naturally to one side. Shoot top-down at exactly 90 degrees in even white overhead daylight. Place one "
                "small evergreen branch in the lower-left or lower-right corner, several white wooden snowflakes, and a "
                "restrained strand of softly blurred warm fairy lights. Keep the composition airy and make the thick "
                "raised punch-needle wool loops and individual yarn fibers unmistakable."
            ),
        ),
        (
            "Christmas tree branch",
            "Punch Needle ornament hanging at center of evergreen branch",
            _pn_ornament_brief(
                "hang the exact ornament at the center of a fresh Christmas tree branch, clearly separated from the pine "
                "needles. Shoot at ornament height from a 30-45 degree angle in soft white-balanced daylight. Add a few "
                "baubles and softly blurred fairy lights behind it without yellowing the linen or hiding the hanging cord, "
                "frame, clasp, motif, or tactile punch-needle loops."
            ),
        ),
        (
            "Gift box",
            "Punch Needle ornament in open Christmas gift box",
            _pn_ornament_brief(
                "place the exact ornament inside one open Christmas-toned gift box lined with clean tissue paper. Shoot "
                "from 35-45 degrees in bright clean luxurious white daylight. Add deep red or champagne ribbon, small pine "
                "sprigs, dried orange slices, cinnamon, and softly blurred gift boxes behind. Keep the complete frame, "
                "clasp, cord, linen face, and raised punch-needle motif uncovered."
            ),
        ),
        (
            "Minimal Christmas table",
            "Punch Needle ornament with low candles and pastel baubles",
            _pn_ornament_brief(
                "place the exact ornament lying flat or standing securely at the center of a minimal Christmas tabletop. "
                "Shoot from a frontal 45-degree angle in soft even white light, never candle-yellow. Style with two low "
                "neutral candles, a few small pinecones, pastel matte baubles, and one evergreen sprig. Keep every prop "
                "secondary and the thick handmade punch-needle loop texture crisp."
            ),
        ),
        (
            "Christmas card flat lay",
            "Punch Needle ornament beside neutral Merry Christmas card",
            _pn_ornament_brief(
                "place the exact ornament as the focal point beside one neutral greeting card whose only readable prop "
                "text is Merry Christmas, on a white wood-grain tabletop. Shoot top-down from 75-90 degrees in clean even "
                "white daylight. Add a thin ribbon, one small gnome, and one small evergreen branch in the upper-left "
                "corner. Keep the card separate and never cover the ornament or add other wording."
            ),
        ),
        (
            "Baby clothing shelf",
            "Punch Needle ornament beside folded baby outfits near window",
            _pn_ornament_brief(
                "place the exact ornament on a white wood-grain shelf or tabletop beside several neatly folded baby "
                "outfits near a bright window. Shoot top-down or at 45 degrees in soft clear white daylight. Use a softly "
                "blurred Christmas background with one small gnome teddy, a Christmas stocking, and a tiny reindeer figure. "
                "Keep the ornament small relative to the clothes and preserve its tactile punch-needle motif."
            ),
        ),
        (
            "Punch Needle process",
            "Woman punch-needling exact ornament motif in round hoop",
            _pn_ornament_brief(
                "show a woman seated at a clean handmade craft table, carefully creating the exact source motif on linen "
                "matching the ornament color inside a round wooden embroidery hoop. One anatomically natural hand supports "
                "the hoop and the other holds a realistic large wooden-handled punch needle at the true stitch position, "
                "with matching wool yarn correctly threaded through the tool and trailing from its rear. Place the finished "
                "source ornament, matching yarn, scissors, and folded linen nearby. Focus on the hands, hoop, fibers, and "
                "dense raised punch-needle loops in soft white window daylight."
            ),
        ),
        (
            "Four-panel making process",
            "Fabric selection sketch Punch Needle stitching and finished ornament",
            _pn_ornament_brief(
                "create one square 1:1 four-panel process collage. Panel 1: a hand selects linen matching the exact source "
                "color from several fabric rolls. Panel 2: the exact motif is lightly sketched but not stitched on a larger "
                "linen piece. Panel 3: the motif is being built in color with a correctly threaded punch needle inside a "
                "round hoop, one hand holding the hoop and the other working at a realistic contact point, with matching "
                "wool yarn nearby. Panel 4: the completed ornament matches the exact source silhouette, frame, clasp, cord, "
                "linen, motif, placement, scale, colors, and thick loop-pile texture. Use soft clean light and Christmas mood."
            ),
        ),
        (
            "Personalized group",
            "Three to five Punch Needle ornaments in row or fan",
            _pn_ornament_brief(
                "arrange three to five ornaments of the exact same physical style in a horizontal row or gentle fan on a "
                "white wood-grain tabletop. If the source visibly contains a personalized name, use a different plausible "
                "name on each while preserving the exact lettering position, scale, punch-needle treatment, motif, frame, "
                "clasp, cord, and colors; if the source has no name, invent no wording. Shoot top-down at 90 degrees or from "
                "a light 60-degree angle in very even white daylight. Add one thin pine sprig, dried orange slices, holly, "
                "and a softly blurred Christmas background."
            ),
        ),
        (
            "Gift wrapping",
            "Punch Needle ornament beside neat Noel wrapping setup",
            _pn_ornament_brief(
                "place the exact ornament beside a neat Noel gift-wrapping setup. Shoot top-down from 60-75 degrees or at "
                "a slight angle in crisp white daylight. Include tasteful Christmas wrapping paper, scissors, ribbon, and "
                "one plain textless gift tag. Keep the ornament embroidery, frame, clasp, linen weave, and hanging cord "
                "fully visible and sharply detailed."
            ),
        ),
        (
            "Mini tree lifestyle",
            "Punch Needle ornament foreground with fresh mini tree",
            _pn_ornament_brief(
                "place the exact ornament prominently in the foreground with a fresh mini Christmas tree in the left or "
                "right background. Shoot straight-on or from a 30-degree angle in bright white daylight. Add two or three "
                "small bells, red berries, and a restrained amount of softly blurred fairy light. Keep the small ornament "
                "as the sharper subject and reveal the thick punch-needle wool loops clearly."
            ),
        ),
        (
            "Baby Christmas lifestyle",
            "One-year-old baby holding small Punch Needle ornament",
            _pn_ornament_brief(
                "show a roughly one-year-old baby wearing a Christmas outfit and Santa hat, seated beside a decorated tree "
                "and smiling naturally while holding the exact ornament. Use soft white-balanced daylight. Keep the ornament "
                "genuinely small relative to the baby's hand and body, never enlarged, with its embroidered face turned "
                "toward the camera and unobstructed. Keep hands anatomically natural and the raised wool loops sharp."
            ),
        ),
        (
            "Books lifestyle",
            "Punch Needle ornament resting on pale hardcover books",
            _pn_ornament_brief(
                "rest the exact ornament against one or two white or pale neutral hardcover books for a refined Christmas "
                "lifestyle scene. Shoot from 30-45 degrees in soft clean white daylight reflecting from the paper. Add one "
                "frosted glass bauble, one evergreen sprig, dried orange slices, and cinnamon. Keep the ornament dominant, "
                "sharp, correctly scaled, and free of beige or yellow color grading."
            ),
        ),
        (
            "Four-panel macro proof",
            "Punch Needle loops linen frame and metal clasp close-ups",
            _pn_ornament_brief(
                "create one square 1:1 collage containing exactly four macro close-up photographs of the same source "
                "ornament: panel 1 shows dense raised punch-needle wool loops and individual fibers; panel 2 shows linen "
                "weave and the transition between loop pile and fabric; panel 3 shows the wooden hoop or frame material and "
                "edge finish; panel 4 shows the metal clasp or fastener and hanging-cord attachment. Every panel must match "
                "the original product exactly and prove genuine handmade Punch Needle work."
            ),
        ),
    ),
}


PRODUCT_SHOT_RULES["jewelry_box"] = {
    "display_name": "Jewelry Box",
    "aliases": (
        "Jewelry Box",
        "Jewery Box",
        "Jewellery Box",
        "jewelry boxes",
        "jewery boxes",
        "jewellery boxes",
        "linen jewelry box",
        "linen jewellery box",
        "embroidered jewelry box",
        "embroidered jewellery box",
        "hand embroidered jewelry box",
        "personalized jewelry box",
        "personalised jewellery box",
        "wedding jewelry box",
        "bridesmaid jewelry box",
        "travel jewelry box",
        "jewelry case",
        "jewellery case",
        "jewelry organizer box",
        "hop dung trang suc",
        "hop trang suc",
    ),
    "target_count": 12,
    "lock": (
        "the complete source collection of small rounded-rectangle silver-framed white linen jewelry boxes must appear "
        "together in every image, with each exact original hand-embroidered motif kept on its corresponding box; every "
        "open product box must have exactly two shallow side-by-side rectangular compartments separated by one straight "
        "front-to-back divider, with a plain flat inner lid and no other interior structures"
    ),
    "shots": (
        (
            "Collection hero",
            "Complete embroidered jewelry-box collection in two balanced rows",
            _jewelry_box_brief(
                "arrange the complete source collection in two balanced rows on a white or light-wood tabletop. Keep "
                "every box closed with every embroidered lid facing the camera, and show every distinct source design, "
                "silver frame, and front clasp clearly. Shoot nearly straight-on with a subtle 15-degree angle. Add only "
                "one restrained white flower sprig and a few tiny jewelry pieces at the outer edges."
            ),
        ),
        (
            "Complete flat lay",
            "All original box designs in a clean overhead grid or fan",
            _jewelry_box_brief(
                "arrange the complete source collection in a clean grid or gentle fan on a white wood-grain surface. "
                "Shoot top-down at 90 degrees. Keep every box fully visible and separated so no lid overlaps another "
                "box's embroidery. Show all original motifs together, sharp and unobstructed."
            ),
        ),
        (
            "Nine personalized boxes",
            "Nine exact source-design boxes personalized with the requested names",
            _jewelry_box_brief(
                "create exactly nine boxes arranged in a precise 3x3 grid on a bright neutral surface. Use the exact "
                "names Anita, Mom, Alice, Maria, Chloe, Jessie, Crystal, Eloise, and Jenna, one name per box and no other "
                "names. Preserve and distribute only exact complete motifs from the source collection, including every "
                "distinct source motif at least once; repeat a complete unchanged source motif only if needed to reach "
                "nine boxes. Shoot top-down at 90 degrees with every embroidered name and motif legible."
            ),
        ),
        (
            "Two-compartment function",
            "Two open boxes with exactly two compartments among the complete collection",
            _jewelry_box_brief(
                "style the complete collection on a bright dressing table. Open exactly two foreground product boxes "
                "to about 100-110 degrees. In each open box show exactly one straight front-to-back center divider and "
                "exactly two side-by-side rectangular compartments: place one ring and one pair of earrings loose in the "
                "left compartment, and one neatly coiled fine necklace loose in the right compartment. Keep both inner "
                "lids plain and flat. Arrange every remaining source box closed behind them with all embroidered designs "
                "facing the camera. Shoot from 45 degrees overhead so both complete two-compartment interiors are obvious."
            ),
        ),
        (
            "Close collection detail",
            "Macro foreground designs with the full source collection behind",
            _jewelry_box_brief(
                "layer the complete source collection on a clean tabletop. Place three closed boxes in the foreground for "
                "a close product view of raised embroidery, linen weave, personalized stitching, silver rim, and clasp. "
                "Arrange all remaining source boxes behind them so every original design remains identifiable. Shoot from "
                "a low 25-35 degree angle with enough depth of field to retain the whole collection."
            ),
        ),
        (
            "Hand embroidery process",
            "Artisan stitching one exact source motif beside all completed boxes",
            _jewelry_box_brief(
                "show a woman hand-embroidering one exact motif from the source collection onto matching white linen in "
                "a round wooden hoop. One natural hand supports the hoop while the other holds a realistically threaded "
                "needle contacting the correct stitch position; the thread color matches that exact source detail. Place "
                "the complete set of finished source boxes together on the same table with all embroidered lids visible, "
                "plus neatly arranged matching floss and small embroidery scissors."
            ),
        ),
        (
            "Two-compartment assembly",
            "Artisan fitting embroidered lid beside exact two-compartment insert",
            _jewelry_box_brief(
                "show an artisan fitting an already embroidered white linen panel into one silver metal lid. Beside it, "
                "show the matching box base during assembly with exactly one straight front-to-back divider creating "
                "exactly two open rectangular compartments, left and right, and no other interior structure. Arrange the "
                "complete collection of finished source boxes in a visible row on the same clean craft table. Add only "
                "small scissors, matching thread, and tidy hand tools in bright white window daylight."
            ),
        ),
        (
            "Bridesmaid gift collection",
            "Complete personalized collection on a bright wedding preparation table",
            _jewelry_box_brief(
                "arrange the complete personalized collection in balanced rows on a bright wedding preparation table. "
                "Keep each exact original motif paired with its box and each embroidered name clear. Add restrained silk "
                "ribbon and white wedding flowers, with pastel bridesmaid dresses softly blurred in the background. Shoot "
                "from a professional 35-45 degree angle without covering any name or embroidery."
            ),
        ),
        (
            "Bride giving bridesmaid gift",
            "Bride presents one box while the complete collection remains visible",
            _jewelry_box_brief(
                "show a bride handing one closed personalized box to a bridesmaid, with the embroidered lid and name "
                "facing the camera in the foreground. Arrange the complete remaining source collection together on a gift "
                "table behind them so every other distinct design remains visible. Frame natural hands and partial attire "
                "rather than faces, using clean white daylight and a refined wedding setting."
            ),
        ),
        (
            "Daily two-compartment use",
            "Woman selecting earrings from exact two-compartment boxes",
            _jewelry_box_brief(
                "arrange the complete collection on a bright dressing table and open exactly two foreground boxes. Each "
                "open base has exactly one straight front-to-back divider and exactly two uninterrupted side-by-side "
                "rectangular compartments. Place rings and earrings loose in the left compartments and a fine necklace "
                "or slim bracelet loose in the right compartments. Show a woman's natural hand taking earrings directly "
                "from one left compartment. Keep both inner lids plain and every remaining box closed with its exact source "
                "embroidery facing outward. Shoot from 45-60 degrees overhead so the two-compartment geometry is explicit."
            ),
        ),
        (
            "Gift packaging collection",
            "All closed boxes in open cream presentation gift boxes",
            _jewelry_box_brief(
                "place every closed jewelry box from the source collection inside its own open cream presentation gift "
                "box lined with white tissue paper, then arrange all gift boxes together on one bright tabletop. Face every "
                "embroidered product lid and personalized name upward. Add restrained satin ribbon, baby's breath flowers, "
                "and blank white cards with no readable text. Shoot overhead from 75-90 degrees."
            ),
        ),
        (
            "Wedding flat lay",
            "Complete closed collection with wedding jewelry and veil",
            _jewelry_box_brief(
                "arrange the complete closed source collection in a premium wedding flat lay on a clean white surface. "
                "Show every different embroidered lid fully and preserve the exact box-to-design mapping. Place wedding "
                "rings, a white veil, white flowers, and pale silk ribbon only around the outer edges, never over a box. "
                "Shoot top-down at 90 degrees in bright white natural daylight."
            ),
        ),
    ),
}


PRODUCT_SHOT_RULES["napkin_set"] = {
    "display_name": "Napkin Set",
    "aliases": (
        "Napkin Set",
        "napkin set",
        "linen napkin set",
        "embroidered napkin set",
        "hand embroidered napkin set",
        "handmade napkin set",
        "dinner napkin set",
        "table napkin set",
        "set of 6 napkins",
        "set of six napkins",
        "six linen napkins",
        "embroidered napkins",
        "linen napkins",
        "fall napkins",
        "autumn napkins",
        "fall linen napkins",
        "autumn linen napkins",
        "khan an linen",
        "bo khan an",
        "bo 6 khan an",
    ),
    "target_count": 10,
    "lock": (
        "the main product must remain the exact same set of six handmade white linen dinner napkins from the source "
        "image, with the same linen weave, square proportions, hems, edge stitching, soft folds, and six distinct autumn "
        "hand-embroidered motifs; each original motif must remain on its own napkin with the exact source design, "
        "placement, scale, raised stitch texture, and thread colors, with no repeated, swapped, invented, printed, or "
        "machine-embroidered motif"
    ),
    "shots": (
        (
            "Plate setting",
            "Single embroidered napkin centered on white dinner plate",
            _napkin_set_brief(
                "fold one exact source napkin elegantly and place it in the center of a white ceramic dinner plate. "
                "Face its original embroidery toward the camera, fully visible and not hidden by a fold. Set the plate "
                "on a neutral linen placemat beside minimal silver flatware. Add one mini white pumpkin and a few small "
                "autumn leaves as restrained edge props. Shoot from a professional 45-degree overhead angle with gentle "
                "background blur and tack-sharp embroidery."
            ),
        ),
        (
            "Six-place table",
            "Wide dining table with one distinct napkin on each plate",
            _napkin_set_brief(
                "create a refined autumn dining table set for exactly six people, with exactly six place settings and "
                "one source napkin on each plate. Show all six distinct original embroidery motifs, one different motif "
                "per napkin, facing upward and visible. Use a light wood table, white tableware, clear glasses, silver "
                "flatware, and an airy centerpiece of mini white pumpkins, sparse autumn foliage, and small dried flowers. "
                "Shoot a balanced wide view from a slightly elevated 45-degree angle."
            ),
        ),
        (
            "Embroidery close-up",
            "Macro fan display showing all six original motifs",
            _napkin_set_brief(
                "stack and fan the six exact napkins in one continuous single-scene composition so every embroidered "
                "corner and all six different source motifs are visible together. Shoot close with macro product detail "
                "showing individual raised hand stitches, thread fibers, accurate colors, linen weave, hems, and edge "
                "stitching. Use a minimal light wood background and soft white side daylight. Keep enough depth of field "
                "for every motif to remain clear; do not create a collage or divided panels."
            ),
        ),
        (
            "Hand embroidery process",
            "Artisan stitching one exact motif in wooden hoop",
            _napkin_set_brief(
                "show an artisan hand-embroidering one exact autumn motif from the source onto matching white linen "
                "stretched in a round wooden hoop. One anatomically natural hand supports the hoop and the other holds "
                "a realistically threaded needle contacting the correct stitch position; the thread color matches that "
                "exact part of the motif. Place the completed set of six source napkins, small embroidery scissors, and "
                "matching thread skeins beside the hoop on a clean craft table. Shoot close at 45 degrees in soft white "
                "window daylight."
            ),
        ),
        (
            "Complete set flat lay",
            "Six-napkin fan flat lay with autumn accents",
            _napkin_set_brief(
                "arrange exactly six source napkins in a clean fan on a light wood table, revealing one complete distinct "
                "original embroidery motif on each napkin. Add only a few acorns, dried maple leaves, and one small "
                "baby's-breath stem around the outer edges without touching the embroidery. Shoot top-down at 90 degrees "
                "with even white daylight, generous negative space, and catalog-level clarity."
            ),
        ),
        (
            "Gift box",
            "Six embroidered napkins in premium open gift box",
            _napkin_set_brief(
                "fold exactly six source napkins neatly inside an open white premium gift box lined with white tissue. "
                "Arrange their embroidered corners facing upward so all six distinct original motifs remain visible. "
                "Place a loose olive-green or burgundy velvet ribbon, one blank unprinted gift tag, and a few acorns "
                "beside the napkins. Shoot from a 45-degree overhead angle in bright natural white light, emphasizing a "
                "luxurious handmade gift presentation."
            ),
        ),
        (
            "Table setting process",
            "Hands placing sixth napkin at autumn table",
            _napkin_set_brief(
                "capture natural adult hands gently placing one source napkin onto the final plate while setting an "
                "autumn dining table. The other five place settings already hold the other five napkins, producing "
                "exactly six napkins total with all six different original motifs. Crop out the person's face. Shoot near "
                "table height at 30-40 degrees in clean white window light, with sharp focus on the napkin being placed "
                "and no hands covering its embroidery."
            ),
        ),
        (
            "Buffet display",
            "Six folded napkins stacked beside white tableware",
            _napkin_set_brief(
                "fold the exact six napkins into a low, neat staggered stack on a light wood dining-room sideboard, "
                "deliberately exposing all six different embroidered corners. Place a small stack of white ceramic "
                "plates, clear glasses, and one small vase of sparse autumn foliage nearby. Shoot frontally from a slight "
                "angle, close enough for the napkins to dominate the frame under bright airy white daylight."
            ),
        ),
        (
            "Autumn porch brunch",
            "Six-place outdoor brunch with embroidered napkins",
            _napkin_set_brief(
                "create a bright autumn porch brunch for exactly six people, with one exact source napkin on each of six "
                "plates. Keep all six distinct original motifs facing upward and readable. Use a natural wood table, white "
                "ceramics, clear glasses, and one small restrained autumn floral vase. Photograph in open shade with clean "
                "white daylight, no golden sun cast, from a professional wide 45-degree angle while keeping the napkins "
                "visually prominent."
            ),
        ),
        (
            "Six-design comparison",
            "Aligned embroidered corners on white wood table",
            _napkin_set_brief(
                "fold all six exact napkins identically and arrange them in one slightly staggered horizontal row on a "
                "white wood-grain table, with each embroidered corner facing the camera for a clean comparison of all six "
                "different original motifs. Add only two mini pumpkins, a few acorns, and one olive branch at the frame "
                "edges. Shoot from 70-80 degrees above with even white daylight and a spacious premium Etsy catalog "
                "composition."
            ),
        ),
    ),
}


PRODUCT_SHOT_RULES["advent_calendar"] = {
    "display_name": "Advent Calendar",
    "aliases": (
        "Advent Calendar",
        "advent_calendar",
        "Christmas Advent Calendar",
        "Christmas Countdown Calendar",
        "Christmas Countdown Wall Hanging",
        "Embroidered Advent Calendar",
        "Hand Embroidered Advent Calendar",
        "Linen Advent Calendar",
        "Personalized Advent Calendar",
        "Personalised Advent Calendar",
        "Fabric Advent Calendar",
        "Wall Hanging Advent Calendar",
        "Pocket Advent Calendar",
        "Christmas Pocket Calendar",
        "advent countdown",
        "christmas countdown",
        "lich dem nguoc giang sinh",
        "lich giang sinh treo tuong",
        "lich advent vai linen",
        "lich advent theu tay",
    ),
    "target_count": 12,
    "allow_planned_multi_panel_shots": True,
    "lock": (
        "the main product must remain the exact same tall handmade linen Christmas wall-hanging advent countdown "
        "calendar from the source, preserving its exact pocket count and grid, every number in the exact source order, "
        "personalized wording and motifs, fabric and thread colors, raised hand embroidery, wooden dowel, hanging cord, "
        "knots, seams, dimensions, and construction; never mix designs from another calendar or convert it into a banner"
    ),
    "shots": (
        (
            "Front hero",
            "Complete advent calendar centered on bright Christmas wall",
            _advent_calendar_brief(
                "hang the complete exact calendar on a bright white wall in a refined Christmas living room. Shoot "
                "straight-on at product height and show the full hanging cord, wooden dowel, fabric body, every pocket, "
                "and the final row. Let the calendar fill about 65-75 percent of the square frame. Add restrained evergreen "
                "branches, softly blurred white fairy lights, and a few gift boxes below, while keeping every source "
                "number, personalized word, and embroidered motif clear and unobstructed."
            ),
        ),
        (
            "Tree lifestyle",
            "Advent calendar beside decorated fresh Christmas tree",
            _advent_calendar_brief(
                "hang the complete exact calendar flat against a light wall beside a real decorated Christmas tree. Shoot "
                "from a subtle 20-30 degree angle that reveals the lifestyle setting without changing the calendar's "
                "rectangular geometry. Keep the tree and gifts softly blurred in the background, use bright white window "
                "daylight, and make the calendar, pocket grid, numbers, lettering, and embroidery the sharpest subject."
            ),
        ),
        (
            "Mantel scene",
            "Advent calendar above a light Christmas mantel",
            _advent_calendar_brief(
                "hang the exact calendar flat on the wall above or immediately beside a pale fireplace mantel. Style the "
                "mantel with a thin evergreen garland, a few red or champagne baubles, small Christmas stockings, and low "
                "white candles that do not cast yellow light. Shoot straight-on or at a very light three-quarter angle, "
                "close enough to read the original pocket numbers and embroidery, with no prop covering the product."
            ),
        ),
        (
            "Children's room",
            "Advent calendar in bright Christmas children's room",
            _advent_calendar_brief(
                "hang the exact calendar securely on a clearly visible wall hook in a bright children's room, near a low "
                "wood shelf or chair. Add one small plush reindeer, one gnome, a mini tree, and a few gift boxes as secondary "
                "Christmas decor. Keep the calendar realistically scaled relative to the furniture and shoot straight-on "
                "or slightly angled in clean white daylight, with the complete calendar visible and sharp."
            ),
        ),
        (
            "Complete flat lay",
            "Full advent calendar flat on white wood surface",
            _advent_calendar_brief(
                "lay the complete calendar flat on a large white wood-grain surface without detaching its wooden dowel or "
                "hanging cord. Arrange the cord naturally above the product. Shoot top-down at exactly 90 degrees and fit "
                "the entire calendar inside the square frame, including every pocket and edge. Add one evergreen sprig, a "
                "few pinecones, dried orange slices, one candy cane, and a thin ribbon only around the outer margins, never "
                "over the original numbers, wording, pockets, or embroidery."
            ),
        ),
        (
            "Four-panel detail proof",
            "Embroidery pockets linen dowel and cord macro collage",
            _advent_calendar_brief(
                "create one square 1:1 collage divided into exactly four clean macro panels of this same source calendar. "
                "Panel 1 shows the exact upper embroidery, personalized name, or source phrase with raised hand stitches. "
                "Panel 2 shows the linen weave, individual thread fibers, and stitch direction. Panel 3 shows a small group "
                "of original numbered pockets with their exact numbers, borders, seams, and spacing. Panel 4 shows the "
                "wooden dowel, top fabric channel, cord, and tied knot construction. Do not invent or replace any detail."
            ),
        ),
        (
            "Hand embroidery process",
            "Artisan stitching exact advent calendar motif in round hoop",
            _advent_calendar_brief(
                "show a woman at a clean bright craft table hand-embroidering one exact motif or lettering fragment from "
                "the source calendar onto matching linen stretched in a round wooden hoop. One anatomically natural hand "
                "supports the hoop and the other holds a realistically threaded needle at the true stitch contact point; "
                "the thread color matches that exact source detail. Place the completed source calendar, matching floss, "
                "small scissors, a fabric ruler, and linen pieces nearby. Shoot close at 45 degrees in soft white window "
                "daylight, proving genuine hand stitching rather than print or machine embroidery."
            ),
        ),
        (
            "Filling a pocket",
            "Adult hand placing small Christmas gift into one pocket",
            _advent_calendar_brief(
                "capture a close lifestyle view of one natural adult hand gently placing one very small wrapped Christmas "
                "gift into a single pocket while the exact calendar hangs flat against the wall. Let the gift protrude only "
                "slightly and never cover that pocket's number or embroidery. Do not open, distort, or alter any other "
                "pocket. Focus sharply on the hand, exact number, seam, linen weave, and hand stitches while keeping enough "
                "of the full source design visible for clear product recognition."
            ),
        ),
        (
            "Child countdown",
            "Young child taking a surprise from advent pocket",
            _advent_calendar_brief(
                "show a young child naturally reaching for one small surprise in one pocket of the exact calendar, mounted "
                "at a safe realistic height in a bright Christmas room. Keep the child's body and hand from covering most "
                "of the product, and preserve the complete grid, every source number, lettering, and motif. Use clean white "
                "daylight with a tree and gifts softly blurred behind, keeping the calendar visually dominant."
            ),
        ),
        (
            "Family countdown",
            "Mother and child pointing to one advent pocket",
            _advent_calendar_brief(
                "create a realistic Etsy lifestyle scene of a mother seated beside her child as they point together at one "
                "pocket on the exact wall-mounted calendar. Frame their faces and bodies as secondary context and prevent "
                "their hands from obscuring the upper embroidery, personalized wording, or pocket rows. Use bright airy "
                "white-balanced natural daylight and restrained Christmas room decor."
            ),
        ),
        (
            "Gift-ready presentation",
            "Advent calendar carefully folded in open premium gift box",
            _advent_calendar_brief(
                "present the exact calendar carefully and realistically folded or loosely rolled inside an open cream or "
                "kraft gift box lined with white tissue, while revealing a substantial recognizable section of its exact "
                "upper embroidery and numbered pockets. Keep the wooden dowel attached unless the source construction "
                "visibly permits removal; if attached, fit it naturally beside the folded fabric inside the box. Add a deep "
                "red ribbon, one evergreen sprig, and one blank textless card. Shoot from 45 degrees above in bright white "
                "daylight for a premium handmade gift presentation."
            ),
        ),
        (
            "Entryway scene",
            "Advent calendar above bright Christmas console table",
            _advent_calendar_brief(
                "hang the complete exact calendar flat against a light entryway wall above a pale console table. Style the "
                "table with a mini fresh tree, a small bowl of Christmas ornaments, restrained evergreen garland, and a few "
                "gift boxes. Shoot a moderately wide professional view close enough to preserve readable source numbers, "
                "lettering, embroidery, linen texture, dowel, and cord. Use crisp winter-white daylight and keep the calendar "
                "as the centered focal point."
            ),
        ),
    ),
}


PRODUCT_SHOT_RULES["christmas_fabric_cross"] = {
    "display_name": "Christmas Fabric Cross",
    "aliases": (
        "Christmas Fabric Cross",
        "Christmas Fabric Crosses",
        "christmas_fabric_cross",
        "Christmas Linen Cross",
        "Christmas Embroidered Cross",
        "Christmas Cross Keepsake",
        "Christmas Soft Cross",
        "Christmas Hanging Fabric Cross",
        "Christmas Cross Ornament",
        "Noel Fabric Cross",
        "Xmas Fabric Cross",
        "Holiday Fabric Cross",
        "fabric cross christmas",
        "embroidered cross christmas",
        "thanh gia vai giang sinh",
        "thanh gia linen giang sinh",
        "thanh gia theu tay giang sinh",
    ),
    "target_count": 12,
    "allow_planned_multi_panel_shots": True,
    "lock": (
        "the main product must remain the exact same soft handmade Christmas fabric cross from the source, preserving "
        "its exact cross silhouette, proportions, fabric, soft volume, seams, embroidery or personalized wording, "
        "thread colors, raised hand stitches, hanging loop material, length, attachment position, and handmade identity"
    ),
    "shots": (
        (
            "Baby holding cross",
            "Baby gently holding exact fabric cross in Christmas nursery",
            _christmas_fabric_cross_brief(
                "show a baby relaxing in a bright neutral nursery or softly decorated home space with subtle Christmas "
                "touches, gently holding the exact cross with both hands. Keep the cross fully recognizable and facing the "
                "camera, with fingers positioned naturally around its edges rather than covering the embroidery, wording, "
                "or hanging loop. Use soft blankets, pale knitwear, delicate decor, clean white window daylight, and shallow "
                "depth of field so the cross is the emotional and visual focal point."
            ),
        ),
        (
            "Teddy nursery display",
            "Fabric cross upright against teddy bear with Christmas accents",
            _christmas_fabric_cross_brief(
                "position the exact cross upright, leaning gently against a soft neutral teddy bear on a cream wool blanket "
                "inside a bright Christmas nursery. Add only a few small matte ornaments, one evergreen sprig, and delicate "
                "botanical accents. Shoot close at a subtle 30-degree angle in clear airy white daylight with soft bokeh. "
                "Keep the teddy and props secondary and reveal the complete cross, loop, embroidery, seams, and texture."
            ),
        ),
        (
            "Crib mobile",
            "Fabric cross hanging from natural wood mobile above Christmas crib",
            _christmas_fabric_cross_brief(
                "hang the exact cross naturally from its original loop on a simple natural-wood mobile above a cozy neutral "
                "crib with cream bedding and a soft pastel throw. Decorate the bright nursery with sparse dried grass, a tiny "
                "evergreen accent, and restrained Christmas ornaments. Shoot at cross height in clean white side daylight, "
                "keeping the cross sharp and safely separated from the softly blurred crib background. Preserve realistic "
                "crib, mobile, loop, and product scale."
            ),
        ),
        (
            "Wreath doorway",
            "Fabric cross centered on Christmas wreath at light oak doorway",
            _christmas_fabric_cross_brief(
                "hang the exact cross by its original loop from one small nail or hidden hook at the center of a refined "
                "evergreen Christmas wreath mounted flat on a light oak door. Shoot straight-on and fairly close in bright "
                "white natural daylight with a softly blurred doorway background. Keep pine needles and ornaments behind "
                "the cross rather than covering its arms, lower stem, embroidery, personalized text, seams, or loop."
            ),
        ),
        (
            "Two-cross textile display",
            "Two exact fabric crosses on woven blanket with Christmas ornaments",
            _christmas_fabric_cross_brief(
                "arrange exactly two copies of the exact source cross side by side on a textured woven wool blanket layered "
                "with soft linen. Both crosses retain the same source fabric color, embroidery, thread colors, loop, and "
                "construction unless the source itself visibly shows two variants. Add a few matte Christmas ornaments and "
                "one pine sprig around the outer edges. Shoot from 60-75 degrees above in clear airy white daylight with "
                "soft natural shadows and neither cross overlapping the other."
            ),
        ),
        (
            "Church lifestyle",
            "Three-year-old girl holding fabric cross beside small pine tree",
            _christmas_fabric_cross_brief(
                "capture a candid three-year-old girl in a light-colored dress standing in a bright church, holding the "
                "exact cross naturally in one hand while her other hand steadies a small artificial pine tree. Crop or turn "
                "her face so it is not clearly identifiable. Shoot in serene white window daylight with shallow depth of "
                "field. Keep the cross front-facing, sharply focused, correctly scaled, and free of fingers covering its "
                "embroidery, personalized text, seams, shape, or hanging loop."
            ),
        ),
        (
            "Four-panel making process",
            "Sketch threading hand embroidery and finished cross process",
            _christmas_fabric_cross_brief(
                "create one square 1:1 collage divided into exactly four clean process panels. Panel 1 shows the exact cross "
                "outline and exact embroidery motif lightly sketched in pencil on linen matching the source color. Panel 2 "
                "shows matching embroidery floss being threaded through the eye of a real needle by anatomically natural "
                "hands. Panel 3 shows the exact motif being hand embroidered on matching linen stretched in a round wooden "
                "hoop, with the needle at a realistic stitch contact point and the correct thread color. Panel 4 shows the "
                "completed exact cross hanging from its original soft loop above a clean surface with restrained dried reeds "
                "and one evergreen sprig. Use clear airy white daylight and no captions or panel labels."
            ),
        ),
        (
            "Christmas table display",
            "Fabric cross upright on wood table with festive blocks and pine",
            _christmas_fabric_cross_brief(
                "stand the exact cross upright and securely supported on a rustic light-wood table as the dominant subject. "
                "Surround it sparsely with textless wooden blocks or blocks turned so no letters are readable, one small pine "
                "tree, a ball of natural yarn, and a soft woven basket. Shoot at table height from a slight 20-degree angle "
                "in clear white side daylight, with a softly blurred festive background and the complete cross, loop, seams, "
                "linen weave, and raised embroidery sharply visible."
            ),
        ),
        (
            "Embroidery macro",
            "Close-up proof of raised hand embroidery and stitching",
            _christmas_fabric_cross_brief(
                "take one close macro photograph of the exact source cross, filling most of the square frame while retaining "
                "enough outer edge to prove its cross shape. Focus on the original embroidered motif or personalized text, "
                "individual thread fibers, stitch direction, raised needlework depth, linen weave, edge seam, and one portion "
                "of the hanging-loop attachment. Use soft white side daylight and shallow background blur, with no redesign, "
                "enhancement, replacement, or invented stitch."
            ),
        ),
        (
            "Sleeping baby keepsake",
            "Adult hands cradling fabric cross beside sleeping baby",
            _christmas_fabric_cross_brief(
                "show anatomically natural adult hands gently cradling the exact cross in the foreground beside a peacefully "
                "sleeping baby in a bright Christmas nursery. Keep the baby safely positioned and softly blurred in the crib "
                "background. Shoot in clean white window daylight with the cross as the sharp focal point. Hands may support "
                "only the outer edges and must not cover the source embroidery, personalized text, cross silhouette, seams, "
                "or hanging loop."
            ),
        ),
        (
            "Christmas tree ornament",
            "Fabric cross hanging naturally on decorated Christmas tree",
            _christmas_fabric_cross_brief(
                "hang the exact cross naturally from its original loop on a fresh Christmas-tree branch like a standard "
                "keepsake ornament. Shoot head-on at product height in soft white-balanced light. Place a few matte baubles "
                "and restrained cool-white LED string lights in the softly blurred background. Keep needles and ornaments "
                "from touching or covering the cross, and make its source hand embroidery, seams, fabric texture, loop, and "
                "complete silhouette tack-sharp."
            ),
        ),
        (
            "Three color options",
            "Three neutral fabric-color crosses in pine-lined wicker basket",
            _christmas_fabric_cross_brief(
                "display exactly three copies of the same cross construction prominently in a natural wicker basket lined "
                "with pine sprigs. Use three distinct tasteful neutral linen base colors, while preserving the exact source "
                "cross silhouette, dimensions, soft volume, embroidery motif, embroidery placement, thread colors, stitch "
                "style, seams, and hanging-loop construction on all three. If the source contains personalized text, use a "
                "different plausible correctly stitched name on each cross in the exact source position and lettering style; "
                "if the source has no text, invent none. Place the basket on a pale table with soft greenery, moss, and small "
                "Christmas accents. Shoot outdoors in open shade or beside a bright window with clean white daylight and no "
                "yellow cast, keeping all three crosses fully visible and dominant."
            ),
        ),
    ),
}
