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


def test_magnet_with_thin_skeleton_avoids_literal_infographic():
    assert ia.select_archetype(
        "Magnet", infographic_type="", layers_count=2,
        has_metaphor=False, has_stat=False,
    ) == "statement_card"


def test_magnet_with_structural_skeleton_prefers_infographic():
    assert ia.select_archetype(
        "Magnet", infographic_type="", layers_count=3,
        has_metaphor=False, has_stat=False,
    ) == "structured_infographic"


# --- Pflichttext-Marker (Readback, Punkt 3) -----------------------------------

from tools.kieai_image import required_text_from_prompt  # noqa: E402

SB_DE = "Planung ist kein Ritual, sondern Steuerung"


def test_statement_card_marks_full_soundbyte_as_required_text():
    _, prompt, _, _ = ia.build_archetype_prompt("statement_card", soundbyte=SB_DE, language="German")
    assert required_text_from_prompt(prompt) == [SB_DE]


def test_stat_hero_marks_the_number_as_required_text():
    _, prompt, _, _ = ia.build_archetype_prompt(
        "stat_hero", soundbyte="73% der Plaene sind im Maerz tot", language="German")
    assert "73%" in required_text_from_prompt(prompt)


def test_stat_hero_marks_planned_headline_as_label():
    _, prompt, _, _ = ia.build_archetype_prompt(
        "stat_hero", soundbyte="73% der Plaene sind im Maerz tot", language="German",
        visual={"scene": "", "headline": "Plaene sterben im Maerz"})
    assert required_text_from_prompt(prompt) == ["73%", "Plaene sterben im Maerz"]


def test_editorial_cover_without_plan_has_no_required_text():
    _, prompt, _, _ = ia.build_archetype_prompt("editorial_cover", soundbyte=SB_DE, language="German")
    assert required_text_from_prompt(prompt) == []


def test_editorial_cover_with_plan_marks_headline_and_embeds_scene():
    visual = {"scene": "A brass compass on slate, raking light from the left.",
              "headline": "Steuern statt Ritual"}
    _, prompt, _, _ = ia.build_archetype_prompt(
        "editorial_cover", soundbyte=SB_DE, language="German", visual=visual)
    assert required_text_from_prompt(prompt) == ["Steuern statt Ritual"]
    assert visual["scene"] in prompt
    # Die offene Richtungsliste weicht der konkreten Szene.
    assert "pick the single strongest visual direction" not in prompt


def test_metaphor_object_and_isometric_and_contrast_embed_scene():
    visual = {"scene": "One domino row on a navy ground.", "headline": "Kaskade stoppen"}
    for key in ("metaphor_object", "isometric_scene", "two_panel_contrast"):
        _, prompt, _, _ = ia.build_archetype_prompt(
            key, soundbyte=SB_DE, language="German", visual=visual,
            skeleton="METAPHER: domino\nEBENEN:\nAlt: a, b\nNeu: c, d")
        assert visual["scene"] in prompt, key


def test_metaphor_object_marks_headline_only_when_planned():
    _, without, _, _ = ia.build_archetype_prompt("metaphor_object", soundbyte=SB_DE, language="German")
    assert required_text_from_prompt(without) == []
    _, with_plan, _, _ = ia.build_archetype_prompt(
        "metaphor_object", soundbyte=SB_DE, language="German",
        visual={"scene": "x", "headline": "Kaskade stoppen"})
    assert required_text_from_prompt(with_plan) == ["Kaskade stoppen"]


def test_overlong_planned_headline_is_dropped():
    visual = {"scene": "x", "headline": "eins zwei drei vier fuenf sechs sieben"}
    _, prompt, _, _ = ia.build_archetype_prompt(
        "editorial_cover", soundbyte=SB_DE, language="German", visual=visual)
    assert required_text_from_prompt(prompt) == []


# --- plan_visual (Sonnet-Schritt, Punkt 2 + 4) ---------------------------------

from unittest.mock import MagicMock, patch  # noqa: E402


def _fake_client(text: str):
    client = MagicMock()
    client.messages.create.return_value = MagicMock(content=[MagicMock(text=text)])
    return client


def test_plan_visual_parses_json_with_code_fence():
    raw = '```json\n{"scene": "A brass compass on slate.", "headline": "Steuern statt Ritual"}\n```'
    with patch.object(ia.anthropic_auth, "anthropic_client", return_value=_fake_client(raw)):
        out = ia.plan_visual("editorial_cover", soundbyte=SB_DE, kontext="", skeleton="", language="German")
    assert out == {"scene": "A brass compass on slate.", "headline": "Steuern statt Ritual"}


def test_plan_visual_skips_archetypes_without_scene_or_headline():
    with patch.object(ia.anthropic_auth, "anthropic_client") as mk:
        assert ia.plan_visual("statement_card", soundbyte=SB_DE) == {}
        assert ia.plan_visual("structured_infographic", soundbyte=SB_DE) == {}
    mk.assert_not_called()


def test_plan_visual_returns_empty_on_failure():
    with patch.object(ia.anthropic_auth, "anthropic_client", side_effect=ValueError("kein Key")):
        assert ia.plan_visual("editorial_cover", soundbyte=SB_DE, language="German") == {}
    with patch.object(ia.anthropic_auth, "anthropic_client", return_value=_fake_client("kein json")):
        assert ia.plan_visual("editorial_cover", soundbyte=SB_DE, language="German") == {}


def test_plan_visual_prompt_carries_message_metaphor_and_brand_rules():
    client = _fake_client('{"scene": "s", "headline": "h"}')
    with patch.object(ia.anthropic_auth, "anthropic_client", return_value=client):
        ia.plan_visual("metaphor_object", soundbyte=SB_DE, language="German",
                       skeleton="METAPHER: eine Bruecke\nEBENEN:\nA: x")
    sent = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert SB_DE in sent and "eine Bruecke" in sent and "German" in sent
    assert ia._BRAND_RULES.splitlines()[0] in sent
