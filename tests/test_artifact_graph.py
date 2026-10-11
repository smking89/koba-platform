"""Real tests for core.artifact_graph — actual files on disk hashed for
real, actual JSON persisted and reloaded, no mocks. Covers the specific
behaviors the master spec calls out by name: dependency traversal,
lineage, change detection, cascading invalidation that stops at the
correct boundary (section 5's "must NOT rebuild unrelated NPC logic"
example), diff, and reproducibility via file-content hashing."""
import os
import shutil
import sys
import tempfile

from core.artifact_graph import (
    ArtifactGraph, new_graph, save_graph, load_graph,
    hash_file, hash_data, find_by_path, get_or_create_source_artifact,
    PASS, FAIL, PENDING, INVALID,
)


def run():
    tmp_dir = tempfile.mkdtemp(prefix="koba_test_artifact_graph_")
    try:
        # --- real file hashing, not a stub ---
        material_path = os.path.join(tmp_dir, "material_v1.json")
        with open(material_path, "w") as f:
            f.write('{"color": "red"}')
        h1 = hash_file(material_path)
        assert len(h1) == 64  # sha256 hex digest length
        with open(material_path, "w") as f:
            f.write('{"color": "blue"}')
        h2 = hash_file(material_path)
        assert h1 != h2, "changing file content must change its hash"
        assert hash_file(material_path) == h2, "hashing must be deterministic"

        # hash_data for non-file artifacts (e.g. build parameters)
        assert hash_data({"a": 1, "b": 2}) == hash_data({"b": 2, "a": 1}), \
            "hash_data must be key-order independent (canonical JSON)"

        # --- build a small real dependency chain: material -> prefab -> package ---
        graph = new_graph()
        material_id = graph.add_artifact(
            artifact_type="material", processor="material_processor", processor_version="1.0",
            input_hash=hash_data({"color": "red"}), output_path=material_path,
        )
        prefab_id = graph.add_artifact(
            artifact_type="prefab", processor="prefab_processor", processor_version="1.0",
            parent_artifacts=[material_id], input_hash=hash_data({"uses": material_id}),
        )
        package_id = graph.add_artifact(
            artifact_type="package", processor="compiler", processor_version="1.0",
            parent_artifacts=[prefab_id],
        )
        # an unrelated branch that must NEVER be touched by the material changing
        npc_id = graph.add_artifact(artifact_type="npc_logic", processor="npc_processor")

        # adding an artifact with an unknown parent must fail loudly, not silently
        try:
            graph.add_artifact(artifact_type="x", processor="x", parent_artifacts=["does-not-exist"])
            assert False, "should have raised on a dangling parent reference"
        except ValueError:
            pass

        # --- traversal ---
        lineage = {a["artifact_id"] for a in graph.lineage(package_id)}
        assert lineage == {material_id, prefab_id}, "package's lineage must be exactly material+prefab"

        affected = {a["artifact_id"] for a in graph.find_affected(material_id)}
        assert affected == {prefab_id, package_id}, \
            "changing the material must affect exactly prefab+package"
        assert npc_id not in affected, \
            "find_affected must NOT include the unrelated npc artifact (master spec section 5)"

        # --- change detection ---
        assert graph.has_changed(material_id, hash_data({"color": "blue"})) is True
        assert graph.has_changed(material_id, hash_data({"color": "red"})) is False

        # --- cascading invalidation stops at the correct boundary ---
        for aid in (material_id, prefab_id, package_id, npc_id):
            graph.set_validation_status(aid, PASS)
        invalidated = set(graph.invalidate(material_id))
        assert invalidated == {material_id, prefab_id, package_id}
        assert graph.get(material_id)["validation_status"] == INVALID
        assert graph.get(prefab_id)["validation_status"] == INVALID
        assert graph.get(package_id)["validation_status"] == INVALID
        assert graph.get(npc_id)["validation_status"] == PASS, \
            "unrelated npc artifact must keep its PASS status, not get invalidated"

        # --- diff ---
        d = graph.diff(material_id, prefab_id)
        assert "artifact_type" in d and d["artifact_type"] == ("material", "prefab")

        # --- persistence round-trip ---
        save_graph(tmp_dir, graph)
        reloaded = load_graph(tmp_dir)
        assert reloaded.get(material_id)["validation_status"] == INVALID
        assert {a["artifact_id"] for a in reloaded.find_affected(material_id)} == {prefab_id, package_id}

        # --- get_or_create_source_artifact: idempotent for external files ---
        source_path = os.path.join(tmp_dir, "dropped_in_by_user.blend")
        with open(source_path, "w") as f:
            f.write("not a real blend, just needs to exist for hashing")
        first_id = get_or_create_source_artifact(graph, source_path, "blend_source")
        second_id = get_or_create_source_artifact(graph, source_path, "blend_source")
        assert first_id == second_id, "calling it twice for the same path must not create a duplicate node"
        assert find_by_path(graph, source_path)["artifact_id"] == first_id
        assert find_by_path(graph, os.path.join(tmp_dir, "nonexistent.blend")) is None

        # loading a project dir with no graph file yet must return an empty graph, not error
        empty_dir = os.path.join(tmp_dir, "no_graph_here")
        os.makedirs(empty_dir)
        empty = load_graph(empty_dir)
        assert isinstance(empty, ArtifactGraph)
        assert empty.artifacts == {}

        return True
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    ok = run()
    print("test_artifact_graph: PASS" if ok else "test_artifact_graph: FAIL")
    sys.exit(0 if ok else 1)
