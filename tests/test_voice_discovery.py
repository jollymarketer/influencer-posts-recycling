"""Autoren-URL im Keyword-Scrape und Stimmen-Discovery.

Hintergrund (Richard, 19.08.2026): Einzelne Beraterinnen und Berater lassen sich
ueber die Websuche kaum finden, ueber den Keyword-Scrape aber sehr wohl - dort
steht unter jedem Fachbeitrag ein Autor. Bisher hat extract_keyword_post nur den
NAMEN behalten, nicht die Profil-URL, und ohne URL kann kein Fund in
influencers.csv. Diese Tests sichern die URL-Extraktion und die Aggregation.
"""
from tools.linkedin_keyword_scraper import extract_keyword_post
from tools.discover_voices import aggregate_authors, is_vendor


def _item(url="https://www.linkedin.com/posts/max-mustermann_abc-123",
          author=None, content=None, likes=10, comments=2, shares=1):
    return {
        "linkedinUrl": url,
        "content": content or ("Wort " * 60).strip(),
        "author": author if author is not None else {
            "name": "Max Mustermann",
            "linkedinUrl": "https://www.linkedin.com/in/max-mustermann/",
            "headline": "Selbstaendiger Unternehmensberater, Controlling",
        },
        "engagement": {"likes": likes, "comments": comments, "shares": shares},
        "postedAt": {"date": "2026-08-18"},
    }


def test_author_url_wird_uebernommen():
    post = extract_keyword_post(_item())
    assert post["author_url"] == "https://www.linkedin.com/in/max-mustermann/"
    assert post["author_headline"].startswith("Selbstaendiger")


def test_author_url_alternative_feldnamen():
    for feld in ("url", "profileUrl", "publicProfileUrl"):
        item = _item(author={"name": "A B", feld: "https://www.linkedin.com/in/ab/"})
        assert extract_keyword_post(item)["author_url"] == "https://www.linkedin.com/in/ab/"


def test_fehlende_author_url_bricht_nicht():
    post = extract_keyword_post(_item(author={"name": "Ohne URL"}))
    assert post["author_url"] == ""
    assert post["influencer"] == "Ohne URL"


def test_aggregation_zaehlt_und_summiert():
    posts = [
        {"influencer": "A", "author_url": "https://www.linkedin.com/in/a/",
         "author_headline": "Berater", "virality": 4},
        {"influencer": "A", "author_url": "https://www.linkedin.com/in/a/",
         "author_headline": "Berater", "virality": 6},
        {"influencer": "B", "author_url": "https://www.linkedin.com/in/b/",
         "author_headline": "Controller", "virality": 9},
    ]
    out = aggregate_authors(posts, min_posts=1)
    assert out[0]["name"] == "A"          # 2 Beitraege schlagen 1 Beitrag
    assert out[0]["posts"] == 2
    assert out[0]["virality_sum"] == 10


def test_aggregation_filtert_seltene_autoren():
    posts = [{"influencer": "A", "author_url": "https://www.linkedin.com/in/a/",
              "author_headline": "", "virality": 5}]
    assert aggregate_authors(posts, min_posts=2) == []


def test_aggregation_ignoriert_autoren_ohne_url():
    posts = [{"influencer": "A", "author_url": "", "author_headline": "", "virality": 5}] * 3
    assert aggregate_authors(posts, min_posts=1) == []


def test_vendor_filter_trifft_gesperrte_anbieter():
    """Sperre Christian Kulle, 13.08.2026 - gilt auch fuer neu gefundene Stimmen."""
    assert is_vendor("LucaNet", "")
    assert is_vendor("Max Mustermann", "Senior Sales Manager bei Jedox")
    assert is_vendor("Anna Beispiel", "Account Executive, Corporate Planning")
    assert is_vendor("Tidely GmbH", "")
    assert not is_vendor("Max Mustermann", "Selbstaendiger Unternehmensberater, Controlling")
    assert not is_vendor("Anna Beispiel", "Steuerberaterin und Wirtschaftspruerin")
