# KOBA PC Plugin — Roadmap

Per `Full_261010_215649.txt` (2026-10-10), Project 3 (`koba-pc-plugin`,
plugin file `KobaCore.cs`).

**Naming note**: this is the project previously called "KOBA Core" in
[../KOBA_PLATFORM_PROJECT_SCOPING.md](../KOBA_PLATFORM_PROJECT_SCOPING.md)
(the Oxide/uMod + Carbon C# Rust plugin). Renamed here to avoid colliding
with the new Project 1, which claims the `koba-core` name for the master
web application — see [../koba-core/ROADMAP.md](../koba-core/ROADMAP.md).

## Scope

A standalone, server-side C# background plugin (`KobaCore.cs`) compiled
natively by Oxide/uMod or Carbon on PC Rust servers. Functions as a silent,
high-performance background data-ingestion and cryptographic-verification
pipeline — overrides native server hooks to translate real-time in-game
events into tamper-proof, signed data rows pushed to `koba-core`'s
ingestion pipeline over WebRCON. **Zero player commands, zero admin
commands** — completely invisible in-game; all profile/economy/moderation
UX lives in the Discord layer (`koba-discord-app` / `koba-bot`) and the
`koba.games` web platform (`koba-core`).

## Current state

**Spec-only.** No C#/Oxide/Carbon code exists in any inspected repo. Same
real blocker noted elsewhere in this platform's docs: no licensed Rust
server/Carbon-Oxide dev environment has been verified in this environment
yet — step 1 below is a hard precondition for everything after it.

## Dependencies

`koba-core`'s Server Adapter Ingestion Pipeline must accept this plugin's
exact signed-payload format (its Gate 2 signature check validates against
this plugin's HMAC key) — the two need to agree on a wire format before
either side can be tested end-to-end, even as stubs.

## Roadmap

1. **Automated installation & key handling** — verify real Carbon/Oxide
   compile-on-drop lifecycle, auto-generate `KobaCore.json` config
   (`KobaServerID`, `KobaVerificationKey` supplied via the koba.games
   install-link flow), confirm hot-reload applies config changes without
   a full server restart.
2. **Cryptographic payload signing contracts** — unencrypted, readable
   event fields (lean network overhead) + HMAC/SHA256 `plugin_signature`
   over every payload keyed by `KobaVerificationKey`; push signed JSON
   down the WebRCON pipe; anything that fails signature verification at
   the `koba-core` adapter is dropped as a forgery.
3. **Combat resolution hooking** — `OnPlayerDeath` (or equivalent)
   interception; capture attacker/victim SteamID64 (string-typed to avoid
   numeric corruption), usernames, weapon shortname, distance, hit zone,
   PvE flag.
4. **Structural damage & raid hooking** — `OnEntityTakeDamage`
   interception filtered strictly to tool cupboards + external walls (to
   protect server tick rate); on explosive-weapon damage, capture
   attacker SteamID64, building-owner SteamID64, damage values, entity
   shortnames — feeds the platform's raid-alert and ORP/ZORP calculations.
5. **Automated marketplace asset licensing** — startup handshake to
   `api.koba.games/v1/assets/validate` with `KobaServerID`/
   `KobaVerificationKey`; stream and write authorized custom assets
   (maps, event scripts, monuments) only on successful validation; drop
   silently on failure or detected unlicensed distribution.

## Suggested repo

`koba-pc-plugin` (new repo, or this directory during early spec-to-code
work).
