"""Kontowache fuer Apify-Laeufe.

SWOT hat ein eigenes Apify-Konto (kueswot). Ohne Wache haette jeder SWOT-Lauf
in diesem Repo auf Jollys Konto abgerechnet, weil alle Tools os.getenv
("APIFY_API_KEY") lasen. Diese Tests sichern, dass der Token aus der Repo-.env
kommt und ein fremdes Konto den Lauf stoppt, bevor Kosten entstehen.
"""
import pytest

import tools.apify_auth as auth


class _Cfg:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class _PydanticLike:
    """Mimikt UserPrivateInfo des Apify-SDK: Attribute statt dict-Zugriff."""
    def __init__(self, username, email):
        self.username = username
        self.email = email


class _FakeUser:
    def __init__(self, username, email="x@y.z", as_model=False):
        self._d = _PydanticLike(username, email) if as_model else {"username": username, "email": email}

    def get(self):
        return self._d


class _FakeClient:
    def __init__(self, username, as_model=False):
        self._u = _FakeUser(username, as_model=as_model)
        self.calls = 0

    def user(self):
        self.calls += 1
        return self._u


@pytest.fixture(autouse=True)
def _reset_cache():
    auth._verified.clear()
    yield
    auth._verified.clear()


def test_default_tokenname_bleibt_apify_api_key():
    assert auth.token_env_name(_Cfg()) == "APIFY_API_KEY"


def test_mandant_kann_eigenen_tokennamen_setzen():
    cfg = _Cfg(APIFY_TOKEN_ENV="APIFY_API_TOKEN_SWOT")
    assert auth.token_env_name(cfg) == "APIFY_API_TOKEN_SWOT"


def test_token_kommt_aus_der_repo_env_nicht_aus_der_prozessumgebung(monkeypatch):
    monkeypatch.setenv("APIFY_API_KEY", "aus-der-prozessumgebung")
    monkeypatch.setattr(auth, "dotenv_values", lambda _p: {"APIFY_API_KEY": "aus-der-env-datei"})
    assert auth.get_token(_Cfg()) == "aus-der-env-datei"


def test_fehlender_token_bricht_mit_klartext_ab(monkeypatch):
    monkeypatch.setattr(auth, "dotenv_values", lambda _p: {})
    cfg = _Cfg(APIFY_TOKEN_ENV="APIFY_API_TOKEN_SWOT")
    with pytest.raises(ValueError) as e:
        auth.get_token(cfg)
    assert "APIFY_API_TOKEN_SWOT" in str(e.value)


def test_ohne_env_datei_kommt_der_token_aus_der_prozessumgebung(monkeypatch, tmp_path):
    """Railway hat keine Repo-.env (gitignored), die Variablen liegen nur in der
    Service-Umgebung. Vom 20. bis 26.08.2026 fiel deshalb jeder Jolly-Lauf mit
    'APIFY_API_KEY fehlt in /app/.env' aus: kein LinkedIn-Scrape, kein Winner."""
    monkeypatch.setattr(auth, "_ENV_PATH", tmp_path / "gibt-es-nicht.env")
    monkeypatch.setenv("APIFY_API_KEY", "aus-der-service-umgebung")
    assert auth.get_token(_Cfg()) == "aus-der-service-umgebung"


def test_env_datei_schlaegt_prozessumgebung_wenn_sie_existiert(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("APIFY_API_KEY=aus-der-env-datei\n", encoding="utf-8")
    monkeypatch.setattr(auth, "_ENV_PATH", env)
    monkeypatch.setenv("APIFY_API_KEY", "aus-der-prozessumgebung")
    assert auth.get_token(_Cfg()) == "aus-der-env-datei"


def test_ohne_erwartetes_konto_keine_wache():
    client = _FakeClient("irgendwer")
    assert auth.verify_account(client, _Cfg()) == ""
    assert client.calls == 0


def test_richtiges_konto_passiert():
    client = _FakeClient("kueswot")
    assert auth.verify_account(client, _Cfg(APIFY_ACCOUNT="kueswot")) == "kueswot"


def test_falsches_konto_bricht_ab_bevor_kosten_entstehen():
    client = _FakeClient("known_pencil")
    with pytest.raises(auth.AccountMismatch) as e:
        auth.verify_account(client, _Cfg(APIFY_ACCOUNT="kueswot"))
    assert "known_pencil" in str(e.value) and "kueswot" in str(e.value)


def test_kontopruefung_laeuft_nur_einmal_je_prozess():
    client = _FakeClient("kueswot")
    cfg = _Cfg(APIFY_ACCOUNT="kueswot")
    auth.verify_account(client, cfg)
    auth.verify_account(client, cfg)
    assert client.calls == 1


def test_swot_config_zeigt_auf_eigenes_konto():
    from clients.swot import config as swot

    assert swot.APIFY_TOKEN_ENV == "APIFY_API_TOKEN_SWOT"
    assert swot.APIFY_ACCOUNT == "kueswot"


def test_jolly_config_bleibt_unveraendert():
    from clients.jolly import config as jolly

    assert auth.token_env_name(jolly) == "APIFY_API_KEY"
    assert auth.expected_account(jolly) == ""


def test_wache_versteht_auch_das_pydantic_modell_des_sdk():
    """Das Apify-SDK liefert UserPrivateInfo, kein dict. Am 19.08.2026 im
    Livelauf aufgefallen: .get('username') warf AttributeError."""
    assert auth.verify_account(_FakeClient("kueswot", as_model=True),
                               _Cfg(APIFY_ACCOUNT="kueswot")) == "kueswot"


def test_pydantic_modell_mit_falschem_konto_bricht_ebenfalls_ab():
    with pytest.raises(auth.AccountMismatch):
        auth.verify_account(_FakeClient("known_pencil", as_model=True),
                            _Cfg(APIFY_ACCOUNT="kueswot"))
