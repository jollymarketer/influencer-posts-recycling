"""Tests for the Apify fetch window of the daily profile scraper.

Mocks the Apify client; no network, no spend. Guards the cost/coverage invariant:
der Actor rechnet pro geliefertem Post ab, das Fenster muss also so schmal wie
moeglich sein — aber echt groesser als MAX_AGE_HOURS, sonst faellt ein Post, der
beim letzten Lauf zu jung war, aus dem Fenster und wird nie gesehen.
"""
from datetime import datetime, timedelta, timezone

from tools import linkedin_scraper
from tools.linkedin_scraper import fetch_window_start, scrape_posts_for_profile


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


# --- fetch_window_start ---

def test_window_is_wider_than_the_age_filter():
    """Sonst verliert der naechste Lauf die Posts, die dieser Lauf als zu jung verwarf."""
    age_hours = (datetime.now(timezone.utc) - _parse(fetch_window_start())).total_seconds() / 3600
    assert age_hours > linkedin_scraper.MAX_AGE_HOURS


def test_window_stays_close_to_the_age_filter():
    """Jede Stunde Fenster ueber MAX_AGE_HOURS hinaus kostet bezahlte, sofort verworfene Posts."""
    age_hours = (datetime.now(timezone.utc) - _parse(fetch_window_start())).total_seconds() / 3600
    assert age_hours <= linkedin_scraper.MAX_AGE_HOURS + linkedin_scraper.FETCH_BUFFER_HOURS + 1


# --- run input ---

def test_run_input_sends_posted_limit_date_not_the_enum():
    client = FakeClient()
    scrape_posts_for_profile(client, "https://www.linkedin.com/in/someone/", max_posts=3)
    ri = client.last_run_input
    assert "postedLimit" not in ri, "das Enum-Fenster ist zu weit und wird pro Post bezahlt"
    assert _parse(ri["postedLimitDate"])  # parsebares ISO-8601-Datum
    assert ri["maxPosts"] == 3
    assert ri["scrapeReactions"] is False
    assert ri["scrapeComments"] is False
