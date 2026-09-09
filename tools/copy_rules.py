"""Kundenregeln fuer Beitragstexte, deterministisch, aus der Client-Config.

Anlass: Notion-Kommentare von Inga Baumert und Muhammed Doganguezel (SWOT)
vom 01. bis 07.09.2026 an neun Beitraegen. Richard hat am 08.09.2026 sieben
davon als Regeln freigegeben, die uebrigen (Listen aufloesen, CTA je Post
neu, "wirkt nicht human") ausdruecklich nicht.

Die Regeln liegen als COPY_RULES in der Client-Config, nicht hier: sie sind
Kundenwissen (wer welche Situation erlebt, welches Wort der Kunde sagt), und
andere Mandanten haben andere. Dieses Modul kennt nur die Pruefmechanik und
liefert Befunde in der Form des Lesers (tools/naturalness), damit die
chirurgische Reparatur sie wie jeden anderen Befund behandelt. Kein Netz.

Schluessel von COPY_RULES, alle optional:

- role_frames: {Sprechername: {"erlaubt": "...", "verboten": [regex, ...]}}.
  Der Name wird im voice-String gesucht (wie naturalness.VOICE_TICS). Trifft
  ein verbotenes Muster, ist die Erzaehlsituation falsch (Inga 07.09.2026:
  "Robert selbst fuehrt keine Einfuehrungsprojekte").
- disparagement: [regex, ...]. Kunde oder frueherer Zustand abgewertet
  (Inga 07.09.2026 zu "vorher falsch gebaut" neben einem Kundennamen).
  Die Haerte haengt am Adressaten, nicht am Wort: steht im selben Satz ein
  Name, eine Rolle oder "der Kunde", ist es "abwertung" und verwirft den
  Text; ohne Adressaten ist es "abwertung_anonym", ein weicher Befund mit
  Vorschlag (Richard 09.09.2026: ein Missstand ohne Adressat ist der
  Painpoint, den der Beitrag zeigen soll).
- disparagement_subjects: [regex, ...]. Zusaetzliche Adressaten des
  Mandanten, etwa die Namen der Referenzkunden aus den Anwenderberichten.
- term_map: {Begriff: Ersatz}. Fachwort nicht aus dem VoC-Korpus; das ganze
  Kompositum wird zitiert und mit Ersatz vorgeschlagen.
- address: "du" oder "Sie". Die jeweils andere Anrede mitten im Satz ist ein
  Registerbruch. Bei "Sie" zaehlen nur eindeutige Marker (du/dich/dir/dein,
  euch/euer/eure, und kleingeschriebenes "ihr", dem kein Substantiv folgt);
  "ihre", "ihrem" und ein grossgeschriebenes "Ihr" sind Besitzformen und
  bleiben unberuehrt.
- cta_bridge: True. Der Schlussabsatz ist eine Bruecke zur automatisch
  angehaengten Terminzeile: keine Frage, kein eigener Link-Hinweis, und er
  spricht den Leser an.
- structure_max_repeat: n. Ein Label-Muster ("Annahme: ...") hoechstens n-mal.
"""
import re

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_SIE = re.compile(r"\b(?:Sie|Ihnen|Ihre?[nmrs]?)\b")
_LABEL = re.compile(r"^([A-ZÄÖÜ][\wäöüß-]{1,24}):", re.M)
_ADDRESS = re.compile(r"\b(?:du|dich|dir|dein\w*|ihr|euch|euer|eure\w*)\b", re.I)
# Anrede des Lesers in du/ihr, eindeutig: "ihr" nur klein und ohne folgendes
# Substantiv ("ihr habt" ist Pronomen, "ihr Zahlenwerk" ist Besitzform).
_DU = re.compile(r"\b(?:[Dd]u|[Dd]ich|[Dd]ir|[Dd]ein\w*|[Ee]uch|[Ee]uer|[Ee]ure\w*)\b"
                 r"|\bihr\b(?!\s+[A-ZÄÖÜ])")
_LINK_HINT = re.compile(r"im (?:ersten )?Kommentar|Link zum Termin|https?://|Termin buchen", re.I)
QUOTE_CAP = 200
# Adressaten einer Abwertung: erst wenn im selben Satz jemand steht, dem das
# Urteil gilt, ist der Befund hart. Namen der Referenzkunden kommen je
# Mandant ueber COPY_RULES["disparagement_subjects"] dazu.
_ZUSCHREIBUNG = (
    r"\b(?:Kunde|Kunden|Kundin|Mandant\w*|Referenzkunde\w*|Anwender\w*)\b",
    r"\b(?:Gesch(?:ä|ae)ftsf(?:ü|ue)hr\w*|Controller\w*|Leiter\w*|Leitung|"
    r"Kolleg\w*|Buchhalt\w*|Team|Gruppe|Mitarbeiter\w*|Vorstand|Pr(?:ü|ue)fer\w*)\b",
    r"\b[A-ZÄÖÜ][a-zäöüß]+(?:-[A-ZÄÖÜ][a-zäöüß]+)?\s+[A-ZÄÖÜ][a-zäöüß]{2,}\b",
)


def _sentence_with(text: str, pos: int) -> str:
    """Satz, der die Position pos enthaelt."""
    start = 0
    for m in re.finditer(r"(?<=[.!?])\s+|\n+", text):
        if m.end() <= pos:
            start = m.end()
        else:
            return text[start:m.start()].strip()
    return text[start:].strip()


def _paragraph_with(text: str, pos: int) -> str:
    """Absatz, der die Position pos enthaelt."""
    start = text.rfind("\n\n", 0, pos)
    start = 0 if start < 0 else start + 2
    ende = text.find("\n\n", pos)
    return text[start:ende if ende >= 0 else len(text)].strip()


def _finding(art: str, zitat: str, grund: str, vorschlag: str) -> dict:
    return {"art": art, "zitat": zitat.strip()[:QUOTE_CAP], "grund": grund,
            "vorschlag": vorschlag}


def _role(text: str, voice: str, frames: dict) -> list[dict]:
    out = []
    for sprecher, frame in (frames or {}).items():
        if sprecher not in (voice or ""):
            continue
        erlaubt = frame.get("erlaubt", "")
        for rx in frame.get("verboten", []):
            m = re.search(rx, text)
            if m:
                out.append(_finding(
                    "rolle", m.group(0),
                    f"{sprecher} erlebt diese Situation nicht; seine Situationen: {erlaubt}",
                    f"Situation ersetzen durch eine aus: {erlaubt}"))
    return out


def _disparagement(text: str, patterns: list, subjects: list | None = None) -> list[dict]:
    out = []
    adressat = list(_ZUSCHREIBUNG) + list(subjects or [])
    for rx in patterns or []:
        m = re.search(rx, text, re.I)
        if not m:
            continue
        # Absatz, nicht Satz: Inga Baumerts Fundstelle nennt den Kunden im
        # ersten Satz und faellt das Urteil im zweiten ("Moebes ... weil das
        # Verfahren vorher falsch gebaut war").
        absatz = _paragraph_with(text, m.start())
        zugeschrieben = any(re.search(a, absatz) for a in adressat)
        out.append(_finding(
            "abwertung" if zugeschrieben else "abwertung_anonym", m.group(0),
            "Kunde oder frueherer Zustand wird abgewertet" if zugeschrieben else
            "Urteil ueber einen Zustand, den der Satz niemandem zuschreibt",
            "früheren Zustand neutral beschreiben (Dauer, Aufwand, Ergebnis), "
            "ohne Urteil über Person oder Verfahren"))
    return out


def _terms(text: str, term_map: dict) -> list[dict]:
    out = []
    for term, ersatz in (term_map or {}).items():
        m = re.search(r"[\w-]*" + re.escape(term) + r"\w*", text, re.I)
        if m:
            token = m.group(0)
            out.append(_finding(
                "fachbegriff", token,
                f"'{term}' sagt der Kunde nicht, der Korpus sagt '{ersatz}'",
                re.sub(re.escape(term), ersatz, token, flags=re.I)))
    return out


def _register(text: str, address: str) -> list[dict]:
    if address == "Sie":
        m = _DU.search(text)
        if not m:
            return []
        return [_finding(
            "register", _sentence_with(text, m.start()),
            "du- oder ihr-Form im Text, der Beitrag siezt den Leser",
            "in die Sie-Form umschreiben")]
    for s in _SENTENCE_SPLIT.split(text):
        for m in _SIE.finditer(s):
            if s[:m.start()].strip(' "„“\'(') == "":
                continue    # Satzanfang: Plural "sie" gross geschrieben
            return [_finding(
                "register", s,
                "Sie-Form im Text, der Beitrag spricht den Leser mit du/ihr an",
                "in du- oder ihr-Form umschreiben")]
    return []


def _cta(text: str, address: str) -> list[dict]:
    absaetze = [a.strip() for a in re.split(r"\n\s*\n", text.strip()) if a.strip()]
    if not absaetze:
        return []
    letzter = absaetze[-1]
    form = "Sie-Form" if address == "Sie" else "du- oder ihr-Form"
    anrede = _SIE if address == "Sie" else _ADDRESS
    bruecke = (f"Schlussabsatz als Brücke in {form} ohne Frage: den "
               "Anlass nennen, das einmal gemeinsam durchzugehen; die "
               "Terminzeile folgt automatisch darunter")
    q = letzter.rfind("?")
    if q >= 0:
        return [_finding("cta", _sentence_with(letzter, q),
                         "Frage im Schlussabsatz, darunter steht die Terminzeile: zwei CTAs",
                         bruecke)]
    m = _LINK_HINT.search(letzter)
    if m:
        return [_finding("cta", _sentence_with(letzter, m.start()),
                         "eigener Link- oder Terminhinweis im Text, die Terminzeile kommt automatisch",
                         bruecke)]
    if not anrede.search(letzter):
        return [_finding("cta", letzter,
                         "Schlussabsatz ohne Leseransprache, keine Brücke zur Terminzeile",
                         bruecke)]
    return []


def _structure(text: str, cap: int) -> list[dict]:
    zaehler: dict[str, list[str]] = {}
    for line in text.splitlines():
        m = _LABEL.match(line)
        if m:
            zaehler.setdefault(m.group(1), []).append(line.strip())
    for label, lines in zaehler.items():
        if len(lines) > cap:
            return [_finding(
                "struktur", lines[cap],
                f"Strukturmuster '{label}:' {len(lines)}-mal, erlaubt {cap}",
                "die weiteren Paare als Fließtext ohne Label schreiben")]
    return []


def findings(text: str, voice: str = "", rules: dict | None = None) -> list[dict]:
    """Befunde der Kundenregeln fuer einen Text, in der Form des Lesers
    (art, zitat, grund, vorschlag). Ohne rules keine Befunde."""
    if not rules or not text:
        return []
    out = []
    out += _role(text, voice, rules.get("role_frames"))
    out += _disparagement(text, rules.get("disparagement"),
                          rules.get("disparagement_subjects"))
    out += _terms(text, rules.get("term_map"))
    address = rules.get("address")
    if address in ("du", "Sie"):
        out += _register(text, address)
    if rules.get("cta_bridge"):
        out += _cta(text, address)
    cap = rules.get("structure_max_repeat")
    if cap:
        out += _structure(text, int(cap))
    return out
