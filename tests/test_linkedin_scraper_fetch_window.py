"""Tests for the Apify fetch window of the daily profile scraper.

Mocks the Apify client; no network, no spend. Guards the cost/coverage invariant:
der Actor rechnet pro geliefertem Post ab, das Fenster muss also so schmal wie
moeglich sein — aber echt groesser als MAX_AGE_HOURS, sonst faellt ein Post, der
beim letzten Lauf zu jung war, aus dem Fenster und wird nie gesehen.
"""
from datetime import datetime, timedelta, timezone

import pytest

from tools import linkedin_scraper
from tools.linkedin_scraper import fetch_window_start, scrape_posts_for_batch


class FakeClient:
    """Mimics ApifyClient: .actor(id).call(run_input=) -> run; .dataset(id).iterate_items()."""

    def __init__(self, items=()):
        self._items = list(items)
        self.last_run_input = None

    def actor(self, actor_id):
        self._actor_id = actor_id
        return self

    def call(self, run_input=None):
        self.last_run_input = run_input
        return type("Run", (), {"default_dataset_id": "ds1"})()

    def dataset(self, ds_id):
        return self

    def iterate_items(self):
        return iter(self._items)


def _parse(iso: str) -> datetime:
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc)


@pytest.fixture
def no_watermark(monkeypatch):
    monkeypatch.setattr(linkedin_scraper, "read_watermark", lambda: None)


@pytest.fixture
def watermark(monkeypatch):
    """Setzt die Zeitmarke auf 'vor N Stunden'."""
    def _set(hours_ago):
        mark = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        monkeypatch.setattr(linkedin_scraper, "read_watermark", lambda: mark)
    return _set


def _window_hours(**kwargs) -> float:
    return (datetime.now(timezone.utc) - _parse(fetch_window_start(**kwargs))).total_seconds() / 3600


# --- fetch_window_start, ohne Zeitmarke ---

def test_window_is_wider_than_the_age_filter(no_watermark):
    """Sonst verliert der naechste Lauf die Posts, die dieser Lauf als zu jung verwarf."""
    assert _window_hours() > linkedin_scraper.MAX_AGE_HOURS


def test_window_stays_close_to_the_age_filter(no_watermark):
    """Jede Stunde Fenster ueber MAX_AGE_HOURS hinaus kostet bezahlte, sofort verworfene Posts."""
    assert _window_hours() <= linkedin_scraper.MAX_AGE_HOURS + linkedin_scraper.FETCH_BUFFER_HOURS + 1


# --- fetch_window_start, mit Zeitmarke ---

def test_watermark_narrows_the_window(watermark):
    """Taeglicher Cron: das Fenster darf nicht bis MAX_AGE_HOURS zurueckreichen, sonst
    wird die Ueberlappung zum Vortag ein zweites Mal geliefert und bezahlt."""
    watermark(24)
    hours = _window_hours()
    expected = 24 + linkedin_scraper.MIN_AGE_HOURS + linkedin_scraper.WATERMARK_BUFFER_HOURS
    assert hours == pytest.approx(expected, abs=0.1)
    assert hours < linkedin_scraper.MAX_AGE_HOURS + linkedin_scraper.FETCH_BUFFER_HOURS


def test_watermark_window_still_covers_posts_dropped_as_too_young(watermark):
    """Der letzte Lauf hat Posts juenger als MIN_AGE_HOURS verworfen. Die muessen jetzt
    noch im Fenster liegen, sonst sind sie fuer immer weg."""
    watermark(24)
    assert _window_hours() >= 24 + linkedin_scraper.MIN_AGE_HOURS


def test_watermark_never_widens_beyond_the_age_filter(watermark):
    """Nach einer Cron-Pause (Mo: 72h seit Fr) darf das Fenster nicht mitwachsen —
    alles aelter als MAX_AGE_HOURS wuerde bezahlt und sofort verworfen."""
    watermark(72)
    ceiling = linkedin_scraper.MAX_AGE_HOURS + linkedin_scraper.FETCH_BUFFER_HOURS
    assert _window_hours() == pytest.approx(ceiling, abs=0.1)


def test_stale_watermark_falls_back_to_the_default_window(monkeypatch):
    """Unlesbare Zeitmarke darf den Lauf nicht kippen."""
    monkeypatch.setattr(linkedin_scraper, "get_meta", lambda key: "kein-datum")
    ceiling = linkedin_scraper.MAX_AGE_HOURS + linkedin_scraper.FETCH_BUFFER_HOURS
    assert _window_hours() == pytest.approx(ceiling, abs=0.1)


def test_unreachable_meta_store_falls_back_to_the_default_window(monkeypatch):
    def boom(key):
        raise RuntimeError("SUPABASE_URL is not set")
    monkeypatch.setattr(linkedin_scraper, "get_meta", boom)
    ceiling = linkedin_scraper.MAX_AGE_HOURS + linkedin_scraper.FETCH_BUFFER_HOURS
    assert _window_hours() == pytest.approx(ceiling, abs=0.1)


# --- run input ---

def test_run_input_sends_posted_limit_date_not_the_enum(no_watermark):
    client = FakeClient()
    scrape_posts_for_batch(client, ["https://www.linkedin.com/in/someone/"], max_posts=3)
    ri = client.last_run_input
    assert "postedLimit" not in ri, "das Enum-Fenster ist zu weit und wird pro Post bezahlt"
    assert _parse(ri["postedLimitDate"])  # parsebares ISO-8601-Datum
    assert ri["maxPosts"] == 3
    assert ri["scrapeReactions"] is False
    assert ri["scrapeComments"] is False


# --- Buendelung ---

def test_batch_sends_all_profiles_in_one_run(no_watermark):
    """maxPosts gilt laut Actor-Schema pro Profil, die Buendelung darf es nicht teilen."""
    client = FakeClient()
    urls = [f"https://www.linkedin.com/in/p{i}/" for i in range(20)]
    scrape_posts_for_batch(client, urls, max_posts=3)
    assert client.last_run_input["targetUrls"] == urls
    assert client.last_run_input["maxPosts"] == 3


def test_batch_reuses_the_passed_window(no_watermark):
    """Alle Batches eines Laufs muessen dasselbe Fenster sehen."""
    client = FakeClient()
    scrape_posts_for_batch(client, ["https://www.linkedin.com/in/a/"],
                           window_start="2026-08-16T05:00:00.000Z")
    assert client.last_run_input["postedLimitDate"] == "2026-08-16T05:00:00.000Z"


# --- Zuordnung Post -> Influencer im Sammel-Run ---

def test_target_url_maps_item_back_to_its_profile():
    item = {"query": {"targetUrl": "https://www.linkedin.com/in/TKKader/", "page": "1"}}
    assert linkedin_scraper.target_url_of(item) == "https://www.linkedin.com/in/tkkader"


def test_profile_key_ignores_trailing_slash_and_query():
    a = linkedin_scraper.profile_key("https://www.linkedin.com/in/x/")
    b = linkedin_scraper.profile_key("https://www.linkedin.com/in/x?miniProfileUrn=urn%3Ali")
    assert a == b


def test_author_name_is_the_fallback_when_query_is_missing():
    assert linkedin_scraper.target_url_of({"author": {"name": "TK Kader"}}) == ""
    assert linkedin_scraper.author_name_of({"author": {"name": "TK Kader"}}) == "TK Kader"


# --- scrape_new_posts: Batches, Zuordnung, Zeitmarke ---

def _item(target_url, post_id, age_hours):
    ts = int((datetime.now(timezone.utc) - timedelta(hours=age_hours)).timestamp() * 1000)
    return {
        "linkedinUrl": f"https://www.linkedin.com/feed/update/{post_id}",
        "content": " ".join(["wort"] * 60),
        "postedAt": {"timestamp": ts},
        "engagement": {"likes": 10, "comments": 2, "shares": 1},
        "query": {"targetUrl": target_url},
    }


@pytest.fixture
def scraper_env(monkeypatch, no_watermark):
    """Verdrahtet scrape_new_posts ohne Netz: feste Influencer-Liste, Fake-Apify,
    aufgezeichnete Zeitmarken-Schreibvorgaenge."""
    monkeypatch.setattr(linkedin_scraper, "MIN_AGE_HOURS", 6)
    monkeypatch.setattr(linkedin_scraper, "MAX_AGE_HOURS", 36)
    monkeypatch.setattr(linkedin_scraper, "BATCH_SIZE", 2)
    written = []
    monkeypatch.setattr(linkedin_scraper, "write_watermark", lambda ts: written.append(ts))

    def _build(influencers, batch_results):
        monkeypatch.setattr(linkedin_scraper, "load_influencers", lambda: influencers)
        monkeypatch.setattr(linkedin_scraper, "apify_client", lambda: object())
        calls = []

        def fake_batch(client, urls, max_posts=3, window_start=None):
            calls.append(list(urls))
            result = batch_results[len(calls) - 1]
            if isinstance(result, Exception):
                raise result
            return result

        monkeypatch.setattr(linkedin_scraper, "scrape_posts_for_batch", fake_batch)
        return calls, written

    return _build


def test_profiles_are_scraped_in_batches_not_one_run_each(scraper_env):
    influencers = [{"name": f"P{i}", "linkedin_url": f"https://www.linkedin.com/in/p{i}/"}
                   for i in range(5)]
    calls, _ = scraper_env(influencers, [[], [], []])
    linkedin_scraper.scrape_new_posts(existing_urls=set())
    assert [len(c) for c in calls] == [2, 2, 1], "5 Profile bei BATCH_SIZE=2 = 3 Runs"


def test_posts_are_attributed_to_the_influencer_from_the_csv(scraper_env):
    influencers = [{"name": "TK Kader", "linkedin_url": "https://www.linkedin.com/in/tkkader/"}]
    scraper_env(influencers, [[_item("https://www.linkedin.com/in/tkkader/", "a1", 12)]])
    posts = linkedin_scraper.scrape_new_posts(existing_urls=set())
    assert [p["influencer"] for p in posts] == ["TK Kader"]


def test_unmapped_item_falls_back_to_the_author_name(scraper_env):
    influencers = [{"name": "TK Kader", "linkedin_url": "https://www.linkedin.com/in/tkkader/"}]
    stray = _item("https://www.linkedin.com/in/someone-else/", "a2", 12)
    stray["author"] = {"name": "Someone Else"}
    scraper_env(influencers, [[stray]])
    posts = linkedin_scraper.scrape_new_posts(existing_urls=set())
    assert [p["influencer"] for p in posts] == ["Someone Else"]


def test_watermark_is_written_after_a_complete_run(scraper_env):
    influencers = [{"name": "A", "linkedin_url": "https://www.linkedin.com/in/a/"}]
    _, written = scraper_env(influencers, [[]])
    linkedin_scraper.scrape_new_posts(existing_urls=set())
    assert len(written) == 1


def test_watermark_is_held_back_when_a_batch_fails(scraper_env):
    """Sonst faellt der ausgefallene Batch aus dem Fenster des naechsten Laufs."""
    influencers = [{"name": f"P{i}", "linkedin_url": f"https://www.linkedin.com/in/p{i}/"}
                   for i in range(4)]
    _, written = scraper_env(influencers, [[], RuntimeError("Apify 500")])
    linkedin_scraper.scrape_new_posts(existing_urls=set())
    assert written == [], "Teilausfall darf die Zeitmarke nicht vorruecken"


def test_profiles_without_url_are_skipped(scraper_env):
    influencers = [{"name": "A", "linkedin_url": ""},
                   {"name": "B", "linkedin_url": "https://www.linkedin.com/in/b/"}]
    calls, _ = scraper_env(influencers, [[]])
    linkedin_scraper.scrape_new_posts(existing_urls=set())
    assert calls == [["https://www.linkedin.com/in/b/"]]
