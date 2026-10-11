"""Authorization check — the actual enforcement of a contract's
allowed_callers list. This is what makes the boundary real rather than
decorative: tool_executor calls check_permission() before it will invoke
anything, and a denied call never reaches the adapter."""


class PermissionDenied(Exception):
    pass


def check_permission(contract, caller_id):
    if caller_id not in contract.allowed_callers:
        raise PermissionDenied(
            f"'{caller_id}' is not authorized to call tool '{contract.tool_id}'. "
            f"Allowed callers: {contract.allowed_callers}"
        )
