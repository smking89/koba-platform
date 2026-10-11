"""The first real repair loop (master spec section 10):

    GENERATE -> VALIDATE -> FAIL -> DIAGNOSE -> CLASSIFY FAILURE ->
    RESOLVE AFFECTED ARTIFACT -> SELECT REPAIR STRATEGY -> REPAIR ->
    CREATE NEW ARTIFACT VERSION -> REVALIDATE -> PASS / FAIL

Deliberately narrow: exactly two repair actions exist, both delegated to
optimize_blend (which can apply either or both in one pass) —

  - merge a named visibility_group, fixing entity_count/unique_meshes
    overages (the only structural fix optimize_blend's merge step can
    perform)
  - in-place decimation, fixing triangle overages (optimization.decimate
    — genuinely reduces the mesh the validator counts, unlike LOD
    registration, which only adds a hidden alternate representation
    nothing switches to at runtime yet)

Material/light/physics/animated-object overages have no automated fix in
this codebase — classify_failure() raises UnrepairableFailure for those
rather than pretending a fix was applied (the same UNSUPPORTED_CAPABILITY
discipline used everywhere else).

Validation-authority separation (Rule 2 — AI IS NOT THE VALIDATION
AUTHORITY) is structural here, not a comment: this module never sets an
artifact's validation_status itself. run_repair() only reports what
optimize_blend did; revalidate() only reports what validate_blend found.
Deciding what those results MEAN for the artifact graph is the caller's
job (cli/main.py's cmd_repair), and it must always come from a fresh
revalidate() call, never from this module's own opinion.
"""
import re

from adapters.blender_bridge import BlenderBridgeError
from tools.tool_executor import execute as run_tool, ToolNotFound, UnsupportedCapability
from tools.tool_permissions import PermissionDenied
from tools.tool_schemas import SchemaValidationError

CALLER_ID = "repair_engine"

# entity_count/unique_meshes are fixed by merging a visibility_group;
# triangles is fixed by in-place decimation. Everything else has no
# automated fix in this codebase.
_MERGE_FIXABLE_KEYS = ("entity_count", "unique_meshes")
_DECIMATE_FIXABLE_KEYS = ("triangles",)

# A little headroom below the budget limit, not exactly-at-budget — a
# ratio landing exactly on the line risks flapping PASS/FAIL from
# triangle-count rounding in the decimate modifier itself.
_DECIMATE_SAFETY_MARGIN = 0.9
_MIN_DECIMATE_RATIO = 0.05  # Blender's Decimate modifier behaves oddly near 0

_FAILURE_RE = re.compile(r"^(\w+) = (\d+) exceeds \w+ = (\d+)$")

_TOOL_ERRORS = (BlenderBridgeError, ToolNotFound, UnsupportedCapability,
                PermissionDenied, SchemaValidationError)


class UnrepairableFailure(Exception):
    """Raised instead of guessing or faking a fix — a failure this engine
    has no real strategy for, or enough information to act on, must say
    so loudly rather than silently no-op or claim success."""


def classify_failure(report, merge_group=None):
    """DIAGNOSE + CLASSIFY FAILURE + SELECT REPAIR STRATEGY. Failure
    strings come from optimization.performance_validator (e.g.
    "entity_count = 400 exceeds max_visible_entities = 350",
    "triangles = 58806 exceeds max_triangles = 250000") — classified by
    their leading metric name, with the actual/limit values parsed out
    for the ones this engine can compute a real fix for."""
    if report["result"] != "FAIL":
        raise UnrepairableFailure("nothing to repair — report did not FAIL")

    failures = report["failures"]
    merge_fixable = [f for f in failures if f.split(" ", 1)[0] in _MERGE_FIXABLE_KEYS]
    decimate_fixable = [f for f in failures if f.split(" ", 1)[0] in _DECIMATE_FIXABLE_KEYS]
    fixable = merge_fixable + decimate_fixable
    unfixable = [f for f in failures if f not in fixable]

    if not fixable:
        raise UnrepairableFailure(
            f"no repair strategy exists for: {failures} — this engine can only address "
            f"{_MERGE_FIXABLE_KEYS} (via merge) or {_DECIMATE_FIXABLE_KEYS} (via decimation)"
        )

    decision = {"strategy": "optimize_repair", "merge_group": None, "decimate_ratio": None,
                "addresses": fixable, "cannot_address": unfixable}

    if merge_fixable:
        if not merge_group:
            raise UnrepairableFailure(
                f"'{merge_fixable[0]}' looks fixable by merging, but no merge_group was given — "
                "the repair engine does not guess which visibility_group to merge"
            )
        decision["merge_group"] = merge_group

    if decimate_fixable:
        match = _FAILURE_RE.match(decimate_fixable[0])
        if not match:
            raise UnrepairableFailure(
                f"'{decimate_fixable[0]}' looks triangle-fixable but couldn't be parsed for a ratio"
            )
        _, current, limit = match.groups()
        current, limit = int(current), int(limit)
        ratio = max(_MIN_DECIMATE_RATIO, min(0.95, (limit / current) * _DECIMATE_SAFETY_MARGIN))
        decision["decimate_ratio"] = round(ratio, 4)

    return decision


def run_repair(blend_path, output_path, profile_name, decision, asset_name=None, caller_id=CALLER_ID):
    """REPAIR — executes the chosen strategy through the same
    tool_executor authorization boundary every other real operation
    uses (Rule 3: AI/repair MUST OPERATE THROUGH KOBA TOOL CONTRACTS).
    Returns optimize_blend's raw result; does not judge it."""
    if decision["strategy"] != "optimize_repair":
        raise UnrepairableFailure(f"unknown repair strategy: {decision['strategy']!r}")
    if decision["merge_group"] is None and decision["decimate_ratio"] is None:
        raise UnrepairableFailure("repair decision has no action to apply")

    try:
        return run_tool(
            "optimize_blend", caller_id, blend_path=blend_path, output_path=output_path,
            profile_name=profile_name, asset_name=asset_name,
            merge_group=decision["merge_group"], decimate_ratio=decision["decimate_ratio"],
        )
    except _TOOL_ERRORS as e:
        raise UnrepairableFailure(f"repair action failed: {e}") from e


def revalidate(blend_path, profile_name, asset_name=None, caller_id=CALLER_ID):
    """REVALIDATE — the only thing allowed to decide PASS/FAIL. Used both
    for the initial diagnosis (against the original blend) and for
    checking whether a repair actually worked (against the repaired
    output) — same call, same authority, no shortcuts."""
    try:
        return run_tool("validate_blend", caller_id, blend_path=blend_path,
                         profile_name=profile_name, asset_name=asset_name)
    except _TOOL_ERRORS as e:
        raise UnrepairableFailure(f"validation failed to run: {e}") from e
