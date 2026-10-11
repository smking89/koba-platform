"""Interaction-point markers (master prompt §33/§39's plugin integration
map: `Casino.Slot.001`, `Hotel.Room.Standard.001.CardReader`, ...).

These are real Blender Empty objects placed at a physical location and
named with the exact plugin-facing identifier — the MAP's half of the
map/plugin split (master prompt §46): this module places WHERE a future
plugin hook goes, never what that hook does. Deliberately NOT routed
through Asset.add_geometry()/EntityMetadata — empties have no mesh data,
so they don't belong in the poly/UV/collision/LOD pipeline that exists
for real geometry; they get their own small, parallel list instead.
"""
import bpy

INTERACTION_PROP = "koba_interaction_point"


def add_interaction_point(asset, name, location=(0.0, 0.0, 0.0)):
    """Creates an Empty named exactly `name` (the plugin integration
    identifier, e.g. "Casino.Slot.001"), places it at `location`, links
    it into the asset's ROOT collection, and tracks it on
    asset.interaction_points (a plain list this module adds to Asset
    instances on first use — Asset itself stays ignorant of this
    concept, same separation as the map/plugin split above)."""
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 0.4
    empty.location = location
    empty[INTERACTION_PROP] = True
    asset.collections["ROOT"].objects.link(empty)

    if not hasattr(asset, "interaction_points"):
        asset.interaction_points = []
    asset.interaction_points.append(empty)
    return empty
