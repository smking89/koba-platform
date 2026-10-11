"""Per-object runtime-behavior metadata.

This is the metadata schema the optimization pipeline (instancing,
static-merging, culling, the performance validator) reads to decide what
it's allowed to do with an object — it must never guess by inspecting
geometry alone. A hinge-driven door panel and a static wall box can look
identical to a mesh-only inspection; only this metadata says one may be
merged into static geometry and the other must not be.

Defaults are deliberately conservative: a caller that says nothing gets a
plain static, mergeable, cullable prop — never accidentally treated as
safe to merge if it might be animated/interactive, since those default
False/None only when explicitly set True.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class EntityMetadata:
    category: str = "prop"
    static: bool = True
    dynamic: bool = False
    interactive: bool = False
    destructible: bool = False
    physics: bool = False
    animated: bool = False
    collision_required: bool = False
    instanceable: bool = False
    mergeable: bool = True
    lod_required: bool = False
    cullable: bool = True
    visibility_group: Optional[str] = None
    importance: str = "medium"  # "hero" | "high" | "medium" | "low" | "trivial"

    def as_dict(self):
        return {
            "category": self.category,
            "static": self.static,
            "dynamic": self.dynamic,
            "interactive": self.interactive,
            "destructible": self.destructible,
            "physics": self.physics,
            "animated": self.animated,
            "collision_required": self.collision_required,
            "instanceable": self.instanceable,
            "mergeable": self.mergeable,
            "lod_required": self.lod_required,
            "cullable": self.cullable,
            "visibility_group": self.visibility_group,
            "importance": self.importance,
        }


def for_static_prop(category="prop", importance="medium", visibility_group=None):
    return EntityMetadata(category=category, static=True, mergeable=True, cullable=True,
                           importance=importance, visibility_group=visibility_group)


def for_instanced_prop(category="prop", importance="low", visibility_group=None):
    """A repeated prop (chair, crate, light fixture, ...) — instanceable,
    NOT mergeable (merging would defeat the point of sharing one mesh)."""
    return EntityMetadata(category=category, static=True, instanceable=True, mergeable=False,
                           cullable=True, importance=importance, visibility_group=visibility_group)


def for_mechanism(category="mechanism", importance="high", collision_required=True):
    """A rigged, animated part (door, crane boom, elevator, ...) — must
    never be merged or instanced away from its own rig."""
    return EntityMetadata(category=category, static=False, dynamic=True, animated=True,
                           collision_required=collision_required, instanceable=False,
                           mergeable=False, cullable=False, importance=importance)


def for_rigid_group_member(category="prop", importance="medium"):
    """An object with no animation of its own, but whose PARENT is animated
    (e.g. a crane cab riding the slew turret) — it genuinely moves in world
    space frame to frame, so it isn't `static`, but it's rigidly fixed
    relative to its siblings under that same parent, so it's still safe to
    merge with them (the merged result just inherits the same parent)."""
    return EntityMetadata(category=category, static=False, dynamic=True, animated=False,
                           mergeable=True, cullable=True, instanceable=False, importance=importance)


def for_hero_asset(category="hero", collision_required=True):
    """A player-visible focal object — never culled/merged/instanced away,
    always gets LOD."""
    return EntityMetadata(category=category, static=True, collision_required=collision_required,
                           instanceable=False, mergeable=False, lod_required=True,
                           cullable=False, importance="hero")
