"""Prompt-Diaet SWOT (Spec 2026-08-28): keine Wortlaut-Verbote, keine
Selbstwidersprueche im Schreib-Prompt. Laedt die Config direkt, unabhaengig
vom Prozess-Mandanten der Test-Session."""
import importlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

cfg = importlib.import_module("clients.swot.config")


def test_bans_carry_no_observer_permission_and_no_glaube_line():
    bans = cfg.TOKENS["LANGUAGE_BANS_DE"]
    assert "Erlaubt ist die Beobachterposition" not in bans
    assert "sehe ich" not in bans
    assert "Glaube" not in bans
    assert "kein Interim-CFO" in bans


def test_focus_topics_avoid_the_banned_kunstwort():
    assert "Uebergabefaehigkeit" not in cfg.TOKENS["FOCUS_TOPICS_DE"]
    assert "uebernehmen" in cfg.TOKENS["FOCUS_TOPICS_DE"]


def test_voice_head_demands_written_syntax_without_filler_wordlist():
    head = cfg.load_voice_profile("werner").split("\n")[2]
    assert "Schriftdeutsch" in head and "Verb an zweiter Stelle" in head
    assert "keine Echo-Antworten" in head
    assert "(halt, irgendwie" not in head


def test_voice_profiles_carry_no_spelled_out_formulas():
    for name in ("werner", "kulle"):
        p = cfg.load_voice_profile(name)
        assert "Das ist kein Tool-Problem" not in p
        assert "Das ist kein X-Problem" not in p
        assert "Game Changer" not in p and "Game-Changer" not in p
        assert "Kennst du das?" not in p
        assert "Was er nie sagen würde" in p


def test_cta_de_carries_the_booking_link():
    # 08.09.2026 (Richard): Link zurueck in den Text, der Verweis auf den
    # ersten Kommentar zwang den Absender zu einem zweiten Handgriff. Ohne
    # FIRST_COMMENT_DE bleibt die Plan-Spalte "Erster Kommentar" unberuehrt.
    assert cfg.CTA_DE == ("30 Minuten mit unseren Planungs- und "
                          "Konsolidierungsexperten, kostenfrei: "
                          "https://www.swot.de/demo-buchen/")
    assert not hasattr(cfg, "FIRST_COMMENT_DE")
    # Keine Sie-Anrede: der Beitrag spricht mit du/ihr.
    assert not re.search(r"\b(?:Sie|Ihnen|Ihre?[nmrs]?)\b", cfg.CTA_DE)


def test_paragraph_rule_and_ich_beobachtung_in_prompt():
    assert "ein bis zwei Saetzen" in cfg.TOKENS["PARAGRAPH_RULE_DE"]
    assert cfg.LENGTH_ROTATION_BY_KANAL["LinkedIn Christian"] == ["standard", "kurz"]


def test_no_persona_offers_the_banned_kunstwort():
    import json
    assert "Uebergabefaehigkeit" not in json.dumps(cfg.CONTENT_PERSONAS, ensure_ascii=False)


# Kundenregeln 08.09.2026 (Richard, aus den Notion-Kommentaren von Inga
# Baumert und Muhammed Doganguezel, 01. bis 07.09.2026).

def test_role_situations_differ_per_account_and_match_copy_rules():
    import re
    robert = cfg.ACCOUNT_VOICES["LinkedIn Robert"]
    christian = cfg.ACCOUNT_VOICES["LinkedIn Christian"]
    assert "Erstgespraech, Live-Demo, Workshop, Schulung" in robert
    assert "Datenuebernahme, Kundenprojekt, Abschlusslauf, Supportfall" in christian
    assert "Einfuehrungsprojekt" not in robert.split("STIMMPROFIL")[0]
    frames = cfg.COPY_RULES["role_frames"]
    assert "Robert Werner" in robert and "Christian Kulle" in christian
    # Was das eine Konto als Situation bekommt, sperrt das andere.
    assert any(re.search(rx, "Einführungsprojekt") for rx in frames["Robert Werner"]["verboten"])
    assert any(re.search(rx, "Datenübernahme") for rx in frames["Robert Werner"]["verboten"])
    assert any(re.search(rx, "Erstgespräch") for rx in frames["Christian Kulle"]["verboten"])
    assert not any(re.search(rx, "Workshop") for rx in frames["Christian Kulle"]["verboten"])


def test_tone_markers_separate_the_accounts_without_sentence_length():
    for kanal in ("LinkedIn Robert", "LinkedIn Christian"):
        v = cfg.ACCOUNT_VOICES[kanal]
        assert "TONMARKER" in v and "nie ueber Satzlaenge" in v
    assert "selbstironischer Halbsatz" in cfg.ACCOUNT_VOICES["LinkedIn Robert"]
    assert "Einschaetzung mit Vorbehalt" in cfg.ACCOUNT_VOICES["LinkedIn Christian"]


def test_each_voice_names_only_its_own_speaker():
    # VOICE_TICS und COPY_RULES["role_frames"] erkennen den Sprecher am Namen
    # im voice-String. Live-Check 08.09.2026: der Name des anderen Kontos im
    # Tonmarker gab Kulle Werners Rollensperre. Der Name des anderen darf
    # nirgends im Prompt-Teil vor dem Stimmprofil stehen.
    robert = cfg.ACCOUNT_VOICES["LinkedIn Robert"].split("STIMMPROFIL")[0]
    christian = cfg.ACCOUNT_VOICES["LinkedIn Christian"].split("STIMMPROFIL")[0]
    assert "Robert Werner" in robert and "Christian Kulle" not in robert
    assert "Christian Kulle" in christian and "Robert Werner" not in christian


def test_closing_rule_bridge_and_single_cta():
    assert "Bruecke" in cfg.CLOSING_RULE_DE and "endet nie mit einer Frage" in cfg.CLOSING_RULE_DE
    assert cfg.CLOSING_RULE_DE in cfg.ACCOUNT_VOICES["LinkedIn Robert"]
    assert cfg.COPY_RULES["cta_bridge"] is True
    assert cfg.COPY_RULES["address"] == "du"
    assert cfg.COPY_RULES["structure_max_repeat"] == 2
    assert cfg.STRUCTURE_REPLACEMENTS == [
        ("2-4 Annahme-gegen-Praxis-Paare", "zwei Annahme-gegen-Praxis-Paare, nie mehr")]


def test_term_map_follows_the_voc_corpus_and_bans_stay_wordlist_free():
    assert cfg.COPY_RULES["term_map"]["Cashforecast"] == "Liquiditätsplanung"
    assert cfg.COPY_RULES["term_map"]["Liquiditätsprognose"] == "Liquiditätsplanung"
    bans = cfg.TOKENS["LANGUAGE_BANS_DE"]
    # Der Schreib-Prompt nennt das richtige Wort, nie die falschen.
    assert "Liquiditaetsplanung" in bans
    assert "Cashforecast" not in bans and "Liquiditaetsprognose" not in bans
    assert "nie abwerten" in bans and "hoechstens zweimal" in bans
    assert "falsch gebaut" not in bans
