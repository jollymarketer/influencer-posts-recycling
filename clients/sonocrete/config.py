"""Sonocrete GmbH (Cottbus) - Mandanten-Config, Stand 09.09.2026.

Anlass: Malt-Bewerbung bei Dr. Nora Baum (CFO), Zusage fuer den 20-Minuten-
Call: drei konkrete Post-Ideen. Diese Config traegt nur, was der Themen-Pfad
(tools/post_writer.write_post) und die Bildstrecke (tools/image_archetypes,
tools/kieai_image) brauchen. Kein Scraping, kein Slate, kein Notion.

Quellen: sonocrete.com (Technology, Benefits, Demo, Press, abgerufen
09.09.2026), Clients/_Prospects/Sonocrete/2026-09-09_sonocrete_meeting-
vorbereitung.md. Zahlen ausschliesslich aus PROOF_ASSETS; alles andere ist
Beobachtung ohne Zahl.

Harte Regeln: Sie-Form durchgehend; keine Preise; keine erfundenen Werke
oder Kundennamen; Referenzen nur Deutsche Bahn (Neues Werk Cottbus), Consolis
Tecnyconta, Mattig & Lindner; Wettbewerber (Zementhersteller, Zusatzmittel,
CO2-Kompensation) nie abwerten; Dauerhaftigkeitsaussagen nur mit der
Einschraenkung "je Rezeptur pruefen".
"""
import os

NAME = "sonocrete"

CONTEXT = """
Sonocrete GmbH (Cottbus, Ausgruendung aus der BTU Cottbus-Senftenberg) bringt Hochleistungsultraschall in die Betonherstellung. Ein Bypass-System mischt einen Teil von Zement, Wasser und Zusatzstoffen vor und behandelt diese Suspension mit Ultraschall. Die Kavitation beschleunigt die Bildung der C-S-H-Phasen, die den Beton erhaerten lassen. Nachruestbar ohne Umbau der bestehenden Mischanlage.

POSITIONIERUNG: Weniger Zement bei gleicher Druckfestigkeit, frueheres Ausschalen, mehr Ausstoss aus derselben Halle. Der Gegner ist der Status quo: Rezepturen, die Fruehfestigkeit ueber Zementueberschuss, Beschleuniger oder Waermebehandlung erkaufen. Nie ein Wettbewerber, nie ein Zementhersteller.

ZIELGRUPPE: Betonfertigteilwerke (konstruktive Fertigteile, Spannbeton, Betonwaren) und Transportbetonwerke im DACH-Raum. Rollen: Werkleiter und Produktionsleiter (Taktzeit, Schalungsumlauf), Betonlaborleiter und Betontechnologen (Rezeptur, Pruefwerte, Dauerhaftigkeit), Geschaeftsfuehrer und Vertriebsleiter (Ausschreibungen mit CO2-Vorgabe, EPD, Kundenanforderungen).

BELEGTE ZAHLEN (nur diese, woertlich): 4-fache Fruehfestigkeit nach 8 Stunden; Ausschalen bis zu 6 Stunden frueher; bis zu 100 Prozent mehr Ausstoss durch kuerzere Erhaertungszeit; 30 Prozent weniger Zement bei gleicher Druckfestigkeit; 10 bis 50 kg Zement je Kubikmeter weniger je nach Rezeptur; 10 bis 30 Prozent weniger CO2; Beispielrechnung 35.000 Kubikmeter Jahresproduktion sparen rund 3.200 Tonnen Klinker im Jahr; erster Werksversuch in Originalgroesse November 2021 mit 30 Prozent weniger CO2.

ANGEBOT (Early-Access-Programm): Das Werk schickt seine Rezeptur, auf Wunsch unter NDA. Sonocrete entwickelt im eigenen Labor zementreduzierte Varianten, auch mit weniger Beschleuniger oder ohne Waermebehandlung. Das Werk prueft die Varianten im eigenen Labor mit den eigenen Ausgangsstoffen. Keine Investition vor dem Ergebnis.

REFERENZEN (nur diese): Deutsche Bahn (Neues Werk Cottbus), Consolis Tecnyconta (Spanien), Mattig & Lindner. Presse: FAZ September 2025, ZDF, n-tv, Deutschlandfunk. Preise: Brandenburger Innovationspreis 2023, OSV Unternehmerpreis 2023.

HARTE REGELN: Sie-Form. Keine Preise. Keine erfundenen Werke, Kunden oder Pruefwerte. Dauerhaftigkeit (Carbonatisierung, Frost-Tausalz) ist je Rezeptur zu pruefen, nie pauschal zugesagt. Zementhersteller, Zusatzmittelhersteller und CO2-Kompensation werden eingeordnet, nie abgewertet. Kein Rechtsrat zu Vergaberecht oder EPD-Pflichten.
"""

TOKENS = {
    "SCORING_ROLE": "Du bist Content-Stratege bei Sonocrete (Ultraschall in der Betonherstellung: weniger Zement, frueheres Ausschalen).",
    "TOPIC_FIT_QUESTION": "Passt das Thema zu Betonfertigteilwerken oder Transportbeton: Rezeptur, Fruehfestigkeit, Ausschalfristen, Taktzeit, Zementgehalt, Klinkerfaktor, CO2 je Kubikmeter, EPD, Ausschreibungen mit CO2-Vorgabe?",
    "ICP_RELEVANZ_QUESTION": "Wuerde ein Werkleiter, Betonlaborleiter oder Geschaeftsfuehrer eines Betonwerks im DACH-Raum diesen Inhalt lesen wollen?",
    "CLASSIFY_PERSONA_MENU": "werkleitung, labor, geschaeftsfuehrung",

    "PERSONA_DE": "Du bist Dr. Ricardo Remus, Gruender und Geschaeftsfuehrer der Sonocrete GmbH in Cottbus. Du bringst Hochleistungsultraschall in die Betonherstellung und stehst seit Jahren in Fertigteilwerken am Mischer.",
    "AUDIENCE_DE": "Werkleiter, Betonlaborleiter, Betontechnologen und Geschaeftsfuehrer von Betonfertigteil- und Transportbetonwerken im deutschsprachigen Raum.",
    "DECISION_MAKERS_DE": "Entscheider in Betonwerken (Werkleitung, Betonlabor, Geschaeftsfuehrung)",
    "FOCUS_TOPICS_DE": "Praxis-Relevanz im Werk: Ausschalfrist, Taktzeit, Zementgehalt je Kubikmeter, Pruefwerte, CO2-Vorgaben in Ausschreibungen",
    "FIRST_PERSON_ROLE_DE": "du bist der Praktiker, der die Rezepturen der Werke im Labor und am Mischer sieht",
    "READER_ADDRESS_DE": "Der Leser wird direkt angesprochen, durchgehend in der Sie-Form, nie du und nie ihr",
    "CONTEXT_TRANSFER_DE": "Auf den Alltag eines Betonwerks uebertragen: Mischer, Schalung, Labor, Ausschreibung. Die Branche nicht plakativ betonen",
    "BELIEF_ACTORS_DE": "Betonlabore und Werkleitungen",
    "COMPARISON_SUBJECT_DE": "ein Weg, den CO2-Wert je Kubikmeter zu senken (klinkerarmer Zement, Kompensation, Rezeptur mit weniger Zement bei gleicher Leistung)",
    "SCENE_ACTOR_DE": "ein Werkleiter oder Betonlaborleiter",
    "HASHTAG_LINE_DE": "Keine Hashtags verwenden. Der Post endet mit dem letzten Inhalts-Satz.",
    "PARAGRAPH_RULE_DE": "- Absaetze hoechstens 3 Saetze lang. Leerzeile zwischen den Absaetzen",
    "LANGUAGE_BANS_DE": """- Niemals Preise, Investitionssummen, Lizenzkosten oder Budget-Groessenordnungen nennen
- Zahlen nur woertlich aus den belegten Zahlen im Kontext oder aus dem Case-Asset; keine anderen Prozentwerte, Tonnen, Stunden oder Kubikmeter erfinden
- Keine erfundenen Werke, Kunden, Pruefreihen oder Normwerte; Referenzen nur Deutsche Bahn (Neues Werk Cottbus), Consolis Tecnyconta, Mattig & Lindner
- Dauerhaftigkeit (Carbonatisierung, Frost-Tausalz-Widerstand) nie pauschal zusagen; erlaubt ist nur "je Rezeptur pruefen" oder "noch nicht fuer jede Rezeptur belegt"
- Zementhersteller, Zusatzmittelhersteller, klinkerarme Zemente und CO2-Kompensation nur einordnen, nie abwerten
- Kein Rechtsrat: keine Aussagen, was Vergaberecht, EPD-Pflichten oder Normen konkret vorschreiben
- Sonocrete hoechstens einmal beilaeufig nennen, nie als Held des Posts
- Anrede durchgehend Sie, nie du, nie ihr
- Schreibweise: Sonocrete, Ultraschall, Zementleim, C-S-H-Phasen, Kubikmeter (nicht m3 im Fliesstext)""",

    "PERSONA_EN": "You are Dr. Ricardo Remus, founder and CEO of Sonocrete GmbH (high-power ultrasound in concrete mixing).",
    "AUDIENCE_EN": "plant managers, concrete lab heads and managing directors of precast and ready-mix plants.",
    "WRITE_FOR_EN": "plant and lab decision-makers, not for marketers",
    "FOCUS_TOPICS_EN": "demoulding time, cycle time, cement content per cubic metre, test values, CO2 requirements in tenders",
    "FIRST_PERSON_ROLE_EN": "you speak from daily practice at the mixer and in the concrete lab",
    "HASHTAG_LINE_EN": "No hashtags. The post ends with the last content sentence.",
    "BELIEF_ACTORS_EN": "concrete labs and plant managers",
    "COMPARISON_SUBJECT_EN": "a way to lower CO2 per cubic metre",
    "SCENE_ACTOR_EN": "a plant manager or concrete lab head",

    "BRAND_NAME": "Sonocrete",
    "IMAGE_BRAND_DIRECTION": """Use the Sonocrete brand system flexibly. The visual identity should feel like
industrial precision: concrete, steel moulds, laboratory glass, cement slurry,
ultrasound waves. Calm, technical, editorial. Never a cartoon, never a stock
handshake.""",
    "IMAGE_BRAND_RULES": """Sonocrete brand rules:
Background: very light cool grey (#F5F7FA) or light concrete texture; deep
petrol navy (#174057) allowed for dark compositions.
Headlines: petrol navy (#174057) on light backgrounds, white on navy,
ultra-bold condensed grotesque (Barlow Condensed style).
Accent color: Sonocrete mint green (#B5DDAE) as THE signature accent, used
for one highlight element, one key numeral or the ultrasound wave motif. A
second accent blue (#0050BD) only for a single fine line if needed.
Supporting neutrals: dark grey (#515750), light grey (#E4EBF3).
Max 3 prominent colors. No logos of any kind, no monograms, no imprinted
marks. Reserve a clean, empty bottom-right corner for a logo overlay.""",
    "IMAGE_TYPOGRAPHY": "Barlow Condensed style bold condensed sans serif",
    "DEFAULT_AUDIENCE_IMAGE": "plant managers and concrete technologists at precast plants in German-speaking countries",
    "DEFAULT_AUDIENCE_ARCHETYPE": "plant managers, concrete lab heads and managing directors of precast plants",
    "TOPIC_CLUSTER_ROLE": "You are a B2B content strategist for Sonocrete GmbH (ultrasound-treated cement slurry for precast and ready-mix concrete plants in the DACH region).",
    "TOPIC_MINING_BRIEF": "Extract specific German-language LinkedIn post topics for plant managers, concrete lab heads and managing directors of precast and ready-mix plants. Never invent numbers.",
    "ARCHETYPE_BRAND_RULES": """Sonocrete brand rules:
- Background: very light cool grey (#F5F7FA) or a light, fine concrete
  texture; deep petrol navy (#174057) allowed for dark compositions. No
  gradients, no generic corporate blue.
- Headline / key type: petrol navy (#174057) on light backgrounds, white on
  navy, ultra-bold condensed grotesque (Barlow Condensed style).
- Accent (one only): Sonocrete mint green (#B5DDAE) for the key numeral, one
  highlight element or an ultrasound wave motif. Never flood the image.
- Supporting neutrals: dark grey (#515750), light grey (#E4EBF3). Max 3
  prominent colors.
- Materials that fit: concrete surfaces, steel formwork, precast elements,
  cement slurry, laboratory beakers, test cubes, ultrasound waves.
- No brand, tool or company logos anywhere, neither Sonocrete's own nor third
  parties'. No monograms, signatures or imprinted marks.
- Reserve a clean, empty bottom-right corner for a logo overlay added later.""",
    "INFOGRAPHIC_BRAND_RULES": """Sonocrete brand rules for diagrams and infographics:
- Background: very light cool grey (#F5F7FA). No gradients.
- Labels and headings: petrol navy (#174057), bold condensed.
- Structural elements: petrol navy (#174057); dark grey (#515750) secondary.
- Accent: mint green (#B5DDAE) for the one element the reader should see
  first. Never more than one accent per diagram.
- At most 3 colors. No logos of any kind. Numbers legible at feed size.""",
}

# Drei Achsen, je eine Situation im Werk. Die Achse bestimmt die Persona und
# damit den Absender (AXIS_TO_ACCOUNT).
CONTENT_PERSONAS = [
    {
        "id": "werkleitung",
        "label": "Werkleitung und Produktionsleitung im Betonfertigteilwerk",
        "share": "dominant",
        "axis": "Taktzeit und Ausstoss: wann die Schalung frei wird, wie viele Umlaeufe eine Halle am Tag schafft",
        "audience_de": "Werkleiter und Produktionsleiter von Betonfertigteilwerken im deutschsprachigen Raum.",
        "decision_makers_de": "Werkleiter, die an Ausstoss je Schalung und Tag gemessen werden",
        "focus_topics_de": "Ausschalfrist, Schalungsumlauf, Taktzeit, Spaetschicht, Waermebehandlung als Kostenblock",
        "pains": "Schalungen sind der Engpass, nicht die Halle; Fruehfestigkeit wird ueber Waermebehandlung oder Beschleuniger erkauft; jede Stunde Wartezeit auf die Ausschalfestigkeit kostet einen Umlauf",
        "kpis": "Ausschalzeitpunkt in Stunden, Umlaeufe je Schalung und Tag, Kubikmeter je Tag, Energie fuer Waermebehandlung",
        "vocabulary_use": "Ausschalfrist, Schalungsumlauf, Taktzeit, Fruehfestigkeit, Ausschalfestigkeit, Waermebehandlung, Rezeptur",
        "vocabulary_avoid": "CO2-Rhetorik als Hauptargument, Nachhaltigkeitsfloskeln, Pruefnormen-Details",
        "scene_de": "ein Werkleiter, der morgens um sechs auf die Schalungen wartet, weil der Beton von gestern Abend noch nicht ausschalfest ist",
        "scene_en": "a plant manager waiting for the moulds at six in the morning because last night's pour is not ready to strip",
        "cta_style": "reply",
    },
    {
        "id": "labor",
        "label": "Betonlaborleitung und Betontechnologie",
        "share": "secondary",
        "axis": "Pruefwerte und Dauerhaftigkeit: was eine Rezeptur mit weniger Zement im Labor wirklich zeigt",
        "audience_de": "Betonlaborleiter, Betontechnologen und Qualitaetsverantwortliche in Betonwerken im deutschsprachigen Raum.",
        "decision_makers_de": "Betonlaborleiter, die eine neue Rezeptur freigeben oder ablehnen",
        "focus_topics_de": "Druckfestigkeit nach 8 Stunden und 28 Tagen, Zementgehalt, C-S-H-Bildung, Dauerhaftigkeit je Rezeptur, eigene Ausgangsstoffe",
        "pains": "jede Zementreduktion gilt im Labor als Risiko fuer die Dauerhaftigkeit; Herstellerdaten stammen aus fremden Rezepturen mit fremden Ausgangsstoffen; die Freigabe traegt der Laborleiter persoenlich",
        "kpis": "Druckfestigkeit nach 8 Stunden und 28 Tagen, Zementgehalt je Kubikmeter, Konsistenz, Pruefreihen mit eigenen Stoffen",
        "vocabulary_use": "Rezeptur, Zementleim, C-S-H-Phasen, Druckfestigkeit, Ausgangsstoffe, Pruefreihe, Dauerhaftigkeit, Wasserzementwert",
        "vocabulary_avoid": "Ausstoss- und Kostenargumente (Werkleitungs-Achse), Marketingversprechen, pauschale Dauerhaftigkeitszusagen",
        "scene_de": "eine Betonlaborleiterin, die eine Rezeptur mit weniger Zement auf dem Tisch hat und sagt, dass sie das nicht freigibt",
        "scene_en": "a concrete lab head with a reduced-cement mix design on the table saying she will not sign it off",
        "cta_style": "reply",
        "voice_de": "Du bist Dr. Christiane Roessler, Mitgruenderin und wissenschaftliche Leiterin der Sonocrete GmbH in Cottbus. Du hast die Ultraschallbehandlung von Zementleim an der BTU Cottbus erforscht und arbeitest heute mit den Betonlaboren der Werke an ihren eigenen Rezepturen.",
    },
    {
        "id": "geschaeftsfuehrung",
        "label": "Geschaeftsfuehrung und Vertriebsleitung von Betonwerken",
        "share": "secondary",
        "axis": "Auftraege gewinnen: CO2-Vorgaben in Ausschreibungen und Kundenanforderungen an das Bauteil",
        "audience_de": "Geschaeftsfuehrer und Vertriebsleiter von Betonfertigteil- und Transportbetonwerken im deutschsprachigen Raum.",
        "decision_makers_de": "Geschaeftsfuehrer, die entscheiden, mit welchem CO2-Wert je Bauteil das Werk anbietet",
        "focus_topics_de": "CO2-Wert je Kubikmeter und je Bauteil, EPD-Anforderungen der Auftraggeber, Bahn und oeffentliche Hand als Vorreiter, Wege zur Senkung und ihre Kosten",
        "pains": "Ausschreibungen verlangen einen CO2-Wert je Bauteil; klinkerarme Zemente bremsen die Fruehfestigkeit; Kompensation kostet und aendert nichts am Bauteil",
        "kpis": "CO2 je Kubikmeter, gewonnene Ausschreibungen mit CO2-Vorgabe, Klinker je Jahr, Mehrkosten je Kubikmeter",
        "vocabulary_use": "Ausschreibung, CO2-Vorgabe, EPD, Klinker, Bauteil, Auftraggeber, Rezeptur",
        "vocabulary_avoid": "Labordetails (Labor-Achse), Taktzeit-Rechnungen (Werkleitungs-Achse), Rechtsrat zum Vergaberecht",
        "scene_de": "ein Geschaeftsfuehrer, der in einer Ausschreibung zum ersten Mal ein Feld fuer den CO2-Wert je Bauteil ausfuellen muss",
        "scene_en": "a managing director filling in a CO2-per-element field in a tender for the first time",
        "cta_style": "reply",
    },
]

AXIS_TO_ACCOUNT = {
    "werkleitung": "LinkedIn Ricardo",
    "labor": "LinkedIn Christiane",
    "geschaeftsfuehrung": "LinkedIn Ricardo",
}

CLOSING_RULE_DE = (
    "Der letzte Absatz ist eine Bruecke von einem Satz in der Sie-Form: er "
    "nennt aus dem Thema den Anlass, die eigene Rezeptur einmal pruefen zu "
    "lassen, ohne Frage und ohne Floskel. Der Beitrag endet nie mit einer "
    "Frage und nennt weder Link noch Kommentar: die Angebotszeile steht "
    "automatisch darunter."
)

STRUCTURE_REPLACEMENTS = [
    ("2-4 Annahme-gegen-Praxis-Paare", "zwei Annahme-gegen-Praxis-Paare, nie mehr"),
]

_HERSTELLER = (
    " Du bist Technologieanbieter, kein Betonwerk und kein Pruefinstitut: "
    "deine Kenntnis stammt aus Laborreihen mit den Rezepturen der Werke und "
    "aus Werksversuchen. Genau eine Beobachtung je Beitrag in der Ich-Form "
    "aus einer konkreten Situation im Labor oder am Mischer. Anrede des "
    "Lesers durchgehend Sie, nie du und nie ihr. Am Schluss: " + CLOSING_RULE_DE
)

ACCOUNT_VOICES = {
    "LinkedIn Ricardo": TOKENS["PERSONA_DE"] + _HERSTELLER,
    "LinkedIn Christiane": CONTENT_PERSONAS[1]["voice_de"] + _HERSTELLER,
}

# Angebotszeile unter jedem Beitrag (post_scorer._append_cta). Kein Link:
# das Angebot wird per Nachricht eingeloest.
CTA_DE = ("Schicken Sie uns Ihre Rezeptur. Sie bekommen die zementreduzierte "
          "Variante zurück und prüfen sie im eigenen Labor mit Ihren "
          "Ausgangsstoffen.")

COPY_RULES = {
    "disparagement": [r"falsch (?:gebaut|gemischt|gerechnet|gemacht)", r"dilettantisch",
                      r"niemand wusste", r"keiner (?:wusste|verstand)"],
    "term_map": {"Betonmischung": "Rezeptur", "Mischung": "Rezeptur"},
    "address": "Sie",
    "cta_bridge": True,
    "structure_max_repeat": 2,
}

LENGTH_ROTATION = ["standard", "kurz", "standard"]

MATRIX = {
    "mix": {"Perspective": 5, "Proof": 3, "Promotion": 2},
    "selection_floor": 2,
    "promotion_cap": 2,
    "boxes": [(job, stage)
              for job in ("Perspective", "Proof", "Promotion")
              for stage in ("Awareness", "Education", "Selection")],
}

# Einzige erlaubte Zahlen (sonocrete.com, 09.09.2026). Nie neue erfinden.
PROOF_ASSETS = [
    {"id": "ausschalen", "persona": "werkleitung",
     "claim": "Ausschalen frueher, mehr Umlaeufe je Schalung",
     "metric": "Ausschalen bis zu 6 Stunden frueher, bis zu 100 Prozent mehr Ausstoss",
     "context": "Angabe von Sonocrete fuer Fertigteilwerke, gilt fuer Rezepturen, die heute ueber Waermebehandlung oder Beschleuniger auf Fruehfestigkeit getrimmt sind"},
    {"id": "fruehfestigkeit", "persona": "labor",
     "claim": "Fruehfestigkeit nach 8 Stunden",
     "metric": "4-fache Druckfestigkeit nach 8 Stunden, 30 Prozent weniger Zement bei gleicher Druckfestigkeit",
     "context": "Angabe von Sonocrete; erster Werksversuch in Originalgroesse November 2021 mit 30 Prozent weniger CO2"},
    {"id": "klinker", "persona": "geschaeftsfuehrung",
     "claim": "Klinker und CO2 je Werk",
     "metric": "35.000 Kubikmeter Jahresproduktion sparen rund 3.200 Tonnen Klinker im Jahr; 10 bis 30 Prozent weniger CO2",
     "context": "Beispielrechnung von Sonocrete"},
]

OFFERS = [
    {"id": "early-access", "name": "Early-Access-Programm",
     "problem": "niemand im Werk gibt eine Rezeptur mit weniger Zement frei, bevor er sie mit den eigenen Ausgangsstoffen geprueft hat",
     "substance": "Rezeptur einreichen, auf Wunsch unter NDA; Sonocrete entwickelt im Labor zementreduzierte Varianten; das Werk prueft sie im eigenen Labor",
     "not_included": "keine Investition, keine Anlage vor dem Ergebnis",
     "cta": CTA_DE},
]
LEAD_MAGNETS: list = []

FEATURES = {
    "supabase_persist": False,
    "keyword_scrape": False,
    "topic_mining": False,
    "keyword_source_daily": False,
    "en_draft": False,
    "grammar_check": True,
    "naturalness_check": True,
    "slate_mode": False,
}

IMAGE_LANGUAGE = "German"
LOGO_FILE = "sonocrete_logo.png"
SCORING_MODEL = "claude-sonnet-4-6"
NOTION_DB_ID_DEFAULT = None
INFLUENCERS_CSV = os.path.join(os.path.dirname(__file__), "influencers.csv")


def _verified_facts_de() -> str:
    zahlen = "\n".join(f"- {a['claim']}: {a['metric']} ({a['context']})" for a in PROOF_ASSETS)
    return ("Belegte Zahlen von Sonocrete (sonocrete.com, 09.09.2026):\n" + zahlen +
            "\n\nReferenzen: Deutsche Bahn (Neues Werk Cottbus), Consolis Tecnyconta (Spanien), "
            "Mattig & Lindner. Das Early-Access-Programm ist kostenlos bis zum Laborergebnis: "
            "Rezeptur einreichen, zementreduzierte Variante zurueck, Pruefung im eigenen Labor.")


VERIFIED_FACTS_DE = _verified_facts_de()
