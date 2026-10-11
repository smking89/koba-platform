"""Package Builder (master spec's `packaging/package_builder` +
`hash_generator`, `version_builder`, `artifact_builder` folded into one
real module — not five speculative ones).

Takes a CompiledProduct descriptor (from compiler/product_compiler.py)
and actually writes a real release to disk: copies each artifact's real
file into the package directory, and writes a manifest.json describing
exactly what's in it with FRESHLY recomputed hashes (never trusting the
artifact graph's recorded hash blindly — if a file changed on disk since
it was last validated, this catches that drift instead of packaging
stale/wrong bytes).
"""
import datetime
import json
import os
import shutil

from core.artifact_graph import hash_file, hash_data

PACKAGE_MANIFEST_FILENAME = "release_manifest.json"


class PackagingError(Exception):
    pass


def _release_dir(proj_dir, version):
    return os.path.join(proj_dir, "releases", version)


def build_package(proj_dir, compiled_product, version=None):
    """Real, bounded versioning: an integer that increments past however
    many releases already exist for this project — not a semver scheme,
    since nothing here tracks semantic compatibility. Returns
    {"package_dir", "manifest_path", "package_hash", "version"}."""
    if version is None:
        releases_dir = os.path.join(proj_dir, "releases")
        existing = [d for d in os.listdir(releases_dir)] if os.path.isdir(releases_dir) else []
        existing_versions = [int(d) for d in existing if d.isdigit()]
        version = str(max(existing_versions, default=0) + 1)

    package_dir = _release_dir(proj_dir, version)
    assets_dir = os.path.join(package_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    packaged_files = []
    for artifact in compiled_product["artifacts"]:
        src_path = artifact["output_path"]
        if not src_path or not os.path.isfile(src_path):
            raise PackagingError(
                f"artifact {artifact['artifact_id']} ({artifact['artifact_type']}) has no "
                f"real file at its recorded storage_location ('{src_path}') — refusing to "
                f"package a release with a missing asset"
            )
        dst_name = f"{artifact['artifact_id'][:8]}_{os.path.basename(src_path)}"
        dst_path = os.path.join(assets_dir, dst_name)
        shutil.copyfile(src_path, dst_path)

        fresh_hash = hash_file(dst_path)
        if artifact["output_hash"] and fresh_hash != artifact["output_hash"]:
            raise PackagingError(
                f"artifact {artifact['artifact_id']}: file content at '{src_path}' no longer "
                f"matches the hash recorded when it was validated ({artifact['output_hash']} "
                f"-> {fresh_hash}) — it changed since validation; re-run validate/optimize "
                f"before packaging, never package stale/mismatched bytes"
            )

        packaged_files.append({
            "artifact_id": artifact["artifact_id"],
            "artifact_type": artifact["artifact_type"],
            "validation_status": artifact["validation_status"],
            "relative_path": os.path.join("assets", dst_name),
            "hash": fresh_hash,
        })

    release_manifest = {
        "product_type": compiled_product["product_type"],
        "product_metadata": compiled_product["product_metadata"],
        "source_project": compiled_product["source_project"],
        "compiled_at": compiled_product["compiled_at"],
        "packaged_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "version": version,
        "files": packaged_files,
    }
    package_hash = hash_data(release_manifest)
    release_manifest["package_hash"] = package_hash

    manifest_path = os.path.join(package_dir, PACKAGE_MANIFEST_FILENAME)
    with open(manifest_path, "w") as f:
        json.dump(release_manifest, f, indent=2)

    return {
        "package_dir": package_dir,
        "manifest_path": manifest_path,
        "package_hash": package_hash,
        "version": version,
    }


def load_release_manifest(manifest_path):
    with open(manifest_path, "r") as f:
        return json.load(f)


def list_releases(proj_dir):
    releases_dir = os.path.join(proj_dir, "releases")
    if not os.path.isdir(releases_dir):
        return []
    releases = []
    for version in sorted(os.listdir(releases_dir), key=lambda v: int(v) if v.isdigit() else -1):
        manifest_path = os.path.join(releases_dir, version, PACKAGE_MANIFEST_FILENAME)
        if os.path.isfile(manifest_path):
            releases.append(load_release_manifest(manifest_path))
    return releases
