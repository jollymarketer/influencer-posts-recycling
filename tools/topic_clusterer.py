"""Single-pass Claude clustering of accumulated influencer posts into
blog-topic candidates. One API call per weekly run.
"""
import json
import os
import re
from dataclasses import dataclass, field

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
MIN_POSTS = 2
EXCERPT_LEN = 500


@dataclass
class ThemeCandidate:
    theme_label: str
    support_count: int
    sample_influencers: list[str]
    blog_score: int
    suggested_title_en: str
    suggested_title_de: str
    keyword_en: str
    keyword_de: str
    supporting_post_urls: list[str] = field(default_factory=list)


SYSTEM_PROMPT = (
    "You are a B2B content strategist for Jolly Marketer, a Berlin-based B2B "
    "RevOps/GTM agency serving the DACH market (B2B SaaS, tech services, "
    "industrial SMEs). You cluster LinkedIn/Substack posts into blog-topic "
    "themes for jollymarketer.com and score each theme's blog potential."
)


def _build_user_prompt(posts: list[dict], recent_titles: list[str]) -> str:
    lines = []
    for p in posts:
        eng = p.get("engagement") or {}
        likes = eng.get("likes", p.get("likes", 0))
        comments = eng.get("comments", p.get("comments", 0))
        text = (p.get("post_text") or "")[:EXCERPT_LEN]
        url = p.get("post_url", "")
        lines.append(
            f"- influencer={p.get('influencer','')} likes={likes} comments={comments} "
            f"url={url}\n  {text}"
        )
    posts_block = "\n".join(lines)
    avoid = "; ".join(recent_titles) if recent_titles else "(none)"
    return (
        f"Here are influencer posts from the last 7 days:\n\n{posts_block}\n\n"
        f"Group them into 3-8 blog-topic themes. AVOID themes that duplicate any "
        f"of these recently-suggested titles: {avoid}.\n\n"
        "For each theme return an object with EXACTLY these keys:\n"
        "  theme_label (string), support_count (int = how many posts back it), "
        "sample_influencers (array of strings), blog_score (int 0-100 weighing "
        "SEO/search intent, evergreen potential, cluster support depth, and fit "
        "to Jolly B2B-DACH ICP), suggested_title_en, suggested_title_de, "
        "keyword_en, keyword_de, supporting_post_urls (array of the source URLs).\n\n"
        "Return ONLY a JSON array of these objects. No prose, no code fence."
    )


def _parse_clusters(raw: str) -> list[ThemeCandidate]:
    text = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for d in data:
        if not isinstance(d, dict):
            continue
        try:
            out.append(ThemeCandidate(
                theme_label=str(d.get("theme_label", "")).strip(),
                support_count=int(d.get("support_count", 0) or 0),
                sample_influencers=list(d.get("sample_influencers", []) or []),
                blog_score=int(d.get("blog_score", 0) or 0),
                suggested_title_en=str(d.get("suggested_title_en", "")).strip(),
                suggested_title_de=str(d.get("suggested_title_de", "")).strip(),
                keyword_en=str(d.get("keyword_en", "")).strip(),
                keyword_de=str(d.get("keyword_de", "")).strip(),
                supporting_post_urls=list(d.get("supporting_post_urls", []) or []),
            ))
        except (ValueError, TypeError):
            continue
    return out


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def filter_candidates(
    candidates: list[ThemeCandidate],
    *,
    threshold: int,
    top_n: int,
    recent_titles: list[str],
) -> list[ThemeCandidate]:
    """Drop below-threshold themes, dedup against recent titles (case-insensitive
    normalized substring either direction), sort by score desc, cap at top_n."""
    recent_norm = [_norm(t) for t in recent_titles if t]

    def is_dupe(c: ThemeCandidate) -> bool:
        for cand_text in (_norm(c.theme_label), _norm(c.suggested_title_en), _norm(c.suggested_title_de)):
            if not cand_text:
                continue
            for r in recent_norm:
                if cand_text in r or r in cand_text:
                    return True
        return False

    kept = [c for c in candidates if c.blog_score >= threshold and not is_dupe(c)]
    kept.sort(key=lambda c: c.blog_score, reverse=True)
    return kept[:top_n]


def cluster_topics(posts: list[dict], recent_titles: list[str]) -> list[ThemeCandidate]:
    """One Claude call clustering posts into theme candidates. Returns [] if too
    few posts or on unparseable output. Caller applies filter_candidates()."""
    if len(posts) < MIN_POSTS:
        return []
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(posts, recent_titles)}],
    )
    raw = resp.content[0].text if resp.content else ""
    return _parse_clusters(raw)
