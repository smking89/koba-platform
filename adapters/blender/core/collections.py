"""Scene collection organization so generated assets don't dump hundreds
of objects into the default Collection."""
import bpy

STANDARD_SUBCOLLECTIONS = ("GEO", "GEO_DETAIL", "MATERIALS_REF", "COLLISION", "RIG", "ANIMATION", "LIGHTS")


def get_or_create(name, parent=None):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def build_asset_collections(asset_name):
    """Create the standard ASSET_<name> collection hierarchy and return a dict of them."""
    root = get_or_create(f"ASSET_{asset_name}")
    subs = {sub: get_or_create(f"{sub}_{asset_name}", parent=root) for sub in STANDARD_SUBCOLLECTIONS}
    subs["ROOT"] = root
    return subs


def link_only(obj, collection):
    """Link obj to `collection` and unlink it from every other collection it's in."""
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
