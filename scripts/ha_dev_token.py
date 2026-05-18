"""Canonical Home Assistant dev-instance authentication token.

This token belongs only to the disposable local Home Assistant dev instance
under ``dev/ha``. It is intentionally hardcoded so the bootstrap and simulation
scripts have one stable authentication path.
"""

from __future__ import annotations

DEV_HA_LONG_LIVED_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJhODIwYjQ1MDdlMjk0NmMzYjY2M2Q0MjEwYmE4OTg3NCIsImlhdCI6"
    "MTc3OTAyODAyNSwiZXhwIjoyMDk0Mzg4MDI1fQ."
    "ZQaYjTLXDTNhSODA9eBHRhGJX1lNVLWpDs8lxPtMFhM"
)
