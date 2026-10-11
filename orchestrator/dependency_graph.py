"""Pipeline-level dependency graph (master spec's `orchestrator/
dependency_graph`) — distinct from `core.artifact_graph`, which tracks
dependencies BETWEEN ARTIFACTS (already real: `find_affected()`,
`invalidate()`, `has_changed()`, `lineage()`). This module answers a
different question: given a pipeline stage that consumes some file path,
and the project's real artifact graph, is that stage STALE — i.e. has
its input genuinely changed since it last ran — or can it be safely
skipped because nothing it depends on changed.

This is a thin translation layer from "artifact X changed" (which
`core.artifact_graph` already answers) to "pipeline stage N is stale,"
not a second copy of dependency tracking. It reuses
`find_by_path()`/`has_changed()`/`hash_file()` entirely.

Scope honesty: not yet wired into `orchestrator/pipeline_manager.py`'s
one real pipeline (`validate_then_repair`) — that pipeline's `validate`
stage must always run (it's the thing that decides whether `repair` is
even needed), so "skip because unchanged" has no honest application
there. This module exists so a future multi-stage artifact-flow pipeline
(e.g. something shaped like `process`'s svg -> png -> webp chain) can use
real skip-if-unchanged logic instead of every stage re-running
unconditionally — wiring it into `pipeline_manager` is future work for
when such a pipeline exists, not faked here.
"""
import os

from core.artifact_graph import find_by_path, hash_file


def stage_is_stale(graph, consumes_path):
    """A stage with no declared input (consumes_path=None) is always
    stale — there's nothing to compare against, so "skip because
    unchanged" would be a guess, not a fact, and this module never
    guesses. Likewise a never-before-tracked artifact, or one whose file
    has since disappeared, is stale by definition (there's no valid prior
    hash to compare against)."""
    if consumes_path is None:
        return True
    if not os.path.isfile(consumes_path):
        return True
    artifact = find_by_path(graph, consumes_path)
    if artifact is None:
        return True
    return graph.has_changed(artifact["artifact_id"], hash_file(consumes_path))


def stale_stages(graph, stages):
    """`stages`: list of dicts each optionally carrying "consumes_path".
    Returns the indices of stages that are stale (must run) — every
    other index can be safely skipped, based purely on a real hash
    comparison, never guessed."""
    return [i for i, s in enumerate(stages) if stage_is_stale(graph, s.get("consumes_path"))]
