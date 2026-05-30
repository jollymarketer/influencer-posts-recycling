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

Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Kontraintuitiver Befund, provokante These oder ueberraschende Zahl. Entscheidet ob jemand weiterliest.
2. Problem: Klares Spannungsfeld das die Zielgruppe kennt. Konkret, nicht abstrakt.
3. Proof/Praxis: Belege aus Beobachtung oder Mustern. Max 3-5 Schritte. Eigener Thought-Leader-Gedanke.
4. Abschluss: Entweder Principle-Loop (loop zurueck zu einer groesseren universellen Wahrheit — etwas das schon bekannt ist aber es wieder wert ist zu sagen) ODER eine Frage — nur wenn sie genuines nicht-offensichtliches Interesse weckt. Kein "Was denkst du?"-Filler. Kein DM-CTA. Actionable content erzeugt Kommentare automatisch.

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
- Eisberg: one large iceberg with a clear waterline; the first layer sits above water, the deeper layers stack below in descending depth. Most important hidden layer at the bottom.
- Funnel/Pyramide: stacked horizontal bands narrowing top-to-bottom (or bottom-to-top), one layer per band.
- Vergleichstabelle: two clean columns, one header per column, aligned rows.
- Framework/Kreise: concentric or nested circles, one layer per ring.
- Horizontaler Vergleich: equal-weight blocks side by side.

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

Final check: Is the structure instantly clear? Are all German labels spelled correctly? Are there zero logos and zero title/type text? Is the bottom-right corner clear for the logo?"""


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
    Fehlt ===POST===, gilt der ganze Text als post (Fallback)."""
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

    parts = _parse_generation_response(raw)
    linkedin_draft = parts["post"]
    sound_byte = parts["soundbyte"]
    kontext = parts["kontext"]
    infographic_skeleton = parts["infografik"]

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

    return linkedin_draft, image_prompt, infographic_skeleton
