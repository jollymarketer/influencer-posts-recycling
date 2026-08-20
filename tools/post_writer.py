"""Beitragstexte fuer den Content-Redaktionsplan, durch die volle
DACH-Prompt-Maschinerie (Richard, 20.08.2026).

Bis zum 20.08. stand hier ein eigener 20-Zeilen-Prompt; damit liefen die
Plan-Posts an allen Text-Kriterien vorbei, die Jolly und lisocon erzwingen
(Sprach-Verbote, E3, Pflicht-Artefakt, Feindbild, Zitat-Zeile, Formate,
Soundbyte, Infografik-Skelett, sanitize + grammar_check). Jetzt nutzt der
Themen-Pfad denselben DACH_POST_PROMPT aus tools/post_scorer.py; nur das
Framing ist chirurgisch getauscht, weil es keinen Quell-Post gibt, sondern
Themen-Material (Titel + Kurzbeschreibung aus dem Redaktionsplan).

Der Text traegt weiter die Stimme des Kontos (ACCOUNT_VOICES): wechselt ein
Beitrag das Konto, wird er neu geschrieben. Die Achse liefert die Persona
(CONTENT_PERSONAS) fuer Schmerzpunkte, Vokabular und Zielgruppen-Override.

Achtung: die Templates in post_scorer sind beim Import mit den TOKENS des
Prozess-Mandanten (CLIENT-Env) gefuellt. Der Plan-Fill-Lauf muss also mit
CLIENT=<mandant> starten; das cfg-Argument steuert nur Stimmen und Personas.
"""
from tools.post_scorer import (
    DACH_POST_PROMPT,
    _format_prompts,
    generate_post_and_image_prompt,
    persona_block,
    persona_prompt_tokens,
)

from clients import load_client

# Chirurgisches Reframing des Recycling-Templates auf Themen-Material. Jedes
# Paar wird per Assert geprueft: aendert sich der Wortlaut in post_scorer,
# bricht der Import hier laut, statt still ein halb umgebautes Prompt zu
# liefern.
_TOPIC_REPLACEMENTS = [
    ("Deine Aufgabe: Recycel den folgenden LinkedIn-Post von {influencer} in "
     "einen hochwertigen DACH-deutschen Thought-Leadership-Post.",
     "Deine Aufgabe: Schreibe aus dem folgenden Themen-Material einen "
     "hochwertigen DACH-deutschen Thought-Leadership-Post."),
    ("ORIGINAL POST:\n{post_text}",
     "THEMEN-MATERIAL:\n{post_text}"),
    ("- Den Quell-Content erkennbar nutzen, aber als eigenstaendige "
     "Praxis-Einordnung - keine freie Neuinterpretation",
     "- Das Themen-Material erkennbar nutzen, aber als eigenstaendige "
     "Praxis-Einordnung - keine freie Neuinterpretation"),
    ("- Einen eigenen, originellen Gedanken einbauen, den der Quell-Post "
     "nicht hat - ohne ihn als solchen zu benennen",
     "- Einen eigenen, originellen Gedanken einbauen, den das Themen-Material "
     "nicht vorgibt - ohne ihn als solchen zu benennen"),
]


def _derive_topic_template(template: str) -> str:
    for old, new in _TOPIC_REPLACEMENTS:
        assert old in template, (
            f"Reframing-Anker nicht gefunden (DACH_POST_PROMPT geaendert?): {old[:80]!r}"
        )
        template = template.replace(old, new)
    return template


TOPIC_DE_TEMPLATE = _derive_topic_template(DACH_POST_PROMPT)


def account_voices(cfg=None) -> dict:
    """Stimme je Kanal. Fehlt ein Kanal, gibt es keinen Text: lieber leer als
    im falschen Ton."""
    cfg = cfg or load_client()
    return getattr(cfg, "ACCOUNT_VOICES", {})


def _material(titel: str, kurz: str) -> str:
    return f"Thema: {titel}\nKurzbeschreibung: {kurz}"


def _prompt_parts(titel: str, kurz: str, kanal: str, achse: str, cfg):
    """Pseudo-Post plus Persona/Stimmen-Bloecke fuer den Themen-Pfad."""
    voices = account_voices(cfg)
    if kanal not in voices:
        raise KeyError(
            f"Keine Stimme fuer Kanal '{kanal}' in ACCOUNT_VOICES "
            f"(clients/{cfg.NAME}/config.py). Ohne Stimme kein Text."
        )
    personas = {p["id"]: p for p in cfg.CONTENT_PERSONAS}
    persona = personas[achse]
    post = {"influencer": "der Themen-Recherche", "post_text": _material(titel, kurz)}
    return post, {
        "persona_de": persona_block(persona, "de"),
        "persona_voice_de": voices[kanal],
        "persona_tokens_de": persona_prompt_tokens(persona),
    }


def build_prompt(titel: str, kurz: str, kanal: str, achse: str,
                 post_format: str = "Opinion",
                 recent_infographic_types=None, cfg=None) -> str:
    """DE-Prompt des Themen-Pfads, ohne Modellaufruf (fuer Tests und Debug).
    Baugleich zu dem, was write_post an das Modell schickt."""
    cfg = cfg or load_client()
    post, blocks = _prompt_parts(titel, kurz, kanal, achse, cfg)
    de, _ = _format_prompts(post, post_format, recent_infographic_types,
                            de_template=TOPIC_DE_TEMPLATE, **blocks)
    return de


def write_post(titel: str, kurz: str, kanal: str, achse: str,
               post_format: str = "Opinion",
               recent_infographic_types=None, cfg=None) -> dict:
    """Ein Beitrag durch die volle Maschinerie: Format-Struktur, Persona,
    Kontostimme, sanitize + grammar_check (in generate_post_and_image_prompt).
    Gibt {text, soundbyte, kontext, skeleton} zurueck; text "" wenn nichts kam."""
    cfg = cfg or load_client()
    post, blocks = _prompt_parts(titel, kurz, kanal, achse, cfg)
    de_draft, _en, _img, skeleton, soundbyte, kontext = generate_post_and_image_prompt(
        post, post_format, recent_infographic_types,
        de_template=TOPIC_DE_TEMPLATE, persona_id=achse, **blocks,
    )
    return {"text": de_draft, "soundbyte": soundbyte, "kontext": kontext,
            "skeleton": skeleton}
