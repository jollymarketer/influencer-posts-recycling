"""lisocon (InTO) — Mandanten-Config.

Stimmen (Richard 2026-07-06): DE-Post = Reinhard Lindner (Gründer/CEO),
EN-Post = Jae Hyun Kim (Sales & Marketing).
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

# Kein Default: NOTION_DB_ID muss als Env gesetzt sein (eigene Lisocon-Content-DB).
NOTION_DB_ID_DEFAULT = None

# Eigene Integration "lisocon-content-engine" (nur auf die Lisocon-Content-DB berechtigt).
NOTION_TOKEN_ENV = "NOTION_TOKEN_LISOCON"
MAKE_WEBHOOK_ENV = "MAKE_REVIEW_WEBHOOK_LISOCON"

INFLUENCERS_CSV = os.path.join(os.path.dirname(__file__), "influencers.csv")
