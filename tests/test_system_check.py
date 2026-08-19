"""Tests fuer den Phase-0-System-Check. Nur die reinen Funktionen - die
Netz-Checks brauchen echte Tokens und laufen im Cron, nicht hier."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import system_check as sc


def _cfg(features=None, readback=None, comments=None, **kw):
    return SimpleNamespace(NAME="test", FEATURES=features or {},
                           ENGAGEMENT_READBACK=readback, COMMENT_DRAFTS=comments, **kw)


# --- required_notion_props ---------------------------------------------------

def test_core_props_always_required():
    props = sc.required_notion_props(_cfg())
    for name in sc.CORE_NOTION_PROPS:
        assert name in props


def test_en_props_default_on_but_droppable():
    assert "LinkedIn Draft EN" in sc.required_notion_props(_cfg())
    assert "LinkedIn Draft EN" not in sc.required_notion_props(_cfg({"en_draft": False}))


def test_slate_props_only_in_slate_mode():
    assert "Score" not in sc.required_notion_props(_cfg())
    assert "Score" in sc.required_notion_props(_cfg({"slate_mode": True}))


def test_readback_props_only_when_configured():
    """Ein Mandant ohne Readback-Config darf die Engagement-Properties nicht
    einfordern - sonst meldet der Check eine Luecke, die niemanden stoert."""
    assert "Likes" not in sc.required_notion_props(_cfg())
    assert "Likes" in sc.required_notion_props(_cfg(readback={"posted_limit": "month"}))


def test_readback_url_props_come_from_the_client():
    """Die URL-Felder heissen pro Mandant anders. Fest verdrahtete lisocon-Namen
    haben den Check fuer jolly auf NO-GO gestellt, obwohl dort nichts fehlte."""
    jolly_like = _cfg(readback={"posted_limit": "month"},
                      POSTED_URL_PROPS={"Richard": "Richard LinkedIn Posted URL"})
    props = sc.required_notion_props(jolly_like)
    assert "Richard LinkedIn Posted URL" in props
    assert "Posted URL (Reinhard)" not in props


def test_poster_column_only_required_with_several_posters():
    """Ein einzelner Poster braucht keine Routing-Spalte."""
    one = _cfg(readback={"x": 1}, POSTED_URL_PROPS={"Richard": "Richard LinkedIn Posted URL"})
    two = _cfg(readback={"x": 1}, POSTED_URL_PROPS={"Reinhard": "Posted URL (Reinhard)",
                                                    "Jae": "Posted URL (Jae)"})
    assert "Poster" not in sc.required_notion_props(one)
    assert "Poster" in sc.required_notion_props(two)


def test_comment_props_only_when_configured():
    assert "Kommentar-Ziel" not in sc.required_notion_props(_cfg())
    assert "Kommentar-Ziel" in sc.required_notion_props(_cfg(comments={"per_run": 12}))


def test_props_are_deduplicated():
    """Poster steht in mehreren Bloecken - darf trotzdem nur einmal auftauchen."""
    props = sc.required_notion_props(
        _cfg({"slate_mode": True}, readback={"x": 1}, comments={"y": 2}))
    assert len(props) == len(set(props))
    assert props.count("Poster") == 1


# --- required_env ------------------------------------------------------------

def test_env_core_severities():
    env = dict(sc.required_env(_cfg()))
    assert env["ANTHROPIC_API_KEY"] == sc.HARD
    assert env["APIFY_API_KEY"] == sc.HARD
    assert env["KIEAI_API_KEY"] == sc.SOFT


def test_env_uses_client_token_names():
    cfg = _cfg(NOTION_TOKEN_ENV="NOTION_TOKEN_LISOCON",
               MAKE_WEBHOOK_ENV="MAKE_REVIEW_WEBHOOK_LISOCON")
    names = [n for n, _ in sc.required_env(cfg)]
    assert "NOTION_TOKEN_LISOCON" in names
    assert "MAKE_REVIEW_WEBHOOK_LISOCON" in names


def test_env_extras_are_feature_gated():
    plain = [n for n, _ in sc.required_env(_cfg())]
    assert "MAKE_SLATE_WEBHOOK" not in plain
    assert "SUPABASE_URL" not in plain
    rich = [n for n, _ in sc.required_env(
        _cfg({"slate_mode": True, "supabase_persist": True}))]
    assert "MAKE_SLATE_WEBHOOK" in rich
    assert "SUPABASE_URL" in rich


# --- Supabase-Weiche ---------------------------------------------------------
# lisocon faehrt supabase_persist=False und trotzdem den Kandidaten-Pool.
# Ohne diese Weiche blieb ausgerechnet die Abhaengigkeit ungeprueft, deren
# Ausfall den Slate garantiert still verschluckt (phase_slate: "kein Slate
# ohne Pool").

def test_slate_mode_uses_supabase_without_persist_flag():
    assert sc.uses_supabase(_cfg({"slate_mode": True})) is True
    assert sc.uses_supabase(_cfg({"supabase_persist": True})) is True
    assert sc.uses_supabase(_cfg()) is False


def test_slate_mode_supabase_env_is_hard():
    env = dict(sc.required_env(_cfg({"slate_mode": True})))
    assert env["SUPABASE_URL"] == sc.HARD
    assert env["SUPABASE_SERVICE_KEY"] == sc.HARD


def test_mining_only_supabase_env_stays_soft():
    """Beim Jolly-Mining ist Supabase eine Nebenwirkung, kein Blocker."""
    env = dict(sc.required_env(_cfg({"supabase_persist": True})))
    assert env["SUPABASE_URL"] == sc.SOFT


def test_probed_table_follows_the_mode():
    assert sc.supabase_table(_cfg({"slate_mode": True})) == "topic_candidates"
    assert sc.supabase_table(_cfg({"supabase_persist": True})) == "influencer_posts"


def test_no_supabase_check_without_usage():
    assert sc.check_supabase(_cfg()) == []


# --- evaluate ----------------------------------------------------------------

def test_soft_failure_still_go():
    go, lines = sc.evaluate([
        sc._result("notion", True, sc.HARD, "ok"),
        sc._result("kieai", False, sc.SOFT, "keine Credits"),
    ])
    assert go is True
    assert any("WARN" in line for line in lines)
    assert lines[-1].endswith("GO")


def test_hard_failure_blocks_and_names_the_check():
    go, lines = sc.evaluate([
        sc._result("notion:properties", False, sc.HARD, "fehlen: Likes"),
        sc._result("kieai", True, sc.SOFT, "828 Credits"),
    ])
    assert go is False
    assert "NO-GO" in lines[-1]
    assert "notion:properties" in lines[-1]


def test_empty_results_are_go():
    go, _ = sc.evaluate([])
    assert go is True
