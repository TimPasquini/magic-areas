"""Generic feature-page schema helpers for options flow."""

from __future__ import annotations

import voluptuous as vol


def copy_schema(schema: vol.Schema) -> vol.Schema:
    """Return a shallow copy so dynamic flow fields do not mutate shared schemas."""
    raw_schema = schema.schema
    if not isinstance(raw_schema, dict):
        return schema
    return vol.Schema(dict(raw_schema), extra=schema.extra)


def filter_schema_for_keys(schema: vol.Schema, include_keys: set[str]) -> vol.Schema:
    """Return a copy of schema containing only desired option keys."""
    raw_schema = schema.schema
    if not isinstance(raw_schema, dict):
        return schema

    filtered: dict[object, object] = {}
    for marker, validator in raw_schema.items():
        key = getattr(marker, "schema", marker)
        if isinstance(key, str) and key in include_keys:
            filtered[marker] = validator
    return vol.Schema(filtered, extra=vol.REMOVE_EXTRA)
