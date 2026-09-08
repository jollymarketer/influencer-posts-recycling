"""Anthropic-Key pro Mandant, gleiches Muster wie tools/apify_auth.py.

Warum (Richard, 08.09.2026): SWOT Controlling GmbH hat eine eigene
Anthropic-Organisation (Task "SWOT Claude API key", 18.05.2026; Guthaben
mit automatischer Nachladung seit 12.08.2026). Christian Kulle am 07.08.2026:
"fuer Anthropic zahlt momentan Jolly, fuer alles andere zahlt SWOT", die
Ausnahme ausdruecklich vorlaeufig. Dieses Repo las an sechs Stellen
`os.getenv("ANTHROPIC_API_KEY")`, also Jollys Konto; jeder SWOT-Text lief
still auf Jolly.

Regeln, bewusst nicht abschaltbar:

1. Der Key kommt aus der `.env` dieses Repos, gelesen per `dotenv_values`
   (ohne .env-Datei, Railway, aus der Prozessumgebung). Kein stiller
   Rueckfall auf ANTHROPIC_API_KEY, wenn die Mandanten-Config einen eigenen
   Namen setzt: das waere Cross-Billing.
2. Der Client entsteht erst beim ersten Aufruf (LazyAnthropic). Module wie
   post_scorer bauen ihn beim Import; ein fehlender Mandanten-Key soll den
   Lauf mit Klartext abbrechen, nicht schon den Import jedes Tests.

Mandanten-Config:
    ANTHROPIC_TOKEN_ENV = "ANTHROPIC_API_KEY_SWOT"   # Default: ANTHROPIC_API_KEY
"""
import os
from pathlib import Path

from dotenv import dotenv_values

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
DEFAULT_ENV = "ANTHROPIC_API_KEY"


def _client_config():
    from clients import load_client
    return load_client()


def token_env_name(cfg=None) -> str:
    return getattr(cfg or _client_config(), "ANTHROPIC_TOKEN_ENV", DEFAULT_ENV)


def get_key(cfg=None) -> str:
    """Key des Mandanten aus der Repo-.env. Fehlt er, Klartext-Abbruch."""
    cfg = cfg or _client_config()
    name = token_env_name(cfg)
    if _ENV_PATH.exists():
        values, quelle = dotenv_values(_ENV_PATH), str(_ENV_PATH)
    else:
        values, quelle = os.environ, "der Prozessumgebung (keine .env-Datei)"
    key = (values.get(name) or "").strip()
    if not key:
        raise ValueError(
            f"{name} fehlt in {quelle}. Der Mandant erwartet diesen Namen "
            f"(ANTHROPIC_TOKEN_ENV in seiner config.py). Kein Fallback auf ein "
            f"anderes Konto - das waere stilles Cross-Billing."
        )
    return key


class LazyAnthropic:
    """anthropic.Anthropic des Mandanten, gebaut beim ersten Zugriff. Tests
    ersetzen das Modulattribut per patch, ohne dass ein Key noetig ist."""

    def __init__(self, cfg=None):
        self._cfg = cfg
        self._client = None

    def _real(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=get_key(self._cfg))
        return self._client

    def __getattr__(self, name):
        return getattr(self._real(), name)


def anthropic_client(cfg=None):
    """Client des aktuellen Mandanten, sofort gebaut (fuer Funktionsaufrufe)."""
    import anthropic
    return anthropic.Anthropic(api_key=get_key(cfg))
