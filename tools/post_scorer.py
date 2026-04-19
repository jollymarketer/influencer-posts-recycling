"""
Post Scorer & Content Generator via Claude API.
- Bewertet Posts nach 5 Dimensionen inkl. Viralitaet (Engagement-Metriken)
- Generiert DACH-deutschen LinkedIn-Post + Bild-Prompt in einem Call
"""

import json
import math
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

JOLLY_CONTEXT = """
Jolly Marketer ist eine B2B Revenue Engine Company (Fractional CMO / GTM as a Service).

POSITIONIERUNG: Planbare B2B-Pipeline in 90 Tagen durch systematischen Outbound.

ICPs:
1. Agency Founders (11-50 MA, Marketing/PR/Digital Agenturen) - bauen Pipeline fuer Clients aber nicht fuer sich selbst
2. SaaS CEOs/Founders (10-50 MA) - haben Product-Market-Fit, kaempfen mit skalierbarem Outbound
3. B2B Manufacturers in DACH (51-200 MA) - Vertrieb ueber Messen/Netzwerk, kein strukturiertes Outbound-System

KERN-THEMEN die den ICP interessieren:
GTM-Strategie, Outbound-Systeme, Cold Email, Pipeline-Aufbau, RevOps, Sales-Marketing-Alignment,
Fractional CMO, B2B SaaS Growth, SDR/BDR Prozesse, LinkedIn fuer B2B, AI in Sales & Marketing,
ICP-Definition, Customer Success, CRM & Sales-Tech-Stack
"""

SCORING_PROMPT = """Du bist Content-Stratege bei Jolly Marketer.

KONTEXT:
{context}

Bewerte diesen LinkedIn-Post von {influencer} nach 5 inhaltlichen Kriterien (je 0-10 Punkte):

POST:
{post_text}

ENGAGEMENT-METRIKEN (bereits gemessen, nicht berechnen):
- Likes: {likes}
- Comments: {comments}
- Shares: {shares}

{diversity_section}

Bewertungskriterien:
1. topic_fit (0-10): Passt das Thema zu GTM, Outbound, RevOps, Pipeline, SaaS-Growth, Fractional CMO?
2. icp_relevanz (0-10): Wuerde Agency Founder / SaaS CEO / B2B Manufacturer diesen Inhalt wollen?
3. recyclierbarkeit (0-10): Kann man daraus einen DACH-deutschen Thought-Leadership-Post machen? (starke These, konkretes Insight)
4. einzigartigkeit (0-10): Frisches Insight oder austauschbarer Allgemeinplatz?
5. themen_diversitaet (0-10): Wie unterschiedlich ist dieses Thema von den kuerzlich geposteten Inhalten? (10 = voellig anderes Thema, 0 = fast identisches Thema wurde kuerzlich gepostet). Falls keine Recent Posts vorhanden: 8 vergeben.

Antworte NUR mit validem JSON (kein Markdown, kein Text davor/danach):
{{"topic_fit": X, "icp_relevanz": X, "recyclierbarkeit": X, "einzigartigkeit": X, "themen_diversitaet": X, "reasoning": "1-2 Saetze warum dieser Score"}}"""

DACH_POST_PROMPT = """Du bist Richard von Jolly Marketer (Fractional CMO / GTM as a Service fuer B2B).

KONTEXT:
{context}

Deine Aufgabe: Recycel den folgenden LinkedIn-Post von {influencer} in einen hochwertigen DACH-deutschen Thought-Leadership-Post.

ORIGINAL POST:
{post_text}

---

TEIL 1 - LINKEDIN POST (auf Deutsch):

Zielgruppe: CEOs und Founder von B2B SaaS, Agenturen, produzierenden Unternehmen im DACH-Raum.

Tonalitaet:
- Schreibe fuer CEOs, nicht fuer Marketer
- Keine Fachbegriffe ohne Erklaerung. Wenn ein Begriff noetig ist (z.B. ICP = Idealer Zielkunde), erklaere ihn beim ersten Mal kurz
- Natuerlich und fluessig schreiben. Variiere Satzlaengen: kurze Saetze fuer Wirkung, laengere fuer Erklaerungen und Zusammenhaenge. Kein Stakkato-Stil mit nur abgehackten Einzelsaetzen. Der Text soll sich lesen wie ein kluger Mensch, der redet, nicht wie eine Bulletpoint-Liste
- Fokus auf CEO-Relevanz: Pipeline, Umsatz, CAC, Sales-Cycle, Planbarkeit
- Keine Buzzwords, kein Marketing-Sprech
- Ich-Form (du bist der Fractional CMO aus der Praxis). Den Leser NICHT direkt ansprechen ("Du"), sondern allgemein formulieren
- Auf DACH-Marktbedingungen ummuentzen: lokale Marktdynamik, DACH-Unternehmensstrukturen
- Der Text soll hilfreich und menschlich rueberkommen, nicht wie AI-generierter Content

Inhaltliche Regeln:
- Den Original-Content erkennbar nutzen, aber als eigenstaendige Praxis-Einordnung - keine freie Neuinterpretation
- Einen eigenen, originellen Gedanken einfuegen, der im Original nicht vorkommt
- Haltung eines erfahrenen Praktikers: operative Details, Schrittfolgen, typische Stolpersteine, KPIs

Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Kontraintuitiver Befund, provokante These oder ueberraschende Zahl. Entscheidet ob jemand weiterliest.
2. Problem: Klares Spannungsfeld das die Zielgruppe kennt. Konkret, nicht abstrakt.
3. Proof/Praxis: Belege aus Beobachtung oder Mustern. Max 3-5 Schritte. Eigener Thought-Leader-Gedanke.
4. CTA: Frage in die Runde oder Einladung zur Diskussion.

Formatierung:
- Absaetze duerfen 2-4 Saetze lang sein. Nicht jeder Satz ist ein eigener Absatz. Leerzeilen nur zwischen thematischen Bloecken, nicht nach jedem Satz
- Genau EIN Formatierungselement auswaehlen:
  * Emoji-Liste (mind. 3 gleichwertige Punkte): z.B. 📍 fuer Befunde, 👉 fuer Empfehlungen
  * Nummerierte Liste mit Unicode: ➊ ➋ ➌
  * GROSSBUCHSTABEN-Label fuer einen zentralen Abschnitt
  * ASCII-Box fuer einen Merksatz: ┌─────┐ │ Merksatz │ └─────┘
- Laenge: ca. 200 Woerter, max. 3.000 Zeichen

Qualitaetspruefung (E3):
- Evidence: Jede Kernaussage belegt durch Daten oder Beobachtung?
- Executable: Sofort umsetzbar ohne grosses Marketing-Team?
- Exclusive: Mind. 1 Gedanke den man so nicht ueberall findet?

Am Ende des Posts: 4-6 relevante Hashtags (#B2BSaaS, #GTM, #RevOps, #Vertrieb, #DACH, #SaaS oder aehnlich)

---

TEIL 2 - SOUND BYTE:

Extrahiere aus dem generierten Post einen einzigen, kurzen, praegnanten Satz als Sound Byte fuer das Bild.

Regeln:
- Kein vollstaendiges Summary des Posts — kein erklaerungsbeduerftiger Satz
- Muss sofort haengen bleiben und eine Reaktion ausloesen
- Klingt wie ein starkes Zitat oder eine provokante These
- Maximal 12 Woerter
- Auf Deutsch (da der Post auf Deutsch ist)

TEIL 3 - KONTEXT (optional):

Fuer wen ist die Aussage besonders relevant? 1-2 Woerter Zielgruppe, z.B. "CEOs, RevOps-Teams" oder leer lassen.

---

OUTPUT-FORMAT (exakt einhalten):

===POST===
[LinkedIn-Post-Text auf Deutsch]

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4

===SOUNDBYTE===
[Sound Byte — ein Satz, max. 12 Woerter]

===KONTEXT===
[Zielgruppe/Kontext oder leer]"""


IMAGE_PROMPT_TEMPLATE = """Create a premium LinkedIn square image (1:1) for Jolly Marketer that communicates the core idea of the post through one clear, strategically strong visual concept.

Core message:
{core_message}

Optional context:
{context}

Language for all visible text in the image:
{language}

Objective:
Create a scroll-stopping LinkedIn featured image that is understood within 1 to 2 seconds on mobile.
The image should communicate one core idea fast and clearly, not explain an entire framework.

Brand direction:
Use the Jolly Marketer brand system flexibly.
The visual identity should feel confident, clean, structured, modern, and premium.
Use Jolly brand colors and Montserrat-style typography, but do not force one fixed layout, one fixed background color, or one recurring visual trick every time.

Jolly Marketer brand rules:

Background: Always white (#FFFFFF). No dark backgrounds, no colored backgrounds, no gradients.
Headlines: Deep Navy (#1E2A3A), ultra-bold, integrated into the composition
Accent colors: Electric Blue (#0066FF) or Bright Orange (#FF6B35) — use sparingly as accent only
Supporting neutrals: Light Grey #F4F6F8 or #EEF1F5, Mid Grey #8892A4
Do not use more than 3 colors prominently in the same composition
Keep the overall look bright, clean, and brand-consistent

Creative discipline:

Reduce the message to one dominant visual idea
Use one primary visual logic only
Prefer one focal scene, one focal metaphor, or one strong visual mechanism
Design for feed impact first, explanation second
If the concept becomes busy, simplify aggressively
Prioritize compression over completeness
The image should feel like a premium editorial social visual, not a workshop slide or business explainer

Concept selection:
First interpret the message, then choose the strongest visual direction for this specific post.
Possible directions include:

editorial poster
symbolic metaphor
clean comparison
minimal typographic concept
conceptual business illustration
Choose only one primary direction and execute it clearly.
Do not combine multiple competing concepts.

Simplicity and clarity rules:

Maximum 2 to 4 major visual elements in the whole composition
One dominant focal point, or one focal point per side only if a comparison is absolutely necessary
Remove anything that does not strengthen the idea immediately
No clutter
No filler objects
No busy scenes
No over-detailed environments
The concept must still read clearly as a small LinkedIn thumbnail

Text discipline:

Use one strong headline only
Headline must be integrated into the composition
Headline: ultra-bold, maximum 4 to 6 words
Optional support line only if truly necessary, maximum 4 to 8 words
Avoid labels, captions, side notes, repeated text, and explanatory copy by default
Every word in the image must earn its place

Typography:

Use Montserrat-style bold sans serif typography
Typography should feel compact, modern, premium, and highly legible
Avoid weak generic fonts, serif fonts, or presentation-style text layouts

Composition:

Build the image around one clear focal point
Create strong hierarchy and reading flow
Use whitespace intentionally, but do not let the image feel empty or unfinished
The composition should feel designed, not templated

Avoid:

generic stock-business visuals
bland SaaS social graphics
infographic clutter
workshop-slide aesthetics
multiple explanatory sections
too many icons or symbols
literal over-explanation
decorative clutter
chaotic comparison layouts

Final check:

Is the core idea instantly clear?
Is there only one dominant visual concept?
Is the image understandable within 1 to 2 seconds?
Is the text minimal and strong?
Is it still clear at mobile thumbnail size?
Does it feel premium and brand-consistent?

Output:
A premium LinkedIn featured image that expresses one clear strategic idea fast, cleanly, and memorably."""


def calculate_virality_score(engagement: dict) -> int:
    """
    Berechnet einen Viralitaets-Score (0-10) basierend auf Engagement-Metriken.
    Verwendet logarithmische Skalierung damit auch mittelgrosse Zahlen sinnvoll bewertet werden.
    """
    likes = engagement.get("likes", 0) or 0
    comments = engagement.get("comments", 0) or 0
    shares = engagement.get("shares", 0) or 0

    # Gewichtung: Comments und Shares sind wertvoller als Likes
    total = likes + (comments * 3) + (shares * 5)

    if total == 0:
        return 0
    # Log-Skalierung: 1000 Punkte = Score 10
    score = min(10, int(math.log10(total + 1) / math.log10(1001) * 10))
    return score


def score_posts(posts: list, recent_drafts: list[str] | None = None) -> list:
    """
    Bewertet Posts nach 6 Dimensionen: 5 inhaltliche (KI) + Viralitaet (Metriken).
    Dimension 5: Themen-Diversitaet — bevorzugt Themen die kuerzlich nicht gepostet wurden.
    Max. Score: 60 Punkte.
    """
    scored = []

    # Diversity-Kontext fuer den Prompt vorbereiten
    if recent_drafts:
        excerpts = "\n".join(f"- {d[:200]}" for d in recent_drafts)
        diversity_section = f"""KUERZLICH GEPOSTETE INHALTE (letzten 7 Posts — fuer Themen-Diversitaet):
{excerpts}

Vermeide Themen-Wiederholungen. Bevorzuge Posts die thematisch neue Perspektiven bieten."""
    else:
        diversity_section = "KUERZLICH GEPOSTETE INHALTE: Keine vorhanden."

    for post in posts:
        # Viralitaet direkt aus Engagement-Metriken
        engagement = post.get("engagement", {"likes": 0, "comments": 0, "shares": 0})
        virality_score = calculate_virality_score(engagement)

        try:
            prompt = SCORING_PROMPT.format(
                context=JOLLY_CONTEXT,
                influencer=post["influencer"],
                post_text=post["post_text"][:3000],
                likes=engagement.get("likes", 0),
                comments=engagement.get("comments", 0),
                shares=engagement.get("shares", 0),
                diversity_section=diversity_section,
            )
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            scores = json.loads(raw)
            content_total = (
                scores["topic_fit"]
                + scores["icp_relevanz"]
                + scores["recyclierbarkeit"]
                + scores["einzigartigkeit"]
                + scores.get("themen_diversitaet", 8)
            )
            total = content_total + virality_score
            scored.append({
                **post,
                "score": total,
                "score_details": {**scores, "viralitaet": virality_score},
                "reasoning": scores.get("reasoning", ""),
            })
        except Exception as e:
            print(f"  Scoring-Fehler bei {post['influencer']}: {e}")
            scored.append({
                **post,
                "score": virality_score,
                "score_details": {"viralitaet": virality_score},
                "reasoning": "KI-Scoring fehlgeschlagen, nur Viralitaet",
            })

    return sorted(scored, key=lambda x: x["score"], reverse=True)


def generate_post_and_image_prompt(post: dict) -> tuple[str, str]:
    """
    Generiert DACH-deutschen LinkedIn-Post + Sound Byte, baut dann den Bild-Prompt.
    Gibt (linkedin_post_text, image_prompt) zurueck.
    """
    prompt = DACH_POST_PROMPT.format(
        context=JOLLY_CONTEXT,
        influencer=post["influencer"],
        post_text=post["post_text"][:3000],
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()

    # Parsen: ===POST===, ===SOUNDBYTE===, ===KONTEXT===
    linkedin_draft = ""
    sound_byte = ""
    kontext = ""

    if "===POST===" in raw:
        post_part = raw.split("===POST===")[1]
        if "===SOUNDBYTE===" in post_part:
            linkedin_draft = post_part.split("===SOUNDBYTE===")[0].strip()
        else:
            linkedin_draft = post_part.strip()
    else:
        linkedin_draft = raw

    if "===SOUNDBYTE===" in raw:
        soundbyte_part = raw.split("===SOUNDBYTE===")[1]
        if "===KONTEXT===" in soundbyte_part:
            sound_byte = soundbyte_part.split("===KONTEXT===")[0].strip()
        else:
            sound_byte = soundbyte_part.strip()

    if "===KONTEXT===" in raw:
        kontext = raw.split("===KONTEXT===")[1].strip()

    # Sprache des Posts erkennen (deutsch, da DACH-Post)
    language = "German"

    # Bild-Prompt aus Template befuellen
    image_prompt = ""
    if sound_byte:
        image_prompt = IMAGE_PROMPT_TEMPLATE.format(
            core_message=sound_byte,
            context=kontext or "B2B CEOs und Founder im DACH-Raum",
            language=language,
        )

    return linkedin_draft, image_prompt
