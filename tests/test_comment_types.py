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
    types_block = cd._types_block()
    for n in range(1, 10):
        assert f"{n}. " in types_block
    assert "Der Beleg" in types_block and "Der Reframe" in types_block and "Der Einzeiler" in types_block
    p = cd.COMMENT_PROMPT
    assert "{types}" in p
    assert "Toller Beitrag" in p and "Danke fürs Teilen" in p
    assert "{emoji_rule}" in p
    assert "kein Emoji als erstes Zeichen" in cd.EMOJI_ON and "kein Emoji als erstes Zeichen" in cd.EMOJI_OFF
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


class _SeqLLM(_FakeLLM):
    """Liefert die Antworten der Reihe nach."""
    def __init__(self, texts):
        super().__init__("")
        self.texts = list(texts)

    def create(self, **kw):
        self.text = self.texts.pop(0)
        return super().create(**kw)


LONG = ("Where it breaks down is when the prospect has done zero research beforehand "
        "and walks in genuinely disoriented and confused about the whole thing.")


def test_prompt_demands_plain_language_and_sentence_cap():
    p = cd.COMMENT_PROMPT.format(voice="", context="", influencer="Anna", post_text="",
                                 types=cd._types_block(), avoid="", length_rule=cd.LENGTH_RULE_DEFAULT,
                                 style_rules="", max_words=cd.MAX_SENTENCE_WORDS, emoji_rule=cd.EMOJI_ON)
    assert "Hoechstens 20 Woerter je Satz" in p and "Jargon" in p and "2 bis 4 Saetze" in p


def test_long_sentences_counts_words_per_sentence():
    assert cd.long_sentences("Kurz. Auch kurz!") == []
    assert cd.long_sentences(f"Kurz. {LONG}") == [LONG]


def test_draft_comment_retries_once_on_long_sentence(monkeypatch):
    fake = _SeqLLM([f"TYP: 4 x\n\n{LONG}", "TYP: 4 x\n\nKurz und klar."])
    monkeypatch.setattr(cd, "_llm", fake)
    d = cd.draft_comment(CFG, POST, "Jae")
    assert d["comment"] == "Kurz und klar."
    assert len(fake.prompts) == 2 and LONG in fake.prompts[1]


def test_emoji_rule_only_for_clients_that_want_it(monkeypatch):
    # Richard 15.09.2026: Jolly-Kommentare mit genau einem Emoji, andere Mandanten ohne
    jolly = SimpleNamespace(**vars(CFG), COMMENT_EMOJI=True)
    fake = _SeqLLM(["TYP: 4 x\n\nKurz und klar.", "TYP: 4 x\n\nKurz und klar. 🎯"])
    monkeypatch.setattr(cd, "_llm", fake)
    assert cd.draft_comment(jolly, POST, "Richard")["comment"] == "Kurz und klar. 🎯"
    assert cd.EMOJI_ON in fake.prompts[0] and "Emoji noetig" in fake.prompts[1]
    fake = _SeqLLM(["TYP: 4 x\n\nKurz und klar."])
    monkeypatch.setattr(cd, "_llm", fake)
    assert cd.draft_comment(CFG, POST, "Jae")["comment"] == "Kurz und klar."
    assert cd.EMOJI_OFF in fake.prompts[0]
    assert cd.comment_issues("🎯 Kurz.", emoji=True) and not cd.comment_issues("Kurz. 🚀", emoji=True)
    assert cd.comment_issues("Kurz — klar. 🚀", emoji=True) and cd.comment_issues("Kurz – klar.")


def test_draft_comment_drops_draft_when_retry_still_too_long(monkeypatch):
    monkeypatch.setattr(cd, "_llm", _SeqLLM([LONG, LONG]))
    assert cd.draft_comment(CFG, POST, "Jae") is None


STYLE = {"words": (30, 40), "humor": True, "banned_types": ["Der Beleg", "Der Einzeiler"],
         "brand_words": ["Jolly"]}
STYLE_POST = {"post_url": "https://www.linkedin.com/posts/y", "influencer": "Anna",
              "post_text": "Unsere Pipeline war drei Monate leer, weil der Vertrieb nur Bestandskunden betreut hat. " * 3}
GOOD = ("Drei Monate leere Pipeline kennt fast jeder Vertrieb, nur redet kaum einer so offen darüber. "
        "Bestandskunden fühlen sich sicher an, bis der Forecast plötzlich ehrlich wird. "
        "Wie plant ihr bei euch den Neukundenanteil danach fest ein? 📈")


def test_style_issues_measure_the_jolly_rules():
    # Richard 15.09.2026: 30 bis 40 Woerter, Floskeln, eine Frage, kein Pitch,
    # Anrede spiegelt den Post, Detail aus dem Post
    text = STYLE_POST["post_text"]
    assert cd.word_count("Kurz und klar. 🎯") == 3
    assert cd.style_issues(GOOD, text, STYLE) == ["Der Autor duzt nicht: neutral schreiben, ohne du"]
    du_post = text + " Wie ist das bei dir?"
    assert cd.style_issues(GOOD, du_post, STYLE) == []
    assert any("Woerter" in i for i in cd.style_issues("Zu kurz. Pipeline.", text, STYLE))
    assert any("Floskel" in i and "danke fürs teilen" in i
               for i in cd.style_issues("Danke fürs Teilen! " + GOOD, du_post, STYLE))
    assert not any("Floskel" in i for i in cd.style_issues(GOOD.replace("offen", "absolute"), du_post, STYLE))
    assert any("eine Frage" in i for i in cd.style_issues(GOOD.replace(".", "?"), du_post, STYLE))
    assert any("Jolly" in i for i in cd.style_issues(GOOD + " Bei Jolly auch.", du_post, STYLE))
    assert any("Sie" in i for i in cd.style_issues(GOOD.replace("plant ihr bei euch", "planen Sie bei Ihnen"), du_post, STYLE))
    assert not any("Sie" in i for i in cd.style_issues("Sie reden kaum darüber. " + GOOD, du_post, STYLE))
    fremd = "Das Wetter heute ist schön und warm, wir gehen später alle gemeinsam an den See baden. " * 2
    assert any("Detail" in i for i in cd.style_issues(fremd, du_post, STYLE))


def test_style_prompt_bans_types_and_gates_humor_on_ernst(monkeypatch):
    jolly = SimpleNamespace(**vars(CFG), COMMENT_STYLE=STYLE)
    fake = _FakeLLM(f"TYP: 4 x\n\n{GOOD}")
    monkeypatch.setattr(cd, "_llm", fake)
    cd.draft_comment(jolly, dict(STYLE_POST, ernst=False), "Richard")
    p = fake.prompts[0]
    assert "Der Beleg" not in p and "Der Einzeiler" not in p and "8. Der Reframe" in p
    assert "30 bis 40 Woerter" in p and "Nie Jolly erwähnen" in p and cd.HUMOR_ON in p
    for ernst in (True, None):
        cd.draft_comment(jolly, dict(STYLE_POST, ernst=ernst), "Richard")
        assert cd.HUMOR_OFF in fake.prompts[-1] and cd.HUMOR_ON not in fake.prompts[-1]
    # andere Mandanten unveraendert: alle Typen, alte Laengenregel, kein Stil-Block
    cd.draft_comment(CFG, POST, "Jae")
    assert "Der Beleg" in fake.prompts[-1] and "2 bis 4 Saetze, nie laenger." in fake.prompts[-1]
    assert "Nie Sie" not in fake.prompts[-1]


def test_style_violation_retries_then_drops(monkeypatch):
    jolly = SimpleNamespace(**vars(CFG), COMMENT_STYLE=STYLE)
    du_post = dict(STYLE_POST, post_text=STYLE_POST["post_text"] + " Wie ist das bei dir?")
    fake = _SeqLLM(["TYP: 4 x\n\nToller Beitrag! Pipeline.", f"TYP: 4 x\n\n{GOOD}"])
    monkeypatch.setattr(cd, "_llm", fake)
    assert cd.draft_comment(jolly, du_post, "Richard")["comment"] == GOOD
    assert "Woerter, erlaubt sind 30 bis 40" in fake.prompts[1]
    monkeypatch.setattr(cd, "_llm", _SeqLLM(["Pipeline.", "Pipeline."]))
    assert cd.draft_comment(jolly, du_post, "Richard") is None


def test_draft_comment_names_the_type_to_avoid(monkeypatch):
    fake = _FakeLLM("TYP: 2 Fehlender Fall\nANSATZ: x\n\nText.")
    monkeypatch.setattr(cd, "_llm", fake)
    cd.draft_comment(CFG, POST, "Jae", avoid_types=["6 Der Beleg"])
    assert "6 Der Beleg" in fake.prompts[0] and "NICHT" in fake.prompts[0]
    cd.draft_comment(CFG, POST, "Jae")
    assert "NICHT diesen Typ" not in fake.prompts[1]


def test_style_issues_flag_templates_and_topic_emoji():
    # Richard 23.09.2026: "blutleer, klingt nach KI". Schablonen aus den alten
    # Typ-Beschreibungen und Themen-Emoji als Deko fallen messbar auf.
    du_post = STYLE_POST["post_text"] + " Wie ist das bei dir?"
    for bad in ("Das stimmt, solange der Vertrieb mitzieht.", "Die meisten Teams merken das spät.",
                "Anders gelesen: das ist Pipeline.", "Das ist kein Tool-Problem, sondern Führung.",
                "Der Satz trifft es gut."):
        assert any("Schablonensatz" in i for i in cd.style_issues(bad + " " + GOOD, du_post, STYLE)), bad
    for topic in ("💡", "🗺️"):
        assert any("Themen-Emoji" in i for i in cd.style_issues(GOOD.replace("📈", topic), du_post, STYLE)), topic
    assert cd.style_issues(GOOD.replace("📈", "😅"), du_post, STYLE) == []


def test_value_gate_retries_then_drops(monkeypatch):
    jolly = SimpleNamespace(**vars(CFG), COMMENT_STYLE=dict(STYLE, value_gate=True))
    du_post = dict(STYLE_POST, post_text=STYLE_POST["post_text"] + " Wie ist das bei dir?")
    fake = _SeqLLM([f"TYP: 4 x\n\n{GOOD}", "NEIN\nNur Zustimmung.",
                    f"TYP: 4 x\n\n{GOOD}", "JA\nKonkreter Test."])
    monkeypatch.setattr(cd, "_llm", fake)
    assert cd.draft_comment(jolly, du_post, "Richard")["comment"] == GOOD
    assert "Nur Zustimmung." in fake.prompts[2]
    monkeypatch.setattr(cd, "_llm", _SeqLLM([f"TYP: 4 x\n\n{GOOD}", "NEIN\nx",
                                             f"TYP: 4 x\n\n{GOOD}", "vielleicht"]))
    assert cd.draft_comment(jolly, du_post, "Richard") is None


def test_retries_setting_allows_second_retry(monkeypatch):
    # Richard 23.09.2026: ein Nachversuch warf 9 von 17 Entwuerfen weg
    jolly = SimpleNamespace(**vars(CFG), COMMENT_STYLE=dict(STYLE, retries=2))
    du_post = dict(STYLE_POST, post_text=STYLE_POST["post_text"] + " Wie ist das bei dir?")
    fake = _SeqLLM([f"TYP: 4 x\n\n{LONG}", f"TYP: 4 x\n\n{LONG}", f"TYP: 4 x\n\n{GOOD}"])
    monkeypatch.setattr(cd, "_llm", fake)
    assert cd.draft_comment(jolly, du_post, "Richard")["comment"] == GOOD
