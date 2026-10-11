"""Real tests for the pipeline-level dependency graph — an actual file on
disk, actually hashed and registered in a real ArtifactGraph, actually
modified to prove staleness detection reacts to a genuine content change,
not a guess."""
import os
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.artifact_graph import ArtifactGraph, hash_file  # noqa: E402
from orchestrator.dependency_graph import stage_is_stale, stale_stages  # noqa: E402


def run():
    tmp_dir = tempfile.mkdtemp(prefix="koba_test_dependency_graph_")
    try:
        graph = ArtifactGraph()

        # --- no declared input: always stale, never a guess ---
        assert stage_is_stale(graph, None) is True

        # --- input path that was never tracked: stale (must run at least once) ---
        src_path = os.path.join(tmp_dir, "source.txt")
        with open(src_path, "w") as f:
            f.write("v1")
        assert stage_is_stale(graph, src_path) is True

        # --- register it, unchanged since: not stale ---
        graph.add_artifact(
            artifact_type="test_source", processor="test",
            output_path=src_path, input_hash=hash_file(src_path),
        )
        assert stage_is_stale(graph, src_path) is False

        # --- real content change: genuinely stale again ---
        with open(src_path, "w") as f:
            f.write("v2 — actually different bytes")
        assert stage_is_stale(graph, src_path) is True

        # --- re-register at the new hash: not stale again ---
        graph2 = ArtifactGraph()
        graph2.add_artifact(
            artifact_type="test_source", processor="test",
            output_path=src_path, input_hash=hash_file(src_path),
        )
        assert stage_is_stale(graph2, src_path) is False

        # --- file deleted since being tracked: stale (nothing to compare against) ---
        os.remove(src_path)
        assert stage_is_stale(graph2, src_path) is True

        # --- stale_stages: mixed list of stage indices ---
        with open(src_path, "w") as f:
            f.write("v3")
        fresh_graph = ArtifactGraph()
        fresh_graph.add_artifact(
            artifact_type="test_source", processor="test",
            output_path=src_path, input_hash=hash_file(src_path),
        )
        stages = [
            {"command": "unchanged_stage", "consumes_path": src_path},
            {"command": "no_input_stage"},  # no consumes_path key at all
        ]
        assert stale_stages(fresh_graph, stages) == [1], \
            "only the stage with no declared input should be stale here"

        with open(src_path, "w") as f:
            f.write("v4 — changed again")
        assert stale_stages(fresh_graph, stages) == [0, 1], \
            "once the tracked file changes, both stages are stale"

        return True
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    ok = run()
    print("test_dependency_graph: PASS" if ok else "test_dependency_graph: FAIL")
    sys.exit(0 if ok else 1)
