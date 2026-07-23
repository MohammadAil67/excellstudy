# apps/core/input_output_types.py

class ValidationError(Exception):
    """Raised when a learner's submitted input doesn't match the
    shape the agent declared for its input_type."""
    pass


APPROVED_INPUT_TYPES = [
    "text_with_units",
    "image_upload",
    "file_upload",
    "file",
    "multiple_choice",
    "free_text",
    "number",
]

APPROVED_OUTPUT_TYPES = [
    "verdict",
    "annotated_image",
    "score",
    "diff",
    "text",
    "step_list",
    "comparison",
    "hint",
]

# Each entry maps a required field name -> the Python type(s) it must be
INPUT_TYPE_SCHEMAS = {
    "text_with_units": {"value": str},
    "number": {"value": (int, float)},
    "image_upload": {"image_url": str},
    "file_upload": {"file_url": str},
    "file": {"file_url": str},
    "multiple_choice": {"selected_index": int},
    "free_text": {"value": str},
}


def validate_input_payload(input_type: str, data: dict) -> None:
    """
    Confirms `data` (the learner's submitted input, from the
    request body's "input" field) matches the schema required
    for the agent's declared input_type.

    Called in views.py::invoke_agent, AFTER resolving the agent
    via registry.get_agent(), and BEFORE calling
    router.forward_to_agent() — so a malformed submission never
    wastes a network call to the agent pod.

    Raises ValidationError with a clear, specific message on
    any mismatch.
    """
    schema = INPUT_TYPE_SCHEMAS.get(input_type)
    if schema is None:
        raise ValidationError(
            f"Unknown input_type '{input_type}' — this agent's "
            f"registered input_type is not one of the approved types."
        )

    if not isinstance(data, dict):
        raise ValidationError(
            f"'input' must be an object, got {type(data).__name__}"
        )

    for field, expected_type in schema.items():
        if field not in data:
            raise ValidationError(
                f"Missing required field '{field}' for input_type "
                f"'{input_type}'"
            )
        if not isinstance(data[field], expected_type):
            raise ValidationError(
                f"Field '{field}' must be of type "
                f"{_type_name(expected_type)}, got "
                f"{type(data[field]).__name__}"
            )


def _type_name(expected_type) -> str:
    if isinstance(expected_type, tuple):
        return " or ".join(t.__name__ for t in expected_type)
    return expected_type.__name__