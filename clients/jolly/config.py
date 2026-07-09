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
B2B SaaS und Tech-Unternehmen (5-250 MA) im deutschsprachigen Raum sowie etablierte B2B-Unternehmen (bis ca. 50 MA, z.B. Tech-Services, Software-nahe Dienstleister, Beratungen), die seit Jahren am Markt sind, deren Neugeschaeft aus Empfehlungen, Bestandskunden oder klassischem Vertrieb kommt und denen ein planbarer digitaler Akquise-Kanal fehlt. Buying Personas: Founder, CEO, Inhaber, Geschaeftsfuehrer, CRO, CSO, VP Sales, Head of Sales - Entscheider, die planbaren Outbound und eine Revenue Engine brauchen, aber bisher keine interne Rolle haben, die das System denkt (nicht nur bedient).

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
    "TOPIC_FIT_QUESTION": "Passt das Thema zu GTM, Outbound, RevOps, Pipeline, digitaler Neukundengewinnung, SaaS-Growth, Fractional CMO?",
    "ICP_RELEVANZ_QUESTION": "Wuerde ein Founder, CEO, Inhaber, CRO, CSO, VP Sales oder Head of Sales in einem B2B-SaaS/Tech-Unternehmen oder einer etablierten B2B-Firma ohne planbaren digitalen Akquise-Kanal (DACH) diesen Inhalt wollen?",

    # --- DE-Post-Prompt ---
    "PERSONA_DE": "Du bist Richard von Jolly Marketer (Fractional CMO / GTM as a Service fuer B2B).",
    "AUDIENCE_DE": "Founder, CEOs, Inhaber, Geschaeftsfuehrer, CROs, CSOs, VP Sales und Heads of Sales in B2B SaaS und Tech-Unternehmen (5-250 MA) sowie etablierten B2B-Firmen ohne planbaren digitalen Akquise-Kanal im deutschsprachigen Raum.",
    "DECISION_MAKERS_DE": "Revenue-Entscheider (Founder, CEO, CRO, CSO, VP/Head of Sales)",
    "FOCUS_TOPICS_DE": "Revenue-Relevanz: Pipeline, Umsatz, CAC, Sales-Cycle, Planbarkeit",
    "FIRST_PERSON_ROLE_DE": "du bist der Fractional CMO aus der Praxis",
    "CONTEXT_TRANSFER_DE": "Auf den Kontext von B2B-Teams in DACH uebertragen (SaaS, Tech, etablierte Dienstleister), ohne den Raum explizit zu betonen",
    "LANGUAGE_BANS_DE": """- Begriff "Mittelstand" niemals verwenden (klingt altbacken, passt nicht zum ICP)
- Das Wort "DACH" maximal EINMAL im gesamten Post - nie als Label wie "DACH-Mittelstand", "DACH-Raum", "DACH-Unternehmen"
- Kein "produzierende Unternehmen", "Industrie-", "traditionelle Firmen"
- Statt Geo-Tags: den Leser durch Problem-Sprache adressieren (Pipeline, Outbound, RevOps), nicht durch Regional-Sprache""",
    "HASHTAG_LINE_DE": "Am Ende des Posts: 4-6 relevante Hashtags (#B2BSaaS, #GTM, #RevOps, #Vertrieb, #SaaS, #Outbound, #Pipeline oder aehnlich). #DACH nur verwenden wenn thematisch zwingend.",

    # --- EN-Post-Prompt ---
    "PERSONA_EN": "You are Richard from Jolly Marketer (Fractional CMO / GTM as a Service for B2B).",
    "AUDIENCE_EN": "founders, CEOs, owner-managers, CROs, CSOs, VPs of Sales and Heads of Sales at B2B SaaS and tech companies (5-250 employees) and established B2B firms without a predictable digital acquisition channel, international.",
    "WRITE_FOR_EN": "revenue decision-makers, not for marketers",
    "FOCUS_TOPICS_EN": "revenue relevance: pipeline, revenue, CAC, sales cycle, predictability",
    "FIRST_PERSON_ROLE_EN": "you are the fractional CMO speaking from practice",
    "HASHTAG_LINE_EN": "End the post with 4-6 relevant hashtags (#B2BSaaS, #GTM, #RevOps, #Sales, #SaaS, #Outbound, #Pipeline or similar).",

    # --- Format-Strukturen ---
    "BELIEF_ACTORS_DE": "Founder/Sales-Teams",
    "BELIEF_ACTORS_EN": "founders/sales teams",
    "SCENE_ACTOR_DE": "ein Founder oder Sales-Leader",
    "SCENE_ACTOR_EN": "a founder or sales leader",
    "COMPARISON_SUBJECT_DE": "externe GTM-Unterstuetzung (Fractional CMO, Outbound-Agentur oder interner Hire)",
    "COMPARISON_SUBJECT_EN": "external GTM support (fractional CMO, outbound agency, or an internal hire)",

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

# Daily-Kadenz (Cron Mo-Fr): 24h-Pool, max 3 Posts/Profil, Filter 6-36h.
SCRAPE = {
    "min_age_hours": 6,
    "max_age_hours": 36,
    "max_posts_per_profile": 3,
    "substack_min_age_hours": 24,
    "substack_max_age_hours": 120,
}

NOTION_DB_ID_DEFAULT = "778bd719db9147ff994ddbf8a4ecac34"

NOTION_TOKEN_ENV = "NOTION_TOKEN"
MAKE_WEBHOOK_ENV = "MAKE_REVIEW_WEBHOOK"

INFLUENCERS_CSV = os.path.join(os.path.dirname(__file__), "influencers.csv")

# --- Content-Matrix (Spec 2026-07-08) ---------------------------------------
# 9 Boxen deklariert; Boxen mit leerem Asset-Block schaltet der Whitelist-Guard
# in tools/content_matrix.py automatisch ab (aktuell: CaseProof/Magnet/Offer).
MATRIX = {
    "mix": {"Perspective": 5, "Proof": 3, "Promotion": 2},  # Soll pro 10 Posts
    "selection_floor": 2,   # mind. 2 von 10 in der Selection-Spalte
    "promotion_cap": 2,     # max. 2 von 10 in der Promotion-Zeile
    "boxes": [(job, stage)
              for job in ("Perspective", "Proof", "Promotion")
              for stage in ("Awareness", "Education", "Selection")],
}

# Nur echte, von Richard freigegebene Zahlen. Leer = CaseProof bleibt aus.
PROOF_ASSETS: list = []

# Aktuelle Angebote mit CTA-Wortlaut. Leer = Offer-Format bleibt aus.
OFFERS: list = []

# Existierende Artefakte (PDF, Checkliste, Template). Leer = Magnet bleibt aus.
LEAD_MAGNETS: list = []

# Content-Personas (v1: Generierungs-Linse + Notion-Tracking; Quota = Phase 2).
# Wortlaut-Entwurf, Freigabe Richard ausstehend.
CONTENT_PERSONAS = [
    {
        "id": "founder-gf",
        "label": "Founder, CEO, Inhaber, Geschaeftsfuehrer",
        "share": "dominant",
        "pains": "Pipeline haengt an wenigen Quellen, die er nicht steuern kann: beim jungen Unternehmen am Gruender-Netzwerk und Einzel-Deals, bei der etablierten Firma an Empfehlungen, Bestandskunden und einzelnen Verkaeufern; kein planbarer digitaler Akquise-Kanal; keine interne Rolle und kein Marketing-Team, das das GTM-System denkt",
        "kpis": "qualifizierte Meetings pro Monat, Anteil Neugeschaeft aus planbaren Kanaelen, CAC, Forecast-Genauigkeit, Zeit bis zum ersten planbaren Kanal",
        "vocabulary_use": "Planbarkeit, System, Engpass, planbarer Kanal, Empfehlungsgeschaeft, Investition vs. Wette",
        "vocabulary_avoid": "Marketing-Jargon (MQL, Attribution-Modelle), Tool-Namen als Loesung, Growth-Hacking-Sprech",
        "scene_de": "waehle pro Post genau EINE Situation: ein Founder, der nach einem starken Quartal in einen leeren Pipeline-Monat laeuft, ODER ein Geschaeftsfuehrer, dessen Neugeschaeft seit Jahren aus Empfehlungen, Bestandskunden und eigenem Vertrieb kommt und dessen Anfragen-Eingang duenn wird",
        "scene_en": "pick exactly ONE situation per post: a founder hitting an empty-pipeline month right after a strong quarter, OR an owner-CEO whose new business has come from referrals, existing accounts and his own sales team for years and whose inbound is thinning",
        "cta_style": "discovery",
    },
    {
        "id": "cro-vp-sales",
        "label": "CRO / VP Sales",
        "share": "secondary",
        "pains": "Team verfehlt Quote trotz Aktivitaet, Uebergaben zwischen Marketing und Sales reissen, Forecast auf Bauchgefuehl",
        "kpis": "Pipeline-Coverage, Conversion je Stage, Ramp-Zeit neuer Reps, Reply-to-Meeting-Rate",
        "vocabulary_use": "Coverage, Stage-Conversion, Playbook, Kadenz, Qualifizierung",
        "vocabulary_avoid": "Brand-Sprech, abstrakte Strategie-Floskeln ohne operativen Hebel",
        "scene_de": "ein VP Sales im Forecast-Call, der die Luecke zwischen Commit und Realitaet erklaeren muss",
        "scene_en": "a VP of sales in a forecast call explaining the gap between commit and reality",
        "cta_style": "discovery",
    },
]
