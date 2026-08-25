"""SWOT Controlling: Mandanten-Config, vorerst NUR fuer den Kommentar-Pfad.

Umfang bewusst schmal. Die Entscheidung vom 29.07.2026 (Memory
`project_swot_content_research_quellen`) stuft den Influencer-Recycling-Pfad
fuer SWOT auf Rang 5 von 5 herunter: in Controlling und Rechnungswesen gibt es
auf DACH-LinkedIn keine 80 lauten Creator, die Viralitaets-Dimension wuerde
Vendor-Marketing nach oben spuelen, und der Score-Floor 25/60 wuerde in der
stillen Nische regelmaessig reissen. Deshalb ist hier KEIN Slate- und kein
Winner-Pfad konfiguriert.

Was hier laeuft, ist `tools/comment_drafts.py`: Posts der Quellen unten ziehen
und Kommentar-Entwuerfe fuer Christian schreiben. Das ist ein anderer Zweck als
Recycling. Es sucht keinen Gewinner-Post zum Nachbauen, sondern einen frischen
Post, unter dem SWOT sichtbar wird. Die Einwaende gegen Rang 5 treffen es nicht.

Die Quellenliste war bis 13.08.2026 anders zusammengesetzt als bei lisocon:
keine Fach-Creator, sondern Wettbewerber-Seiten plus Fachverbaende. Begruendung
war Rang 4 derselben Notiz, "Beschwerde-Posts und Kommentare unter Vendor-Posts
sind Themen-Gold": unter einem LucaNet-Post liest SWOTs Zielgruppe mit.

AUFGEHOBEN durch SWOT am 13.08.2026 (Notion-Kommentar an der Task "Namen fuer
die Kommentar-Ziele nennen",
https://app.notion.com/p/3ba1617b1baf811fb8ccf49fb0de64e7): "wir sollten nicht
bei Jedox, Corporate Planning, Lucanet, Agicap, Tidely posten - sonst pushen wir
ja deren Content." Vorlaeufer war die muendliche Auflage aus dem GTM-Call vom
12.08.2026, unter der bereits vier Entwuerfe verworfen wurden.

GESPERRTE ZIELE, nicht in influencers.csv aufnehmen: LucaNet, Jedox, CP
Corporate Planning, Agicap, Tidely, dazu die gleich gelagerten CPM-Wettbewerber
IDL (insightsoftware) und Unit4/prevero. Die Sperre gilt fuer jeden Anbieter
konkurrierender Planungs-, Konsolidierungs- oder Liquiditaetssoftware, auch
wenn er hier nicht namentlich steht.

Uebrig bleiben zwei Fachverbands-Quellen. Das traegt den Kommentar-Pfad nicht:
schon mit sieben Quellen lieferte ein 72-Stunden-Fenster genau 1 brauchbaren
Post. Bis SWOT die angefragte Namensliste liefert (selbstaendige Berater und
Beraterinnen, denen sie folgen), ist der Pfad faktisch ausgesetzt.

Posten bleibt manuell. Ein Kommentar unter fremdem Namen laeuft nie
automatisiert.
"""
import os

NAME = "swot"

CONTEXT = """
SWOT Controlling GmbH, Berlin. Software fuer Corporate Performance Management
im deutschsprachigen Raum: Konsolidierung, Finanz- und Personalkostenplanung,
Liquiditaetsplanung, Reporting.

Zielgruppe: Controlling und Rechnungswesen im Mittelstand, mit einer eigenen
Vertikale in der Sozialwirtschaft (diakonische und caritative Traeger,
Pflegeeinrichtungen). Ansprechpartner sind Kaufmaennische Leitung,
Controlling-Leitung und Geschaeftsfuehrung.

Marktlage: der DACH-CPM-Markt konsolidiert. prevero ging an Unit4, IDL an
insightsoftware, cubus an Serviceware, Corporate Planning an proALPHA. SWOT ist
einer der wenigen verbliebenen eigenstaendigen Anbieter. Bestandskunden der
uebernommenen Anbieter sind haeufig wechselwillig.

Fachliche Anker mit Fristwirkung: AVR.DD Entgelterhoehung zum 01.09.2026, AVR
Caritas Neufassung zum 01.01.2027, IFRS 18 ab Geschaeftsjahr 2027 mit bereits
laufendem Vergleichsjahr 2026, E-Rechnung: Empfangspflicht seit 01.01.2025,
Versandpflicht ab 01.01.2027 (nie als Empfangspflicht 2027 schreiben). CSRD ist
ausdruecklich KEIN Thema: das Omnibus-I-Paket hat die Schwelle auf ueber 1.000
Beschaeftigte angehoben, SWOTs Mittelstands-Zielgruppe faellt heraus.

Belegmaterial: 52 Anwenderberichte, davon 43 online, 8 aus der Sozialwirtschaft.
""".strip()

# Seit 19.08.2026 vier Konten statt einem (Entscheidung Richard). Die Personas
# stehen weiter unten in CONTENT_PERSONAS. Die TOKENS-Werte fuer AUDIENCE_DE,
# DECISION_MAKERS_DE und FOCUS_TOPICS_DE bleiben der Fallback, den eine Persona
# ueberschreiben darf (siehe post_scorer.persona_prompt_tokens).
TOKENS = {
    # Stimme auf Robert Werner umgestellt (GTM-Call 29.07.2026: Posts und
    # Kommentare laufen ueber Roberts Account, Monat 1 ausschliesslich
    # Berater-Content; Umstellung ausgefuehrt 12.08.2026).
    "PERSONA_DE": (
        "Du bist Robert Werner, Leiter Vertrieb und Akademie der SWOT "
        "Controlling GmbH in Berlin. Du sprichst taeglich mit "
        "Beratungsgesellschaften, Steuerberatern und Wirtschaftspruefern, die "
        "Planung, Konsolidierung und Liquiditaet fuer ihre Mandate aufbauen. "
        "Du sprichst aus der Praxis, nicht aus der Produktbroschuere."
    ),

    # --- Scoring (Freigabe Richard 2026-08-19) -------------------------------
    "SCORING_ROLE": (
        "Du bist Content-Stratege bei SWOT Controlling (Software fuer "
        "Konsolidierung, integrierte Finanz- und Personalkostenplanung, "
        "Liquiditaetsplanung und Reporting im deutschsprachigen Mittelstand)."
    ),
    "TOPIC_FIT_QUESTION": (
        "Passt das Thema zu Konsolidierung, integrierter Planung ueber GuV, "
        "Bilanz und Liquiditaet, Personalkostenplanung, Forecast, Reporting, "
        "Kostenstellenrechnung oder Schnittstellen zu DATEV und ERP? Bonus, "
        "wenn es einen im KONTEXT belegten Schmerz trifft: Excel-Modelle, die "
        "niemand uebergeben kann, Daten, die zwischen zwei Systemen haengen "
        "bleiben, ein Planungsmodell, das nur eine Person versteht, oder eine "
        "datierte Frist (IFRS 18, E-Rechnung, AVR)."
    ),
    "ICP_RELEVANZ_QUESTION": (
        "Wuerde eine kaufmaennische Leitung, eine Controlling-Leitung oder "
        "eine Geschaeftsfuehrung im deutschsprachigen Mittelstand diesen "
        "Inhalt wollen, oder ein Steuerberater, Wirtschaftspruefer oder "
        "Unternehmensberater mit Planungsmandaten?"
    ),

    # --- Zielgruppe und Ton (Fallback, Personas duerfen ueberschreiben) ------
    "AUDIENCE_DE": (
        "Kaufmaennische Leitung, Controlling-Leitung und Geschaeftsfuehrung im "
        "deutschsprachigen Mittelstand, dazu Steuerberater, Wirtschaftspruefer "
        "und Unternehmensberater mit Planungsmandaten. Eigene Vertikale: "
        "diakonische und caritative Traeger und Pflegeeinrichtungen."
    ),
    "DECISION_MAKERS_DE": (
        "Kaufmaennische Leitung, Controlling-Leitung und Geschaeftsfuehrung, "
        "bei Beratungsgesellschaften die Partner und Mandatsverantwortlichen"
    ),
    "FOCUS_TOPICS_DE": (
        "Belastbarkeit der Zahlen: Datenherkunft und Schnittstellen, "
        "integrierte Planung ueber GuV, Bilanz und Liquiditaet, "
        "Forecast-Genauigkeit, Uebergabefaehigkeit des Modells, datierte Fristen"
    ),
    # Perspektive (Kulle, Notion-Kommentare 24.08.2026): SWOT ist
    # Softwarehersteller, kein Interim-CFO. "Wir sitzen als Softwarehersteller
    # nicht im Bankgespraech dabei. Wir unterstuetzen lediglich das Zahlenwerk
    # aufzubereiten." Erzaehlposition ist der Blick auf Kundenprojekte,
    # Einfuehrungen und Schulungen, nie der Stuhl am Verhandlungstisch.
    "FIRST_PERSON_ROLE_DE": (
        "du begleitest seit Jahren Einfuehrungen von Planungs- und "
        "Konsolidierungssoftware im Mittelstand und in der Sozialwirtschaft "
        "und siehst, wie Kunden ihr Zahlenwerk fuer Bank, Gesellschafter oder "
        "Pruefer aufbereiten"
    ),
    "CONTEXT_TRANSFER_DE": (
        "Auf den Alltag von Controlling und Rechnungswesen im Mittelstand "
        "uebertragen, ohne die Branche plakativ zu betonen. Gesetze, Normen "
        "und Tarifwerke (StaRUG, IFRS 18, AVR, InsO) beim ersten Auftreten in "
        "einem Halbsatz einordnen: was es ist und seit wann es gilt. Fuer "
        "Leser schreiben, die nicht taeglich auf LinkedIn sind: ein Gedanke je "
        "Absatz, kein Fachwort ohne Erklaerung"
    ),
    "BELIEF_ACTORS_DE": "Controlling- und Rechnungswesen-Teams",
    "COMPARISON_SUBJECT_DE": (
        "ein Weg zur Planung (gewachsene Excel-Modelle, ein Modul des "
        "Vorsystems oder eine eigenstaendige Planungssoftware)"
    ),
    "SCENE_ACTOR_DE": (
        "eine kaufmaennische Leitung oder ein Berater mit Planungsmandaten"
    ),
    "HASHTAG_LINE_DE": (
        "Keine Hashtags verwenden. Der Post endet mit dem letzten "
        "Inhalts-Satz."
    ),

    # Sperrliste. Die Wettbewerber-Sperre stammt von Christian Kulle
    # (Notion-Kommentar 13.08.2026) und ist von uns auf IDL und Unit4 mit
    # prevero ausgeweitet worden.
    "LANGUAGE_BANS_DE": """- Niemals Preise, Lizenzkosten oder Budget-Groessenordnungen nennen (auch keine ungefaehren Zahlen und keine Spannen)
- Keine Wettbewerbernamen: Jedox, Corporate Planning, LucaNet, Agicap, Tidely, IDL, Unit4 mit prevero, cubus. Gilt fuer jeden Anbieter konkurrierender Planungs-, Konsolidierungs- oder Liquiditaetssoftware. Ausnahmen nur, wenn sie fuer einen einzelnen Beitrag ausdruecklich freigegeben sind
- Niemals auf fremde Beitraege verlinken oder daraus zitieren. Aufgegriffen wird das Thema, nie der fremde Text
- SWOT nie als BI-Tool, Reporting-Tool oder DATEV-Ersatz bezeichnen
- CSRD ist kein Thema: das Omnibus-I-Paket hat die Schwelle angehoben, die Zielgruppe faellt heraus
- Kein Em-Dash. Echte Umlaute schreiben
- Keine erfundenen Zahlen. Belegt sind ausschliesslich die Angaben aus dem KONTEXT
- Nie in der Ich- oder Wir-Form als Teilnehmer eines Bankgespraechs, Gerichtstermins, einer Gesellschafterrunde oder eines Gremiums schreiben. SWOT ist Softwarehersteller, kein Interim-CFO und kein Berater am Tisch. Erlaubt ist die Beobachterposition: "in Einfuehrungsprojekten sehe ich", "Kunden berichten", "in der Schulung zeigt sich"
- "Glaube" ist kein Fachwort: es heisst Annahme, Hypothese oder Praemisse""",

    # --- Englisch: SWOT ist DACH-only (FEATURES["en_draft"] = False). Die
    # Tokens muessen trotzdem existieren, weil apply_tokens beim Import auch
    # ueber EN_POST_PROMPT laeuft und bei jedem offenen Marker abbricht.
    "PERSONA_EN": (
        "You are Robert Werner, head of sales and academy at SWOT Controlling "
        "GmbH in Berlin. You speak daily with consultancies, tax advisors and "
        "auditors who build planning, consolidation and liquidity models for "
        "their clients."
    ),
    "AUDIENCE_EN": (
        "finance directors, heads of controlling and managing directors at "
        "German-speaking mid-market companies, plus tax advisors, auditors and "
        "consultants with planning mandates."
    ),
    "WRITE_FOR_EN": (
        "finance and controlling decision-makers, not for IT or for marketers"
    ),
    "FOCUS_TOPICS_EN": (
        "reliability of the numbers: data lineage and interfaces, integrated "
        "planning across P&L, balance sheet and liquidity, forecast accuracy, "
        "handover of the model, dated deadlines"
    ),
    "FIRST_PERSON_ROLE_EN": (
        "you speak from years of planning and consolidation projects in the "
        "mid-market and in the social economy"
    ),
    "BELIEF_ACTORS_EN": "controlling and accounting teams",
    "COMPARISON_SUBJECT_EN": (
        "a way to plan (grown spreadsheet models, a module of the source "
        "system, or dedicated planning software)"
    ),
    "SCENE_ACTOR_EN": "a finance director or a consultant with planning mandates",
    "HASHTAG_LINE_EN": (
        "No hashtags. The post ends with the last content sentence."
    ),

    # --- Bild-Prompts (Freigabe Richard 2026-08-12) --------------------------
    # Farbwelt direkt von swot.de abgeleitet (Logo-Pixel + Site-CSS, 12.08.2026):
    # SWOT-Gelb #FCC100, Navy #182047, Anthrazit #202020, Weiss; Font Roboto.
    "BRAND_NAME": "SWOT Controlling",
    "IMAGE_BRAND_DIRECTION": """Use the SWOT Controlling brand system flexibly.
The visual identity should feel like precise, calm finance-software authority:
clear, structured, editorial rather than loud. Think controlling, planning and
consolidation: numbers, structure, clarity. Use the SWOT palette and
Roboto-style typography, but do not force one fixed layout, one fixed
background color, or one recurring visual trick every time.""",
    "IMAGE_BRAND_RULES": """SWOT Controlling brand rules:

Background: White (#FFFFFF) or very light cool grey (#F5F6F8); a deep navy
(#182047) background is allowed for dark compositions. No gradients, no
generic corporate light-blue.
Headlines: Anthracite (#202020) or Navy (#182047) on light backgrounds,
White on navy backgrounds, ultra-bold, integrated into the composition.
Accent color: SWOT Yellow (#FCC100) as THE signature accent, used for key
numerals, one highlight element or one accent shape. Use deliberately, never
flood the image with yellow.
Supporting neutrals: mid grey (#6B7280), light grey (#E5E7EB).
Do not use more than 3 colors prominently in the same composition.
No brand, tool or company logos anywhere in the image - not SWOT's own and no
third party's (e.g. DATEV, Microsoft, LucaNet). Third parties may appear only
as plain words inside the headline text, never as a rendered logo, wordmark or
branded object in the scene. No monograms, signatures or imprinted marks.
Reserve a clean, empty bottom-right corner (no text, no graphic) for a logo
overlay added later.
Keep the overall look clear, structured, premium, and brand-consistent.""",
    "IMAGE_TYPOGRAPHY": "Roboto-style modern grotesque sans serif",
    "DEFAULT_AUDIENCE_IMAGE": "consultants, tax advisors and controlling leads in German-speaking mid-market firms",
    "DEFAULT_AUDIENCE_ARCHETYPE": "finance directors, heads of controlling and consultants with planning mandates",

    # Topic-Mining-Rolle (Seed-Lauf 19.08.2026, dort noch per Monkeypatch).
    # Achsen-Definitionen konsistent zu CONTENT_PERSONAS halten.
    "TOPIC_CLUSTER_ROLE": (
        "You are a B2B content strategist for SWOT Controlling GmbH (Berlin), a "
        "DACH vendor of corporate performance management software: consolidation, "
        "integrated financial and personnel cost planning, liquidity planning, "
        "reporting. You cluster German LinkedIn posts into LINKEDIN CONTENT topic "
        "themes for SWOT's audience: the person responsible for the numbers in a "
        "German-speaking mid-market company (managing director doing the numbers "
        "on the side, the single in-house controller, or an external interim "
        "CFO / restructuring advisor / tax advisor with planning mandates). "
        "Score each theme's potential for LinkedIn thought-leadership posts. "
        "Five content axes qualify a theme: a grown Excel model at its limit; "
        "many units (companies, sites, mandates) needing one procedure; where "
        "the numbers come from (interfaces, source systems, data ownership); "
        "accountability to outsiders (bank, shareholders, boards, auditors, "
        "cost carriers); dated deadlines (IFRS 18, e-invoicing, AVR). Themes "
        "about competing planning-software vendors (Jedox, LucaNet, Corporate "
        "Planning, Agicap, Tidely, IDL, prevero, cubus) must NOT become themes "
        "about those vendors; reframe to the underlying situation or score low."
    ),

    # Mining-Brief (20.08.2026): LinkedIn-Post-Themen, KEINE Blog-SEO-Fragen.
    # Bis dahin lief SWOTs Mining durch den fest verdrahteten Jolly-Brief
    # ("blog-post topics for jollymarketer.com" samt Smartlead/GTM-Beispielen).
    "TOPIC_MINING_BRIEF": (
        "Extract 8-15 SPECIFIC German-language LinkedIn POST topics for SWOT's "
        "audience. This is NOT blog SEO: no search-query phrasing, no 'Wie "
        "viele X...?' Google questions. Each topic is ONE concrete situation "
        "from the working life of the person responsible for the numbers - the "
        "kind of moment a reader recognizes from last week.\n"
        "Anchor every topic in at least one concrete specific: a named source "
        "system (DATEV, ERP, Excel), a named counterpart (Bank, Gesellschafter, "
        "Wirtschaftspruefer, Kostentraeger), a role (Interim-CFO, Steuerberater "
        "mit Planungsmandat, der einzige Controller im Haus), a dated deadline "
        "(IFRS 18, E-Rechnung, AVR) - or a NUMBER, but ONLY if one of the posts "
        "above states that exact number with the same unit and meaning. NEVER "
        "invent a number. A topic with no source-backed number simply uses a "
        "non-numeric anchor.\n"
        "Good shape: 'Das Excel-Modell rechnet noch, aber der Erbauer geht in "
        "Rente: was eine Uebergabe wirklich braucht'. Bad shape: 'Excel vs. "
        "Planungssoftware: der grosse Vergleich' (generic head term) or "
        "'Warum LucaNet-Kunden wechseln' (vendor hook).\n"
        "EXCLUDE topics whose hero is a competing planning-software vendor "
        "(Jedox, LucaNet, Corporate Planning, Agicap, Tidely, IDL, prevero, "
        "cubus): reframe to the underlying situation or drop the topic. "
        "EXCLUDE CSRD (audience falls outside Omnibus-I threshold). EXCLUDE "
        "prices and licence costs.\n"
        "suggested_title_de is the primary field and must be German; "
        "suggested_title_en is its English translation, and it must not be "
        "longer than the German original."
    ),
    "ARCHETYPE_BRAND_RULES": """SWOT Controlling brand rules:
- Background: White (#FFFFFF) or very light cool grey (#F5F6F8); deep navy
  (#182047) allowed for dark compositions. No gradients, no generic corporate
  light-blue.
- Headline / key type: Anthracite (#202020) or Navy (#182047) on light
  backgrounds, White on navy, ultra-bold, Roboto-style grotesque sans-serif.
- Accent (one only): SWOT Yellow (#FCC100), used for a key numeral, one
  highlight element or one accent shape. Never flood the image with yellow.
- Supporting neutrals: mid grey (#6B7280), light grey (#E5E7EB). Max 3
  prominent colors.
- No brand, tool or company logos anywhere, neither SWOT's own nor third
  parties'. No monograms, no signatures, no imprinted marks. Third-party names
  may appear as plain words inside headline text only.
- Reserve a clean, empty bottom-right corner for a logo overlay added later.""",
    "INFOGRAPHIC_BRAND_RULES": """SWOT Controlling brand rules for diagrams and infographics:
- Background: White (#FFFFFF) or very light cool grey (#F5F6F8). No gradients.
- Labels and headings: Anthracite (#202020) or Navy (#182047), bold.
- Structural elements (lines, boxes, arrows): Navy (#182047); mid grey
  (#6B7280) for secondary structure.
- Accent: SWOT Yellow (#FCC100) for the one element the reader should look at
  first. Never more than one accent per diagram.
- At most 3 colors prominently in the same composition.
- No logos of any kind, neither SWOT's own nor third parties'. Third-party
  names may appear as plain label text only.
- Numbers and axis labels must stay legible at LinkedIn feed size.""",
}

# Content-Achsen (Entscheidung Richard 19.08.2026). Die Achse ist eine
# SITUATION, ueber die ein Beitrag handelt, nicht eine Person. Rollen sind
# Auspraegungen der Persona, nie eine eigene Achse: sonst liegt derselbe Fund
# in mehreren Achsen und die Einsortierung ist nicht mehr eindeutig.
#
# Abgeleitet aus allen 52 Anwenderberichten, also branchenuebergreifend, nicht
# aus den zwei Kampagnen-Playbooks. Gemessene Anteile stehen je Achse dabei.
# Die frueheren vier Personas nach Absender (Kulle, Werner, Baumert,
# Unternehmensseite) sind ersetzt: die Achse bestimmt die Persona, die Persona
# bestimmt das Konto, nicht umgekehrt. Kontozuordnung in AXIS_TO_ACCOUNT.
#
# ALLGEMEINE CONTENT-PERSONA, drei Auspraegungen:
#   1. der Chef, der die Zahlen nebenbei macht (in 22 von 52 Berichten die
#      zitierte Rolle) und Entlastung sucht
#   2. der eine Controller oder die kaufmaennische Leitung im Haus, sucht
#      Handwerk
#   3. der externe Zahlenverantwortliche: Interim-CFO, Restrukturierer,
#      Steuerberater mit Planungsmandat. Auf LinkedIn die aktivste Gruppe
#      (Messung 19.08.: von 31 rollenpassenden Autoren 6 Interim- oder externe
#      Finanzleitungen, 4 Restrukturierer, 4 Controller, 4 Steuerberater)
CONTENT_PERSONAS = [
    {
        "id": "excel_am_limit",
        "label": "Excel am Limit",
        "share": "dominant",   # 46 von 52 Anwenderberichten
        "axis": ("Das gewachsene Tabellenmodell traegt die Aufgabe nicht mehr. "
                 "Es rechnet noch, aber niemand kann es uebergeben, pruefen "
                 "oder erweitern"),
        "audience_de": ("Wer im Haus fuer die Zahlen geradesteht: "
                        "Geschaeftsfuehrung im Mittelstand, die eine "
                        "Controlling-Stelle, kaufmaennische Leitung. Dazu "
                        "externe Zahlenverantwortliche mit Planungsmandat."),
        "decision_makers_de": ("Geschaeftsfuehrung und kaufmaennische Leitung, "
                               "bei Beratungen die Mandatsverantwortlichen"),
        "focus_topics_de": ("Uebergabefaehigkeit und Pruefbarkeit eines "
                            "Planungsmodells, Trennung von Annahme und "
                            "Rechenlogik, Versionen"),
        "pains": ("ein Modell, das an einer Person haengt; Zellen, deren Grund "
                  "niemand mehr kennt; ein Nachfolger, der neu baut statt zu "
                  "uebernehmen"),
        "kpis": ("Zeit bis ein Dritter das Modell aktualisieren kann, "
                 "Nacharbeit nach einem Wechsel"),
        "vocabulary_use": ("Modell, Annahme, Rechenlogik, Version, Uebergabe, "
                           "nachvollziehbar, Excel"),
        "vocabulary_avoid": ("Excel-Schelte, Formeltricks, Toolvergleiche, "
                             "Feature-Listen"),
        "scene_de": ("jemand, der eine uebernommene Datei zum ersten Mal "
                     "oeffnet und die Verknuepfungen nicht versteht"),
        "scene_en": ("someone opening an inherited spreadsheet for the first "
                     "time and not understanding the links"),
        "cta_style": "reply",
    },
    {
        "id": "viele_einheiten",
        "label": "Viele Einheiten, ein Verfahren",
        "share": "secondary",   # 37 von 52 Anwenderberichten
        "axis": ("Mehrere Gesellschaften, Standorte oder Mandate muessen nach "
                 "demselben Verfahren gerechnet werden. Nutzen ist die "
                 "konsolidierte Zahl und, beim externen "
                 "Zahlenverantwortlichen, dass der zweite Fall billiger wird "
                 "als der erste"),
        "audience_de": ("Verantwortliche in Haeusern mit mehr als einer "
                        "Einheit: Gesellschaften, Standorte, Spartenrechnung. "
                        "Dazu Beratungen, die dasselbe Verfahren ueber mehrere "
                        "Mandate fahren."),
        "decision_makers_de": ("Geschaeftsfuehrung, Leitung Rechnungswesen, "
                               "Konsolidierungsverantwortliche, bei Beratungen "
                               "Partner und Mandatsleitung"),
        "focus_topics_de": ("Konsolidierung ueber Rechtstraeger, einheitlicher "
                            "Kontenrahmen, Standardvorlage statt "
                            "Einzelanfertigung, Vergleichbarkeit zwischen "
                            "Einheiten"),
        "pains": ("jede Einheit rechnet anders; das zweite Mandat kostet so "
                  "viel wie das erste; Vergleiche zwischen Standorten sind "
                  "nicht belastbar"),
        "kpis": ("Aufwand je zusaetzlicher Einheit, Dauer des "
                 "Konsolidierungslaufs, Anteil wiederverwendeter Struktur"),
        "vocabulary_use": ("Gesellschaft, Standort, Mandat, Kontenrahmen, "
                           "Vorlage, Konsolidierung, Verfahren"),
        "vocabulary_avoid": ("Konzern-Jargon fuer Haeuser mit einer Einheit, "
                             "Skalierung als Schlagwort"),
        "scene_de": ("eine Leitung, die dieselbe Kennzahl aus drei Einheiten "
                     "bekommt und drei verschiedene Definitionen vorfindet"),
        "scene_en": ("a finance lead receiving the same metric from three "
                     "units and finding three different definitions"),
        "cta_style": "reply",
    },
    {
        "id": "woher_die_zahlen",
        "label": "Woher die Zahlen kommen",
        "share": "secondary",   # 35 von 52 Anwenderberichten
        "axis": ("Die Daten liegen in einem System, das dem "
                 "Zahlenverantwortlichen nicht gehoert. Schnittstelle, "
                 "Mapping, Datenuebergabe, was beim Systemwechsel passiert"),
        "audience_de": ("Wer Zahlen aus Vorsystemen zusammenfuehrt: "
                        "Controlling, Rechnungswesen, kaufmaennische Leitung, "
                        "dazu Berater, die Mandantendaten uebernehmen."),
        "decision_makers_de": ("Leitung Controlling und Rechnungswesen, "
                               "Geschaeftsfuehrung bei Systementscheidungen"),
        "focus_topics_de": ("Schnittstellen zu Buchhaltung, ERP und "
                            "Personalsystem, Mapping und Kontenzuordnung, "
                            "Datenhoheit, Aufwand vor dem ersten Bericht"),
        "pains": ("Daten bleiben zwischen zwei Systemen haengen; die Vorarbeit "
                  "steht in keinem Projektplan; beim Systemwechsel ist unklar, "
                  "wem die Historie gehoert"),
        "kpis": ("Zeit bis zum ersten belastbaren Bericht, Zahl der "
                 "angebundenen Vorsysteme, Anteil manueller Nacharbeit"),
        "vocabulary_use": ("Schnittstelle, Vorsystem, Mapping, "
                           "Kontenzuordnung, Datenhoheit, DATEV, ERP"),
        "vocabulary_avoid": ("reine IT-Themen ohne Bezug zur Steuerung, "
                             "Produktnamen als Held"),
        "scene_de": ("jemand, der den Monatsbericht nicht anfangen kann, weil "
                     "eine Datei aus dem Vorsystem fehlt"),
        "scene_en": ("someone unable to start the monthly report because one "
                     "file from the source system is missing"),
        "cta_style": "reply",
    },
    {
        "id": "rechenschaft",
        "label": "Wem man Rechenschaft schuldet",
        "share": "secondary",   # 35 von 52 Anwenderberichten
        "axis": ("Der Empfaenger der Zahlen sitzt ausserhalb des Hauses: Bank, "
                 "Gesellschafter, Aufsichtsgremium, Wirtschaftspruefer, "
                 "Kostentraeger"),
        "audience_de": ("Wer Zahlen nach aussen vertreten muss: "
                        "Geschaeftsfuehrung, kaufmaennische Leitung, dazu "
                        "Berater, die ihre Mandanten in solche Termine "
                        "begleiten."),
        "decision_makers_de": ("Geschaeftsfuehrung, Vorstand, kaufmaennische "
                               "Leitung"),
        "focus_topics_de": ("Bankgespraech und Finanzierung, Gesellschafter- "
                            "und Gremienberichte, Pruefungsvorbereitung, "
                            "Verhandlungen mit Kostentraegern"),
        "pains": ("im Termin nachreichen statt rechnen zu koennen; eine "
                  "Abweichung begruenden muessen, deren Ursache niemand mehr "
                  "kennt; Unterlagen, die der Empfaenger anders schneidet"),
        "kpis": ("Nachreichungen je Termin, Vorbereitungszeit, Zahl der "
                 "Rueckfragen von Bank oder Pruefer"),
        "vocabulary_use": ("Bankgespraech, Gesellschafter, Aufsichtsgremium, "
                           "Pruefer, Kostentraeger, Nachweis, belastbar"),
        "vocabulary_avoid": ("internes Reporting ohne externen Adressaten, "
                             "Compliance als Schlagwort"),
        "scene_de": ("eine Geschaeftsfuehrung, die im Bankgespraech eine "
                     "Anpassung nachreichen muss statt sie zu zeigen"),
        "scene_en": ("a managing director having to follow up after a bank "
                     "meeting instead of showing the change live"),
        "cta_style": "reply",
    },
    {
        "id": "fristen",
        "label": "Fristen mit Datum",
        "share": "secondary",   # kein Anteil: eigener Kalender
        "axis": ("Ein gesetzlicher oder tariflicher Termin steht fest und die "
                 "Vorarbeit faellt vorher an. Nur mit Datum und nur bei "
                 "Betroffenheit der Zielgruppe"),
        "audience_de": ("Wer die Vorarbeit zu einer Frist leisten muss: "
                        "Leitung Rechnungswesen, Controlling, "
                        "Geschaeftsfuehrung, dazu Berater, die ihre Mandanten "
                        "durch die Umstellung fuehren."),
        "decision_makers_de": ("Geschaeftsfuehrung, Leitung Rechnungswesen, "
                               "bei Beratungen die Mandatsverantwortlichen"),
        "focus_topics_de": ("IFRS 18 mit laufendem Vergleichsjahr 2026, "
                            "E-Rechnungspflicht ab 2027, AVR Caritas und "
                            "AVR.DD, jeweils Vorlaufzeit statt Stichtag"),
        "pains": ("die Arbeit faellt ein Jahr vor dem Stichtag an und ist im "
                  "Kalender nicht sichtbar; mehrere Fristen treffen dieselben "
                  "wenigen Personen; doppeltes Rechnen bei spaeter "
                  "Umstellung"),
        "kpis": ("Vorlauf bis zum Stichtag, vermiedene zweite Rechenlaeufe"),
        "vocabulary_use": ("Vergleichsjahr, Bezugsjahr, Stichtag, Gliederung, "
                           "Eingruppierung, Vorlauf"),
        "vocabulary_avoid": ("Regulierung ohne Datum, CSRD (Zielgruppe faellt "
                             "durch Omnibus I heraus), Panikmache, Detailtiefe "
                             "einer einzelnen Traegerart oder Tarifgruppe, die "
                             "der Rest der Zielgruppe nicht braucht (Kulle "
                             "24.08.2026: 'zu spezifisch auf Caritas')"),
        "scene_de": ("eine Leitung, die den Kalender fuers naechste Jahr "
                     "aufschlaegt und drei Fristen im selben Quartal findet"),
        "scene_en": ("a finance lead opening next year's calendar and finding "
                     "three deadlines in the same quarter"),
        "cta_style": "reply",
    },
]

# Welches Konto eine Achse faehrt. Die Achse entscheidet, nicht das Konto.
# Mehrere Konten je Achse sind erlaubt, die Reihenfolge ist die Praeferenz.
# Baumert bekommt bewusst keine Regulierungs-Achse: eine
# Marketing-Operations-Rolle hat vor Controllern keine eigene Fachautoritaet.
# Sie faehrt Auswertungen aus vorhandenem Material und Fragen an die Community.
AXIS_TO_ACCOUNT = {
    "excel_am_limit":   ["werner", "unternehmensseite"],
    "viele_einheiten":  ["werner", "unternehmensseite"],
    "woher_die_zahlen": ["werner", "baumert", "unternehmensseite"],
    "rechenschaft":     ["kulle", "unternehmensseite"],
    "fristen":          ["kulle", "unternehmensseite"],
}

# Bild-Texte auf Deutsch (Zielgruppe DACH-Berater).
IMAGE_LANGUAGE = "German"

# SWOT-Logo (Resources/swot_logo.png, transparentes PNG von swot.de, 12.08.2026)
# als Overlay unten rechts in generierten Bildern.
LOGO_FILE = "swot_logo.png"

FEATURES = {
    # Themen-Recherche scharfgestellt am 19.08.2026 (Richard). Der Kommentar-Pfad
    # bleibt unveraendert; neu ist die Themenfindung ueber Stichwort-Scrape plus
    # woechentliches Clustering, damit die Folgemonate nicht von Hand gefuellt werden.
    "supabase_persist": True,
    "keyword_scrape": True,
    "topic_mining": True,
    # Scoring-Gate vor dem Clustering (Richard 20.08.2026): jeder Post im
    # Mining-Fenster laeuft durch score_posts (topic_fit, icp_relevanz usw.,
    # VIRALITY_WEIGHT 0.3); unter MIN_SCORE faellt er raus, bevor er Themen
    # praegen kann. Haiku, grob unter 1 EUR je Wochenlauf.
    "mining_score_gate": True,
    "keyword_source_daily": False,
    "en_draft": False,
    "grammar_check": True,
    # Deutscher Lektor hinter der Textwache (Richard 24.08.2026: "gutes und
    # natuerlich klingendes Deutsch"). Ein Sonnet-Call je Post, bei Neulauf
    # zwei mehr. Siehe tools/naturalness.py.
    "naturalness_check": True,
    # Kein Slate- und kein Winner-Pfad, siehe Modul-Docstring.
    "slate_mode": False,
}

# Stichwortliste SWOT. Erweitert 19.08.2026 von 15 auf 40 Begriffe.
# Die Begriffe sind nicht geraten, sondern aus der Kundensprache gemessen:
# 71 Dateien aus Case-Studies/_markdown, voc-run-1-berater/evidence und
# voc-sales-calls, 2,36 Mio Zeichen. Trefferzahlen im Korpus in Klammern.
# Bewusst keine Head-Terms wie "Controlling Software": dort dominieren LucaNet
# und Jedox, und der Scrape zieht Vendor-Marketing statt Fachstimmen.
KEYWORDS = [
    # Planung und Abschluss (Kernprozesse)
    "Liquiditätsplanung",              # 35
    "Liquiditätsvorschau",
    "integrierte Finanzplanung",
    "integrierte Planung",              # 23
    "Unternehmensplanung",              # 8
    "Cashflow Planung",                 # 17 cashflow
    "Szenarioplanung",
    "Investitionsplanung",
    "Budgetierung Mittelstand",
    "Mittelfristplanung",
    "Konsolidierung",                   # 27
    "Konzernabschluss",
    "Monatsabschluss",                  # 8
    # Rechnungswesen und Steuerung
    "Kostenstellenrechnung",            # 101 kostenstellen
    "Kostenträgerrechnung",            # 23
    "Deckungsbeitragsrechnung",         # 7
    "Soll-Ist-Vergleich",               # 31
    "Hochrechnung Jahresende",          # 20
    "Forecast Genauigkeit",             # 64 forecast
    "Kennzahlensystem",                 # 84 kennzahlen
    # Werkzeuge und Bruchstellen (staerkstes Signal im Korpus)
    "Excel Controlling",                # 426 excel
    "Excel Planung ablösen",
    "Schnittstelle DATEV",              # 191 schnittstelle, 157 datev
    "DATEV Auswertung",
    "ERP Schnittstelle Controlling",    # 40 erp
    "Berichtswesen automatisieren",     # 9
    "Reporting Automatisierung",        # 215 reporting
    "Controlling Dashboard",            # 26 dashboard
    # Datierte Ausloeser
    "IFRS 18",
    "E-Rechnung Pflicht",
    "AVR Caritas",
    "AVR Diakonie",
    "Personalkostenplanung",            # 11
    "Tarifsteigerung Planung",
    # Zielgruppen und Branchen
    "Wirtschaftsplan Träger",          # 40 wirtschaftsplan
    "Controlling Sozialwirtschaft",     # 71 sozialwirtschaft
    "Controlling Wohnungswirtschaft",   # 7
    "Controlling Mittelstand",
    "Planungssoftware Auswahl",
    # Berater-Kontext (Welle 1)
    "Planungsmandat",                   # 440 mandant/mandanten
    "Bankgespräch Planung",            # 32 banken
    "Restrukturierung Mittelstand",     # 17 restrukturierung
    "Sanierungsberatung",               # 26 sanierung
]

# Zuordnung der 43 Begriffe auf die fuenf Achsen (Richard, 20.08.2026).
# Grund: der Seed-Lauf vom 19.08. clusterte alle Begriffe in einem Topf, und
# 10 der 15 Themen wurden Liquiditaet. Die AXIS_MIX-Regel (min 2 je Achse) kann
# aus einem schiefen Pool nichts geraderuecken, die Vielfalt muss vorher
# entstehen. Der Scrape laeuft deshalb je Achse und schreibt
# source="linkedin_search:<achse>", damit das Clustern die Herkunft kennt.
KEYWORDS_BY_AXIS = {
    "excel_am_limit": [
        "Excel Controlling", "Excel Planung ablösen", "Berichtswesen automatisieren",
        "Reporting Automatisierung", "Controlling Dashboard", "Planungssoftware Auswahl",
        "integrierte Finanzplanung", "integrierte Planung", "Szenarioplanung",
        "Mittelfristplanung", "Forecast Genauigkeit", "Liquiditätsplanung",
        "Liquiditätsvorschau", "Cashflow Planung",
    ],
    "woher_die_zahlen": [
        "Schnittstelle DATEV", "DATEV Auswertung", "ERP Schnittstelle Controlling",
        "Kostenstellenrechnung", "Kostenträgerrechnung", "Deckungsbeitragsrechnung",
        "Kennzahlensystem",
    ],
    "viele_einheiten": [
        "Konsolidierung", "Konzernabschluss", "Planungsmandat",
        "Controlling Sozialwirtschaft", "Controlling Wohnungswirtschaft",
        "Controlling Mittelstand", "Wirtschaftsplan Träger",
    ],
    "rechenschaft": [
        "Bankgespräch Planung", "Restrukturierung Mittelstand", "Sanierungsberatung",
        "Soll-Ist-Vergleich", "Hochrechnung Jahresende", "Monatsabschluss",
        "Unternehmensplanung", "Budgetierung Mittelstand", "Investitionsplanung",
    ],
    "fristen": [
        "IFRS 18", "E-Rechnung Pflicht", "AVR Caritas", "AVR Diakonie",
        "Personalkostenplanung", "Tarifsteigerung Planung",
    ],
}

# Scoring-Justierung fuer die stille DACH-Controlling-Nische (Richard 19.08.2026,
# Begruendung in der Vault-Notiz "SWOT Content-Research-Quellen" vom 29.07.2026).
# Volles Viralitaets-Gewicht wuerde Vendor-Marketing nach oben spuelen; ein Beitrag
# mit 12 Reaktionen von einem kaufmaennischen Leiter ist fuer SWOT mehr wert als
# 800 Reaktionen unter einem Berater-Karussell. Max-Score sinkt damit auf 53.
# Apify-Konto SWOT, getrennt von Jolly seit 12.08.2026 (Konto "kueswot",
# kue@swot.de). Der Tokenname weicht bewusst ab, damit ein fehlender SWOT-Token
# NICHT still auf Jollys APIFY_API_KEY zurueckfaellt. Die Wache in
# tools/apify_auth.py prueft zusaetzlich den Kontonamen vor dem ersten Lauf.
APIFY_TOKEN_ENV = "APIFY_API_TOKEN_SWOT"
APIFY_ACCOUNT = "kueswot"

# kie.ai-Konto SWOT (Richard 20.08.2026), gleiche Logik wie beim Apify-Token:
# eigener Env-Name, damit ein fehlender SWOT-Key nie still auf Jollys
# KIEAI_API_KEY zurueckfaellt. Aufgeloest in tools/kieai_image._api_key.
KIEAI_TOKEN_ENV = "KIEAI_API_KEY_SWOT"

VIRALITY_WEIGHT = 0.3
MIN_SCORE = 15

# Wird vom Kommentar-Pfad nicht gelesen (der nutzt COMMENT_DRAFTS), steht hier
# nur, weil tools/linkedin_scraper.py das Attribut erwartet.
SCRAPE = {
    "min_age_hours": 6,
    "max_age_hours": 168,
    "max_posts_per_profile": 5,
    "substack_min_age_hours": 24,
    "substack_max_age_hours": 168,
}

OWN_PROFILES = [
    {"poster": "Christian", "url": "https://www.linkedin.com/in/christian-kulle"},
]

# Kadenz wie bei lisocon nach der Korrektur vom 30.07.2026: drei Lauftage,
# ein Entwurf pro Lauf. Drei Kommentare an einem Tag lesen sich als Kampagne,
# und ein Kommentar wirkt nur unter einem frischen Post.
# Nur noch 2 Quellen, deshalb profiles_per_day = 2: die Rotation deckt die volle
# Liste in einem Lauf ab. Waechst die Liste, hier nachziehen.
#
# Quellen-Korrektur 2026-08-13: die 5 Wettbewerber-Seiten sind raus, SWOT hat
# Kommentare unter Wettbewerber-Posts untersagt (siehe Modul-Docstring). Was
# bleibt, sind ICV und Controller Institut. Der Pfad laeuft damit rechnerisch
# leer und ist erst wieder sinnvoll, wenn SWOT eigene Wunsch-Ziele nennt.
#
# Mengen-Korrektur 2026-08-10 (Richard): Deckel wie bei lisocon auf 5 je
# Lauftag, Fenster auf 72 Stunden (Abstand zwischen zwei Lauftagen).
# WARNUNG, gemessen am 10.08.: die 7 Quellen liefern in einer ganzen Woche nur
# 8 brauchbare Posts, unter 72 Stunden genau 1. Der Deckel ist damit kein
# Versprechen - realistisch bleiben 1 bis 2 Entwuerfe je Lauftag, bis
# influencers.csv deutlich waechst. Die Zahl ist ein Angebotsproblem, kein
# Deckelproblem.
COMMENT_DRAFTS = {
    "profiles_per_day": 2,    # volle Liste; waechst die CSV, hier nachziehen
    "max_posts_per_profile": 2,
    "max_age_hours": 72,      # Abstand zwischen zwei Lauftagen (Mo/Mi/Fr)
    "posters": ["Christian"],
    "days": (0, 2, 4),        # Mo, Mi, Fr (weekday())
    "drafts_per_poster": 5,   # muss x Poster >= drafts_total sein, sonst greift der Deckel nie
    "drafts_total": 5,
}

# Kein Default: NOTION_DB_ID muss als Env gesetzt sein (eigene SWOT-Content-DB).
NOTION_DB_ID_DEFAULT = None

# Eigene Themen-DB "SWOT Topic Ideas (mined)", angelegt 19.08.2026 unter
# Jolly Blogging Engine. Bewusst NICHT im SWOT-Dashboard: das ist das
# Kundenportal, ungepruefte Themenvorschlaege gehoeren dort nicht hin.
TOPIC_IDEAS_DB_ID_DEFAULT = "3c11617b-1baf-81f2-b521-d4bab7bc8656"

INFLUENCERS_CSV = os.path.join(os.path.dirname(__file__), "influencers.csv")

# --- Monatsplan (run_monthly_plan.py, Entscheidung Richard 19.08.2026) -------

# Content-Redaktionsplan Blog und LinkedIn im SWOT-Dashboard (kundensichtbar).
# Bewusst getrennt von NOTION_DB_ID_DEFAULT: das bleibt None, damit der
# Winner-Pfad der Recycling-Pipeline nie hierher schreibt. Der Monatsplan
# schreibt ausschliesslich Status "Entwurf" (seit 21.08.2026 gibt es keinen
# "Themenvorschlag" mehr; Zeilen betreten den Plan immer mit Text). Die
# Stufen "Text freigegeben" und "Freigegeben" setzt der Kunde von Hand.
CONTENT_PLAN_DB_ID = "4e7b33b3-e1a3-4e3d-8024-011731d3b373"

# Stimme je Kanal fuer tools/post_writer.py. Der Text traegt die Stimme des
# Kontos, nicht nur das Thema: wechselt ein Beitrag das Konto, wird er neu
# geschrieben. Fehlt ein Kanal hier, entsteht kein Text (lieber leer als im
# falschen Ton).
#
# Beide aktiven Stimmen tragen die Softwarehersteller-Position (Kulle,
# 24.08.2026): der Autor sitzt nicht im Bankgespraech, er sieht in Projekten,
# wie Kunden das Zahlenwerk dafuer vorbereiten. Sonst liest der Post wie ein
# Interim-CFO und SWOT verliert Glaubwuerdigkeit.
_HERSTELLER_POSITION = (
    " Du bist Softwarehersteller, kein Interim-CFO und kein Berater: du sitzt "
    "nicht im Bankgespraech, nicht vor Gericht, nicht in der "
    "Gesellschafterrunde. Du siehst in Einfuehrungsprojekten, Schulungen und "
    "Supportfaellen, wie Kunden ihr Zahlenwerk fuer solche Termine "
    "aufbereiten, und schreibst aus dieser Beobachterposition."
)


# Stimmprofile aus den Call-Transkripten (Richard 25.08.2026: "wo hast du
# die Menschlichkeit eingebaut?"). Je Konto eine Seite in clients/swot/voices/:
# Satzbau, typische und verbotene Wendungen, Haltung, zwei Schreibmuster.
# Sie haengen an der Kontostimme und gehen damit in den Schreib-Prompt UND
# als Massstab in den Lektor (naturalness.critic_prompt). Fehlt die Datei,
# bleibt nur die Rollenbeschreibung, nichts bricht.
_VOICES_DIR = os.path.join(os.path.dirname(__file__), "voices")


def load_voice_profile(name: str) -> str:
    path = os.path.join(_VOICES_DIR, f"{name}.md")
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return ("\n\nSTIMMPROFIL, daran misst sich jeder Satz. Es beschreibt gesprochene "
                "Sprache: Rhythmus, Bilder, Haltung und Wortwahl uebernehmen; Fuellwoerter "
                "(halt, irgendwie, also, ne) NIE; die typischen Wendungen sind Muster, "
                "hoechstens eine davon woertlich je Beitrag.\n" + f.read().strip())


ACCOUNT_VOICES = {
    "LinkedIn Robert": (
        "Du schreibst als Robert Werner, Leiter Vertrieb und Akademie der SWOT "
        "Controlling GmbH. Du sprichst taeglich mit Beratungsgesellschaften, "
        "Steuerberatern und Wirtschaftspruefern und schreibst aus der Praxis "
        "der Einfuehrungen und Schulungen." + _HERSTELLER_POSITION
        + load_voice_profile("werner")
    ),
    "LinkedIn Christian": (
        "Du schreibst als Christian Kulle von der SWOT Controlling GmbH. Du "
        "sprichst zu Verantwortlichen, die Zahlen nach aussen vertreten: vor "
        "Bank, Gesellschaftern, Aufsichtsgremium oder Pruefer. Nenne keinen "
        "Titel und keine Funktion im Text." + _HERSTELLER_POSITION
        + load_voice_profile("kulle")
    ),
    "LinkedIn Inga": (
        "Du schreibst als Inga Baumert von der SWOT Controlling GmbH. Du bist "
        "keine Fachautoritaet im Controlling und tust auch nicht so. Du wertest "
        "vorhandenes Material aus und stellst eine echte Frage an die Fachleute "
        "in deinem Netzwerk. Keine Ratschlaege an Controller."
    ),
    "LinkedIn Unternehmensseite": (
        "Du schreibst fuer die Unternehmensseite der SWOT Controlling GmbH, "
        "also in der Wir-Form. Sachlich, kein Ich."
    ),
}

# Aktive Absender-Konten (Richard, 20.08.2026). Nur diese bekommen Slots und
# damit Beitraege. Ausdruecklich vorlaeufig: Baumert und die Unternehmensseite
# kommen spaeter zurueck, dann reicht es, sie hier wieder aufzunehmen. Leere
# Liste oder fehlender Eintrag heisst: alle Konten aus POSTING_SCHEDULE.
ACTIVE_ACCOUNTS = ["werner", "kulle"]

# Laengenband je Kanal im Wechsel (run_plan_fill.length_band_for): jeder
# dritte Beitrag eines Kontos ist kurz (500-900 Zeichen, ein Gedanke, keine
# Liste). Kulle 24.08.2026: "Posts immer sehr lang, Aufbau immer gleich."
# Die Vielfalt steht im Code, nicht als Bitte im Prompt.
LENGTH_ROTATION = ["standard", "standard", "kurz"]

# Feste Beitragstage je Konto (Wochentag, Montag=0). Aus dem September-Plan.
POSTING_SCHEDULE = {
    "kulle":             {"kanal": "LinkedIn Christian",        "weekdays": [1, 3]},
    "werner":            {"kanal": "LinkedIn Robert",           "weekdays": [1, 2]},
    "baumert":           {"kanal": "LinkedIn Inga",             "weekdays": [2, 3]},
    "unternehmensseite": {"kanal": "LinkedIn Unternehmensseite", "weekdays": [1, 3]},
}

# Achsen-Mix je Monat. Durchgesetzt im Auswahl-Code (run_monthly_plan), NICHT
# im Scoring-Prompt: Scoring erzwingt keine Batch-Vielfalt.
AXIS_MIX = {
    # dominante Achse darf hoechstens ein Drittel der Slots belegen
    "max_share": {"excel_am_limit": 1 / 3},
    # jede Achse erscheint mindestens zweimal, sofern Themen vorliegen
    "min_per_axis": 2,
    # Fristen-Themen nur, wenn der Termin binnen dieser Frist liegt
    "fristen_horizon_days": 120,
}

# Fristen-Kalender fuer die Achse "fristen". Aktiv von horizon_days vor dem
# Termin bis 30 Tage danach (eine gerade in Kraft getretene Regel traegt noch
# einen Rueckblick-Beitrag, danach nicht mehr).
FRISTEN_KALENDER = [
    {"id": "ifrs18", "deadline": "2027-01-01",
     "label": "IFRS 18: Vergleichsjahr 2026 schliesst zum 31.12."},
    {"id": "erechnung", "deadline": "2027-01-01",
     "label": "E-Rechnung: Versandpflicht ab 01.01.2027, Bezugsjahr 2026"},
    {"id": "avr_caritas", "deadline": "2027-01-01",
     "label": "AVR Caritas: Neufassung ab 01.01.2027"},
    {"id": "avr_dd", "deadline": "2026-09-01",
     "label": "AVR.DD: Entgelterhoehung 3,0 Prozent zum 01.09.2026"},
]
