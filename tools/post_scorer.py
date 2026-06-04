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

ICP:
B2B SaaS und Tech-Unternehmen (5-250 MA) im deutschsprachigen Raum. Buying Personas: Founder, CEO, CRO, CSO, VP Sales, Head of Sales - Entscheider mit Product-Market-Fit, die planbaren Outbound und eine Revenue Engine brauchen, aber bisher keine interne Rolle haben, die das System denkt (nicht nur bedient).

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
2. icp_relevanz (0-10): Wuerde ein Founder, CEO, CRO, CSO, VP Sales oder Head of Sales in einem B2B SaaS/Tech-Unternehmen in DACH diesen Inhalt wollen?
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

Zielgruppe: Founder, CEOs, CROs, CSOs, VP Sales und Heads of Sales in B2B SaaS und Tech-Unternehmen (5-250 MA) im deutschsprachigen Raum.

Tonalitaet:
- Schreibe fuer Revenue-Entscheider (Founder, CEO, CRO, CSO, VP/Head of Sales), nicht fuer Marketer
- Keine Fachbegriffe ohne Erklaerung. Wenn ein Begriff noetig ist (z.B. ICP = Idealer Zielkunde), erklaere ihn beim ersten Mal kurz
- Natuerlich und fluessig schreiben. Variiere Satzlaengen: kurze Saetze fuer Wirkung, laengere fuer Erklaerungen und Zusammenhaenge. Kein Stakkato-Stil mit nur abgehackten Einzelsaetzen. Der Text soll sich lesen wie ein kluger Mensch, der redet, nicht wie eine Bulletpoint-Liste
- Fokus auf Revenue-Relevanz: Pipeline, Umsatz, CAC, Sales-Cycle, Planbarkeit
- Keine Buzzwords, kein Marketing-Sprech
- Ich-Form (du bist der Fractional CMO aus der Praxis). Den Leser NICHT direkt ansprechen ("Du"), sondern allgemein formulieren
- Auf den Kontext moderner B2B-SaaS/Tech-Teams in DACH uebertragen, ohne den Raum explizit zu betonen
- Der Text soll hilfreich und menschlich rueberkommen, nicht wie AI-generierter Content

Sprach-Verbote (hart):
- Begriff "Mittelstand" niemals verwenden (klingt altbacken, passt nicht zum ICP)
- Das Wort "DACH" maximal EINMAL im gesamten Post - nie als Label wie "DACH-Mittelstand", "DACH-Raum", "DACH-Unternehmen"
- Kein "produzierende Unternehmen", "Industrie-", "traditionelle Firmen"
- Statt Geo-Tags: den Leser durch Problem-Sprache adressieren (Pipeline, Outbound, RevOps), nicht durch Regional-Sprache

Inhaltliche Regeln:
- Den Original-Content erkennbar nutzen, aber als eigenstaendige Praxis-Einordnung - keine freie Neuinterpretation
- Einen eigenen, originellen Gedanken einfuegen, der im Original nicht vorkommt
- Haltung eines erfahrenen Praktikers: operative Details, Schrittfolgen, typische Stolpersteine, KPIs

{structure_block}

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

Am Ende des Posts: 4-6 relevante Hashtags (#B2BSaaS, #GTM, #RevOps, #Vertrieb, #SaaS, #Outbound, #Pipeline oder aehnlich). #DACH nur verwenden wenn thematisch zwingend.

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

TEIL 4 - INFOGRAFIK-SKELETT:

Basierend auf dem generierten Post: Empfehle den staerksten Infografik-Typ und liefere die Keywords fuer den Canva-Aufbau.

INFOGRAFIK-TYPEN (nur einen waehlen):
- Vergleichstabelle: Zwei Spalten (z.B. "Was Leute denken" vs. "Was es wirklich ist")
- Funnel/Pyramide: 3-5 Ebenen mit Hierarchie (oben = Wichtigstes oder Ausgangspunkt)
- Eisberg: Sichtbares vs. verborgene Tiefe
- Framework/Kreise: Konzentrische oder verschachtelte Ebenen
- Horizontaler Vergleich: Nebeneinander, gleichwertig

Regeln:
- Keywords nicht Saetze (max. 3-4 Keywords pro Ebene/Spalte)
- 3-7 Elemente total, nicht mehr
- Komplementaritaet: Wenn Infografik das Problem zeigt beschreibt der Post-Text die Loesung; wenn Infografik die Struktur zeigt erklaert der Post-Text das Warum
- Tool-Logos empfehlen wenn ICP-relevante Tools im Post vorkommen (HubSpot, Smartlead, Clay, Make.com, Apollo etc.)
- Visuelle Metapher empfehlen wenn eine den Kerngedanken verstaerkt (z.B. Eisberg fuer versteckte Komplexitaet, Rubik's Cube fuer Vielschichtigkeit)

OUTPUT-FORMAT (exakt einhalten):

===POST===
[LinkedIn-Post-Text auf Deutsch]

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4

===SOUNDBYTE===
[Sound Byte — ein Satz, max. 12 Woerter]

===KONTEXT===
[Zielgruppe/Kontext oder leer]

===INFOGRAFIK===
TYP: [Typ-Name]
METAPHER: [Visuelle Metapher oder "keine"]
KOMPLEMENTARITAET: [Infografik zeigt X → Post-Text erklaert Y]
EBENEN:
[Label 1]: [Keyword 1], [Keyword 2], [Keyword 3]
[Label 2]: [Keyword 1], [Keyword 2], [Keyword 3]
[Label 3]: [Keyword 1], [Keyword 2], [Keyword 3]
TOOL-LOGOS: [Tool-Namen oder "keine"]"""

EN_POST_PROMPT = """You are Richard from Jolly Marketer (Fractional CMO / GTM as a Service for B2B).

CONTEXT:
{context}

Your task: recycle the following LinkedIn post by {influencer} into a high-quality, native English thought-leadership post. Write it natively in English — do NOT translate German phrasing or sentence structure. Same core thesis, your own added thought, but it must read like it was written in English from scratch.

ORIGINAL POST:
{post_text}

---

PART 1 - LINKEDIN POST (in English):

Audience: founders, CEOs, CROs, CSOs, VPs of Sales and Heads of Sales at B2B SaaS and tech companies (5-250 employees), international.

Tone:
- Write for revenue decision-makers, not for marketers.
- No jargon without explanation. If a term is needed (e.g. ICP = ideal customer profile), define it briefly on first use.
- Natural, fluid writing. Vary sentence length: short sentences for impact, longer ones for explanation and context. No choppy staccato of single-sentence lines. It should read like a smart person talking, not a bullet list.
- Focus on revenue relevance: pipeline, revenue, CAC, sales cycle, predictability.
- No buzzwords, no marketing-speak.
- First person (you are the fractional CMO speaking from practice). Light, natural use of "you" toward the reader is fine.
- The post should feel helpful and human, not AI-generated.

Content rules:
- Use the original content recognizably, but as your own practitioner's framing — not a free reinterpretation.
- Add one original thought that does not appear in the original.
- Stance of an experienced operator: operational detail, sequencing, common pitfalls, KPIs.

{structure_block}

Formatting:
- Paragraphs may be 2-4 sentences. Not every sentence is its own paragraph. Blank lines only between thematic blocks.
- Pick exactly ONE formatting element:
  * Emoji list (at least 3 equal items): e.g. 📍 for findings, 👉 for recommendations
  * Numbered list with Unicode: ➊ ➋ ➌
  * ALL-CAPS label for one central section
  * ASCII box for a key takeaway: ┌─────┐ │ takeaway │ └─────┘
- Length: ~200 words, max 3,000 characters.

Quality check (E3):
- Evidence: is each core claim backed by data or observation?
- Executable: immediately actionable without a big marketing team?
- Exclusive: at least one thought you would not find everywhere?

End the post with 4-6 relevant hashtags (#B2BSaaS, #GTM, #RevOps, #Sales, #SaaS, #Outbound, #Pipeline or similar).

---

PART 2 - SOUND BYTE:

Extract from the generated post a single short, sharp sound byte for the image.

Rules:
- Not a summary of the post — no sentence that needs explaining.
- Must stick instantly and provoke a reaction.
- Sounds like a strong quote or a provocative thesis.
- Maximum 12 words.
- In English (the post is in English).

PART 3 - CONTEXT (optional):

For whom is the statement most relevant? 1-2 words audience, e.g. "CEOs, RevOps teams", or leave blank.

---

PART 4 - INFOGRAPHIC SKELETON:

Based on the generated post: recommend the strongest infographic type and provide the keywords for the Canva build.

INFOGRAPHIC TYPES (choose only one):
- Comparison table: two columns (e.g. "What people think" vs. "What it really is")
- Funnel/pyramid: 3-5 levels with hierarchy (top = most important or starting point)
- Iceberg: visible vs. hidden depth
- Framework/circles: concentric or nested levels
- Horizontal comparison: side by side, equal weight

Rules:
- Keywords not sentences (max 3-4 keywords per level/column)
- 3-7 elements total, no more
- Complementarity: if the infographic shows the problem, the post text describes the solution; if the infographic shows the structure, the post text explains the why
- Recommend tool logos when ICP-relevant tools appear in the post (HubSpot, Smartlead, Clay, Make.com, Apollo etc.)
- Recommend a visual metaphor when one reinforces the core idea (e.g. iceberg for hidden complexity, Rubik's cube for many-layeredness)

OUTPUT FORMAT (follow exactly):

IMPORTANT: Reproduce the section headers (===POST===, ===SOUNDBYTE===, ===KONTEXT===, ===INFOGRAFIK===) and the field labels (TYP, METAPHER, KOMPLEMENTARITAET, EBENEN, TOOL-LOGOS) EXACTLY as written below, character for character. Do NOT translate or rename them, even though some are German — an automated parser depends on these exact strings. Only the content you fill in is in English.

===POST===
[LinkedIn post text in English]

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4

===SOUNDBYTE===
[Sound byte — one sentence, max 12 words]

===KONTEXT===
[Audience/context or blank]

===INFOGRAFIK===
TYP: [type name]
METAPHER: [visual metaphor or "none"]
KOMPLEMENTARITAET: [infographic shows X -> post text explains Y]
EBENEN:
[Label 1]: [keyword 1], [keyword 2], [keyword 3]
[Label 2]: [keyword 1], [keyword 2], [keyword 3]
[Label 3]: [keyword 1], [keyword 2], [keyword 3]
TOOL-LOGOS: [tool names or "none"]"""


FORMAT_STRUCTURES = {
    "Opinion": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Eine kontroverse These oder ein Gegen-Befund zu einer gaengigen Praxis. Entscheidet ob jemand weiterliest.
2. Spannung: Was die meisten Teams glauben oder tun - und warum das in der Praxis nicht traegt. Konkret, nicht abstrakt.
3. Position: Deine Gegenposition als erfahrener Praktiker, begruendet aus Beobachtung. Max 3-5 Belege oder Schritte. Ein eigener Gedanke der im Original nicht vorkommt.
4. Abschluss: Principle-Loop zurueck zu einer groesseren Wahrheit. Kein "Was denkst du?"-Filler, kein DM-CTA.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): a contrarian thesis or counter-finding against a common practice. Decides whether anyone reads on.
2. Tension: what most teams believe or do - and why it does not hold up in practice. Concrete, not abstract.
3. Position: your contrarian take as an experienced operator, reasoned from observation. Max 3-5 proofs or steps. One original thought not in the source.
4. Close: principle loop back to a larger truth. No "What do you think?" filler, no DM CTA.""",
    },
    "POV": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Benenne eine Denk-Linse oder ein Reframe das die Zielgruppe so noch nicht hatte. Entscheidet ob jemand weiterliest.
2. Framework: 2-4 benannte Bestandteile eines Modells, mit dem man das Problem klarer sieht. Konkret, nicht abstrakt.
3. Anwendung: Wie man die Linse in der Praxis nutzt. Max 3-5 Schritte. Ein eigener Gedanke der im Original nicht vorkommt.
4. Abschluss: Principle-Loop zurueck zu einer groesseren Wahrheit. Kein "Was denkst du?"-Filler, kein DM-CTA.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): name a lens or reframe the audience did not have yet. Decides whether anyone reads on.
2. Framework: 2-4 named parts of a model that makes the problem clearer. Concrete, not abstract.
3. Application: how to use the lens in practice. Max 3-5 steps. One original thought not in the source.
4. Close: principle loop back to a larger truth. No "What do you think?" filler, no DM CTA.""",
    },
    "Signature": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): "Was Founder/Sales-Teams glauben:" - die verbreitete Annahme, zugespitzt. Entscheidet ob jemand weiterliest.
2. Realitaet: Was tatsaechlich das Ergebnis treibt - im Kontrast zur Annahme. Konkret, nicht abstrakt.
3. Kontraste: 2-4 Glaube-gegen-Realitaet-Paare, je knapp. Ein eigener Gedanke der im Original nicht vorkommt.
4. Abschluss: Das Operating-Principle das aus den Kontrasten folgt. Kein "Was denkst du?"-Filler, kein DM-CTA.
Hinweis fuer die Infografik weiter unten: Bevorzuge die Vergleichstabelle (Glaube vs. Realitaet).""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): "What founders/sales teams believe:" - the common assumption, sharpened. Decides whether anyone reads on.
2. Reality: what actually drives the outcome, in contrast to the assumption. Concrete, not abstract.
3. Contrasts: 2-4 belief-vs-reality pairs, each tight. One original thought not in the source.
4. Close: the operating principle that follows from the contrasts. No "What do you think?" filler, no DM CTA.
Note for the infographic section below: prefer the comparison table (belief vs. reality).""",
    },
}


def _format_prompts(post: dict, post_format: str = "Opinion") -> tuple[str, str]:
    """Pure builder: returns (de_prompt, en_prompt) with the format structure
    injected. Unknown format keys fall back to Opinion. No API calls."""
    structures = FORMAT_STRUCTURES.get(post_format, FORMAT_STRUCTURES["Opinion"])
    de = DACH_POST_PROMPT.format(
        context=JOLLY_CONTEXT,
        influencer=post["influencer"],
        post_text=post["post_text"][:3000],
        structure_block=structures["de"],
    )
    en = EN_POST_PROMPT.format(
        context=JOLLY_CONTEXT,
        influencer=post["influencer"],
        post_text=post["post_text"][:3000],
        structure_block=structures["en"],
    )
    return de, en


VALID_FORMATS = ("Opinion", "POV", "Signature")

PICK_FORMAT_PROMPT = """Du waehlst das Post-Format fuer einen Recycling-Post.

Verfuegbare Formate:
- Opinion: kontroverse These gegen eine gaengige Praxis.
- POV: eine strukturierte Denk-Linse / ein Framework.
- Signature: "Glaube vs. Realitaet" - verbreitete Annahme gegen das was wirklich zaehlt.

QUELL-POST:
{post_text}

{recent_section}

Regeln:
- Waehle das Format das am besten zum Thema des Quell-Posts passt.
- Das zuletzt genutzte Format ist verboten (nie zweimal hintereinander).
- Antworte mit EINEM Wort: Opinion, POV oder Signature. Nichts sonst."""


def pick_format(post: dict, recent_formats: list[str]) -> str:
    """Waehlt Opinion/POV/Signature: bester Topic-Fit, aber nie das zuletzt
    genutzte Format. Faellt deterministisch zurueck und wirft nie."""
    most_recent = recent_formats[0] if recent_formats else None

    if recent_formats:
        recent_section = (
            f"Zuletzt genutzte Formate (neuestes zuerst): {', '.join(recent_formats)}. "
            f"VERBOTEN ist: {most_recent}."
        )
    else:
        recent_section = "Zuletzt genutzte Formate: keine."

    try:
        prompt = PICK_FORMAT_PROMPT.format(
            post_text=post["post_text"][:3000],
            recent_section=recent_section,
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        choice = response.content[0].text.strip()
        for f in VALID_FORMATS:
            if f.lower() in choice.lower() and f != most_recent:
                return f
    except Exception as e:
        print(f"  Format-Pick fehlgeschlagen, Fallback: {e}")

    # Deterministic fallback: first valid format that is not the most recent.
    for f in VALID_FORMATS:
        if f != most_recent:
            return f
    return "Opinion"


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


INFOGRAPHIC_PROMPT_TEMPLATE = """Create a premium, clean LinkedIn infographic (vertical 4:5 or square) for Jolly Marketer that renders the layers below as a single, instantly readable visual.

Layout style: {layout}
{metaphor_line}
ONLY the following layers and their keywords may appear as visible text. Render them EXACTLY as written in {language}, no translation, no extra words, no title, no type name, no meta labels:

{layers}

Objective:
A save-worthy LinkedIn infographic. The reader should grasp the structure in 2 to 3 seconds and want to save it as a reference. Structure over decoration.

Layout logic:
- Iceberg: one large iceberg with a clear waterline; the first layer sits above water, the deeper layers stack below in descending depth. Most important hidden layer at the bottom.
- Funnel/pyramid: stacked horizontal bands narrowing top-to-bottom (or bottom-to-top), one layer per band.
- Comparison table: two clean columns, one header per column, aligned rows.
- Framework/circles: concentric or nested circles, one layer per ring.
- Horizontal comparison: equal-weight blocks side by side.

Each layer shows its label as a short bold heading plus its keywords as a tight list. Keywords stay keywords, never full sentences.

Jolly Marketer brand rules:
- Background: always white (#FFFFFF). No dark or colored backgrounds, no gradients.
- Headings/labels: Deep Navy (#1E2A3A), bold.
- Accents (lines, the waterline, key shapes): Electric Blue (#0066FF) or Bright Orange (#FF6B35), used sparingly.
- Neutrals: Light Grey #F4F6F8 / #EEF1F5, Mid Grey #8892A4.
- Maximum 3 prominent colors. Montserrat-style bold sans-serif typography, compact and highly legible.

Hard rules:
- No brand, tool, or company logos anywhere in the image. No logo row, no tool chips.
- No title text, no infographic-type name (like "Eisberg" or "Funnel"), no metaphor word rendered as a label.

Composition:
- One clear vertical reading flow, strong hierarchy, generous whitespace between layers.
- Reserve clean empty space in the bottom-right corner for a logo overlay (no text or graphic there).
- It must still read clearly at LinkedIn thumbnail size.

Avoid: clutter, decorative icons that add no meaning, busy backgrounds, more than 3 colors, full sentences, tiny unreadable text, chaotic layouts.

Final check: Is the structure instantly clear? Are all {language} labels spelled correctly? Are there zero logos and zero title/type text? Is the bottom-right corner clear for the logo?"""


def build_infographic_prompt(skeleton: str, language: str = "German") -> str:
    """
    Baut aus dem strukturierten Infografik-Skelett (TYP/METAPHER/EBENEN/TOOL-LOGOS,
    erzeugt von generate_post_and_image_prompt) einen kie.ai-Bild-Prompt fuer eine
    echte gerenderte Infografik. Gibt "" zurueck wenn kein Skelett vorhanden ist.

    Nur die EBENEN werden als sichtbarer Text gerendert. TYP steuert das Layout,
    METAPHER nur die visuelle Richtung. Keine Tool-Logos, kein Titel/Typ-Name im Bild.
    """
    skeleton = (skeleton or "").strip()
    if not skeleton:
        return ""

    layout = ""
    metaphor = ""
    layers: list[str] = []
    in_ebenen = False
    for line in skeleton.splitlines():
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("TYP:"):
            layout = stripped.split(":", 1)[1].strip()
            in_ebenen = False
        elif upper.startswith("METAPHER:"):
            metaphor = stripped.split(":", 1)[1].strip()
            in_ebenen = False
        elif upper.startswith("KOMPLEMENTARIT") or upper.startswith("TOOL-LOGOS:"):
            in_ebenen = False
        elif upper.startswith("EBENEN:"):
            in_ebenen = True
        elif in_ebenen and stripped:
            layers.append(stripped)

    # Ohne Ebenen kein verlaesslicher Bild-Aufbau.
    if not layers:
        return ""

    metaphor_line = (
        f"Visual direction (do NOT render this word as text): {metaphor}" if metaphor else ""
    )
    return INFOGRAPHIC_PROMPT_TEMPLATE.format(
        layout=layout or "structured stacked layers",
        metaphor_line=metaphor_line,
        language=language,
        layers="\n".join(layers),
    )


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


def _parse_generation_response(raw: str) -> dict:
    """Zerlegt eine LLM-Antwort an den ===MARKER=== in ihre Teile.
    Gibt dict mit keys post, soundbyte, kontext, infografik zurueck.
    Fehlt ===POST===, gilt der ganze Text als post (Fallback).
    Erwartet bereits gestrippten Input (Callsites strippen die LLM-Antwort)."""
    parts = {"post": "", "soundbyte": "", "kontext": "", "infografik": ""}

    if "===POST===" in raw:
        post_part = raw.split("===POST===")[1]
        parts["post"] = (
            post_part.split("===SOUNDBYTE===")[0].strip()
            if "===SOUNDBYTE===" in post_part
            else post_part.strip()
        )
    else:
        parts["post"] = raw.strip()

    if "===SOUNDBYTE===" in raw:
        sb = raw.split("===SOUNDBYTE===")[1]
        parts["soundbyte"] = (
            sb.split("===KONTEXT===")[0].strip()
            if "===KONTEXT===" in sb
            else sb.split("===INFOGRAFIK===")[0].strip()
            if "===INFOGRAFIK===" in sb
            else sb.strip()
        )

    if "===KONTEXT===" in raw:
        kp = raw.split("===KONTEXT===")[1]
        parts["kontext"] = (
            kp.split("===INFOGRAFIK===")[0].strip()
            if "===INFOGRAFIK===" in kp
            else kp.strip()
        )

    if "===INFOGRAFIK===" in raw:
        parts["infografik"] = raw.split("===INFOGRAFIK===")[1].strip()

    return parts


def generate_post_and_image_prompt(post: dict, post_format: str = "Opinion") -> tuple[str, str, str, str]:
    """Generiert DE-Post (DACH-Prompt) + nativen EN-Post (EN-Prompt).
    Das Bild wird aus den EN-Teilen (Soundbyte + Infografik) gebaut.
    post_format waehlt den Struktur-Block (Opinion/POV/Signature).
    Gibt (de_draft, en_draft, image_prompt, infographic_skeleton) zurueck.
    """
    de_prompt, en_prompt = _format_prompts(post, post_format)

    de_resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": de_prompt}],
    )
    de_draft = _parse_generation_response(de_resp.content[0].text.strip())["post"]

    en_resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": en_prompt}],
    )
    en_parts = _parse_generation_response(en_resp.content[0].text.strip())
    en_draft = en_parts["post"]
    sound_byte = en_parts["soundbyte"]
    kontext = en_parts["kontext"]
    infographic_skeleton = en_parts["infografik"]

    image_prompt = ""
    if sound_byte:
        image_prompt = IMAGE_PROMPT_TEMPLATE.format(
            core_message=sound_byte,
            context=kontext or "B2B CEOs and founders",
            language="English",
        )

    return de_draft, en_draft, image_prompt, infographic_skeleton
