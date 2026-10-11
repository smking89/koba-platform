"""KOBA Performance Report — inspects a built Asset against a PC
performance profile (config/performance_profiles.py) and reports whether
it's within budget. Reads core.entity_metadata that generators already
attached; does not guess by inspecting geometry alone.
"""
import bpy

from config.performance_profiles import get_profile
from geometry.instancing import count_unique_meshes, detect_instanceable_candidates
from optimization.culling import culling_coverage


def _triangle_count(obj):
    if obj.type != "MESH":
        return 0
    # A quad counts as 2 triangles for a fair budget comparison — polygons()
    # alone underrepresents cost for non-triangulated meshes.
    return sum(max(len(p.vertices) - 2, 1) for p in obj.data.polygons)


def collect_metrics(asset):
    bpy.context.view_layer.update()
    objects = asset.geometry_objects

    unique_meshes = count_unique_meshes(objects)
    instanced = sum(1 for o in objects if asset.get_metadata(o).instanceable)
    triangles = sum(_triangle_count(o) for o in objects)
    dynamic_lights = sum(1 for o in bpy.data.objects if o.type == "LIGHT" and o.data.type != "SUN")
    physics_objects = sum(1 for o in objects if asset.get_metadata(o).physics)
    animated_objects = sum(1 for o in objects if asset.get_metadata(o).animated) + len(asset.rig)

    needs_collision = [o for o in objects if asset.get_metadata(o).collision_required]
    collision_coverage = (
        1.0 if not needs_collision else
        min(1.0, len(asset.collision_objects) / len(needs_collision))
    )

    needs_lod = [o for o in objects if asset.get_metadata(o).lod_required]
    lod_covered_names = {n for objs in asset.lod_objects.values() for n in (o.name for o in objs)}
    lod_coverage = (
        1.0 if not needs_lod else
        sum(1 for o in needs_lod if o.name in lod_covered_names) / len(needs_lod)
    )

    return {
        "entity_count": len(objects),
        "unique_meshes": unique_meshes,
        "instanced_count": instanced,
        "triangles": triangles,
        "materials": len(asset.material_names),
        "dynamic_lights": dynamic_lights,
        "physics_objects": physics_objects,
        "animated_objects": animated_objects,
        "collision_coverage": round(collision_coverage, 2),
        "lod_coverage": round(lod_coverage, 2),
        "culling_coverage": culling_coverage(asset, objects),
    }


class PerformanceReport:
    def __init__(self, profile_name, metrics, budget):
        self.profile_name = profile_name
        self.metrics = metrics
        self.budget = budget
        self.warnings = []
        self.failures = []

    @property
    def result(self):
        return "FAIL" if self.failures else "PASS"

    def report(self):
        lines = [f"KOBA PERFORMANCE REPORT (profile: {self.profile_name})", ""]
        m = self.metrics
        lines += [
            f"ENTITY COUNT        {m['entity_count']}",
            f"UNIQUE MESHES        {m['unique_meshes']}",
            f"INSTANCED            {m['instanced_count']}",
            f"TRIANGLES            {m['triangles']}",
            f"MATERIALS            {m['materials']}",
            f"DYNAMIC LIGHTS        {m['dynamic_lights']}",
            f"PHYSICS OBJECTS        {m['physics_objects']}",
            f"ANIMATED OBJECTS        {m['animated_objects']}",
            f"COLLISION COVERAGE        {m['collision_coverage'] * 100:.0f}%",
            f"LOD COVERAGE        {m['lod_coverage'] * 100:.0f}%",
            f"CULLING COVERAGE        {m['culling_coverage'] * 100:.0f}%",
            "",
            f"RESULT: {self.result}",
        ]
        if self.failures:
            lines.append("\nFAILURES (over budget):")
            lines += [f"  - {f}" for f in self.failures]
        if self.warnings:
            lines.append("\nWARNINGS:")
            lines += [f"  - {w}" for w in self.warnings]
        return "\n".join(lines)


_BUDGET_KEYS = {
    "entity_count": "max_visible_entities",
    "unique_meshes": "max_unique_meshes",
    "triangles": "max_triangles",
    "materials": "max_materials",
    "dynamic_lights": "max_dynamic_lights",
    "physics_objects": "max_physics_objects",
    "animated_objects": "max_animated_objects",
}


def validate_performance(asset, profile_name="60fps_standard"):
    budget = get_profile(profile_name)
    metrics = collect_metrics(asset)
    report = PerformanceReport(profile_name, metrics, budget)

    for metric_key, budget_key in _BUDGET_KEYS.items():
        limit = budget.get(budget_key)
        if limit is None:
            continue
        value = metrics[metric_key]
        if value > limit:
            report.failures.append(f"{metric_key} = {value} exceeds {budget_key} = {limit}")

    candidates = detect_instanceable_candidates(asset)
    if candidates:
        for c in candidates:
            report.warnings.append(
                f"{c['count']} objects look like duplicates of the same shape but use "
                f"{c['unique_mesh_count']} separate mesh datablocks — candidates for "
                f"geometry.instancing.create_instance: {c['object_names'][:5]}"
                + (f" (+{len(c['object_names']) - 5} more)" if len(c['object_names']) > 5 else "")
            )
    elif metrics["entity_count"] > 0 and metrics["unique_meshes"] > 0:
        reuse_ratio = metrics["entity_count"] / metrics["unique_meshes"]
        if reuse_ratio < 1.5 and metrics["entity_count"] > 10:
            report.warnings.append(
                f"low instancing reuse ({reuse_ratio:.1f}x) for {metrics['entity_count']} entities — "
                "consider geometry.instancing.create_instance for repeated props"
            )

    if metrics["collision_coverage"] < 1.0:
        report.warnings.append(f"collision coverage only {metrics['collision_coverage']*100:.0f}% of objects that need it")
    if metrics["lod_coverage"] < 1.0:
        report.warnings.append(f"LOD coverage only {metrics['lod_coverage']*100:.0f}% of objects that need it")
    if metrics["culling_coverage"] < 1.0:
        report.warnings.append(
            f"culling coverage only {metrics['culling_coverage']*100:.0f}% — "
            "run optimization.culling.assign_visibility_distances before shipping"
        )

    return report
