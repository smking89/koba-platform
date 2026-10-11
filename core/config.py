"""Loads config/*.yaml. Never hard-code a tool's executable path outside
these files — read it through here so the user can override without
touching code."""
import os

import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")


def _load_yaml(filename):
    path = os.path.join(CONFIG_DIR, filename)
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def load_tools_config():
    return _load_yaml("tools.yaml")


def load_defaults():
    return _load_yaml("defaults.yaml")


def load_export_profiles():
    return _load_yaml("export_profiles.yaml")


def load_projects_registry():
    return _load_yaml("projects.yaml")


def load_ai_providers_config():
    return _load_yaml("ai_providers.yaml")


def save_projects_registry(data):
    path = os.path.join(CONFIG_DIR, "projects.yaml")
    with open(path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
