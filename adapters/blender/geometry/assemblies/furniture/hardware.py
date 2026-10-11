"""Shared small hardware pieces — turned legs/feet, drawer knobs, and
decorative studs — built from geometry.profiles/geometry.detailing so
every furniture assembly (beds, desks, seating, storage) pulls from one
real, decorative profile instead of each file defining its own plain
cylinder. Added 2026-10-01 as part of moving lathe/inset/array-detail
techniques out of isolated test demos and into the actual factory
assemblies.
"""
from core.entity_metadata import for_static_prop
from core.naming import name as make_name
from geometry.primitives import create_cylinder
from geometry.profiles import lathe_profile


def turned_leg_profile(height, radius):
    """A real decorative turned-leg vector path: a flared foot, a
    collar, a waisted taper, a second collar, a straight run to the
    top — explicit notches/collars/taper, not a uniform cylinder."""
    return [
        (radius * 1.4, 0.0),                # flared foot
        (radius * 1.4, height * 0.04),
        (radius * 0.85, height * 0.09),      # notch down from the foot
        (radius * 1.15, height * 0.16),      # lower collar
        (radius * 1.15, height * 0.20),
        (radius * 0.5, height * 0.48),       # waisted taper (the "turned" look)
        (radius * 0.5, height * 0.52),
        (radius * 1.1, height * 0.74),       # upper collar
        (radius * 1.1, height * 0.78),
        (radius * 0.8, height * 0.85),       # notch below the top
        (radius * 0.8, height),
    ]


def build_turned_leg(asset, part_name, height, radius=0.03, material=None, steps=12):
    """A real lathed furniture leg (geometry.profiles.lathe_profile)
    with explicit collars/notches/taper — the shared leg every
    bed/sofa/desk/lounge assembly should call instead of a plain
    cylinder. Returns the leg Object, base at local Z=0."""
    profile = turned_leg_profile(height, radius)
    leg = lathe_profile(make_name("mesh", asset.name, part_name), profile, steps=steps, material=material)
    asset.add_geometry(leg, metadata=for_static_prop(category="furniture_leg", importance="low"))
    return leg


def build_drawer_knob(asset, part_name, radius=0.015, depth=0.04, material=None):
    """A small turned knob (a tiny lathed profile — a real round
    handle silhouette, not a flat box) for drawer/door fronts. Returns
    the knob Object; caller positions it (it protrudes along +Y from
    its own local origin)."""
    profile = [
        (radius * 0.3, 0.0),
        (radius * 0.9, depth * 0.25),
        (radius, depth * 0.6),
        (radius * 0.6, depth),
    ]
    knob = lathe_profile(make_name("mesh", asset.name, part_name), profile, steps=10, material=material)
    knob.rotation_euler.x = 1.5708  # lathe revolves around local Z; tip the knob to point along Y
    asset.add_geometry(knob, metadata=for_static_prop(category="furniture_hardware", importance="low"))
    return knob


def build_stud_source(asset, part_name, radius=0.012, height=0.015, material=None):
    """A small decorative stud/rivet source object for
    geometry.detailing.distribute_array_detail — real shared-mesh
    instances placed along a frame edge, border, or seam."""
    stud = create_cylinder(make_name("mesh", asset.name, part_name), radius=radius, depth=height, vertices=10, material=material)
    asset.add_geometry(stud, metadata=for_static_prop(category="furniture_hardware", importance="low"))
    return stud
