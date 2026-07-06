"""Client-Registry: die Env-Variable CLIENT waehlt den Mandanten (Default: jolly).

Jeder Mandant ist ein Modul clients/<name>/config.py mit:
- NAME: str
- CONTEXT: str (Positionierungs-Kontext fuer Scoring + Generierung)
- TOKENS: dict[str, str] ([[TOKEN]]-Ersetzungen fuer die Prompt-Templates)
- FEATURES: dict[str, bool] (supabase_persist, keyword_scrape, topic_mining)
- NOTION_DB_ID_DEFAULT: str | None
- INFLUENCERS_CSV: str (absoluter Pfad zur Influencer-Liste)
"""
import importlib
import os
from functools import lru_cache


@lru_cache(maxsize=1)
def load_client():
    name = os.getenv("CLIENT", "jolly").strip().lower()
    return importlib.import_module(f"clients.{name}.config")


def apply_tokens(template: str, cfg) -> str:
    """Ersetzt [[TOKEN]]-Marker durch die Werte des Mandanten. Wirft bei
    uebrig gebliebenen Markern, damit eine halb gefuellte Client-Config nie
    Prompts mit rohen Markern ausliefern kann."""
    for key, value in cfg.TOKENS.items():
        template = template.replace(f"[[{key}]]", value)
    if "[[" in template:
        start = template.index("[[")
        raise KeyError(f"Unaufgeloester Client-Token: {template[start:start + 60]}")
    return template
