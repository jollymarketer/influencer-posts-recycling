"""Jolly Marketer — Mandanten-Config (Default-Client).

Alle Strings sind byte-identisch zu den vormals in tools/post_scorer.py und
tools/image_archetypes.py hartkodierten Jolly-Bloecken. Bei Aenderungen an
Positionierung, Zielgruppe oder Brand hier pflegen, nicht in den Templates.
"""
import os

NAME = "jolly"

CONTEXT = """
Jolly Marketer ist eine B2B Revenue Engine Company (Fractional CMO / GTM as a Service).

POSITIONIERUNG: Planbare B2B-Pipeline in 90 Tagen durch systematischen Outbound.

ICP:
B2B SaaS und Tech-Unternehmen (5-250 MA) im deutschsprachigen Raum. Buying Personas: Founder, CEO, CRO, CSO, VP Sales, Head of Sales - Entscheider mit Product-Market-Fit, die planbaren Outbound und eine Revenue Engine brauchen, aber bisher keine interne Rolle haben, die das System denkt (nicht nur bedient).

KERN-THEMEN die den ICP interessieren:
GTM-Strategie, Outbound-Systeme, Cold Email, Pipeline-Aufbau, RevOps, Sales-Marketing-Alignment,
Fractional CMO, B2B SaaS Growth, SDR/BDR Prozesse, LinkedIn fuer B2B, AI in Sales & Marketing,
ICP-Definition, Customer Success, CRM & Sales-Tech-Stack

NICHT pushen: Clay. Jolly setzt Clay nicht mehr ein. Clay-zentrische Posts (Clay als Held/Loesung)
niedriger bewerten (topic_fit, recyclierbarkeit) und in generierten Posts nicht als Tool featuren.
Beilaeufige Erwaehnungen sind ok; grundsaetzlich tool-agnostisch bleiben.
"""

TOKENS = {
    # --- Scoring ---
    "SCORING_ROLE": "Du bist Content-Stratege bei Jolly Marketer.",
    "TOPIC_FIT_QUESTION": "Passt das Thema zu GTM, Outbound, RevOps, Pipeline, SaaS-Growth, Fractional CMO?",
    "ICP_RELEVANZ_QUESTION": "Wuerde ein Founder, CEO, CRO, CSO, VP Sales oder Head of Sales in einem B2B SaaS/Tech-Unternehmen in DACH diesen Inhalt wollen?",

    # --- DE-Post-Prompt ---
    "PERSONA_DE": "Du bist Richard von Jolly Marketer (Fractional CMO / GTM as a Service fuer B2B).",
    "AUDIENCE_DE": "Founder, CEOs, CROs, CSOs, VP Sales und Heads of Sales in B2B SaaS und Tech-Unternehmen (5-250 MA) im deutschsprachigen Raum.",
    "DECISION_MAKERS_DE": "Revenue-Entscheider (Founder, CEO, CRO, CSO, VP/Head of Sales)",
    "FOCUS_TOPICS_DE": "Revenue-Relevanz: Pipeline, Umsatz, CAC, Sales-Cycle, Planbarkeit",
    "FIRST_PERSON_ROLE_DE": "du bist der Fractional CMO aus der Praxis",
    "CONTEXT_TRANSFER_DE": "Auf den Kontext moderner B2B-SaaS/Tech-Teams in DACH uebertragen, ohne den Raum explizit zu betonen",
    "LANGUAGE_BANS_DE": """- Begriff "Mittelstand" niemals verwenden (klingt altbacken, passt nicht zum ICP)
- Das Wort "DACH" maximal EINMAL im gesamten Post - nie als Label wie "DACH-Mittelstand", "DACH-Raum", "DACH-Unternehmen"
- Kein "produzierende Unternehmen", "Industrie-", "traditionelle Firmen"
- Statt Geo-Tags: den Leser durch Problem-Sprache adressieren (Pipeline, Outbound, RevOps), nicht durch Regional-Sprache""",
    "HASHTAG_LINE_DE": "Am Ende des Posts: 4-6 relevante Hashtags (#B2BSaaS, #GTM, #RevOps, #Vertrieb, #SaaS, #Outbound, #Pipeline oder aehnlich). #DACH nur verwenden wenn thematisch zwingend.",

    # --- EN-Post-Prompt ---
    "PERSONA_EN": "You are Richard from Jolly Marketer (Fractional CMO / GTM as a Service for B2B).",
    "AUDIENCE_EN": "founders, CEOs, CROs, CSOs, VPs of Sales and Heads of Sales at B2B SaaS and tech companies (5-250 employees), international.",
    "WRITE_FOR_EN": "revenue decision-makers, not for marketers",
    "FOCUS_TOPICS_EN": "revenue relevance: pipeline, revenue, CAC, sales cycle, predictability",
    "FIRST_PERSON_ROLE_EN": "you are the fractional CMO speaking from practice",
    "HASHTAG_LINE_EN": "End the post with 4-6 relevant hashtags (#B2BSaaS, #GTM, #RevOps, #Sales, #SaaS, #Outbound, #Pipeline or similar).",

    # --- Format-Strukturen ---
    "BELIEF_ACTORS_DE": "Founder/Sales-Teams",
    "BELIEF_ACTORS_EN": "founders/sales teams",
    "SCENE_ACTOR_DE": "ein Founder oder Sales-Leader",
    "SCENE_ACTOR_EN": "a founder or sales leader",

    # --- Bild-Prompts ---
    "BRAND_NAME": "Jolly Marketer",
    "IMAGE_BRAND_DIRECTION": """Use the Jolly Marketer brand system flexibly.
The visual identity should feel confident, clean, structured, modern, and premium.
Use Jolly brand colors and Montserrat-style typography, but do not force one fixed layout, one fixed background color, or one recurring visual trick every time.""",
    "IMAGE_BRAND_RULES": """Jolly Marketer brand rules:

Background: Always white (#FFFFFF). No dark backgrounds, no colored backgrounds, no gradients.
Headlines: Deep Navy (#1E2A3A), ultra-bold, integrated into the composition
Accent colors: Electric Blue (#0066FF) or Bright Orange (#FF6B35) — use sparingly as accent only
Supporting neutrals: Light Grey #F4F6F8 or #EEF1F5, Mid Grey #8892A4
Do not use more than 3 colors prominently in the same composition
Keep the overall look bright, clean, and brand-consistent""",
    "IMAGE_TYPOGRAPHY": "Montserrat-style bold sans serif",
    "INFOGRAPHIC_BRAND_RULES": """Jolly Marketer brand rules:
- Background: always white (#FFFFFF). No dark or colored backgrounds, no gradients.
- Headings/labels: Deep Navy (#1E2A3A), bold.
- Accents (lines, the waterline, key shapes): Electric Blue (#0066FF) or Bright Orange (#FF6B35), used sparingly.
- Neutrals: Light Grey #F4F6F8 / #EEF1F5, Mid Grey #8892A4.
- Maximum 3 prominent colors. Montserrat-style bold sans-serif typography, compact and highly legible.""",
    "ARCHETYPE_BRAND_RULES": """Jolly Marketer brand rules:
- Background: white (#FFFFFF). No dark or colored backgrounds, no full-bleed gradients.
- Headline / key type: Deep Navy (#1E2A3A), ultra-bold, Montserrat-style sans-serif.
- Accent (one only): Electric Blue (#0066FF) or Bright Orange (#FF6B35), used sparingly.
- Supporting neutrals: Light Grey #F4F6F8 / #EEF1F5, Mid Grey #8892A4. Max 3 prominent colors.
- No brand, tool or company logos anywhere. No monograms, no signatures, no imprinted marks.
- Reserve a clean, empty bottom-right corner (no text, no graphic) for a logo overlay added later.
- It must read clearly at LinkedIn thumbnail size. Premium editorial feel, never a workshop slide.""",
    "DEFAULT_AUDIENCE_IMAGE": "B2B CEOs and founders",
    "DEFAULT_AUDIENCE_ARCHETYPE": "B2B founders, CEOs, revenue leaders",
}

FEATURES = {
    "supabase_persist": True,   # Rohdaten fuer das woechentliche Blog-Topic-Mining
    "keyword_scrape": True,     # Donnerstag: Keyword-Scrape fuer Jolly-Blog-Themen
    "topic_mining": True,       # Freitag: Blog-Topic-Clustering
}

NOTION_DB_ID_DEFAULT = "778bd719db9147ff994ddbf8a4ecac34"

INFLUENCERS_CSV = os.path.join(os.path.dirname(__file__), "influencers.csv")
