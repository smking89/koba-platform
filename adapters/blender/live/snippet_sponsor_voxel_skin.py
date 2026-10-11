import bpy
from core.scene import frame_objects, clear_asset_collection
from generators.voxel_sponsor_skin import build_sponsor_voxel_skin

default_cube = bpy.data.objects.get("Cube")
if default_cube is not None:
    bpy.data.objects.remove(default_cube, do_unlink=True)

clear_asset_collection("SponsorSkin_CubeClashHouseAd")

asset = build_sponsor_voxel_skin(
    advertiser_name="CubeClashHouseAd",
    primary_hex="#FFC400",
    secondary_hex="#1E90FF",
    logo_path="/home/koba/Desktop/Cube-Clash-logo.png",
)
frame_objects(asset.geometry_objects)
print("Live asset created:", asset.summary())
