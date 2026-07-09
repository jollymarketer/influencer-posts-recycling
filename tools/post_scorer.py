"""
Post Scorer & Content Generator via Claude API.
- Bewertet Posts nach 5 Dimensionen inkl. Viralitaet (Engagement-Metriken)
- Generiert DACH-deutschen LinkedIn-Post + Bild-Prompt in einem Call
"""

import json
import math
import os
import re

import anthropic
from dotenv import load_dotenv

from clients import apply_tokens, load_client

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_cfg = load_client()

CLIENT_CONTEXT = _cfg.CONTEXT

SCORING_PROMPT = """[[SCORING_ROLE]]

KONTEXT:
{context}

Bewerte diesen LinkedIn-Post von {influencer} nach 5 inhaltlichen Kriterien (je 0-10 Punkte):

POST:
{post_text}

ENGAGEMENT-METRIKEN (bereits gemessen, nicht berechnen):
- Likes: {likes}
- Comments: {comments}
- Shares: {shares}

{diversity_section}

Bewertungskriterien:
1. topic_fit (0-10): [[TOPIC_FIT_QUESTION]]
2. icp_relevanz (0-10): [[ICP_RELEVANZ_QUESTION]]
3. recyclierbarkeit (0-10): Kann man daraus einen DACH-deutschen Thought-Leadership-Post machen? (starke These, konkretes Insight)
4. einzigartigkeit (0-10): Frisches Insight oder austauschbarer Allgemeinplatz?
5. themen_diversitaet (0-10): Wie unterschiedlich ist dieses Thema von den kuerzlich geposteten Inhalten? (10 = voellig anderes Thema, 0 = fast identisches Thema wurde kuerzlich gepostet). Falls keine Recent Posts vorhanden: 8 vergeben.

Antworte NUR mit validem JSON (kein Markdown, kein Text davor/danach):
{{"topic_fit": X, "icp_relevanz": X, "recyclierbarkeit": X, "einzigartigkeit": X, "themen_diversitaet": X, "reasoning": "1-2 Saetze warum dieser Score"}}"""
SCORING_PROMPT = apply_tokens(SCORING_PROMPT, _cfg)

DACH_POST_PROMPT = """[[PERSONA_DE]]

KONTEXT:
{context}
{persona_block}

Deine Aufgabe: Recycel den folgenden LinkedIn-Post von {influencer} in einen hochwertigen DACH-deutschen Thought-Leadership-Post.

ORIGINAL POST:
{post_text}

---

TEIL 1 - LINKEDIN POST (auf Deutsch):

Zielgruppe: [[AUDIENCE_DE]]

Tonalitaet:
- Schreibe fuer [[DECISION_MAKERS_DE]], nicht fuer Marketer
- Keine Fachbegriffe ohne Erklaerung. Wenn ein Begriff noetig ist (z.B. ICP = Idealer Zielkunde), erklaere ihn beim ersten Mal kurz
- Natuerlich und fluessig schreiben. Variiere Satzlaengen: kurze Saetze fuer Wirkung, laengere fuer Erklaerungen und Zusammenhaenge. Kein Stakkato-Stil mit nur abgehackten Einzelsaetzen. Der Text soll sich lesen wie ein kluger Mensch, der redet, nicht wie eine Bulletpoint-Liste
- Fokus auf [[FOCUS_TOPICS_DE]]
- Keine Buzzwords, kein Marketing-Sprech
- Ich-Form ([[FIRST_PERSON_ROLE_DE]]). Leichte, sparsame Direktansprache des Lesers ("du"/"ihr") ist erlaubt und erwuenscht, wo sie den Sog erhoeht
- [[CONTEXT_TRANSFER_DE]]
- Der Text soll hilfreich und menschlich rueberkommen, nicht wie AI-generierter Content

Sprach-Verbote (hart):
[[LANGUAGE_BANS_DE]]
- Nie die eigene Konstruktion offenlegen: verweise nie auf "das Original", "der Quell-Post", "der eigene Gedanke", "was im Original fehlt", "ich ergaenze". Den zusaetzlichen Gedanken einbauen, nie ankuendigen
- Keine erfundenen Belege: keine erfundenen Kundennamen, Umsatzzahlen, Fallstudien oder konkrete Einzelfall-Statistiken. Muster-Beobachtungen ("ich sehe oft, dass...") sind ok, erfundene Spezifika nicht
- Keine langen Striche: weder Em Dash (—) noch Halbgeviertstrich (–) als Gedankenstrich. Stattdessen Punkt, Doppelpunkt oder Komma. Normaler Bindestrich in Komposita bleibt erlaubt

Inhaltliche Regeln:
- Den Quell-Content erkennbar nutzen, aber als eigenstaendige Praxis-Einordnung - keine freie Neuinterpretation
- Einen eigenen, originellen Gedanken einbauen, den der Quell-Post nicht hat - ohne ihn als solchen zu benennen
- Haltung eines erfahrenen Praktikers: operative Details, Schrittfolgen, typische Stolpersteine, KPIs
- Genau EIN konkretes, scanbares Artefakt liefern, das man speichern will: nummerierte Schritte, eine kurze Checkliste, ein benanntes Framework oder eine harte Zahl. Als abgesetztes Element formatieren, nicht als Fliesstext-Beschreibung. Der Leser muss es in 2 Sekunden als Referenz erkennen. Im Story-Format stattdessen eine einzelne, klar benannte Regel oder Zahl, die haengen bleibt
- Eine falsche Praxis oder ein Feindbild explizit und hart benennen. Brave Ausgewogenheit ("X ist nicht Y, sondern Z") allein reicht nicht - es braucht eine klare Gegenposition, gegen die jemand argumentieren kann

{assets_block}
{structure_block}

Formatierung:
- Kein Markdown: keine **Sternchen** fuer Fettung, kein *kursiv*, keine #-Ueberschriften. LinkedIn rendert Markdown nicht, die Zeichen erscheinen woertlich im Post
- Absaetze duerfen 2-4 Saetze lang sein. Nicht jeder Satz ist ein eigener Absatz. Leerzeilen nur zwischen thematischen Bloecken, nicht nach jedem Satz
- Hoechstens EIN Formatierungselement auswaehlen (Story-Format: keines):
  * Emoji-Liste (mind. 3 gleichwertige Punkte): z.B. 📍 fuer Befunde, 👉 fuer Empfehlungen
  * Nummerierte Liste mit Unicode: ➊ ➋ ➌
  * GROSSBUCHSTABEN-Label fuer einen zentralen Abschnitt
  * ASCII-Box fuer einen Merksatz: ┌─────┐ │ Merksatz │ └─────┘
- Eine zugespitzte, eigenstaendige Zitat-Zeile auf eine eigene Zeile setzen (Screenshot- und Repost-faehig)
- Laenge: ca. 200 Woerter, max. 3.000 Zeichen

Qualitaetspruefung (E3):
- Evidence: Jede Kernaussage belegt durch Daten oder Beobachtung?
- Executable: Sofort umsetzbar ohne grosses Marketing-Team?
- Exclusive: Mind. 1 Gedanke den man so nicht ueberall findet?

[[HASHTAG_LINE_DE]]

---

TEIL 2 - SOUND BYTE:

Extrahiere aus dem generierten Post einen einzigen, kurzen, praegnanten Satz als Sound Byte fuer das Bild.

Regeln:
- Kein vollstaendiges Summary des Posts — kein erklaerungsbeduerftiger Satz
- Muss sofort haengen bleiben und eine Reaktion ausloesen
- Klingt wie ein starkes Zitat oder eine provokante These
- Maximal 12 Woerter
- Auf Deutsch (da der Post auf Deutsch ist)

TEIL 3 - KONTEXT (optional):

Fuer wen ist die Aussage besonders relevant? 1-2 Woerter Zielgruppe, z.B. "CEOs, RevOps-Teams" oder leer lassen.

---

TEIL 4 - INFOGRAFIK-SKELETT:

Basierend auf dem generierten Post: Empfehle den staerksten Infografik-Typ und liefere die Keywords fuer den Canva-Aufbau.

INFOGRAFIK-TYPEN (waehle den EINEN der zur Logik des Posts am besten passt):
- Vergleichstabelle: Zwei Spalten (z.B. "Was Leute denken" vs. "Was es wirklich ist")
- Funnel/Pyramide: 3-5 Ebenen mit Hierarchie (oben = Wichtigstes oder Ausgangspunkt)
- Eisberg: Sichtbare Spitze vs. verborgene Tiefe darunter
- Framework/Kreise: Konzentrische oder verschachtelte Ebenen
- Horizontaler Vergleich: Nebeneinander, gleichwertig
- Timeline/Sequenz: geordnete Schritte oder Phasen
- 2x2-Matrix: vier Quadranten aus zwei Achsen (z.B. Aufwand vs. Wirkung)
- Flywheel/Kreislauf: ein Zyklus, in dem jede Stufe die naechste speist
- Waage/Hebel: zwei Seiten gegeneinander abgewogen (Trade-off oder Ungleichgewicht)
- Vorher/Nachher-Split: ein Zustand vs. der veraenderte Zustand, nebeneinander
- Baum/Verzweigung: eine Wurzel, die sich in Aeste oder Ergebnisse teilt

Typ-Wahl-Regeln (Output ist aktuell viel zu monoton — das beheben):
- Typ an die echte Logik des Posts koppeln: Trade-off -> Waage, Prozess -> Funnel oder Timeline, zwei Denkweisen -> Vergleichstabelle, Zyklus -> Flywheel, zwei Achsen -> 2x2-Matrix.
- Eisberg ist stark ueberstrapaziert. Nur waehlen wenn es im Post wirklich um eine sichtbare Oberflaeche geht, die eine tiefere Realitaet verbirgt, und nichts anderes besser passt.
{recent_types_line}

Regeln:
- Keywords nicht Saetze (max. 3-4 Keywords pro Ebene/Spalte)
- 3-7 Elemente total, nicht mehr
- Komplementaritaet: Wenn Infografik das Problem zeigt beschreibt der Post-Text die Loesung; wenn Infografik die Struktur zeigt erklaert der Post-Text das Warum
- Keine Tool-Logos: das Bild bleibt logofrei (AI-Render verzerrt Marken). TOOL-LOGOS immer "keine"
- Visuelle Metapher nur empfehlen wenn sie den Kerngedanken wirklich verstaerkt (z.B. Bruecke fuer das Verbinden zweier Seiten, Domino-Kette fuer Kaskaden-Effekte, Hebel fuer ueberproportionale Wirkung). Nicht erzwingen.

OUTPUT-FORMAT (exakt einhalten):

===POST===
[LinkedIn-Post-Text auf Deutsch]

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4

===SOUNDBYTE===
[Sound Byte — ein Satz, max. 12 Woerter]

===KONTEXT===
[Zielgruppe/Kontext oder leer]

===INFOGRAFIK===
TYP: [Typ-Name]
METAPHER: [Visuelle Metapher oder "keine"]
KOMPLEMENTARITAET: [Infografik zeigt X → Post-Text erklaert Y]
EBENEN:
[Label 1]: [Keyword 1], [Keyword 2], [Keyword 3]
[Label 2]: [Keyword 1], [Keyword 2], [Keyword 3]
[Label 3]: [Keyword 1], [Keyword 2], [Keyword 3]
TOOL-LOGOS: keine"""
# PERSONA_DE wird erst zur Generierungszeit gefuellt: der Persona-Split kann
# die Stimme wechseln (voice_de in CONTENT_PERSONAS, z.B. lisocon: Anwender-
# Posts in Jaes Stimme). Ohne Override bleibt TOKENS["PERSONA_DE"].
DACH_POST_PROMPT = apply_tokens(
    DACH_POST_PROMPT.replace("[[PERSONA_DE]]", "{persona_voice}"), _cfg
)

EN_POST_PROMPT = """[[PERSONA_EN]]

CONTEXT:
{context}
{persona_block}

Your task: recycle the following LinkedIn post by {influencer} into a high-quality, native English thought-leadership post. Write it natively in English — do NOT translate German phrasing or sentence structure. Same core thesis, your own added thought, but it must read like it was written in English from scratch.

ORIGINAL POST:
{post_text}

---

PART 1 - LINKEDIN POST (in English):

Audience: [[AUDIENCE_EN]]

Tone:
- Write for [[WRITE_FOR_EN]].
- No jargon without explanation. If a term is needed (e.g. ICP = ideal customer profile), define it briefly on first use.
- Natural, fluid writing. Vary sentence length: short sentences for impact, longer ones for explanation and context. No choppy staccato of single-sentence lines. It should read like a smart person talking, not a bullet list.
- Focus on [[FOCUS_TOPICS_EN]].
- No buzzwords, no marketing-speak.
- No long dashes: never use an em dash (—) or en dash (–) as a sentence break. Use a period, colon or comma instead. Normal hyphens in compounds are fine.
- First person ([[FIRST_PERSON_ROLE_EN]]). Light, natural use of "you" toward the reader is fine.
- The post should feel helpful and human, not AI-generated.

Content rules:
- Use the source content recognizably, but as your own practitioner's framing — not a free reinterpretation.
- Add one original thought the source post does not have — without flagging it as such.
- Never expose your own construction: never reference "the original", "the source post", "my own added thought", "what's missing". Build the thought in, never announce it.
- No fabricated proof: no invented client names, revenue numbers, case studies or specific single-case statistics. Pattern observations ("I often see...") are fine, invented specifics are not.
- Stance of an experienced operator: operational detail, sequencing, common pitfalls, KPIs.
- Deliver exactly ONE concrete, scannable artifact worth saving: numbered steps, a short checklist, a named framework or a hard number. Format it as a set-apart element, not buried in prose. The reader must recognize it as a reference in 2 seconds. In the Story format, instead give one clearly named rule or number that sticks.
- Name one wrong practice or enemy explicitly and hard. A balanced "X is not Y, it's Z" alone is not enough — there must be a clear counter-position someone can argue against.

{assets_block}
{structure_block}

Formatting:
- No Markdown: no **asterisks** for bold, no *italics*, no # headings. LinkedIn does not render Markdown, the characters appear literally in the post.
- Paragraphs may be 2-4 sentences. Not every sentence is its own paragraph. Blank lines only between thematic blocks.
- Pick at most ONE formatting element (Story format: none):
  * Emoji list (at least 3 equal items): e.g. 📍 for findings, 👉 for recommendations
  * Numbered list with Unicode: ➊ ➋ ➌
  * ALL-CAPS label for one central section
  * ASCII box for a key takeaway: ┌─────┐ │ takeaway │ └─────┘
- Put one sharp, standalone quote line on its own line (screenshot- and repost-friendly).
- Length: ~200 words, max 3,000 characters.

Quality check (E3):
- Evidence: is each core claim backed by data or observation?
- Executable: immediately actionable without a big marketing team?
- Exclusive: at least one thought you would not find everywhere?

[[HASHTAG_LINE_EN]]

---

PART 2 - SOUND BYTE:

Extract from the generated post a single short, sharp sound byte for the image.

Rules:
- Not a summary of the post — no sentence that needs explaining.
- Must stick instantly and provoke a reaction.
- Sounds like a strong quote or a provocative thesis.
- Maximum 12 words.
- In English (the post is in English).

PART 3 - CONTEXT (optional):

For whom is the statement most relevant? 1-2 words audience, e.g. "CEOs, RevOps teams", or leave blank.

---

PART 4 - INFOGRAPHIC SKELETON:

Based on the generated post: recommend the strongest infographic type and provide the keywords for the Canva build.

INFOGRAPHIC TYPES (pick the ONE that matches the post's logic best):
- Comparison table: two columns (e.g. "What people think" vs. "What it really is")
- Funnel/pyramid: 3-5 levels with hierarchy (top = most important or starting point)
- Iceberg: visible tip vs. hidden depth below the surface
- Framework/circles: concentric or nested levels
- Horizontal comparison: side by side, equal weight
- Timeline/sequence: ordered steps or stages
- 2x2 matrix: four quadrants from two axes (e.g. effort vs. impact)
- Flywheel/loop: a cycle where each stage feeds the next
- Scale/seesaw: two sides weighed against each other (a trade-off or imbalance)
- Before/after split: one state vs. the changed state, side by side
- Tree/branching: one root splitting into branches or outcomes

Type-selection rules (the output is currently far too monotone — fix that):
- Match the type to the post's real logic: a trade-off -> scale, a process -> funnel or timeline, two mindsets -> comparison table, a cycle -> flywheel, two axes -> 2x2 matrix.
- Iceberg is heavily overused. Choose it ONLY when the post is genuinely about a visible surface hiding a deeper reality, and nothing else fits better.
{recent_types_line}

Rules:
- Keywords not sentences (max 3-4 keywords per level/column)
- 3-7 elements total, no more
- Complementarity: if the infographic shows the problem, the post text describes the solution; if the infographic shows the structure, the post text explains the why
- No tool logos: the image stays logo-free (the AI render distorts brands). TOOL-LOGOS is always "none"
- Recommend a visual metaphor only when it genuinely reinforces the core idea (e.g. a bridge for connecting two sides, a domino chain for cascading effects, a lever for outsized impact). Do not force one.

OUTPUT FORMAT (follow exactly):

IMPORTANT: Reproduce the section headers (===POST===, ===SOUNDBYTE===, ===KONTEXT===, ===INFOGRAFIK===) and the field labels (TYP, METAPHER, KOMPLEMENTARITAET, EBENEN, TOOL-LOGOS) EXACTLY as written below, character for character. Do NOT translate or rename them, even though some are German — an automated parser depends on these exact strings. Only the content you fill in is in English.

===POST===
[LinkedIn post text in English]

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4

===SOUNDBYTE===
[Sound byte — one sentence, max 12 words]

===KONTEXT===
[Audience/context or blank]

===INFOGRAFIK===
TYP: [type name]
METAPHER: [visual metaphor or "none"]
KOMPLEMENTARITAET: [infographic shows X -> post text explains Y]
EBENEN:
[Label 1]: [keyword 1], [keyword 2], [keyword 3]
[Label 2]: [keyword 1], [keyword 2], [keyword 3]
[Label 3]: [keyword 1], [keyword 2], [keyword 3]
TOOL-LOGOS: none"""
EN_POST_PROMPT = apply_tokens(EN_POST_PROMPT, _cfg)


FORMAT_STRUCTURES = {
    "Opinion": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Eine kontroverse These oder ein Gegen-Befund zu einer gaengigen Praxis. Entscheidet ob jemand weiterliest.
2. Spannung: Was die meisten Teams glauben oder tun - und warum das in der Praxis nicht traegt. Konkret, nicht abstrakt.
3. Position: Deine Gegenposition als erfahrener Praktiker, begruendet aus Beobachtung. Max 3-5 Belege oder Schritte. Ein eigener Gedanke der im Original nicht vorkommt.
4. Abschluss: Offene Schleife statt sauberem Punkt. Entweder eine spezifische, streitbare Frage zur Kern-These, oder eine Flag-Plant-Zeile, gegen die jemand Position beziehen kann. Verboten ist nur das generische "Was denkst du?". Kein DM-CTA.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): a contrarian thesis or counter-finding against a common practice. Decides whether anyone reads on.
2. Tension: what most teams believe or do - and why it does not hold up in practice. Concrete, not abstract.
3. Position: your contrarian take as an experienced operator, reasoned from observation. Max 3-5 proofs or steps. One original thought not in the source.
4. Close: an open loop, not a clean full stop. Either a specific, arguable question on the core thesis, or a flag-plant line someone can take a stand against. Only the generic "What do you think?" is banned. No DM CTA.""",
    },
    "POV": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Benenne eine Denk-Linse oder ein Reframe das die Zielgruppe so noch nicht hatte. Entscheidet ob jemand weiterliest.
2. Framework: 2-4 benannte Bestandteile eines Modells, mit dem man das Problem klarer sieht. Konkret, nicht abstrakt.
3. Anwendung: Wie man die Linse in der Praxis nutzt. Max 3-5 Schritte. Ein eigener Gedanke der im Original nicht vorkommt.
4. Abschluss: Offene Schleife statt sauberem Punkt. Entweder eine spezifische, streitbare Frage zur Kern-These, oder eine Flag-Plant-Zeile, gegen die jemand Position beziehen kann. Verboten ist nur das generische "Was denkst du?". Kein DM-CTA.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): name a lens or reframe the audience did not have yet. Decides whether anyone reads on.
2. Framework: 2-4 named parts of a model that makes the problem clearer. Concrete, not abstract.
3. Application: how to use the lens in practice. Max 3-5 steps. One original thought not in the source.
4. Close: an open loop, not a clean full stop. Either a specific, arguable question on the core thesis, or a flag-plant line someone can take a stand against. Only the generic "What do you think?" is banned. No DM CTA.""",
    },
    "Signature": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): "Was [[BELIEF_ACTORS_DE]] glauben:" - die verbreitete Annahme, zugespitzt. Entscheidet ob jemand weiterliest.
2. Realitaet: Was tatsaechlich das Ergebnis treibt - im Kontrast zur Annahme. Konkret, nicht abstrakt.
3. Kontraste: 2-4 Glaube-gegen-Realitaet-Paare, je knapp. Ein eigener Gedanke der im Original nicht vorkommt.
4. Abschluss: Offene Schleife. Eine spezifische, streitbare Frage oder eine Flag-Plant-Zeile, die das Operating-Principle zuspitzt und gegen die jemand argumentieren kann. Verboten ist nur das generische "Was denkst du?". Kein DM-CTA.
Hinweis fuer die Infografik weiter unten: Bevorzuge die Vergleichstabelle (Glaube vs. Realitaet).""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): "What [[BELIEF_ACTORS_EN]] believe:" - the common assumption, sharpened. Decides whether anyone reads on.
2. Reality: what actually drives the outcome, in contrast to the assumption. Concrete, not abstract.
3. Contrasts: 2-4 belief-vs-reality pairs, each tight. One original thought not in the source.
4. Close: an open loop. A specific, arguable question or a flag-plant line that sharpens the operating principle and that someone can argue against. Only the generic "What do you think?" is banned. No DM CTA.
Note for the infographic section below: prefer the comparison table (belief vs. reality).""",
    },
    "Story": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Steig mitten in eine konkrete Szene ein - ein Satz, den [[SCENE_ACTOR_DE]] sinngemaess sagt, oder ein Moment aus der Praxis. Entscheidet ob jemand weiterliest.
2. Spannung: Wie die Szene sich entwickelt und wo der eigentliche Konflikt sitzt. Erzaehlend, keine Bullet-Liste, keine Box.
3. Wendung: Die Erkenntnis aus der Szene, die das Muster sichtbar macht. Ein eigener Gedanke, den der Quell-Post nicht hat.
4. Abschluss: Offene Schleife - eine spezifische, streitbare Frage oder eine Flag-Plant-Zeile. Verboten ist nur das generische "Was denkst du?". Kein DM-CTA.
Erfinde dabei keine konkreten Namen, Umsatzzahlen oder Fallstudien. Eine generische, plausible Szene ohne erfundene Spezifika - oder ein erkennbares Muster ("ich sehe das oft") statt eines erfundenen Einzelfalls. Dieses Format nutzt KEINE Emoji-Liste und KEINE ASCII-Box.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): drop into a concrete scene - a line [[SCENE_ACTOR_EN]] would say, or a moment from practice. Decides whether anyone reads on.
2. Tension: how the scene unfolds and where the real conflict sits. Narrative, no bullet list, no box.
3. Turn: the realization from the scene that exposes the pattern. One original thought the source post does not have.
4. Close: an open loop - a specific, arguable question or a flag-plant line. Only the generic "What do you think?" is banned. No DM CTA.
Do not invent specific names, revenue figures or case studies. A generic, plausible scene without fabricated specifics - or a recognizable pattern ("I see this often") instead of an invented single case. This format uses NO emoji list and NO ASCII box.""",
    },
    "Comparison": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Der Entscheidungs-Moment - jemand steht vor der Wahl von [[COMPARISON_SUBJECT_DE]] und waehlt nach den falschen Kriterien. Entscheidet ob jemand weiterliest.
2. Entscheidungskriterien: 3-5 harte Kriterien oder Red Flags als scanbares Artefakt (das ist das eine Artefakt dieses Posts). Jedes Kriterium konkret pruefbar, keine Allgemeinplaetze.
3. Einordnung: Wann welche Option wirklich passt - inklusive mindestens einem ehrlichen Fall, in dem die eigene Kategorie NICHT die richtige Wahl ist. Kein Wettbewerber-Bashing, keine Namen.
4. Abschluss: Offene Schleife - eine spezifische, streitbare Frage zur Entscheidungslogik oder eine Flag-Plant-Zeile. Verboten ist nur das generische "Was denkst du?". Kein DM-CTA.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): the decision moment - someone choosing [[COMPARISON_SUBJECT_EN]] using the wrong criteria. Decides whether anyone reads on.
2. Decision criteria: 3-5 hard criteria or red flags as the scannable artifact of this post. Each one concretely checkable, no platitudes.
3. Placement: when each option genuinely fits - including at least one honest case where your own category is NOT the right choice. No competitor bashing, no names.
4. Close: an open loop - a specific, arguable question about the decision logic, or a flag-plant line. Only the generic "What do you think?" is banned. No DM CTA.""",
    },
    "Method": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Das Ergebnis oder der Engpass, den die Methode adressiert - konkret, nicht abstrakt. Entscheidet ob jemand weiterliest.
2. Methode: 3-5 nummerierte Schritte (➊ ➋ ➌) als das eine scanbare Artefakt. Jeder Schritt eine Handlung mit erkennbarem Output, keine Theorie.
3. Stolperstein: Der eine Punkt, an dem Teams in der Praxis scheitern, und wie man ihn umgeht. Ein eigener Gedanke, den der Quell-Post nicht hat. Vorher-Nachher nur qualitativ - keine erfundenen Zahlen.
4. Abschluss: Offene Schleife - eine spezifische, streitbare Frage zur Methode oder eine Flag-Plant-Zeile. Verboten ist nur das generische "Was denkst du?". Kein DM-CTA.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): the outcome or bottleneck the method addresses - concrete, not abstract. Decides whether anyone reads on.
2. Method: 3-5 numbered steps (➊ ➋ ➌) as the one scannable artifact. Each step an action with a visible output, no theory.
3. Pitfall: the one point where teams fail in practice and how to avoid it. One original thought the source post does not have. Before/after only qualitative - no invented numbers.
4. Close: an open loop - a specific, arguable question about the method, or a flag-plant line. Only the generic "What do you think?" is banned. No DM CTA.""",
    },
    "CaseProof": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Die Ergebnis-Zahl aus dem CASE-ASSET unten, im Kontext des Problems. Entscheidet ob jemand weiterliest.
2. Ausgangslage: Wo das Unternehmen vorher stand und warum der Status quo teuer war. Konkret, ohne erfundene Details.
3. Weg: Was konkret veraendert wurde (Methode, Reihenfolge, Entscheidung) - als kurzes scanbares Artefakt. Ein eigener Gedanke, den der Quell-Post nicht hat.
4. Abschluss: Das Learning als uebertragbare Regel plus offene Schleife (streitbare Frage oder Flag-Plant-Zeile). Kein DM-CTA.
Harte Zahlen-Regel: JEDE Zahl mit Einheit (Prozent, Euro, x-fach) stammt woertlich aus dem CASE-ASSET-Block. Keine weiteren Zahlen erfinden, auch keine plausiblen. Firmenname nur wenn im Asset genannt. Keine anderen Referenzen oder Kundennamen nennen, auch keine anderen freigegebenen Cases.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): the result number from the CASE ASSET below, framed by the problem. Decides whether anyone reads on.
2. Starting point: where the company stood before and why the status quo was expensive. Concrete, no invented detail.
3. Path: what concretely changed (method, sequence, decision) - as a short scannable artifact. One original thought the source post does not have.
4. Close: the learning as a transferable rule plus an open loop (arguable question or flag-plant line). No DM CTA.
Hard numbers rule: EVERY unit-bearing number (percent, currency, x-times) is taken verbatim from the CASE ASSET block. Invent no further numbers, not even plausible ones. Company name only if the asset names it. Name no other references or client cases, not even other approved ones.""",
    },
    "Debate": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Eine polarisierende Entweder-Oder-These, bei der sich beide Lager sofort angesprochen fuehlen. Entscheidet ob jemand weiterliest.
2. Zwei Lager: Beide Positionen kurz und fair in je 2-3 Saetzen - so, dass Vertreter beider Seiten sich wiedererkennen. Konkret, nicht abstrakt.
3. Eigene Position: Auf welcher Seite du stehst und der eine Beleg aus der Praxis. Ein eigener Gedanke, den der Quell-Post nicht hat.
4. Abschluss: Explizite Aufforderung, sich in den Kommentaren fuer ein Lager zu entscheiden und die Wahl zu begruenden. Das ist der Kern dieses Formats. Kein DM-CTA, keine Umfrage-Mechanik ausserhalb der Kommentare.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): a polarizing either-or thesis both camps instantly react to. Decides whether anyone reads on.
2. Two camps: both positions short and fair, 2-3 sentences each - so members of either side recognize themselves. Concrete, not abstract.
3. Your position: which camp you are in and the one proof from practice. One original thought the source post does not have.
4. Close: an explicit prompt to pick a camp in the comments and justify the pick. That prompt is the point of this format. No DM CTA, no poll mechanics outside the comments.""",
    },
    "Magnet": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Das Problem, das das LEAD-MAGNET-ASSET unten loest - aus der Praxis, nicht als Werbetext. Entscheidet ob jemand weiterliest.
2. Substanz-Vorschau: 3-5 konkrete Punkte aus dem Artefakt als scanbares Element - genug Wert, dass der Post auch ohne Download traegt. Keine leeren Teaser.
3. Einordnung: Fuer wen das Artefakt gedacht ist und was es NICHT ist (Erwartungen ehrlich setzen). Ein eigener Gedanke, den der Quell-Post nicht hat.
4. Abschluss: Genau EIN Kommentar-CTA mit dem Keyword aus dem LEAD-MAGNET-ASSET (z.B. "Kommentiere KEYWORD, ich schicke es dir"). Kein DM-CTA daneben, kein kuenstlicher Zeitdruck, keine Follower-Bedingung.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): the problem the LEAD MAGNET ASSET below solves - from practice, not ad copy. Decides whether anyone reads on.
2. Substance preview: 3-5 concrete points from the artifact as the scannable element - enough value that the post stands without the download. No empty teasers.
3. Placement: who the artifact is for and what it is NOT (set expectations honestly). One original thought the source post does not have.
4. Close: exactly ONE comment CTA using the keyword from the LEAD MAGNET ASSET (e.g. "Comment KEYWORD and I'll send it over"). No DM CTA next to it, no fake scarcity, no follow-gate.""",
    },
    "Offer": {
        "de": """Post-Struktur (ohne explizite Benennung):
1. Hook (1-2 Saetze): Das Ergebnis, das das OFFER-ASSET unten verspricht, verankert im Problem der Zielgruppe. Kein Marktschreier-Ton. Entscheidet ob jemand weiterliest.
2. Passung: Fuer wen das Angebot gebaut ist (2-3 harte Fit-Kriterien) und fuer wen explizit nicht. Ehrlichkeit ist der Differenzierer.
3. Inhalt: Was konkret drinsteckt - 3-4 Punkte als scanbares Artefakt, Ablauf oder Bestandteile. Ein eigener Gedanke, warum JETZT der richtige Zeitpunkt ist (Markt-Logik, kein Druck).
4. Abschluss: Genau EIN CTA, woertlich aus dem OFFER-ASSET (DM oder Discovery-Call). Kein kuenstlicher Zeitdruck, keine erfundene Verknappung, keine Fake-Slots. Preise nur wenn im Asset genannt.""",
        "en": """Post structure (without labeling it):
1. Hook (1-2 sentences): the outcome the OFFER ASSET below promises, anchored in the audience's problem. No carnival-barker tone. Decides whether anyone reads on.
2. Fit: who the offer is built for (2-3 hard fit criteria) and who it is explicitly not for. Honesty is the differentiator.
3. Contents: what is concretely inside - 3-4 points as the scannable artifact, sequence or components. One original thought on why NOW is the right time (market logic, no pressure).
4. Close: exactly ONE CTA, taken verbatim from the OFFER ASSET (DM or discovery call). No fake scarcity, no invented urgency, no fake slots. Pricing only if the asset states it.""",
    },
}
FORMAT_STRUCTURES = {
    fmt: {lang: apply_tokens(text, _cfg) for lang, text in variants.items()}
    for fmt, variants in FORMAT_STRUCTURES.items()
}


def _recent_types_lines(recent_infographic_types) -> tuple[str, str]:
    """Baut die DE/EN Anti-Repeat-Zeile fuer den Infografik-Typ. Leere Liste -> ("", "")."""
    recent = [t for t in (recent_infographic_types or []) if t]
    if not recent:
        return "", ""
    joined = ", ".join(recent)
    de = (f"- Zuletzt genutzte Typen (neuestes zuerst): {joined}. "
          f"Vermeide jeden Typ aus den letzten 3 Runs, ausser er passt klar am besten.")
    en = (f"- Types used in recent posts (newest first): {joined}. "
          f"Avoid any type from the last 3 runs unless it is clearly the best fit.")
    return de, en


def _format_prompts(post: dict, post_format: str = "Opinion",
                    recent_infographic_types=None,
                    assets_de: str = "", assets_en: str = "",
                    persona_de: str = "", persona_en: str = "",
                    persona_voice_de: str = "") -> tuple[str, str]:
    """Pure builder: returns (de_prompt, en_prompt) with the format structure,
    the infographic anti-repeat line, and optional persona/asset blocks
    injected. persona_voice_de overrides the DE author voice (Persona-Split);
    empty falls back to TOKENS["PERSONA_DE"]. Unknown format keys fall back
    to Opinion. No API calls."""
    structures = FORMAT_STRUCTURES.get(post_format, FORMAT_STRUCTURES["Opinion"])
    de_recent, en_recent = _recent_types_lines(recent_infographic_types)
    de = DACH_POST_PROMPT.format(
        context=CLIENT_CONTEXT,
        influencer=post["influencer"],
        post_text=post["post_text"][:3000],
        structure_block=structures["de"],
        recent_types_line=de_recent,
        persona_block=persona_de,
        assets_block=assets_de,
        persona_voice=persona_voice_de or _cfg.TOKENS["PERSONA_DE"],
    )
    en = EN_POST_PROMPT.format(
        context=CLIENT_CONTEXT,
        influencer=post["influencer"],
        post_text=post["post_text"][:3000],
        structure_block=structures["en"],
        recent_types_line=en_recent,
        persona_block=persona_en,
        assets_block=assets_en,
    )
    return de, en


# Kanonische Infografik-Typen — fuer ein sauberes Notion-Select + verlaessliches
# Anti-Repeat. Roh-TYP des LLM wird per Keyword-Match auf einen Kanon abgebildet.
INFOGRAPHIC_TYPE_CANON = [
    ("Comparison table", ("comparison", "vergleichstabelle", "table", "tabelle")),
    ("Funnel/pyramid", ("funnel", "pyramid", "pyramide", "trichter")),
    ("Iceberg", ("iceberg", "eisberg")),
    ("Framework/circles", ("framework", "circle", "kreis")),
    ("Horizontal comparison", ("horizontal",)),
    ("Timeline", ("timeline", "sequence", "sequenz", "zeitstrahl")),
    ("2x2 matrix", ("matrix", "quadrant", "2x2")),
    ("Flywheel/loop", ("flywheel", "loop", "cycle", "kreislauf", "zyklus")),
    ("Scale/seesaw", ("scale", "seesaw", "waage", "hebel", "balance")),
    ("Before/after", ("before", "after", "vorher", "nachher")),
    ("Tree/branching", ("tree", "branch", "baum", "verzweig")),
]


def parse_infographic_type(skeleton: str) -> str:
    """Liest den rohen TYP-Wert aus einem Infografik-Skelett (TYP: ...). '' wenn keiner."""
    for line in (skeleton or "").splitlines():
        s = line.strip()
        if s.upper().startswith("TYP:"):
            return s.split(":", 1)[1].strip()
    return ""


def normalize_infographic_type(raw: str) -> str:
    """Bildet einen rohen TYP-String per Keyword-Match auf einen kanonischen Typ ab.
    Kein Match -> der gestrippte Roh-Wert (gekappt), damit Anti-Repeat trotzdem greift."""
    r = (raw or "").strip().lower()
    if not r:
        return ""
    for canon, keywords in INFOGRAPHIC_TYPE_CANON:
        if any(k in r for k in keywords):
            return canon
    return (raw or "").strip()[:40]


VALID_FORMATS = ("Opinion", "POV", "Signature", "Story")

# Kurzbeschreibung je Format fuer den Auswahl-Prompt.
FORMAT_PICK_DESCRIPTIONS = {
    "Opinion": "kontroverse These gegen eine gaengige Praxis.",
    "POV": "eine strukturierte Denk-Linse / ein Framework.",
    "Signature": '"Glaube vs. Realitaet" - verbreitete Annahme gegen das was wirklich zaehlt.',
    "Story": "eine konkrete Szene oder Anekdote aus der Praxis, erzaehlend statt Liste.",
    "Comparison": "Entscheidungshilfe: harte Kriterien und Red Flags fuer eine Auswahl.",
    "Method": "Schritt-fuer-Schritt-Methode mit dem typischen Stolperstein.",
    "CaseProof": "echtes Kundenergebnis, getragen von einer belegten Zahl.",
    "Debate": "polarisierende Entweder-Oder-These, die explizit zur Antwort auffordert.",
    "Magnet": "wertvolles Artefakt mit Kommentar-CTA.",
    "Offer": "konkretes Angebot mit ehrlichem naechsten Schritt.",
}

PICK_FORMAT_PROMPT = """Du waehlst das Post-Format fuer einen Recycling-Post.

Verfuegbare Formate:
{format_menu}

QUELL-POST:
{post_text}

{recent_section}

Regeln:
- Waehle das Format das am besten zum Thema des Quell-Posts passt.
- Das zuletzt genutzte Format ist verboten (nie zweimal hintereinander).
- Antworte mit EINEM Wort: {format_names}. Nichts sonst."""


def pick_format(post: dict, recent_formats: list[str],
                candidates: list[str] | None = None) -> str:
    """Waehlt das Format unter den Kandidaten: bester Topic-Fit, aber nie das
    zuletzt genutzte Format. candidates=None -> die 4 Legacy-Formate.
    Genau EIN Kandidat (Pflicht-Box) -> direkt zurueck, ohne API-Call und
    ohne Anti-Repeat (Quota schlaegt Wiederholungs-Regel).
    Faellt deterministisch zurueck und wirft nie."""
    candidates = list(candidates) if candidates else list(VALID_FORMATS)
    if len(candidates) == 1:
        return candidates[0]

    recent_formats = [f for f in recent_formats if f]
    most_recent = recent_formats[0] if recent_formats else None

    if recent_formats:
        recent_section = (
            f"Zuletzt genutzte Formate (neuestes zuerst): {', '.join(recent_formats)}. "
            f"VERBOTEN ist: {most_recent}."
        )
    else:
        recent_section = "Zuletzt genutzte Formate: keine."

    format_menu = "\n".join(
        f"- {f}: {FORMAT_PICK_DESCRIPTIONS.get(f, '')}" for f in candidates
    )
    try:
        prompt = PICK_FORMAT_PROMPT.format(
            format_menu=format_menu,
            post_text=post["post_text"][:3000],
            recent_section=recent_section,
            format_names=", ".join(candidates),
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        choice = response.content[0].text.strip()
        for f in candidates:
            if f.lower() in choice.lower() and f != most_recent:
                return f
    except Exception as e:
        print(f"  Format-Pick fehlgeschlagen, Fallback: {e}")

    for f in candidates:
        if f != most_recent:
            return f
    return candidates[0]


RANK_BOX_FIT_PROMPT = """Du pruefst, welcher Quell-Post am besten ein bestimmtes Content-Format tragen kann.

ZIEL-BOX: {job} x {stage}
ZIEL-FORMAT(E): {formats} - {format_desc}

KANDIDATEN (nummeriert):
{numbered_posts}

Bewerte je Kandidat mit fit 0-10: Wie gut laesst sich aus DIESEM Quell-Post ein Post im Ziel-Format machen? 10 = der Quell-Post liefert die Struktur praktisch mit, 0 = passt gar nicht.

Antworte NUR mit validem JSON (kein Markdown):
[{{"index": 0, "fit": X}}, {{"index": 1, "fit": X}}, ...]"""


def rank_box_fit(scored_posts: list, box, formats: list, min_fit: int = 6):
    """Re-rankt die Top-Kandidaten auf Tauglichkeit fuer die Pflicht-Box.
    Gibt den Index des besten Posts mit fit >= min_fit zurueck, sonst None.
    Jeder Fehler -> None (Run faellt auf freien Best-Fit zurueck)."""
    if not scored_posts:
        return None
    try:
        numbered = "\n".join(
            f"[{i}] ({p['influencer']}) {p['post_text'][:400]}"
            for i, p in enumerate(scored_posts)
        )
        prompt = RANK_BOX_FIT_PROMPT.format(
            job=box[0], stage=box[1],
            formats=", ".join(formats),
            format_desc=" / ".join(FORMAT_PICK_DESCRIPTIONS.get(f, "") for f in formats),
            numbered_posts=numbered,
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        ranking = json.loads(raw)
        best_index, best_fit = None, min_fit - 1
        for entry in ranking:
            idx, fit = int(entry["index"]), int(entry["fit"])
            if 0 <= idx < len(scored_posts) and fit > best_fit:
                best_index, best_fit = idx, fit
        return best_index
    except Exception as e:
        print(f"  Box-Fit-Rank fehlgeschlagen (Fallback: freier Run): {e}")
        return None


PERSONA_BLOCK_DE = """ZIEL-PERSONA fuer diesen Post (genau EINE Persona, deren Wertachse nie mit einer anderen mischen):
- Rolle: {label}
- Schmerzpunkte: {pains}
- KPIs die zaehlen: {kpis}
- Vokabular nutzen: {vocabulary_use}
- Vokabular meiden: {vocabulary_avoid}
- Typische Szene: {scene}"""

PERSONA_BLOCK_EN = """TARGET PERSONA for this post (exactly ONE persona, never mix its value axis with another):
- Role: {label}
- Pains: {pains}
- KPIs that matter: {kpis}
- Vocabulary to use: {vocabulary_use}
- Vocabulary to avoid: {vocabulary_avoid}
- Typical scene: {scene}"""


def persona_block(persona, lang: str) -> str:
    """Persona-Linse fuer den Generierungs-Prompt. None/leer -> ""."""
    if not persona:
        return ""
    template = PERSONA_BLOCK_DE if lang == "de" else PERSONA_BLOCK_EN
    return template.format(
        label=persona.get("label", ""),
        pains=persona.get("pains", ""),
        kpis=persona.get("kpis", ""),
        vocabulary_use=persona.get("vocabulary_use", ""),
        vocabulary_avoid=persona.get("vocabulary_avoid", ""),
        scene=persona.get("scene_de" if lang == "de" else "scene_en", ""),
    )


_ASSET_BLOCK_HEADERS = {
    "CaseProof": ("CASE-ASSET (einzige erlaubte Zahlenquelle, Zahlen woertlich uebernehmen)",
                  "CASE ASSET (the only allowed source of numbers, use them verbatim)"),
    "Magnet": ("LEAD-MAGNET-ASSET (dieses Artefakt bewirbt der Post, CTA-Keyword woertlich nutzen)",
               "LEAD MAGNET ASSET (the artifact this post promotes, use the CTA keyword verbatim)"),
    "Offer": ("OFFER-ASSET (dieses Angebot bewirbt der Post, CTA woertlich uebernehmen)",
              "OFFER ASSET (the offer this post promotes, use the CTA verbatim)"),
}


def assets_block(post_format: str, asset, lang: str) -> str:
    """Asset-Whitelist-Block fuer CaseProof/Magnet/Offer. Sonst ""."""
    if not asset or post_format not in _ASSET_BLOCK_HEADERS:
        return ""
    header = _ASSET_BLOCK_HEADERS[post_format][0 if lang == "de" else 1]
    lines = [f"- {k}: {v}" for k, v in asset.items() if isinstance(v, str) and v]
    return header + ":\n" + "\n".join(lines)


PICK_PERSONA_PROMPT = """Du waehlst die Ziel-Persona fuer einen LinkedIn-Post.

PERSONAS:
{persona_menu}

QUELL-POST:
{post_text}

Regel: Waehle die Persona, deren Schmerzpunkte der Quell-Post am direktesten trifft. Im Zweifel: {dominant_id}.
Antworte NUR mit der id, nichts sonst."""


def pick_persona(post: dict, cfg, recent_personas: list):
    """v1-Persona-Wahl: Best-Fit zum Quell-Post, im Zweifel dominante Persona,
    dieselbe Sekundaer-Persona nie zweimal hintereinander. Wirft nie.
    Mandant ohne CONTENT_PERSONAS -> None (statische Audience-Tokens gelten)."""
    personas = getattr(cfg, "CONTENT_PERSONAS", None) or []
    if not personas:
        return None
    by_id = {p["id"]: p for p in personas}
    dominant = next((p for p in personas if p.get("share") == "dominant"), personas[0])
    if len(personas) == 1:
        return dominant

    choice_id = dominant["id"]
    try:
        menu = "\n".join(
            f"- {p['id']}: {p['label']} | Schmerzpunkte: {p['pains']}" for p in personas
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{"role": "user", "content": PICK_PERSONA_PROMPT.format(
                persona_menu=menu,
                post_text=post["post_text"][:2000],
                dominant_id=dominant["id"],
            )}],
        )
        raw = response.content[0].text.strip().lower()
        for pid in by_id:
            if pid in raw:
                choice_id = pid
                break
    except Exception as e:
        print(f"  Persona-Pick fehlgeschlagen, Fallback dominant: {e}")

    chosen = by_id[choice_id]
    # Sekundaer-Persona nie zweimal in Folge.
    if (chosen["id"] != dominant["id"] and recent_personas
            and recent_personas[0] == chosen["id"]):
        return dominant
    return chosen


IMAGE_PROMPT_TEMPLATE = """Create a premium LinkedIn square image (1:1) for [[BRAND_NAME]] that communicates the core idea of the post through one clear, strategically strong visual concept.

Core message:
{core_message}

Optional context:
{context}

Language for all visible text in the image:
{language}

Objective:
Create a scroll-stopping LinkedIn featured image that is understood within 1 to 2 seconds on mobile.
The image should communicate one core idea fast and clearly, not explain an entire framework.

Brand direction:
[[IMAGE_BRAND_DIRECTION]]

[[IMAGE_BRAND_RULES]]

Creative discipline:

Reduce the message to one dominant visual idea
Use one primary visual logic only
Prefer one focal scene, one focal metaphor, or one strong visual mechanism
Design for feed impact first, explanation second
If the concept becomes busy, simplify aggressively
Prioritize compression over completeness
The image should feel like a premium editorial social visual, not a workshop slide or business explainer

Concept selection:
First interpret the message, then choose the strongest visual direction for this specific post.
Possible directions include:

editorial poster
symbolic metaphor
clean comparison
minimal typographic concept
conceptual business illustration
Choose only one primary direction and execute it clearly.
Do not combine multiple competing concepts.

Simplicity and clarity rules:

Maximum 2 to 4 major visual elements in the whole composition
One dominant focal point, or one focal point per side only if a comparison is absolutely necessary
Remove anything that does not strengthen the idea immediately
No clutter
No filler objects
No busy scenes
No over-detailed environments
The concept must still read clearly as a small LinkedIn thumbnail

Text discipline:

Use one strong headline only
Headline must be integrated into the composition
Headline: ultra-bold, maximum 4 to 6 words
Optional support line only if truly necessary, maximum 4 to 8 words
Avoid labels, captions, side notes, repeated text, and explanatory copy by default
Every word in the image must earn its place

Typography:

Use [[IMAGE_TYPOGRAPHY]] typography
Typography should feel compact, modern, premium, and highly legible
Avoid weak generic fonts, serif fonts, or presentation-style text layouts

Composition:

Build the image around one clear focal point
Create strong hierarchy and reading flow
Use whitespace intentionally, but do not let the image feel empty or unfinished
The composition should feel designed, not templated

Avoid:

generic stock-business visuals
bland SaaS social graphics
infographic clutter
workshop-slide aesthetics
multiple explanatory sections
too many icons or symbols
literal over-explanation
decorative clutter
chaotic comparison layouts

Final check:

Is the core idea instantly clear?
Is there only one dominant visual concept?
Is the image understandable within 1 to 2 seconds?
Is the text minimal and strong?
Is it still clear at mobile thumbnail size?
Does it feel premium and brand-consistent?

Output:
A premium LinkedIn featured image that expresses one clear strategic idea fast, cleanly, and memorably."""
IMAGE_PROMPT_TEMPLATE = apply_tokens(IMAGE_PROMPT_TEMPLATE, _cfg)


INFOGRAPHIC_PROMPT_TEMPLATE = """Create a premium, clean LinkedIn infographic (vertical 4:5 or square) for [[BRAND_NAME]] that renders the layers below as a single, instantly readable visual.

Layout style: {layout}
{metaphor_line}
ONLY the following layers and their keywords may appear as visible text. Render them EXACTLY as written in {language}, no translation, no extra words, no title, no type name, no meta labels:

{layers}

Objective:
A save-worthy LinkedIn infographic. The reader should grasp the structure in 2 to 3 seconds and want to save it as a reference. Structure over decoration.

Layout logic:
- Iceberg: one large iceberg with a clear waterline; the first layer sits above water, the deeper layers stack below in descending depth. Most important hidden layer at the bottom.
- Funnel/pyramid: stacked horizontal bands narrowing top-to-bottom (or bottom-to-top), one layer per band.
- Comparison table: two clean columns, one header per column, aligned rows.
- Framework/circles: concentric or nested circles, one layer per ring.
- Horizontal comparison: equal-weight blocks side by side.
- Timeline/sequence: ordered nodes connected along a single line, each node one layer, clear direction.
- 2x2 matrix: four quadrants formed by one horizontal and one vertical axis, one layer per quadrant, axis ends lightly implied.
- Flywheel/loop: layers arranged around a circle with arrows showing the cycle direction.
- Scale/seesaw: a balance beam with the contrasted layers placed on each side.
- Before/after split: the canvas divided in two, the prior state on one side and the changed state on the other.
- Tree/branching: a root at the top or left branching out into the deeper layers.

Each layer shows its label as a short bold heading plus its keywords as a tight list. Keywords stay keywords, never full sentences.

[[INFOGRAPHIC_BRAND_RULES]]

Hard rules:
- No brand, tool, or company logos anywhere in the image. No logo row, no tool chips.
- No title text, no infographic-type name (like "Eisberg" or "Funnel"), no metaphor word rendered as a label.

Composition:
- One clear vertical reading flow, strong hierarchy, generous whitespace between layers.
- Reserve clean empty space in the bottom-right corner for a logo overlay (no text or graphic there).
- It must still read clearly at LinkedIn thumbnail size.

Avoid: clutter, decorative icons that add no meaning, busy backgrounds, more than 3 colors, full sentences, tiny unreadable text, chaotic layouts.

Final check: Is the structure instantly clear? Are all {language} labels spelled correctly? Are there zero logos and zero title/type text? Is the bottom-right corner clear for the logo?"""
INFOGRAPHIC_PROMPT_TEMPLATE = apply_tokens(INFOGRAPHIC_PROMPT_TEMPLATE, _cfg)


def build_infographic_prompt(skeleton: str, language: str = "German") -> str:
    """
    Baut aus dem strukturierten Infografik-Skelett (TYP/METAPHER/EBENEN/TOOL-LOGOS,
    erzeugt von generate_post_and_image_prompt) einen kie.ai-Bild-Prompt fuer eine
    echte gerenderte Infografik. Gibt "" zurueck wenn kein Skelett vorhanden ist.

    Nur die EBENEN werden als sichtbarer Text gerendert. TYP steuert das Layout,
    METAPHER nur die visuelle Richtung. Keine Tool-Logos, kein Titel/Typ-Name im Bild.
    """
    skeleton = (skeleton or "").strip()
    if not skeleton:
        return ""

    layout = ""
    metaphor = ""
    layers: list[str] = []
    in_ebenen = False
    for line in skeleton.splitlines():
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("TYP:"):
            layout = stripped.split(":", 1)[1].strip()
            in_ebenen = False
        elif upper.startswith("METAPHER:"):
            metaphor = stripped.split(":", 1)[1].strip()
            in_ebenen = False
        elif upper.startswith("KOMPLEMENTARIT") or upper.startswith("TOOL-LOGOS:"):
            in_ebenen = False
        elif upper.startswith("EBENEN:"):
            in_ebenen = True
        elif in_ebenen and stripped:
            layers.append(stripped)

    # Ohne Ebenen kein verlaesslicher Bild-Aufbau.
    if not layers:
        return ""

    metaphor_line = (
        f"Visual direction (do NOT render this word as text): {metaphor}" if metaphor else ""
    )
    return INFOGRAPHIC_PROMPT_TEMPLATE.format(
        layout=layout or "structured stacked layers",
        metaphor_line=metaphor_line,
        language=language,
        layers="\n".join(layers),
    )


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


def score_posts(posts: list, recent_drafts: list[str] | None = None) -> list:
    """
    Bewertet Posts nach 6 Dimensionen: 5 inhaltliche (KI) + Viralitaet (Metriken).
    Dimension 5: Themen-Diversitaet — bevorzugt Themen die kuerzlich nicht gepostet wurden.
    Max. Score: 60 Punkte.
    """
    scored = []

    # Diversity-Kontext fuer den Prompt vorbereiten
    if recent_drafts:
        excerpts = "\n".join(f"- {d[:200]}" for d in recent_drafts)
        diversity_section = f"""KUERZLICH GEPOSTETE INHALTE (letzten 7 Posts — fuer Themen-Diversitaet):
{excerpts}

Vermeide Themen-Wiederholungen. Bevorzuge Posts die thematisch neue Perspektiven bieten."""
    else:
        diversity_section = "KUERZLICH GEPOSTETE INHALTE: Keine vorhanden."

    for post in posts:
        # Viralitaet direkt aus Engagement-Metriken
        engagement = post.get("engagement", {"likes": 0, "comments": 0, "shares": 0})
        virality_score = calculate_virality_score(engagement)

        try:
            prompt = SCORING_PROMPT.format(
                context=CLIENT_CONTEXT,
                influencer=post["influencer"],
                post_text=post["post_text"][:3000],
                likes=engagement.get("likes", 0),
                comments=engagement.get("comments", 0),
                shares=engagement.get("shares", 0),
                diversity_section=diversity_section,
            )
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
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
                + scores.get("themen_diversitaet", 8)
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


def sanitize_generated_text(text: str) -> str:
    """Deterministische Nachbereitung der LLM-Drafts (Kundenfeedback lisocon 2026-07-08).
    Prompt-Verbote allein halten nicht zuverlaessig:
    - Markdown-Sternchen: LinkedIn rendert kein Markdown, **fett** erscheint woertlich
    - Em/En-Dash als Gedankenstrich liest als KI-Signal -> Komma;
      Zahlenbereiche behalten einen normalen Bindestrich, Strich-Bullets werden "- "
    """
    text = text.replace("**", "")
    text = re.sub(r"(?m)^([ \t]*)[—–][ \t]+", r"\1- ", text)
    text = re.sub(r"(?<=\d)[ \t]*[—–][ \t]*(?=\d)", "-", text)
    text = re.sub(r"[ \t]*[—–][ \t]*", ", ", text)
    return text


def _append_cta(text: str, cta: str) -> str:
    """Haengt den Mandanten-CTA (CTA_DE/CTA_EN in der Client-Config) ganz unten an."""
    if not cta or not text:
        return text
    return text.rstrip() + "\n\n" + cta


GRAMMAR_CHECK_PROMPT = """Du bist ein praeziser deutscher Korrektor. Pruefe den folgenden LinkedIn-Post ausschliesslich auf Grammatik-, Rechtschreib-, Artikel- und Kasusfehler und korrigiere sie minimal-invasiv.

HARTE REGELN:
- Aendere NUR echte Fehler. Stil, Wortwahl, Tonalitaet, Satzbau, Emojis, Zeilenumbrueche, Sonderzeichen-Listen und Hashtags bleiben exakt unveraendert.
- Englische Fachbegriffe im deutschen Text sind kein Fehler; korrigiere nur inkonsistente Artikel oder Deklination drumherum.
- Wenn nichts zu korrigieren ist, gib den Text ZEICHENGENAU unveraendert zurueck.
- Antworte NUR mit dem Text selbst: kein Kommentar, keine Erklaerung, kein Markdown.

TEXT:
{text}"""


def grammar_check(text: str) -> str:
    """Letzte Stufe der Texterstellung (FEATURES["grammar_check"], Kundenfeedback
    lisocon 2026-07-09: Artikel-/Kasusfehler wie "Fehlender Tool Support").
    Minimal-invasive LLM-Korrektur; non-fatal und mit Laengen-Guard, damit ein
    ausufernder Umbau des Posts nie den Draft ersetzt."""
    if not text or not _cfg.FEATURES.get("grammar_check"):
        return text
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": GRAMMAR_CHECK_PROMPT.format(text=text)}],
        )
        fixed = resp.content[0].text.strip()
    except Exception as e:
        print(f"  Grammar-Check fehlgeschlagen (nicht kritisch): {e}", flush=True)
        return text
    if not fixed or abs(len(fixed) - len(text)) > max(80, int(len(text) * 0.15)):
        print("  Grammar-Check verworfen (Laengen-Guard).", flush=True)
        return text
    if fixed != text:
        print("  Grammar-Check: Korrekturen uebernommen.", flush=True)
    return fixed


def _parse_generation_response(raw: str) -> dict:
    """Zerlegt eine LLM-Antwort an den ===MARKER=== in ihre Teile.
    Gibt dict mit keys post, soundbyte, kontext, infografik zurueck.
    Fehlt ===POST===, gilt der ganze Text als post (Fallback).
    Erwartet bereits gestrippten Input (Callsites strippen die LLM-Antwort)."""
    parts = {"post": "", "soundbyte": "", "kontext": "", "infografik": ""}

    if "===POST===" in raw:
        post_part = raw.split("===POST===")[1]
        parts["post"] = (
            post_part.split("===SOUNDBYTE===")[0].strip()
            if "===SOUNDBYTE===" in post_part
            else post_part.strip()
        )
    else:
        parts["post"] = raw.strip()

    if "===SOUNDBYTE===" in raw:
        sb = raw.split("===SOUNDBYTE===")[1]
        parts["soundbyte"] = (
            sb.split("===KONTEXT===")[0].strip()
            if "===KONTEXT===" in sb
            else sb.split("===INFOGRAFIK===")[0].strip()
            if "===INFOGRAFIK===" in sb
            else sb.strip()
        )

    if "===KONTEXT===" in raw:
        kp = raw.split("===KONTEXT===")[1]
        parts["kontext"] = (
            kp.split("===INFOGRAFIK===")[0].strip()
            if "===INFOGRAFIK===" in kp
            else kp.strip()
        )

    if "===INFOGRAFIK===" in raw:
        parts["infografik"] = raw.split("===INFOGRAFIK===")[1].strip()

    return parts


def generate_post_and_image_prompt(post: dict, post_format: str = "Opinion",
                                   recent_infographic_types=None,
                                   assets_de: str = "", assets_en: str = "",
                                   persona_de: str = "", persona_en: str = "",
                                   persona_voice_de: str = "") -> tuple[str, str, str, str, str, str]:
    """Generiert DE-Post (DACH-Prompt) + nativen EN-Post (EN-Prompt).
    Mit FEATURES["en_draft"]=False (lisocon, GTM-Call 2026-07-09) entfaellt der
    EN-Call komplett; Soundbyte/Kontext/Infografik-Skelett kommen dann aus dem
    DE-Response (der DACH-Prompt liefert sie auf Deutsch), en_draft ist "".
    Die Bild-Text-Sprache steuert IMAGE_LANGUAGE der Client-Config.
    post_format waehlt den Struktur-Block (Opinion/POV/Signature).
    recent_infographic_types steuert das Anti-Repeat des Infografik-Typs.
    assets_de/assets_en und persona_de/persona_en sind vorgefertigte Prompt-
    Bloecke (siehe assets_block/persona_block), Default "" bleibt wirkungslos.
    persona_voice_de wechselt die DE-Autorenstimme (Persona-Split).
    Gibt (de_draft, en_draft, image_prompt, infographic_skeleton, soundbyte, kontext)
    zurueck. soundbyte/kontext speisen den Bild-Archetyp-Router (image_archetypes).
    """
    de_prompt, en_prompt = _format_prompts(
        post, post_format, recent_infographic_types,
        assets_de=assets_de, assets_en=assets_en,
        persona_de=persona_de, persona_en=persona_en,
        persona_voice_de=persona_voice_de,
    )

    de_resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": de_prompt}],
    )
    de_parts = _parse_generation_response(de_resp.content[0].text.strip())
    de_draft = grammar_check(sanitize_generated_text(de_parts["post"]))
    de_draft = _append_cta(de_draft, getattr(_cfg, "CTA_DE", ""))

    if _cfg.FEATURES.get("en_draft", True):
        en_resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": en_prompt}],
        )
        en_parts = _parse_generation_response(en_resp.content[0].text.strip())
        en_draft = _append_cta(sanitize_generated_text(en_parts["post"]),
                               getattr(_cfg, "CTA_EN", ""))
        image_parts = en_parts
    else:
        en_draft = ""
        image_parts = de_parts

    sound_byte = sanitize_generated_text(image_parts["soundbyte"])
    kontext = image_parts["kontext"]
    infographic_skeleton = image_parts["infografik"]

    image_prompt = ""
    if sound_byte:
        image_prompt = IMAGE_PROMPT_TEMPLATE.format(
            core_message=sound_byte,
            context=kontext or _cfg.TOKENS["DEFAULT_AUDIENCE_IMAGE"],
            language=getattr(_cfg, "IMAGE_LANGUAGE", "English"),
        )

    return de_draft, en_draft, image_prompt, infographic_skeleton, sound_byte, kontext
