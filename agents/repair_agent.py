"""The second real agent (master spec's `agents/repair_agent`) — proves
the one-router/multiple-agents pattern `blender_agent` established
actually generalizes, without building all 18 agents speculatively.

Scope, stated precisely: this agent's real contribution is extracting a
`merge_group` name from free text (e.g. "merge the 'cluster' group and
retry") — a genuine extraction task (see `ai/providers/
rule_based_provider.py`'s `_extract_merge_group`), not a fabricated one.
It does NOT itself run the repair pipeline end-to-end: `cmd_repair_agent`
in `cli/main.py` orchestrates diagnosis/record/classify/repair/revalidate
in the exact same order `cmd_repair` does, for a real reason — an
artifact's source node must be created and its FAIL status persisted
(`_record_validation`) BEFORE a fresh graph load can correctly resolve
the SAME artifact id for repair-attempt versioning. Collapsing all of
that behind one agent call (an earlier version of this file did) created
a real bug: two separate `get_or_create_source_artifact` calls against
two different in-memory graph snapshots minted two different artifact
ids for the same file, and the second `save_graph()` crashed trying to
operate on an id the freshly-reloaded graph had never seen. Keeping the
agent to "decide, don't orchestrate" avoids that class of bug entirely —
and still never decides PASS/FAIL itself (Rule 2): every `revalidate()`
call is the exact same real `validate_blend` tool-contract call
`blender_agent` and `cmd_repair` already use.
"""
from ai.provider_base import AIProviderError
from ai.router import AIRouter, ProviderUnavailable

CALLER_ID = "repair_agent"

TOOL_CATALOG = [
    {
        "tool_id": "attempt_repair",
        "description": "Diagnose a Blender asset and attempt an automated repair if one exists. "
                        "Merging a named visibility_group fixes entity_count/unique_meshes overages "
                        "(the instruction should name the group, e.g. \"merge the 'cluster' group\"); "
                        "decimating geometry fixes triangle overages (ratio computed automatically, "
                        "no group name needed).",
    },
]


class RepairAgentError(Exception):
    pass


class RepairAgent:
    def __init__(self, router=None):
        self.router = router or AIRouter()

    def get_merge_group_hint(self, instruction):
        """The agent's one real decision: does the instruction name a
        visibility_group to merge, and if so, which one. Returns None if
        the provider found none — the caller must still refuse to guess
        (repair.repair_engine.classify_failure already does), this just
        supplies what free text actually named, same as a human would
        type into --merge-group."""
        try:
            provider = self.router.get_provider()
        except ProviderUnavailable as e:
            raise RepairAgentError(str(e)) from e

        try:
            decision = provider.decide(instruction, TOOL_CATALOG)
        except AIProviderError as e:
            raise RepairAgentError(f"provider '{provider.provider_id}' could not decide: {e}") from e

        return provider, decision.get("args", {}).get("merge_group")
