"""lisocon (InTO) — Mandanten-Config.

Stimmen (GTM-Call Jae 2026-07-09, ersetzt den DE/EN-Split vom 06.07):
100% Deutsch, kein EN-Draft mehr. Persona-Split statt Sprach-Split:
Reinhard Lindner postet Käufer/Entscheider-Posts, Jae Hyun Kim die
Anwender-Posts (beide auf Deutsch, Stimme wechselt mit der Persona).
Quellen: Full_Social_Media_Strategy_InTO.txt, playbook-lisocon.md,
InTo brand-guide_v2.json (warm-ivory premium-editorial, Montserrat+Poppins).

Harte Regeln aus dem Playbook: niemals Preise in Content (40K-Anchor nur im
Discovery-Call), InTO nie als Übersetzungstool framen, Feindbild ist der Status
quo (nie ein Wettbewerber, Across = Partner), jeder Post zahlt auf eine der 5
Content-Säulen ein, Schreibweisen InTO / lisocon strikt.

Content-Strategie-Quelle (Richard 2026-07-06): 5 Themen-Säulen + Persona-Split +
Feindbild-Leitplanke, siehe project_lisocon_content_strategy.md /
project_lisocon_into_positioning_objection_battlecard.md.
"""
import os

NAME = "lisocon"

CONTEXT = """
lisocon (lindner software & consulting GmbH, Hannover) ist ein B2B-Software-Unternehmen. Produkt: InTO — übersetzt InDesign-Dokumente direkt im Original-Layout. Kein Copy-Paste, keine DTP-Nacharbeit, kein Formatierungs-Chaos nach der Übersetzung; 99,5% Layout-Erhalt. SaaS oder On-Premise, SAP-Integration, arbeitet mit allen gängigen Translation-Management-Systemen (Trados, Across etc.).

POSITIONIERUNG (Kernbotschaft, wörtlich): "Übersetzt ist erst die Hälfte. Der teure Teil ist das Layout." InTO tritt nicht gegen DeepL/Trados/Crowdin an, sondern besitzt die Kategorie NACH der Übersetzung: Post-Translation-Layout-Automatisierung. Es eliminiert die versteckten Layout-Kosten zwischen übersetztem Text und druckfertigem Dokument. Der eigentliche Gegner ist der Status quo: Agenturen bündeln DTP-Nacharbeit unsichtbar in die Rechnung. Der Engpass ist Nachfrage/Awareness, nicht Wettbewerb: Content macht erst das Problem sichtbar ("Layout ist der teure Teil"), bevor er eine Lösung andeutet.

ICP:
Marketingleiter/MarCom-Direktoren, Lokalisierungsverantwortliche und Leiter Technische Dokumentation in produzierenden Unternehmen (500-10.000 MA), DACH und international. Typisch: Kataloge, Datenblätter und Technische Dokumentation in 10+ Sprachen, InDesign-basierte Publishing-Workflows, signifikantes Übersetzungs-/DTP-Budget.

KERN-THEMEN die den ICP interessieren:
Versteckte Lokalisierungs-/DTP-Kosten, Time-to-Market mehrsprachiger Materialien, Terminologie-Konsistenz, Translation Management, Technische Redaktion und Dokumentation, CCMS und strukturierter Content, InDesign-/Publishing-Automatisierung, AI in Übersetzung und Dokumentation, EU-Maschinenverordnung 2027, globale Content Operations, Abgrenzung der Ebenen: KI-Übersetzung (DeepL, Google, Plugins, Portale) löst Text, nicht Layout.

CONTENT-SÄULEN (jeder Post zahlt klar auf EINE dieser 5 Säulen ein; höherer Säulen-Bezug = besserer Score):
1. Versteckte Lokalisierungskosten — die teure DTP-Nacharbeit, die niemand budgetiert (Money-Säule, Persona Käufer).
2. Mehrsprachige Dokumentproduktion in der Praxis — InDesign-/DTP-/Versions-Chaos über viele Sprachen.
3. Terminologie und Qualität über Sprachen — Konsistenz, Glossare, TM; die stärkste Säule.
4. Compliance/Zukunft — EU-Maschinenverordnung 2023/1230 ab 14.01.2027, Sprachpflicht je Zielland als Deadline-Anker.
5. Einwände und Abgrenzung — "KI übersetzt doch schon", Google, DeepL-Plugin, Portale: jeder Einwand ist Steilvorlage, nicht Bedrohung. Ebenen-Trennung Text vs. Layout.
Kein Produkt-Content: InTO ist nie das Thema, höchstens die beiläufige Auflösung.

PERSONA-REGEL (zwei kollidierende Wertachsen, in EINEM Post nie mischen):
- Käufer/Entscheider (Marketing-/MarCom-Leitung, GF, Leitung Technische Dokumentation & Lokalisierung): versteckte Kosten, DTP-Nacharbeit, ROI. Marketing-Leitung ist laut Daten der einzige belegte Konverter — im Zweifel diese Achse und dieser Adressat.
- Anwender (Translation-Manager, Designer): einfache Bedienung, Browser-Lektorat ohne InDesign.
Ein Post fährt genau EINE Achse. Kosten-Argument und Easy-to-use nie im selben Post vermengen.

SOCIAL PROOF (nur diese echten Referenzen, nie neue erfinden, Zahlen exakt so): Hörmann (offiziell 69% Kostensenkung), WAGO (80% Kostenreduktion, 17 Sprachen), Stiebel Eltron (30 Sprachen).

HARTE REGELN:
- Niemals Preise, Lizenzkosten oder Budget-Größenordnungen nennen
- InTO nie als Übersetzungstool oder DeepL/Trados-Konkurrent framen
- InTO höchstens beiläufig erwähnen; Posts sind Thought Leadership, kein Produkt-Pitch
- Feindbild ist IMMER der Status quo (versteckte DTP-Kosten, manuelles Neu-Layouten, der Glaube "übersetzt = fertig"), NIE ein namentlicher Wettbewerber. Across = Partner, nie angreifen. Trados/SDL/Crowdin/DeepL/Google nur über die Ebenen-Trennung einordnen ("löst Text, nicht Layout"), nie abwerten
- Schreibweisen: "InTO" (großes I, T, O), "lisocon" (immer klein)
"""

TOKENS = {
    # --- Scoring ---
    "SCORING_ROLE": "Du bist Content-Stratege bei lisocon (Produkt: InTO, Layout-Automatisierung für mehrsprachige Dokumente).",
    "TOPIC_FIT_QUESTION": "Passt das Thema zu Lokalisierung, Übersetzung, Technischer Dokumentation, Terminologie, mehrsprachigem Content, DTP/Publishing-Workflows, CCMS oder Content Operations?",
    "ICP_RELEVANZ_QUESTION": "Würde ein Marketingleiter, Lokalisierungsverantwortlicher oder Leiter Technische Dokumentation in einem produzierenden Unternehmen (500-10.000 MA) diesen Inhalt wollen?",

    # --- DE-Post-Prompt (Stimme: Reinhard Lindner) ---
    "PERSONA_DE": "Du bist Reinhard Lindner, Gründer und Geschäftsführer von lisocon (InTO: Übersetzung von InDesign-Dokumenten direkt im Original-Layout). Du automatisierst seit über 20 Jahren Dokumentproduktion und Lokalisierungs-Workflows in der Industrie.",
    "AUDIENCE_DE": "Marketingleiter, MarCom-Direktoren, Lokalisierungsverantwortliche und Leiter Technische Dokumentation in produzierenden Unternehmen (500-10.000 MA) im deutschsprachigen Raum.",
    "DECISION_MAKERS_DE": "Entscheider in Marketing, Lokalisierung und Technischer Dokumentation (Marketingleiter, Doku-Leiter, Localization Manager)",
    "FOCUS_TOPICS_DE": "Prozess- und Kosten-Relevanz: Durchlaufzeiten, versteckte DTP-Kosten, Terminologie-Qualität, Skalierbarkeit über Sprachen",
    "FIRST_PERSON_ROLE_DE": "du bist der Praktiker, der seit Jahren mehrsprachige Dokumentproduktion in der Industrie automatisiert",
    "CONTEXT_TRANSFER_DE": "Auf den Kontext produzierender Unternehmen mit mehrsprachiger Dokumentation übertragen, ohne die Branche plakativ zu betonen",
    "LANGUAGE_BANS_DE": """- Niemals Preise, Lizenzkosten oder Budget-Größenordnungen nennen (auch keine ungefähren Zahlen)
- InTO nie als Übersetzungstool, DeepL-Alternative oder Trados-Konkurrent bezeichnen
- InTO höchstens EINMAL beiläufig erwähnen, nie als Held des Posts; kein Produkt-Pitch, kein Demo-CTA
- Schreibweisen strikt: "InTO" (großes I, T, O), "lisocon" (immer klein)""",
    "HASHTAG_LINE_DE": "Am Ende des Posts: 4-6 relevante Hashtags (#TechnischeDokumentation, #Lokalisierung, #Übersetzung, #Terminologie, #InDesign, #ContentOperations, #Maschinenbau oder ähnlich).",

    # --- EN-Post-Prompt (Stimme: Jae Hyun Kim) ---
    "PERSONA_EN": "You are Jae Hyun Kim, Sales & Marketing at lisocon (InTO: translation of InDesign documents directly in the original layout). You work daily with marketing and documentation teams at manufacturing companies drowning in multilingual DTP rework.",
    "AUDIENCE_EN": "heads of marketing, MarCom directors, localization managers and technical documentation leads at manufacturing companies (500-10,000 employees), international.",
    "WRITE_FOR_EN": "marketing, localization and documentation decision-makers, not for translators",
    "FOCUS_TOPICS_EN": "process and cost relevance: turnaround times, hidden DTP costs, terminology quality, scaling across languages",
    "FIRST_PERSON_ROLE_EN": "you speak from daily practice with multilingual document production in manufacturing",
    "HASHTAG_LINE_EN": "End the post with 4-6 relevant hashtags (#Localization, #TechnicalDocumentation, #TranslationManagement, #Terminology, #InDesign, #ContentOps or similar).",

    # --- Format-Strukturen ---
    "BELIEF_ACTORS_DE": "Marketing- und Doku-Teams",
    "BELIEF_ACTORS_EN": "marketing and documentation teams",
    "SCENE_ACTOR_DE": "ein Marketingleiter oder Doku-Verantwortlicher",
    "SCENE_ACTOR_EN": "a marketing lead or localization manager",
    "COMPARISON_SUBJECT_DE": "eine Lösung für mehrsprachige Dokumentproduktion (Agentur-DTP, interne Nacharbeit oder Automatisierung)",
    "COMPARISON_SUBJECT_EN": "a solution for multilingual document production (agency DTP, internal rework, or automation)",

    # --- Bild-Prompts (InTO Brand: warm-ivory premium-editorial, NICHT blau/weiss) ---
    "BRAND_NAME": "lisocon / InTO",
    "IMAGE_BRAND_DIRECTION": """Use the lisocon / InTO brand system flexibly.
The visual identity should feel like Adobe-like premium enterprise: restrained, precise, calm authority, editorial rather than loud.
Use the warm lisocon palette and Montserrat-style typography, but do not force one fixed layout, one fixed background color, or one recurring visual trick every time.""",
    "IMAGE_BRAND_RULES": """lisocon / InTO brand rules:

Background: Always Warm Ivory (#F4EEE3) or Paper White (#FFFCF8). No pure white, no dark backgrounds, no cold corporate blue, no gradients.
Headlines: Espresso Ink (#1A1612) or Deep Indigo (#2F4569), ultra-bold, integrated into the composition
Accent colors: Deep Indigo (#2F4569) or Saturated Teal (#3F6E6B); Warm Amber (#B57A3F) only for small highlights and key numerals — use sparingly
Supporting neutrals: Stone (#6B6058), Surface Alt (#F0E7DB)
Do not use more than 3 colors prominently in the same composition
Keep the overall look warm, calm, premium, and brand-consistent""",
    "IMAGE_TYPOGRAPHY": "Montserrat-style bold sans serif",
    "INFOGRAPHIC_BRAND_RULES": """lisocon / InTO brand rules:
- Background: always Warm Ivory (#F4EEE3). No pure white, no dark or cold-blue backgrounds, no gradients.
- Headings/labels: Espresso Ink (#1A1612) or Deep Indigo (#2F4569), bold.
- Accents (lines, key shapes): Deep Indigo (#2F4569) or Saturated Teal (#3F6E6B); Warm Amber (#B57A3F) only as a small highlight.
- Neutrals: Stone (#6B6058), Surface Alt (#F0E7DB).
- Maximum 3 prominent colors. Montserrat-style bold sans-serif typography, compact and highly legible.""",
    "ARCHETYPE_BRAND_RULES": """lisocon / InTO brand rules:
- Background: Warm Ivory (#F4EEE3) or Paper White (#FFFCF8). No pure white, no dark or cold-blue backgrounds, no full-bleed gradients.
- Headline / key type: Espresso Ink (#1A1612) or Deep Indigo (#2F4569), ultra-bold, Montserrat-style sans-serif.
- Accent (one only): Deep Indigo (#2F4569) or Saturated Teal (#3F6E6B); Warm Amber (#B57A3F) only for a small highlight or key numeral.
- Supporting neutrals: Stone (#6B6058), Surface Alt (#F0E7DB). Max 3 prominent colors.
- No brand, tool or company logos anywhere. No monograms, no signatures, no imprinted marks.
- Reserve a clean, empty bottom-right corner (no text, no graphic) for a logo overlay added later.
- It must read clearly at LinkedIn thumbnail size. Premium editorial feel, never a workshop slide.""",
    "DEFAULT_AUDIENCE_IMAGE": "marketing and documentation leaders in manufacturing",
    "DEFAULT_AUDIENCE_ARCHETYPE": "marketing, localization and documentation leaders in manufacturing",
}

FEATURES = {
    "supabase_persist": False,  # speist nur das Jolly-Blog-Topic-Mining
    "keyword_scrape": False,
    "topic_mining": False,
    "keyword_source_daily": True,  # Schritt 2b: Keyword-Suche als Daily-Quelle
    # GTM-Call Jae 2026-07-09: 100% Deutsch, kein EN-Draft; Bild-Inputs
    # (Soundbyte/Skelett) kommen aus dem DE-Response.
    "en_draft": False,
    # Grammatikpruefung als letzte Stufe der Texterstellung (Anlass:
    # Artikel-/Kasusfehler wie "Fehlender Tool Support", Reinhard 09.07).
    "grammar_check": True,
}

# GTM-Call Jae 2026-07-09: auch Bild-Texte auf Deutsch (Default: English).
IMAGE_LANGUAGE = "German"

# Persona-Split (GTM-Call Jae 2026-07-09): Reinhard postet Kaeufer/Entscheider,
# Jae die Anwender-Posts. Steuert die Notion-Property "Poster" (Make routet
# den Post auf den jeweiligen LinkedIn-Account) und den Stimm-Wechsel im
# DE-Prompt (voice_de in CONTENT_PERSONAS).
POSTER_BY_PERSONA = {"kaeufer": "Reinhard", "anwender": "Jae"}
POSTER_DEFAULT = "Reinhard"

# Poster-Balance (Richard 2026-07-10): gleich viel Content fuer Jae und
# Reinhard. Zaehlt die Poster der letzten 8 Eintraege; wer zurueckliegt,
# bekommt den naechsten Post (siehe pick_persona in tools/post_scorer.py).
PERSONA_BALANCE_WINDOW = 8

# Keyword-Suche als zusaetzliche Daily-Quelle (Richard 2026-07-06, ~4 EUR/Monat Apify):
# LinkedIn-weite Suche nach InTO-Kernthemen, konkurriert im selben Scoring-Pool wie
# die Influencer-Posts. Bewusst enge Begriffe (Doku x Mehrsprachigkeit x Layout);
# breite Begriffe wie "technical documentation" abgelehnt (zu viel Rauschen).
# posted_limit "week" = gleicher 7-Tage-Pool wie SCRAPE (Verlierer konkurrieren erneut).
DAILY_KEYWORD_SEARCH = {
    "keywords": [
        "multilingual technical documentation",
        "documentation localization",
        "DTP localization",
        "InDesign localization",
        "DITA localization",
        "CCMS",
        "Fremdsprachensatz",
        "mehrsprachige Dokumentation",
        "Redaktionssystem",
    ],
    "max_posts": 10,
    "posted_limit": "week",
}

# Kadenz (Richard 2026-07-06): 4 Winner/Woche aus einem 7-Tage-Content-Pool.
# Cron beim Scharfstellen: "0 7 * * 2-5" (Di-Fr 07:00 UTC, Montag-Skip wie Jolly).
# Verlierer werden nicht persistiert und bleiben im Pool: sie konkurrieren in den
# Folge-Laeufen erneut, nur Winner sind via Notion-URL-Dedup gesperrt.
# max_posts 5 (Richard 2026-07-06, Kosten ~7 USD/Monat statt ~13 bei 10):
# deckt die 5 neuesten Posts pro Profil im 7-Tage-Pool, Vielposter verlieren etwas Tiefe.
SCRAPE = {
    "min_age_hours": 6,
    "max_age_hours": 168,
    "max_posts_per_profile": 5,
    "substack_min_age_hours": 24,
    "substack_max_age_hours": 168,
}

# Kundenfeedback Reinhard 2026-07-08: InTO-Logo (statt Jolly) als Bild-Overlay,
# CTA-Link ganz unten in jedem Post. Wortlaut DE vom Kunden vorgegeben (Sie-Form).
LOGO_FILE = "into_logo.png"
CTA_DE = "Interessant? Besuchen Sie uns auf www.in2go.io"
CTA_EN = "Sounds interesting? Visit us at www.in2go.io"

# Kein Default: NOTION_DB_ID muss als Env gesetzt sein (eigene Lisocon-Content-DB).
NOTION_DB_ID_DEFAULT = None

# Eigene Integration "lisocon-content-engine" (nur auf die Lisocon-Content-DB berechtigt).
NOTION_TOKEN_ENV = "NOTION_TOKEN_LISOCON"
MAKE_WEBHOOK_ENV = "MAKE_REVIEW_WEBHOOK_LISOCON"

INFLUENCERS_CSV = os.path.join(os.path.dirname(__file__), "influencers.csv")

# --- Content-Matrix (Spec 2026-07-08) ---------------------------------------
# Promotion × Selection ist per Playbook AUSGESCHLOSSEN (kein Demo-CTA, kein
# Produkt-Pitch) - deklarativ, nicht nur asset-gated. Promotion × Education
# fällt automatisch weg, solange LEAD_MAGNETS leer ist.
MATRIX = {
    "mix": {"Perspective": 5, "Proof": 3, "Promotion": 2},
    "selection_floor": 2,
    "promotion_cap": 2,
    "boxes": [(job, stage)
              for job in ("Perspective", "Proof", "Promotion")
              for stage in ("Awareness", "Education", "Selection")
              if (job, stage) != ("Promotion", "Selection")],
}

# Einzige erlaubte Referenzen (Playbook), Zahlen exakt so - nie neue erfinden.
PROOF_ASSETS = [
    {"id": "hoermann", "claim": "Katalog- und Doku-Produktion automatisiert",
     "metric": "69% Kostensenkung", "context": "offizielle, freigegebene Zahl"},
    {"id": "wago", "claim": "mehrsprachige Dokumentproduktion",
     "metric": "80% Kostenreduktion bei 17 Sprachen", "context": "freigegebene Referenz"},
    {"id": "stiebel-eltron", "claim": "Dokumentproduktion über 30 Sprachen",
     "metric": "30 Sprachen im Einsatz", "context": "freigegebene Referenz"},
]

OFFERS: list = []        # bewusst leer: kein Offer-Content für lisocon
LEAD_MAGNETS: list = []  # keine Lead Magnets gebaut -> Magnet-Format aus

# Aus der PERSONA-REGEL im CONTEXT strukturiert: genau EINE Achse pro Post.
CONTENT_PERSONAS = [
    {
        "id": "kaeufer",
        "label": "Käufer/Entscheider (Marketing-/MarCom-/Doku-Leitung)",
        "share": "dominant",
        "pains": "versteckte DTP-Nacharbeit sprengt Budget und Timeline, niemand budgetiert die Layout-Kosten nach der Übersetzung",
        "kpis": "Kosten pro Sprachversion, Time-to-Market mehrsprachiger Materialien, Reklamationen wegen Layout-Fehlern",
        "vocabulary_use": "versteckte Kosten, Durchlaufzeit, ROI, Prozesskette, druckfertig",
        "vocabulary_avoid": "Toolbedienung, Feature-Details, Übersetzungsqualität als Thema",
        "scene_de": "ein Marketingleiter, der die Agentur-Rechnung liest und die DTP-Position zum ersten Mal hinterfragt",
        "scene_en": "a head of marketing reading the agency invoice and questioning the DTP line item for the first time",
        "cta_style": "reply",
    },
    {
        "id": "anwender",
        "label": "Anwender (Translation-Manager, Designer)",
        "share": "secondary",
        "pains": "Copy-Paste-Korrekturen in InDesign über Dutzende Sprachversionen, Versionschaos zwischen Übersetzern und Layout",
        "kpis": "Korrekturschleifen pro Dokument, Stunden Nacharbeit pro Sprache, Fehler nach Freigabe",
        "vocabulary_use": "Korrekturlauf, Lektorat im Browser, Versionen, Layout-Erhalt",
        "vocabulary_avoid": "Budget- und ROI-Argumente (Käufer-Achse), Preise",
        "scene_de": "eine Designerin, die zum dritten Mal denselben Umbruch in zwölf Sprachversionen fixt",
        "scene_en": "a designer fixing the same line break in twelve language versions for the third time",
        "cta_style": "reply",
        # Anwender-Posts postet Jae — der DE-Prompt wechselt auf seine Stimme.
        "voice_de": "Du bist Jae Hyun Kim, Sales & Marketing bei lisocon (InTO: Übersetzung von InDesign-Dokumenten direkt im Original-Layout). Du arbeitest täglich mit Marketing-, Übersetzungs- und Doku-Teams, die in mehrsprachiger DTP-Nacharbeit versinken.",
    },
]
