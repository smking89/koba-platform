"""The actual authorization boundary (master spec Rule 3: "AI must
operate through KOBA Tool Contracts", Rule 4: "adapters are the only
external-application boundary" — this is what sits between a caller and
that boundary). Every real tool invocation in this codebase should go
through execute(), not call an adapter function directly — including
from the CLI, which is why cli/main.py was rewired to use this instead
of importing adapters.blender_bridge etc. directly.
"""
import time

from core.detection import detect_tool
from tools import tool_registry
from tools.tool_permissions import check_permission, PermissionDenied
from tools.tool_schemas import validate as validate_schema, SchemaValidationError
from tools.tool_audit import record as audit_record


class ToolNotFound(Exception):
    pass


class UnsupportedCapability(Exception):
    """Raised instead of ever attempting a call when a required capability
    isn't actually present — master spec section 8: "never fake successful
    execution."""


def execute(tool_id, caller_id, **kwargs):
    contract = tool_registry.get(tool_id)
    if contract is None:
        raise ToolNotFound(f"No such tool: '{tool_id}'")

    start = time.monotonic()
    try:
        check_permission(contract, caller_id)

        for capability in contract.required_capabilities:
            status = detect_tool(capability)
            if not status.found:
                raise UnsupportedCapability(
                    f"Tool '{tool_id}' requires capability '{capability}', which is not "
                    f"available on this machine: {status.error}"
                )

        if contract.input_schema:
            validate_schema(kwargs, contract.input_schema, label=f"{tool_id} input")

        result = contract.implementation(**kwargs)

        if contract.output_schema and isinstance(result, dict):
            validate_schema(result, contract.output_schema, label=f"{tool_id} output")

    except (PermissionDenied, UnsupportedCapability, SchemaValidationError, Exception) as e:
        audit_record(tool_id, caller_id, success=False, duration_seconds=time.monotonic() - start,
                      arg_keys=kwargs.keys(), error=f"{type(e).__name__}: {e}")
        raise

    audit_record(tool_id, caller_id, success=True, duration_seconds=time.monotonic() - start,
                  arg_keys=kwargs.keys())
    return result
