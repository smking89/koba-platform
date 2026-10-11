from tests.test_assembly_furniture import build_furniture_showcase

asset, counts = build_furniture_showcase(interactive=True)
from core.scene import frame_objects
frame_objects(asset.geometry_objects)
print("Live asset created:", asset.summary())
print("Counts:", counts)
