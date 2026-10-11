"""Creates a real project under the actual projects/ directory (project.py
doesn't support redirecting PROJECTS_DIR, so this is the honest way to
test it) using a clearly-throwaway name, and removes it — directory and
registry entry — when done, regardless of pass/fail."""
import os
import shutil
import sys

from core.config import load_projects_registry, save_projects_registry
from core.manifest import MANIFEST_FILENAME
from core.project import (
    create_project, project_exists, project_dir_for, slugify,
    list_projects, get_project_status, SUBDIRS,
)

TEST_PROJECT_NAME = "Koba Test Project ZZZ Temp"


def _cleanup():
    proj_dir = project_dir_for(TEST_PROJECT_NAME)
    if os.path.isdir(proj_dir):
        shutil.rmtree(proj_dir)
    registry = load_projects_registry()
    slug = slugify(TEST_PROJECT_NAME)
    if slug in registry.get("projects", []):
        registry["projects"].remove(slug)
        save_projects_registry(registry)


def run():
    _cleanup()  # in case a previous failed run left it behind
    try:
        assert not project_exists(TEST_PROJECT_NAME)

        plan = create_project(TEST_PROJECT_NAME, project_type="prop", dry_run=True)
        assert not project_exists(TEST_PROJECT_NAME), "dry_run must not create anything"
        assert set(plan["would_create_subdirs"]) == set(SUBDIRS)

        proj_dir = create_project(TEST_PROJECT_NAME, project_type="prop")
        assert project_exists(TEST_PROJECT_NAME)
        for sub in SUBDIRS:
            assert os.path.isdir(os.path.join(proj_dir, sub)), f"missing subdir: {sub}"
        assert os.path.isfile(os.path.join(proj_dir, MANIFEST_FILENAME))

        try:
            create_project(TEST_PROJECT_NAME, project_type="prop")
            assert False, "creating an already-existing project should raise"
        except FileExistsError:
            pass

        assert slugify(TEST_PROJECT_NAME) in list_projects()

        status = get_project_status(TEST_PROJECT_NAME)
        assert status["name"] == TEST_PROJECT_NAME
        assert status["type"] == "prop"
        assert status["asset_count"] == 0

        return True
    finally:
        _cleanup()


if __name__ == "__main__":
    ok = run()
    print("test_project: PASS" if ok else "test_project: FAIL")
    sys.exit(0 if ok else 1)
