"""Real tests for the validation registry. Checks the registry is
honest: every entry it claims IMPLEMENTED has a real entry point that
actually resolves (not just a string that looks plausible), and every
UNSUPPORTED entry has a reason, never a silent gap.

Entry points under adapters/blender/ can't be *imported* to prove they
resolve — they `import bpy` at module level, which only exists inside
Blender's own bundled Python (confirmed and documented repeatedly
elsewhere in this codebase), not the system Python this test runs under;
those get a file-existence + source-text check instead. Entry points
elsewhere (e.g. validation/texture_validator.py, plain Python, no bpy)
are genuinely imported and hasattr-checked — a real resolution, not a
text match.
"""
import importlib
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
BLENDER_ADAPTER_DIR = os.path.join(PROJECT_ROOT, "adapters", "blender")

from validation.validation_registry import (  # noqa: E402
    get, list_validators, is_implemented, UnknownValidator, IMPLEMENTED, UNSUPPORTED,
)

# The master spec's 17 named validator types under validation/ (section
# with geometry_validator, topology_validator, ..., security_validator).
EXPECTED_VALIDATOR_IDS = {
    "geometry", "topology", "collision", "texture", "material", "asset",
    "dependency", "compatibility", "manifest", "runtime", "interaction",
    "npc", "event", "performance", "memory", "network", "security",
}


def _entry_point_resolves(dotted_path):
    parts = dotted_path.split(".")
    if parts[0] == "adapters" and parts[1] == "blender":
        # bpy-dependent — can't import under system Python, see module docstring.
        module_path = os.path.join(BLENDER_ADAPTER_DIR, *parts[2:-1]) + ".py"
        func_name = parts[-1]
        assert os.path.isfile(module_path), f"{dotted_path}: no such file {module_path}"
        with open(module_path) as f:
            source = f.read()
        assert f"def {func_name}(" in source, f"{dotted_path}: {module_path} has no 'def {func_name}('"
    else:
        # plain Python, no bpy — genuinely import and check, not a text match.
        module_path, func_name = ".".join(parts[:-1]), parts[-1]
        module = importlib.import_module(module_path)
        assert hasattr(module, func_name), f"{dotted_path}: {module_path} has no attribute {func_name!r}"
        assert callable(getattr(module, func_name))


def run():
    entries = list_validators()

    # --- completeness: exactly the spec's 17 named types, no more, no fewer ---
    assert set(entries.keys()) == EXPECTED_VALIDATOR_IDS, \
        f"registry drifted from the spec's validator list: {set(entries.keys()) ^ EXPECTED_VALIDATOR_IDS}"

    # --- honesty: every entry is well-formed for its status ---
    for validator_id, entry in entries.items():
        assert entry.validator_id == validator_id
        assert entry.status in (IMPLEMENTED, UNSUPPORTED)
        if entry.status == IMPLEMENTED:
            assert entry.entry_point, f"{validator_id}: IMPLEMENTED but no entry_point given"
            assert entry.covers, f"{validator_id}: IMPLEMENTED but doesn't say what it covers"
            assert entry.reason is None, f"{validator_id}: IMPLEMENTED but also has an UNSUPPORTED-style reason"
            _entry_point_resolves(entry.entry_point)
        else:
            assert entry.reason, f"{validator_id}: UNSUPPORTED but no reason given — never a silent gap"
            assert entry.entry_point is None, f"{validator_id}: UNSUPPORTED but has an entry_point"
            assert entry.covers == [], f"{validator_id}: UNSUPPORTED but claims to cover something"

    # --- known real facts about this codebase, so the test breaks if the
    # registry silently drifts from reality ---
    assert is_implemented("geometry")
    assert is_implemented("performance")
    assert not is_implemented("npc")
    assert not is_implemented("security")

    # --- get(): real lookups + honest failure for unknown ids ---
    assert get("performance").status == IMPLEMENTED
    try:
        get("not_a_real_validator")
        assert False, "must raise for an unknown validator id, not return None"
    except UnknownValidator:
        pass

    return True


if __name__ == "__main__":
    ok = run()
    print("test_validation_registry: PASS" if ok else "test_validation_registry: FAIL")
    sys.exit(0 if ok else 1)
