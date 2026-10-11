"""The one real AI agent (master spec section 9). Proves the full path —
AI decision -> tool contract -> authorization boundary -> adapter ->
artifact — end to end, without the agent ever declaring an artifact
valid itself (Rule 2: AI IS NOT THE VALIDATION AUTHORITY). Only wraps the
two Blender tool contracts that already exist and already authorize
"blender_agent" as a caller (see tools/registered_tools.py) — it does not
speculatively grow a tool catalog beyond what's actually implemented.
"""
from ai.provider_base import AIProviderError
from ai.router import AIRouter, ProviderUnavailable
from tools.tool_executor import execute as run_tool, ToolNotFound, UnsupportedCapability
from tools.tool_permissions import PermissionDenied
from tools.tool_registry import get as get_contract
from tools.tool_schemas import SchemaValidationError

CALLER_ID = "blender_agent"

TOOL_CATALOG = [
    {
        "tool_id": "validate_blend",
        "description": "Check a Blender asset against a PC performance profile "
                        "(entity counts, triangle budget, culling coverage). Use for "
                        "instructions about checking, validating, verifying, or "
                        "measuring performance.",
    },
    {
        "tool_id": "optimize_blend",
        "description": "Assign culling distances and optionally merge a group into a "
                        "new optimized copy. Use for instructions about optimizing, "
                        "improving performance, reducing draw calls, culling, or merging.",
    },
]


class BlenderAgentError(Exception):
    pass


class BlenderAgent:
    def __init__(self, router=None):
        self.router = router or AIRouter()

    def run(self, instruction, **context):
        """`context` carries the grounded facts the AI must never be
        allowed to hallucinate — blend_path, output_path, asset_name,
        profile_name, merge_group. The provider only decides WHICH tool to
        call (and may add non-grounded args); context is filtered down to
        whatever the chosen tool's own input schema accepts, so passing
        the full context here regardless of which tool ends up chosen is
        safe — the tool contract's schema is the single source of truth
        for what a given tool takes, not this agent."""
        try:
            provider = self.router.get_provider()
        except ProviderUnavailable as e:
            raise BlenderAgentError(str(e)) from e

        try:
            decision = provider.decide(instruction, TOOL_CATALOG)
        except AIProviderError as e:
            raise BlenderAgentError(f"provider '{provider.provider_id}' could not decide: {e}") from e

        tool_id = decision["tool_id"]
        contract = get_contract(tool_id)
        allowed_keys = set(contract.input_schema.keys()) if contract and contract.input_schema else set(context.keys())
        filtered_context = {k: v for k, v in context.items() if k in allowed_keys}
        args = {**decision.get("args", {}), **filtered_context}

        try:
            result = run_tool(tool_id, CALLER_ID, **args)
        except (ToolNotFound, UnsupportedCapability, PermissionDenied, SchemaValidationError) as e:
            raise BlenderAgentError(f"tool '{tool_id}' failed: {e}") from e

        return {
            "provider_id": provider.provider_id,
            "model_id": getattr(provider, "model_id", None),
            "tool_id": tool_id,
            "reasoning": decision.get("reasoning"),
            "result": result,
        }
