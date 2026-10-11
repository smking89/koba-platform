"""PC-ONLY performance budgets. Koba Creator Engine targets PC games/
environments/cinematics exclusively — do NOT add console (Xbox/
PlayStation) profiles or console certification budgets here.

A plain Python dict, not YAML — Blender's bundled Python interpreter has
no pyyaml installed (verified directly, not assumed), and this project
already established the convention of plain-Python config for anything
loaded inside Blender (see export_config.py).

Numbers are starting points for a single generated ASSET or scene, not
an entire shipped game — tune per project. None means no limit.
"""

PROFILES = {
    "60fps_standard": dict(
        target_fps=60, max_visible_entities=2000, max_unique_meshes=300,
        max_triangles=2_000_000, max_materials=80, max_dynamic_lights=32,
        max_physics_objects=64, max_animated_objects=64, texture_memory_mb=2048,
    ),
    "90fps_vr": dict(
        target_fps=90, max_visible_entities=1200, max_unique_meshes=200,
        max_triangles=1_200_000, max_materials=60, max_dynamic_lights=16,
        max_physics_objects=48, max_animated_objects=48, texture_memory_mb=1536,
    ),
    "120fps_competitive": dict(
        target_fps=120, max_visible_entities=900, max_unique_meshes=150,
        max_triangles=800_000, max_materials=48, max_dynamic_lights=12,
        max_physics_objects=32, max_animated_objects=32, texture_memory_mb=1024,
    ),
    "144fps_enthusiast": dict(
        target_fps=144, max_visible_entities=700, max_unique_meshes=120,
        max_triangles=600_000, max_materials=40, max_dynamic_lights=10,
        max_physics_objects=24, max_animated_objects=24, texture_memory_mb=1024,
    ),
    "165fps_high_refresh": dict(
        target_fps=165, max_visible_entities=550, max_unique_meshes=100,
        max_triangles=450_000, max_materials=32, max_dynamic_lights=8,
        max_physics_objects=20, max_animated_objects=20, texture_memory_mb=768,
    ),
    "240fps_esports": dict(
        target_fps=240, max_visible_entities=350, max_unique_meshes=60,
        max_triangles=250_000, max_materials=24, max_dynamic_lights=4,
        max_physics_objects=12, max_animated_objects=12, texture_memory_mb=512,
    ),
    # No entity/triangle cap — for hero/cinematic renders, offline
    # turntables, marketing shots, etc. where interactive framerate
    # doesn't apply. Still sanity-checks material/light counts.
    "cinematic_unbudgeted": dict(
        target_fps=None, max_visible_entities=None, max_unique_meshes=None,
        max_triangles=None, max_materials=200, max_dynamic_lights=64,
        max_physics_objects=None, max_animated_objects=None, texture_memory_mb=8192,
    ),
}


def get_profile(name):
    if name not in PROFILES:
        raise ValueError(f"Unknown performance profile '{name}'. Known: {sorted(PROFILES)}")
    return PROFILES[name]
