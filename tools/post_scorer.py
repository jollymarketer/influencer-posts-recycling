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

Bewerte diesen LinkedIn-Post von {influencer} nach 4 inhaltlichen Kriterien (je 0-10 Punkte):

POST:
{post_text}

ENGAGEMENT-METRIKEN (bereits gemessen, nicht berechnen):
- Likes: {likes}
- Comments: {comments}
- Shares: {shares}

Bewertungskriterien:
1. topic_fit (0-10): Passt das Thema zu GTM, Outbound, RevOps, Pipeline, SaaS-Growth, Fractional CMO?
2. icp_relevanz (0-10): Wuerde Agency Founder / SaaS CEO / B2B Manufacturer diesen Inhalt wollen?
3. recyclierbarkeit (0-10): Kann man daraus einen DACH-deutschen Thought-Leadership-Post machen? (starke These, konkretes Insight)
4. einzigartigkeit (0-10): Frisches Insight oder austauschbarer Allgemeinplatz?

Antworte NUR mit validem JSON (kein Markdown, kein Text davor/danach):
{{"topic_fit": X, "icp_relevanz": X, "recyclierbarkeit": X, "einzigartigkeit": X, "reasoning": "1-2 Saetze warum dieser Score"}}"""

DACH_POST_PROMPT = """Du bist Richard von Jolly Marketer (Fractional CMO / GTM as a Service fuer B2B).

KONTEXT:
{context}

Deine Aufgabe: Recycel den folgenden LinkedIn-Post von {influencer} in einen hochwertigen DACH-deutschen Thought-Leadership-Post PLUS einen Bild-Prompt.

ORIGINAL POST:
{post_text}

---

TEIL 1 - LINKEDIN POST (auf Deutsch):

Zielgruppe: CEOs und Founder von B2B SaaS, Agenturen, produzierenden Unternehmen im DACH-Raum.

Tonalitaet:
- Schreibe fuer CEOs, nicht fuer Marketer
- Keine Fachbegriffe ohne Erklaerung. Wenn ein Begriff noetig ist (z.B. ICP = Idealer Zielkunde), erklaere ihn beim ersten Mal kurz
- Kurze, scannbare Saetze. Konkret statt theoretisch
- Fokus auf CEO-Relevanz: Pipeline, Umsatz, CAC, Sales-Cycle, Planbarkeit
- Keine Buzzwords, kein Marketing-Sprech
- Ich-Form (du bist der Fractional CMO aus der Praxis). Den Leser NICHT direkt ansprechen ("Du"), sondern allgemein formulieren
- Auf DACH-Marktbedingungen ummuentzen: lokale Marktdynamik, DACH-Unternehmensstrukturen

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
- Weissraum ist Pflicht: Ein Gedanke pro Absatz, Leerzeile dazwischen
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

TEIL 2 - BILD-PROMPT:

Das Ziel: SCROLL-STOPP beim CEO im LinkedIn-Feed. Das Bild muss sofort eine emotionale Reaktion ausloesen.

DESIGN-VORBILD (immer anstreben):
Landscape-Format, weisser Hintergrund. LINKS: dominante Bold-Typography mit dem zentralen Keyword riesig und fett (wie ein Magazin-Cover-Titel), darunter 1-2 erklaerende Zeilen in kleinerer Schrift. RECHTS: eine reichhaltige, semi-realistische Business-Illustration mit mehreren thematisch vernetzten Icons die das Problem oder den Kontrast visuell erzaehlen. Die Icons sind NICHT flach und isoliert sondern verbunden durch Pfeile oder Bewegungslinien — sie zeigen ein System oder einen Prozess in Aktion. Stil: Editorial-Illustration wie ein B2B-Magazin-Beitrag. Kein Stock-Photo. Keine sterile Infografik.

SCROLL-STOPP REGELN:
- Das zentrale Keyword (1-3 Woerter) links nimmt 40-50% der Bildhoeehe ein — riesig, kein Kompromiss
- Die Illustration rechts zeigt aktiv einen Zustand (Chaos, Problem, Prozess) — nicht nur Symbole nebeneinander
- Zahlen oder krasse Aussagen als Subheadline links (klein, aber lesbar)
- Alles muss auf dem Handy-Thumbnail sofort verstaendlich sein

CANVAS-REGEL: Den GESAMTEN Canvas gleichmaessig nutzen. Kein Leerraum/Whitespace-Bloecke. Die Illustration rechts soll die volle Hoehe und Breite ihrer Haelfte ausfuellen. Das Keyword links soll die volle Hoehe ausschoepfen. KEIN Logo ins Bild generieren — wird separat hinzugefuegt.

Waehle den Stil anhand des Post-Inhalts:

1. Keyword + Problem-Illustration (Standardwahl)
Linke Seite: riesiges Bold-Keyword + Subheadline (These/Kontrast). Rechte Seite: vernetzte semi-realistische Illustration die das Problem zeigt — Chaos-Elemente, unterbrochene Prozesse, gestresster Business-Charakter, rote Warnsignale.
Prompt-Basis: landscape B2B editorial illustration, white background, LEFT side: oversized Montserrat ExtraBold keyword [KEYWORD] in Electric Blue #0066FF or Deep Navy #1E2A3A taking up 45% image height, below it 2 lines of medium bold text in dark grey explaining the contrast, RIGHT side: rich semi-realistic business illustration cluster with interconnected icons (funnel, warning signs, tangled arrows, stressed business person, broken chart) showing chaos or problem, connected by flow arrows, editorial magazine style, no stock photo

2. Vorher/Nachher Editorial (bei Transformation, Systemwechsel)
Zwei klar getrennte Bereiche mit semi-realistischen Szenen. Links: dunkler/muted chaotischer Zustand. Rechts: helle klare Loesung.
Prompt-Basis: landscape split editorial illustration, LEFT half muted dark grey tones showing frustrated business person surrounded by chaotic disconnected icons and broken processes, label "[PROBLEM-ZUSTAND]" in bold above, RIGHT half bright clean illustration showing organized system with confident character and connected flowing icons, label "[LOESUNG]" in Electric Blue above, bold German headline spanning top of image

3. Schock-Zahl + Kontext-Illustration (bei starken Datenpunkten)
Die Zahl dominiert links riesig. Rechts erklaert eine Illustration was diese Zahl bedeutet.
Prompt-Basis: landscape editorial, LEFT side enormous Montserrat ExtraBold number "[X%]" or "[X von Y]" in Electric Blue #0066FF taking 60% of left side height, short German shock-label below in Deep Navy bold, RIGHT side semi-realistic editorial illustration showing the real-world consequence of this statistic, business context icons, interconnected, editorial magazine style

4. Dark Poster Editorial (bei starken Meinungen, klarer Haltung)
Tiefdunkler Hintergrund, weisse riesige Headline, eine dramatische zentrale Illustration.
Prompt-Basis: Deep Navy #1E2A3A full background, centered oversized white Montserrat ExtraBold German headline spanning full width, below it one dramatic semi-realistic editorial illustration (spotlight, broken chain, target with arrow, cracked foundation) in Electric Blue and Orange tones, high contrast, poster aesthetic, editorial B2B magazine feel

JOLLY MARKETER BRAND (immer anwenden):
- Farben: Deep Navy #1E2A3A, Electric Blue #0066FF, Orange #FF6B35 — max 3 Farben pro Bild
- Orange sparsam als Akzent fuer das wichtigste Element (Pfeil, Zahl, CTA-Element)
- Typografie: Montserrat ExtraBold fuer Haupt-Keywords/Headlines, Montserrat Bold fuer Subheadlines
- KEIN Logo in den Prompt aufnehmen — das echte Jolly Marketer Logo wird automatisch per Post-Processing eingeblendet

Format: Landscape 16:9 bevorzugt (wie das Referenzbild). Alles muss auf dem Handy-Thumbnail lesbar sein.

---

OUTPUT-FORMAT (exakt einhalten):

===POST===
[LinkedIn-Post-Text auf Deutsch]

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4

===BILDPROMPT===
[Detaillierter Bildgenerierungs-Prompt]"""


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


def score_posts(posts: list) -> list:
    """
    Bewertet Posts nach 5 Dimensionen: 4 inhaltliche (KI) + Viralitaet (Metriken).
    Max. Score: 50 Punkte.
    """
    scored = []

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
            )
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
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
    Generiert DACH-deutschen LinkedIn-Post + Bild-Prompt in einem Call.
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

    # Parsen: ===POST=== und ===BILDPROMPT=== Trennzeichen
    linkedin_draft = ""
    image_prompt = ""
    if "===POST===" in raw and "===BILDPROMPT===" in raw:
        parts = raw.split("===BILDPROMPT===")
        post_part = parts[0].replace("===POST===", "").strip()
        image_part = parts[1].strip() if len(parts) > 1 else ""
        linkedin_draft = post_part
        image_prompt = image_part
    else:
        # Fallback: gesamter Output als Post-Text
        linkedin_draft = raw

    return linkedin_draft, image_prompt
