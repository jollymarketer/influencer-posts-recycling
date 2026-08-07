"""ABM-Kommentar-Pfad (OrLI W01): Wochen-Gate, Guard-Semantik, Obergrenzen."""
import types
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import tools.abm_comment_drafts as acd

MON = datetime(2026, 8, 10, 5, 0, tzinfo=timezone.utc)
TUE = MON + timedelta(days=1)

_CFG = types.SimpleNamespace(
    NAME="lisocon",
    ABM_COMMENT_DRAFTS={"watchlist_csv": "wl.csv", "day": 0, "poster": "Reinhard",
                        "author_dedup_days": 14, "per_domain_per_week": 2,
                        "drafts_total": 10},
    CONTENT_PERSONAS=[], TOKENS={}, CONTEXT="x", POSTER_DEFAULT="Reinhard")


def _post(url="p1", author="a1", domain="d1.com", prio="1"):
    return {"post_url": url, "post_text": "t " * 30, "influencer": "N N",
            "author_url": author, "domain": domain, "prio": prio, "age_hours": 5}


def _patch(**kw):
    defaults = dict(
        get_meta=MagicMock(return_value=""),
        set_meta=MagicMock(),
        get_comment_target_urls=MagicMock(return_value=set()),
        get_abm_comment_log=MagicMock(return_value=[]),
        load_watchlist=MagicMock(return_value=[{"linkedin_url": "u",
                                                "first_name": "N", "last_name": "N",
                                                "domain": "d1.com", "prio": "1"}]),
        fetch_watchlist_posts=MagicMock(return_value=[_post()]),
        draft_comment=MagicMock(return_value={"title": "t", "comment": "c",
                                              "poster": "Reinhard", "target_url": "p1",
                                              "influencer": "N N", "excerpt": "e"}),
        create_comment_entry=MagicMock(return_value="page"),
        _notify=MagicMock(),
    )
    defaults.update(kw)
    ctx = ExitStack()
    mocks = {}
    for name, mock in defaults.items():
        ctx.enter_context(patch.object(acd, name, mock))
        mocks[name] = mock
    return ctx, mocks


def test_skips_on_non_run_day():
    ctx, mocks = _patch()
    with ctx:
        assert acd.run_abm_comment_drafts(_CFG, TUE) == 0
    mocks["fetch_watchlist_posts"].assert_not_called()


def test_skips_when_week_guard_is_set():
    ctx, mocks = _patch(get_meta=MagicMock(return_value="2026-W33"))
    with ctx:
        assert acd.run_abm_comment_drafts(_CFG, MON) == 0
    mocks["fetch_watchlist_posts"].assert_not_called()


def test_guard_set_even_when_scrape_finds_nothing():
    # Anders als der Influencer-Pfad: leeres Ergebnis ist der Normalfall,
    # der zweite Cron-Slot soll den Scrape nicht doppelt bezahlen.
    ctx, mocks = _patch(fetch_watchlist_posts=MagicMock(return_value=[]))
    with ctx:
        assert acd.run_abm_comment_drafts(_CFG, MON) == 0
    mocks["set_meta"].assert_called_once_with("last_abm_comments_at_lisocon", "2026-W33")


def test_writes_draft_with_abm_status_and_props():
    ctx, mocks = _patch()
    with ctx:
        assert acd.run_abm_comment_drafts(_CFG, MON) == 1
    _, kwargs = mocks["create_comment_entry"].call_args
    assert kwargs["status"] == acd.ABM_COMMENT_STATUS
    assert kwargs["extra_props"]["ABM-Autor"] == {"url": "a1"}
    assert kwargs["extra_props"]["ABM-Domain"]["rich_text"][0]["text"]["content"] == "d1.com"


def test_dedup_against_already_commented_post():
    ctx, mocks = _patch(get_comment_target_urls=MagicMock(return_value={"p1"}))
    with ctx:
        assert acd.run_abm_comment_drafts(_CFG, MON) == 0
    mocks["create_comment_entry"].assert_not_called()


def test_caps_author_within_14_days():
    log = [{"author_url": "a1", "domain": "x.com", "created": MON - timedelta(days=10)}]
    picked = acd.apply_caps([_post()], log, MON, _CFG.ABM_COMMENT_DRAFTS)
    assert picked == []


def test_author_free_again_after_14_days():
    log = [{"author_url": "a1", "domain": "x.com", "created": MON - timedelta(days=15)}]
    picked = acd.apply_caps([_post()], log, MON, _CFG.ABM_COMMENT_DRAFTS)
    assert len(picked) == 1


def test_caps_domain_at_two_per_week():
    log = [{"author_url": "b1", "domain": "d1.com", "created": MON - timedelta(days=2)},
           {"author_url": "b2", "domain": "d1.com", "created": MON - timedelta(days=3)}]
    picked = acd.apply_caps([_post()], log, MON, _CFG.ABM_COMMENT_DRAFTS)
    assert picked == []


def test_caps_apply_within_one_run_too():
    posts = [_post(url=f"p{i}", author=f"a{i}") for i in range(3)]
    picked = acd.apply_caps(posts, [], MON, _CFG.ABM_COMMENT_DRAFTS)
    assert len(picked) == 2  # per_domain_per_week deckelt auch im Lauf selbst


def test_drafts_total_caps_the_run():
    posts = [_post(url=f"p{i}", author=f"a{i}", domain=f"d{i}.com") for i in range(15)]
    picked = acd.apply_caps(posts, [], MON, _CFG.ABM_COMMENT_DRAFTS)
    assert len(picked) == 10


def test_watchlist_loader_filters_persons_and_sorts_by_prio(tmp_path):
    p = tmp_path / "wl.csv"
    p.write_text(
        "prio,typ,domain,company,persona,first_name,last_name,title,linkedin_url,"
        "rolle_committee,email_track,letzter_kommentar_am,kommentar_anzahl\n"
        "2,person,b.com,B,GF,Bob,B,CEO,https://l/in/b,champion,,,\n"
        "1,firmenseite,a.com,A,,,,,,,W14,,\n"
        "1,person,a.com,A,GF,Ann,A,CEO,https://l/in/a,champion,W14,,\n"
        "3,person,c.com,C,GF,Cee,C,CEO,,champion,,,\n",
        encoding="utf-8")
    rows = acd.load_watchlist(str(p))
    assert [r["last_name"] for r in rows] == ["A", "B"]  # Firmenseite + URL-lose raus
