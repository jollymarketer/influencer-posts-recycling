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
    assert post["author_url"] == "https://www.linkedin.com/in/max-mustermann"
    assert post["author_headline"].startswith("Selbstaendiger")


def test_author_url_alternative_feldnamen():
    for feld in ("url", "profileUrl", "publicProfileUrl"):
        item = _item(author={"name": "A B", feld: "https://www.linkedin.com/in/ab/"})
        assert extract_keyword_post(item)["author_url"] == "https://www.linkedin.com/in/ab"


def test_fehlende_author_url_bricht_nicht():
    post = extract_keyword_post(_item(author={"name": "Ohne URL"}))
    assert post["author_url"] == ""
    assert post["influencer"] == "Ohne URL"


DE = "Wir haben die Planung mit dem Team besprochen und sind auch der Meinung dass sich das lohnt"


def test_aggregation_zaehlt_und_summiert():
    posts = [
        {"influencer": "A", "author_url": "https://www.linkedin.com/in/a",
         "author_headline": "Berater", "virality": 4, "post_text": DE},
        {"influencer": "A", "author_url": "https://www.linkedin.com/in/a",
         "author_headline": "Berater", "virality": 6, "post_text": DE},
        {"influencer": "B", "author_url": "https://www.linkedin.com/in/b",
         "author_headline": "Controller", "virality": 9, "post_text": DE},
    ]
    out = aggregate_authors(posts, min_posts=1)
    assert out[0]["name"] == "A"          # 2 Beitraege schlagen 1 Beitrag
    assert out[0]["posts"] == 2
    assert out[0]["virality_sum"] == 10


def test_aggregation_filtert_seltene_autoren():
    posts = [{"influencer": "A", "author_url": "https://www.linkedin.com/in/a",
              "author_headline": "", "virality": 5, "post_text": DE}]
    assert aggregate_authors(posts, min_posts=2) == []


def test_aggregation_ignoriert_autoren_ohne_url():
    posts = [{"influencer": "A", "author_url": "", "author_headline": "",
              "virality": 5, "post_text": DE}] * 3
    assert aggregate_authors(posts, min_posts=1) == []


def test_vendor_filter_trifft_gesperrte_anbieter():
    """Sperre Christian Kulle, 13.08.2026 - gilt auch fuer neu gefundene Stimmen."""
    assert is_vendor("LucaNet", "")
    assert is_vendor("Max Mustermann", "Senior Sales Manager bei Jedox")
    assert is_vendor("Anna Beispiel", "Account Executive, Corporate Planning")
    assert is_vendor("Tidely GmbH", "")
    assert not is_vendor("Max Mustermann", "Selbstaendiger Unternehmensberater, Controlling")
    assert not is_vendor("Anna Beispiel", "Steuerberaterin und Wirtschaftspruerin")


# --- Nachtrag aus dem Livelauf vom 19.08.2026 ---

def test_headline_kommt_aus_dem_feld_info():
    """Der Actor nennt die Positionszeile `info`, nicht `headline`."""
    item = _item(author={"name": "A", "publicIdentifier": "a",
                         "info": "Kaufmaennischer Leiter"})
    assert extract_keyword_post(item)["author_headline"] == "Kaufmaennischer Leiter"


def test_url_wird_kanonisch_aus_dem_slug_gebaut():
    item = _item(author={"name": "A", "type": "profile", "publicIdentifier": "max-mustermann",
                         "linkedinUrl": "https://www.linkedin.com/in/max-mustermann?miniProfileUrn=urn%3Ali%3Ax"})
    assert extract_keyword_post(item)["author_url"] == "https://www.linkedin.com/in/max-mustermann"


def test_firmenseite_bekommt_company_pfad():
    item = _item(author={"name": "X GmbH", "type": "company", "publicIdentifier": "x-gmbh"})
    post = extract_keyword_post(item)
    assert post["author_url"] == "https://www.linkedin.com/company/x-gmbh"
    assert post["author_type"] == "company"


def test_tracking_query_und_posts_suffix_fallen_weg():
    item = _item(author={"name": "X", "linkedinUrl": "https://www.linkedin.com/company/cashlink/posts?x=1"})
    assert extract_keyword_post(item)["author_url"] == "https://www.linkedin.com/company/cashlink"


def test_firmen_werden_standardmaessig_ausgefiltert():
    from tools.discover_voices import aggregate_authors
    posts = [{"influencer": "X GmbH", "author_url": "https://www.linkedin.com/company/x",
              "author_headline": "", "author_type": "company", "virality": 5,
              "post_text": "Wir und die Planung ist mit dem Team auf dem Weg dass sich das lohnt"}]
    assert aggregate_authors(posts, min_posts=1) == []
    assert len(aggregate_authors(posts, min_posts=1, nur_personen=False)) == 1


def test_nichtdeutsche_beitraege_fallen_raus():
    from tools.discover_voices import aggregate_authors, is_german
    assert not is_german("This is an English post about liquidity planning and controlling")
    assert is_german("Wir haben die Planung mit dem Team besprochen und sind auch der Meinung dass sich das lohnt")
    posts = [{"influencer": "Li Chen", "author_url": "https://www.linkedin.com/in/li",
              "author_headline": "", "author_type": "profile", "virality": 5,
              "post_text": "This is an English post about cash flow and planning software"}]
    assert aggregate_authors(posts, min_posts=1) == []


def test_vertriebsrollen_fallen_raus():
    from tools.discover_voices import is_vendor
    assert is_vendor("Jean-Luc Lebaillif", "Senior Sales Manager - Automotive - Semiconductor")
    assert is_vendor("Nomentia", "")
    assert not is_vendor("Anna Beispiel", "Kaufmaennische Leiterin, Sozialwirtschaft")
