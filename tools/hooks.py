"""Hook-Katalog mit Rotation (Spec docs/superpowers/specs/
2026-09-14-hook-katalog-und-audit-design.md).

Anlass: Repo-Vergleich mit Jakeschincariol/linkedin-agent-skill (14.09.2026).
Bis dahin war der Hook Zeile 1 jeder Formatstruktur, eine Anweisung je Format;
ob Sonnet daraus Zahl, Frage, Dialogzeile oder Behauptung baute, entschied das
Modell je Lauf. Ohne ID gab es nichts, woran sich Ergebnisse festmachen liessen.

Der Katalog traegt 16 der 21 Formeln des Repos, deutsch gefasst, plus die
eigene Formel "assumption" fuer Signature. Je Formel eine Falle (wie die
Formel misslingt), sie steht mit im Prompt. Weggelassen: Permission Slip
(US-Coach-Ton), Callout (Verachtung fuer das Publikum), Good vs Great (ist
unser Signature), Curiosity Gap (Clickbait), Pattern Interrupt (Einwort-Zeile,
kollidiert mit der Pointen-Regel der Textwache).

Familien buendeln Formeln fuer die Steuerung: bei rund 20 Posts im Monat auf
17 Formeln oeffnet das Stichproben-Gate je Formel erst nach Monaten, je
Familie nach etwa sechs Wochen. Kein Modellaufruf in diesem Modul.
"""
import json
import re
from datetime import date, timedelta

STEERING_MAX_AGE_DAYS = 60

HOOKS = {
    "contrarian": {
        "name": "Contrarian Take", "family": "These",
        "template_de": "Alle sagen {gängiger Rat}. Nach {konkrete Erfahrung} halte ich das für falsch.",
        "template_en": "Everyone says {common advice}. After {specific experience}, I think that is wrong.",
        "trap_de": "Widerspruch gegen etwas, das ohnehin niemand glaubt.",
    },
    "unpopular_rule": {
        "name": "Unpopular Rule", "family": "These",
        "template_de": "Ich mache {verbreitete Praxis} nicht. Nie. Der Grund:",
        "template_en": "I do not {widely accepted practice}. Ever. Here is why.",
        "trap_de": "Eine Regel, die der Autor selbst bricht.",
    },
    "myth_bust": {
        "name": "Myth Bust", "family": "These",
        "template_de": "{Gängige Erklärung} ist nicht der Grund, warum {schlechtes Ergebnis} passiert.",
        "template_en": "{Popular explanation} is not why {bad outcome} is happening to you.",
        "trap_de": "Den wahren Grund nie nennen.",
    },
    "warning": {
        "name": "Warning", "family": "These",
        "template_de": "{Gängige Praxis} kostet still {etwas, das der Leser wirklich will}.",
        "template_en": "{Common practice} is quietly costing you {specific thing they care about}.",
        "trap_de": "Angst ohne Ausweg.",
    },
    "assumption": {
        "name": "Annahme", "family": "These",
        "template_de": "Was {Zielgruppe} annehmen: {die verbreitete Annahme, zugespitzt}.",
        "template_en": "What {audience} assume: {the common assumption, sharpened}.",
        "trap_de": "Eine Annahme, die in der Zielgruppe niemand hat.",
    },
    "number_reveal": {
        "name": "Number Reveal", "family": "Zahl",
        "template_de": "{Ergebniszahl aus dem Asset} in {Zeitraum}. Was dabei wirklich passiert ist.",
        "template_en": "{Result number from the asset} in {period}. Here is what actually happened.",
        "trap_de": "Die Zahl im zweiten Satz vergraben.",
    },
    "time_anchor": {
        "name": "Time Anchor", "family": "Zahl",
        "template_de": "{Aufgabe} hat früher {lange Dauer} gedauert. Heute {kurze Dauer}.",
        "template_en": "{Task} used to take {long time}. It now takes {short time}.",
        "trap_de": "Unglaubwürdiges Verhältnis: fünf Stunden zu zwanzig Minuten trägt, fünf Stunden zu acht Sekunden nicht.",
    },
    "receipt": {
        "name": "Receipt", "family": "Zahl",
        "template_de": "{Harte Zahl aus dem Asset}. {Ein Satz Kontext}.",
        "template_en": "{Hard number from the asset}. {One sentence of context}.",
        "trap_de": "Beleg ohne Geschichte dahinter.",
    },
    "before_after": {
        "name": "Before/After", "family": "Zahl",
        "template_de": "{Zeitpunkt} war {Ausgangslage}. Heute {Ergebnis}. Der Unterschied war {ein einziger Hebel}.",
        "template_en": "{Time ago} it was {low state}. Today {high state}. The difference was {one thing}.",
        "trap_de": "Drei Hebel statt einem.",
    },
    "cold_open": {
        "name": "Story Cold Open", "family": "Szene",
        "template_de": "\"{Ein gesprochener Satz}\" Dann: {wer ihn sagte, wann, und warum er zählte}.",
        "template_en": "\"{Line of dialogue}\" Then: {who said it, when, and why it mattered}.",
        "trap_de": "Ein Satz, den so niemand sagt.",
    },
    "mistake": {
        "name": "Mistake Confession", "family": "Szene",
        "template_de": "{Konkreter Preis} hat mich {ein Fehler} gekostet.",
        "template_en": "{Specific cost} is what {one mistake} cost me.",
        "trap_de": "Falsche Bescheidenheit, und ein Preis ohne Beleg: Zahlen nur aus Quellpost oder Asset, sonst ohne Zahl.",
    },
    "walk_away": {
        "name": "Walk-Away", "family": "Szene",
        "template_de": "Ich habe {etwas Wertvolles} {gekündigt, gestrichen, abgesagt}. {Ergebnis}.",
        "template_en": "I {fired, quit, deleted, cancelled} {valuable thing}. {Result}.",
        "trap_de": "Nicht nennen, was es gekostet hat.",
    },
    "question_trap": {
        "name": "Question Trap", "family": "Frage",
        "template_de": "{Konkrete Situation mit echtem Preis}. Was tun?",
        "template_en": "{Specific scenario with a real cost}. What do you do?",
        "trap_de": "Eine Frage mit offensichtlicher Antwort.",
    },
    "comparison": {
        "name": "Comparison", "family": "Frage",
        "template_de": "{Teure Option} gegen {günstige Option}. {Überraschendes Urteil}.",
        "template_en": "{Expensive option} vs {cheap option}. {Surprising verdict}.",
        "trap_de": "Unfairer Vergleich: einräumen, was die teure Option besser kann.",
    },
    "direct_value": {
        "name": "Direct Value", "family": "Gabe",
        "template_de": "Hier ist genau {Artefakt}, mit dem {konkretes Ergebnis} entstand. Zum Mitnehmen.",
        "template_en": "Here is the exact {artifact} used to {specific outcome}. Steal it.",
        "trap_de": "Das Artefakt hinter einem Gate verstecken statt im Post zu geben.",
    },
    "list_promise": {
        "name": "List Promise", "family": "Gabe",
        "template_de": "{N} Dinge, die mir vor {Meilenstein} niemand gesagt hat.",
        "template_en": "{N} things I wish someone had told me before {milestone}.",
        "trap_de": "N über zehn.",
    },
    "insider_secret": {
        "name": "Insider Secret", "family": "Gabe",
        "template_de": "Nach {N} Jahren {Tätigkeit}: der Teil, der in keiner {Stellenanzeige, Schulung, Pitch} steht.",
        "template_en": "After {N} years {doing thing}, here is the part nobody puts in the {job posting, course, pitch}.",
        "trap_de": "Allgemeinwissen als Geheimnis verkaufen.",
    },
}

# Zahlenformeln brauchen eine belegte Zahl; die liefert nur ein Asset
# (content_matrix.FORMAT_ASSET_ATTR). Der Zahlen-Guard bleibt unveraendert.
NUMBER_HOOKS = frozenset({"number_reveal", "time_anchor", "receipt"})

HOOKS_BY_FORMAT = {
    "Opinion": ("contrarian", "unpopular_rule", "myth_bust", "warning"),
    "POV": ("insider_secret", "myth_bust", "before_after"),
    "Signature": ("assumption",),
    "Story": ("cold_open", "mistake", "walk_away"),
    "Comparison": ("comparison", "warning"),
    "Method": ("direct_value", "list_promise"),
    "CaseProof": ("number_reveal", "time_anchor", "receipt"),
    "Debate": ("question_trap", "contrarian"),
    "Magnet": ("direct_value", "warning"),
    "Offer": ("before_after", "number_reveal"),
}

HOOK_FAMILIES = {}
for _hid, _h in HOOKS.items():
    HOOK_FAMILIES[_h["family"]] = HOOK_FAMILIES.get(_h["family"], ()) + (_hid,)


def family_of(hook_id: str) -> str:
    return HOOKS.get(hook_id, {}).get("family", "")


def load_steering(raw: str, today: date) -> dict:
    """Steuerlisten aus engine_meta["hook_steering_<client>"]. Leer, wenn
    das JSON unlesbar ist, as_of fehlt oder aelter als STEERING_MAX_AGE_DAYS
    ist: ein alter Befund darf nicht ewig weitersteuern."""
    try:
        data = json.loads(raw or "")
        as_of = date.fromisoformat(str(data["as_of"]))
    except (ValueError, KeyError, TypeError):
        return {}
    if today - as_of > timedelta(days=STEERING_MAX_AGE_DAYS):
        return {}
    return {"stop": list(data.get("stop") or []),
            "do_more": list(data.get("do_more") or []),
            "as_of": as_of.isoformat(), "n": int(data.get("n") or 0)}


def pick_hook(fmt: str, recent: list[str], steering: dict | None = None) -> str:
    """Deterministische Rotation: der am laengsten nicht genutzte Kandidat des
    Formats. recent sind die letzten Hook-IDs aus Notion, neueste zuerst.
    STOP sperrt Familien, sperrt es alle Kandidaten des Formats, gilt es
    fuer dieses Format nicht (Log). DO-MORE-Familien zaehlen ihren Abstand
    doppelt, sie kommen also doppelt so oft dran. Gleichstand: Katalogreihe."""
    cands = HOOKS_BY_FORMAT.get(fmt) or HOOKS_BY_FORMAT["Opinion"]
    steering = steering or {}
    stop, do_more = set(steering.get("stop", [])), set(steering.get("do_more", []))
    allowed = [h for h in cands if family_of(h) not in stop]
    if not allowed:
        print(f"  Hook-Steuerung: STOP sperrt alle Formeln von {fmt}, ignoriert.", flush=True)
        allowed = list(cands)

    def age(h: str) -> int:
        try:
            posts_since = recent.index(h) + 1
        except ValueError:
            posts_since = len(recent) + len(cands) + 1
        return posts_since * (2 if family_of(h) in do_more else 1)

    return max(allowed, key=lambda h: (age(h), -cands.index(h)))


_HOOK_LINE_RE = re.compile(r"(?m)^1\. Hook[^\n]*$")


def hook_line(hook_id: str, lang: str) -> str:
    """Zeile 1 der Formatstruktur fuer diese Formel, mit Falle. Der Katalog
    fuehrt bewusst nur eine deutsche Falle; im EN-Prompt steht sie ebenso."""
    h = HOOKS[hook_id]
    if lang == "en":
        return (f"1. Hook (1-2 sentences), formula {h['name']}: {h['template_en']} "
                f"Trap: {h['trap_de']} Decides whether anyone reads on.")
    return (f"1. Hook (1-2 Sätze), Formel {h['name']}: {h['template_de']} "
            f"Falle: {h['trap_de']} Entscheidet, ob jemand weiterliest.")


def inject_hook(structure: str, hook_id: str, lang: str) -> str:
    """Ersetzt genau die Zeile "1. Hook ..." der Struktur. Ohne hook_id oder
    ohne Hook-Zeile (Kurzform) bleibt die Struktur, wie sie ist. Lambda statt
    Ersetzungsstring, damit Backslashes und Klammern der Vorlage stehen bleiben."""
    if not hook_id or hook_id not in HOOKS:
        return structure
    return _HOOK_LINE_RE.sub(lambda m: hook_line(hook_id, lang), structure, count=1)
