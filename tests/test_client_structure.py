"""Abschluss- und Strukturregeln je Mandant im Schreib-Prompt
(post_scorer._client_structure, 08.09.2026). Ohne Config-Eintrag bleibt
jeder Block byte-identisch."""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer as ps

RULE = "Der letzte Absatz ist eine Bruecke, keine Frage."


def test_without_config_blocks_are_unchanged():
    with patch.object(ps._cfg, "CLOSING_RULE_DE", "", create=True), \
         patch.object(ps._cfg, "STRUCTURE_REPLACEMENTS", None, create=True):
        for fmt, variants in ps.FORMAT_STRUCTURES.items():
            assert ps._client_structure(variants["de"]) == variants["de"]
        assert ps._client_structure(ps.KURZ_STRUCTURE["de"]) == ps.KURZ_STRUCTURE["de"]


def test_closing_rule_replaces_every_open_loop_line():
    with patch.object(ps._cfg, "CLOSING_RULE_DE", RULE, create=True), \
         patch.object(ps._cfg, "STRUCTURE_REPLACEMENTS", None, create=True):
        for fmt, variants in ps.FORMAT_STRUCTURES.items():
            out = ps._client_structure(variants["de"])
            assert f"4. Abschluss: {RULE}" in out, fmt
            assert "Offene Schleife" not in out, fmt
            assert "streitbare Frage" not in out, fmt
            # Alle anderen Zeilen bleiben.
            assert out.count("\n") == variants["de"].count("\n"), fmt
        kurz = ps._client_structure(ps.KURZ_STRUCTURE["de"])
        assert f"3. Abschluss: {RULE}" in kurz and "streitbare Frage" not in kurz


def test_structure_replacements_apply_where_the_anchor_exists():
    pairs = [("2-4 Annahme-gegen-Praxis-Paare", "zwei Annahme-gegen-Praxis-Paare, nie mehr")]
    with patch.object(ps._cfg, "CLOSING_RULE_DE", "", create=True), \
         patch.object(ps._cfg, "STRUCTURE_REPLACEMENTS", pairs, create=True):
        sig = ps._client_structure(ps.FORMAT_STRUCTURES["Signature"]["de"])
        assert "zwei Annahme-gegen-Praxis-Paare, nie mehr" in sig
        assert "2-4 Annahme" not in sig
        op = ps.FORMAT_STRUCTURES["Opinion"]["de"]
        assert ps._client_structure(op) == op


def test_format_prompts_use_the_client_structure():
    post = {"influencer": "x", "post_text": "Thema: T\nKurzbeschreibung: K",
            "likes": 0, "comments": 0, "shares": 0}
    with patch.object(ps._cfg, "CLOSING_RULE_DE", RULE, create=True), \
         patch.object(ps._cfg, "STRUCTURE_REPLACEMENTS", None, create=True):
        de, en = ps._format_prompts(post, "Signature")
        assert RULE in de
        assert "Offene Schleife" not in de
        # EN-Prompt bleibt unberuehrt.
        assert "open loop" in en
