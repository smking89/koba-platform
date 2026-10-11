"""Product Type Registry (master spec section 12's Product Manifest
"Type" field, formalized — the spec explicitly calls out "Monuments (as
a KOBA product type, not just 'a big Blender scene')"). Mirrors
validation/validation_registry.py's honest-registry pattern: each
declared product type lists required manifest metadata fields and which
real validators (from validation.validation_registry) apply — so
registering a project as a given product type means something checkable,
not just a free-form string tag (which is all core.project.create_project's
`--type` has ever been).

Scope honesty, stated plainly: none of these product types get a real
runtime — there is no game engine/KOBA Core in this environment (see
ROADMAP.md's integrations/ section). What's real here is:
  - schema validation of declared metadata (always real, always enforced)
  - for product types with required_validators, those are the SAME real
    validators validation_registry already tracks — `cui` ties to the
    real texture validator, `monument`/`vehicle` tie to the real Blender
    geometry/performance validators. `npc` and `event` have NO required
    validators: there is no character-rigging or scripting-trigger system
    to validate against, so their schemas exist to prove the product-type
    CONCEPT (declared, typed metadata) without fabricating runtime
    enforcement that doesn't exist.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from validation.validation_registry import is_implemented


@dataclass
class ProductTypeSchema:
    product_type: str
    required_metadata: Dict[str, object]  # field_name -> expected type (or tuple of types)
    required_validators: List[str] = field(default_factory=list)
    asset_backing: Optional[str] = None  # "blend" | "texture" | None
    notes: str = ""


class UnknownProductType(Exception):
    pass


class ProductMetadataError(Exception):
    """Raised instead of silently accepting a product registration with
    missing/wrong-typed metadata — a declared product type is a real
    contract, not a suggestion."""


_REGISTRY = {
    "cui": ProductTypeSchema(
        "cui",
        required_metadata={"resolution_width": int, "resolution_height": int, "anchor": str},
        required_validators=["texture"],
        asset_backing="texture",
        notes="A UI prefab asset (panel/icon/HUD element) — a flat raster texture with "
              "declared layout metadata. Validated for real via validation.texture_validator "
              "against the declared resolution. No interaction/widget runtime exists to "
              "validate behavior against.",
    ),
    "monument": ProductTypeSchema(
        "monument",
        required_metadata={"height_meters": (int, float), "era": str, "landmark_importance": str},
        required_validators=["geometry", "asset"],
        asset_backing="blend",
        notes="A static landmark prop — real geometry/asset validation via the existing "
              "Blender validator (adapters/blender/core/validation.py), same as any other "
              "generated asset. The master spec's own example of 'a product type, not just "
              "a big Blender scene.'",
    ),
    "vehicle": ProductTypeSchema(
        "vehicle",
        required_metadata={"vehicle_class": str, "seats": int},
        required_validators=["geometry", "asset", "performance"],
        asset_backing="blend",
        notes="A drivable/rideable asset (boat/jetski/yacht/car/...) — real geometry + "
              "performance-budget validation, the same real validators validate_blend already "
              "uses. No vehicle-physics/drivetrain runtime exists to validate against.",
    ),
    "npc": ProductTypeSchema(
        "npc",
        required_metadata={"faction": str, "role": str},
        required_validators=[],
        asset_backing=None,
        notes="Metadata-only. No character-rigging, AI-behavior, or dialogue system exists "
              "in this codebase to validate an NPC against — this schema proves the "
              "product-type concept (declared, typed metadata) without fabricating runtime "
              "enforcement.",
    ),
    "event": ProductTypeSchema(
        "event",
        required_metadata={"trigger_type": str, "description": str},
        required_validators=[],
        asset_backing=None,
        notes="Metadata-only. No scripting/trigger-execution runtime exists in this codebase "
              "to validate an event against — same honesty caveat as npc.",
    ),
    "building_skin": ProductTypeSchema(
        "building_skin",
        required_metadata={"tile_size_meters": (int, float), "material_category": str},
        required_validators=["texture"],
        asset_backing="texture",
        notes="A tileable facade/material texture — real validation via the same real "
              "texture validator CUI uses, PLUS a real seamless-tiling check "
              "(ImageMagickAdapter.check_seamless_tiling — actual opposite-edge pixel "
              "comparison, not a heuristic), since tiling cleanly is the entire point of "
              "this asset type and CUI panels don't need it.",
    ),
    "audio": ProductTypeSchema(
        "audio",
        required_metadata={"max_duration_seconds": (int, float), "category": str},
        required_validators=[],
        asset_backing="audio",
        notes="Backed by a real audio file, validated for real via "
              "validation.audio_validator.validate_audio() (duration/sample-rate/channels, "
              "ffprobe-backed) — called directly, not through this registry's "
              "required_validators, since 'audio' isn't one of validation_registry's 17 "
              "formal types (the master spec's validation/ section doesn't name an "
              "audio_validator). required_validators stays [] so unsupported_validators() "
              "never has to guess at an id that doesn't exist in that registry.",
    ),
    "vfx": ProductTypeSchema(
        "vfx",
        required_metadata={"effect_type": str, "duration_frames": int},
        required_validators=["geometry", "asset", "performance"],
        asset_backing="blend",
        notes="A particle/effect Blender scene — real geometry + performance-budget "
              "validation, same real validators monument/vehicle already use. No "
              "particle-simulation-at-runtime or compositing-pipeline validation exists "
              "beyond what the standard Blender asset validators already check.",
    ),
}


def get(product_type):
    schema = _REGISTRY.get(product_type)
    if schema is None:
        raise UnknownProductType(f"no such product type: '{product_type}' — known: {sorted(_REGISTRY)}")
    return schema


def list_product_types():
    return dict(_REGISTRY)


def validate_metadata(product_type, metadata):
    """Checks `metadata` against the product type's required_metadata
    schema — every required field present AND of the declared type.
    Raises ProductMetadataError listing every problem at once (not just
    the first), so a caller doesn't have to fix-and-rerun repeatedly."""
    schema = get(product_type)
    problems = []
    for field_name, expected_type in schema.required_metadata.items():
        if field_name not in metadata:
            problems.append(f"missing required field '{field_name}'")
            continue
        if not isinstance(metadata[field_name], expected_type):
            problems.append(
                f"field '{field_name}' must be {expected_type}, got {type(metadata[field_name]).__name__}"
            )
    if problems:
        raise ProductMetadataError(f"product type '{product_type}': " + "; ".join(problems))
    return True


def unsupported_validators(product_type):
    """Of this product type's required_validators, which ones are
    actually IMPLEMENTED in validation_registry right now vs still
    UNSUPPORTED — so a caller knows exactly how much real enforcement it
    gets, not just a list of names."""
    schema = get(product_type)
    return [v for v in schema.required_validators if not is_implemented(v)]
