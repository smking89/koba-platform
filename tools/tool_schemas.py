"""Minimal schema validation — plain dict-based, no jsonschema dependency
(consistent with this project's stdlib-only orchestration layer). A
schema is {"field_name": {"type": <type or tuple of types>, "required": bool}}.
Good enough for the tool contracts in this repo; not a general-purpose
JSON Schema implementation.
"""


class SchemaValidationError(Exception):
    pass


def validate(data, schema, label="value"):
    """Raises SchemaValidationError with a precise message on the first
    problem found. Returns nothing on success — call it for its side
    effect (raising), matching how the rest of this codebase signals
    failure (exceptions, not a silently-ignored return code)."""
    for field, spec in schema.items():
        required = spec.get("required", False)
        expected_type = spec.get("type")

        if field not in data or data[field] is None:
            if required:
                raise SchemaValidationError(f"{label}: missing required field '{field}'")
            continue

        if expected_type is not None and not isinstance(data[field], expected_type):
            raise SchemaValidationError(
                f"{label}: field '{field}' expected {expected_type}, got {type(data[field]).__name__}"
            )

    unexpected = set(data.keys()) - set(schema.keys())
    if unexpected:
        raise SchemaValidationError(f"{label}: unexpected field(s) not in schema: {sorted(unexpected)}")
