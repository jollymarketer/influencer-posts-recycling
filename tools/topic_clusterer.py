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
MAX_TOKENS = 8192
MIN_POSTS = 2  # Bare minimum to attempt clustering, not a quality bar; caller filters further.
MIN_MATCH_LEN = 12
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
    # Verbatim source-post sentence backing any number in the titles ("" when the
    # titles carry no number). Written to Notion for pick-time provenance and
    # enforced by _has_unbacked_number.
    evidence_quote: str = ""


SYSTEM_PROMPT = (
    "You are a B2B content strategist for Jolly Marketer, a Berlin-based B2B "
    "RevOps/GTM agency serving the DACH market (B2B SaaS, tech services, "
    "industrial SMEs). You cluster LinkedIn/Substack posts into blog-topic "
    "themes for jollymarketer.com and score each theme's blog potential."
)


def _build_user_prompt(posts: list[dict], recent_titles: list[str],
                       taste: dict | None = None) -> str:
    lines = []
    for p in posts:
        eng = p.get("engagement") or {}
        likes = eng.get("likes", p.get("likes", 0))
        comments = eng.get("comments", p.get("comments", 0))
        shares = eng.get("shares", p.get("shares", 0))
        text = (p.get("post_text") or "")[:EXCERPT_LEN]
        lines.append(
            f"- influencer={p.get('influencer','')} likes={likes} comments={comments} "
            f"shares={shares}\n  {text}"
        )
    posts_block = "\n".join(lines)
    avoid = "; ".join(recent_titles) if recent_titles else "(none)"
    # Richard's revealed taste (from his real picks/rejects in the Blog Pipeline);
    # shapes topic generation AND blog_score calibration. Hard rules (Clay cap,
    # HubSpot ban) stay as deterministic filters regardless of this block.
    taste_block = ""
    if taste and (taste.get("picked") or taste.get("rejected")):
        liked = "; ".join(taste.get("picked") or []) or "(none yet)"
        disliked = "; ".join(taste.get("rejected") or []) or "(none yet)"
        taste_block = (
            "RICHARD'S REVEALED TASTE — learned from his real approve/reject decisions "
            "on past candidates. Weigh this heavily in topic choice and blog_score:\n"
            f"He APPROVED these (generate topics matching this taste): {liked}\n"
            f"He REJECTED these (do NOT propose similar angles): {disliked}\n\n"
        )
    return (
        taste_block +
        f"Here are recent, high-engagement B2B LinkedIn/Substack posts:\n\n{posts_block}\n\n"
        "Extract 15-25 HYPER-SPECIFIC, ULTRA-LONG-TAIL blog-post topics for jollymarketer.com.\n"
        "Each must be ONE single concrete buyer question - the kind someone types verbatim into Google "
        "or ChatGPT when they have exactly that problem. Anchor every topic to at least one concrete "
        "specific: a NAMED tool (Smartlead, Apollo, n8n, Claude), a specific CHANNEL, a specific "
        "ROLE/segment, a specific SCENARIO - or a NUMBER/threshold, but ONLY if one of the posts above "
        "states that exact number with the same unit and meaning. NEVER invent a number, and NEVER "
        "change its unit or what it measures (a post saying '20.000 EUR contract value' does NOT "
        "license a title about '20.000 accounts'). A topic with no source-backed number simply uses a "
        "non-numeric anchor. 6-10 word keyword. "
        "Do not stop at the topic level - go one level deeper into the exact sub-question.\n"
        "Apply this three-level transformation and always output LEVEL 3:\n"
        "  L1 head 'Cold email deliverability'\n"
        "  L2 long-tail 'Warum B2B Cold Emails im Spam landen: SPF, DKIM, DMARC setzen'\n"
        "  L3 ULTRA 'Wie viele Cold Emails pro Domain und Tag 2026, ohne im Spam zu landen?'\n"
        "  L1 'RevOps process design' -> L3 'Ab wie vielen Pflichtfeldern im CRM-Deal kippt die "
        "Datenqualitaet (und welche 5 reichen)?'\n"
        "  L1 'GTM engineering' -> L3 'Ab welchem ARR lohnt sich der erste GTM Engineer statt eines "
        "zweiten SDR im DACH-SaaS?'\n"
        "  L1 'ICP' -> L3 'ICP aus 20 Closed-Won-Deals in Claude extrahieren: das Prompt-Template'\n\n"
        f"AVOID topics that duplicate any of these recently-suggested titles: {avoid}.\n\n"
        "Jolly no longer uses or promotes Clay: DE-PRIORITIZE any topic whose core hook is the Clay "
        "tool specifically (cap its blog_score at 40). Passing mentions are fine; stay tool-agnostic.\n\n"
        "EXCLUDE any topic whose core hook is the HubSpot tool (Richard 2026-07-12: no HubSpot-centric "
        "blog topics). Do not propose them at all; a passing HubSpot mention inside a broader "
        "RevOps/CRM topic is fine.\n\n"
        "For each topic return an object with EXACTLY these keys:\n"
        "  theme_label (string = short internal label), support_count (int = how many posts back it), "
        "sample_influencers (array of strings), blog_score (int 0-100 weighing long-tail search "
        "intent, evergreen potential, cluster support depth, and fit to Jolly B2B-DACH ICP), "
        "suggested_title_en, suggested_title_de (the full long-tail article title), "
        "keyword_en, keyword_de (the 4-8 word long-tail keyword), "
        "evidence_quote (string: if either title contains a number, the VERBATIM sentence from one of "
        "the posts above that states that number - copy it exactly, do not paraphrase; \"\" when the "
        "titles carry no number). Candidates whose title numbers are missing from their "
        "evidence_quote are dropped by a deterministic filter, so an unbacked number wastes the slot.\n\n"
        "Do NOT echo post URLs. Return ONLY a JSON array of these objects. No prose, no code fence."
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
                evidence_quote=str(d.get("evidence_quote", "")).strip(),
            ))
        except (ValueError, TypeError):
            continue
    return out


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


# Deterministic backstop for the prompt's "cap its blog_score at 40" Clay rule:
# the prompt line is advisory (LLM can ignore it), this clamp is not. With
# SCORE_THRESHOLD = 70 in run_topic_mining.py the capped topics are dropped;
# under a threshold <= 40 they survive but sort last (de-prioritized).
CLAY_SCORE_CAP = 40
_CLAY_RE = re.compile(r"\bclay\b", re.IGNORECASE)

# Hard ban (Richard 2026-07-12): no HubSpot-hook blog topics at all. The prompt
# excludes them; this filter is the deterministic backstop. Unlike the Clay cap
# (de-prioritise), a HubSpot hook drops the candidate outright at ANY threshold.
_HUBSPOT_RE = re.compile(r"\bhubspot\b", re.IGNORECASE)


def _hook_fields(c: ThemeCandidate) -> tuple:
    return (c.theme_label, c.suggested_title_en, c.suggested_title_de,
            c.keyword_en, c.keyword_de)


def _cap_clay_topics(candidates: list[ThemeCandidate]) -> list[ThemeCandidate]:
    for c in candidates:
        if any(_CLAY_RE.search(f or "") for f in _hook_fields(c)):
            c.blog_score = min(c.blog_score, CLAY_SCORE_CAP)
    return candidates


def _drop_hubspot_topics(candidates: list[ThemeCandidate]) -> list[ThemeCandidate]:
    return [c for c in candidates
            if not any(_HUBSPOT_RE.search(f or "") for f in _hook_fields(c))]


# --- number provenance (Gate A, 2026-07-13) ---------------------------------
# The prompt used to demand "a NUMBER or threshold" per topic; Claude minted
# thresholds no source stated (draft 46313: "TAM unter 20.000 Accounts" from a
# post that said "20.000 EUR"). The prompt now conditions numbers on a verbatim
# evidence_quote; this filter is the deterministic backstop. It is an assertion
# on VALUES, not units -- unit fidelity is prompt-enforced here and re-checked
# against fresh research by the blogging agent's title-premise gate.

_NUM_TOKEN_RE = re.compile(r"\d[\d.,]*")
_K_SUFFIX_RE = re.compile(r"(\d[\d.,]*)\s*[kK]\b")
_CLAIM_UNIT_RE = re.compile(r"[%€$]|EUR|USD", re.IGNORECASE)
_UNIT_WINDOW = 4  # chars around a number in which a unit sign marks it a claim


def _canon(token: str) -> str:
    return token.strip(".,").replace(".", "").replace(",", "")


def _extract_claim_numbers(title: str) -> set[str]:
    """Numbers in a title that need source evidence: any value >= 1000 plus any
    value carrying a %/currency sign. Bare 4-digit years and small unit-less
    counts ("die 5 Pflichtfelder", "aus 20 Deals" - the article's own structure
    or scenario framing) are exempt."""
    claims: set[str] = set()
    for m in _NUM_TOKEN_RE.finditer(title or ""):
        token = m.group().strip(".,")
        canon = _canon(token)
        if not canon:
            continue
        if re.fullmatch(r"(19|20)\d{2}", token):
            continue  # bare calendar year (a separated "2.000" does not match)
        window = title[max(0, m.start() - _UNIT_WINDOW):m.end() + _UNIT_WINDOW]
        if int(canon) >= 1000 or _CLAIM_UNIT_RE.search(window):
            claims.add(canon)
    return claims


def _evidence_numbers(evidence: str) -> set[str]:
    nums = {_canon(m.group()) for m in _NUM_TOKEN_RE.finditer(evidence or "")}
    # "20k" in a source post backs "20.000" in a title.
    for m in _K_SUFFIX_RE.finditer(evidence or ""):
        base = _canon(m.group(1))
        if base.isdigit():
            nums.add(str(int(base) * 1000))
    return {n for n in nums if n}


def _has_unbacked_number(c: ThemeCandidate) -> bool:
    claims = _extract_claim_numbers(c.suggested_title_en) | _extract_claim_numbers(c.suggested_title_de)
    if not claims:
        return False
    return not claims <= _evidence_numbers(c.evidence_quote)


def _drop_unbacked_number_topics(candidates: list[ThemeCandidate]) -> list[ThemeCandidate]:
    kept = []
    for c in candidates:
        if _has_unbacked_number(c):
            print(
                f"  Kandidat verworfen (Titel-Zahl ohne Quellsatz): "
                f"{c.suggested_title_de or c.suggested_title_en!r} "
                f"evidence={c.evidence_quote[:120]!r}",
                flush=True,
            )
            continue
        kept.append(c)
    return kept


def filter_candidates(
    candidates: list[ThemeCandidate],
    *,
    threshold: int,
    top_n: int,
    recent_titles: list[str],
) -> list[ThemeCandidate]:
    """Drop below-threshold themes, dedup against recent titles (case-insensitive
    normalized substring either direction), sort by score desc, cap at top_n.
    HubSpot-hook themes are dropped outright; Clay-hook themes are clamped to
    CLAY_SCORE_CAP first; themes whose title numbers lack a verbatim source
    quote are dropped (number provenance)."""
    candidates = _drop_hubspot_topics(candidates)
    candidates = _drop_unbacked_number_topics(candidates)
    candidates = _cap_clay_topics(candidates)
    recent_norm = [_norm(t) for t in recent_titles if t]

    def is_dupe(c: ThemeCandidate) -> bool:
        for cand_text in (_norm(c.theme_label), _norm(c.suggested_title_en), _norm(c.suggested_title_de)):
            if len(cand_text) < MIN_MATCH_LEN:
                continue
            for r in recent_norm:
                if len(r) < MIN_MATCH_LEN:
                    continue
                if cand_text in r or r in cand_text:
                    return True
        return False

    kept = [c for c in candidates if c.blog_score >= threshold and not is_dupe(c)]
    kept.sort(key=lambda c: c.blog_score, reverse=True)
    return kept[:top_n]


def cluster_topics(posts: list[dict], recent_titles: list[str],
                   taste: dict | None = None) -> list[ThemeCandidate]:
    """One Claude call clustering posts into theme candidates. Returns [] if too
    few posts or on unparseable output. Caller applies filter_candidates()."""
    if len(posts) < MIN_POSTS:
        return []
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(posts, recent_titles, taste=taste)}],
    )
    raw = resp.content[0].text if resp.content else ""
    return _parse_clusters(raw)
