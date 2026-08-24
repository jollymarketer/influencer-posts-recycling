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
    """Alle Verstoesse fuer den Neulauf-Hinweis: harte plus Umlaut-Kandidaten."""
    out = hard_violations(text, max_chars)
    uml = umlaut_candidates(text)
    if uml:
        out.append("ae/oe/ue statt Umlaut: " + ", ".join(uml[:6]))
    return out
