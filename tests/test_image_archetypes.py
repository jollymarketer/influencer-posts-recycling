"""Guard tests for the image-archetype router (tools/image_archetypes.py).

These encode the anti-clunk invariants the selector must keep holding:
- the literal infographic is never the default for a non-structural post,
- concept-forward bias (low-text forms win when the post fits several),
- a strong stat routes to the stat hero,
- anti-repeat rotates away from the last two used archetypes,
- the dispatcher returns a non-empty prompt for every archetype, with graceful
  fallbacks. No API calls anywhere in this module's selection path.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import image_archetypes as ia


# --- extract_stat -------------------------------------------------------------

def test_extract_stat_finds_percentage_money_multiplier():
    assert ia.extract_stat("Closes 73% faster") == "73%"
    assert ia.extract_stat("We saved €5k per rep") == "€5k"
    assert ia.extract_stat("3x the pipeline") == "3x"
    assert ia.extract_stat("10,000 leads ignored") == "10,000"


def test_extract_stat_empty_when_no_number():
    assert ia.extract_stat("Most outbound is noise") == ""
    assert ia.extract_stat("") == ""


# --- _parse_skeleton ----------------------------------------------------------

def test_parse_skeleton_pulls_metaphor_and_layers():
    sk = ("TYP: Scale/seesaw\nMETAPHER: a balance beam\n"
          "KOMPLEMENTARITAET: shows X -> text explains Y\n"
          "EBENEN:\nSpeed: fast, cheap\nQuality: slow, durable\nTOOL-LOGOS: none")
    out = ia._parse_skeleton(sk)
    assert out["metaphor"] == "a balance beam"
    assert out["layers"] == ["Speed: fast, cheap", "Quality: slow, durable"]


def test_parse_skeleton_treats_keine_as_no_metaphor():
    assert ia._parse_skeleton("METAPHER: keine\nEBENEN:\nA: x")["metaphor"] == ""
    assert ia._parse_skeleton("")["metaphor"] == "" and ia._parse_skeleton("")["layers"] == []


# --- select_archetype: concept-forward, no clunky default ---------------------

def test_opinion_non_structural_never_picks_infographic():
    pick = ia.select_archetype("Opinion", "Iceberg", layers_count=3, has_metaphor=False, has_stat=False)
    assert pick != "structured_infographic"
    assert pick in ("statement_card", "editorial_cover")


def test_story_routes_concept_forward():
    pick = ia.select_archetype("Story", "", layers_count=0)
    assert pick in ("statement_card", "editorial_cover")


def test_strong_stat_routes_to_stat_hero():
    assert ia.select_archetype("Opinion", "Iceberg", has_stat=True) == "stat_hero"


def test_signature_or_contrast_type_routes_to_contrast_panel():
    assert ia.select_archetype("Signature", "Comparison table", layers_count=2) == "two_panel_contrast"
    assert ia.select_archetype("POV", "Scale/seesaw", layers_count=2) == "two_panel_contrast"


def test_metaphor_present_routes_to_metaphor_object_for_pov():
    # POV with a metaphor and no contrast/stat -> metaphor object ranks first.
    assert ia.select_archetype("POV", "Framework/circles", layers_count=2, has_metaphor=True) == "metaphor_object"


def test_infographic_only_when_structural_and_enough_layers():
    # Genuinely structural AND concept forms suppressed by anti-repeat -> infographic reachable.
    pick = ia.select_archetype(
        "POV", "Funnel/pyramid", layers_count=4, has_metaphor=False,
        recent_archetypes=["isometric_scene", "editorial_cover"],
    )
    assert pick == "structured_infographic"


def test_structural_but_too_few_layers_stays_concept():
    pick = ia.select_archetype("POV", "Funnel/pyramid", layers_count=2)
    assert pick != "structured_infographic"


# --- select_archetype: anti-repeat --------------------------------------------

def test_anti_repeat_skips_last_two():
    pick = ia.select_archetype(
        "Opinion", "Iceberg", recent_archetypes=["statement_card", "editorial_cover"]
    )
    assert pick not in ("statement_card", "editorial_cover")


def test_anti_repeat_only_skips_two_not_three():
    # editorial_cover was used 3 back, so it is eligible again here.
    pick = ia.select_archetype(
        "Opinion", "Iceberg",
        recent_archetypes=["statement_card", "metaphor_object", "editorial_cover"],
    )
    assert pick == "editorial_cover"


def test_selector_always_returns_known_archetype():
    for fmt in ("Opinion", "POV", "Signature", "Story", "Weird"):
        pick = ia.select_archetype(fmt, "")
        assert pick in ia.ARCHETYPES


# --- build_archetype_prompt: dispatch + fallbacks -----------------------------

SK_STRUCT = ("TYP: Funnel/pyramid\nMETAPHER: none\nEBENEN:\n"
             "Awareness: ads, posts\nConsideration: demos\nDecision: pricing\nTOOL-LOGOS: none")


def test_every_archetype_builds_nonempty_prompt():
    for key in ia.ARCHETYPES:
        eff, prompt, ratio, strip = ia.build_archetype_prompt(
            key, soundbyte="Closes 73% faster", kontext="CEOs", skeleton=SK_STRUCT, language="English"
        )
        assert prompt.strip()
        assert ratio == "1:1"
        assert eff in ia.ARCHETYPES


def test_infographic_uses_layer_text_and_no_strip():
    eff, prompt, ratio, strip = ia.build_archetype_prompt(
        "structured_infographic", skeleton=SK_STRUCT, language="English"
    )
    assert eff == "structured_infographic"
    assert strip is False
    assert "Awareness" in prompt


def test_infographic_without_layers_falls_back_to_editorial():
    eff, prompt, ratio, strip = ia.build_archetype_prompt(
        "structured_infographic", soundbyte="Most outbound is noise", skeleton="", language="English"
    )
    assert eff == "editorial_cover"
    assert strip is True


def test_stat_hero_without_stat_falls_back_to_statement():
    eff, _, _, _ = ia.build_archetype_prompt(
        "stat_hero", soundbyte="Most outbound is noise", skeleton="", language="English"
    )
    assert eff == "statement_card"


def test_statement_card_renders_full_soundbyte():
    _, prompt, _, _ = ia.build_archetype_prompt(
        "statement_card", soundbyte="Pipeline is a process, not a prayer", language="English"
    )
    assert "Pipeline is a process, not a prayer" in prompt


# --- select_archetype: new formats (Comparison, Method, CaseProof, Debate, Magnet, Offer) ---

def test_comparison_prefers_two_panel_contrast():
    assert ia.select_archetype(
        "Comparison", infographic_type="", layers_count=0,
        has_metaphor=False, has_stat=False,
    ) == "two_panel_contrast"


def test_caseproof_prefers_stat_hero():
    assert ia.select_archetype(
        "CaseProof", infographic_type="", layers_count=0,
        has_metaphor=False, has_stat=False,
    ) == "stat_hero"


def test_debate_and_offer_prefer_statement_card():
    for fmt in ("Debate", "Offer"):
        assert ia.select_archetype(
            fmt, infographic_type="", layers_count=0,
            has_metaphor=False, has_stat=False,
        ) == "statement_card"
