-- scripts/blog_content_mining_schema.sql
-- Apply via Supabase SQL editor or `supabase db execute`. One-time.
create schema if not exists blog_content_mining;

create table if not exists blog_content_mining.influencer_posts (
    post_url    text primary key,
    source      text not null,            -- 'linkedin' | 'substack'
    influencer  text,
    post_text   text,
    post_date   date,
    likes       integer default 0,
    comments    integer default 0,
    shares      integer default 0,
    scraped_at  timestamptz not null default now()
);

create index if not exists influencer_posts_post_date_idx
    on blog_content_mining.influencer_posts (post_date);

-- PostgREST exposes non-public schemas only if listed. Add the schema:
--   Dashboard -> Settings -> API -> Exposed schemas -> add "blog_content_mining"
-- (or set db.schemas in config). Required for the REST wrapper to reach it.
