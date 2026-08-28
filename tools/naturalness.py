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
2. Leser (READER_PROMPT hier, Aufruf in post_scorer._reader_loop): sieben
   Fragen mit Zitatpflicht, Befundliste statt Note. Befunde werden
   chirurgisch repariert; verworfen wird ein Text nur bei harten
   Restbefunden (Sinnfehler, HARD_ARTEN) oder Textwache, weiche Reste
   bleiben mit Log stehen, und eine Reparatur, die harte Befunde erst
   einbaut, faellt auf das Original zurueck. Stand 28.08.2026, Spec
   docs/superpowers/specs/2026-08-28-leser-gate-design.md. Der Lektor mit
   Note 1-10 (24.08. bis 28.08.) mittelte Defekte weg: ein kaputter Opener
   plus neun saubere Absaetze ergab eine 7.

Massstab ist der Vault-Kontext "00 Kontext/Schreibstil": klar, direkt,
sachlich, kein Beratersprech, kein unnoetiges Englisch, kein Pathos, keine
Stilspielerei, natuerlich klingend statt Agenturmaschine.
"""
import json
import re

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
    # Abschluss-Review 28.08.2026: Leser-Frage 5 nimmt seit der Verengung auf
    # Strukturformeln die einzelne Antithese ausdruecklich aus, und keine
    # Regex fing die nackte Form. Damit blieb der Grunddefekt der Spec
    # ("baut kein Modell, sondern eine persoenliche Ueberzeugung") ungefangen.
    # Der Ausschluss von "sondern weil/dass/damit" haelt Kulles echte
    # Kausalkonstruktion draussen (siehe VOICE_TICS, sie ist kein Tic).
    ("kein A, sondern B (Antithese)",
     re.compile(r"\bkein(?:e|en|em|er|es)? [^.,;:!?\n]{2,40}, sondern "
                r"(?!weil\b|dass\b|damit\b)(?:ein|eine|einen|einem|einer)? ?"
                r"[^.,;:!?\n]{2,60}", re.I)),
]

# Formeln, die NUR fuer ein Konto eine Formel sind. "Nicht weil ..., sondern
# weil ..." ist Christian Kulles echte Konstruktion (Stimmprofil 25.08.2026)
# und steht deshalb nicht in TICS. Im Revision-2-Lauf am 27.08.2026 leakte sie
# aber zu Robert Werner: 2 Treffer je Konto, gleich verteilt. Der Schluessel
# wird im voice-String gesucht (ACCOUNT_VOICES nennt den Namen des Kontos);
# fehlt der Name, greift die Regel nicht.
VOICE_TICS = {
    "Robert Werner": [
        ("Fremdstimme nicht weil, sondern weil (Kulle)",
         re.compile(r"\bnicht,? weil\b[^.!?\n]{2,160}\bsondern,? weil\b", re.I)),
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


# Leser statt Lektor (Richard 28.08.2026, Spec docs/superpowers/specs/
# 2026-08-28-leser-gate-design.md). Anlass: "Den 13-Wochen-Cashforecast baut
# man einmal auf und denkt, die Zahlen muessen stimmen. Stimmen sie nicht. Und
# das ist in Ordnung." Verberststellung, Opener gegen Text, rollierender
# Forecast "einmal" gebaut: keine der drei Stellen fiel dem Lektor auf, weil
# eine Note mittelt und elf Stilpunkte keinen Sinn pruefen. Der Leser stellt
# Fragen mit Zitatpflicht; jeder Befund ist eine Reparatur, keine Note.
# Der Leser darf Beispiel-Wortlaute tragen: er schreibt nichts ab. Verbots-
# listen mit Wortlaut gehoeren deshalb hierher, nie in den Schreib-Prompt.
FINDING_ARTEN = ("schriftdeutsch", "kohaerenz", "deckung", "fachlogik",
                 "schablone", "muendlich", "fremdstimme", "satzlaenge")
# Sinnfehler: nur sie verwerfen einen Text nach der letzten Reparaturrunde.
# Stil-Reste (Schablone, Fremdstimme, Muendlich, Satzlaenge) bleiben mit Log
# stehen (Trockenlauf 28.08.2026: der Reparierer ersetzt Formeln durch
# Formeln, harte Verwerfung leerte 3 von 3 Texten).
HARD_ARTEN = ("schriftdeutsch", "kohaerenz", "deckung", "fachlogik")
MAX_FINDINGS = 6

READER_PROMPT = """Du liest einen deutschen LinkedIn-Beitrag als strenger, aber fairer Fachlektor mit Controlling-Hintergrund. Du bewertest nicht, du findest Defekte, die ein Lektor tatsächlich ändern würde, und belegst jeden mit einem wörtlichen Zitat aus dem Text. Ein sauberer Text hat null Befunde. Im Zweifel kein Befund: jeder Fehlalarm löst eine Reparatur aus, die den Text verschlechtert.
{voice_block}
MATERIAL, das der Beitrag einlösen soll:
{material}

Sieben Fragen. Jede Antwort ist entweder "nichts gefunden" oder ein Befund mit Zitat:
1. schriftdeutsch: Gibt es einen Satz, der als geschriebenes Deutsch nicht korrekt ist? Nur: ein Aussagesatz mit dem Verb an erster Stelle, der weder Frage noch Befehl noch Bedingungssatz ist ("Stimmen sie nicht." als Antwort auf den Satz davor); fehlendes Subjekt oder Verb; ein Fragment, das der Leser als abgebrochenen Nebensatz liest. Kein Befund: uneingeleitete Bedingungssätze ("Stimmen Planung und Gliederung nicht überein, entsteht doppeltes Rechnen"), Ellipsen mit Modalverb ("wo er hin will"), bewusst kurze vollständige Sätze.
2. kohaerenz: Behauptet der erste Absatz etwas, das der Rest widerlegt? Nur, wenn beide Stellen zusammen unvereinbar sind. Kein Befund: der Rest vertieft oder erweitert den Opener, nennt die Ursache hinter dem Symptom oder wechselt zur Lösung. Zitiere beide Stellen im Feld zitat, getrennt durch " | ", und nenne im Feld grund, warum sie einander ausschließen. Stimme und Register gehören zu Frage 7, nicht hierher.
3. deckung: Löst der Text ein, was das Material verspricht? Nur, wenn ein versprochener Teil fehlt oder der Text von etwas anderem handelt.
4. fachlogik: Gibt es eine Aussage, die ein Controller oder Wirtschaftsprüfer als falsch erkennt? Nur Verfahren, Fristen, Fachbegriffe und Zahlen, und nur, wenn du die richtige Fassung nennen kannst (Norm mit Paragraf, Datum, Zahl). Ein rollierender Forecast, der monatlich um einen Monat vorrückt, ist korrekt beschrieben; falsch wäre ein rollierender Forecast, der "einmal" gebaut wird. Kein Befund: Vorschläge, die die Aussage nur umformulieren; Kritik an Belegdichte oder Formulierung; Normen, deren Fundstelle du nicht sicher weißt.
5. schablone: Gibt es Strukturformeln, die eine eigene Pointe tragen? Nur: Negation-Negation-Korrektur ("Nicht A. Nicht B. Sondern C."), Pointen-Einzeiler als eigener Absatz ohne neuen Sachverhalt, Dreier-Parallelismus mit gleichem Satzbau, Absolution nach der Pointe ("Und das ist in Ordnung."), dieselbe Antithese ("kein A, sondern B") mehr als einmal im Text. Kein Befund: eine einzelne Antithese, ein einzelner Satz, der mit "Wer" beginnt, ein Kontrast im Satzinneren, eine sachliche Aufzählung, Wendungen, die der Maßstab als typisch für die Person nennt.
6. muendlich: Nur Wörter dieser abschließenden Liste: halt, irgendwie, sozusagen, quasi, "Also," am Satzanfang, "ne?"; dazu Verständnisfragen an den Leser als Floskel ("Kennst du das?", "Ist das soweit klar?"). Kein Befund: kurze vollständige Sätze, "also" im Satzinneren, "irgendwann", "tatsächlich", Herkunftsangaben wie "in Schulungen".
7. fremdstimme: Nur drei Fälle. Erstens Beratersprech und Lehnübersetzungen dieser Art: Mehrwert schaffen, ganzheitlich, Hebel, orchestrieren, skalieren, Mindset, Enabler, macht Sinn, am Ende des Tages, Ownership, Level, Game Changer. Zweitens Neubildungen ohne Wörterbucheintrag (Übergabefähigkeit, Vertrauensereignis, Fortschreibungslogik); gewöhnliche Wörter wie Übergabe, Brücke, Stand sind keine. Drittens eine Passage, die eine Regel des Maßstabs verletzt; dann zitierst du im Feld grund die verletzte Regel wörtlich, sonst gilt der Befund nicht. Die Herkunft der eigenen Kenntnis zu benennen ("in Einführungsprojekten sehe ich") ist nur dann ein Befund, wenn der Maßstab es ausdrücklich verbietet.

Antworte NUR mit JSON, ohne Kommentar:
{{"befunde": [{{"art": "<schriftdeutsch|kohaerenz|deckung|fachlogik|schablone|muendlich|fremdstimme>", "zitat": "<wörtlich aus dem Text>", "grund": "<ein Satz>", "vorschlag": "<so schreibt es ein Mensch>"}}]}}
Leere Liste, wenn nichts gefunden. Höchstens {max_findings} Befunde, die schwersten zuerst. Kein Befund ohne wörtliches Zitat.

TEXT:
{text}"""

_READER_VOICE_BLOCK = """
MASSSTAB für die Fragen 5 und 7 ist die Person, in deren Namen der Beitrag erscheint. So spricht und schreibt sie:
{voice}
"""

# Antwortformat als Schema fuer Structured Output (Sonde 28.08.2026: mit
# "Antworte NUR mit JSON" schrieb Sonnet 4.6 erst eine Prosa-Analyse samt
# Volltext-Zitat und lief bei 1024 Tokens ins Limit, 7 von 12 Antworten ohne
# JSON). Prefill gibt es auf Sonnet 4.6 nicht mehr; output_config erzwingt
# das JSON als ersten Textblock. "satzlaenge" ist deterministisch und kein
# Leser-Befund. Laengen und Anzahl kappt parse_findings, nicht das Schema.
READER_SCHEMA = {
    "type": "object",
    "properties": {
        "befunde": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "art": {"type": "string",
                            "enum": [a for a in FINDING_ARTEN if a != "satzlaenge"]},
                    "zitat": {"type": "string"},
                    "grund": {"type": "string"},
                    "vorschlag": {"type": "string"},
                },
                "required": ["art", "zitat", "grund", "vorschlag"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["befunde"],
    "additionalProperties": False,
}


def reader_prompt(text: str, material: str = "", voice: str = "") -> str:
    """Leser-Prompt: Text, Material (Thema und Kurzbeschreibung oder Quell-
    Post) und das Stimmprofil als Massstab, wenn eines vorliegt."""
    voice = (voice or "").strip()
    return READER_PROMPT.format(
        text=text,
        material=(material or "").strip() or "(kein Material)",
        voice_block=_READER_VOICE_BLOCK.format(voice=voice) if voice else "",
        max_findings=MAX_FINDINGS,
    )


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _quote_in_text(zitat: str, text: str) -> bool:
    """Jeder Zitat-Teil (bei kohaerenz durch " | " getrennt) muss woertlich im
    Text stehen, Whitespace normalisiert. Erfundene Zitate fallen raus; die
    Reparatur muss die Passage sonst nicht finden."""
    t = _norm(text)
    return all(_norm(part) in t for part in zitat.split(" | ") if _norm(part))


QUOTE_CAP = 200


def _cap_quote(zitat: str) -> str:
    """Jeden Zitat-Teil einzeln auf QUOTE_CAP kappen. Abschluss-Review
    28.08.2026: ein kohaerenz-Zitat traegt zwei Passagen, getrennt durch
    " | ", und ist zusammen oft laenger als 200 Zeichen. Der Schnitt ueber
    das ganze Zitat kappte mitten im Wort und die zweite Passage weg; der
    Reparierer fand die Stelle dann nicht mehr."""
    return " | ".join(part[:QUOTE_CAP] for part in zitat.split(" | "))


def parse_findings(raw: str, text: str | None = None) -> list[dict] | None:
    """Befundliste aus der Leser-Antwort. None bei unlesbarer Antwort (dann
    kein Urteil, der Text bleibt). Befunde ohne Zitat oder mit Zitat, das
    nicht im Text steht, werden verworfen. Hoechstens MAX_FINDINGS."""
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        items = data.get("befunde")
    except (ValueError, AttributeError):
        return None
    if not isinstance(items, list):
        return None
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        zitat = str(it.get("zitat") or "").strip()
        if not zitat or (text is not None and not _quote_in_text(zitat, text)):
            continue
        art = str(it.get("art") or "").strip().lower()
        out.append({
            "art": art if art in FINDING_ARTEN else "sonstiges",
            "zitat": _cap_quote(zitat),
            "grund": str(it.get("grund") or "").strip()[:200],
            "vorschlag": str(it.get("vorschlag") or "").strip()[:300],
        })
    return out[:MAX_FINDINGS]


def deterministic_findings(text: str, voice: str = "") -> list[dict]:
    """Regex-Formeln und Satzlaengen als Befunde derselben Form, damit die
    Reparatur eine Liste bekommt. Die Regex-Liste waechst nicht mehr; der
    Leser ist der allgemeine Fang."""
    out = []
    for hit in tic_hits(text, voice):
        name, _, zitat = hit.partition(": ")
        out.append({"art": "schablone", "zitat": zitat.strip().strip('"'),
                    "grund": name, "vorschlag": ""})
    for s in long_sentences(text):
        out.append({"art": "satzlaenge", "zitat": s,
                    "grund": f"ueber {MAX_SENTENCE_WORDS} Woerter",
                    "vorschlag": "in zwei Saetze teilen"})
    return out


def findings_note(findings: list[dict]) -> str:
    """Befunde als Zeilen fuer den Reparatur-Prompt und das Log."""
    lines = []
    for f in findings:
        line = f"- [{f['art']}] \"{f['zitat']}\": {f['grund']}"
        if f.get("vorschlag"):
            line += f" Vorschlag: {f['vorschlag']}"
        lines.append(line)
    return "\n".join(lines)


# Kuerzester Kern, der eine Dublette belegen darf. Abschluss-Review
# 28.08.2026: das Leser-Zitat "Also," (muendlich) enthielt als Teilstring
# einen 130 Zeichen langen satzlaenge-Befund und unterdrueckte ihn.
DUP_MIN_KERN = 25


def merge_findings(llm: list[dict] | None, det: list[dict]) -> list[dict]:
    """Leser-Befunde plus deterministische, ohne Dubletten: trifft eine Regex
    dieselbe Passage wie der Leser (ein Zitat enthaelt das andere), zaehlt
    sie nicht doppelt. Diaet-Messung 28.08.2026: 3 von 8 Befunden eines
    Posts waren solche Dubletten, die Reparatur sah die Stelle zweimal.
    Dublette nur bei gleicher Art und ab DUP_MIN_KERN Zeichen im kuerzeren
    Kern: ein kurzes Zitat steckt sonst in jedem langen Satz."""
    def kern(zitat: str) -> str:
        # Satzzeichen an den Raendern weg: der Leser zitiert "X." und die
        # Regex "kein Y. X" ohne Punkt, gemeint ist dieselbe Stelle.
        return _norm(zitat).strip(".,;:!?\"'„“ ")

    out = list(llm or [])
    seen = [(f["art"], kern(f["zitat"])) for f in out]
    for f in det:
        z = kern(f["zitat"])
        if z and any(art == f["art"] and s and min(len(z), len(s)) >= DUP_MIN_KERN
                     and (z in s or s in z) for art, s in seen):
            continue
        out.append(f)
    return out
