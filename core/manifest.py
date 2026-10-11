"""Per-project machine-readable manifest (project.json). This is the
source of truth for what a project contains, what generated it, and
whether anything failed — every other tool (validator, packager,
marketplace prep) reads this instead of re-scanning the filesystem."""
import datetime
import json
import os

MANIFEST_FILENAME = "project.json"


def new_manifest(name, project_type="generic", version="1.0.0", author="claude-code"):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "name": name,
        "version": version,
        "type": project_type,
        "author": author,
        "created": now,
        "updated": now,
        "assets": [],
        "tools": [],
        "exports": [],
        "dependencies": [],
        "errors": [],
        "warnings": [],
    }


def load_manifest(project_dir):
    path = os.path.join(project_dir, MANIFEST_FILENAME)
    with open(path, "r") as f:
        return json.load(f)


def save_manifest(project_dir, manifest):
    manifest["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    path = os.path.join(project_dir, MANIFEST_FILENAME)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return path


def set_product_type(manifest, product_type, metadata):
    """Stamps the formal product type (products/product_types.py) and its
    validated metadata onto the manifest. Callers must validate metadata
    via products.product_types.validate_metadata() BEFORE calling this —
    this function just persists it, matching the project's established
    separation (schema validation lives in the registry module, this
    module only persists)."""
    manifest["product_type"] = product_type
    manifest["product_metadata"] = metadata


def add_asset(manifest, name, asset_type, source_files=None, generated_files=None,
              polycount=None, texture_resolution=None):
    manifest["assets"].append({
        "name": name,
        "type": asset_type,
        "source_files": source_files or [],
        "generated_files": generated_files or [],
        "polycount": polycount,
        "texture_resolution": texture_resolution,
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })


def add_tool_used(manifest, tool_name, version=None):
    entry = {"tool": tool_name, "version": version}
    if entry not in manifest["tools"]:
        manifest["tools"].append(entry)


def add_export(manifest, asset_name, fmt, path, size_bytes=None):
    manifest["exports"].append({
        "asset": asset_name,
        "format": fmt,
        "path": path,
        "size_bytes": size_bytes,
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })


def add_error(manifest, message):
    manifest["errors"].append({"message": message, "time": datetime.datetime.now(datetime.timezone.utc).isoformat()})


def add_warning(manifest, message):
    manifest["warnings"].append({"message": message, "time": datetime.datetime.now(datetime.timezone.utc).isoformat()})
