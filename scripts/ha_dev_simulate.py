#!/usr/bin/env python3
"""Compatibility entrypoint for the modular Magic Areas HA dev simulator."""

from __future__ import annotations

from scripts.ha_dev_simulation.cli import main, parse_args
from scripts.ha_dev_simulation.runner import simulate

__all__ = ["main", "parse_args", "simulate"]


if __name__ == "__main__":
    raise SystemExit(main())
