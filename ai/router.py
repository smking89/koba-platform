"""AIRouter: the single seam for master-spec Rule 1 (AI IS REPLACEABLE).
Everything that wants an AI decision — agents/blender_agent.py today,
any future agent — asks the router for "the active provider" and never
imports a specific provider module directly. Swapping providers is a
one-line edit to config/ai_providers.yaml.
"""
import importlib

from core.config import load_ai_providers_config


class ProviderUnavailable(Exception):
    pass


def _instantiate(entry):
    module = importlib.import_module(entry["module"])
    cls = getattr(module, entry["class"])
    return cls()


class AIRouter:
    def __init__(self, config=None):
        self.config = config or load_ai_providers_config()

    def get_provider(self, name=None):
        name = name or self.config["active_provider"]
        entry = self.config["providers"].get(name)
        if entry is None:
            raise ProviderUnavailable(f"no such AI provider configured: '{name}'")

        provider = _instantiate(entry)
        if not provider.available():
            raise ProviderUnavailable(
                f"AI provider '{name}' is not available (e.g. missing API key) — "
                f"see config/ai_providers.yaml"
            )
        return provider
