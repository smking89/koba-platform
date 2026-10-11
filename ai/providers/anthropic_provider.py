"""A real Anthropic (Claude) provider — genuine HTTP calls to the actual
Messages API via stdlib urllib, consistent with this project's
stdlib-only orchestration layer (no `anthropic` SDK dependency). Requires
ANTHROPIC_API_KEY in the environment; available() reports False rather
than faking a response when it's missing, same as core.detection does
for GIMP/Krita/FFmpeg. This is what section 32's "Claude -> GPT" provider
swap actually points at — the router (ai/router.py) is the only thing
that has to change to go from rule_based to this, or from this to a
future OpenAI provider.
"""
import json
import os
import urllib.error
import urllib.request

from ai.provider_base import AIProvider, AIProviderError, parse_json_decision

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-3-5-haiku-20241022"


def _build_system_prompt(tool_catalog):
    lines = [
        "You are the blender_agent decision layer for the KOBA Creator Engine.",
        "Given an instruction, choose exactly one tool from this catalog and reply with ONLY a JSON object "
        '{"tool_id": "<id>", "args": {}, "reasoning": "<one sentence>"}. '
        "Never invent a tool_id outside the catalog. Never decide whether a result is valid — "
        "that is not your job.",
        "",
        "Tool catalog:",
    ]
    for tool in tool_catalog:
        lines.append(f"- {tool['tool_id']}: {tool['description']}")
    return "\n".join(lines)


class AnthropicProvider(AIProvider):
    provider_id = "anthropic"
    model_id = DEFAULT_MODEL

    def __init__(self, api_key=None, model=DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model_id = model

    def available(self):
        return bool(self.api_key)

    def decide(self, instruction, tool_catalog):
        if not self.available():
            raise AIProviderError("ANTHROPIC_API_KEY not set — anthropic provider unavailable")

        payload = json.dumps({
            "model": self.model_id,
            "max_tokens": 300,
            "system": _build_system_prompt(tool_catalog),
            "messages": [{"role": "user", "content": instruction}],
        }).encode("utf-8")

        request = urllib.request.Request(
            ANTHROPIC_API_URL, data=payload, method="POST",
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": ANTHROPIC_API_VERSION,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise AIProviderError(f"anthropic API request failed: {e}") from e

        text = "".join(block.get("text", "") for block in body.get("content", []))
        return parse_json_decision(text, tool_catalog)
