"""Internal helpers to assemble maps from map elements."""


def is_reference_field(cls: type, field_name: str) -> bool:
    """Return whether a field of a model element class refers to another element.

    A field refers to another element when a class of `cls.__mro__` that
    declares the field marks it with `"reference": True` in its metadata, so a
    subclass that declares the field again needs no mark.

    Args:
        cls: The model element class.
        field_name: The name of the field.

    Returns:
        `True` if the field is a reference field, `False` otherwise.
    """
    for base in cls.__mro__:
        field = base.__dict__.get("__dataclass_fields__", {}).get(field_name)
        if field is not None and field.metadata.get("reference", False):
            return True
    return False
