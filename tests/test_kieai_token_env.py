"""Tests fuer den mandantenfaehigen kie.ai-Key (Muster APIFY_TOKEN_ENV)."""
import importlib
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import kieai_image as ki


def test_default_env_name_without_client_override(monkeypatch):
    monkeypatch.setenv("KIEAI_API_KEY", "jolly-key")
    cfg = SimpleNamespace(NAME="jolly")
    assert ki._api_key(cfg) == "jolly-key"


def test_client_override_reads_own_env_name(monkeypatch):
    monkeypatch.setenv("KIEAI_API_KEY", "jolly-key")
    monkeypatch.setenv("KIEAI_API_KEY_SWOT", "swot-key")
    cfg = SimpleNamespace(NAME="swot", KIEAI_TOKEN_ENV="KIEAI_API_KEY_SWOT")
    assert ki._api_key(cfg) == "swot-key"


def test_missing_client_key_never_falls_back(monkeypatch):
    monkeypatch.setenv("KIEAI_API_KEY", "jolly-key")
    monkeypatch.delenv("KIEAI_API_KEY_FEHLT", raising=False)
    cfg = SimpleNamespace(NAME="x", KIEAI_TOKEN_ENV="KIEAI_API_KEY_FEHLT")
    with pytest.raises(ValueError, match="KIEAI_API_KEY_FEHLT"):
        ki._api_key(cfg)


def test_swot_config_declares_own_token_env():
    swot = importlib.import_module("clients.swot.config")
    assert swot.KIEAI_TOKEN_ENV == "KIEAI_API_KEY_SWOT"
