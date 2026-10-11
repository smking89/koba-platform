"""Real tests for the AI provider/router/agent path (master spec section
9 + 32). No mocks: the rule_based provider is a genuinely working
deterministic provider (not a stand-in for a real one), and the
end-to-end agent test runs an actual Blender subprocess exactly like
test_cli.py's validate/optimize integration test."""
import os
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.provider_base import AIProviderError  # noqa: E402
from ai.providers.rule_based_provider import RuleBasedProvider  # noqa: E402
from ai.providers.anthropic_provider import AnthropicProvider  # noqa: E402
from ai.router import AIRouter, ProviderUnavailable  # noqa: E402
from agents.blender_agent import BlenderAgent, BlenderAgentError, TOOL_CATALOG  # noqa: E402
from core.config import load_tools_config  # noqa: E402
from tools import registered_tools  # noqa: E402
from tools.tool_audit import read_recent  # noqa: E402

registered_tools.register_all()

BLENDER_ADAPTER_DIR = os.path.join(PROJECT_ROOT, "adapters", "blender")


def _build_real_fixture_blend(dest_path):
    """Same real (non-mocked) Blender build used by test_cli.py."""
    blender = load_tools_config()["blender"]["executable"]
    subprocess.run(
        [blender, "-b", "--python", "tests/test1_crate.py"],
        cwd=BLENDER_ADAPTER_DIR, capture_output=True, text=True, timeout=60, check=True,
    )
    src = os.path.join(BLENDER_ADAPTER_DIR, "assets", "generated", "test1_crate.blend")
    assert os.path.isfile(src), "fixture build did not produce test1_crate.blend"
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.copyfile(src, dest_path)


def run():
    # --- RuleBasedProvider: real deterministic decisions, no network ---
    provider = RuleBasedProvider()
    assert provider.available() is True

    decision = provider.decide("please validate this asset's performance", TOOL_CATALOG)
    assert decision["tool_id"] == "validate_blend"

    decision = provider.decide("optimize this and merge the mergeable group", TOOL_CATALOG)
    assert decision["tool_id"] == "optimize_blend"

    try:
        provider.decide("make me a sandwich", TOOL_CATALOG)
        assert False, "an instruction that maps to nothing must raise, not silently guess"
    except AIProviderError:
        pass

    # --- AnthropicProvider: honest capability detection, no fake success ---
    anthropic = AnthropicProvider(api_key=None)
    assert anthropic.available() is False, \
        "no ANTHROPIC_API_KEY is set in this environment — must genuinely report unavailable"
    try:
        anthropic.decide("validate this", TOOL_CATALOG)
        assert False, "must not fake a decision when unavailable"
    except AIProviderError:
        pass

    # --- AIRouter: Rule 1 (AI IS REPLACEABLE) — swap providers via config alone ---
    router = AIRouter(config={
        "active_provider": "rule_based",
        "providers": {
            "rule_based": {"module": "ai.providers.rule_based_provider", "class": "RuleBasedProvider"},
            "anthropic": {"module": "ai.providers.anthropic_provider", "class": "AnthropicProvider"},
        },
    })
    provider_a = router.get_provider()
    assert provider_a.provider_id == "rule_based"

    router.config["active_provider"] = "anthropic"
    try:
        router.get_provider()
        assert False, "anthropic provider must be reported unavailable, not silently substituted"
    except ProviderUnavailable:
        pass

    try:
        router.get_provider(name="not_a_real_provider")
        assert False, "an unconfigured provider name must raise, not return None"
    except ProviderUnavailable:
        pass

    # --- BlenderAgent: real end-to-end, through the actual tool contracts ---
    fixture_path = os.path.join(BLENDER_ADAPTER_DIR, "assets", "generated", "test_ai_agent_fixture.blend")
    _build_real_fixture_blend(fixture_path)
    try:
        agent = BlenderAgent()

        outcome = agent.run(
            "please validate this asset against our performance budget",
            blend_path=fixture_path, profile_name="60fps_standard",
        )
        assert outcome["tool_id"] == "validate_blend"
        assert outcome["provider_id"] == "rule_based"
        assert outcome["result"]["result"] == "PASS"

        recent = read_recent(limit=5)
        assert any(e["tool_id"] == "validate_blend" and e["caller_id"] == "blender_agent" and e["success"]
                   for e in recent), "the agent's call must go through the real authorization/audit boundary"

        optimized_path = os.path.join(BLENDER_ADAPTER_DIR, "assets", "generated", "test_ai_agent_optimized.blend")
        outcome = agent.run(
            "optimize this asset and cut down draw calls",
            blend_path=fixture_path, profile_name="60fps_standard", output_path=optimized_path,
        )
        assert outcome["tool_id"] == "optimize_blend"
        assert os.path.isfile(optimized_path), "the real optimize_blend adapter must have run and written output"

        # unmappable instruction must fail loudly through the agent too, not silently no-op
        try:
            agent.run("what's the weather today", blend_path=fixture_path)
            assert False
        except BlenderAgentError:
            pass

    finally:
        optimized_path = os.path.join(BLENDER_ADAPTER_DIR, "assets", "generated", "test_ai_agent_optimized.blend")
        if os.path.isfile(fixture_path):
            os.remove(fixture_path)
        if os.path.isfile(optimized_path):
            os.remove(optimized_path)

    return True


if __name__ == "__main__":
    ok = run()
    print("test_ai_agent: PASS" if ok else "test_ai_agent: FAIL")
    sys.exit(0 if ok else 1)
