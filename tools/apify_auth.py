"""Apify-Token und Kontowache pro Mandant.

Warum (Richard, 19.08.2026): SWOT Controlling GmbH hat seit 12.08.2026 ein
eigenes Apify-Konto ("kueswot", kue@swot.de). Dieses Repo las bisher an fuenf
Stellen `os.getenv("APIFY_API_KEY")`, also Jollys Konto. Jeder SWOT-Lauf haette
still auf Jolly abgerechnet. Gleiches Muster wie im Repo swot-outbound-engine,
dort geloest in Commit 5d0c490.

Zwei Regeln, beide bewusst nicht abschaltbar:

1. Der Token kommt ausschliesslich aus der `.env` dieses Repos, gelesen per
   `dotenv_values`. Kein `os.getenv`, kein Parent-Walking. Damit kann eine
   Windows-Umgebungsvariable den Mandanten nicht mehr stillschweigend umbiegen.
2. Definiert die Mandanten-Config `APIFY_ACCOUNT`, wird vor dem ersten
   Actor-Lauf `/users/me` abgefragt und der Kontoname verglichen. Ein Mismatch
   bricht ab, BEVOR Kosten entstehen. Der erwartete Name steht in der Config,
   nicht in der .env: eine per .env abschaltbare Wache ist keine Wache.

Mandanten-Config:
    APIFY_TOKEN_ENV = "APIFY_API_TOKEN_SWOT"   # Default: APIFY_API_KEY
    APIFY_ACCOUNT   = "kueswot"                # ohne Angabe keine Wache
"""
import os
from pathlib import Path

from dotenv import dotenv_values

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
_verified: dict[str, str] = {}


class AccountMismatch(RuntimeError):
    """Der Token gehoert zu einem anderen Apify-Konto als erwartet."""


def _feld(obj, name: str) -> str:
    """Feld aus der Apify-Antwort lesen. Der Client liefert je nach SDK-Version
    ein dict oder ein Pydantic-Modell (UserPrivateInfo), deshalb beide Wege."""
    if obj is None:
        return ""
    if isinstance(obj, dict):
        return str(obj.get(name) or "")
    return str(getattr(obj, name, "") or "")


def _client_config():
    from clients import load_client
    return load_client()


def token_env_name(cfg=None) -> str:
    return getattr(cfg or _client_config(), "APIFY_TOKEN_ENV", "APIFY_API_KEY")


def expected_account(cfg=None) -> str:
    return getattr(cfg or _client_config(), "APIFY_ACCOUNT", "") or ""


def get_token(cfg=None) -> str:
    """Token aus der Repo-.env. Fehlt er, bricht der Lauf mit Klartext ab.

    Ohne .env-Datei (Railway: die Datei ist gitignored, die Variablen liegen
    nur in der Service-Umgebung) gilt die Prozessumgebung. Vom 20. bis
    26.08.2026 brach sonst jeder Jolly-Lauf im Scrape ab, kein Winner, und
    der Make-Publisher postete die letzte Approved-Zeile taeglich neu."""
    cfg = cfg or _client_config()
    name = token_env_name(cfg)
    if _ENV_PATH.exists():
        values, quelle = dotenv_values(_ENV_PATH), str(_ENV_PATH)
    else:
        values, quelle = os.environ, "der Prozessumgebung (keine .env-Datei)"
    token = (values.get(name) or "").strip()
    if not token:
        raise ValueError(
            f"{name} fehlt in {quelle}. Der Mandant erwartet diesen Namen "
            f"(APIFY_TOKEN_ENV in seiner config.py). Kein Fallback auf ein "
            f"anderes Konto - das waere stilles Cross-Billing."
        )
    return token


def verify_account(client, cfg=None) -> str:
    """Kontoname gegen APIFY_ACCOUNT pruefen. Je Prozess einmal."""
    cfg = cfg or _client_config()
    erwartet = expected_account(cfg)
    if not erwartet:
        return ""
    if erwartet in _verified:
        return _verified[erwartet]

    me = client.user().get()
    ist = _feld(me, "username").strip()
    if ist.lower() != erwartet.lower():
        raise AccountMismatch(
            f"Apify-Konto '{ist or 'unbekannt'}' erwartet war '{erwartet}'. "
            f"Lauf abgebrochen, bevor Kosten entstehen. Pruefe "
            f"{token_env_name(cfg)} in {_ENV_PATH}."
        )
    _verified[erwartet] = ist
    print(f"  Apify-Konto: {ist} ({_feld(me, 'email') or 'ohne E-Mail'})")
    return ist


def apify_client(cfg=None):
    """Geprueften ApifyClient des aktuellen Mandanten liefern."""
    from apify_client import ApifyClient

    cfg = cfg or _client_config()
    client = ApifyClient(get_token(cfg))
    verify_account(client, cfg)
    return client
