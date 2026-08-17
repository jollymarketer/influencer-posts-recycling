"""Kommentar-Kadenz: Wochentags-Gate, Gesamt-Deckel, Poster-Rotation.

Anlass (Richard 2026-07-30, Kundenfeedback Jae): lisocon produzierte 6
Kommentar-Entwuerfe pro Tag = 30 pro Woche. Soll sind 3 pro Woche, verteilt
statt geblockt.
"""
import importlib
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.comment_drafts import assign_posts, poster_rotation

POSTS = [{"post_url": f"p{i}", "post_text": "x", "influencer": f"inf{i}"}
         for i in range(10)]
POSTERS = ["Reinhard", "Jae"]
DAYS = (0, 2, 4)


def _day(week: int, offset: int) -> datetime:
    """Montag der ISO-Woche `week` in 2026, plus `offset` Tage."""
    return (datetime.fromisocalendar(2026, week, 1).replace(tzinfo=timezone.utc)
            + timedelta(days=offset))


def test_total_caps_below_per_poster_product():
    assert len(assign_posts(POSTS, POSTERS, 3, total=1)) == 1
    assert len(assign_posts(POSTS, POSTERS, 3, total=4)) == 4


def test_total_wins_over_a_too_small_per_poster_number():
    """Anlass 10.08.2026: drafts_total 5 bei drafts_per_poster 1 und zwei
    Postern haette still 2 Entwuerfe ergeben. Der Deckel ist bindend."""
    assert len(assign_posts(POSTS, POSTERS, 1, total=5)) == 5
    assert len(assign_posts(POSTS, ["Christian"], 1, total=5)) == 5


def test_client_configs_can_actually_reach_their_total():
    """Die Configs sollen den Deckel auch ohne die Notbremse oben erreichen."""
    for module in ("clients.lisocon.config", "clients.swot.config"):
        cfg = importlib.import_module(module)
        s = cfg.COMMENT_DRAFTS
        assert s["drafts_per_poster"] * len(s["posters"]) >= s["drafts_total"], module


def test_total_none_keeps_old_behaviour():
    assert len(assign_posts(POSTS, POSTERS, 3)) == 6
    assert len(assign_posts(POSTS, POSTERS, 3, total=None)) == 6


def test_total_never_exceeds_available_posts():
    assert len(assign_posts(POSTS[:2], POSTERS, 3, total=5)) == 2


def test_one_post_is_never_assigned_twice():
    assigned = assign_posts(POSTS, POSTERS, 3, total=3)
    assert len({post["post_url"] for _, post in assigned}) == 3


def test_poster_rotation_alternates_across_comment_days():
    """Mo/Mi/Fr liegen alle auf geraden yday-Abstaenden - eine Rotation ueber
    tm_yday % 2 wuerde immer denselben Poster ziehen."""
    seen = [poster_rotation(POSTERS, DAYS, _day(32, o))[0] for o in (0, 2, 4)]
    assert len(set(seen)) == 2, seen


def test_poster_rotation_continues_into_next_week():
    a = [poster_rotation(POSTERS, DAYS, _day(32, o))[0] for o in (0, 2, 4)]
    b = [poster_rotation(POSTERS, DAYS, _day(33, o))[0] for o in (0, 2, 4)]
    assert a != b


def test_poster_rotation_is_stable_within_one_day():
    day = _day(32, 0)
    assert poster_rotation(POSTERS, DAYS, day) == poster_rotation(POSTERS, DAYS, day)


def test_poster_rotation_without_days_falls_back():
    day = _day(32, 0)
    assert set(poster_rotation(POSTERS, None, day)) == set(POSTERS)
    assert poster_rotation([], DAYS, day) == []


# --- Fetch-Fenster des Kommentar-Pfads ---

class _FakeClient:
    """Mimikt ApifyClient: .actor(id).call(run_input=) -> run mit default_dataset_id."""

    def __init__(self):
        self.last_run_input = None

    def actor(self, actor_id):
        return self

    def call(self, run_input=None):
        self.last_run_input = run_input
        return type("Run", (), {"default_dataset_id": "ds1"})()

    def dataset(self, ds_id):
        return self

    def iterate_items(self):
        return iter(())


def _run_input(settings, monkeypatch):
    from tools import comment_drafts
    client = _FakeClient()
    monkeypatch.setattr(comment_drafts, "APIFY_API_KEY", "test-key")
    monkeypatch.setattr(comment_drafts, "ApifyClient", lambda key: client)
    comment_drafts.fetch_fresh_posts(
        [{"name": "A", "linkedin_url": "https://www.linkedin.com/in/a/"}], settings)
    return client.last_run_input


def _window_hours(iso: str) -> float:
    cutoff = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - cutoff).total_seconds() / 3600


def test_comment_run_sends_a_date_not_the_week_enum(monkeypatch):
    """`postedLimit="week"` holt 168h, gefiltert wird auf max_age_hours — die
    Differenz wird pro Post bezahlt und sofort verworfen."""
    ri = _run_input({"max_age_hours": 72, "max_posts_per_profile": 2}, monkeypatch)
    assert "postedLimit" not in ri
    assert _window_hours(ri["postedLimitDate"]) < 168


def test_comment_window_follows_max_age_hours(monkeypatch):
    from tools import linkedin_scraper
    ri = _run_input({"max_age_hours": 72, "max_posts_per_profile": 2}, monkeypatch)
    hours = _window_hours(ri["postedLimitDate"])
    assert 72 < hours <= 72 + linkedin_scraper.FETCH_BUFFER_HOURS + 1


def test_comment_window_is_wider_than_the_age_filter(monkeypatch):
    """Sonst verliert ein verspaeteter Cron-Lauf Posts am Fensterrand."""
    for max_age in (30, 72, 168):
        ri = _run_input({"max_age_hours": max_age, "max_posts_per_profile": 2}, monkeypatch)
        assert _window_hours(ri["postedLimitDate"]) > max_age
