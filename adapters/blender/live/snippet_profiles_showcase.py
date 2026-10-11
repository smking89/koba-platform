from tests.test_geometry_profiles import build_profiles_showcase

asset, counts = build_profiles_showcase(interactive=True)
from core.scene import frame_objects
frame_objects(asset.geometry_objects)
print("Live asset created:", asset.summary())
print("Counts:", counts)
