"""Runs every test_*.py in this directory and prints a pass/fail summary.
No pytest dependency — plain functions, consistent with this project's
stdlib-only orchestration layer."""
import os
import sys
import traceback

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import tests.test_detection as test_detection  # noqa: E402
import tests.test_manifest as test_manifest  # noqa: E402
import tests.test_project as test_project  # noqa: E402
import tests.test_artifact_graph as test_artifact_graph  # noqa: E402
import tests.test_tool_executor as test_tool_executor  # noqa: E402
import tests.test_job as test_job  # noqa: E402
import tests.test_ai_agent as test_ai_agent  # noqa: E402
import tests.test_repair as test_repair  # noqa: E402
import tests.test_validation_registry as test_validation_registry  # noqa: E402
import tests.test_capability_registry as test_capability_registry  # noqa: E402
import tests.test_pipeline_manager as test_pipeline_manager  # noqa: E402
import tests.test_dependency_graph as test_dependency_graph  # noqa: E402
import tests.test_job_queue as test_job_queue  # noqa: E402
import tests.test_repair_agent as test_repair_agent  # noqa: E402
import tests.test_texture_validator as test_texture_validator  # noqa: E402
import tests.test_product_types as test_product_types  # noqa: E402
import tests.test_audio_validator as test_audio_validator  # noqa: E402
import tests.test_cli as test_cli  # noqa: E402
import tests.test_adapters as test_adapters  # noqa: E402
import tests.test_compiler_packaging as test_compiler_packaging  # noqa: E402
import tests.test_repair_retry_managers as test_repair_retry_managers  # noqa: E402
import tests.test_artifact_store as test_artifact_store  # noqa: E402
import tests.test_telemetry_manifest as test_telemetry_manifest  # noqa: E402

TEST_MODULES = [
    ("detection", test_detection),
    ("manifest", test_manifest),
    ("project", test_project),
    ("artifact_graph", test_artifact_graph),
    ("tool_executor (authorization boundary)", test_tool_executor),
    ("job (state machine + isolated workspaces)", test_job),
    ("ai_agent (provider router + blender_agent, real Blender calls)", test_ai_agent),
    ("repair (repair loop, real Blender calls)", test_repair),
    ("validation_registry", test_validation_registry),
    ("capability_registry", test_capability_registry),
    ("pipeline_manager (real Blender calls)", test_pipeline_manager),
    ("dependency_graph (pipeline-level)", test_dependency_graph),
    ("job_queue (real Blender calls)", test_job_queue),
    ("repair_agent (second real agent, real Blender calls)", test_repair_agent),
    ("texture_validator", test_texture_validator),
    ("product_types (real Blender + ImageMagick calls)", test_product_types),
    ("audio_validator (+ seamless-tiling check)", test_audio_validator),
    ("adapters (Inkscape + ImageMagick, real subprocess calls)", test_adapters),
    ("cli (includes real Blender validate/optimize integration test)", test_cli),
    ("compiler_packaging (real Ed25519 signing, real Blender fixtures)", test_compiler_packaging),
    ("repair_retry_managers (bounded repair-loop + checkpoint retry)", test_repair_retry_managers),
    ("artifact_store (content-addressed store + real repair-loop cache hit)", test_artifact_store),
    ("telemetry_manifest (log aggregation + repair/package manifest wiring)", test_telemetry_manifest),
]


def main():
    results = []
    for name, module in TEST_MODULES:
        print(f"--- {name} ---")
        try:
            ok = module.run()
            results.append((name, ok, None))
            print("PASS" if ok else "FAIL")
        except Exception as e:
            results.append((name, False, f"{type(e).__name__}: {e}"))
            print(f"FAIL: {type(e).__name__}: {e}")
            traceback.print_exc()
        print()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"{passed}/{len(results)} test modules passed")
    for name, ok, err in results:
        mark = "✓" if ok else "✗"
        print(f"  {mark} {name}" + (f" — {err}" if err else ""))

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
