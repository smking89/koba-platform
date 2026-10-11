# KOBA Platform — Project Scoping

Source material: the 22 spec `.txt` files in `~/Desktop/koba pc engine stuff/`,
plus `README.md`, `ARCHITECTURE_ASSESSMENT.md`, `ROADMAP.md`, and
`KOBA_CASINO_RESORT_ROADMAP.md` in this repo, plus a directory listing of
`projects/`.

Decision already made by the user (not re-litigated here): split the
platform into separate projects along KOBA's named sub-brands, not along a
simple "engine vs content" axis. This document proposes the project list,
grounded in what each spec doc actually says and what code/assets actually
exist today — not invented scope.

---

## 1. Dependency / sequencing diagram

```
TIER 0 — FOUNDATION (must exist before almost anything else is usable)
  KOBA Creator Engine (the only one with real code today)

TIER 1 — RUNTIME PLATFORM (Rust-server side; content plugs into this)
  KOBA Core  ─────────────────────────────┐
     │                                     │
     ├── KOBA Adaptive Capacity (extends Core)
     ├── KOBA Building Skin System (extends Core)
     └── (all monuments/vehicles/events below register with Core)

TIER 2 — IDENTITY / ECONOMY / MARKETPLACE SPINE
  KOBAid Identity & Licensing  ──requires Core for server-side validation──┐
     │                                                                      │
  KOBA Creator Ecosystem (API/SDK)  ──depends on KOBAid + Core────────────┤
     │                                                                      │
  KOBA Live (showcase/verification) ──depends on Core, KOBAid, Marketplace┘

TIER 3 — CONTENT PROJECTS (each depends on: Creator Engine for production,
          Core for runtime, KOBAid/Marketplace for distribution)
  KOBA Casino & Resort          (IN PROGRESS — real .blend phases exist)
  KOBA Ferry Terminal
  KOBA Mega Yacht  +  KOBA Mobile Yacht  (see note — likely same product, see §13)
  KOBA Theme Park
  KOBA Quarry
  KOBA MOBO (vehicle product)
  KOBA Player-Built Submarine (vehicle product)
  KOBA World Events (grouped: Dragon, Dragon vs Patrol Helicopter, Spider
     Queen, The Infection, Nightfall, Winterfest, Gold Run)

NOT YET A PROJECT (too thin/speculative — see §15)
  KOBA Dragon's Lair (monument referenced by the Dragon event doc but has
     no spec file of its own)
```

**Why split this way**: the specs themselves already describe KOBA Core as
a single shared Rust runtime that every monument/vehicle/event "plugs into"
(KOBA CORE §30–31, explicitly: "do not write separate implementations ...
for every monument"), and describe KOBA Creator Engine / KOBAid / KOBA Live
as separate platform services with their own data models, APIs, and
databases. Splitting along those seams matches the architecture the specs
already assume, rather than cutting across it. Content projects (monuments,
vehicles, events) are naturally separable because each spec explicitly frames
itself as an installable product a server owner buys independently — e.g.
KOBA MOBO §"PRODUCT SEPARATION"-equivalent language, KOBA Submarine §46
("A server owner should be able to install KOBA PLAYER-BUILT SUBMARINES
without purchasing KOBA Casino... or other KOBA products").

---

## 2. TIER 0 — KOBA Creator Engine

| | |
|---|---|
| **Scope** | An AI-enabled, five-layer production orchestration platform (per `KOBA CREATOR ENGINE MASTER PRODUCTION ARCHITECTURE_260928_235448.txt`, the actual target spec for this repo) that drives Blender/Inkscape/ImageMagick/GIMP/etc. to generate, validate, optimize, and package game assets — Layers 1 (AI) through 5 (artifact graph/compilation/signing). A second, overlapping spec file ("Koba engine" txt, calling itself the "KOBA Universal Content Engine") describes a broader multi-target (Rust/Unreal/Unity) content factory with procedural monument tiers, marketing-render studio, and batch production — this is a superset/alternate framing of the same ambition and has NOT been reconciled with the five-layer spec; treat it as input to this project's backlog, not a separate project. |
| **Current state** | **Real, partially built.** Per `README.md`/`ARCHITECTURE_ASSESSMENT.md`/`ROADMAP.md`: Layers 3 (tool adapters: Blender/Inkscape/ImageMagick, GIMP partial) and a slice of Layer 4 (geometry/materials/rigging/animation/optimization inside `adapters/blender/`) are real and tested. Layer 2 has a real `orchestrator/pipeline_manager`, job tracking, and a real artifact graph (contradicts the "nothing exists" framing of the Universal Content Engine doc — this repo is ahead of that doc in some areas). Layer 1 has two real agents (`blender_agent`, `repair_agent`) plus a real AI router with a rule-based and an Anthropic provider. Layer 5 has `core/manifest.py` + a real artifact graph (`artifact_graph.json` files exist per project) but no compiler/signing beyond what casino-resort release manifests show (`release_manifest.json.sig` files exist in `projects/koba_casino_resort_phase*/releases/1/`, so signing is further along than the assessment doc implies as of this writing — check `ROADMAP.md` for the latest status rather than trusting this summary alone). No marketplace/KOBA-Live/KOBA-Core integration exists. |
| **Dependencies** | None — this is the foundation every other project needs to actually produce assets. |
| **Roadmap outline** | 1. Formalize existing adapters under the spec's real tool-contract interface. 2. Harden the artifact graph (lineage/hashing) as the one piece nearly everything depends on. 3. Expand orchestration (job queue, dependency-aware rebuilds). 4. Add remaining tool contracts (RustEdit — blocked, no licensed Rust install; FFmpeg — not installed). 5. Grow the agent roster past the two proven agents only as real need appears. 6. Reconcile the "Universal Content Engine" doc's monument-tier/marketing-studio ambitions into this roadmap or explicitly defer them. |
| **Suggested repo name** | `koba-creator-engine` (already is the repo name; no change needed if kept as its own repo). |

---

## 3. TIER 1 — KOBA Core

| | |
|---|---|
| **Scope** | Per `KOBA CORE_260927_214218.txt`: a single installable Oxide/uMod + Carbon-compatible C# Rust plugin that is the shared runtime for every KOBA monument/event/vehicle — monument registration, zones, interactions, events, teams, economy abstraction, loot, door/access control, wipe integration, commands, permissions, database, versioned API, third-party integration, logging, diagnostics. Explicitly: "ONE INSTALLABLE KOBA PLUGIN. MANY INTERNAL MODULES." |
| **Current state** | **Spec-only.** No C#/Rust-plugin code exists anywhere in the inspected repos. `ARCHITECTURE_ASSESSMENT.md` confirms KOBA Core "is not present in this repository or referenced by any code." |
| **Dependencies** | None upstream (it's the runtime foundation for Tier 1+), but it needs a real Rust/Carbon/uMod dev environment to build against — none of the specs' "inspect the installed Rust server" first steps have apparently been done yet in this environment. |
| **Roadmap outline** | 1. Verify actual Carbon/Oxide APIs on a real target Rust server version (every spec insists on this before any code). 2. Core infra: config, logging, permissions, command dispatch. 3. Monument registration + zone + interaction frameworks (the systems every content project needs first). 4. Event framework + reset/wipe integration. 5. Economy/loot/door abstractions. 6. API versioning for future KOBA products to register against. |
| **Suggested repo name** | `koba-core` |

---

## 4. TIER 1 — KOBA Adaptive Capacity (Performance & Capacity System)

| | |
|---|---|
| **Scope** | Per `KOBA Adaptive Capacity_260927_235753.txt`: a centralized performance/capacity manager living *inside* KOBA Core that lets every KOBA subsystem (AI, NPCs, entities, events, vehicles) request a workload budget and scale down/up based on measured server performance, not assumed hardware tiers. |
| **Current state** | Spec-only — and explicitly depends on KOBA Core already existing ("extend the existing KOBA Core architecture... do NOT create a second KOBA architecture"). |
| **Dependencies** | **Hard dependency on KOBA Core.** This is designed as a module inside Core, not standalone. |
| **Roadmap outline** | 1. Server detection + performance baseline. 2. Real-time monitoring + hysteresis-protected performance states. 3. Centralized workload budget (AI/NPC/entity/event/vehicle). 4. Integration hooks for Dragon/Spider Queen/seasonal events/vehicles (i.e., this project's "done" state depends on those content projects existing to integrate with). 5. Admin commands + KOBA Live telemetry. |
| **Suggested repo name** | Likely a module/folder inside `koba-core` rather than its own repo, given how tightly coupled the spec makes it — flag this as a judgment call to revisit once KOBA Core's repo structure exists. |

---

## 5. TIER 1 — KOBA Building Skin System

| | |
|---|---|
| **Scope** | Per `KOBA CORE — CUSTOM PLAYER BUILDING SKIN SYSTEM PRO...txt`: lets KOBA-authorized players automatically apply licensed Rust building skins to player-built structures, using real (not invented) Rust skin APIs, with an entitlement cache, offline grace period, and thread-safety rules for queuing skin application onto the Rust main thread. |
| **Current state** | Spec-only. The doc itself frames this as a "production prototype implementation" task that has not been executed — no code exists in the inspected repos. |
| **Dependencies** | **Hard dependency on KOBA Core** (build-event hooks, module registration) and **KOBAid/licensing** (entitlement checks) — this doc explicitly assumes both already exist and says to extend, not duplicate, them. |
| **Roadmap outline** | 1. Verify actual Rust BuildingBlock skin API. 2. Minimal single-skin prototype (place one wall, confirm client renders skin). 3. Entitlement cache + offline policy. 4. Manifest/signature validation tied into KOBAid. 5. Rate protection + telemetry. 6. Marketplace packaging of a real skin pack. |
| **Suggested repo name** | `koba-building-skins` (or a module inside `koba-core`, given how small and Core-coupled it is — see §15 for the "don't split too thin" judgment call). |

---

## 6. TIER 2 — KOBAid Identity, Licensing & Digital Scarcity Engine

| | |
|---|---|
| **Scope** | Per `KOBAid IDENTITY_260927_221438.txt`: the permanent cross-context identity (`KOBAid`) tying together player/business/creator/server-owner/marketplace-seller profiles, plus asset identity, versioning, cryptographic manifests, rarity tiers, limited editions with DB-enforced scarcity, licensing, entitlements, server-side validation API, and anti-tampering/audit infrastructure. PostgreSQL-authoritative, Redis for ephemeral caching only. |
| **Current state** | Spec-only. No PostgreSQL schema, no identity service, no cryptographic signing service exists in any inspected repo. |
| **Dependencies** | Needs **KOBA Core** for the server-side validation integration point (§15/35 of the spec), but the identity/marketplace/licensing core (PHASES 1–13 of its own 18-phase build order) can be built and tested independently of Core first. |
| **Roadmap outline** | Follows the spec's own 18-phase order: 1. KOBAid generation. 2. PostgreSQL schema. 3–5. Asset registry/versioning/signed manifests. 6–7. Rarity + edition scarcity (with real concurrency testing — "100 simultaneous purchases for a 5-edition Mythic asset must never issue more than 5"). 8–10. Licensing/purchase flow/entitlements. 11–13. Validation API + Redis cache + secure delivery. 14. KOBA Core integration. 15–18. Dashboards, audit, testing. |
| **Suggested repo name** | `koba-identity` (or `koba-id`) |

---

## 7. TIER 2 — KOBA Creator Ecosystem (Core + API/SDK + Asset Runtime)

| | |
|---|---|
| **Scope** | Per `KOBA CREATOR ECOSYSTEM_260928_222641.txt`: the two-path creator integration platform — Path A (use KOBA Core directly, no custom plugin) and Path B (creator's own Rust plugin + KOBA API/SDK) — with a protected-product extension-manifest model, asset capability matrix, CUI as a first-class content type, and a formal capability matrix separating what creators/plugins can and cannot touch. |
| **Current state** | Spec-only. This is explicitly the layer that sits on top of KOBAid + KOBA Core + Marketplace once those exist; none of the API/SDK/extension-manifest code exists yet. |
| **Dependencies** | **Hard dependency on KOBAid** (licensing/entitlement) and **KOBA Core** (runtime integration path). Logically this is the *last* Tier-2 piece to build since it's an API surface over the other two. |
| **Roadmap outline** | 1. Product/extension-manifest model. 2. Protected-boundary enforcement for monuments (depends on at least one real monument project, e.g. Casino, existing to test against). 3. KOBA API + SDK with scoped credentials. 4. Creator sandbox separate from production. 5. Verification pipeline. 6. Fee/payout accounting split (marketplace fee vs. Core runtime fee). |
| **Suggested repo name** | `koba-creator-ecosystem` (API/SDK), separate from `koba-creator-engine` (the Blender/asset production tool) — these are two different "Creator" names in the specs and should not be merged just because they share a word. |

---

## 8. TIER 2 — KOBA Live

| | |
|---|---|
| **Scope** | Per `KOBA LIVE_260927_225405.txt`: the live showcase/verification/analytics platform — ProductID-driven showcase deployments, an async KOBA-Core-to-ingestion event pipeline, Redis live state, a camera-director service, cryptographically signed version-specific "KOBA LIVE VERIFIED" reports, creator dashboard, and full marketplace-conversion funnel analytics. Explicitly must never block or depend on by Rust gameplay. |
| **Current state** | Spec-only. No ingestion service, director, Redis live-state schema, or verification pipeline exists. |
| **Dependencies** | Needs **KOBA Core** (event emission), **KOBAid** (ProductID/CreatorID model it's built on), and a **Marketplace** (not separately spec'd as its own project — see §15) to actually display live showcase pages against. In practice this is the last platform piece to build since it has the most dependencies and the least immediate content-production value. |
| **Roadmap outline** | 1. Product/version/deployment identity model (reuses KOBAid's AssetID/ProductID pattern — don't duplicate). 2. Core event system + async transport abstraction. 3. Ingestion service + Redis live state. 4. Director (camera scoring, anti-thrashing). 5. Capture-node/streaming integration (external to KOBA Core). 6. Verification pipeline + signed reports. 7. Creator dashboard + analytics funnel. |
| **Suggested repo name** | `koba-live` |

---

## 9. TIER 3 — KOBA Casino & Resort

| | |
|---|---|
| **Scope** | Per `KOBA resort_260926_200310.txt`: a massive Tier-3 (large) original Rust monument — grand casino, hotel, arcade, nightclub, pool, restaurant, VIP floor, security, vault, tournament arena, Mad Max race arena — built as physical architecture only (gambling/rental/reward *logic* is explicitly deferred to a future KOBA Core plugin per the doc's own §46 map-vs-plugin split). |
| **Current state** | **Furthest along of any content project — real, in-progress Blender work exists.** `KOBA_CASINO_RESORT_ROADMAP.md` and the `projects/koba_casino_resort_phase1_exterior` through `phase10b_signagepass` directories show real `.blend` blockout files, job logs, artifact graphs, and signed release manifests (`release_manifest.json.sig`) for: exterior, floors, main casino, hotel wing, arcade, nightclub, pool/social, restaurant/bar, conference, VIP-floor-shell, security/vault/service, rooftop, tournament arena, Mad Max race, exterior grounds, and signage. This is procedural primitive-level blockout (per the roadmap's own "Reality check" — boxes/panels/cylinders, not hand-crafted AAA prop art), explicitly not yet a loadable Rust monument (RustEdit path is blocked — no licensed Rust install on this machine) and not yet wired to any plugin logic. |
| **Dependencies** | Built via **KOBA Creator Engine** (already proven). Needs **KOBA Core** to exist before the physical monument becomes a playable Rust monument with working gambling/hotel/event logic. Needs **KOBAid/Marketplace** before it can be sold as a product. |
| **Roadmap outline** | 1–10 (done/in progress): per-module Blender blockout + validation, as tracked in `KOBA_CASINO_RESORT_ROADMAP.md`. 11. Higher-fidelity furniture/casino-machine asset pass (explicitly deferred in the roadmap, not blocked). 12. RustEdit/Rust export — blocked pending a licensed Rust install. 13. KOBA Core plugin for gambling/hotel-rental/tournament/Mad-Max logic. 14. Marketplace packaging. |
| **Suggested repo name** | Stays as a `projects/koba_casino_resort_*` workspace inside `koba-creator-engine` for now (it's build output, not a separate codebase) — but the *gameplay plugin* half of this product (once built) belongs in its own repo, e.g. `koba-casino-resort-plugin`, since it will depend on `koba-core` directly. |

---

## 10. TIER 3 — KOBA Ferry Terminal

| | |
|---|---|
| **Scope** | Per `KOBA FERRY TERMINAL_260926_234225.txt`: a Tier-2-sized moving-water monument — a fixed shoreline terminal plus a separate moving ferry that cruises an ocean route, docks, lets players board for a configurable window, then departs. Full PvP, no safe zones. Explicitly reusable "Ferry System" architecture meant to seed future KOBA maritime products. |
| **Current state** | Spec-only. No code, no `.blend` assets found for this product anywhere in the inspected repos. |
| **Dependencies** | **KOBA Creator Engine** for asset production. **KOBA Core** for the moving-monument/docking/boarding runtime logic — the spec itself says to research actual Rust entity-parenting/moving-monument support before building, since this is one of the more technically uncertain specs (explicitly flags that continuous smooth movement may not be achievable and a fallback architecture may be required). |
| **Roadmap outline** | Spec's own 20-phase plan compresses to: 1. Research Rust moving-entity/parenting capabilities (blocking everything else). 2. Reusable Ferry System core (route/lifecycle/docking state machine) — meant to be reusable for future KOBA maritime products, so build it generically. 3. First vertical slice (small ferry, one route, dock/board/depart) tested on a real server before full production. 4. Full terminal + ferry builds. 5. Loot/NPC/PvP. 6. Persistence/anti-exploit. 7. Commercial packaging + marketing renders. |
| **Suggested repo name** | `koba-ferry-terminal` |

---

## 11. TIER 3 — KOBA Mega Yacht (and KOBA Mobile Yacht — see note)

| | |
|---|---|
| **Scope** | Per `KOBA MEGA YACHT_260926_233613.txt`: a large (180–250m) moving offshore PvP monument on its own ocean route, carrying normal Scientists, a locked-crate event with Heavy-Scientist helicopter reinforcement (Oil-Rig-style escalation), and optional NPC patrol boats/jet skis (flagged as technically uncertain — "verify current Rust NPC vehicle AI support before implementation"). `KOBA MOBILE YACHT _260927_195107.txt` describes what reads as the *same monument* from a pure Blender-construction-and-RustEdit-integration angle (mobile entity hierarchy, collision system, deck-by-deck build order, tender garage, moon pool, hull breaches, Rust integration markers) — it does not introduce a second distinct gameplay identity. |
| **Current state** | Spec-only — no yacht assets found in `projects/`. |
| **Dependencies** | **KOBA Creator Engine** for asset production, **KOBA Core** for moving-monument/NPC/event runtime (same open research question as the Ferry Terminal re: Rust entity movement/parenting), **KOBA Adaptive Capacity** for the NPC/patrol-boat budget integration the Adaptive Capacity spec explicitly calls out. |
| **Roadmap outline** | 1. Resolve the Mega-Yacht-vs-Mobile-Yacht naming/scope overlap with the user before starting build work (flagged here, not resolved by this document). 2. Research moving-monument + NPC-vehicle Rust capabilities. 3. Minimal moving-yacht vertical slice (spawn, route, board, one scientist, one loot crate, despawn). 4. Locked-crate + Heavy Scientist helicopter event. 5. Patrol boats / jet skis (document limitation if unsupported). 6. Full deck-by-deck production build (hull/decks/underwater/tender garage/moon pool per the Mobile Yacht doc's construction detail). 7. Packaging + marketing. |
| **Suggested repo name** | `koba-mega-yacht` (pending the naming/scope question above — do not create two repos for what may be one product). |

---

## 12. TIER 3 — KOBA Theme Park

| | |
|---|---|
| **Scope** | Per `Koba theme park_260926_200931.txt`: a Tier-3 (large) original post-apocalyptic amusement-park monument with distinct districts (Thrill Zone, Carnival, Family, Arcade, Horror, Water Park, Go-Kart, Entertainment, Restaurants, Shops, Security, Maintenance, Underground), anchored by an original giant coaster ("KOBA Colossus"). Same map-vs-plugin split as the Casino doc — physical geometry/interaction points only, ride/game logic deferred to a future Core plugin. |
| **Current state** | Spec-only — no theme-park assets found in `projects/`. |
| **Dependencies** | Same shape as Casino & Resort: **KOBA Creator Engine** for production, **KOBA Core** for eventual ride/game-logic plugins, **KOBAid/Marketplace** for distribution. |
| **Roadmap outline** | Mirrors the Casino roadmap's discipline (explicitly told to do a master blockout + player-scale validation before detailed decoration): 1. Master plan + blockout (entrance, plaza, district footprints, coaster footprint). 2. Central landmark coaster + major rides (geometry only). 3. District-by-district build (Carnival/Family/Arcade/Horror/WaterPark/GoKart/Entertainment/Restaurants/Shops). 4. Backstage/maintenance/security/underground. 5. Environmental storytelling + lighting pass. 6. Performance validation. 7. Plugin integration-point documentation (handoff to a future Core-based ride/game plugin). |
| **Suggested repo name** | `koba-theme-park` |

---

## 13. TIER 3 — KOBA Quarry

| | |
|---|---|
| **Scope** | Per `KOBA QUARRY_260926_223535.txt`: a smaller, more tightly-scoped PvP monument whose core identity is a single mechanic — players can excavate underground, build bases in the excavated space, and get raided, with normal Rust crate/barrel loot distributed between surface and underground. No safe-zone assumption. |
| **Current state** | Spec-only — and notably thinner than the Casino/Theme-Park docs (no module list, no deliverables list, no floor-by-floor breakdown — it's "core gameplay rules" only, not a full monument-construction prompt). This is the most underspecified content doc of the lot; expect more design work before a build roadmap can be written with confidence. |
| **Dependencies** | **KOBA Creator Engine** for whatever excavation/geometry tooling is needed (note: player-driven terrain excavation is a *gameplay* mechanic, likely requiring new KOBA Core systems, not just static Blender geometry — this is architecturally different from Casino/Theme Park and should not be scoped as "just another monument build"). **KOBA Core** for the excavation/building/raiding mechanics themselves. |
| **Roadmap outline** | 1. Design pass to fill the gaps this spec leaves open (module layout, scale, specific buildable/protected volumes) — flag to the user as needed before production starts. 2. Research actual Rust terrain-modification/excavation capabilities (not addressed in the spec at all — a real open technical question). 3. Static surface monument geometry (industrial/mining buildings) via Creator Engine. 4. Core-side excavation + buildable-zone + loot systems. 5. PvP/raid validation. |
| **Suggested repo name** | `koba-quarry` |

---

## 14. TIER 3 — Vehicle products: KOBA MOBO and KOBA Player-Built Submarine

| | |
|---|---|
| **Scope — MOBO** | Per `Koba MOBO_260926_222718.txt`: an original fixed (non-player-built) surface/submersible vehicle in three sizes (Scout/Explorer/Deep), sold as a standalone plugin+asset product, explicitly map/monument-independent and explicitly non-pay-to-win. |
| **Scope — Submarine** | Per `Koba submarine _260926_222625.txt`: a *player-built modular* submarine construction system (building station, snap-together hull/structural/propulsion/ballast components, buoyancy/pressure/flooding simulation) — explicitly **not** MOBO and explicitly must not be merged with it ("Do not merge these systems"). |
| **Current state** | Both spec-only. No vehicle code or assets found. |
| **Dependencies** | Both need **KOBA Creator Engine** (3D asset production) and **KOBA Core** (vehicle/physics/networking integration, non-pay-to-win acquisition hooks). MOBO's underwater detection system is also a named integration point in the Adaptive Capacity spec ("vehicle systems: MOBO, player-built submarines, ferry systems"), so both should coordinate with **KOBA Adaptive Capacity** once that exists. |
| **Roadmap outline — MOBO** | 1. Research current Rust vehicle/plugin framework APIs. 2. Build one size (Scout) end-to-end: surface physics, dive transition, depth tracking, sonar. 3. Expand to Explorer/Deep. 4. Cargo/damage/emergency systems. 5. Packaging + marketing renders of all three sizes. |
| **Roadmap outline — Submarine** | 1. Research Rust building-system APIs (this is explicitly told not to reuse Rust's boat-building pieces). 2. Building station + modular hull/structural components + validation. 3. Ballast/buoyancy/depth/pressure simulation. 4. Flooding/compartment damage. 5. Sonar/power/oxygen (each independently toggleable per spec). 6. Multiplayer sync + anti-exploit + persistence. |
| **Suggested repo names** | `koba-mobo`, `koba-submarine` — two separate repos, per the spec's explicit "do not merge" instruction. |

---

## 15. TIER 3 — KOBA World Events (grouped project)

| | |
|---|---|
| **Scope** | A single grouped project covering seven event specs that each describe a server-side gameplay event riding on a shared "KOBA Core Seasonal Event Framework" / "KOBA World Event System" that none of the individual docs fully define on its own: **KOBA Dragon World Event + Flight System**, **Dragon vs Patrol Helicopter** (an explicit extension of the Dragon event — not a standalone system), **Spider Queen** (asset-package doc for a boss encounter), **The Infection** (outbreak/wave PvE event), **KOBA Nightfall** (Halloween), **KOBA Winterfest** (Christmas, Santa-convoy), **KOBA Gold Run** (St. Patrick's Day, gold-convoy). |
| **Why grouped rather than split into 7 projects** | Each of these is a single bounded event (one state machine, one or two NPC types, one loot table, one boss) riding entirely on infrastructure (seasonal event framework, zone system, NPC system, boss system) that must be built once inside **KOBA Core** regardless of how many events use it. None of them has enough independent surface area (no separate asset pipeline beyond Spider Queen's boss model, no separate licensing/marketplace model, no separate runtime service) to justify the overhead of a standalone repo, roadmap, and release cadence each. Grouping them into one project with one shared backlog avoids seven near-duplicate "build the event framework" line items. Dragon vs Patrol Helicopter specifically must not be split out at all — the spec says explicitly it's an extension of the Dragon event, not its own system. |
| **Current state** | All seven spec-only. No seasonal-event framework, boss system, or convoy system exists in any inspected repo. Spider Queen is further along *conceptually* in that its doc is a full Blender asset-production brief (boss model, babies, nest, webs) rather than a pure gameplay-logic doc — but no actual Blender work for it exists yet either. |
| **Dependencies** | **Hard dependency on KOBA Core** (every doc insists on reusing Core's event/zone/NPC/boss/loot framework rather than building a parallel one) and **KOBA Adaptive Capacity** (Dragon and Spider Queen are both named explicitly in the Adaptive Capacity spec as systems that must query it before spawning NPCs/effects). Spider Queen and Dragon both also need **KOBA Creator Engine** for their boss/creature assets. |
| **Roadmap outline** | 1. Build the shared Seasonal/World Event Framework inside KOBA Core first (state machine, zone/NPC/boss hooks) — this is the one piece all seven events need and none of them individually own. 2. Dragon + Flight System (the most architecturally distinct one — flight/route system). 3. Dragon vs Patrol Helicopter (extension, once Dragon exists). 4. Spider Queen (boss asset + brood/web mechanics, budget-integrated). 5. The Infection (wave/outbreak logic, reuses the framework most directly). 6. Seasonal rotation: Nightfall → Winterfest → Gold Run (convoy-pattern events, likely shareable convoy/vault sub-system across the latter two). |
| **Suggested repo name** | `koba-world-events` (one repo, one roadmap, per-event folders inside it). |

---

## 16. What NOT to split out yet

- **KOBA Dragon's Lair** — referenced as an existing monument by the Dragon
  World Event doc ("The Dragon originates from KOBA DRAGON'S LAIR") and
  listed as an example product in the Creator Ecosystem doc, but has **no
  spec file of its own** among the 22 docs inspected. There is nothing to
  scope yet beyond "the Dragon event needs a lair monument to live in" —
  don't invent a project brief for it. Either fold a minimal lair-monument
  build into the World Events project's Dragon milestone, or wait for a
  real spec doc before giving it independent status.
- **KOBA Adaptive Capacity** and **KOBA Building Skin System** — both specs
  explicitly describe themselves as *modules inside KOBA Core*, not
  standalone products a server owner would install on their own (unlike
  MOBO, the Submarine, or the monuments, which are each explicitly
  sold/installed independently). They're listed above as Tier 1 line items
  with their own roadmap outlines because they're substantial enough to
  track separately, but they likely belong in the `koba-core` repo as
  modules rather than as separate repos — revisit once `koba-core`'s repo
  structure actually exists.
- **A generic "Marketplace" project** — KOBA Live, KOBAid, and the Creator
  Ecosystem docs all *refer to* "KOBA.GAMES Marketplace" / "the storefront"
  as something that exists or will exist, but none of the 22 docs is itself
  a marketplace/storefront spec. Scoping a Marketplace project now would be
  inventing requirements no doc actually states. Treat it as an acknowledged
  gap, not a project, until a real marketplace spec shows up.
- **KOBA Mega Yacht vs KOBA Mobile Yacht as two projects** — flagged in §11
  as likely the same product described from two angles (gameplay-event doc
  vs. Blender-construction doc). Splitting them into two projects now risks
  building two divergent yachts. Resolve the naming/identity question with
  the user before creating two separate project scopes.
- **The "Koba engine" Universal Content Engine doc as a project separate
  from KOBA Creator Engine** — it describes the same ambition (a
  multi-target, data-driven content factory) as the master
  five-layer spec that `koba_creator_engine`'s own `README.md`/
  `ARCHITECTURE_ASSESSMENT.md` already treat as this repo's real target.
  The two documents haven't been reconciled (different layer models,
  different CLI surface: `koba project create` vs. `asset-factory create`),
  but that's a backlog/reconciliation task *within* KOBA Creator Engine, not
  grounds for a second engine project.
