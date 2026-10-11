from tests.build_post_apocalyptic_chair import build_post_apocalyptic_chair

asset = build_post_apocalyptic_chair(interactive=True)
from core.scene import frame_objects
frame_objects(asset.geometry_objects)
print("Live asset created:", asset.summary())
