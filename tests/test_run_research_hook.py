"""Hook-Wahl im Winner-Flow: Rotation aus Notion plus Steuerung aus engine_meta.
Alles gemockt, kein Netz."""
import os
import sys
from datetime import date
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_research as rr


def test_choose_hook_uses_recent_hooks_and_steering(monkeypatch):
    monkeypatch.setattr(rr, "get_recent_hooks", lambda limit=20: ["contrarian", "warning"])
    monkeypatch.setattr(rr, "get_meta", lambda key: '{"stop": ["These"], "do_more": [], "as_of": "2026-10-01", "n": 10}')
    cfg = SimpleNamespace(NAME="jolly")
    # Debate: contrarian (These) gesperrt -> question_trap
    assert rr.choose_hook(cfg, "Debate", date(2026, 10, 5)) == "question_trap"


def test_choose_hook_survives_notion_and_meta_failures(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(rr, "get_recent_hooks", boom)
    monkeypatch.setattr(rr, "get_meta", boom)
    assert rr.choose_hook(SimpleNamespace(NAME="jolly"), "Opinion", date(2026, 10, 5)) == "contrarian"
