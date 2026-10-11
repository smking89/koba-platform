"""Creates and manages isolated project workspaces. Source files are never
touched by later optimization/export stages — everything downstream
writes into its own subdirectory, never overwriting source/."""
import os
import re

from core.config import PROJECT_ROOT, load_projects_registry, save_projects_registry
from core.manifest import new_manifest, save_manifest, load_manifest, MANIFEST_FILENAME
from core.artifact_graph import new_graph, save_graph

PROJECTS_DIR = os.path.join(PROJECT_ROOT, "projects")

SUBDIRS = (
    "source",
    "blender", "inkscape", "gimp", "krita",
    "textures", "models", "materials", "animations", "renders", "previews",
    "optimized",  # optimize's output .blend files — never overwrites blender/ (source)
    "exports", "marketplace",
    "logs",
)


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not slug:
        raise ValueError(f"Project name '{name}' produces an empty slug")
    return slug


def project_dir_for(name):
    return os.path.join(PROJECTS_DIR, slugify(name))


def project_exists(name):
    return os.path.isdir(project_dir_for(name))


def create_project(name, project_type="generic", dry_run=False):
    """Create the isolated project directory tree + manifest. Refuses to
    clobber an existing project (use load_manifest to work with one that
    already exists)."""
    slug = slugify(name)
    proj_dir = os.path.join(PROJECTS_DIR, slug)

    if os.path.isdir(proj_dir):
        raise FileExistsError(f"Project '{slug}' already exists at {proj_dir}")

    if dry_run:
        return {
            "would_create_dir": proj_dir,
            "would_create_subdirs": list(SUBDIRS),
            "would_create_manifest": True,
            "would_create_artifact_graph": True,
        }

    os.makedirs(proj_dir)
    for sub in SUBDIRS:
        os.makedirs(os.path.join(proj_dir, sub))

    manifest = new_manifest(name=name, project_type=project_type)
    save_manifest(proj_dir, manifest)
    save_graph(proj_dir, new_graph())

    registry = load_projects_registry()
    registry.setdefault("projects", [])
    if slug not in registry["projects"]:
        registry["projects"].append(slug)
    save_projects_registry(registry)

    return proj_dir


def list_projects():
    if not os.path.isdir(PROJECTS_DIR):
        return []
    return sorted(
        d for d in os.listdir(PROJECTS_DIR)
        if os.path.isfile(os.path.join(PROJECTS_DIR, d, MANIFEST_FILENAME))
    )


def find_blend_files(name, subdir="blender"):
    """List .blend files in a project's blender/ (source) or optimized/
    subdirectory — used by the CLI's validate/optimize commands to find
    something to operate on when the user doesn't pass --blend-file."""
    proj_dir = project_dir_for(name)
    target_dir = os.path.join(proj_dir, subdir)
    if not os.path.isdir(target_dir):
        return []
    return sorted(
        os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith(".blend")
    )


def get_project_status(name):
    proj_dir = project_dir_for(name)
    if not os.path.isdir(proj_dir):
        return None
    manifest = load_manifest(proj_dir)
    return {
        "name": manifest["name"],
        "type": manifest["type"],
        "version": manifest["version"],
        "created": manifest["created"],
        "updated": manifest["updated"],
        "asset_count": len(manifest["assets"]),
        "export_count": len(manifest["exports"]),
        "error_count": len(manifest["errors"]),
        "warning_count": len(manifest["warnings"]),
    }
