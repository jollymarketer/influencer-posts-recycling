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

Since 2026-09-09 (Richard, prompt review points 2 + 4): an optional Sonnet step,
plan_visual, turns soundbyte + metaphor into ONE concrete scene and a headline
of at most 4 words BEFORE the prompt is built. The image model no longer picks
from an open list of directions or shortens the 12-word soundbyte itself.
Mandatory text is marked in the prompt (kieai_image.render_text_line) so the
post-render readback can verify it. Callers pass the plan via `visual=`; the
selector and the builders stay free of API calls.
"""
import json
import re

from clients import load_client
from tools import anthropic_auth
from tools.kieai_image import render_text_line
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
        if layers_count >= 3:
            ranked += ["structured_infographic", "statement_card"]
        else:
            ranked += ["statement_card", "editorial_cover"]
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


# --- visual plan (Sonnet, one call per image) ---------------------------------

_BRAND_RULES = _cfg.TOKENS["ARCHETYPE_BRAND_RULES"]

VISUAL_PLAN_MODEL = "claude-sonnet-4-6"
HEADLINE_MAX_WORDS = 4
# Planned headlines longer than this are dropped (LLM ignored the cap); the
# builder then falls back to the unmarked wording.
_HEADLINE_HARD_CAP = 6

# Archetypes that get a plan, with the hint the art director receives.
_PLAN_HINTS = {
    "editorial_cover": "magazine-cover still: one conceptual object or scene, atmosphere, depth of field",
    "metaphor_object": "one tactile hero object that embodies the metaphor, studio light, material detail",
    "isometric_scene": "a small designed 3D-style world that shows the system, 2-4 elements, one reading flow",
    "two_panel_contrast": "two opposing sides, one simple focal element per side; describe both sides",
    "stat_hero": "typographic: one giant number; describe only the ground, texture and where the accent sits",
}

VISUAL_PLAN_PROMPT = """You are an art director briefing an image model for a LinkedIn visual (square 1:1).

Archetype: {archetype} ({hint})
Core message: {soundbyte}
Visual metaphor from the editor (may be empty): {metaphor}
Structure keywords (may be empty): {layers}

Brand rules:
{brand_rules}

Task 1 - SCENE: describe ONE concrete image in 50-80 words: the single hero object or scene, its material and surface, the light, the camera angle, where the one accent color sits, and where the headline sits. Concrete nouns only, no abstractions, no list of options. No people at desks, no handshakes, no generic office stock imagery. The bottom-right corner stays empty.

Task 2 - HEADLINE: the core message compressed to at most {max_words} words in {language}: a complete, natural phrase, not a truncated sentence. Keep umlauts. No trailing punctuation, no quotes.

Return strict JSON only, no prose, no markdown fences:
{{"scene": "...", "headline": "..."}}"""


def _clean_headline(text: str) -> str:
    words = " ".join((text or "").replace('"', "").split()).strip(" .!?:;,")
    if not words or len(words.split()) > _HEADLINE_HARD_CAP:
        return ""
    return words


def plan_visual(
    archetype: str,
    *,
    soundbyte: str = "",
    kontext: str = "",
    skeleton: str = "",
    language: str = "English",
) -> dict:
    """One Sonnet call: {"scene": str, "headline": str} for the archetype.
    Returns {} for archetypes that need neither (statement card renders the
    soundbyte itself, the infographic renders its layers) and on any failure:
    the prompt then keeps its previous, unplanned wording."""
    hint = _PLAN_HINTS.get(archetype)
    if not hint:
        return {}
    parsed = _parse_skeleton(skeleton)
    prompt = VISUAL_PLAN_PROMPT.format(
        archetype=ARCHETYPES[archetype]["label"], hint=hint,
        soundbyte=soundbyte, metaphor=parsed["metaphor"] or "-",
        layers="; ".join(parsed["layers"]) or "-",
        brand_rules=_BRAND_RULES, max_words=HEADLINE_MAX_WORDS, language=language,
    )
    try:
        client = anthropic_auth.anthropic_client()
        resp = client.messages.create(
            model=VISUAL_PLAN_MODEL, max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
        scene = " ".join(str(data.get("scene", "")).split())
        headline = _clean_headline(str(data.get("headline", "")))
    except Exception as e:
        print(f"  Bildplan (Sonnet) ausgefallen, Prompt ohne Szene: {e}", flush=True)
        return {}
    if not scene and not headline:
        return {}
    return {"scene": scene, "headline": headline}


# --- prompt builders ----------------------------------------------------------

def _headline_block(visual: dict, language: str, max_words: int, optional: bool = False) -> str:
    """Headline paragraph: marked and mandatory when the plan delivered one,
    otherwise the previous free wording (nothing to verify)."""
    headline = _clean_headline((visual or {}).get("headline", ""))
    if headline:
        return (f"Headline (ultra-bold, integrated into the composition, in {language}). "
                f"{render_text_line(headline)}\n"
                f"No other text: no captions, no labels, no body copy.")
    if optional:
        return (f"Optional headline only if it sharpens the idea, max {max_words} words in "
                f"{language}; otherwise no text at all. No diagram labels, no callouts, "
                f"no icon rows. Spell any text correctly.")
    return (f"Text discipline: one integrated headline, ultra-bold, max {max_words} words, "
            f"in {language}. No captions, no labels, no body copy. Spell every word correctly.")


def _scene_block(visual: dict, fallback: str) -> str:
    scene = (visual or {}).get("scene", "")
    if scene:
        return f"Scene to render (follow it, do not add competing elements):\n{scene}"
    return fallback


def _editorial_cover(soundbyte, kontext, parsed, language, visual=None):
    concept = _scene_block(visual, (
        "Concept: pick the single strongest visual direction (symbolic metaphor, cinematic "
        "still, conceptual illustration, tactile object). One dominant focal point, 2-4 major "
        "elements maximum. Atmosphere, depth of field and subtle texture are encouraged. "
        "Do not combine competing concepts."))
    return f"""Create a premium editorial cover visual (square 1:1) for a B2B tech-leadership audience. One strong conceptual image, magazine-cover quality — not advertising, not a slide.

Core message to translate into a single image:
{soundbyte}

Audience: {kontext or _DEFAULT_AUDIENCE}

{concept}

{_headline_block(visual, language, 6)}

{_BRAND_RULES}"""


def _stat_hero(soundbyte, kontext, parsed, language, visual=None):
    stat = extract_stat(soundbyte) or extract_stat(" ".join(parsed["layers"]))
    label = _clean_headline((visual or {}).get("headline", ""))
    if label:
        label_line = (f"Short supporting label (small, secondary, in {language}). "
                      f"{render_text_line(label)}")
    else:
        label_line = (f"Short supporting line (small, secondary), drawn from this idea: "
                      f"{soundbyte}\nOne short label beneath or beside the number, max 6 "
                      f"words in {language}. Spell the label correctly.")
    ground = _scene_block(visual, "")
    return f"""Create a bold statistic-hero visual (square 1:1) where ONE number is the entire composition.

Hero number (large, dominant, unmistakable). {render_text_line(stat)}
{label_line}
Audience: {kontext or _DEFAULT_AUDIENCE}
{ground}

Composition: the number fills most of the frame as the single focal point, ultra-bold. One accent color only. Generous whitespace. Nothing else competes with the number. No charts, no icons, no decorative clutter, no other text.

{_BRAND_RULES}"""


def _statement_card(soundbyte, kontext, parsed, language, visual=None):
    return f"""Create a typographic statement card (square 1:1): one sharp sentence rendered as confident type art. The words ARE the visual.

The statement, rendered in full as the hero, in {language}. {render_text_line(soundbyte)}

Composition: strong typographic hierarchy — emphasize the 2-3 load-bearing words with size, weight or the single accent color, keep the rest calm. Tight, intentional layout on a clean light ground with subtle texture or a single geometric accent. No illustration, no icons, no photo, no other text. The sentence must be spelled exactly as given and read instantly at thumbnail size.

{_BRAND_RULES}"""


def _two_panel_contrast(soundbyte, kontext, parsed, language, visual=None):
    layers = parsed["layers"]
    left = layers[0] if len(layers) > 0 else "the common belief"
    right = layers[1] if len(layers) > 1 else "the reality"
    scene = _scene_block(visual, "")
    return f"""Create a clean two-panel contrast visual (square 1:1): the canvas split into two sides that visually oppose each other (belief vs reality, before vs after, old way vs new way).

Tension to depict (do not render this whole line as text):
{soundbyte}

Left side keywords: {left}
Right side keywords: {right}
{scene}

Composition: a clear vertical or diagonal divider, one simple focal element per side, the contrast obvious in under 2 seconds. At most one short label per side, max 4 words each, in {language}. Use the single accent color to mark the favorable side. Minimal text, no full sentences, no clutter. Spell labels correctly.

{_BRAND_RULES}"""


def _metaphor_object(soundbyte, kontext, parsed, language, visual=None):
    metaphor = parsed["metaphor"] or "a single strong object that embodies the idea"
    scene = _scene_block(visual, (
        "Composition: one hero object as the sole focal point, rendered tactile and premium "
        "(studio light, depth, material detail). The metaphor must read instantly without "
        "explanation."))
    return f"""Create a single-metaphor-object visual (square 1:1): one striking object or scene that carries the whole idea — a real depicted thing, not a labeled chart.

Visual metaphor to build around: {metaphor}
Idea it must convey: {soundbyte}
Audience: {kontext or _DEFAULT_AUDIENCE}

{scene}

{_headline_block(visual, language, 5, optional=True)}

{_BRAND_RULES}"""


def _isometric_scene(soundbyte, kontext, parsed, language, visual=None):
    layers = parsed["layers"]
    callouts = "; ".join(layers[:3]) if layers else "the 2-3 key moving parts of the system"
    scene = _scene_block(visual, "")
    return f"""Create a modern isometric scene (square 1:1) that shows the system or workflow as a small, designed 3D-style world — clean and premium, not a flat clip-art diagram.

Idea / system to depict:
{soundbyte}

Up to three light callouts to place in the scene: {callouts}
{scene}

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
    visual: dict | None = None,
) -> tuple[str, str, str, bool]:
    """Builds the kie.ai prompt for the chosen archetype.

    Returns (effective_archetype, prompt, aspect_ratio, strip_marks). The
    effective archetype may differ from the requested one when a graceful
    fallback fires: structured_infographic with no parseable layers, or
    stat_hero with no extractable stat, both fall back to editorial_cover.
    `visual` is the plan_visual output ({"scene", "headline"}); without it
    the builders keep their unplanned wording and mark no headline."""
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
    prompt = builder(soundbyte, kontext, parsed, language, visual or {})
    strip = ARCHETYPES[archetype]["strip_marks"]
    return archetype, prompt, ASPECT_RATIO, strip
