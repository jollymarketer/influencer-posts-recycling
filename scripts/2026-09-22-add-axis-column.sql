-- Themenachse je Post (Spec 2026-09-22, jolly).
--
-- Nullable und additiv: bestehende Zeilen bleiben unberuehrt.
--
-- Zwei Spalten, nicht eine: "passt in keine Achse" ist ein gueltiges Ergebnis
-- des Klassifizierers und darf nicht mit "noch nicht klassifiziert"
-- verschmelzen. axis=null plus gesetztes axis_classified_at heisst entschieden,
-- axis_classified_at=null heisst offen. Ohne die Trennung bezahlt jeder
-- Backfill-Lauf dieselben Grenzfaelle erneut.
alter table blog_content_mining.influencer_posts
    add column if not exists axis text,
    add column if not exists axis_classified_at timestamptz;

create index if not exists influencer_posts_axis_idx
    on blog_content_mining.influencer_posts (client, axis);
