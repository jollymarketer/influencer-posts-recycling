"""Hook-Katalog: gepinnt wie die Formatstrukturen. Rotation und Steuerung
rein deterministisch. Kein Netz."""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import hooks
from tools.content_matrix import FORMAT_ASSET_ATTR
from tools.post_scorer import FORMAT_STRUCTURES


def test_catalog_has_seventeen_complete_entries():
    assert len(hooks.HOOKS) == 17
    for hid, h in hooks.HOOKS.items():
        assert hid == hid.lower() and " " not in hid
        for key in ("name", "family", "template_de", "template_en", "trap_de"):
            assert h[key].strip(), f"{hid} ohne {key}"


def test_every_format_has_hooks_and_every_hook_a_family():
    assert set(hooks.HOOKS_BY_FORMAT) == set(FORMAT_STRUCTURES)
    for fmt, ids in hooks.HOOKS_BY_FORMAT.items():
        assert ids, fmt
        assert all(i in hooks.HOOKS for i in ids), fmt
    in_families = [i for ids in hooks.HOOK_FAMILIES.values() for i in ids]
    assert sorted(in_families) == sorted(hooks.HOOKS)
    for hid, h in hooks.HOOKS.items():
        assert hooks.family_of(hid) == h["family"]
        assert hid in hooks.HOOK_FAMILIES[h["family"]]


def test_number_hooks_only_in_asset_formats():
    for fmt, ids in hooks.HOOKS_BY_FORMAT.items():
        if fmt not in FORMAT_ASSET_ATTR:
            assert not (set(ids) & hooks.NUMBER_HOOKS), fmt


def test_signature_keeps_its_own_single_formula():
    assert hooks.HOOKS_BY_FORMAT["Signature"] == ("assumption",)


def test_pick_hook_takes_the_longest_unused_candidate():
    # recent: neueste zuerst. warning nie genutzt -> zuerst dran.
    assert hooks.pick_hook("Opinion", ["contrarian", "myth_bust", "unpopular_rule"]) == "warning"
    # alle genutzt: der am laengsten zurueckliegende (unpopular_rule, Index 3)
    assert hooks.pick_hook("Opinion", ["contrarian", "myth_bust", "warning", "unpopular_rule"]) == "unpopular_rule"


def test_pick_hook_tie_falls_back_to_catalog_order_and_signature_is_fixed():
    assert hooks.pick_hook("Opinion", []) == "contrarian"
    assert hooks.pick_hook("Signature", ["assumption"]) == "assumption"
    assert hooks.pick_hook("Unbekannt", []) == "contrarian"   # Rueckfall Opinion


def test_pick_hook_stop_blocks_family_but_never_the_whole_format():
    st = {"stop": ["These"], "do_more": [], "as_of": "2026-10-05", "n": 20}
    assert hooks.pick_hook("Debate", [], st) == "question_trap"       # contrarian (These) gesperrt
    assert hooks.pick_hook("Opinion", [], st) == "contrarian"          # nur These -> STOP ignoriert


def test_pick_hook_do_more_halves_the_wait():
    recent = ["mistake", "cold_open", "walk_away"]
    assert hooks.pick_hook("Story", recent) == "walk_away"
    # Comparison: comparison (Frage) vor 1 Post, warning (These) vor 2 Posts.
    st2 = {"stop": [], "do_more": ["Frage"], "as_of": "2026-10-05", "n": 20}
    assert hooks.pick_hook("Comparison", ["comparison", "warning"]) == "warning"
    assert hooks.pick_hook("Comparison", ["comparison", "warning"], st2) == "comparison"


def test_load_steering_expires_after_sixty_days_and_survives_garbage():
    raw = '{"stop": ["These"], "do_more": [], "as_of": "2026-09-01", "n": 12}'
    assert hooks.load_steering(raw, date(2026, 10, 1))["stop"] == ["These"]
    assert hooks.load_steering(raw, date(2026, 11, 15)) == {}
    assert hooks.load_steering("", date(2026, 10, 1)) == {}
    assert hooks.load_steering("kein json", date(2026, 10, 1)) == {}
    assert hooks.load_steering('{"stop": []}', date(2026, 10, 1)) == {}
