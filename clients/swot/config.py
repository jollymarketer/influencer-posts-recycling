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
laufendem Vergleichsjahr 2026, E-Rechnungspflicht ab 01.01.2027. CSRD ist
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
    "FIRST_PERSON_ROLE_DE": (
        "du arbeitest seit Jahren an Planungs- und Konsolidierungsprojekten im "
        "Mittelstand und in der Sozialwirtschaft"
    ),
    "CONTEXT_TRANSFER_DE": (
        "Auf den Alltag von Controlling und Rechnungswesen im Mittelstand "
        "uebertragen, ohne die Branche plakativ zu betonen"
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
- Keine erfundenen Zahlen. Belegt sind ausschliesslich die Angaben aus dem KONTEXT""",

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

# Vier Konten ab September 2026 (Entscheidung Richard 19.08.2026). Die Rollen
# sind aus LinkedIn, Impressum und dem Call vom 27.07.2026 belegt.
#
# `axis` ist der Winkel, nach dem der Classifier einen Kandidaten einsortiert,
# nicht die Person. Derselbe Fachbereich kann je nach Winkel auf einer anderen
# Achse landen.
#
# HARTE REGEL: Baumert bekommt keine Fach-Aussagen zu AVR, IFRS oder
# E-Rechnung. Eine Marketing-Operations-Rolle hat vor Controllern und Beratern
# keine eigene Fachautoritaet, geliehene Autoritaet faellt in dieser Zielgruppe
# sofort auf. Regulierungsthemen laufen ueber Kulle und die Unternehmensseite.
CONTENT_PERSONAS = [
    {
        "id": "werner",
        "label": "Robert Werner, Leiter Vertrieb und Akademie",
        "share": "dominant",
        "axis": ("Projekt- und Schulungspraxis: was in Planungsprojekten und "
                 "Mandaten typischerweise schiefgeht und woran es liegt"),
        "audience_de": ("Steuerberater, Wirtschaftspruefer und "
                        "Unternehmensberater mit Planungsmandaten im "
                        "deutschsprachigen Raum."),
        "decision_makers_de": ("Partner und Mandatsverantwortliche in "
                               "Kanzleien und Beratungsgesellschaften"),
        "focus_topics_de": ("Praxis im Mandat: Datenzugang, Uebergabe von "
                            "Modellen, Standardvorlage gegen Einzelanfertigung, "
                            "Einfuehrungsdauer"),
        "pains": ("Excel-Modelle, die den Berater ueberleben, das Wissen darin "
                  "aber nicht; Planungsmodelle, die nur eine Person versteht; "
                  "Daten, die aus dem Vorsystem nicht sauber ankommen"),
        "kpis": ("Zeit bis zum ersten produktiven Mandat, Aufwand je "
                 "Folgemandat, Vertretungsfaehigkeit im Team"),
        "vocabulary_use": ("Mandat, Planungsmandat, Kontenrahmen, Vorlage, "
                           "Uebergabe, Schnittstelle, DATEV"),
        "vocabulary_avoid": "Feature-Listen, Lizenzmodelle, Produktnamen als Held",
        "scene_de": ("ein Berater, der ein uebernommenes Excel-Modell zum "
                     "ersten Mal oeffnet"),
        "scene_en": ("a consultant opening an inherited spreadsheet model for "
                     "the first time"),
        "cta_style": "reply",
    },
    {
        "id": "kulle",
        "label": "Christian Kulle, Geschaeftsfuehrer",
        "share": "secondary",
        "axis": ("Fristen, Regulierung und Marktbewegungen, eingeordnet aus "
                 "Geschaeftsfuehrungssicht"),
        "audience_de": ("Geschaeftsfuehrung und kaufmaennische Leitung im "
                        "deutschsprachigen Mittelstand und bei Traegern der "
                        "Sozialwirtschaft."),
        "decision_makers_de": ("Geschaeftsfuehrung, kaufmaennische Leitung, "
                               "Leitung Rechnungswesen"),
        "focus_topics_de": ("datierte Fristen und ihre Vorlaufzeit: IFRS 18, "
                            "E-Rechnung, AVR; dazu Eigentuemerwechsel im "
                            "Anbietermarkt und was sie fuer Bestandskunden "
                            "bedeuten"),
        "pains": ("Fristen, deren Arbeit ein Jahr vor dem Stichtag anfaellt; "
                  "Planung, die nach einem Anbieterwechsel keine eigene "
                  "Roadmap mehr hat"),
        "kpis": ("Vorlauf bis zum Stichtag, doppelte Rechenlaeufe vermieden, "
                 "Planungssicherheit ueber die Vertragslaufzeit"),
        "vocabulary_use": ("Vergleichsjahr, Stichtag, Gliederung, "
                           "Eingruppierung, Bestandskunde, Roadmap"),
        "vocabulary_avoid": ("Tagesgeschaeft aus dem Projekt, Schulungsanekdoten, "
                             "Produktbedienung"),
        "scene_de": ("eine Geschaeftsfuehrung, die den Kalender fuer 2027 "
                     "aufschlaegt und drei Fristen im selben Quartal findet"),
        "scene_en": ("a managing director opening the 2027 calendar and "
                     "finding three deadlines in the same quarter"),
        "cta_style": "reply",
    },
    {
        "id": "baumert",
        "label": "Inga Baumert, Marketing Operations Manager",
        "share": "secondary",
        "axis": ("Auswertungen aus vorhandenem Material, Nutzen einer Funktion "
                 "im Alltag, Fragen an die Community. Referiert Befunde, "
                 "urteilt nicht fachlich"),
        "audience_de": ("Anwenderinnen und Anwender in Controlling und "
                        "Rechnungswesen, dazu die Fachoeffentlichkeit im "
                        "deutschsprachigen Raum."),
        "decision_makers_de": ("Controlling- und Rechnungswesen-Teams, die mit "
                               "der Planung taeglich arbeiten"),
        "focus_topics_de": ("was in den eigenen Anwenderberichten steht, "
                            "Funktionen und ihr Nutzen im Alltag, offene "
                            "Fragen an die Community"),
        "pains": ("Funktionen, die vorhanden sind und trotzdem nicht genutzt "
                  "werden; Vorarbeit vor der eigentlichen Planung, die in "
                  "keinem Projektplan steht"),
        "kpis": ("Antworten und Kommentare je Frage, Nutzung vorhandener "
                 "Funktionen"),
        "vocabulary_use": ("Anwenderbericht, ausgezaehlt, Befund, Lesart, "
                           "Versionsvergleich, Berichtsverteilung"),
        "vocabulary_avoid": ("AVR, IFRS, E-Rechnung und jede andere fachliche "
                             "Bewertung von Regulierung oder Tarifrecht; "
                             "Aussagen ueber Bilanzierung"),
        "scene_de": ("jemand, der die eigenen Anwenderberichte auszaehlt und "
                     "ein unerwartetes Muster findet"),
        "scene_en": ("someone counting their own customer stories and finding "
                     "an unexpected pattern"),
        "cta_style": "question",
    },
    {
        "id": "unternehmensseite",
        "label": "SWOT Unternehmensseite",
        "share": "secondary",
        "axis": ("Anwenderberichte aus einzelnen Branchen und Marktueberblick, "
                 "gesprochen als Unternehmen"),
        "audience_de": ("Controlling und kaufmaennische Leitung quer durch die "
                        "Branchen der 52 Anwenderberichte, mit Schwerpunkt "
                        "Sozialwirtschaft."),
        "decision_makers_de": ("kaufmaennische Leitung und Controlling-Leitung "
                               "in Mittelstand, Sozialwirtschaft und "
                               "Wohnungswirtschaft"),
        "focus_topics_de": ("belegte Kundenprojekte: was vorher war, was sich "
                            "gemessen geaendert hat, worauf bei der Auswahl zu "
                            "achten ist"),
        "pains": ("abgebrochene Controlling-Projekte; Einfuehrungen, die an "
                  "Schnittstellen haengen bleiben; Auswahlkriterien, die die "
                  "Besonderheiten der eigenen Branche nicht abbilden"),
        "kpis": ("Dauer bis zur produktiven Nutzung, Aufwand je Berichtszyklus, "
                 "Zahl der angebundenen Vorsysteme"),
        "vocabulary_use": ("Anwenderbericht, Einfuehrung, Schnittstelle, "
                           "Gesellschaften, Kostenstellen, Berichtszyklus"),
        "vocabulary_avoid": ("Ich-Form, persoenliche Anekdote, Meinung ohne "
                             "Beleg aus einem Kundenprojekt"),
        "scene_de": ("ein Controller, der nach der Umstellung das erste Mal "
                     "monatlich statt jaehrlich berichtet"),
        "scene_en": ("a controller reporting monthly instead of annually for "
                     "the first time after the switch"),
        "cta_style": "reply",
    },
]

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
    "keyword_source_daily": False,
    "en_draft": False,
    "grammar_check": True,
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
    "Liquiditaetsplanung",              # 35
    "Liquiditaetsvorschau",
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
    "Kostentraegerrechnung",            # 23
    "Deckungsbeitragsrechnung",         # 7
    "Soll-Ist-Vergleich",               # 31
    "Hochrechnung Jahresende",          # 20
    "Forecast Genauigkeit",             # 64 forecast
    "Kennzahlensystem",                 # 84 kennzahlen
    # Werkzeuge und Bruchstellen (staerkstes Signal im Korpus)
    "Excel Controlling",                # 426 excel
    "Excel Planung abloesen",
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
    "Wirtschaftsplan Traeger",          # 40 wirtschaftsplan
    "Controlling Sozialwirtschaft",     # 71 sozialwirtschaft
    "Controlling Wohnungswirtschaft",   # 7
    "Controlling Mittelstand",
    "Planungssoftware Auswahl",
    # Berater-Kontext (Welle 1)
    "Planungsmandat",                   # 440 mandant/mandanten
    "Bankgespraech Planung",            # 32 banken
    "Restrukturierung Mittelstand",     # 17 restrukturierung
    "Sanierungsberatung",               # 26 sanierung
]

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
