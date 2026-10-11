"""Global project defaults. Individual assets may override any of these."""

DEFAULT_SCALE_UNIT = "meters"
DEFAULT_AUTHOR = "claude-code"
NAMING_SEPARATOR = "_"

# Polygon budgets used by validation.py — advisory, not hard limits.
POLY_BUDGET_PROP = 5_000
POLY_BUDGET_VEHICLE = 40_000
POLY_BUDGET_BUILDING = 80_000
POLY_BUDGET_MONUMENT = 150_000
