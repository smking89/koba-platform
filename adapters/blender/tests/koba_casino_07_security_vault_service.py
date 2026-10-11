"""KOBA CASINO & RESORT — Phase 7: Security, Vault, Service.

Per KOBA_CASINO_RESORT_ROADMAP.md's Phase 7 / master prompt §21-23:
the Security Facility (office/CCTV/control/equipment), the Casino
Vault (reinforced entrance, lobby, an enormous vault door, secure +
prize storage, an emergency route), and Staff/Service areas (laundry,
housekeeping, maintenance/electrical, storage, staff room, employee
entrance, loading dock).

Sits on Floor8_SecurityVault's footprint from Phase 2 (tier2 band ->
23x17 usable, floor surface at z=40.4 = Floor8's z_cursor=40.0 +
Phase 2's SLAB_THICKNESS=0.4).

Prompt §22 explicitly requires the vault to support a future "KOBA
CASINO HEIST" event and warns against inaccessible geometry — the
vault lobby and emergency route are deliberately left as OPEN floor
areas (no walls), not sealed rooms, so nothing here blocks that future
access.

Honest consolidation, stated plainly: Guard Room + Access-Control Room
+ Emergency Control Area (3 named rooms in §21) are combined into one
physical "Control Room" for this blockout, and Maintenance + Electrical
(2 named rooms in §23) are combined into one "Maintenance/Electrical"
room — distinct interaction points still exist for each original name,
but they share one enclosure rather than getting 5 separate tiny rooms.
The service elevator reuses Phase 2's existing elevator shaft (no new
shaft geometry here) — just a real interaction point at this floor's
landing.

Run with:
  <blender> -b --python tests/koba_casino_07_security_vault_service.py
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import bpy  # noqa: E402

from core.asset import Asset  # noqa: E402
from core.scene import prepare_scene, frame_objects  # noqa: E402
from core.transforms import apply_all_transforms, set_origin_to_bounds_bottom  # noqa: E402
from core.validation import validate_asset  # noqa: E402
from core.preview import render_preview  # noqa: E402
from core.entity_metadata import for_static_prop  # noqa: E402
from core.naming import name as make_name  # noqa: E402
from core.interaction_point import add_interaction_point  # noqa: E402
from geometry.primitives import create_box, create_cylinder, create_panel  # noqa: E402
from materials.stone import carved_stone  # noqa: E402
from materials.metal import galvanized_steel, bare_metal  # noqa: E402
from materials.wood import painted_wood  # noqa: E402
from optimization.collision import generate_box_collision  # noqa: E402
from optimization.lod import generate_decimated_lod  # noqa: E402
from export.exporter import export_asset  # noqa: E402
from config.blender_config import GENERATED_DIR  # noqa: E402

FLOOR_Z = 40.4  # Floor8_SecurityVault's slab top surface (Phase 2: z_cursor=40.0 + SLAB_THICKNESS=0.4)
WALL_HEIGHT = 2.5
WALL_THICKNESS = 0.2


def build_room_walls(asset, mats, label, cx, cy, width, depth, wall_mat_key="wall", door_mat_key="door"):
    half_w, half_d = width / 2, depth / 2
    segments = [
        (width, WALL_THICKNESS, 0.0, -half_d),
        (WALL_THICKNESS, depth, -half_w, 0.0),
        (WALL_THICKNESS, depth, half_w, 0.0),
    ]
    for i, (w, d, ox, oy) in enumerate(segments):
        seg = create_box(make_name("mesh", asset.name, f"{label}_Wall{i}"), width=w, depth=d, height=WALL_HEIGHT, material=mats[wall_mat_key])
        seg.location.x, seg.location.y, seg.location.z = cx + ox, cy + oy, FLOOR_Z
        apply_all_transforms(seg)
        asset.add_geometry(seg, metadata=for_static_prop(category="service_wall", importance="low"))

    door_gap = min(1.1, width * 0.35)
    side_w = (width - door_gap) / 2
    for sign in (-1, 1):
        seg = create_box(make_name("mesh", asset.name, f"{label}_NorthWall{sign}"), width=side_w, depth=WALL_THICKNESS, height=WALL_HEIGHT, material=mats[wall_mat_key])
        seg.location.x, seg.location.y, seg.location.z = cx + sign * (door_gap / 2 + side_w / 2), cy + half_d, FLOOR_Z
        apply_all_transforms(seg)
        asset.add_geometry(seg, metadata=for_static_prop(category="service_wall", importance="low"))

    door = create_panel(make_name("mesh", asset.name, f"{label}_Door"), width=door_gap, height=2.1, thickness=0.08, material=mats[door_mat_key])
    door.location.x, door.location.y, door.location.z = cx, cy + half_d, FLOOR_Z + 1.05
    apply_all_transforms(door)
    asset.add_geometry(door, metadata=for_static_prop(category="service_door", importance="high"))


def _box(asset, part, x, y, z, w, d, h, mat, category="service_prop", importance="medium"):
    obj = create_box(make_name("mesh", asset.name, part), width=w, depth=d, height=h, material=mat)
    obj.location.x, obj.location.y, obj.location.z = x, y, z
    apply_all_transforms(obj)
    asset.add_geometry(obj, metadata=for_static_prop(category=category, importance=importance))
    return obj


def build_security_vault_service(interactive=False):
    prepare_scene("KobaCasinoResort_SecurityVaultService", interactive)
    asset = Asset(name="KobaCasinoResort_SecurityVaultService", asset_type="monument")

    mats = {
        "wall": carved_stone(make_name("material", asset.name, "ServiceWall"), color=(0.5, 0.48, 0.45)),
        "door": painted_wood(make_name("material", asset.name, "ServiceDoor"), color=(0.3, 0.25, 0.2)),
        "vault_wall": galvanized_steel(make_name("material", asset.name, "VaultWall")),
        "vault_door": bare_metal(make_name("material", asset.name, "VaultDoorMetal")),
        "console": bare_metal(make_name("material", asset.name, "SecurityConsole")),
        "service_equip": galvanized_steel(make_name("material", asset.name, "ServiceEquipment")),
        "storage": painted_wood(make_name("material", asset.name, "StorageShelving")),
        "lobby_floor": carved_stone(make_name("material", asset.name, "VaultLobbyFloor"), color=(0.35, 0.33, 0.3)),
    }
    for mat in mats.values():
        asset.register_material(mat.name)

    # === SECURITY FACILITY (west) ===
    build_room_walls(asset, mats, "SecurityOffice", -9.0, -5.0, 3.0, 3.0)
    _box(asset, "SecurityOffice_Desk", -9.0, -5.3, FLOOR_Z, 1.5, 0.6, 0.9, mats["console"], category="security_furniture")
    add_interaction_point(asset, "Security.Office.001", location=(-9.0, -5.0, FLOOR_Z + 0.9))

    build_room_walls(asset, mats, "CCTVRoom", -9.0, -1.0, 3.0, 3.0)
    _box(asset, "CCTVRoom_Console", -9.0, -1.3, FLOOR_Z, 2.0, 0.5, 1.2, mats["console"], category="security_furniture")
    add_interaction_point(asset, "Security.CCTV.001", location=(-9.0, -1.0, FLOOR_Z + 1.2))

    build_room_walls(asset, mats, "ControlRoom", -9.0, 3.0, 3.0, 3.0)
    _box(asset, "ControlRoom_Console", -9.0, 2.7, FLOOR_Z, 2.0, 0.5, 1.2, mats["console"], category="security_furniture")
    add_interaction_point(asset, "Security.Control.001", location=(-9.0, 3.0, FLOOR_Z + 1.2))
    add_interaction_point(asset, "Security.AccessControl.001", location=(-8.3, 3.0, FLOOR_Z + 1.2))
    add_interaction_point(asset, "Security.EmergencyControl.001", location=(-9.7, 3.0, FLOOR_Z + 1.2))

    build_room_walls(asset, mats, "EquipmentRoom", -5.0, -5.0, 2.5, 2.5)
    add_interaction_point(asset, "Security.Equipment.001", location=(-5.0, -5.0, FLOOR_Z + 1.0))

    # === CASINO VAULT (center) — open lobby + emergency route, never sealed ===
    _box(asset, "VaultLobby_Floor", 0.0, -3.0, FLOOR_Z, 4.0, 6.0, 0.05, mats["lobby_floor"],
         category="vault_lobby", importance="hero")
    add_interaction_point(asset, "Vault.Lobby.001", location=(0.0, -3.0, FLOOR_Z + 0.05))

    reinforced_door = create_panel(make_name("mesh", asset.name, "Vault_ReinforcedEntrance"), width=2.0, height=2.4, thickness=0.2, material=mats["vault_door"])
    reinforced_door.location.x, reinforced_door.location.y, reinforced_door.location.z = 0.0, -6.0, FLOOR_Z + 1.2
    apply_all_transforms(reinforced_door)
    asset.add_geometry(reinforced_door, metadata=for_static_prop(category="vault_door", importance="hero"))
    add_interaction_point(asset, "Vault.ReinforcedEntrance.001", location=(0.0, -6.0, FLOOR_Z + 1.2))

    vault_door = create_cylinder(make_name("mesh", asset.name, "Vault_BigDoor"), radius=1.6, depth=0.4, material=mats["vault_door"])
    vault_door.rotation_euler.x = 1.5708  # stand the disc upright, facing down the lobby
    vault_door.location.x, vault_door.location.y, vault_door.location.z = 0.0, 1.0, FLOOR_Z + 1.6
    apply_all_transforms(vault_door)
    asset.add_geometry(vault_door, metadata=for_static_prop(category="vault_door", importance="hero"))
    add_interaction_point(asset, "Vault.BigDoor.001", location=(0.0, 1.0, FLOOR_Z + 1.6))

    build_room_walls(asset, mats, "SecureStorage", 0.0, 5.0, 5.0, 4.0, wall_mat_key="vault_wall", door_mat_key="vault_door")
    _box(asset, "SecureStorage_Racks", -1.5, 5.5, FLOOR_Z, 1.5, 1.0, 1.8, mats["storage"], category="vault_storage")
    add_interaction_point(asset, "Vault.SecureStorage.001", location=(0.0, 5.0, FLOOR_Z + 1.0))

    _box(asset, "PrizeStorage_Case", 2.5, 5.5, FLOOR_Z, 1.2, 1.0, 1.2, mats["storage"], category="vault_storage", importance="high")
    add_interaction_point(asset, "Vault.PrizeStorage.001", location=(2.5, 5.5, FLOOR_Z + 1.2))

    _box(asset, "Vault_EmergencyRoute", -3.0, 1.0, FLOOR_Z, 2.0, 6.0, 0.03, mats["lobby_floor"],
         category="vault_route", importance="medium")
    add_interaction_point(asset, "Vault.EmergencyRoute.001", location=(-3.0, 1.0, FLOOR_Z + 0.03))

    # === STAFF / SERVICE AREAS (east) ===
    build_room_walls(asset, mats, "Laundry", 6.0, -5.0, 3.0, 3.0)
    add_interaction_point(asset, "Service.Laundry.001", location=(6.0, -5.0, FLOOR_Z + 1.0))

    build_room_walls(asset, mats, "Housekeeping", 6.0, -1.0, 3.0, 3.0)
    add_interaction_point(asset, "Service.Housekeeping.001", location=(6.0, -1.0, FLOOR_Z + 1.0))

    build_room_walls(asset, mats, "MaintenanceElectrical", 6.0, 3.0, 3.0, 3.0)
    _box(asset, "Maintenance_Equipment", 6.0, 2.7, FLOOR_Z, 1.8, 0.6, 1.5, mats["service_equip"], category="service_equipment")
    add_interaction_point(asset, "Service.Maintenance.001", location=(6.0, 3.0, FLOOR_Z + 1.0))
    add_interaction_point(asset, "Service.Electrical.001", location=(5.3, 3.0, FLOOR_Z + 1.0))

    build_room_walls(asset, mats, "StaffRoom", 9.5, -5.0, 3.0, 3.0)
    add_interaction_point(asset, "Service.StaffRoom.001", location=(9.5, -5.0, FLOOR_Z + 1.0))

    build_room_walls(asset, mats, "Storage", 9.5, -1.0, 3.0, 3.0)
    _box(asset, "Storage_Shelving", 9.5, -1.3, FLOOR_Z, 2.0, 0.5, 1.8, mats["storage"], category="service_storage")
    add_interaction_point(asset, "Service.Storage.001", location=(9.5, -1.0, FLOOR_Z + 1.0))

    employee_door = create_panel(make_name("mesh", asset.name, "EmployeeEntrance_Door"), width=1.0, height=2.1, thickness=0.08, material=mats["door"])
    employee_door.location.x, employee_door.location.y, employee_door.location.z = 9.5, 5.0, FLOOR_Z + 1.05
    apply_all_transforms(employee_door)
    asset.add_geometry(employee_door, metadata=for_static_prop(category="service_door", importance="medium"))
    add_interaction_point(asset, "Service.EmployeeEntrance.001", location=(9.5, 5.0, FLOOR_Z + 1.05))

    _box(asset, "LoadingDock_Platform", 6.0, 7.0, FLOOR_Z, 4.0, 2.0, 0.4, mats["lobby_floor"],
         category="service_loading", importance="medium")
    add_interaction_point(asset, "Service.LoadingDock.001", location=(6.0, 7.0, FLOOR_Z + 0.4))

    # Service elevator landing — reuses Phase 2's existing shaft, no new shaft geometry.
    add_interaction_point(asset, "Service.Elevator.001", location=(9.5, 1.5, FLOOR_Z + 1.0))

    for obj in asset.geometry_objects:
        set_origin_to_bounds_bottom(obj)

    walls = [o for o in asset.geometry_objects if "_Wall" in o.name]
    generate_box_collision(asset, "RoomWalls", walls)
    generate_box_collision(asset, "VaultFeatures", [vault_door, reinforced_door])
    generate_decimated_lod(asset, "VaultBigDoor", vault_door, level=1, ratio=0.5)

    if interactive:
        frame_objects(asset.geometry_objects)

    return asset


def main():
    asset = build_security_vault_service()

    result = validate_asset(asset, poly_budget=200000)
    print(result.report())
    print(f"Interaction points: {len(getattr(asset, 'interaction_points', []))}")
    for ip in getattr(asset, "interaction_points", []):
        print(f"  {ip.name}")

    preview_path = render_preview(asset, angle="top")
    print(f"Preview rendered: {preview_path}")

    asset.save_asset_properties()
    os.makedirs(GENERATED_DIR, exist_ok=True)
    blend_path = os.path.join(GENERATED_DIR, "koba_casino_07_security_vault_service.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    fbx_path = export_asset(asset, preset_name="fbx_generic", filename="koba_casino_07_security_vault_service.fbx")
    print(f"Exported: {fbx_path}")

    print("SUMMARY:", asset.summary())

    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
