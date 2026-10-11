"""The AI provider interface (master spec section 9/32). Every provider
— rule-based, Anthropic, or a future OpenAI one — implements this same
two-method contract, which is what makes the router swap (Rule 1: AI IS
REPLACEABLE) real instead of aspirational: nothing outside ai/ needs to
change to add or swap a provider.
"""
import json
import re
from abc import ABC, abstractmethod


class AIProviderError(Exception):
    pass


class AIProvider(ABC):
    provider_id = None
    model_id = None

    @abstractmethod
    def available(self):
        """Capability check — e.g. an API key is present. Mirrors
        core.detection's pattern of never faking availability: a provider
        that can't actually run must say so, not be silently skipped."""

    @abstractmethod
    def decide(self, instruction, tool_catalog):
        """Maps a free-text instruction plus a catalog of tool descriptors
        (list of {"tool_id", "description"}) to {"tool_id": ..., "args": {},
        "reasoning": ...}. Must raise AIProviderError rather than returning
        a tool_id absent from tool_catalog. The provider only decides WHAT
        to do — per master-spec Rule 2 (AI IS NOT THE VALIDATION
        AUTHORITY), it never sees or reports validation results, and the
        caller is responsible for actually executing the decision through
        tools.tool_executor."""


def parse_json_decision(text, tool_catalog):
    """Shared by any provider that gets its decision back as raw text
    containing a JSON object (e.g. an LLM's response) rather than
    structured output."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise AIProviderError(f"provider response did not contain a JSON decision: {text!r}")
    try:
        decision = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise AIProviderError(f"provider response was not valid JSON: {e}") from e

    catalog_ids = {t["tool_id"] for t in tool_catalog}
    if decision.get("tool_id") not in catalog_ids:
        raise AIProviderError(f"provider chose an unknown tool_id: {decision.get('tool_id')!r}")
    decision.setdefault("args", {})
    return decision
