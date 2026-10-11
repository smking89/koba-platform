"""Pre-export asset validation. Produces a readable pass/warn/fail report."""
import bpy
import bmesh

from core.naming import PREFIXES


class ValidationResult:
    def __init__(self):
        self.checks = []  # list of (label, status, detail) status in PASS/WARN/FAIL

    def add(self, label, status, detail=""):
        self.checks.append((label, status, detail))

    @property
    def passed(self):
        return all(s != "FAIL" for _, s, _ in self.checks)

    def report(self):
        lines = ["ASSET VALIDATION", ""]
        for label, status, detail in self.checks:
            line = f"[{status}] {label}"
            if detail:
                line += f" — {detail}"
            lines.append(line)
        return "\n".join(lines)


def _poly_count(obj):
    return len(obj.data.polygons) if obj.type == "MESH" else 0


def validate_asset(asset, poly_budget=None):
    result = ValidationResult()

    if not asset.geometry_objects:
        result.add("Geometry", "FAIL", "no geometry objects registered")
    else:
        non_manifold_objs = []
        for obj in asset.geometry_objects:
            if obj.type != "MESH":
                continue
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bad_edges = [e for e in bm.edges if not e.is_manifold]
            bm.free()
            if bad_edges:
                non_manifold_objs.append(obj.name)
        if non_manifold_objs:
            result.add("Geometry", "WARNING", f"non-manifold edges in: {', '.join(non_manifold_objs)}")
        else:
            result.add("Geometry", "PASS")

    total_polys = sum(_poly_count(o) for o in asset.geometry_objects)
    if poly_budget and total_polys > poly_budget:
        result.add("Poly budget", "WARNING", f"{total_polys} polys exceeds budget {poly_budget}")
    else:
        result.add("Poly budget", "PASS", f"{total_polys} polys")

    if not asset.material_names:
        result.add("Materials", "WARNING", "no materials registered")
    else:
        missing_mat = [o.name for o in asset.geometry_objects if o.type == "MESH" and len(o.data.materials) == 0]
        if missing_mat:
            result.add("Materials", "WARNING", f"objects with no material slot: {', '.join(missing_mat)}")
        else:
            result.add("Materials", "PASS")

    no_uv = [o.name for o in asset.geometry_objects if o.type == "MESH" and len(o.data.uv_layers) == 0]
    if no_uv:
        result.add("UVs", "WARNING", f"missing UVs: {', '.join(no_uv)}")
    else:
        result.add("UVs", "PASS")

    known_prefixes = tuple(PREFIXES.values())
    bad_names = [o.name for o in asset.geometry_objects if not o.name.startswith(known_prefixes)]
    if bad_names:
        result.add("Naming", "WARNING", f"non-conforming names: {', '.join(bad_names)}")
    else:
        result.add("Naming", "PASS")

    unapplied = [o.name for o in asset.geometry_objects if tuple(o.scale) != (1.0, 1.0, 1.0)]
    if unapplied:
        result.add("Transforms", "WARNING", f"unapplied scale on: {', '.join(unapplied)}")
    else:
        result.add("Transforms", "PASS")

    if asset.collision_objects:
        result.add("Collision", "PASS")
    else:
        result.add("Collision", "WARNING", "no collision geometry")

    if asset.lod_objects:
        result.add("LOD", "PASS", f"levels: {sorted(asset.lod_objects.keys())}")
    else:
        result.add("LOD", "WARNING", "no LODs generated")

    rig_detail = ", ".join(r.get("part", "?") for r in asset.rig) if asset.rig else "no rig"
    result.add("Rig", "PASS" if asset.rig else "WARNING", rig_detail)
    result.add("Animation", "PASS" if asset.animations else "WARNING", "" if asset.animations else "no animation")

    return result
