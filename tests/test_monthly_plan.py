"""Auswahllogik des Monatsplans: Raster, Fristen-Vorrang, Achsen-Quote,
Konto-Zuordnung. Reine Logik, kein Netz. Laeuft mit CLIENT=swot im Subprozess
NICHT — die Config wird direkt geladen, weil load_client den Default jolly
cachen wuerde."""
import os
import sys
from datetime import date

import pytest

os.environ["CLIENT"] = "swot"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients import load_client

load_client.cache_clear()
_cfg = load_client()
if _cfg.NAME != "swot":
    pytest.skip("braucht CLIENT=swot", allow_module_level=True)

from tools.monthly_plan import Topic, active_fristen, build_slots, select


def _topics(spec: dict[str, int], score0: int = 90) -> list[Topic]:
    out = []
    i = 0
    for axis, n in spec.items():
        for _ in range(n):
            out.append(Topic(page_id=f"p{i}", title=f"T{i}", title_de=f"T{i}",
                             keyword_de="kw", score=score0 - i, axis=axis))
            i += 1
    return out


def test_build_slots_oktober_2026():
    slots = build_slots(2026, 10)
    # Oktober 2026: Do 01., dann 4 volle Wochen. Jedes Konto 2 Slots je voller
    # Woche; Zaehlung gegen den Kalender, nicht gegen eine Wunschzahl.
    assert all(s.day.weekday() in (1, 2, 3) for s in slots)
    kulle = [s for s in slots if s.account == "kulle"]
    assert all(s.day.weekday() in (1, 3) for s in kulle)
    assert len({(s.day, s.account) for s in slots}) == len(slots)


def test_fristen_vorrang_und_konto():
    slots = build_slots(2026, 10)
    fristen = [{"id": "ifrs18", "label": "IFRS 18", "deadline": "2027-01-01"}]
    out = select(slots, [], fristen, _cfg.AXIS_MIX, _cfg.AXIS_TO_ACCOUNT)
    frist_slots = [s for s in out if s.frist]
    assert len(frist_slots) == 1
    assert frist_slots[0].account in _cfg.AXIS_TO_ACCOUNT["fristen"]


def test_dominante_achse_gedeckelt():
    slots = build_slots(2026, 10)
    total = len(slots)
    topics = _topics({"excel_am_limit": total})  # mehr Excel-Themen als Slots
    out = select(slots, topics, [], _cfg.AXIS_MIX, _cfg.AXIS_TO_ACCOUNT)
    excel = [s for s in out if s.axis == "excel_am_limit"]
    assert len(excel) <= int(total * (1 / 3))


def test_min_per_axis_greift():
    slots = build_slots(2026, 10)
    topics = _topics({"excel_am_limit": 10, "rechenschaft": 3,
                      "viele_einheiten": 3, "woher_die_zahlen": 3})
    out = select(slots, topics, [], _cfg.AXIS_MIX, _cfg.AXIS_TO_ACCOUNT)
    per = {}
    for s in out:
        if s.axis:
            per[s.axis] = per.get(s.axis, 0) + 1
    for ax in ("rechenschaft", "viele_einheiten", "woher_die_zahlen"):
        assert per.get(ax, 0) >= _cfg.AXIS_MIX["min_per_axis"], per


def test_konto_folgt_achse():
    slots = build_slots(2026, 10)
    topics = _topics({"rechenschaft": 4})
    out = select(slots, topics, [], _cfg.AXIS_MIX, _cfg.AXIS_TO_ACCOUNT)
    for s in out:
        if s.topic:
            assert s.account in _cfg.AXIS_TO_ACCOUNT[s.axis]


def test_thema_nur_einmal():
    slots = build_slots(2026, 10)
    topics = _topics({"excel_am_limit": 3, "rechenschaft": 3})
    out = select(slots, topics, [], _cfg.AXIS_MIX, _cfg.AXIS_TO_ACCOUNT)
    ids = [s.topic["page_id"] for s in out if s.topic]
    assert len(ids) == len(set(ids))


def test_leere_slots_bleiben_leer():
    slots = build_slots(2026, 10)
    topics = _topics({"rechenschaft": 1})
    out = select(slots, topics, [], _cfg.AXIS_MIX, _cfg.AXIS_TO_ACCOUNT)
    filled = [s for s in out if s.topic or s.frist]
    assert len(filled) == 1


def test_active_fristen_horizont():
    fr = active_fristen(date(2026, 10, 1), 120)
    ids = {f["id"] for f in fr}
    # 01.01.2027 liegt binnen 120 Tagen; AVR.DD (01.09.2026) ist aelter als 30 Tage.
    assert {"ifrs18", "erechnung", "avr_caritas"} <= ids
    assert "avr_dd" not in ids
