"""Tests for format structure injection. Pure functions, no API calls."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.post_scorer import FORMAT_STRUCTURES, _format_prompts

POST = {"influencer": "Jane Doe", "post_text": "Some source post about pipeline."}


ALL_FORMAT_KEYS = {"Opinion", "POV", "Signature", "Story",
                   "Comparison", "Method", "CaseProof", "Debate", "Magnet", "Offer"}


def test_formats_defined_with_de_and_en():
    assert set(FORMAT_STRUCTURES) == ALL_FORMAT_KEYS
    for key in FORMAT_STRUCTURES:
        assert FORMAT_STRUCTURES[key]["de"].strip()
        assert FORMAT_STRUCTURES[key]["en"].strip()


def test_story_injects_narrative_structure():
    de, en = _format_prompts(POST, "Story")
    assert "Szene" in de
    assert "narrative" in en.lower()


def test_opinion_injects_contrarian_structure():
    de, en = _format_prompts(POST, "Opinion")
    assert "Gegenposition" in de
    assert "contrarian" in en.lower()


def test_pov_injects_framework_structure():
    de, en = _format_prompts(POST, "POV")
    assert "Denk-Linse" in de
    assert "lens" in en.lower()


def test_signature_injects_belief_vs_reality_structure():
    de, en = _format_prompts(POST, "Signature")
    # "Glaube" ist raus (Kulle 24.08.2026: "merkwuerdiges Deutsch"), es heisst
    # Annahme gegen Praxis.
    assert "annehmen" in de.lower()
    assert "Glaube-gegen" not in de
    assert "Vergleichstabelle" in de
    assert "belief" in en.lower()


def test_no_caps_label_option_in_either_prompt():
    de, en = _format_prompts(POST, "POV")
    assert "GROSSBUCHSTABEN-Label" not in de
    assert "ALL-CAPS label" not in en
    assert "Grossbuchstaben" in de and "capitals" in en


def test_opinion_has_no_list_pov_has_numbered_list():
    de_op, _ = _format_prompts(POST, "Opinion")
    de_pov, _ = _format_prompts(POST, "POV")
    assert "KEINE Liste" in de_op
    assert "➊ ➋ ➌" in de_pov


def test_kurz_band_replaces_structure_and_target():
    de, en = _format_prompts(POST, "Story", band="kurz")
    assert "Kurzform" in de and "500-900 Zeichen" in de
    assert "Szene" not in de                      # Story-Struktur ersetzt
    assert "short form" in en and "500-900 characters" in en
    de_default, _ = _format_prompts(POST, "Story")
    assert "1.600-2.000 Zeichen" in de_default


def test_lang_band_stays_under_instagram_caption_limit():
    """Make 8912831 postet den DE-Draft plus CTA_DE auch auf Instagram
    (Caption max 2.200 Zeichen). 30.07., 11.08. und 13.08.2026 scheiterten
    dort drei Posts mit 2.429-2.584 Zeichen; der Ignore-Handler verschluckte
    danach den Notion-Writeback und die Zeile blieb Approved."""
    from tools.post_scorer import LENGTH_CAP
    from clients.jolly import config as jolly
    assert LENGTH_CAP["lang"] + len("\n\n" + jolly.CTA_DE) <= 2200
    de, en = _format_prompts(POST, "Story")
    assert "Nie ueber 2.100 Zeichen" in de and "Never above 2,100 characters" in en


def test_unknown_format_falls_back_to_opinion():
    de_known, _ = _format_prompts(POST, "Opinion")
    de_unknown, _ = _format_prompts(POST, "Nonsense")
    assert "Gegenposition" in de_unknown  # same as Opinion block


def test_post_text_and_influencer_present_in_prompt():
    de, en = _format_prompts(POST, "POV")
    assert "Jane Doe" in de and "Jane Doe" in en
    assert "Some source post" in de and "Some source post" in en


from unittest.mock import MagicMock, patch


def test_generate_threads_format_into_de_prompt():
    captured = []

    def fake_create(**kw):
        captured.append(kw["messages"][0]["content"])
        resp = MagicMock()
        resp.content = [MagicMock(text="===POST===\nBody.\n===SOUNDBYTE===\nByte.")]
        return resp

    with patch("tools.post_scorer.client") as c:
        c.messages.create.side_effect = fake_create
        from tools.post_scorer import generate_post_and_image_prompt
        generate_post_and_image_prompt(POST, "Signature")

    # First call is the DE prompt; it must carry the Signature structure.
    assert "Vergleichstabelle" in captured[0]


def _gen_with_responses(bodies, post_format="Opinion", band=None, grammar=False,
                        naturalness=False, avoid=None):
    """Laesst generate_post_and_image_prompt gegen eine Folge von
    Modellantworten laufen. Gibt (de_draft, gesendete Prompts) zurueck."""
    captured, bodies = [], list(bodies)

    def fake_create(**kw):
        captured.append(kw["messages"][0]["content"])
        resp = MagicMock()
        resp.content = [MagicMock(text=bodies.pop(0))]
        return resp

    from tools import post_scorer as ps
    with patch("tools.post_scorer.client") as c, \
         patch.dict(ps._cfg.FEATURES, {"grammar_check": grammar, "en_draft": False,
                                       "naturalness_check": naturalness}):
        c.messages.create.side_effect = fake_create
        de, *_ = ps.generate_post_and_image_prompt(POST, post_format, band=band,
                                                   avoid_phrases=avoid)
    return de, captured


def test_textwache_retries_once_with_findings_then_accepts():
    bad = "===POST===\nDREI PRUEFSCHRITTE VOR DEM TERMIN\nDer Uebergabetest.\n===SOUNDBYTE===\nx"
    good = "===POST===\nDrei Prüfschritte vor dem Termin. Der Übergabetest.\n===SOUNDBYTE===\nx"
    de, sent = _gen_with_responses([bad, good])
    assert de.startswith("Drei Prüfschritte")
    assert len(sent) == 2
    assert "KORREKTUR" in sent[1] and "Grossbuchstaben" in sent[1]
    assert "Uebergabetest" in sent[1]


def test_textwache_drops_text_after_failed_retry():
    bad = "===POST===\nDREI PRUEFSCHRITTE VOR DEM TERMIN\nText.\n===SOUNDBYTE===\nx"
    de, sent = _gen_with_responses([bad, bad])
    assert de == ""
    assert len(sent) == 2


def test_textwache_umlaut_only_goes_to_grammar_check_not_drop():
    with_uml = "===POST===\nDer Uebergabetest zeigt es.\n===SOUNDBYTE===\nx"
    fixed = "Der Übergabetest zeigt es."
    # Lauf 1 verstoesst (Umlaut), Lauf 2 identisch, dann Korrektor mit Kandidaten.
    de, sent = _gen_with_responses([with_uml, with_uml, fixed], grammar=True)
    assert de.startswith(fixed)                   # dahinter ggf. Mandanten-CTA
    assert len(sent) == 3
    assert "Uebergabetest" in sent[2] and "Umschreibungen" in sent[2]


_CLEAN = "===POST===\nDie zweite Gesellschaft kostet so viel wie die erste, weil der Kontenrahmen neu verhandelt wird.\n===SOUNDBYTE===\nx"
_FORMEL = "===POST===\nDas ist kein Planungsproblem. Das ist ein Strukturproblem.\n===SOUNDBYTE===\nx"


def test_lektor_accepts_good_text_with_one_call():
    de, sent = _gen_with_responses([_CLEAN, '{"note": 9, "fundstellen": []}'], naturalness=True)
    assert de.startswith("Die zweite Gesellschaft")
    assert len(sent) == 2 and "Lektor" in sent[1]


def test_lektor_low_note_triggers_rewrite_and_keeps_better():
    low = '{"note": 4, "fundstellen": ["Das ist kein Planungsproblem: Formel, sagt niemand"]}'
    de, sent = _gen_with_responses([_FORMEL, low, _CLEAN, '{"note": 8, "fundstellen": []}'],
                                   naturalness=True)
    assert de.startswith("Die zweite Gesellschaft")
    assert len(sent) == 4
    assert "KORREKTUR" in sent[2] and "Note 4 von 10" in sent[2]
    assert "kein X-Problem" in sent[2]                 # deterministischer Tic im Hinweis


def test_lektor_keeps_original_when_rewrite_is_worse():
    de, sent = _gen_with_responses(
        [_CLEAN, '{"note": 6, "fundstellen": ["x: y"]}', _FORMEL, '{"note": 5, "fundstellen": []}'],
        naturalness=True)
    assert de.startswith("Die zweite Gesellschaft")


def test_lektor_unreadable_verdict_keeps_text():
    de, sent = _gen_with_responses([_CLEAN, "kein json"], naturalness=True)
    assert de.startswith("Die zweite Gesellschaft") and len(sent) == 2


def test_avoid_phrases_land_in_prompt():
    from tools.naturalness import CLOSING_QUESTION
    de, sent = _gen_with_responses([_CLEAN], avoid=["In Projekten sehe ich", CLOSING_QUESTION, CLOSING_QUESTION])
    assert "SCHON VERBRAUCHT" in sent[0] and "In Projekten sehe ich" in sent[0]
    assert "endet NICHT mit einer Frage" in sent[0]


def test_kurz_band_caps_at_1000_chars():
    long_body = "===POST===\n" + ("Ein Satz mit Inhalt. " * 60) + "\n===SOUNDBYTE===\nx"
    de, sent = _gen_with_responses([long_body, long_body], band="kurz")
    assert de == ""
    assert "hoechstens 1000" in sent[1]


def test_comparison_injects_decision_structure():
    de, en = _format_prompts(POST, "Comparison")
    assert "Entscheidungskriterien" in de and "Red Flags" in de
    assert "red flags" in en.lower()
    assert "Kein DM-CTA" in de  # promotion ban stays outside promotion row


def test_method_injects_steps_and_pitfall():
    de, en = _format_prompts(POST, "Method")
    assert "Stolperstein" in de
    assert "pitfall" in en.lower()


def test_caseproof_pins_numbers_to_asset():
    de, en = _format_prompts(POST, "CaseProof")
    assert "CASE-ASSET" in de and "woertlich" in de
    assert "case asset" in en.lower() and "verbatim" in en.lower()
    assert "Keine anderen Referenzen" in de
    assert "no other references" in en.lower()


def test_debate_demands_reply_not_dm():
    de, en = _format_prompts(POST, "Debate")
    assert "Lager" in de and "Kein DM-CTA" in de
    assert "camp" in en.lower()


def test_magnet_allows_exactly_one_cta_from_asset():
    # Seit 2026-07-25: CTA kommt aus dem Asset (Kommentar-Keyword ODER Direktlink).
    de, en = _format_prompts(POST, "Magnet")
    assert "Genau EIN CTA" in de and "LEAD-MAGNET-ASSET" in de
    assert "Kommentar-Keyword" in de and "Direktlink" in de
    assert "comment keyword" in en.lower() and "direct link" in en.lower()


def test_offer_allows_dm_or_discovery_cta_without_scarcity():
    de, en = _format_prompts(POST, "Offer")
    assert "OFFER-ASSET" in de and "Kein kuenstlicher Zeitdruck" in de
    assert "scarcity" in en.lower()
