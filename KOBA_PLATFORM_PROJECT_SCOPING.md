# KOBA Platform — Project Scoping

Source material: the 22 spec `.txt` files in `~/Desktop/koba pc engine stuff/`,
plus `README.md`, `ARCHITECTURE_ASSESSMENT.md`, and `ROADMAP.md` in this repo,
plus the source of `~/Desktop/kobabot/` (the KOBA Bot Discord bot).

Decision already made by the user (not re-litigated here): split the
platform into separate projects along KOBA's named sub-brands, not along a
simple "engine vs content" axis. This document proposes the project list,
grounded in what each spec doc actually says and what code/assets actually
exist today — not invented scope.

**2026-10-11 descope**: the user confirmed they will **not** be building any
of the monument/skin content products (Casino & Resort, Ferry Terminal,
Yachts, Theme Park, Quarry, MOBO, Submarine, World Events, the Building Skin
System). Those sections have been removed from this document rather than
kept as "not pursuing" filler — the active KOBA platform scope is now
**KOBA Bot**, **KOBA Creator Engine**, and **KOBA Core / KOBA Live / KOBAid**
(the runtime + identity/economy spine), as confirmed by the user.

---

## 1. Dependency / sequencing diagram

```
KOBA Bot (standalone — real code today, no dependency on anything below)

TIER 0 — FOUNDATION (must exist before most platform work is usable)
  KOBA Creator Engine (the only platform-spec project with real code today)

TIER 1 — RUNTIME PLATFORM (Rust-server side)
  KOBA Core  ─────────────────────────────┐
     │                                     │
     └── KOBA Adaptive Capacity (extends Core)

TIER 2 — IDENTITY / ECONOMY / MARKETPLACE SPINE
  KOBAid Identity & Licensing  ──requires Core for server-side validation──┐
     │                                                                      │
  KOBA Creator Ecosystem (API/SDK)  ──depends on KOBAid + Core────────────┤
     │                                                                      │
  KOBA Live (showcase/verification) ──depends on Core, KOBAid, Marketplace┘
```

**Why split this way**: the specs themselves already describe KOBA Core as
a single shared Rust runtime, and KOBA Creator Engine / KOBAid / KOBA Live
as separate platform services with their own data models, APIs, and
databases. Splitting along those seams matches the architecture the specs
already assume, rather than cutting across it. KOBA Bot is scoped separately
from all of this — it's a real, already-shipping Discord bot for Rust
Console Edition server admins, with no current dependency on the
KOBA Core/KOBAid/Live spec stack.

---

## 2. KOBA Bot

| | |
|---|---|
| **Scope** | A Discord bot (discord.js v14) that gives Rust Console Edition server admins a Clan/Team War Event Manager and Roster Commander, controlled via real WebRCON — interactive war terminal, rank/fireteam hierarchy, a virtual crafting economy, monument-zone capture rewards, and 5 bomb variants with real RCON detonation loops. Has a companion admin dashboard and marketing website. Originally built as "BoomBot," rebranded to "KOBA Bot" 2026-10-11. |
| **Current state** | **Real, shipping code.** `~/Desktop/kobabot/` — `rcon/manager.js` + `rcon/parsers.js` for real WebRCON I/O, ~30 slash commands, a SQLite-backed economy/roster/licensing system, Stripe billing, and a Next.js-based admin dashboard + marketing site. A background research pass is in progress cross-checking the current RCON command usage against the official Rust Console Edition community-server documentation to catch gaps or syntax drift. |
| **Dependencies** | None on any other KOBA platform project today — it talks directly to a Rust Console Edition server's WebRCON interface, not to KOBA Core. (A future KOBAid-based per-account licensing integration is plausible given KOBA Bot already has its own per-Discord-user licensing model, but that's speculative, not scoped.) |
| **Roadmap outline** | 1. Finish the RCON-command/gap-check research pass against the official docs (in progress). 2. Fix any confirmed syntax mismatches between KOBA Bot's RCON calls and the documented commands. 3. Replace `logo.png` and any remaining brand art with real KOBA-branded assets. 4. Decide whether to expand to any other console game found viable by the parallel research pass (none confirmed yet). |
| **Suggested repo name** | `kobabot` (already the local folder name). |

---

## 3. TIER 0 — KOBA Creator Engine

| | |
|---|---|
| **Scope** | An AI-enabled, five-layer production orchestration platform (per `KOBA CREATOR ENGINE MASTER PRODUCTION ARCHITECTURE_260928_235448.txt`, the actual target spec for this repo) that drives Blender/Inkscape/ImageMagick/GIMP/etc. to generate, validate, optimize, and package game assets — Layers 1 (AI) through 5 (artifact graph/compilation/signing). A second, overlapping spec file ("Koba engine" txt, calling itself the "KOBA Universal Content Engine") describes a broader multi-target (Rust/Unreal/Unity) content factory — this is a superset/alternate framing of the same ambition and has NOT been reconciled with the five-layer spec; treat it as input to this project's backlog, not a separate project. **Note**: the engine's most developed proving ground to date (the Casino & Resort monument build) is a dropped content product per the 2026-10-11 descope — the engine itself is still active, just without that specific use case going forward. |
| **Current state** | **Real, partially built.** Per `README.md`/`ARCHITECTURE_ASSESSMENT.md`/`ROADMAP.md`: Layers 3 (tool adapters: Blender/Inkscape/ImageMagick, GIMP partial) and a slice of Layer 4 (geometry/materials/rigging/animation/optimization inside `adapters/blender/`) are real and tested. Layer 2 has a real `orchestrator/pipeline_manager`, job tracking, and a real artifact graph. Layer 1 has two real agents (`blender_agent`, `repair_agent`) plus a real AI router with a rule-based and an Anthropic provider. Layer 5 has `core/manifest.py` + a real artifact graph and release signing. No marketplace/KOBA-Live/KOBA-Core integration exists. |
| **Dependencies** | None — this is the foundation any future asset-production work would need. |
| **Roadmap outline** | 1. Formalize existing adapters under the spec's real tool-contract interface. 2. Harden the artifact graph (lineage/hashing) as the one piece nearly everything depends on. 3. Expand orchestration (job queue, dependency-aware rebuilds). 4. Add remaining tool contracts (RustEdit — blocked, no licensed Rust install; FFmpeg — not installed). 5. Grow the agent roster past the two proven agents only as real need appears. 6. Decide on a real next production target now that the Casino & Resort build is dropped, rather than defaulting back into monument work. |
| **Suggested repo name** | `koba-creator-engine` (already is the repo name). |

---

## 4. TIER 1 — KOBA Core

| | |
|---|---|
| **Scope** | Per `KOBA CORE_260927_214218.txt`: a single installable Oxide/uMod + Carbon-compatible C# Rust plugin — shared runtime infrastructure covering zones, interactions, events, teams, economy abstraction, loot, door/access control, wipe integration, commands, permissions, database, versioned API, third-party integration, logging, diagnostics. Explicitly: "ONE INSTALLABLE KOBA PLUGIN. MANY INTERNAL MODULES." **Note**: the spec frames much of this as infrastructure for monuments/events the user is no longer building — scope Core itself around whatever real use case is actually being pursued (e.g. a future KOBA Bot RCON-adjacent integration) rather than building out monument/event hooks with nothing to register against. |
| **Current state** | **Spec-only.** No C#/Rust-plugin code exists anywhere in the inspected repos. `ARCHITECTURE_ASSESSMENT.md` confirms KOBA Core "is not present in this repository or referenced by any code." |
| **Dependencies** | None upstream, but needs a real Rust/Carbon/uMod dev environment to build against. |
| **Roadmap outline** | 1. Verify actual Carbon/Oxide APIs on a real target Rust server version. 2. Core infra: config, logging, permissions, command dispatch. 3. Economy/loot/door abstractions — scoped to a real, current use case rather than the full monument/event framework the original spec assumed. 4. API versioning for future KOBA products to register against. |
| **Suggested repo name** | `koba-core` |

---

## 5. TIER 1 — KOBA Adaptive Capacity (Performance & Capacity System)

| | |
|---|---|
| **Scope** | Per `KOBA Adaptive Capacity_260927_235753.txt`: a centralized performance/capacity manager living *inside* KOBA Core that lets every KOBA subsystem request a workload budget and scale down/up based on measured server performance, not assumed hardware tiers. **Note**: the spec's original integration points (Dragon/Spider Queen/seasonal events, MOBO/submarine/ferry vehicle systems) are all dropped content — this module now has no concrete subsystem to budget for until a real use case exists. |
| **Current state** | Spec-only — and explicitly depends on KOBA Core already existing. |
| **Dependencies** | **Hard dependency on KOBA Core.** Designed as a module inside Core, not standalone. |
| **Roadmap outline** | 1. Server detection + performance baseline. 2. Real-time monitoring + hysteresis-protected performance states. 3. Centralized workload budget API. 4. Defer "integration hooks" work until a real subsystem exists to integrate with — don't build speculative hooks for dropped content. 5. Admin commands. |
| **Suggested repo name** | Likely a module/folder inside `koba-core` rather than its own repo. |

---

## 6. TIER 2 — KOBAid Identity, Licensing & Digital Scarcity Engine

| | |
|---|---|
| **Scope** | Per `KOBAid IDENTITY_260927_221438.txt`: the permanent cross-context identity (`KOBAid`) tying together player/business/creator/server-owner/marketplace-seller profiles, plus asset identity, versioning, cryptographic manifests, rarity tiers, limited editions with DB-enforced scarcity, licensing, entitlements, server-side validation API, and anti-tampering/audit infrastructure. PostgreSQL-authoritative, Redis for ephemeral caching only. |
| **Current state** | Spec-only. No PostgreSQL schema, no identity service, no cryptographic signing service exists in any inspected repo. **Note**: KOBA Bot already has its own simpler per-Discord-account licensing model (`commands/license.js`, `commands/activate-user.js`) — worth comparing against this spec before building a second, separate licensing system. |
| **Dependencies** | Needs **KOBA Core** for the server-side validation integration point, but the identity/marketplace/licensing core can be built and tested independently of Core first. |
| **Roadmap outline** | Follows the spec's own phased order: 1. KOBAid generation. 2. PostgreSQL schema. 3–5. Asset registry/versioning/signed manifests. 6–7. Rarity + edition scarcity (with real concurrency testing). 8–10. Licensing/purchase flow/entitlements. 11–13. Validation API + Redis cache + secure delivery. 14. KOBA Core integration. 15–18. Dashboards, audit, testing. |
| **Suggested repo name** | `koba-identity` (or `koba-id`) |

---

## 7. TIER 2 — KOBA Creator Ecosystem (Core + API/SDK + Asset Runtime)

| | |
|---|---|
| **Scope** | Per `KOBA CREATOR ECOSYSTEM_260928_222641.txt`: the two-path creator integration platform — Path A (use KOBA Core directly, no custom plugin) and Path B (creator's own Rust plugin + KOBA API/SDK) — with a protected-product extension-manifest model, asset capability matrix, CUI as a first-class content type. |
| **Current state** | Spec-only. This is explicitly the layer that sits on top of KOBAid + KOBA Core + Marketplace once those exist; none of the API/SDK/extension-manifest code exists yet. |
| **Dependencies** | **Hard dependency on KOBAid** (licensing/entitlement) and **KOBA Core** (runtime integration path). Logically this is the *last* Tier-2 piece to build since it's an API surface over the other two. |
| **Roadmap outline** | 1. Product/extension-manifest model. 2. Protected-boundary enforcement — originally meant to be tested against a real monument project (Casino), which is now dropped; needs a new real test case before this phase is concrete. 3. KOBA API + SDK with scoped credentials. 4. Creator sandbox separate from production. 5. Verification pipeline. 6. Fee/payout accounting split. |
| **Suggested repo name** | `koba-creator-ecosystem` (API/SDK), separate from `koba-creator-engine` (the Blender/asset production tool) — these are two different "Creator" names in the specs and should not be merged just because they share a word. |

---

## 8. TIER 2 — KOBA Live

| | |
|---|---|
| **Scope** | Per `KOBA LIVE_260927_225405.txt`: the live showcase/verification/analytics platform — ProductID-driven showcase deployments, an async KOBA-Core-to-ingestion event pipeline, Redis live state, a camera-director service, cryptographically signed version-specific "KOBA LIVE VERIFIED" reports, creator dashboard, and full marketplace-conversion funnel analytics. Explicitly must never block or depend on by Rust gameplay. |
| **Current state** | Spec-only. No ingestion service, director, Redis live-state schema, or verification pipeline exists. |
| **Dependencies** | Needs **KOBA Core** (event emission), **KOBAid** (ProductID/CreatorID model it's built on), and a **Marketplace** (not separately spec'd as its own project — see §10) to actually display live showcase pages against. In practice this is the last platform piece to build. |
| **Roadmap outline** | 1. Product/version/deployment identity model (reuses KOBAid's AssetID/ProductID pattern). 2. Core event system + async transport abstraction. 3. Ingestion service + Redis live state. 4. Director (camera scoring, anti-thrashing). 5. Capture-node/streaming integration (external to KOBA Core). 6. Verification pipeline + signed reports. 7. Creator dashboard + analytics funnel. |
| **Suggested repo name** | `koba-live` |

---

## 9. Dropped scope (2026-10-11)

Per the user's explicit decision, none of the following will be built. Kept
as a one-line record only so the reasoning isn't lost, not as active scope:

- **KOBA Building Skin System** — a Rust building-skin application system;
  dropped as a "skins" product.
- **KOBA Casino & Resort, KOBA Ferry Terminal, KOBA Mega Yacht / KOBA Mobile
  Yacht, KOBA Theme Park, KOBA Quarry, KOBA MOBO, KOBA Player-Built
  Submarine, KOBA World Events (Dragon, Dragon vs Patrol Helicopter, Spider
  Queen, The Infection, Nightfall, Winterfest, Gold Run), KOBA Dragon's
  Lair** — all monument/vehicle/event content products; dropped as
  "monuments ... or things like that."
- The Casino & Resort Blender blockout work that already exists under
  `koba_creator_engine/projects/koba_casino_resort_*` is left on disk as-is
  (real, signed release artifacts) but is not active roadmap work going
  forward.

---

## 10. What NOT to split out yet

- **KOBA Adaptive Capacity** — the spec explicitly describes itself as a
  *module inside KOBA Core*, not a standalone product a server owner would
  install on their own. Listed above as a Tier 1 line item with its own
  roadmap outline because it's substantial enough to track separately, but
  it likely belongs in the `koba-core` repo as a module rather than as a
  separate repo — revisit once `koba-core`'s repo structure exists.
- **A generic "Marketplace" project** — KOBA Live, KOBAid, and the Creator
  Ecosystem docs all *refer to* "KOBA.GAMES Marketplace" / "the storefront"
  as something that exists or will exist, but none of the 22 docs is itself
  a marketplace/storefront spec. Scoping a Marketplace project now would be
  inventing requirements no doc actually states. Treat it as an acknowledged
  gap, not a project, until a real marketplace spec shows up.
- **The "Koba engine" Universal Content Engine doc as a project separate
  from KOBA Creator Engine** — it describes the same ambition (a
  multi-target, data-driven content factory) as the master five-layer spec
  that `koba_creator_engine`'s own `README.md`/`ARCHITECTURE_ASSESSMENT.md`
  already treat as this repo's real target. The two documents haven't been
  reconciled, but that's a backlog/reconciliation task *within* KOBA
  Creator Engine, not grounds for a second engine project.
