"""Tests for the keyword-based LinkedIn post scraper (harvestapi/linkedin-post-search).

Mocks the Apify client; no network, no spend. Validates run-input construction and item parsing
into the post-dict shape that supabase_db.upsert_posts expects.
"""
from tools.linkedin_keyword_scraper import (
    build_run_input,
    extract_keyword_post,
    is_hiring_ad,
    scrape_keyword_posts,
)


def _item(url, text, author="Jane Doe", likes=10, comments=2, shares=1):
    return {
        "linkedinUrl": url,
        "content": text,
        "postedAt": {"date": "2026-06-05T10:00:00Z", "timestamp": 1781000000000},
        "author": {"name": author},
        "engagement": {"likes": likes, "comments": comments, "shares": shares},
    }


_LONG = " ".join(["wort"] * 60)  # 60 words, passes the >=50 filter


class FakeClient:
    """Mimics ApifyClient: .actor(id).call(run_input=) -> run; .dataset(id).iterate_items()."""

    def __init__(self, items):
        self._items = items
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


# --- build_run_input ---

def test_build_run_input_sets_search_queries_and_defaults():
    ri = build_run_input(["revops", "cold email"], max_posts=20, posted_limit="month", sort_by="relevance")
    assert ri["searchQueries"] == ["revops", "cold email"]
    assert ri["maxPosts"] == 20
    assert ri["postedLimit"] == "month"
    assert ri["sortBy"] == "relevance"
    # mining wants post text only, no costly enrichment
    assert ri.get("scrapeReactions") is False
    assert ri.get("scrapeComments") is False


def test_build_run_input_omits_author_keywords_when_empty():
    ri = build_run_input(["revops"])
    assert "authorKeywords" not in ri


def test_build_run_input_includes_author_keywords_when_given():
    ri = build_run_input(["revops"], author_keywords="revops, gtm, sales")
    assert ri["authorKeywords"] == "revops, gtm, sales"


# --- extract_keyword_post ---

def test_extract_parses_core_fields():
    post = extract_keyword_post(_item("https://linkedin.com/posts/x", _LONG, author="Sam Lee"))
    assert post["post_url"] == "https://linkedin.com/posts/x"
    assert post["influencer"] == "Sam Lee"
    assert post["post_text"] == _LONG
    assert post["date"].startswith("2026-06-05")
    assert post["engagement"] == {"likes": 10, "comments": 2, "shares": 1}


def test_extract_drops_short_posts():
    assert extract_keyword_post(_item("https://x", "too short", author="A")) is None


def test_extract_drops_missing_url_or_text():
    assert extract_keyword_post(_item("", _LONG)) is None
    assert extract_keyword_post(_item("https://x", "")) is None


def test_extract_handles_alternate_author_keys():
    item = _item("https://x", _LONG)
    del item["author"]
    item["authorFullName"] = "Alt Name"
    assert extract_keyword_post(item)["influencer"] == "Alt Name"


# --- scrape_keyword_posts ---

def test_scrape_aggregates_and_dedups_existing():
    items = [
        _item("https://a", _LONG),
        _item("https://b", _LONG),
        _item("https://a", _LONG),  # duplicate url within results
    ]
    client = FakeClient(items)
    posts = scrape_keyword_posts(["revops"], existing_urls={"https://b"}, client=client)
    urls = {p["post_url"] for p in posts}
    assert urls == {"https://a"}  # b excluded (existing), a deduped to one
    assert client.last_run_input["searchQueries"] == ["revops"]


# --- virality filter ---

def test_extract_includes_virality_score():
    # likes 200 + comments 30*3 + shares 5*5 = 315 -> high log score
    post = extract_keyword_post(_item("https://x", _LONG, likes=200, comments=30, shares=5))
    assert isinstance(post["virality"], int)
    assert post["virality"] >= 7


def test_scrape_filters_below_min_virality():
    items = [
        _item("https://low", _LONG, likes=1, comments=0, shares=0),       # tiny -> low score
        _item("https://high", _LONG, likes=400, comments=60, shares=10),  # viral -> high score
    ]
    posts = scrape_keyword_posts(["revops"], min_virality=6, client=FakeClient(items))
    urls = {p["post_url"] for p in posts}
    assert urls == {"https://high"}


# --- hiring-ad exclusion ---

_HIRING = "We're hiring a GTM Engineer to join our team. " + " ".join(["detail"] * 55)
_NORMAL = "Here is my contrarian take on revenue operations. " + " ".join(["wort"] * 55)


def test_is_hiring_ad_detects_job_posts():
    assert is_hiring_ad(_HIRING) is True
    assert is_hiring_ad("Wir suchen einen Sales Manager (m/w/d) ab sofort.") is True


def test_is_hiring_ad_false_for_thought_leadership():
    assert is_hiring_ad(_NORMAL) is False


def test_scrape_excludes_hiring_ads_by_default():
    items = [
        _item("https://job", _HIRING, likes=500, comments=80, shares=20),  # viral hiring ad
        _item("https://post", _NORMAL, likes=500, comments=80, shares=20),
    ]
    posts = scrape_keyword_posts(["gtm"], min_virality=0, client=FakeClient(items))
    assert {p["post_url"] for p in posts} == {"https://post"}  # hiring ad dropped despite virality


def test_scrape_keeps_hiring_when_disabled():
    items = [_item("https://job", _HIRING, likes=500, comments=80, shares=20)]
    posts = scrape_keyword_posts(["gtm"], min_virality=0, exclude_hiring=False, client=FakeClient(items))
    assert {p["post_url"] for p in posts} == {"https://job"}
