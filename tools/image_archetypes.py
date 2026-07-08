"""Image-archetype router: a menu of 7 distinct visual forms + a concept-forward
selector + a dispatcher that builds the kie.ai prompt for the chosen form.

Why this exists: the pipeline used to render the literal layered infographic
(build_infographic_prompt) on almost every post, which read as a clunky,
template-y slide. This module replaces that single default with a menu of seven
visually distinct archetypes and a deterministic selector that picks the best
fit for each post, biased toward low-text concept visuals (the iceberg-monotony
fix, one level up: now it is the whole infographic form that varies, not just
its layout type). Same pattern as the format/infographic-type anti-repeat:
menu + selector + guard tests, no live API in the selection path.

The selector is pure and deterministic (unit-testable). The dispatcher returns
(prompt, aspect_ratio, strip_marks) ready for tools.kieai_image.generate_image.
"""
import re

from clients import load_client
from tools.post_scorer import build_infographic_prompt

_cfg = load_client()
_DEFAULT_AUDIENCE = _cfg.TOKENS["DEFAULT_AUDIENCE_ARCHETYPE"]

# Canonical infographic-type names (from post_scorer.INFOGRAPHIC_TYPE_CANON) that
# represent a genuine structure worth rendering as a literal layered infographic.
STRUCTURAL_TYPES = {
    "Funnel/pyramid",
    "2x2 matrix",
    "Timeline",
    "Framework/circles",
    "Tree/branching",
}
# Types whose logic is a two-sided contrast — best shown as a split/contrast panel.
CONTRAST_TYPES = {
    "Comparison table",
    "Scale/seesaw",
    "Before/after",
    "Horizontal comparison",
}

# The seven archetypes, ordered low-text -> high-text. strip_marks follows the
# kieai_image convention: True = run the hallucinated-logo vision wipe (safe when
# the image carries little intentional text), False = leave the render untouched
# (the literal infographic has intentional text low in the frame).
ARCHETYPES = {
    "editorial_cover": {
        "label": "Editorial-Cover",
        "strip_marks": True,
    },
    "stat_hero": {
        "label": "Stat-Hero",
        "strip_marks": True,
    },
    "statement_card": {
        "label": "Statement-Card",
        "strip_marks": True,
    },
    "two_panel_contrast": {
        "label": "Kontrast-Split",
        "strip_marks": True,
    },
    "metaphor_object": {
        "label": "Metapher-Objekt",
        "strip_marks": True,
    },
    "isometric_scene": {
        "label": "Isometrische-Szene",
        "strip_marks": True,
    },
    "structured_infographic": {
        "label": "Infografik",
        "strip_marks": False,
    },
}

ASPECT_RATIO = "1:1"  # LinkedIn square — always (see memory feedback_image_generation)


# --- parsing helpers ----------------------------------------------------------

def _parse_skeleton(skeleton: str) -> dict:
    """Pulls METAPHER + the EBENEN layer lines out of an infographic skeleton.
    Returns {"metaphor": str, "layers": [str, ...]}. Tolerant of a missing/empty
    skeleton (returns empty values)."""
    metaphor = ""
    layers: list[str] = []
    in_ebenen = False
    for line in (skeleton or "").splitlines():
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("METAPHER:"):
            metaphor = stripped.split(":", 1)[1].strip()
            in_ebenen = False
        elif upper.startswith("TYP:") or upper.startswith("KOMPLEMENTARIT") or upper.startswith("TOOL-LOGOS:"):
            in_ebenen = False
        elif upper.startswith("EBENEN:"):
            in_ebenen = True
        elif in_ebenen and stripped:
            layers.append(stripped)
    if metaphor.lower() in ("keine", "none", ""):
        metaphor = ""
    return {"metaphor": metaphor, "layers": layers}


_STAT_RE = re.compile(
    r"""(?<![\w.])(
        \d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?\s?%?   |  # 10,000  12.500
        \d+(?:[.,]\d+)?\s?%                       |  # 73%  12,5%
        [€$£]\s?\d+(?:[.,]\d+)?[kKmMbB]?          |  # €5k  $1.2M
        \d+(?:[.,]\d+)?\s?[xX](?![\w])            |  # 3x  10x
        \d+(?:[.,]\d+)?[kKmMbB](?![\w])              # 5k  2M
    )""",
    re.VERBOSE,
)


def extract_stat(text: str) -> str:
    """Returns the most prominent number-as-claim in the text (percentage, money,
    multiplier, or large/scaled number), or '' if there is no strong stat. Used
    to (a) gate the stat_hero archetype and (b) feed it the hero number."""
    if not text:
        return ""
    m = _STAT_RE.search(text)
    return m.group(1).strip() if m else ""


def skeleton_signals(skeleton: str, soundbyte: str = "") -> dict:
    """Derives the selector inputs from a skeleton + soundbyte in one call:
    {"layers_count", "has_metaphor", "has_stat"}. Keeps run_research out of the
    parsing internals."""
    parsed = _parse_skeleton(skeleton)
    has_stat = bool(extract_stat(soundbyte) or extract_stat(" ".join(parsed["layers"])))
    return {
        "layers_count": len(parsed["layers"]),
        "has_metaphor": bool(parsed["metaphor"]),
        "has_stat": has_stat,
    }


# --- selector (pure, deterministic, concept-forward) --------------------------

def select_archetype(
    post_format: str,
    infographic_type: str,
    layers_count: int = 0,
    has_metaphor: bool = False,
    has_stat: bool = False,
    recent_archetypes: list[str] | None = None,
) -> str:
    """Picks ONE archetype key for the post. Concept-forward: low-text visuals
    rank above the literal infographic, which is only a strong candidate for a
    genuinely structural post (structural type + 3+ layers). Anti-repeat skips
    the last two used archetypes when an equally-eligible alternative exists.

    Pure and deterministic — no API calls. Drives the guard tests."""
    ranked: list[str] = []

    if has_stat:
        ranked.append("stat_hero")
    if post_format == "Signature" or infographic_type in CONTRAST_TYPES:
        ranked.append("two_panel_contrast")
    if has_metaphor:
        ranked.append("metaphor_object")
    if post_format in ("Opinion", "Story"):
        ranked += ["statement_card", "editorial_cover"]
    elif post_format == "POV":
        ranked += ["isometric_scene", "editorial_cover"]
    elif post_format == "Comparison":
        ranked += ["two_panel_contrast", "structured_infographic"]
    elif post_format == "CaseProof":
        ranked += ["stat_hero", "editorial_cover"]
    elif post_format == "Method":
        ranked += ["isometric_scene", "structured_infographic"]
    elif post_format in ("Debate", "Offer"):
        ranked += ["statement_card", "editorial_cover"]
    elif post_format == "Magnet":
        ranked += ["structured_infographic", "statement_card"]
    # Literal infographic only when the post is genuinely structural.
    if infographic_type in STRUCTURAL_TYPES and layers_count >= 3:
        ranked.append("structured_infographic")

    # Concept-forward fallback fillers (low-text first, infographic strictly last).
    ranked += [
        "editorial_cover",
        "statement_card",
        "metaphor_object",
        "two_panel_contrast",
        "isometric_scene",
        "stat_hero",
        "structured_infographic",
    ]

    # Dedupe, preserve order.
    seen: set[str] = set()
    ordered = [a for a in ranked if not (a in seen or seen.add(a))]

    # Anti-repeat: avoid the last two used unless they are the only options left.
    recent = set((recent_archetypes or [])[:2])
    for a in ordered:
        if a not in recent:
            return a
    return ordered[0]


# --- prompt builders ----------------------------------------------------------

_BRAND_RULES = _cfg.TOKENS["ARCHETYPE_BRAND_RULES"]


def _editorial_cover(soundbyte, kontext, parsed, language):
    return f"""Create a premium editorial cover visual (square 1:1) for a B2B tech-leadership audience. One strong conceptual image, magazine-cover quality — not advertising, not a slide.

Core message to translate into a single image:
{soundbyte}

Audience: {kontext or _DEFAULT_AUDIENCE}

Concept: pick the single strongest visual direction (symbolic metaphor, cinematic still, conceptual illustration, tactile object). One dominant focal point, 2-4 major elements maximum. Atmosphere, depth of field and subtle texture are encouraged. Do not combine competing concepts.

Text discipline: one integrated headline, ultra-bold, max 6 words, in {language}. No captions, no labels, no body copy. Spell every word correctly.

{_BRAND_RULES}"""


def _stat_hero(soundbyte, kontext, parsed, language):
    stat = extract_stat(soundbyte) or extract_stat(" ".join(parsed["layers"]))
    return f"""Create a bold statistic-hero visual (square 1:1) where ONE number is the entire composition.

Hero number (render large, dominant, unmistakable): {stat}
Short supporting line (small, secondary), drawn from this idea: {soundbyte}
Audience: {kontext or _DEFAULT_AUDIENCE}

Composition: the number fills most of the frame as the single focal point, ultra-bold. One short label beneath or beside it, max 6 words in {language}. One accent color only. Generous whitespace. Nothing else competes with the number. No charts, no icons, no decorative clutter. Spell the label correctly.

{_BRAND_RULES}"""


def _statement_card(soundbyte, kontext, parsed, language):
    return f"""Create a typographic statement card (square 1:1): one sharp sentence rendered as confident type art. The words ARE the visual.

The statement (render in full, as the hero, in {language}):
"{soundbyte}"

Composition: strong typographic hierarchy — emphasize the 2-3 load-bearing words with size, weight or the single accent color, keep the rest calm. Tight, intentional layout on a clean light ground with subtle texture or a single geometric accent. No illustration, no icons, no photo. The sentence must be spelled exactly as given and read instantly at thumbnail size.

{_BRAND_RULES}"""


def _two_panel_contrast(soundbyte, kontext, parsed, language):
    layers = parsed["layers"]
    left = layers[0] if len(layers) > 0 else "the common belief"
    right = layers[1] if len(layers) > 1 else "the reality"
    return f"""Create a clean two-panel contrast visual (square 1:1): the canvas split into two sides that visually oppose each other (belief vs reality, before vs after, old way vs new way).

Tension to depict (do not render this whole line as text):
{soundbyte}

Left side keywords: {left}
Right side keywords: {right}

Composition: a clear vertical or diagonal divider, one simple focal element per side, the contrast obvious in under 2 seconds. At most one short label per side, max 4 words each, in {language}. Use the single accent color to mark the favorable side. Minimal text, no full sentences, no clutter. Spell labels correctly.

{_BRAND_RULES}"""


def _metaphor_object(soundbyte, kontext, parsed, language):
    metaphor = parsed["metaphor"] or "a single strong object that embodies the idea"
    return f"""Create a single-metaphor-object visual (square 1:1): one striking object or scene that carries the whole idea — a real depicted thing, not a labeled chart.

Visual metaphor to build around: {metaphor}
Idea it must convey: {soundbyte}
Audience: {kontext or _DEFAULT_AUDIENCE}

Composition: one hero object as the sole focal point, rendered tactile and premium (studio light, depth, material detail). The metaphor must read instantly without explanation. Optional headline only if it sharpens the idea, max 5 words in {language}; otherwise no text at all. No diagram labels, no callouts, no icon rows. Spell any text correctly.

{_BRAND_RULES}"""


def _isometric_scene(soundbyte, kontext, parsed, language):
    layers = parsed["layers"]
    callouts = "; ".join(layers[:3]) if layers else "the 2-3 key moving parts of the system"
    return f"""Create a modern isometric scene (square 1:1) that shows the system or workflow as a small, designed 3D-style world — clean and premium, not a flat clip-art diagram.

Idea / system to depict:
{soundbyte}

Up to three light callouts to place in the scene: {callouts}

Composition: one coherent isometric scene with clear depth and a single reading flow, 2-4 elements max. At most three short callout labels, max 3 words each, in {language}. The single accent color highlights the most important node. Cohesive, uncluttered, instantly legible at thumbnail size. Spell labels correctly.

{_BRAND_RULES}"""


_BUILDERS = {
    "editorial_cover": _editorial_cover,
    "stat_hero": _stat_hero,
    "statement_card": _statement_card,
    "two_panel_contrast": _two_panel_contrast,
    "metaphor_object": _metaphor_object,
    "isometric_scene": _isometric_scene,
}


def build_archetype_prompt(
    archetype: str,
    *,
    soundbyte: str = "",
    kontext: str = "",
    skeleton: str = "",
    language: str = "English",
) -> tuple[str, str, str, bool]:
    """Builds the kie.ai prompt for the chosen archetype.

    Returns (effective_archetype, prompt, aspect_ratio, strip_marks). The
    effective archetype may differ from the requested one when a graceful
    fallback fires: structured_infographic with no parseable layers, or
    stat_hero with no extractable stat, both fall back to editorial_cover."""
    parsed = _parse_skeleton(skeleton)

    if archetype == "structured_infographic":
        prompt = build_infographic_prompt(skeleton, language=language)
        if prompt:
            return "structured_infographic", prompt, ASPECT_RATIO, False
        archetype = "editorial_cover"  # no layers -> concept fallback

    if archetype == "stat_hero" and not (
        extract_stat(soundbyte) or extract_stat(" ".join(parsed["layers"]))
    ):
        archetype = "statement_card" if soundbyte else "editorial_cover"

    builder = _BUILDERS.get(archetype, _editorial_cover)
    archetype = archetype if archetype in _BUILDERS else "editorial_cover"
    prompt = builder(soundbyte, kontext, parsed, language)
    strip = ARCHETYPES[archetype]["strip_marks"]
    return archetype, prompt, ASPECT_RATIO, strip
