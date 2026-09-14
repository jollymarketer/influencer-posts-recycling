"""Hook-Zeile ersetzt Zeile 1 der Formatstruktur. Kein Netz."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import hooks
from tools import post_scorer as ps

POST = {"influencer": "Anna", "post_text": "Quelle " * 30}


def test_hook_line_carries_name_template_and_trap():
    line = hooks.hook_line("contrarian", "de")
    assert line.startswith("1. Hook (1-2 Sätze), Formel Contrarian Take: ")
    assert "Alle sagen" in line and "Falle: Widerspruch" in line
    assert line.endswith("Entscheidet, ob jemand weiterliest.")
    en = hooks.hook_line("contrarian", "en")
    assert en.startswith("1. Hook (1-2 sentences), formula Contrarian Take: ")
    assert "Everyone says" in en and "Trap: " in en


def test_inject_hook_replaces_only_the_hook_line():
    de = ps.FORMAT_STRUCTURES["Opinion"]["de"]
    out = hooks.inject_hook(de, "warning", "de")
    assert out.count("\n") == de.count("\n")
    assert "Formel Warning" in out
    assert "kontroverse These" not in out
    rest_alt = "\n".join(de.splitlines()[2:])
    assert rest_alt in out
    assert hooks.inject_hook(de, "", "de") == de
    assert hooks.inject_hook("keine Struktur", "warning", "de") == "keine Struktur"


def test_format_prompts_take_the_hook_in_both_languages():
    de, en = ps._format_prompts(POST, "Opinion", hook_id="myth_bust")
    assert "Formel Myth Bust" in de and "Gängige Erklärung" in de
    assert "formula Myth Bust" in en and "Popular explanation" in en
    de0, _ = ps._format_prompts(POST, "Opinion")
    assert "Formel Myth Bust" not in de0 and "kontroverse These" in de0


def test_kurz_band_has_no_hook_line_and_stays_untouched():
    de, _ = ps._format_prompts(POST, "Opinion", band="kurz", hook_id="myth_bust")
    assert "Formel Myth Bust" not in de and "These in einem Satz" in de
