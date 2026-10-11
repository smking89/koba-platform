# KOBA Discord App — Roadmap

Per `Full_261010_215649.txt` (2026-10-10), Project 2.

## Scope

A lightweight, hyper-optimized Node.js/TypeScript app hosted alongside
`koba-core` on the same GoDaddy Plesk VPS. Manages the live, authenticated
WebRCON connections to multiple game servers and hosts the dual-login
process for both **KOBA Bot** (in-server economy/game engine, see
[../koba-bot/ROADMAP.md](../koba-bot/ROADMAP.md)) and **KOBA Plus** (a mini
global-lookup helper bot). Must remain completely "dumb" — zero business
logic, zero local database storage, zero data calculation — purely an
execution/listening/rendering client, to avoid memory leaks across
hundreds of concurrent server connections.

## Current state

**Spec-only.** No code exists yet.

## Dependencies

Needs `koba-core`'s ingestion-pipeline and interaction-router endpoints to
exist (or at least a stable contract) to be useful end-to-end, since every
packet and interaction it handles gets forwarded there. Hosts the runtime
that `koba-bot` logs in through.

## Roadmap

1. **Multi-tenant WebRCON WebSocket manager** (`src/core/WebRCONManager.ts`)
   — isolated connection slots per server (own socket, own auth, own
   status), strict server-id/guild-id tagging on every packet at ingestion
   time, resilient heartbeat/auto-reconnect with back-off (survives
   G-Portal/Nitrado restarts without throwing), rolling dedup cache to
   prevent replayed-packet double-fires, WebRCON passwords fully hidden
   from logs/embeds/output.
2. **Decoupled KOBA Bot & KOBA Plus login manager** — single Node.js
   runtime booting and maintaining both bot client tokens off one shared
   codebase.
3. **Real-time console feed parser & forwarder** — ingest the raw
   `public.log` stream, regex-prefilter for high-signal events (joins/
   leaves, chat commands, combat/death lines, item notes, admin spawns),
   hand off unparsed candidate strings to `koba-core`'s ingestion pipeline;
   anything that doesn't match a known format gets logged to a debug file
   and dropped, never blocks the network thread.
4. **Centralized interaction pipeline (webhook forwarder)** — intercept
   every slash command/button interaction, package a clean JSON payload
   (`guild_id`, `discord_user_id`, command, params), POST it to `koba-core`
   over local loopback, await the pre-rendered embed/string response and
   print it instantly with no local modification.

## Suggested repo

`koba-discord-app` (new repo, or this directory during early spec-to-code
work).
