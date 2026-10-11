"""Validation Registry (master spec's `validation/validation_registry`) —
a formal, honest catalog of the validator types the spec names (17 of
them, under `validation/`). Master spec Rule 11 (VALIDATION AUTHORITY):
"AI is NOT the final authority... The system must never convert 'AI says
PASS' into 'KOBA validation PASS' without actual validator evidence."
This registry is the single place that says, for each named validator
type, whether a real deterministic implementation exists (and where) or
not — so nothing downstream can silently assume a validator ran when it
didn't, and no caller has to guess which of the spec's 17 named
categories this codebase actually covers.

3 of the 17 have a real implementation today:
- geometry (+ topology/collision-presence/material as sub-checks) via
  adapters/blender/core/validation.py's validate_asset()
- performance via
  adapters/blender/optimization/performance_validator.py's
  validate_performance()
- texture via validation/texture_validator.py's validate_texture() — the
  one entry point here that does NOT need bpy (textures are plain image
  files, not Blender scenes), added once a real caller (the `cui` product
  type) needed real texture validation instead of metadata-only checks

The first two run inside Blender's own Python (they need bpy) — this
registry has no bpy dependency and never calls them directly; it's a
declarative catalog the orchestration layer (CLI, tool contracts) can
consult to
answer "does a validator for X exist, and if not, why," the same
UNSUPPORTED_CAPABILITY discipline used everywhere else in this codebase
(core.detection, repair_engine.classify_failure).
"""
from dataclasses import dataclass, field
from typing import List, Optional

IMPLEMENTED = "IMPLEMENTED"
UNSUPPORTED = "UNSUPPORTED"


@dataclass
class ValidatorEntry:
    validator_id: str
    status: str  # IMPLEMENTED | UNSUPPORTED
    entry_point: Optional[str] = None  # dotted path, only set when IMPLEMENTED
    covers: List[str] = field(default_factory=list)  # human-readable sub-checks, only set when IMPLEMENTED
    reason: Optional[str] = None  # only set when UNSUPPORTED — why not


class UnknownValidator(Exception):
    pass


_REGISTRY = {
    "geometry": ValidatorEntry(
        "geometry", IMPLEMENTED,
        entry_point="adapters.blender.core.validation.validate_asset",
        covers=["manifold edges", "naming convention", "UV presence",
                "unapplied transforms", "material slot presence"],
    ),
    "topology": ValidatorEntry(
        "topology", IMPLEMENTED,
        entry_point="adapters.blender.core.validation.validate_asset",
        covers=["the manifold-edge check doubles as the only real topology signal today"],
    ),
    "collision": ValidatorEntry(
        "collision", IMPLEMENTED,
        entry_point="adapters.blender.core.validation.validate_asset",
        covers=["presence of collision geometry only — not collision-mesh "
                "correctness, leak-testing, or convexity"],
    ),
    "material": ValidatorEntry(
        "material", IMPLEMENTED,
        entry_point="adapters.blender.core.validation.validate_asset",
        covers=["material slot presence — not shader-graph or "
                "texture-binding correctness"],
    ),
    "asset": ValidatorEntry(
        "asset", IMPLEMENTED,
        entry_point="adapters.blender.core.validation.validate_asset",
        covers=["the composite report itself: geometry + material + UV + "
                "naming + transforms + collision + LOD"],
    ),
    "performance": ValidatorEntry(
        "performance", IMPLEMENTED,
        entry_point="adapters.blender.optimization.performance_validator.validate_performance",
        covers=["entity/mesh/triangle/material/light/physics/animated-object "
                "counts vs. a PC performance profile",
                "collision/LOD/culling coverage"],
    ),
    "texture": ValidatorEntry(
        "texture", IMPLEMENTED,
        entry_point="validation.texture_validator.validate_texture",
        covers=["resolution floor (width/height)", "power-of-two dimensions (warning only)",
                "format"],
    ),
    "dependency": ValidatorEntry(
        "dependency", UNSUPPORTED,
        reason="core.artifact_graph's find_affected()/has_changed() provide real "
               "dependency-impact traversal, but that's graph analysis, not a "
               "PASS/FAIL validator",
    ),
    "compatibility": ValidatorEntry(
        "compatibility", UNSUPPORTED,
        reason="no engine/platform-version compatibility checking exists",
    ),
    "manifest": ValidatorEntry(
        "manifest", UNSUPPORTED,
        reason="core.manifest.py covers a small slice (assets/exports/errors) "
               "with no PASS/FAIL validation of manifest completeness",
    ),
    "runtime": ValidatorEntry(
        "runtime", UNSUPPORTED,
        reason="no runtime/game-engine execution environment exists to validate against",
    ),
    "interaction": ValidatorEntry(
        "interaction", UNSUPPORTED,
        reason="no interactive/gameplay content type exists yet",
    ),
    "npc": ValidatorEntry(
        "npc", UNSUPPORTED,
        reason="no NPC content type exists yet",
    ),
    "event": ValidatorEntry(
        "event", UNSUPPORTED,
        reason="no event content type exists yet",
    ),
    "memory": ValidatorEntry(
        "memory", UNSUPPORTED,
        reason="no runtime memory-budget measurement exists",
    ),
    "network": ValidatorEntry(
        "network", UNSUPPORTED,
        reason="no networked/multiplayer content exists",
    ),
    "security": ValidatorEntry(
        "security", UNSUPPORTED,
        reason="no sandboxing/credential/malware-scanning validator exists "
               "(see ROADMAP.md's security/ gap)",
    ),
}


def get(validator_id):
    entry = _REGISTRY.get(validator_id)
    if entry is None:
        raise UnknownValidator(f"no such validator type: '{validator_id}' — known: {sorted(_REGISTRY)}")
    return entry


def list_validators():
    return dict(_REGISTRY)


def is_implemented(validator_id):
    return get(validator_id).status == IMPLEMENTED
