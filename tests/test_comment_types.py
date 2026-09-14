"""Kommentar-Typen (Repo-Vergleich linkedin-agent-skill, 14.09.2026, li-comment):
neun Kommentar-Typen im Prompt, TYP-Zeile im Output, Typ im Titel, der
zuletzt verwendete Typ wird im Lauf gemieden. Kein Netz."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import comment_drafts as cd


class _FakeLLM:
    def __init__(self, text):
        self.text = text
        self.prompts = []
        self.messages = self

    def create(self, **kw):
        self.prompts.append(kw["messages"][0]["content"])
        return SimpleNamespace(content=[SimpleNamespace(text=self.text)])


CFG = SimpleNamespace(CONTEXT="Kontext.", TOKENS={"PERSONA_DE": "Du bist Jae."},
                      CONTENT_PERSONAS=[], POSTER_BY_PERSONA={})
POST = {"post_url": "https://www.linkedin.com/posts/x", "post_text": "Ein Post " * 20,
        "influencer": "Anna"}


def test_prompt_lists_nine_types_and_german_banned_openers():
    p = cd.COMMENT_PROMPT
    for n in range(1, 10):
        assert f"\n{n}. " in p
    assert "Der Beleg" in p and "Der Reframe" in p and "Der Einzeiler" in p
    assert "Toller Beitrag" in p and "Danke fürs Teilen" in p
    assert "kein Emoji als erstes Zeichen" in p
    assert "TYP: " in p


def test_draft_comment_parses_typ_and_ansatz_header(monkeypatch):
    fake = _FakeLLM("TYP: 6 Der Beleg\nANSATZ: eigener Fall Terminologie\n\n"
                    "Bei uns dauerte das drei Wochen. Der Grund lag im Glossar.")
    monkeypatch.setattr(cd, "_llm", fake)
    d = cd.draft_comment(CFG, POST, "Jae")
    assert d["comment"] == "Bei uns dauerte das drei Wochen. Der Grund lag im Glossar."
    assert d["typ"] == "6 Der Beleg"
    assert d["title"] == "Kommentar Jae [6 Der Beleg]: eigener Fall Terminologie"


def test_draft_comment_without_header_keeps_whole_text(monkeypatch):
    monkeypatch.setattr(cd, "_llm", _FakeLLM("Nur der Kommentar."))
    d = cd.draft_comment(CFG, POST, "Jae")
    assert d["comment"] == "Nur der Kommentar." and d["typ"] == ""
    assert d["title"] == "Kommentar Jae: Anna"


def test_draft_comment_names_the_type_to_avoid(monkeypatch):
    fake = _FakeLLM("TYP: 2 Fehlender Fall\nANSATZ: x\n\nText.")
    monkeypatch.setattr(cd, "_llm", fake)
    cd.draft_comment(CFG, POST, "Jae", avoid_types=["6 Der Beleg"])
    assert "6 Der Beleg" in fake.prompts[0] and "NICHT" in fake.prompts[0]
    cd.draft_comment(CFG, POST, "Jae")
    assert "NICHT diesen Typ" not in fake.prompts[1]
