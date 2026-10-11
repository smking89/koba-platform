# KOBA Platform — Project Scoping

Source material: the 22 spec `.txt` files in `~/Desktop/koba pc engine stuff/`,
plus the source of `~/Desktop/kobabot/` (the KOBA Bot Discord bot), plus
`~/Desktop/new things /Full_261010_215649.txt` (2026-10-10), a concrete
4-project architecture doc covering `koba-core`, `koba-discord-app`,
`koba-bot`, and `koba-pc-plugin` — see §3-6.

Decision already made by the user (not re-litigated here): split the
platform into separate projects along KOBA's named sub-brands, not along a
simple "engine vs content" axis. This document proposes the project list,
grounded in what each spec doc actually says and what code/assets actually
exist today — not invented scope.

**2026-10-11 descope**: the user confirmed they will **not** be building any
of the monument/skin content products (Casino & Resort, Ferry Terminal,
Yachts, Theme Park, Quarry, MOBO, Submarine, World Events, the Building Skin
System). Those sections have been removed from this document rather than
kept as "not pursuing" filler.

**2026-10-11, second correction**: **KOBA Creator Engine has nothing to do
with this project.** It's a standalone repo (`~/Desktop/koba_creator_engine/`)
with its own separate scope and its own `ROADMAP.md` — it does not belong in
the koba-platform umbrella and has been removed from this document entirely.
Don't re-add it here.

**2026-10-11, third correction**: **KOBA Live is removed** — stale/old, per
the user. Not part of this repo's active scope.

The active KOBA platform scope tracked in this repo is: **KOBA Bot**,
**KOBA Core**, **KOBA Discord App**, **KOBA PC Plugin**, **KOBA Adaptive
Capacity**, **KOBAid**, and **KOBA Creator Ecosystem**.

---

## 1. Dependency / sequencing diagram

```
KOBA Bot (existing, real code today — future migration target toward the
  dumb-client architecture below, see §2; no code change happening yet)

NEW CONCRETE ARCHITECTURE (per Full_261010_215649.txt, 2026-10-10 — spec-only, all 4 greenfield)
  koba-core (web "master brain": Next.js app, DB, ingestion pipeline, discipline engine)
     │
     ├── koba-discord-app (dumb WebRCON/connection client, hosts both bot logins) ──┐
     │        │                                                                      │
     │        └── koba-bot (dumb slash-command client, forwards everything to core) │
     │                                                                               │
     └── koba-pc-plugin (Oxide/Carbon C# plugin, signs + forwards game events) ─────┘
          (was called "KOBA Core" before this doc existed — renamed to avoid
           colliding with the new koba-core web app, see §3/§6)

TIER 1 — RUST RUNTIME MODULES (extend koba-pc-plugin)
  KOBA Adaptive Capacity (module inside koba-pc-plugin)

TIER 2 — IDENTITY / ECONOMY SPINE
  KOBAid Identity & Licensing  ──requires koba-pc-plugin for server-side validation──┐
     │        (NOTE: likely overlaps with koba-core's own koba_identities/          │
     │         licensing tables — unreconciled, see §10)                           │
  KOBA Creator Ecosystem (API/SDK)  ──depends on KOBAid + koba-pc-plugin──────────┘
```

**Why split this way**: the specs themselves already describe the Rust
runtime plugin as a single shared foundation, and KOBAid as a separate
platform service with its own data model, API, and database. Splitting
along those seams matches the architecture the specs already assume,
rather than cutting across it. KOBA Bot is scoped separately from all of
this — it's a real, already-shipping Discord bot for Rust Console
Edition server admins, with no current dependency on the koba-core/KOBAid
spec stack.

---

## 2. KOBA Bot

| | |
|---|---|
| **Scope** | A Discord bot (discord.js v14) that gives Rust Console Edition server admins a Clan/Team War Event Manager and Roster Commander, controlled via real WebRCON — interactive war terminal, rank/fireteam hierarchy, a virtual crafting economy, monument-zone capture rewards, 5 bomb variants with real RCON detonation loops, plus a growing games suite (Ticket Jackpot, Bradley APC Ambush, Recycler Roulette, Target Range, Cargo Ship Heist). Has a companion admin dashboard and marketing website. Originally built as "BoomBot," rebranded to "KOBA Bot" 2026-10-11. |
| **Current state** | **Real, shipping code.** `~/Desktop/kobabot/` — `rcon/manager.js` + `rcon/parsers.js` for real WebRCON I/O, ~30 slash commands, a SQLite-backed economy/roster/licensing system, Stripe billing, a Next.js-based admin dashboard + marketing site, and a real combat-events/kill-feed pipeline (`utils/combatEvents.js`). |
| **Dependencies** | None on any other KOBA platform project today — it talks directly to a Rust Console Edition server's WebRCON interface, not to koba-core. (A future KOBAid-based per-account licensing integration is plausible given KOBA Bot already has its own per-Discord-user licensing model, but that's speculative, not scoped.) |
| **Roadmap outline** | 1. Keep closing RCON command/syntax gaps found against the official Rust Console Edition docs as they're discovered. 2. Replace `logo.png` and any remaining brand art with real KOBA-branded assets. 3. Decide whether to expand to any other console game (Conan Exiles via GPORTAL flagged as the most promising candidate researched so far). 4. **Future direction, not started**: `Full_261010_215649.txt`'s Project 2B describes a "koba-bot" with the opposite architecture to today's — zero local DB/economy, everything forwarded to a new `koba-core` web app (see §3) and run inside a new `koba-discord-app` host (see §4). Per explicit user direction (2026-10-11), this is a future migration target only — no code changes are happening now. See [koba-bot/ROADMAP.md](koba-bot/ROADMAP.md) for that target architecture in full. |
| **Suggested repo name** | `kobabot` (already the local folder name). |

---

## 3. koba-core (the web "master brain")

| | |
|---|---|
| **Scope** | Per `Full_261010_215649.txt` (2026-10-10), Project 1: the centralized Next.js web application for koba.games — DB layer (identities, linked accounts, guild game-adapters, feed-channel routing, clan tiers, player homes, discipline matrix), the Universal Command Router API, the Secure Server Adapter Ingestion Pipeline (4 verification gates for incoming WebRCON events), the Three-Strike Disciplinary & Blacklist Engine, and the persistent app-shell frontend. **This is a different project from the old "KOBA Core" Rust plugin** — that project is renamed **KOBA PC Plugin** below (§6) to free up this name. |
| **Current state** | Spec-only. No Next.js project, schema, or API routes exist yet. |
| **Dependencies** | None upstream — this is what `koba-pc-plugin`, `koba-discord-app`, and `koba-bot` all talk to. |
| **Roadmap outline** | See [koba-core/ROADMAP.md](koba-core/ROADMAP.md) for the full 5-phase breakdown (DB layer → command router → ingestion pipeline → disciplinary engine → app shell). |
| **Suggested repo name** | `koba-core` |

---

## 4. koba-discord-app

| | |
|---|---|
| **Scope** | Per `Full_261010_215649.txt`, Project 2: a lightweight, "dumb" (zero business logic/DB/calculation) Node.js/TypeScript app that manages live multi-tenant WebRCON connections to game servers and hosts the dual bot-login process for **KOBA Bot** and **KOBA Plus**. Parses console feeds and forwards both events and Discord interactions to `koba-core`. |
| **Current state** | Spec-only. No code exists. |
| **Dependencies** | Needs `koba-core`'s ingestion/interaction endpoints (or a stable contract) to be useful end-to-end. Hosts the runtime `koba-bot` logs in through. |
| **Roadmap outline** | See [koba-discord-app/ROADMAP.md](koba-discord-app/ROADMAP.md) for the full 4-phase breakdown (WebRCON manager → dual-login → feed parser → interaction forwarder). |
| **Suggested repo name** | `koba-discord-app` |

---

## 5. koba-bot (Project 2B — future target architecture, not the current `kobabot`)

| | |
|---|---|
| **Scope** | Per `Full_261010_215649.txt`, Project 2B: the user-facing slash-command layer for KOBA Bot + KOBA Plus — fully "dumb," forwards every interaction to `koba-core` and prints back whatever embed comes back. **Important**: this is architecturally the opposite of the existing, real `~/Desktop/kobabot` (which owns its own SQLite economy/roster/billing). Per explicit user direction (2026-10-11), this is a future migration target only — see §2 above and [koba-bot/ROADMAP.md](koba-bot/ROADMAP.md) for the full reconciliation note and command-tree breakdown (player commands, clan/warfare, staff discipline trees, owner-only `/nuke`, developer-only HQ-gated commands, brand visual language system). |
| **Current state** | Spec-only as this architecture. (The *existing*, differently-architected `kobabot` is real — see §2.) |
| **Dependencies** | Runs inside `koba-discord-app`; forwards everything to `koba-core`. |
| **Roadmap outline** | See [koba-bot/ROADMAP.md](koba-bot/ROADMAP.md). |
| **Suggested repo name** | TBD pending the migration-vs-new-repo decision — see the roadmap doc. |

---

## 6. TIER 1 — KOBA PC Plugin (formerly "KOBA Core")

| | |
|---|---|
| **Scope** | Per `KOBA CORE_260927_214218.txt`, and renamed/refined by `Full_261010_215649.txt` Project 3 (`koba-pc-plugin`, plugin file `KobaCore.cs`): a single installable Oxide/uMod + Carbon-compatible C# Rust plugin, now scoped specifically as a **silent background ingestion + cryptographic verification pipeline** — zero player/admin commands, invisible in-game. Signs combat/raid/structural events with HMAC/SHA256 and pushes them to `koba-core`'s ingestion pipeline over WebRCON. Also handles startup license/asset-validation handshakes for paid custom content. |
| **Current state** | **Spec-only.** No C#/Rust-plugin code exists anywhere in the inspected repos. |
| **Dependencies** | None upstream, but needs a real Rust/Carbon/uMod dev environment to build against (unverified in this environment so far), and needs to agree on a signed-payload wire format with `koba-core`'s ingestion pipeline (§3) before either side can be tested end-to-end. |
| **Roadmap outline** | See [koba-pc-plugin/ROADMAP.md](koba-pc-plugin/ROADMAP.md) for the full 5-phase breakdown (install/key handling → payload signing → combat hooking → raid hooking → marketplace asset licensing). |
| **Suggested repo name** | `koba-pc-plugin` |

---

## 7. TIER 1 — KOBA Adaptive Capacity (Performance & Capacity System)

| | |
|---|---|
| **Scope** | Per `KOBA Adaptive Capacity_260927_235753.txt`: a centralized performance/capacity manager living *inside* the Rust plugin (`koba-pc-plugin`, §6) that lets every KOBA subsystem request a workload budget and scale down/up based on measured server performance, not assumed hardware tiers. **Note**: the spec's original integration points (Dragon/Spider Queen/seasonal events, MOBO/submarine/ferry vehicle systems) are all dropped content — this module now has no concrete subsystem to budget for until a real use case exists. |
| **Current state** | Spec-only — and explicitly depends on the Rust plugin already existing. |
| **Dependencies** | **Hard dependency on KOBA PC Plugin.** Designed as a module inside it, not standalone. |
| **Roadmap outline** | 1. Server detection + performance baseline. 2. Real-time monitoring + hysteresis-protected performance states. 3. Centralized workload budget API. 4. Defer "integration hooks" work until a real subsystem exists to integrate with — don't build speculative hooks for dropped content. 5. Admin commands. |
| **Suggested repo name** | Likely a module/folder inside `koba-pc-plugin` rather than its own repo. |

---

## 8. TIER 2 — KOBAid Identity, Licensing & Digital Scarcity Engine

| | |
|---|---|
| **Scope** | Per `KOBAid IDENTITY_260927_221438.txt`: the permanent cross-context identity (`KOBAid`) tying together player/business/creator/server-owner/marketplace-seller profiles, plus asset identity, versioning, cryptographic manifests, rarity tiers, limited editions with DB-enforced scarcity, licensing, entitlements, server-side validation API, and anti-tampering/audit infrastructure. PostgreSQL-authoritative, Redis for ephemeral caching only. **One KOBAid per real person** (user-confirmed 2026-10-11): a user creating a business account who already has a player account uses the *same* KOBAid — account types are roles/labels on one identity, not separate IDs. |
| **Current state** | Spec-only. No PostgreSQL schema, no identity service, no cryptographic signing service exists in any inspected repo. **Note**: KOBA Bot already has its own simpler per-Discord-account licensing model (`commands/license.js`, `commands/activate-user.js`), and the new `koba-core` web app (§3) specs its *own* `koba_identities`/`koba_linked_accounts` tables covering much of the same ground — three overlapping identity models now exist across three docs, unreconciled. See §10. |
| **Dependencies** | Needs **KOBA PC Plugin** for the server-side validation integration point, but the identity/marketplace/licensing core can be built and tested independently first. |
| **Roadmap outline** | Follows the spec's own phased order: 1. KOBAid generation (one per person, see above). 2. PostgreSQL schema. 3–5. Asset registry/versioning/signed manifests. 6–7. Rarity + edition scarcity (with real concurrency testing). 8–10. Licensing/purchase flow/entitlements. 11–13. Validation API + Redis cache + secure delivery. 14. KOBA PC Plugin integration. 15–18. Dashboards, audit, testing. |
| **Suggested repo name** | `koba-identity` (or `koba-id`) |

---

## 9. TIER 2 — KOBA Creator Ecosystem (Core + API/SDK + Asset Runtime)

| | |
|---|---|
| **Scope** | Per `KOBA CREATOR ECOSYSTEM_260928_222641.txt`: the two-path creator integration platform — Path A (use the Rust runtime directly, no custom plugin) and Path B (creator's own Rust plugin + KOBA API/SDK) — with a protected-product extension-manifest model, asset capability matrix, CUI as a first-class content type. |
| **Current state** | Spec-only. This is explicitly the layer that sits on top of KOBAid + the Rust runtime + Marketplace once those exist; none of the API/SDK/extension-manifest code exists yet. |
| **Dependencies** | **Hard dependency on KOBAid** (licensing/entitlement) and **KOBA PC Plugin** (runtime integration path). Logically this is the *last* Tier-2 piece to build since it's an API surface over the other two. |
| **Roadmap outline** | 1. Product/extension-manifest model. 2. Protected-boundary enforcement — needs a real test case to validate against (no monument/content project exists to test with anymore, per the 2026-10-11 descope). 3. KOBA API + SDK with scoped credentials. 4. Creator sandbox separate from production. 5. Verification pipeline. 6. Fee/payout accounting split. |
| **Suggested repo name** | `koba-creator-ecosystem` |

---

## 10. What NOT to split out yet

- **KOBA Adaptive Capacity** — the spec explicitly describes itself as a
  *module inside the Rust plugin* (`koba-pc-plugin`), not a standalone
  product a server owner would install on their own. Listed above as a
  Tier 1 line item with its own roadmap outline because it's substantial
  enough to track separately, but it likely belongs in the `koba-pc-plugin`
  repo as a module rather than as a separate repo — revisit once that
  repo's structure exists.
- **A generic "Marketplace" project** — KOBAid and the Creator Ecosystem
  docs both *refer to* "KOBA.GAMES Marketplace" / "the storefront" as
  something that exists or will exist, but none of the 22 docs is itself
  a marketplace/storefront spec. Scoping a Marketplace project now would be
  inventing requirements no doc actually states. Treat it as an acknowledged
  gap, not a project, until a real marketplace spec shows up.
- **A third identity/licensing system** — `koba-core` (§3), `KOBAid` (§8),
  and the existing `kobabot` (§2) each independently define their own
  identity/account-linking/licensing model. This document does not pick a
  winner — flagging it plainly as unreconciled so no one builds a third
  implementation before the user decides whether `koba-core`'s tables
  *are* the KOBAid system, a separate thing, or need merging. KOBAid's
  "one per real person" rule (§8) should apply to whichever model wins.
