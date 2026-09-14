"""Deterministische Textwache nach der Generierung.

Anlass: Kundenfeedback SWOT (Christian Kulle, Notion-Kommentare 24.08.2026)
an 8 von 19 September-Beitraegen: Bloecke in Grossbuchstaben, ae/oe/ue statt
Umlauten ("Uebergabetest"), zu lange und immer gleich gebaute Posts. Messung
am selben Abend ueber alle 19 Beitraege aus der Maschinerie: 12 mit
CAPS-Zeile, 7 mit ASCII-Umlauten (3 davon komplett), Laenge 1.305 bis 2.527
Zeichen.

Prompt-Verbote allein halten nicht (dieselbe Lehre wie bei
sanitize_generated_text). Diese Wache misst deterministisch; die Callsite
entscheidet ueber Neulauf oder Verwerfen. Kein Modellaufruf, kein Netz.
"""
import re
from statistics import mean, pstdev

# Abkuerzungen ab vier Buchstaben, die in Grossbuchstaben stehen duerfen.
# Kuerzere (GuV, ERP, BWA) und gemischte (StaRUG, IFRS 18) trifft das Muster
# ohnehin nicht.
CAPS_ALLOWED = frozenset("""
CAPEX CSRD DACH DATEV DEEPL EBIT EBITDA GMBH IFRS INSO MPMS OPEX STARUG SWOT
""".split())

_CAPS_WORD = re.compile(r"\b[A-ZÄÖÜ]{4,}\b")


def caps_words(text: str) -> list[str]:
    """Woerter ab vier Grossbuchstaben, die keine erlaubte Abkuerzung sind."""
    return [w for w in _CAPS_WORD.findall(text) if w not in CAPS_ALLOWED]


def caps_lines(text: str) -> list[str]:
    """Zeilen, die nach Abzug erlaubter Abkuerzungen ueberwiegend aus
    Grossbuchstaben bestehen (der "CAPS-Block" aus dem Kundenfeedback)."""
    out = []
    for line in text.splitlines():
        rest = _CAPS_WORD.sub(lambda m: "" if m.group() in CAPS_ALLOWED else m.group(), line)
        letters = [c for c in rest if c.isalpha()]
        if len(letters) >= 8 and sum(c.isupper() for c in letters) / len(letters) > 0.8:
            out.append(line.strip())
    return out


# Umschreibungen ae/oe/ue. Nicht jedes "ue" ist eine: nach a, e, o, q ist es
# Diphthong plus e (Bauer, neue, Quelle), vor l ist es echt (aktuell, Manuel).
_UML = re.compile(r"(?<![aeoqAEOQ])[uU][eE](?![lL])|[aAoO][eE]")
# Eigennamen und Fremdwoerter, die wirklich so geschrieben werden. Bewusst
# kurz: die Wache liefert Kandidaten, das Urteil faellt der Korrektor mit
# Kontext. "ue$" faengt Revue, Statue, Fondue, Queue, Value.
_UML_EXCEPTIONS = re.compile(
    r"(?i)(israel|michael|aero|poesie|oboe|goethe|boehringer|schaeffler|phoenix"
    r"|noel|zoe|kanoe|rafael|raphael|gael|paella|influenc|duett|menuett|statue"
    r"|guerill|zuerst|^due$|ue$)"
)


def umlaut_candidates(text: str) -> list[str]:
    """Woerter, die nach ae/oe/ue-Umschreibung aussehen, in Textreihenfolge,
    ohne Dubletten."""
    seen, out = set(), []
    for w in re.findall(r"[A-Za-zÄÖÜäöüß]+", text):
        if w in seen or _UML_EXCEPTIONS.search(w) or not _UML.search(w):
            continue
        seen.add(w)
        out.append(w)
    return out


def hard_violations(text: str, max_chars: int) -> list[str]:
    """Verstoesse, die einen Text verwerfen: Grossbuchstaben als Hervorhebung
    und Ueberlaenge. Klartext, damit die Meldung direkt in den
    Neulauf-Hinweis und ins Log passt."""
    out = []
    block = caps_lines(text) or caps_words(text)
    if block:
        out.append("Grossbuchstaben als Hervorhebung: " + ", ".join(block[:4]))
    if len(text) > max_chars:
        out.append(f"{len(text)} Zeichen, erlaubt sind hoechstens {max_chars}")
    return out


def violations(text: str, max_chars: int) -> list[str]:
    """Alle Verstoesse fuer den Neulauf-Hinweis: harte plus Umlaut-Kandidaten
    plus Rhythmus und Strukturformeln (shape_notes)."""
    out = hard_violations(text, max_chars)
    uml = umlaut_candidates(text)
    if uml:
        out.append("ae/oe/ue statt Umlaut: " + ", ".join(uml[:6]))
    out.extend(shape_notes(text))
    return out


# Rhythmus und Strukturformeln (Repo-Vergleich Jakeschincariol/linkedin-agent-
# skill, 14.09.2026). Die Masse stammen aus dessen detect.py und sind
# sprachneutral: Variationskoeffizient der Satzlaengen (Maschine um 0.22,
# Mensch um 0.70, Flag unter 0.35) und gleich lange Listenpunkte (Stdabw der
# Wortzahl unter 1.6). Die zwei Strukturmuster sind deutsch nachgebaut: der
# Dreier-Parallelismus nur aus Kleinwoertern (Adjektive, Verben), damit eine
# Aufzaehlung von Substantiven wie "Excel, Word und PowerPoint" nicht trifft,
# und die Pointen-Frage als eigene Zeile ("Das Ergebnis?"). Alles weich: der
# Befund geht in den einen Neulauf-Hinweis, verworfen wird deswegen nichts.
# Bei SWOT fragt der Leser (naturalness, Frage 5) dieselben Formeln danach
# noch einmal ab; bei Jolly und lisocon ist dieser Hinweis der einzige Fang.
MIN_SENTENCE_CV = 0.35
MIN_SENTENCES = 4
BULLET_STDEV_MIN = 1.6
MIN_BULLETS = 3

_BULLET = re.compile(r"(?m)^[ \t]*(?:[-•*]|\d+[.)])[ \t]+(.+)$")
_TRIAD = re.compile(r"\b[a-zäöüß]+, [a-zäöüß]+ und [a-zäöüß]+[.!]")
_POINTE_FRAGE = re.compile(r"(?m)^[ \t]*(?:Das|Der|Die|Mein|Meine|Unser|Unsere) \w+\?[ \t]*$")


def _word_counts(parts: list[str]) -> list[int]:
    return [n for n in (len(p.split()) for p in parts) if n > 0]


def sentence_length_cv(text: str) -> float | None:
    """Variationskoeffizient der Satzlaengen in Woertern. None unter
    MIN_SENTENCES Saetzen; Zeilenumbruch zaehlt wie in long_sentences als
    Satzende."""
    lengths = _word_counts(re.split(r"(?<=[.!?])\s+|\n+", text))
    if len(lengths) < MIN_SENTENCES:
        return None
    return pstdev(lengths) / mean(lengths)


def uniform_bullets(text: str) -> list[str]:
    """Listenpunkte, wenn ab MIN_BULLETS Punkten alle fast gleich lang sind."""
    items = [m.group(1).strip() for m in _BULLET.finditer(text)]
    if len(items) < MIN_BULLETS:
        return []
    return items if pstdev(_word_counts(items)) < BULLET_STDEV_MIN else []


def shape_notes(text: str) -> list[str]:
    """Weiche Befunde zu Rhythmus und Strukturformeln, Klartext fuer den
    Neulauf-Hinweis."""
    out = []
    cv = sentence_length_cv(text)
    if cv is not None and cv < MIN_SENTENCE_CV:
        out.append(f"Satzlaengen zu gleichfoermig (Streuung {cv:.2f}): "
                   "kurze und lange Saetze mischen")
    bullets = uniform_bullets(text)
    if bullets:
        out.append("Listenpunkte alle gleich lang, unterschiedlich lang machen: "
                   + " | ".join(b[:40] for b in bullets[:3]))
    m = _TRIAD.search(text)
    if m:
        out.append(f"Dreier-Parallelismus, ein Element streichen: \"{m.group(0)}\"")
    m = _POINTE_FRAGE.search(text)
    if m:
        out.append("Pointen-Frage als Einzeiler, als Aussage in den Absatz ziehen: "
                   f"\"{m.group(0).strip()}\"")
    return out
