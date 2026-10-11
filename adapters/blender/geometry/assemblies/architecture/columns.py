"""Column / pillar assemblies — base plinth + shaft + capital, real
parts instead of a single bare cylinder/box.
"""
from core.entity_metadata import for_static_prop
from core.naming import name as make_name
from core.transforms import apply_all_transforms
from geometry.primitives import create_box, create_cylinder


def build_column(asset, name_prefix, x, y, z, height=3.0, radius=0.3, style="round", mat=None,
                  base_height=0.2, capital_height=0.2):
    """z is the floor (column base). `style` "round" uses cylinders for
    base/shaft/capital; "square" uses boxes of equivalent footprint.
    Returns {"base", "shaft", "capital"}."""
    shaft_height = height - base_height - capital_height
    parts = {}

    if style == "round":
        base = create_cylinder(make_name("mesh", asset.name, f"{name_prefix}_base"), radius=radius * 1.3, depth=base_height, vertices=24, material=mat)
        shaft = create_cylinder(make_name("mesh", asset.name, f"{name_prefix}_shaft"), radius=radius, depth=shaft_height, vertices=24, material=mat)
        capital = create_cylinder(make_name("mesh", asset.name, f"{name_prefix}_capital"), radius=radius * 1.3, depth=capital_height, vertices=24, material=mat)
    else:
        side = radius * 2
        base = create_box(make_name("mesh", asset.name, f"{name_prefix}_base"), width=side * 1.3, depth=side * 1.3, height=base_height, bevel_width=0.02, material=mat)
        shaft = create_box(make_name("mesh", asset.name, f"{name_prefix}_shaft"), width=side, depth=side, height=shaft_height, bevel_width=0.02, material=mat)
        capital = create_box(make_name("mesh", asset.name, f"{name_prefix}_capital"), width=side * 1.3, depth=side * 1.3, height=capital_height, bevel_width=0.02, material=mat)

    base.location.x, base.location.y, base.location.z = x, y, z
    shaft.location.x, shaft.location.y, shaft.location.z = x, y, z + base_height
    capital.location.x, capital.location.y, capital.location.z = x, y, z + base_height + shaft_height

    for part_name, obj in (("base", base), ("shaft", shaft), ("capital", capital)):
        apply_all_transforms(obj)
        asset.add_geometry(obj, metadata=for_static_prop(category="architecture_column", importance="medium"))
        parts[part_name] = obj
    return parts
