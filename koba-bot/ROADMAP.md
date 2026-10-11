# KOBA Bot — Roadmap

Per `Full_261010_215649.txt` (2026-10-10), Project 2B.

## Relationship to the existing `~/Desktop/kobabot` repo — read this first

This document describes a **future target architecture**, not the current
codebase. The real, shipping bot at `~/Desktop/kobabot/` (rebranded from
"BoomBot" on 2026-10-11 — boombot is the old/retired name) is architecturally
the *opposite* of what's specced here: it owns a local SQLite database,
real in-process economy/roster/crafting logic, and Stripe billing. This
spec calls for a bot that is completely "dumb" — zero local database
tables, zero game-specific state math, every interaction forwarded to
`koba-core` which computes the response and hands back a pre-rendered
embed.

**Per explicit user direction (2026-10-11): no code migration is happening
now.** This roadmap documents where `kobabot` may eventually move toward
once `koba-core` and `koba-discord-app` exist for real, not an immediate
rewrite. The single biggest reconciliation task before any real migration
starts is deciding what happens to `kobabot`'s existing local economy/
roster/licensing data — this spec assumes that state lives in `koba-core`'s
Postgres layer instead, which is a real data-migration project of its own,
not just a refactor.

## Scope

The user-facing command mapping modules, autocomplete engines, and
multi-channel layout engines for both **KOBA Bot** and **KOBA Plus**. Holds
zero heavy computation — every slash command or dashboard button forwards
immediately to `koba-core` (Project 1), which computes the response and
returns a pre-styled embed for this layer to print.

## Current state

**Spec-only** as the architecture described here. (The *existing*,
differently-architected `kobabot` is real and shipping — see note above.)

## Dependencies

Runs inside the `koba-discord-app` process (shares its dual-token login
manager). Forwards every interaction to `koba-core`'s Universal Command
Router. Both must exist first for this to function.

## Roadmap

1. **Master clean slash command specification** — player core commands
   (`/claim`, `/shop`, `/play`, `/coins [balance|send]`, `/progression`,
   `/challenge`, `/lfg`, `/support`, `/commands`), clan/warfare (`/clan
   [create|manage|leave]`, `/war [declare|end]`), identity (`/link`,
   `/unlink` with platform/gamertag/web-verification-code flow).
2. **Decoupled universal interface routing ("Option A" shape-shifting)** —
   forward every interaction's context to `koba-core`, print back whatever
   pre-rendered embed comes back without local modification (Rust Console
   → Green/Kits/Dial-a-Ride layout, DayZ → Cyan/Medical-Supplies layout,
   same parent command either way); admin/config buttons hide themselves
   contextually from regular players.
3. **Multi-channel advanced log generator & feeds** — dynamic
   (DB-config-driven, not hardcoded) channel routing for killfeeds, raid
   alerts, item-note feeds, ORP/ZORP state, event feeds (cargo ship/crates/
   supply drops), and per-server + global admin-spawn transparency feeds.
4. **Staff discipline subcommand trees + owner-only nuke** — `/config
   [shops|casino|games|feeds]` (Admin+), `/set [roles|baseline]`, `/setup
   [wizard|repair|template]`, `/mod [warning|strike]` (the 3-strike
   router), server-owner-only `/server [add|remove|status]`, `/staff
   [post|review]`, and `/nuke` (Absolute Platform Zero, gated behind a
   mandatory multi-step confirmation panel).
5. **Developer-only commands (official KOBA HQ server only)** — `/license
   [activate|manage|transfer]`, `/globalban`, `/globalunban`,
   `/bypass-cooldown`, `/directory-setup`, `/activate-user`,
   `/ad-message-config` — hard-gated to never appear or function outside
   the official server.
6. **Core brand visual language system** — KOBA Green/Cyan/Gold/Danger-Red
   embed color system, near-black/graphite/thin-border layout constraints
   (no glow effects), SQUAD/STANDARD_CLAN/ZERG group-size labeling wired
   to `koba-core`'s thresholds.

## Suggested repo

Either a new `koba-bot` repo (distinct from the existing `kobabot`), or —
once the migration question above is resolved — the eventual successor
codebase for `kobabot` itself.
