"""Natuerlichkeits-Stufe fuer deutsche Beitragstexte.

Anlass (Richard, 24.08.2026, zum Signature-Post "Glaube: ... Realitaet: ..."):
"niemand wuerde das Wort Glaube verwenden, das ist ein schlechter Ausdruck; du
musst die Posts in gutem und natuerlich klingendem Deutsch schreiben." Bis
dahin prueften Grammatik-Check und Textwache nur Rechtschreibung, Markdown,
Grossbuchstaben und Laenge. Niemand pruefte, ob ein Deutscher so redet.

Zwei Teile, nach dem Muster des JBA-Humanizer-Loops (Vault-Notiz "JBA Gate-2
Humanizer Closed-Loop", 18.07.2026), dort aber als bekannte Grenze notiert:
"Der Loop fixt nur, was der regelbasierte Scanner faengt. Haertungsoption:
LLM-Stil-Judge als zweite Detektionsstufe." Genau das hier:

1. Deterministisch (dieses Modul, kein Netz): Formeln, die das Modell
   reflexhaft baut (TICS), Formulierungen, die sich ueber einen Monats-Batch
   nicht wiederholen duerfen (phrases), Schachtelsaetze.
2. LLM-Lektor (Prompt hier, Aufruf in post_scorer): Note 1-10 plus Fundstellen
   mit dem Wortlaut, den ein Mensch gewaehlt haette. Unter NATURALNESS_MIN oder
   bei Tic-Treffern schreibt das Modell einmal neu, die bessere Fassung bleibt.

Massstab ist der Vault-Kontext "00 Kontext/Schreibstil": klar, direkt,
sachlich, kein Beratersprech, kein unnoetiges Englisch, kein Pathos, keine
Stilspielerei, natuerlich klingend statt Agenturmaschine.
"""
import json
import re

NATURALNESS_MIN = 7
MAX_SENTENCE_WORDS = 25

# Formeln, die das Modell in fast jedem Post baut. Messung 24.08.2026 ueber die
# acht Neufassungen: "Das ist kein X-Problem, das ist ein Y-Problem" in 5 von
# 8, Sentenz-Einzeiler in 6. "Nicht weil ..., sondern weil" steht bewusst NICHT
# hier: Kulle korrigiert Ursachen genau so (Stimmprofil 25.08.2026); der
# Lektor wiegt es mit dem Profil ab, die harte Liste wuerde es verbieten.
TICS = [
    ("kein X-Problem, sondern Y-Problem",
     re.compile(r"kein \S*problem[.,]? (?:das|es|sondern) (?:ist )?(?:ein )?\S*problem", re.I)),
    ("Nicht X. Nicht Y. Sondern Z.",
     re.compile(r"\bNicht [^.!?\n]{2,60}\. Nicht [^.!?\n]{2,60}\. Sondern\b")),
    ("X ist kein Y. Es ist ein Z.",
     re.compile(r"\bist kein \w+\. (?:Er|Sie|Es) ist (?:ein|eine) \w+\.")),
    ("Das Fatale/Tueckische",
     re.compile(r"\bDas (?:Fatale|Tückische|Bittere|Absurde|Perfide)\b")),
    ("Wer X, hat/bezahlt Y (Sentenz)",
     re.compile(r"^Wer [^.?!\n]{5,90}, (?:hat|bezahlt|verliert|merkt|bekommt) [^.?!\n]{2,90}\.$", re.M)),
    ("Glaube als Fachwort",
     re.compile(r"\bGlaube:|\bGlaube-gegen|\bGlaubens?satz\b")),
    # Lauf 3 (25.08.2026): mit Stimmprofil kopierte das Modell die gesprochene
    # Sprache samt Fuellwoertern ("halt", "irgendwie", Einstieg mit "Also,").
    ("Fuellwort der gesprochenen Sprache",
     re.compile(r"\b(?:halt|irgendwie|sozusagen|quasi)\b|(?:^|\n)Also,|\bne\?", re.I)),
    # Revision-2-Lauf (27.08.2026): die Beobachterposition wurde benannt statt
    # gezeigt, in 6 von 8 Beitraegen. Sie stand als fertiger Satzbaustein im
    # Prompt (SWOT _HERSTELLER_POSITION) und wurde abgeschrieben. Als weiche
    # avoid_phrase reichte sie nicht, deshalb jetzt harter Neulauf.
    ("Beobachterposition benannt statt gezeigt",
     re.compile(r"(?:In|Aus) (?:Einführungsprojekten|Projekten|Schulungen|Supportfällen)"
                r"[^.:,]{0,25}?(?:sehe|erlebe|höre) ich"
                r"|Was ich (?:in|bei) [^.:,]{3,40}(?:sehe|erlebe|höre)")),
]

# Formeln, die NUR fuer ein Konto eine Formel sind. "Nicht weil ..., sondern
# weil ..." ist Christian Kulles echte Konstruktion (Stimmprofil 25.08.2026)
# und steht deshalb nicht in TICS. Im Revision-2-Lauf am 27.08.2026 leakte sie
# aber zu Robert Werner: 2 Treffer je Konto, gleich verteilt. Der Schluessel
# wird im voice-String gesucht (ACCOUNT_VOICES nennt den Namen des Kontos);
# fehlt der Name, greift die Regel nicht.
VOICE_TICS = {
    "Robert Werner": [
        ("Fremdstimme: nicht weil, sondern weil (Kulle)",
         re.compile(r"\bicht,? weil\b[^.!?\n]{2,80}\bsondern weil\b", re.I)),
    ],
}

# Formulierungen, die je Konto und Monat nur einmal vorkommen duerfen. Die
# Beobachterposition ist erwuenscht, aber "In Einfuehrungsprojekten sehe ich"
# stand nach dem ersten Lauf in 7 von 8 Texten.
PHRASE_PATTERNS = [
    re.compile(r"(?:In|Aus) (?:Einführungsprojekten|Projekten|Schulungen|Supportfällen)"
               r"[^.:,]{0,25}?(?:sehe|erlebe|höre) ich"),
    re.compile(r"Ich (?:sehe|erlebe|höre) das (?:in [^.:,]{3,30}|immer wieder|regelmäßig|oft)"),
    re.compile(r"Was ich [^.:,]{3,40} (?:sehe|erlebe|höre)"),
    re.compile(r"Die (?:eigentliche|entscheidende|ehrliche|härteste|wichtigste) Frage"),
    re.compile(r"Die Frage, die (?:ich|mich) [^.:,]{3,30}"),
    re.compile(r"Das ist kein \S+, das ist \S+"),
    re.compile(r"Das ist kein \S+\. Das ist ein \S+\."),
]
CLOSING_QUESTION = "Schlussfrage"


def tic_hits(text: str, voice: str = "") -> list[str]:
    """Name plus Fundstelle je getroffener Formel, fuer Log und Neulauf.
    voice ist die Kontostimme: nennt sie den Sprecher eines VOICE_TICS-
    Eintrags, gelten dessen Fremdstimmen-Formeln zusaetzlich."""
    regeln = list(TICS)
    for sprecher, extra in VOICE_TICS.items():
        if sprecher in voice:
            regeln.extend(extra)
    out = []
    for name, rx in regeln:
        m = rx.search(text)
        if m:
            out.append(f"{name}: \"{m.group(0).strip()[:90]}\"")
    return out


def phrases(text: str) -> list[str]:
    """Verbrauchte Formulierungen dieses Textes: woertliche Treffer der
    PHRASE_PATTERNS plus die Marke CLOSING_QUESTION, wenn der Text mit einer
    Frage endet. Die Callsite sammelt sie je Konto ueber den Lauf."""
    seen, out = set(), []
    for rx in PHRASE_PATTERNS:
        for m in rx.finditer(text):
            s = m.group(0).strip()
            if s not in seen:
                seen.add(s)
                out.append(s)
    if text.rstrip().endswith("?"):
        out.append(CLOSING_QUESTION)
    return out


def long_sentences(text: str, max_words: int = MAX_SENTENCE_WORDS) -> list[str]:
    """Saetze ueber max_words Woertern. Zeilenumbruch zaehlt als Satzende,
    damit Listenzeilen nicht zusammenlaufen."""
    out = []
    for s in re.split(r"(?<=[.!?])\s+|\n+", text):
        s = s.strip()
        if len(s.split()) > max_words:
            out.append(s[:120])
    return out


def avoid_note(used: list[str] | None) -> str:
    """Prompt-Zusatz aus den verbrauchten Formulierungen des Laufs. Leer ohne
    Eintraege. Ab zwei Schlussfragen im Lauf endet der naechste Beitrag mit
    einer Feststellung."""
    used = used or []
    literal = [u for u in used if u != CLOSING_QUESTION]
    lines = []
    if literal:
        lines.append("SCHON VERBRAUCHT in diesem Monat auf diesem Konto, nicht wiederverwenden, "
                     "auch nicht sinngemaess umgestellt: " + " | ".join(dict.fromkeys(literal)))
    if used.count(CLOSING_QUESTION) >= 2:
        lines.append("Dieser Beitrag endet NICHT mit einer Frage, sondern mit einer Feststellung.")
    return ("\n\n" + "\n".join(lines)) if lines else ""


CRITIC_PROMPT = """Du bist Lektor für deutsche B2B-Fachtexte. Prüfe, ob der folgende LinkedIn-Beitrag klingt, als hätte ihn ein deutschsprachiger Fachmensch selbst geschrieben, oder wie eine Maschine, die Deutsch aus dem Englischen ableitet.
{voice_block}
Prüfliste, jeder Treffer kostet Punkte:
1. Kunstwörter und Substantivierungen, die niemand sagt (Übergabefähigkeit, Vertrauensereignis, Fortschreibungslogik). Ein Mensch sagt: "ob jemand anderes das Modell übernehmen kann".
2. Falsche Kollokationen und Lehnübersetzungen aus dem Englischen ("Glaube" statt Annahme, "macht Sinn", "am Ende des Tages", "Level", "Ownership").
3. Formeln: "Das ist kein X-Problem, das ist ein Y-Problem", "Nicht X. Nicht Y. Sondern Z.", "Nicht weil ..., sondern weil ...", "X ist kein Y. Es ist ein Z."
4. Pointen-Einzeiler als eigener Absatz, Doppelpunkt-Dramatik, Sentenzen ("Wer X, bezahlt Y").
5. Dreier-Parallelismen, gleich lange Sätze in Serie, Stakkato aus Fragmenten.
6. Reflexhafte Schlussfrage.
7. Beratersprech und Buzzwords (orchestrieren, harmonisieren, Hebel, skalieren, Mindset, Enabler).
8. Schachtelsätze über 25 Wörter, Nominalstil statt Verben.
9. Wiederholte Satzanfänge oder dieselbe Konstruktion mehrfach.
10. Pathos, Superlative, künstliche Dramatik.
{voice_item}
Note von 1 bis 10: 10 = so schreibt ein erfahrener Praktiker in einer ruhigen Minute, 7 = brauchbar mit Ecken, unter 6 = liest sich als Maschine.

Antworte NUR mit JSON, ohne Kommentar: {{"note": <1-10>, "fundstellen": ["<wörtliches Zitat>: <was daran unnatürlich ist, und wie ein Mensch es sagen würde>", ...]}} mit höchstens 5 Fundstellen, die schlimmsten zuerst.

TEXT:
{text}"""


_VOICE_BLOCK = """
MASSSTAB ist die Person, in deren Namen der Beitrag erscheint. So spricht und schreibt sie:
{voice}
"""
_VOICE_ITEM = ("11. Klingt der Text nach dieser Person? Wendungen, die sie laut Profil nie benutzen "
               "würde, Register, das nicht ihres ist, eine Haltung, die nicht ihre ist: kostet am "
               "meisten Punkte. Ein sauberer Text in fremder Stimme ist höchstens eine 6.")


def critic_prompt(text: str, voice: str = "") -> str:
    """Lektor-Prompt, mit Stimmprofil als Massstab, wenn eines vorliegt
    (Richard 25.08.2026: der Lektor soll "wuerde Robert das so sagen"
    pruefen, nicht nur "ist das Maschine")."""
    voice = (voice or "").strip()
    return CRITIC_PROMPT.format(
        text=text,
        voice_block=_VOICE_BLOCK.format(voice=voice) if voice else "",
        voice_item=("\n" + _VOICE_ITEM) if voice else "",
    )


def parse_verdict(raw: str) -> dict | None:
    """JSON des Lektors aus der Antwort ziehen. None, wenn nichts Brauchbares
    kommt: dann faellt die Stufe still auf 'kein Urteil' zurueck, statt einen
    guten Text wegen eines Parse-Fehlers neu zu schreiben."""
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        note = int(data.get("note"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    funde = [str(f) for f in (data.get("fundstellen") or [])][:5]
    return {"note": max(1, min(10, note)), "fundstellen": funde}


def rewrite_note(verdict: dict | None, tics: list[str], longs: list[str]) -> str:
    """Neulauf-Hinweis aus Lektor-Urteil und deterministischen Befunden."""
    lines = []
    if verdict:
        lines.append(f"Ein deutscher Lektor gibt dem Entwurf Note {verdict['note']} von 10. Fundstellen:")
        lines += [f"- {f}" for f in verdict["fundstellen"]]
    if tics:
        lines.append("Formeln, die eine Maschine verraten, nicht wieder bauen:")
        lines += [f"- {t}" for t in tics]
    if longs:
        lines.append(f"Saetze ueber {MAX_SENTENCE_WORDS} Woerter, aufteilen:")
        lines += [f"- {s}" for s in longs[:3]]
    return ("\n\nKORREKTUR: Schreibe den Beitrag neu, in Deutsch, wie ein Fachmensch es "
            "selbst schreiben wuerde. Gleicher Inhalt, gleiche Ausgabe-Struktur wie oben.\n"
            + "\n".join(lines))
