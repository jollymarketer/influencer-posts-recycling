"""Anthropic-Key pro Mandant (tools/anthropic_auth, Muster APIFY_TOKEN_ENV).
Richard 08.09.2026: SWOT-Texte laufen auf SWOTs Anthropic-Konto, kein
stiller Rueckfall auf Jollys Key."""
import importlib
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import anthropic_auth as aa


def _env(monkeypatch, tmp_path, **values):
    """Repo-.env durch eine Testdatei ersetzen."""
    p = tmp_path / ".env"
    p.write_text("".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8")
    monkeypatch.setattr(aa, "_ENV_PATH", p)


def test_default_env_name_without_client_override(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, ANTHROPIC_API_KEY="jolly-key")
    assert aa.get_key(SimpleNamespace(NAME="jolly")) == "jolly-key"


def test_client_override_reads_own_env_name(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, ANTHROPIC_API_KEY="jolly-key", ANTHROPIC_API_KEY_SWOT="swot-key")
    cfg = SimpleNamespace(NAME="swot", ANTHROPIC_TOKEN_ENV="ANTHROPIC_API_KEY_SWOT")
    assert aa.get_key(cfg) == "swot-key"


def test_missing_client_key_never_falls_back(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, ANTHROPIC_API_KEY="jolly-key")
    cfg = SimpleNamespace(NAME="x", ANTHROPIC_TOKEN_ENV="ANTHROPIC_API_KEY_FEHLT")
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY_FEHLT"):
        aa.get_key(cfg)


def test_process_env_only_without_env_file(monkeypatch, tmp_path):
    monkeypatch.setattr(aa, "_ENV_PATH", tmp_path / "gibt_es_nicht")
    monkeypatch.setenv("ANTHROPIC_API_KEY_SWOT", "railway-key")
    cfg = SimpleNamespace(NAME="swot", ANTHROPIC_TOKEN_ENV="ANTHROPIC_API_KEY_SWOT")
    assert aa.get_key(cfg) == "railway-key"


def test_lazy_client_builds_on_first_use_with_the_client_key(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, ANTHROPIC_API_KEY_SWOT="swot-key")
    cfg = SimpleNamespace(NAME="swot", ANTHROPIC_TOKEN_ENV="ANTHROPIC_API_KEY_SWOT")
    lazy = aa.LazyAnthropic(cfg)
    with patch("anthropic.Anthropic") as A:
        A.return_value.messages = "M"
        assert A.call_count == 0
        assert lazy.messages == "M"
        assert lazy.messages == "M"
    A.assert_called_once_with(api_key="swot-key")


def test_swot_config_declares_own_token_env_and_repo_env_carries_it():
    swot = importlib.import_module("clients.swot.config")
    assert swot.ANTHROPIC_TOKEN_ENV == "ANTHROPIC_API_KEY_SWOT"
    # Der Wert selbst wird nie geprueft, nur dass die Repo-.env den Namen traegt.
    from dotenv import dotenv_values
    if aa._ENV_PATH.exists():
        assert dotenv_values(aa._ENV_PATH).get("ANTHROPIC_API_KEY_SWOT")


def test_all_llm_callsites_use_the_client_key():
    # Kein Modul liest den Jolly-Key mehr direkt.
    root = os.path.dirname(os.path.dirname(__file__))
    for name in ("post_scorer", "comment_drafts", "topic_clusterer", "monthly_plan",
                 "kieai_image", "system_check"):
        with open(os.path.join(root, "tools", f"{name}.py"), encoding="utf-8") as f:
            src = f.read()
        assert 'os.getenv("ANTHROPIC_API_KEY")' not in src, name
        assert "anthropic_auth" in src, name
