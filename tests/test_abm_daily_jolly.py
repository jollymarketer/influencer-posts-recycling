"""Jolly-Kommentarpfad auf der Watchlist (14.09.2026): Tageslauf statt Wochenlauf,
Rotation, Kunden-Sperrliste, Relevanz-Gate, Watchlist-Builder. Kein Netz."""
import json
import os
import sys
import types
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import tools.abm_comment_drafts as acd
from tools import jolly_watchlist as jw

MON = datetime(2026, 9, 14, 5, 0, tzinfo=timezone.utc)
TUE = MON + timedelta(days=1)
HEADER = ("prio,typ,domain,company,persona,first_name,last_name,title,linkedin_url,"
          "rolle_committee,email_track,letzter_kommentar_am,kommentar_anzahl\n")


def _cfg(**over):
    settings = {"watchlist_csv": "wl.csv", "day": None, "poster": "Richard",
                "author_dedup_days": 14, "per_domain_per_week": 2, "drafts_total": 3,
                "profiles_per_run": 2, "relevance_gate": True, "min_relevance": 6,
                "exclude_companies": ["lindner software", "in2go"]}
    settings.update(over)
    return types.SimpleNamespace(NAME="jolly", ABM_COMMENT_DRAFTS=settings,
                                 CONTENT_PERSONAS=[], TOKENS={"PERSONA_DE": "Richard"},
                                 CONTEXT="x", POSTER_DEFAULT="Richard")


def _post(url="p1", author="a1", company="Firma A", text="t " * 40, prio="1"):
    return {"post_url": url, "post_text": text, "influencer": "N N", "author_url": author,
            "domain": "", "company": company, "prio": prio, "age_hours": 5}


def _patch(**kw):
    defaults = dict(
        get_meta=MagicMock(return_value=""), set_meta=MagicMock(),
        get_comment_target_urls=MagicMock(return_value=set()),
        get_abm_comment_log=MagicMock(return_value=[]),
        load_watchlist=MagicMock(return_value=[{"linkedin_url": f"u{i}", "first_name": "N",
                                                "last_name": str(i), "domain": "", "company": "F",
                                                "prio": "1"} for i in range(5)]),
        fetch_watchlist_posts=MagicMock(return_value=[_post()]),
        draft_comment=MagicMock(return_value={"title": "t", "comment": "c", "typ": "6 Der Beleg",
                                              "poster": "Richard", "target_url": "p1",
                                              "influencer": "N N", "excerpt": "e"}),
        create_comment_entry=MagicMock(return_value="page"),
        _notify=MagicMock(),
        _gate_client=MagicMock(return_value=_FakeGate('{"kommentierbar": true, "score": 8, "grund": "Fachthema"}')),
    )
    defaults.update(kw)
    ctx = ExitStack()
    mocks = {}
    for name, mock in defaults.items():
        ctx.enter_context(patch.object(acd, name, mock))
        mocks[name] = mock
    return ctx, mocks


class _FakeGate:
    def __init__(self, text):
        self.text, self.calls, self.messages = text, [], self

    def create(self, **kw):
        self.calls.append(kw["messages"][0]["content"])
        return types.SimpleNamespace(content=[types.SimpleNamespace(text=self.text)])


def test_load_watchlist_excludes_own_clients(tmp_path):
    p = tmp_path / "wl.csv"
    p.write_text(HEADER
                 + "1,person,,Lindner Software & Consulting,,Jae,Kim,Director,https://l/in/jae,,,,\n"
                 + "2,person,in2go.io,InTO,,Reinhard,L,GF,https://l/in/rl,,,,\n"
                 + "1,person,,Realcube GmbH,,Uwe,F,MD,https://l/in/uwe,,,,\n", encoding="utf-8")
    rows = acd.load_watchlist(str(p), exclude=["lindner software", "in2go"])
    assert [r["last_name"] for r in rows] == ["F"]
    assert len(acd.load_watchlist(str(p))) == 3


def test_rotate_watchlist_slices_deterministically():
    rows = [{"linkedin_url": f"u{i}"} for i in range(5)]
    assert [r["linkedin_url"] for r in acd.rotate_watchlist(rows, 2, 0)] == ["u0", "u1"]
    assert [r["linkedin_url"] for r in acd.rotate_watchlist(rows, 2, 1)] == ["u2", "u3"]
    assert [r["linkedin_url"] for r in acd.rotate_watchlist(rows, 2, 2)] == ["u4", "u0"]
    assert acd.rotate_watchlist(rows, None, 7) == rows
    assert acd.rotate_watchlist([], 2, 0) == []


def test_daily_mode_runs_on_any_weekday_and_guards_per_day():
    ctx, m = _patch()
    with ctx:
        assert acd.run_abm_comment_drafts(_cfg(), TUE) == 1
    m["set_meta"].assert_any_call("last_abm_comments_at_jolly", "2026-09-15")
    ctx, m = _patch(get_meta=MagicMock(return_value="2026-09-15"))
    with ctx:
        assert acd.run_abm_comment_drafts(_cfg(), TUE) == 0
    m["fetch_watchlist_posts"].assert_not_called()


def test_daily_mode_fetches_only_the_rotated_slice():
    ctx, m = _patch()
    with ctx:
        acd.run_abm_comment_drafts(_cfg(profiles_per_run=2), MON)
    rows = m["fetch_watchlist_posts"].call_args.args[0]
    assert len(rows) == 2


def test_weekly_mode_stays_as_before():
    cfg = _cfg(day=0, relevance_gate=False, profiles_per_run=None)
    ctx, m = _patch()
    with ctx:
        assert acd.run_abm_comment_drafts(cfg, TUE) == 0
        assert acd.run_abm_comment_drafts(cfg, MON) == 1
    m["set_meta"].assert_any_call("last_abm_comments_at_jolly", "2026-W38")


def test_relevance_gate_drops_hiring_low_scores_and_unparseable():
    posts = [_post("p1", text="Wir stellen ein: Sales Manager m/w/d " * 5),
             _post("p2", text="Unsere Pipeline war drei Monate leer. " * 5),
             _post("p3", text="Guter Beitrag zum Forecast. " * 5)]
    answers = iter(['{"kommentierbar": true, "score": 4, "grund": "duenn"}',
                    '{"kommentierbar": true, "score": 9, "grund": "These"}'])

    class Gate(_FakeGate):
        def create(self, **kw):
            self.text = next(answers)
            return super().create(**kw)

    gate = Gate("")
    with patch.object(acd, "_gate_client", MagicMock(return_value=gate)):
        out = acd.relevance_gate(posts, _cfg(), {"relevance_gate": True, "min_relevance": 6})
    assert [p["post_url"] for p in out] == ["p3"]
    assert out[0]["relevance"] == 9 and "These" in out[0]["relevance_grund"]
    assert len(gate.calls) == 2                      # Stellenanzeige nie an das Modell
    assert acd.relevance_gate(posts, _cfg(), {"relevance_gate": False}) == posts


def test_domain_cap_ignores_rows_without_domain():
    # Livetest 14.09.2026: drei domainlose Posts, nur zwei Entwuerfe, weil ""
    # als eine Firma zaehlte.
    posts = [_post(f"p{i}", author=f"a{i}") for i in range(4)]
    picked = acd.apply_caps(posts, [], MON, {"drafts_total": 3, "per_domain_per_week": 2})
    assert len(picked) == 3
    mit = [dict(p, domain="x.com") for p in posts]
    assert len(acd.apply_caps(mit, [], MON, {"drafts_total": 3, "per_domain_per_week": 2})) == 2


def test_gate_parse_survives_garbage():
    assert acd._parse_gate("kein json") == (False, 0, "")
    assert acd._parse_gate('Hier: {"kommentierbar": false, "score": 2, "grund": "Event"}') == (False, 2, "Event")


def test_title_carries_typ_and_company_and_type_is_avoided_next():
    ctx, m = _patch(fetch_watchlist_posts=MagicMock(return_value=[_post("p1", "a1"), _post("p2", "a2")]))
    with ctx:
        acd.run_abm_comment_drafts(_cfg(), MON)
    draft = m["create_comment_entry"].call_args.args[0]
    assert draft["title"] == "ABM Kommentar [6 Der Beleg]: N N (Firma A)"
    calls = m["draft_comment"].call_args_list
    assert calls[0].kwargs["avoid_types"] == [] and calls[1].kwargs["avoid_types"] == ["6 Der Beleg"]


def test_gate_prompt_binds_to_the_posters_field():
    assert "Themenfeld von Richard" in acd.GATE_PROMPT.format(
        poster="Richard", name="n", title="t", company="c", text="x")
    assert "Börsen- und Aktienanalysen" in acd.GATE_PROMPT


def test_gate_rejects_competitors_and_sees_title():
    # Richard 15.09.2026: Konver und Pangea Summit sind Wettbewerber, nicht ICP.
    assert '"wettbewerber": true oder false' in acd.GATE_PROMPT.format(
        poster="Richard", name="n", title="t", company="c", text="x")
    # Wettbewerber schlaegt ein positives Themen-Urteil
    gate = _FakeGate('{"verkauft": "Sales Coaching", "wettbewerber": true, '
                     '"kommentierbar": true, "score": 9, "grund": "These"}')
    post = dict(_post(company="Konver"), title="Co-Founder & CEO")
    with patch.object(acd, "_gate_client", MagicMock(return_value=gate)):
        assert acd.relevance_gate([post], _cfg(), {"relevance_gate": True}) == []
    assert "Co-Founder & CEO, Konver" in gate.calls[0]
    assert acd._parse_gate('{"verkauft": "Compliance-Software", "wettbewerber": false, '
                           '"kommentierbar": true, "score": 8, "grund": "These"}') == (True, 8, "These")


def test_fetch_watchlist_posts_carries_title():
    item = {"content": "wort " * 30, "linkedinUrl": "p1", "postedAt": "x",
            "query": {"targetUrl": "u1"}}
    client = MagicMock()
    client.actor.return_value.call.return_value = {"defaultDatasetId": "d"}
    client.dataset.return_value.iterate_items.return_value = [item]
    row = {"linkedin_url": "u1", "first_name": "E", "last_name": "Y", "company": "Konver",
           "title": "Co-Founder & CEO", "prio": "2"}
    with patch.object(acd, "apify_client", MagicMock(return_value=client)), \
         patch.object(acd, "parse_post_age_hours", MagicMock(return_value=5)):
        posts = acd.fetch_watchlist_posts([row], {})
    assert posts[0]["title"] == "Co-Founder & CEO"


def test_jolly_config_block():
    from clients.jolly import config as jolly
    s = jolly.ABM_COMMENT_DRAFTS
    assert s["day"] is None and s["drafts_total"] == 3 and s["poster"] == "Richard"
    assert s["relevance_gate"] is True and s["max_age_hours"] <= 36
    assert s["max_posts_per_profile"] == 1
    assert any("lindner" in e for e in s["exclude_companies"])
    assert os.path.basename(s["watchlist_csv"]) == "abm_watchlist.csv"


def test_watchlist_builder_merges_sources_with_prio_and_dedupe(tmp_path):
    src = tmp_path / "watchlist"
    src.mkdir()
    (src / "sn_poster_ind4_hcC_2026-09-14.jsonl").write_text(
        json.dumps({"urn": "ACwAAA1", "person-name": "Anna Alt", "title": "CEO", "company-name": "Alt GmbH", "location": "Berlin"}) + "\n"
        + json.dumps({"urn": "ACwAAA2", "person-name": "Bert Bau", "title": "Founder", "company-name": "Bau AG", "location": "Wien"}) + "\n"
        + json.dumps({"urn": "ACwAAA9", "person-name": "Fuzzy Fill", "title": "Chief Technology Officer", "company-name": "Noise"}) + "\n",
        encoding="utf-8")
    (src / "sn_poster_ind96_hcD_2026-09-14.jsonl").write_text(
        json.dumps({"urn": "ACwAAA1", "person-name": "Anna Alt", "title": "CEO", "company-name": "Alt GmbH"}) + "\n",
        encoding="utf-8")
    (src / "hubspot_warm_2026-09-14.json").write_text(json.dumps([
        {"url": "https://www.linkedin.com/in/uwe-f", "name": "Uwe Forgber", "title": "MD", "company": "Realcube GmbH", "status": "IN_PROGRESS"}]),
        encoding="utf-8")
    (src / "pool_active_2026-09-14.json").write_text(json.dumps([
        {"url": "https://www.linkedin.com/in/uwe-f", "name": "Uwe Forgber", "title": "MD", "company": "Realcube GmbH", "src": "hubspot_warm", "age_hours": 40},
        {"url": "https://www.linkedin.com/in/carl-c", "name": "Carl Cee", "title": "CRO", "company": "Cee SaaS", "src": "li-saas-nomarketing-de", "age_hours": 500}]),
        encoding="utf-8")
    out = tmp_path / "abm_watchlist.csv"
    rows = jw.build(str(src), str(out))
    assert [r["prio"] for r in rows] == ["1", "2", "2", "3"]
    assert [r["last_name"] for r in rows] == ["Forgber", "Alt", "Bau", "Cee"]
    assert rows[1]["linkedin_url"] == "https://www.linkedin.com/in/ACwAAA1"
    assert rows[0]["first_name"] == "Uwe" and rows[0]["company"] == "Realcube GmbH"
    assert all(r["typ"] == "person" for r in rows)
    text = out.read_text(encoding="utf-8")
    assert text.startswith(HEADER.strip()) and text.count("\n") == 5
