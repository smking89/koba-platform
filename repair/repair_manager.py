"""Repair Manager — bounded multi-attempt extension of repair_engine's
single repair action (master spec section 10's REPAIR<->REVALIDATE loop,
closed into an actual loop instead of requiring the operator to manually
rerun `repair` after each attempt).

Scope honesty: this does NOT add a new repair strategy. It still only
ever delegates to repair_engine.classify_failure/run_repair, which can
fix exactly entity_count/unique_meshes (merge) or triangles (decimate) —
nothing else. What it adds is bounded persistence on the SAME strategy:
if a decimate attempt still fails on triangles afterward, it tries again
with a strictly tighter ratio, up to max_attempts times. It refuses to
keep retrying (stops immediately, rather than guessing) when:

  - the chosen strategy was a merge — merging a visibility_group is
    deterministic, so retrying it against the same failure produces the
    identical result; looping would just waste real Blender invocations
    for a guaranteed-unchanged outcome, or
  - a revalidation attempt surfaces a failure metric that wasn't present
    in the attempt before it — a genuinely new/different problem this
    manager has no strategy for either, not a signal to keep pushing the
    same lever harder.
"""
import os
import shutil

from core import artifact_store
from core.artifact_graph import hash_file
from repair.repair_engine import classify_failure, run_repair, revalidate, UnrepairableFailure  # noqa: F401

DEFAULT_MAX_ATTEMPTS = 3
RATIO_TIGHTEN_FACTOR = 0.75
MIN_DECIMATE_RATIO = 0.05


def tighten_ratio(ratio):
    """Pure arithmetic: how much more aggressive the next decimate
    attempt gets, floored so Blender's Decimate modifier never receives
    a near-zero ratio (same floor repair_engine itself enforces)."""
    return max(MIN_DECIMATE_RATIO, round(ratio * RATIO_TIGHTEN_FACTOR, 4))


def should_retry(decision, prior_failures, new_failures, attempt_num, max_attempts):
    """Pure decision logic, factored out of repair_loop so it can be
    tested directly against crafted failure lists without needing a real
    Blender call for every branch (same spirit as repair_engine's own
    "unit-level, no Blender needed" classify_failure tests)."""
    if decision["decimate_ratio"] is None:
        return False  # merge is deterministic — retrying repeats the same outcome
    if attempt_num >= max_attempts:
        return False
    prior_metrics = {f.split(" ", 1)[0] for f in prior_failures}
    new_metrics = {f.split(" ", 1)[0] for f in new_failures}
    return new_metrics <= prior_metrics  # no genuinely new problem appeared


def repair_loop(initial_report, blend_path, profile_name, output_path_fn,
                 merge_group=None, asset_name=None, max_attempts=DEFAULT_MAX_ATTEMPTS,
                 caller_id="repair_engine", proj_dir=None):
    """initial_report: the DIAGNOSE-stage validate_blend result that
    triggered repair — the caller already has this from its own
    diagnosis step, it is never re-fetched here.

    output_path_fn(attempt_number) -> str: the caller owns artifact-graph
    and filesystem-layout decisions (numbering against prior attempts
    against this exact source, etc.) — this module only drives the loop.

    caller_id defaults to "repair_engine", not a separate identity, for
    the tool_executor authorization boundary (Rule 3) — this module is a
    bounded retry wrapper AROUND repair_engine, not a new actor that
    needs its own entry in tools/tool_permissions.py's allowed-callers
    list.

    proj_dir, if given, enables core.artifact_store caching: an attempt
    whose exact (source bytes, merge_group/decimate_ratio/profile) has
    already been computed before skips the real Blender invocation and
    reuses the cached bytes instead — construction only, never
    validation (revalidate() always runs for real regardless of a cache
    hit; Rule 2 forbids skipping that for any reason, including a cache
    hit on the construction step).

    Returns a list of attempt dicts (never empty — raises
    UnrepairableFailure immediately, same as repair_engine itself, if the
    very first classification fails), each:
      {"attempt", "source_path", "output_path", "decision",
       "repair_result", "revalidation"}
    Stopping at the first PASS, at max_attempts, or as soon as
    should_retry() says continuing isn't justified.
    """
    attempts = []
    report = initial_report
    source_path = blend_path
    decimate_override = None

    for attempt_num in range(1, max_attempts + 1):
        decision = classify_failure(report, merge_group=merge_group)
        if decimate_override is not None and decision["decimate_ratio"] is not None:
            decision["decimate_ratio"] = decimate_override

        output_path = output_path_fn(attempt_num)

        cached_path = None
        input_hash = None
        cache_params = None
        if proj_dir:
            input_hash = hash_file(source_path)
            cache_params = {"merge_group": decision["merge_group"], "decimate_ratio": decision["decimate_ratio"],
                             "profile_name": profile_name, "asset_name": asset_name}
            cached_path = artifact_store.cache_lookup(proj_dir, "optimize_blend", input_hash, cache_params)

        if cached_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copyfile(cached_path, output_path)
            result = {"output_path": output_path,
                      "actions": ["(cache hit — reused a previously computed repair output, no Blender invocation)"]}
        else:
            result = run_repair(source_path, output_path, profile_name, decision,
                                 asset_name=asset_name, caller_id=caller_id)
            if proj_dir:
                artifact_store.cache_store(proj_dir, "optimize_blend", input_hash, cache_params, result["output_path"])

        revalidated = revalidate(output_path, profile_name, asset_name=asset_name, caller_id=caller_id)

        attempts.append({
            "attempt": attempt_num, "source_path": source_path, "output_path": output_path,
            "decision": decision, "repair_result": result, "revalidation": revalidated,
        })

        if revalidated["result"] == "PASS":
            break
        if not should_retry(decision, report["failures"], revalidated["failures"], attempt_num, max_attempts):
            break

        decimate_override = tighten_ratio(decision["decimate_ratio"])
        source_path = output_path
        report = revalidated

    return attempts
