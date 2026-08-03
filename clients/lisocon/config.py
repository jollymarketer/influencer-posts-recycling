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

VoC-Härtung (Richard 2026-07-12): Pains, Szenen, Vokabular und rote Linien aus
dem VoC Pain Hunt Run 1 (2026-07-10, 105 verifizierte Praktiker-Zitate),
Quelle: Clients\\Lisocon\\Research\\voc-run-1-praktiker-pain-hunt\\ (voc-report.md, mapping.md).
Verbatim-Zitate aus dem Korpus bleiben dem separaten, kuratierten
"Receipt"-Format vorbehalten und gehören NICHT in diese automatisierte Pipeline.

Persona-Schnitt und Magnet-Bindung (Kundenfeedback Jae 2026-07-29): die Achse
entscheidet, nicht die Rolle im Original-Post. Käufer = Zeit und Kosten des
GESAMTEN Übersetzungsprozesses (Reinhard). Anwender = Zeitaufwand und Mühe der
eigenen Layout-Arbeit (Jae). Leiter Technische Dokumentation, technische
Redakteure und Lokalisierungsverantwortliche stehen ab jetzt auf der
Anwender-Achse, obwohl sie Budget mitverantworten: ihr Post argumentiert
Arbeitserleichterung, nie ROI. Jede Persona hat genau EINEN Lead-Magneten
(Anwender: Layout-Check, Käufer: Prozess-Diagnose). Auslöser: im Run vom
29.07. trug ein Anwender-Post die Prozess-Diagnose (Reifegrad-Check), weil die
Magnet-Wahl bis dahin persona-blind per LRU rotierte.

MVO-Thema (Richard 2026-07-26): Säule 4 (Compliance/Zukunft) ist als eigener
Themen-Strang ausgebaut — EU-Maschinenverordnung (EU) 2023/1230, Geltungsbeginn
20.01.2027. Einziges datiertes, extern erzwungenes WHY im ganzen Themenraum.
Datum korrigiert: frühere Fassung nannte 14.01.2027, korrekt ist 20.01.2027
(veröffentlicht 29.06.2023, in Kraft 19.07.2023, keine allgemeine Übergangsfrist).
Rote Linie: MVO ist Anlass, nie Rechtsrat — siehe LANGUAGE_BANS_DE.
"""
import os

NAME = "lisocon"

CONTEXT = """
lisocon (lindner software & consulting GmbH, Hannover) ist ein B2B-Software-Unternehmen. Produkt: InTO — übersetzt InDesign-Dokumente direkt im Original-Layout. Kein Copy-Paste, keine DTP-Nacharbeit, kein Formatierungs-Chaos nach der Übersetzung; 99,5% Layout-Erhalt. SaaS oder On-Premise, SAP-Integration, arbeitet mit allen gängigen Translation-Management-Systemen (Trados, Across etc.).

POSITIONIERUNG (Kernbotschaft, wörtlich): "Übersetzt ist erst die Hälfte. Der teure Teil ist das Layout." InTO tritt nicht gegen DeepL/Trados/Crowdin an, sondern besitzt die Kategorie NACH der Übersetzung: Post-Translation-Layout-Automatisierung. Es eliminiert die versteckten Layout-Kosten zwischen übersetztem Text und druckfertigem Dokument. Der eigentliche Gegner ist der Status quo: Agenturen bündeln DTP-Nacharbeit unsichtbar in die Rechnung. Der Engpass ist Nachfrage/Awareness, nicht Wettbewerb: Content macht erst das Problem sichtbar ("Layout ist der teure Teil"), bevor er eine Lösung andeutet.

ICP:
Marketingleiter/MarCom-Direktoren, Lokalisierungsverantwortliche und Leiter Technische Dokumentation in produzierenden Unternehmen (500-10.000 MA), DACH und international. Typisch: Kataloge, Datenblätter und Technische Dokumentation in 10+ Sprachen, InDesign-basierte Publishing-Workflows, signifikantes Übersetzungs-/DTP-Budget.

KERN-THEMEN die den ICP interessieren:
Versteckte Lokalisierungs-/DTP-Kosten, Time-to-Market mehrsprachiger Materialien, Terminologie-Konsistenz, Translation Management, Technische Redaktion und Dokumentation, CCMS und strukturierter Content, InDesign-/Publishing-Automatisierung, AI in Übersetzung und Dokumentation, EU-Maschinenverordnung (EU) 2023/1230 ab 20.01.2027 (Sprachpflicht und Betriebsanleitungen), globale Content Operations, Abgrenzung der Ebenen: KI-Übersetzung (DeepL, Google, Plugins, Portale) löst Text, nicht Layout.

VOC-EVIDENZ (Pain Hunt Run 1, 2026-07-10, 105 verifizierte Praktiker-Zitate — diese Schmerzen sind real belegt; Posts, die einen davon treffen, sind nachweislich relevanter):
- Copy-Paste-Hölle (Anwender): übersetzte Texte werden Rahmen für Rahmen von Hand zurück ins InDesign-Layout gesetzt — pro Sprache, pro Version, jedes Jahr wieder. Der stärkste Recognition-Hook des Korpus.
- Versteckte DTP-Kostenlinie (Käufer): Layout-Nacharbeit ist bezahlte Facharbeit, multipliziert sich mit jeder Zielsprache und steht in keinem Budget-Posten. ROI-Logik immer: Stunden x Sprachen x Korrekturrunden.
- PDF-Korrekturschleife: Korrekturen laufen als PDF-Kommentar, manuelle Umsetzung in InDesign, Re-Export, Re-Check — meistens 3 bis 4 Runden pro Dokument. Guter zweiter Beat nach dem Copy-Paste-Hook, nicht als Standalone-Aufhänger.
- Textexpansion: Deutsch läuft nach der Übersetzung bis zu einem Drittel länger, Layouts brechen in jeder Zielsprache neu. Emotional stärkstes Thema — aber NIE als von InTO "gelöst" darstellen (siehe harte Regeln).
- Tool-Stack-Blindspot: Trados, Phrase oder DeepL sind da, und das Layout bleibt trotzdem Handarbeit. Beste Antwort-Munition auf "KI übersetzt doch schon".
- Post-AI-Klammer (stärkster aktueller Winkel): Teams übersetzen längst mit ChatGPT/DeepL — und setzen den Text trotzdem von Hand zurück ins Layout. KI hat die Übersetzung entwertet, nicht die Wiedereinsetzung.
Content-Franchise-Dach: "Die teure Hälfte" (direkt aus der Kernbotschaft; Käufer hört "teuer", Anwender hört "Hälfte"). Anwender-Fachbegriff mit Insider-Signal: "Fremdsprachensatz".

CONTENT-SÄULEN (jeder Post zahlt klar auf EINE dieser 5 Säulen ein; höherer Säulen-Bezug = besserer Score):
1. Versteckte Lokalisierungskosten — die teure DTP-Nacharbeit, die niemand budgetiert (Money-Säule, Persona Käufer).
2. Mehrsprachige Dokumentproduktion in der Praxis — InDesign-/DTP-/Versions-Chaos über viele Sprachen.
3. Terminologie und Qualität über Sprachen — Konsistenz, Glossare, TM; die stärkste Säule.
4. Compliance/Zukunft — EU-Maschinenverordnung als Deadline-Anker (Persona Käufer, sekundär Anwender). Details siehe MVO-ANKER.
5. Einwände und Abgrenzung — "KI übersetzt doch schon", Google, DeepL-Plugin, Portale: jeder Einwand ist Steilvorlage, nicht Bedrohung. Ebenen-Trennung Text vs. Layout.
Kein Produkt-Content: InTO ist nie das Thema, höchstens die beiläufige Auflösung.

MVO-ANKER (Säule 4, einziges datiertes und extern erzwungenes WHY im ganzen Themenraum — Posts, die diesen Anker sauber treffen, sind wertvoller als generischer Lokalisierungs-Content):
- Fakt: EU-Maschinenverordnung (EU) 2023/1230 gilt ab 20.01.2027 und ersetzt die Maschinenrichtlinie 2006/42/EG. Keine allgemeine Übergangsfrist. Das Datum ist der Anker, exakt so, nie ein anderes Datum, nie "Anfang 2027", nie "2026".
- Betroffene Dokumente: Betriebsanleitungen und Sicherheitsinformationen von Maschinen. Sie müssen in der Amtssprache des Mitgliedstaats bereitstehen, in dem die Maschine in Verkehr gebracht wird. Neu erlaubt ist die digitale Bereitstellung der Anleitung; auf Verlangen des Nutzers bleibt eine Papierfassung geschuldet, Sicherheitsinformationen bleiben in Papierform.
- Erzählwinkel (immer ein Prozess-Winkel, nie ein Paragraphen-Winkel): eine Sprachpflicht ist eine Doku-Produktions-Aufgabe. Mehr Zielsprachen mal mehr Dokumente mal Korrekturrunden bis zu einem festen Datum, mit demselben Team. Der Übersetzungstext ist dabei das kleinere Problem, die druckreife Fassung je Sprache das größere.
- Brücke zum kanonischen Spine: "übersetzt ist erst die Hälfte" trifft bei einer Deadline härter, weil ein Termin nicht verhandelbar ist. Wer erst im Herbst 2026 anfängt, layoutet unter Zeitdruck.
- Zweitwinkel für den Anwender: digitale Anleitung heißt zusätzliche Ausgabekanäle je Sprache, nicht weniger Layout-Arbeit.
- ROTE LINIEN MVO: kein Rechtsrat und keine Rechtsberatungs-Anmutung, keine Artikel- oder Anhang-Zitate, keine Aussage darüber, wer konkret betroffen ist oder was ein Unternehmen tun muss, keine Konformitäts- oder Haftungs-Versprechen, keine Bußgeld- oder Strafandrohung, keine Angst-Rhetorik. InTO macht niemanden MVO-konform; erlaubt ist ausschließlich der Prozess- und Kapazitäts-Winkel.

PERSONA-REGEL (zwei kollidierende Wertachsen, in EINEM Post nie mischen; die Achse entscheidet, nicht die Hierarchie-Ebene der Rolle):
- Käufer/Entscheider (Marketing-/MarCom-Leitung, Geschäftsführung), postet Reinhard: Zeit und Kosten des GESAMTEN Übersetzungsprozesses. Versteckte DTP-Kosten, Durchlaufzeit über alle Sprachen, ROI. Marketing-Leitung ist laut Daten der einzige belegte Konverter — im Zweifel diese Achse und dieser Adressat.
- Anwender und Fach-Leads (DTP und Designer, Translation-Manager, technische Redakteure, Leiter Technische Dokumentation, Lokalisierungsverantwortliche), postet Jae: Zeitaufwand und Mühe der eigenen Layout- und Dokumentarbeit. Leitfrage jedes Anwender-Posts ist "wie mache ich mir die Arbeit leichter", nie "wie bewerte ich meinen Prozess". Auch wenn ein Doku-Leiter Budget mitverantwortet, argumentiert sein Post Arbeitserleichterung, nie Kosten.
Ein Post fährt genau EINE Achse. Kosten-Argument und Arbeitserleichterung nie im selben Post vermengen. Fachthemen sind nicht per se einer Achse zugeordnet: Terminologie zum Beispiel ist Käufer-Thema als Qualitätskosten über alle Sprachen und Anwender-Thema als "Lektor sichert Konsistenz selbst ab, ohne Rückfrage an die Agentur".

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
    "TOPIC_FIT_QUESTION": "Passt das Thema zu Lokalisierung, Übersetzung, Technischer Dokumentation, Terminologie, mehrsprachigem Content, DTP/Publishing-Workflows, CCMS oder Content Operations? Bonus, wenn es einen VoC-verifizierten Schmerz trifft: manuelles Zurücksetzen übersetzter Texte ins Layout, versteckte DTP-Kosten pro Sprachversion, PDF-Korrekturschleifen, Textexpansion, oder 'KI übersetzt, Layout bleibt Handarbeit'. Themen rund um die EU-Maschinenverordnung 2023/1230 ab 20.01.2027 (Sprachpflicht, Betriebsanleitungen, digitale Anleitung, Produktsicherheits-Doku, CE-Dokumentation) zählen als passendes Thema, aber OHNE Bonus: sie werden wie jedes andere Thema bewertet und brauchen einen Doku- oder Prozess-Bezug, rein juristische Posts fallen durch. Abzug dagegen für Themen, die ausschliesslich VOR der Übersetzung spielen und nie bei mehrsprachiger Ausgabe landen: Prüfsoftware und Autorenunterstützung beim Verfassen, Terminologiearbeit allein im Ausgangsdokument, Redaktionsleitfäden in der Ausgangssprache. Das ist nicht unsere Kategorie.",
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
- Schreibweisen strikt: "InTO" (großes I, T, O), "lisocon" (immer klein)
- Nie behaupten, Textexpansion werde verhindert oder Copyfitting automatisiert; erlaubt ist nur: im gerenderten Layout sofort sichtbar und in einer Runde korrigierbar
- Einzelfall-Zahlen nie als Marktfakt: keine 400.000 EUR/Jahr, keine 55-150 EUR/h, keine 20-35%, kein 2-4x, kein 10x; Textexpansion höchstens als "bis zu einem Drittel länger" und als Praktiker-Schätzung gekennzeichnet
- Den Copy-Paste-Schmerz nie als "das löst niemand" framen (günstige Tools lösen den nackten Schritt); Differenzierung nur über das, was danach übrig bleibt: manueller Layout-Pass pro Sprache, stille Fehler, Korrekturschleifen
- Nie ein Adobe-Bordmittel schlechtreden oder ein konkretes Tool-Problem als aktuellen Bug zitieren
- Bei MVO-Posts: kein Rechtsrat, keine Artikel-/Anhang-Zitate, keine Aussage wer betroffen ist oder was zu tun ist, keine Konformitäts-, Haftungs- oder Bußgeld-Aussagen, keine Angst-Rhetorik; als Datum ausschließlich 20.01.2027, InTO nie als Weg zur MVO-Konformität darstellen""",
    "HASHTAG_LINE_DE": "Keine Hashtags verwenden. Der Post endet mit dem letzten Inhalts-Satz.",

    # --- EN-Post-Prompt (Stimme: Jae Hyun Kim) ---
    "PERSONA_EN": "You are Jae Hyun Kim, Sales & Marketing at lisocon (InTO: translation of InDesign documents directly in the original layout). You work daily with marketing and documentation teams at manufacturing companies drowning in multilingual DTP rework.",
    "AUDIENCE_EN": "heads of marketing, MarCom directors, localization managers and technical documentation leads at manufacturing companies (500-10,000 employees), international.",
    "WRITE_FOR_EN": "marketing, localization and documentation decision-makers, not for translators",
    "FOCUS_TOPICS_EN": "process and cost relevance: turnaround times, hidden DTP costs, terminology quality, scaling across languages",
    "FIRST_PERSON_ROLE_EN": "you speak from daily practice with multilingual document production in manufacturing",
    "HASHTAG_LINE_EN": "No hashtags. The post ends with the last content sentence.",

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
    # Slate-Modus (spec 2026-07-16): 3-Phasen-Pipeline statt Winner-Flow.
    "slate_mode": True,
}

# GTM-Call Jae 2026-07-09: auch Bild-Texte auf Deutsch (Default: English).
IMAGE_LANGUAGE = "German"

# Scoring-Modell (Richard 2026-07-16): Slate-Klassifikation (Persona, VoC,
# Themen-Winkel) braucht mehr Praezision als Haiku liefert.
SCORING_MODEL = "claude-sonnet-4-6"

# InTO-Bruecke (Kundenfeedback Jae 2026-07-29): Zusatzfeld der Klassifikation,
# das Kandidaten ohne Bezug zur Kategorie NACH der Uebersetzung deterministisch
# aus dem Slate wirft (run_slate.drop_without_bridge). Anlass war ein Thema zu
# Terminologie-Inkonsistenzen im Ausgangsdokument: hoher topic_fit ueber das
# Stichwort Terminologie, inhaltlich aber Pruefsoftware beim Verfassen, also
# vorgelagert und ohne jeden InTO-Bezug.
CLASSIFY_BRIDGE = (
    "EIN Satz, wie der Winkel bei mehrsprachiger Ausgabe oder bei der "
    "Layout-Arbeit NACH der Uebersetzung landet. Themen, die ausschliesslich "
    "vor der Uebersetzung spielen (Pruefsoftware und Autorenunterstuetzung "
    "beim Verfassen, Terminologiearbeit allein im Ausgangsdokument, "
    "Redaktionsleitfaeden in der Ausgangssprache), haben keine Bruecke: dann "
    "leerer String. Keine Bruecke konstruieren, die der Quell-Post nicht "
    "hergibt."
)

# Slate-Ready-Mail (17.07.2026): Link auf die Notion-View "Themen-Slate",
# geht via MAKE_SLATE_WEBHOOK (Env) + Make-Szenario 9537326 an Jae.
SLATE_VIEW_URL = "https://www.notion.so/3951617b1baf819e97a5d01a4765f606?v=39f1617b1baf81fab0cd000c9b527cac"

# Kommentar-Queue-View (26.07.2026). Die Mail dazu ist optional: ohne gesetztes
# MAKE_COMMENT_WEBHOOK schreibt die Engine die Zeilen stumm in die View.
COMMENT_VIEW_URL = "https://www.notion.so/3951617b1baf819e97a5d01a4765f606?v=3a91617b1baf81b18432000c90e28558"

# Slate-Modus (spec 2026-07-16): 10 Kandidaten, hart quotiert 5 kaeufer +
# 5 anwender. Jae pickt fuer beide Poster.
# Kadenz-Korrektur 2026-07-30 (Richard, Anlass Kundenfeedback Jae): vorher
# 2 Slates/Woche (Mo+Do) = 20 Kandidaten gegen 10 Publish-Slots (2/Tag x 5
# Werktage). Jae las das Slate als Freigabe-Queue statt als Menue, approvte 9
# von 10 und bekam zwei Tage spaeter die naechsten 10. Jetzt ein Slate pro
# Woche = 10 Kandidaten = genau die Wochenkapazitaet, eine Review-Sitzung.
# Deckt sich zugleich mit SCRAPE["max_age_hours"] = 168 (7 Tage, keine Luecke,
# keine Doppelabdeckung). Phase C und D laufen damit nur noch montags; die
# taeglichen Kommentar-Entwuerfe (Phase B) sind davon unberuehrt.
SLATE = {
    "days": (0,),            # Mo (weekday())
    "size": 10,
    "per_persona": 5,
    "max_age_days": 60,
    "max_times_slated": 3,
    # Rescore-Floor (Richard 2026-07-30): nur Kandidaten ab diesem gespeicherten
    # Score werden pro Slate-Lauf neu bewertet, der Rest behaelt seinen Score.
    # Gemessen an dem Tag: 132 von 307 statt 307, Median lag bei 18, Gate bei 25.
    # Wer unter 20 liegt, kann in diesem Lauf nicht mehr aufsteigen - bewusster
    # Kompromiss. 0 schaltet die Sparlogik ab.
    "rescore_floor": 20,
    # Winner-Repeat (Richard 2026-07-17, ColdIQ-Masterclass): gepickte Themen
    # nach 6 Wochen zurueck in den Pool - bewaehrte Winkel werden neu gescored
    # und als frischer Draft wieder angeboten, niemand merkt Wiederholungen.
    "revive_picked_days": 42,
}

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
# VoC-Härtung 2026-07-12: zwei Kaeufer-Achse-Begriffe ergaenzt (T5 versteckte
# DTP-Kostenlinie war in den Keywords bisher gar nicht abgedeckt).
# MVO-Thema 2026-07-26 (Richard, Freigabe ca. +1,5 EUR/Monat): vier Begriffe fuer
# Saeule 4. Die 39 Influencer-Profile reden nicht ueber die Maschinenverordnung,
# ohne diese Keywords kommt kein MVO-Kandidat in den Slate. Dient zugleich als
# billigster V1-Resonanz-Sweep (MVO-WHY hat null Zitate im VoC-Korpus).
# Kuerzung 2026-07-30 (Kundenfeedback Jae): vier MVO-Begriffe schwemmten den
# Kandidaten-Pool, der Slate vom 30.07. trug 5 von 5 Kaeufer-Themen zur MVO.
# Bleiben zwei: "Maschinenverordnung" als DE-Anker und "Betriebsanleitung
# Uebersetzung" als Doku-Bezug. Raus sind "EU Machinery Regulation" (englisches
# Duplikat desselben Ankers, ICP ist DACH) und "technische Dokumentation
# Compliance" (zog juristische Posts ohne Prozess-Winkel).
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
        "localization costs",
        "DTP Nacharbeit",
        "Maschinenverordnung",
        "Betriebsanleitung Übersetzung",
    ],
    "max_posts": 10,
    "posted_limit": "week",
}

# Themen-Cap je Persona-Seite (Kundenfeedback Jae 2026-07-30). Der Slate vom
# 30.07. trug auf der Kaeufer-Seite 5 von 5 MVO-Themen, Reinhard haette fuenf
# Tage hintereinander ueber dieselbe Verordnung gepostet. Ursache ist
# strukturell: `themen_diversitaet` im Scoring bewertet jeden Kandidaten in
# einem eigenen API-Call und nur gegen die zuletzt VEROEFFENTLICHTEN Posts -
# fuenf frische MVO-Kandidaten sehen einander nie. Greift deterministisch in
# run_slate.select_slate, kostet keinen zusaetzlichen API-Call.
TOPIC_CLUSTER_CAP = 2

# Cluster-Erkennung ueber den vom Scoring formulierten Winkel (topic_angle_de),
# nicht ueber den Quell-Post: gedeckelt gehoert, worueber WIR schreiben wuerden.
# Reihenfolge zaehlt, der erste Treffer gewinnt. Kein Treffer = kein Cluster =
# kein Cap; ein Cap auf "sonstiges" wuerde den Slate ohne Not verknappen.
# Keywords in Kleinschreibung, mit echten Umlauten wie im LLM-Output.
TOPIC_CLUSTERS = [
    {"id": "mvo",
     "keywords": ("maschinenverordnung", "machinery regulation", "2023/1230",
                  "20.01.2027", "20. januar 2027", "betriebsanleitung")},
    {"id": "terminologie",
     "keywords": ("terminologie", "glossar", "translation memory")},
    {"id": "dtp-kosten",
     "keywords": ("dtp-kosten", "dtp-nacharbeit", "versteckte kosten",
                  "kosten pro sprachversion")},
    {"id": "ki-uebersetzung",
     "keywords": ("ki-übersetzung", "ki übersetzt", "deepl", "chatgpt",
                  "maschinelle übersetzung")},
]

# Kadenz (Stand 2026-07-26, serverseitig per GraphQL gesetzt, NICHT aus der toml):
# Cron "0 5,10 * * 1-5" = Mo-Fr 05:00 und 10:00 UTC, also 07:00 und 12:00 Berlin.
# Der Morgenslot lag bis 26.07. auf 07:00 UTC und wurde auf Wunsch Richards auf
# 07:00 Ortszeit vorgezogen. ACHTUNG Zeitumstellung: 05:00 UTC ist nur bis zum
# 25.10.2026 gleich 07:00 Berlin, danach 06:00 - dann auf "0 6,11" ziehen.
# Jeder Lauf: Phase A (Bilder) + B (Kommentar-Entwuerfe, Tages-Guard).
# Phase D (Engagement-Readback) + C (Scrape + Slate) nur montags (SLATE["days"],
# seit 30.07. ein Slate statt zwei pro Woche).
# Der zweite Slot faehrt bewusst zwischen den beiden Publish-Zeiten (Jae 10:00,
# Reinhard 13:00 Ortszeit, Make 9517006 / 9506674), damit ein vormittags
# freigegebener Text noch am selben Tag sein Bild bekommt.
# Nicht gepickte Kandidaten persistieren in Supabase (topic_candidates) und
# konkurrieren in Folge-Slates erneut; Winner/Picks sind via Notion-URL-Dedup gesperrt.
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

# CTA-Politik (Richard 2026-07-26, Performance-Analyse der ersten 17 Live-Posts:
# 14 Likes gesamt, 2 Kommentare, 0 Leads). Derselbe externe Link unter jedem Post
# daempft Reichweite und liest sich als Automatik. Ab jetzt tragen nur noch
# Magnet-Posts einen Link, und zwar den auf das jeweilige Tool statt auf die
# Startseite. WEICHT VON Reinhards Vorgabe vom 08.07. AB - muss ihm gesagt werden.
CTA_POLICY = "magnet_only"

# Magnet-Slots je Slate (Richard 2026-07-26): erzwingt den Konversionspfad.
# Ohne diesen Zwang ist das Magnet-Format im Slate-Pfad unerreichbar (Box-Logik),
# Ergebnis waren 17 Posts ohne einen einzigen Lead-Magnet-Post. 2 von 10 deckt
# sich mit MATRIX["promotion_cap"].
MAGNET_SLOTS_PER_SLATE = 2

# Eigene Profile fuer den Engagement-Readback (Phase D).
OWN_PROFILES = [
    {"poster": "Reinhard", "url": "https://www.linkedin.com/in/reinhard-lindner"},
    {"poster": "Jae", "url": "https://www.linkedin.com/in/jae-hyun-kim-472723110"},
]

# Engagement-Readback (Richard 2026-07-26): die Pipeline endete bisher beim
# Publish, Winner-Repeat entschied rein nach Alter. Laeuft an den Slate-Tagen,
# ein Apify-Run fuer beide Profile (~0,10 USD/Monat). Impressionen liefert die
# API nicht, die kommen aus den nativen LinkedIn-Analytics der Poster.
ENGAGEMENT_READBACK = {
    "max_posts_per_profile": 20,
    "posted_limit": "month",
}

# Kommentar-Entwuerfe (Richard 2026-07-26): rotierender Ausschnitt der 39
# Influencer-Profile, ein Apify-Run pro Lauftag. Posten bleibt manuell.
# Tages-Guard `last_comments_at_lisocon` (engine_meta): der Cron faehrt zwei
# Slots pro Tag, Entwuerfe entstehen trotzdem nur einmal. Ein leerer Morgenlauf
# setzt den Guard nicht, damit der zweite Slot nachziehen kann.
#
# Kadenz-Korrektur 2026-07-30 (Richard, Anlass Kundenfeedback Jae): vorher 3
# Entwuerfe je Poster an jedem Werktag = 30 pro Woche, zusaetzlich zu 20
# Themenvorschlaegen. Soll sind 3 Kommentare pro Woche. Bewusst auf Mo/Mi/Fr
# verteilt statt als Wochenblock: ein Kommentar wirkt nur unter einem frischen
# Post (max_age_hours 30), und drei Kommentare an einem Tag lesen sich als
# Kampagne. `drafts_total` deckelt ueber beide Poster, `poster_rotation` in
# tools/comment_drafts.py laesst Reinhard und Jae abwechseln.
# Kosten sinken mit auf 3 statt 5 Apify-Runs pro Woche (~0,85 statt ~2 USD/Monat).
COMMENT_DRAFTS = {
    "profiles_per_day": 12,
    "max_posts_per_profile": 2,
    "posted_limit": "week",   # belegter Enum-Wert; das echte Fenster ist max_age_hours
    "max_age_hours": 30,
    "posters": ["Reinhard", "Jae"],
    "days": (0, 2, 4),        # Mo, Mi, Fr (weekday())
    "drafts_per_poster": 1,
    "drafts_total": 1,        # bindender Deckel ueber alle Poster
}

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

# Zwei live Tools auf in2go.io (Richard 2026-07-25). CTA ist der Direktlink
# (Self-Service-Tools, kein Kommentar-Keyword noetig). Der CTA-Wortlaut ist
# Kundenvorgabe (Richard 2026-07-31) und wird in tools/post_scorer.py
# (enforce_magnet_cta) woertlich unter den Post gesetzt, nicht vom Modell
# formuliert. `name` traegt denselben Tool-Namen wie die Landingpage, damit
# Fliesstext und CTA dasselbe Tool nennen. Zahlen von den
# Tool-Seiten NICHT uebernehmen (Website keine Zahlenquelle); erlaubte
# Referenz-Zahlen kommen ausschliesslich aus PROOF_ASSETS.
#
# Persona-Bindung (Kundenfeedback Jae 2026-07-29): genau ein Magnet je Persona,
# `persona` steuert asset_for_format. Layout-Check gehoert zur Anwender-Achse
# (er zeigt die Handarbeit im Dokument), Prozess-Diagnose zur Kaeufer-Achse
# (Reifegrad und Massnahmen sind eine Management-Bewertung). Vorher rotierte
# die Wahl persona-blind per LRU, dadurch trug ein Jae-Post den Reifegrad-Check.
# OFFEN (Jae pruefen): der Layout-Check rechnet die Kostenzeile erst nach
# Eingabe eines eigenen Stundensatzes. Zeigt er ohne diese Angabe kein
# brauchbares Ergebnis, bricht der Anwender-Pfad auf der Landingpage.
LEAD_MAGNETS = [
    {"id": "layout-check",
     "name": "Layout-Kosten-Rechner",
     "persona": "anwender",
     "problem": "nach jeder Uebersetzung geht dieselbe Handarbeit von vorne los: Rahmen anpassen, Umbrueche fixen, Ueberlaeufe suchen, pro Sprache und pro Version",
     "substance": "zwei PDF-Versionen desselben Dokuments (Quell- und Zielsprache) hochladen; die Analyse laeuft im Browser, Dateien bleiben lokal; Ergebnis: die gefundenen manuellen Layout-Eingriffe und eine Stunden-Schaetzung, auf Wunsch zusaetzlich Jahreskosten heute vs. automatisiert",
     "not_included": "kein Account noetig, keine Weitergabe der Dokumente, keine Kostenrechnung ohne eigene Stundensatz-Angabe",
     "cta": "Probieren Sie unseren Layout-Kosten-Rechner direkt im Browser: https://lnkd.in/dGACGzrs"},
    {"id": "prozess-diagnose",
     "name": "Übersetzungsmanagement-Stresstest",
     "persona": "kaeufer",
     "problem": "niemand im Team kann belegen, wie reif der mehrsprachige Dokumentenprozess wirklich ist",
     "substance": "10 Aussagen, rund 3 Minuten; Ergebnis: Reifegrad-Score 0-100, Zeitersparnis pro Projekt, Potenzial bei Korrekturschleifen, drei priorisierte Massnahmen",
     "not_included": "kein Audit-Ersatz, keine Tool-Empfehlungsliste; volle Ergebnisse erst nach Angabe der Business-E-Mail",
     "cta": "Probieren Sie unseren Übersetzungsmanagement-Stresstest direkt im Browser: https://in2go.io/diagnose/"},
]

# Aus der PERSONA-REGEL im CONTEXT strukturiert: genau EINE Achse pro Post.
#
# `axis` steuert die Persona-Klassifikation im Scoring (post_scorer._classify_section),
# `audience_de` / `decision_makers_de` / `focus_topics_de` ueberschreiben die
# gleichnamigen TOKENS im DE-Generierungs-Prompt. Ohne diese Felder schrieb der
# Prompt beiden Postern dieselbe Entscheider-Anweisung vor ("Schreibe fuer
# Entscheider ... Fokus auf Kosten-Relevanz") und zog Jaes Posts systematisch
# auf die Manager-Achse (Kundenfeedback 2026-07-29, Themen 2 und 5).
CONTENT_PERSONAS = [
    {
        "id": "kaeufer",
        "label": "Käufer/Entscheider (Marketing-/MarCom-Leitung, Geschäftsführung)",
        "share": "dominant",
        "axis": "Zeit und Kosten des GESAMTEN Übersetzungsprozesses (Budget, Durchlaufzeit über alle Sprachen, ROI, Gesamtprozess)",
        "audience_de": "Marketingleiter, MarCom-Direktoren und Geschäftsführung in produzierenden Unternehmen (500-10.000 MA) im deutschsprachigen Raum.",
        "decision_makers_de": "Marketing- und MarCom-Entscheider mit Budgetverantwortung für mehrsprachige Materialien",
        "focus_topics_de": "Zeit und Kosten des gesamten Übersetzungsprozesses: Durchlaufzeiten, versteckte DTP-Kosten, Skalierbarkeit über Sprachen",
        "pains": "versteckte DTP-Nacharbeit sprengt Budget und Timeline; Layout-Nacharbeit multipliziert sich mit jeder Zielsprache und steht in keinem Budget-Posten; Übersetzung läuft im Unternehmen nebenbei mit, unkoordiniert und unbudgetiert (VoC-verifiziert)",
        "kpis": "Kosten pro Sprachversion (Stunden x Sprachen x Korrekturrunden), Time-to-Market mehrsprachiger Materialien, Reklamationen wegen Layout-Fehlern",
        "vocabulary_use": "versteckte Kosten, DTP-Nacharbeit, Durchlaufzeit, ROI, Prozesskette, druckfertig, direkt im Layout",
        "vocabulary_avoid": "Toolbedienung, Feature-Details, Übersetzungsqualität als Thema",
        "scene_de": "ein Marketingleiter, der die Agentur-Rechnung liest und die DTP-Position zum ersten Mal hinterfragt",
        "scene_en": "a head of marketing reading the agency invoice and questioning the DTP line item for the first time",
        "cta_style": "reply",
    },
    {
        "id": "anwender",
        "label": "Anwender und Fach-Leads (DTP/Designer, Translation-Manager, technische Redakteure, Leiter Technische Dokumentation, Lokalisierungsverantwortliche)",
        "share": "secondary",
        "axis": "Zeitaufwand und Mühe der eigenen Layout- und Dokumentarbeit (Handgriffe, Korrekturschleifen, Abstimmungsaufwand)",
        "audience_de": "DTP- und Layout-Verantwortliche, Designer, Translation-Manager, technische Redakteure sowie Leiter Technische Dokumentation und Lokalisierung in produzierenden Unternehmen (500-10.000 MA) im deutschsprachigen Raum.",
        # Das Template haengt ", nicht fuer Marketer" an: hier keine zweite
        # Verneinung, sonst steht sie doppelt im Prompt.
        "decision_makers_de": "Praktiker, die die mehrsprachige Dokumentproduktion selbst machen",
        "focus_topics_de": "Arbeitserleichterung im eigenen Tagesgeschäft: Handgriffe pro Sprachversion, Korrekturschleifen, Abstimmungsaufwand mit der Übersetzungsagentur, Terminologie selbst absichern",
        "value_axis": "Der Post endet in weniger Arbeit, nie in einer Bewertung: weniger Handarbeit pro Sprachversion, weniger Korrekturschleifen, weniger Abstimmung mit der Übersetzungsagentur, schneller ausrollen, mit gleichem Budget mehr mehrsprachiges Material. Leitfrage ist 'wie mache ich mir die Arbeit leichter', nie 'wie reif ist unser Prozess'.",
        "pains": "übersetzte Texte Rahmen für Rahmen von Hand zurück ins Layout setzen (pro Sprache, pro Version, jedes Jahr wieder); PDF-Kommentar-Korrekturschleifen mit 3-4 Runden pro Dokument; Versionschaos zwischen Übersetzern und Layout (VoC-verifiziert)",
        "kpis": "Korrekturschleifen pro Dokument, Stunden Nacharbeit pro Sprache, Fehler nach Freigabe",
        "vocabulary_use": "Korrekturlauf, Lektorat im Browser, Versionen, Layout-Erhalt, Rahmen für Rahmen, Fremdsprachensatz",
        "vocabulary_avoid": "Budget- und ROI-Argumente (Käufer-Achse), Preise, Bewertungs- und Management-Rahmen (Reifegrad, Assessment, Prozess-Audit, Benchmark, Kennzahlen-Vergleich, Maturity)",
        "scene_de": "eine Designerin, die zum dritten Mal denselben Umbruch in zwölf Sprachversionen fixt",
        "scene_en": "a designer fixing the same line break in twelve language versions for the third time",
        "cta_style": "reply",
        # Anwender-Posts postet Jae — der DE-Prompt wechselt auf seine Stimme.
        "voice_de": "Du bist Jae Hyun Kim, Sales & Marketing bei lisocon (InTO: Übersetzung von InDesign-Dokumenten direkt im Original-Layout). Du arbeitest täglich mit Marketing-, Übersetzungs- und Doku-Teams, die in mehrsprachiger DTP-Nacharbeit versinken.",
    },
]
