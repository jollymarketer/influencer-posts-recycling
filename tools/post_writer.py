"""Beitragstexte fuer den Content-Redaktionsplan.

Der Text traegt die Stimme des Kontos, nicht nur das Thema. Deshalb baut
build_prompt() aus drei Teilen: Mandanten-Kontext, Konto-Stimme und der
Achsen-Persona des Themas. Wechselt ein Beitrag das Konto, muss sein Text neu
geschrieben werden (Richard, 20.08.2026).

Der Promptbau ist von der API getrennt, damit er ohne Modellaufruf testbar ist.
"""
import os

import anthropic
from dotenv import load_dotenv

from clients import load_client

load_dotenv()

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1200

_client = None


def _ai():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def account_voices(cfg=None) -> dict:
    """Stimme je Kanal. Fehlt ein Kanal, gibt es keinen Text: lieber leer als
    im falschen Ton."""
    cfg = cfg or load_client()
    return getattr(cfg, "ACCOUNT_VOICES", {})


def build_prompt(titel: str, kurz: str, kanal: str, achse: str, cfg=None) -> str:
    cfg = cfg or load_client()
    voices = account_voices(cfg)
    if kanal not in voices:
        raise KeyError(
            f"Keine Stimme fuer Kanal '{kanal}' in ACCOUNT_VOICES "
            f"(clients/{cfg.NAME}/config.py). Ohne Stimme kein Text."
        )
    personas = {p["id"]: p for p in cfg.CONTENT_PERSONAS}
    p = personas[achse]
    return (
        f"{cfg.CONTEXT}\n\n{voices[kanal]}\n\n"
        f"Achse dieses Beitrags: {p['label']}. {p['axis']}\n"
        f"Publikum: {p['audience_de']}\n"
        f"Schmerzpunkte: {p['pains']}\n"
        f"Vokabular verwenden: {p['vocabulary_use']}\n"
        f"Vokabular vermeiden: {p['vocabulary_avoid']}\n"
        f"Szene, die traegt: {p['scene_de']}\n\n"
        f"Regeln:\n{cfg.TOKENS['LANGUAGE_BANS_DE']}\n{cfg.TOKENS['HASHTAG_LINE_DE']}\n"
        "- Kein Produkt-Pitch, SWOT wird nicht angeboten und nicht erklaert\n"
        "- Deutsch mit echten Umlauten, kein Gedankenstrich, keine Aufzaehlungszeichen\n"
        "- 120 bis 180 Woerter, Saetze hoechstens rund 20 Woerter\n"
        "- Beginne mit einer konkreten Situation, nicht mit einer These\n"
        "- Erfinde keine Zahl. Zahlen nur, wenn sie im Titel oder in der "
        "Kurzbeschreibung stehen\n"
        "- Ende mit einer echten Frage an die Leser\n\n"
        f"Thema: {titel}\n"
        f"Herkunft: {kurz}\n\n"
        "Schreibe genau den Beitragstext. Keine Ueberschrift, keine "
        "Anfuehrungszeichen, keine Erklaerung davor oder danach."
    )


def write_post(titel: str, kurz: str, kanal: str, achse: str, cfg=None) -> str:
    """Ein Modellaufruf, ein Beitragstext. Leerer String, wenn nichts kam."""
    prompt = build_prompt(titel, kurz, kanal, achse, cfg=cfg)
    resp = _ai().messages.create(model=MODEL, max_tokens=MAX_TOKENS,
                                 messages=[{"role": "user", "content": prompt}])
    return resp.content[0].text.strip() if resp.content else ""
