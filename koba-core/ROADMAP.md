# KOBA Core — Roadmap

**Not to be confused with**: the earlier "KOBA Core" entry in
[../KOBA_PLATFORM_PROJECT_SCOPING.md](../KOBA_PLATFORM_PROJECT_SCOPING.md),
which referred to the Oxide/Carbon C# Rust plugin. That project has been
renamed **[KOBA PC Plugin](../koba-pc-plugin/ROADMAP.md)** to free up the
`koba-core` name for this one — the master web application, per
`Full_261010_215649.txt` (2026-10-10), Project 1.

## Scope

The centralized "master brain" of the KOBA competitive gaming social
network (koba.games) — a Next.js web application shell, the core database
layer, the secure KOBA Server Adapter Ingestion Pipeline, the
administrative/disciplinary engines, and the centralized command routing
APIs that service the decoupled Discord clients (`koba-discord-app`,
`koba-bot`) and PC plugin (`koba-pc-plugin`). Built for deployment on a
GoDaddy Plesk VPS.

Brand constraints: near-black backgrounds (`--bg:#07080b`), graphite
panels, thin dark borders; KOBA Green (`#7cff4f`) for success, Cyan
(`#43d9ff`) for metadata/clans, Gold (`#ffc857`) for rewards, Danger Red
(`#ff4f67`) for discipline/errors — professional/data-driven tone, no
glow effects or generic SaaS gradients.

## Current state

**Spec-only.** No Next.js project, database schema, or API routes exist
yet anywhere in the inspected repos.

## Dependencies

None upstream — this is the system everything else (the PC plugin, the
Discord connection client, the bot) talks to. It does depend on at least
one real "game adapter" definition existing to be useful end-to-end
(`RUST_CONSOLE` is the obvious first target, matching the existing real
work in `kobabot`/`koba-pc-plugin`).

## Roadmap

1. **Database layer** (`src/lib/db.ts`) — the 7 core models: `koba_identities`
   (KOBAid, Master KOBA Score, form state, badges), `koba_linked_accounts`
   (one-master-link-per-footprint across Discord/Steam/Xbox/PSN),
   `koba_guild_game_adapters` (per-guild paid game scope + license status),
   `koba_server_feed_channels` (killfeed/raid/note/ORP-ZORP/admin-spawn
   channel routing), `koba_clan_profiles` (SQUAD 1-4 / STANDARD_CLAN 5-8 /
   ZERG 9-20+ tiers), `koba_player_homes` (max 3, float coords),
   `koba_discipline_matrix` (3-strike + blacklist state).
2. **Centralized Universal Command Router** (`src/app/api/v1/interactions/route.ts`)
   — ingest universal slash-command payloads, resolve the guild's paid game
   scope, dynamically render game-specific embeds (Rust Console in Green,
   DayZ in Cyan) off the *same* parent command, gate execution behind a
   verified KOBAid link.
3. **Secure KOBA Server Adapter Ingestion Pipeline** — the 4 verification
   gates (host key → plugin signature → sanity/rate check → identity
   mapping) for raw WebRCON/WebSocket event packets; provisional caching
   for packets that pass signature/sanity but fail host/identity checks;
   historical back-dating when an account later links or a server verifies.
4. **Three-Strike Disciplinary & Blacklist Engine** — Level 1 Mod (max 1
   warning), Level 2 Admin (max 3 strikes, immutable audit log, 3rd strike
   locks profile to `UNDER_REVIEW`), Level 3 Master Developer (sole
   authority to remove a strike or commit a permanent multi-identifier
   blacklist); full restoration path that doesn't wipe historical data.
5. **Persistent app shell frontend** — Next.js App Router layout (sidebar:
   Home/Discover/Rivals/Challenges/Clans, profile card w/ live rank +
   score delta), global cross-game search, Home workspace (Live Mutation
   Feed, Form Trend Matrix), mobile-responsive table-to-card collapse.

## Suggested repo

`koba-core` (new repo, or this directory if kept inside `koba-platform`
during early spec-to-code work).
