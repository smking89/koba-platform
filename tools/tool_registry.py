"""Central registry of every ToolContract — the only place tool_id ->
implementation mappings exist. tool_executor is the only module allowed
to look things up here and actually call them."""

_REGISTRY = {}


def register(contract):
    if contract.tool_id in _REGISTRY:
        raise ValueError(f"Tool '{contract.tool_id}' is already registered")
    _REGISTRY[contract.tool_id] = contract
    return contract


def get(tool_id):
    return _REGISTRY.get(tool_id)


def list_tools():
    return list(_REGISTRY.values())


def clear():
    """Test-only: reset the registry between test runs so re-importing
    registered_tools.py doesn't hit the duplicate-registration guard."""
    _REGISTRY.clear()
