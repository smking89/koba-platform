"""The build state machine (master spec section 23). This is a real
subset of the spec's full state list (CREATED, QUEUED, PLANNING, RUNNING,
VALIDATING, REPAIRING, PACKAGING, SIGNING, READY, PUBLISHED, FAILED,
CANCELLED) — only the states this codebase's actual commands can reach
are wired up. REPAIRING is real (repair/repair_engine.py +
cli/main.py's cmd_repair). PACKAGING -> SIGNING -> READY is real now too
(compiler/product_compiler.py + packaging/package_builder.py +
packaging/signature_generator.py's real Ed25519 signing, reached via
cli/main.py's cmd_package). QUEUED/PLANNING (no AI planner yet —
pipeline_manager dispatches synchronously, it doesn't queue/schedule) and
PUBLISHED (no marketplace yet) are still declared for forward-
compatibility but have no valid transitions into them today — reaching
them would be fabricating capability that doesn't exist, which this
project avoids on principle.
"""

CREATED = "CREATED"
QUEUED = "QUEUED"
PLANNING = "PLANNING"
RUNNING = "RUNNING"
VALIDATING = "VALIDATING"
REPAIRING = "REPAIRING"
PACKAGING = "PACKAGING"
SIGNING = "SIGNING"
READY = "READY"
PUBLISHED = "PUBLISHED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"

ALL_STATES = {CREATED, QUEUED, PLANNING, RUNNING, VALIDATING, REPAIRING,
              PACKAGING, SIGNING, READY, PUBLISHED, FAILED, CANCELLED}

TERMINAL_STATES = {READY, PUBLISHED, CANCELLED}

# Only transitions this codebase can actually reach today are allowed.
_TRANSITIONS = {
    CREATED: {RUNNING, CANCELLED},
    RUNNING: {VALIDATING, PACKAGING, REPAIRING, FAILED, CANCELLED},
    VALIDATING: {READY, FAILED, CANCELLED},
    PACKAGING: {SIGNING, READY, FAILED, CANCELLED},
    SIGNING: {READY, FAILED, CANCELLED},
    REPAIRING: {READY, FAILED, CANCELLED},
    READY: set(),
    FAILED: {RUNNING, CANCELLED},  # resume re-enters RUNNING — never silently overwrites, see job_manager.resume
    CANCELLED: set(),
    # Declared, not reachable yet — see module docstring:
    QUEUED: set(),
    PLANNING: set(),
    PUBLISHED: set(),
}


class InvalidTransition(Exception):
    pass


def valid_transition(from_state, to_state):
    return to_state in _TRANSITIONS.get(from_state, set())


def require_valid_transition(from_state, to_state):
    if not valid_transition(from_state, to_state):
        raise InvalidTransition(f"Cannot transition {from_state} -> {to_state}")
