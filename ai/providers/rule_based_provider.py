"""A real, working AI provider that makes no network call — always
available, no API key, fully deterministic. This is the default provider
(see config/ai_providers.yaml) precisely so the agent path has something
genuine to run against without depending on external credentials; it is
not a mock standing in for a real provider; it IS one, per the same
interface every other provider implements.
"""
import re

from ai.provider_base import AIProvider, AIProviderError

_KEYWORDS = {
    "optimize_blend": (
        "optimize", "improve performance", "merge", "reduce draw calls",
        "cull", "lod", "instance", "lower poly", "speed up",
    ),
    "validate_blend": (
        "validate", "check", "verify", "how does it perform", "does it pass",
        "measure", "test performance", "audit",
    ),
}

# Real extraction, not a guess: looks for an explicit visibility_group
# name in the instruction text, tried most-specific pattern first. Only
# applied for tool_ids where a merge_group is actually meaningful (see
# decide() below) — RepairAgent's one-entry catalog, or BlenderAgent's
# optimize_blend when the instruction happens to name a group.
_MERGE_GROUP_PATTERNS = (
    re.compile(r"merge\s+(?:the\s+)?['\"]([^'\"]+)['\"]\s*group", re.IGNORECASE),
    re.compile(r"group\s+['\"]([^'\"]+)['\"]", re.IGNORECASE),
    re.compile(r"merge\s+(?:the\s+)?(\w[\w-]*)\s+group", re.IGNORECASE),
)


def _extract_merge_group(instruction):
    for pattern in _MERGE_GROUP_PATTERNS:
        match = pattern.search(instruction)
        if match:
            return match.group(1)
    return None


class RuleBasedProvider(AIProvider):
    provider_id = "rule_based"
    model_id = "keyword-match-v1"

    def available(self):
        return True

    def decide(self, instruction, tool_catalog):
        catalog_ids = [t["tool_id"] for t in tool_catalog]

        if len(catalog_ids) == 1:
            # A single-entry catalog (e.g. RepairAgent's) has nothing to
            # disambiguate — the catalog itself is the decision.
            tool_id = catalog_ids[0]
        else:
            lowered = instruction.lower()
            scored = []
            for tid, keywords in _KEYWORDS.items():
                if tid not in catalog_ids:
                    continue
                hits = sum(1 for kw in keywords if kw in lowered)
                if hits:
                    scored.append((hits, tid))
            if not scored:
                raise AIProviderError(f"could not map instruction to any tool in catalog: {instruction!r}")
            scored.sort(reverse=True)
            _, tool_id = scored[0]

        args = {}
        if tool_id in ("optimize_blend", "attempt_repair"):
            merge_group = _extract_merge_group(instruction)
            if merge_group:
                args["merge_group"] = merge_group

        return {"tool_id": tool_id, "args": args, "reasoning": f"keyword match ({self.model_id})"}
