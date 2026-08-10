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

Die Quellenliste ist entsprechend anders zusammengesetzt als bei lisocon: keine
Fach-Creator, sondern Wettbewerber-Seiten plus Fachverbaende. Begruendung ist
Rang 4 derselben Notiz, "Beschwerde-Posts und Kommentare unter Vendor-Posts
sind Themen-Gold": unter einem LucaNet-Post liest SWOTs Zielgruppe mit.

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

# Einziger Poster, deshalb keine CONTENT_PERSONAS und kein POSTER_BY_PERSONA.
# `_voice()` in tools/comment_drafts.py faellt in diesem Fall auf PERSONA_DE
# zurueck, das ist hier der gewollte Pfad.
TOKENS = {
    "PERSONA_DE": (
        "Du bist Christian Kulle, Geschaeftsfuehrer der SWOT Controlling GmbH "
        "in Berlin. Du arbeitest seit Jahren mit Controlling- und "
        "Rechnungswesen-Teams im Mittelstand und in der Sozialwirtschaft an "
        "Konsolidierung, Finanz- und Personalkostenplanung. Du sprichst aus der "
        "Praxis, nicht aus der Produktbroschuere."
    ),
}

FEATURES = {
    "supabase_persist": False,
    "keyword_scrape": False,
    "topic_mining": False,
    "keyword_source_daily": False,
    "en_draft": False,
    "grammar_check": True,
    # Kein Slate- und kein Winner-Pfad, siehe Modul-Docstring.
    "slate_mode": False,
}

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
# Nur 7 Quellen, deshalb profiles_per_day = 7: die Rotation deckt die volle
# Liste in einem Lauf ab. Waechst die Liste, hier nachziehen.
#
# Mengen-Korrektur 2026-08-10 (Richard): Deckel wie bei lisocon auf 5 je
# Lauftag, Fenster auf 72 Stunden (Abstand zwischen zwei Lauftagen).
# WARNUNG, gemessen am 10.08.: die 7 Quellen liefern in einer ganzen Woche nur
# 8 brauchbare Posts, unter 72 Stunden genau 1. Der Deckel ist damit kein
# Versprechen - realistisch bleiben 1 bis 2 Entwuerfe je Lauftag, bis
# influencers.csv deutlich waechst. Die Zahl ist ein Angebotsproblem, kein
# Deckelproblem.
COMMENT_DRAFTS = {
    "profiles_per_day": 7,    # volle Liste; waechst die CSV, hier nachziehen
    "max_posts_per_profile": 2,
    "posted_limit": "week",   # belegter Enum-Wert; das echte Fenster ist max_age_hours
    "max_age_hours": 72,      # Abstand zwischen zwei Lauftagen (Mo/Mi/Fr)
    "posters": ["Christian"],
    "days": (0, 2, 4),        # Mo, Mi, Fr (weekday())
    "drafts_per_poster": 5,   # muss x Poster >= drafts_total sein, sonst greift der Deckel nie
    "drafts_total": 5,
}

# Kein Default: NOTION_DB_ID muss als Env gesetzt sein (eigene SWOT-Content-DB).
NOTION_DB_ID_DEFAULT = None

INFLUENCERS_CSV = os.path.join(os.path.dirname(__file__), "influencers.csv")
