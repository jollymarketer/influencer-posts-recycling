-- scripts/setup_topic_pool_tables.sql
-- Topic candidate pool for the lisocon slate model (spec 2026-07-16).
create table if not exists blog_content_mining.topic_candidates (
    post_url        text primary key,
    client          text not null,
    source          text not null default '',
    influencer      text not null default '',
    post_text       text not null default '',
    post_date       date,
    likes           int  not null default 0,
    comments        int  not null default 0,
    shares          int  not null default 0,
    persona         text not null default '',
    matrix_job      text not null default '',
    matrix_stage    text not null default '',
    voc_hit         text not null default '',
    topic_angle_de  text not null default '',
    score_total     int  not null default 0,
    scores          jsonb,
    reasoning       text not null default '',
    state           text not null default 'pool',
    times_slated    int  not null default 0,
    first_seen_at   timestamptz not null default now(),
    last_scored_at  timestamptz,
    last_slated_at  timestamptz
);
create index if not exists topic_candidates_client_state_idx
    on blog_content_mining.topic_candidates (client, state);

create table if not exists blog_content_mining.engine_meta (
    key   text primary key,
    value text not null default ''
);
