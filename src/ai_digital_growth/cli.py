"""CLI for reviewing a scenario file without changing its assumptions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .economics import EconomicsInputs, FunnelAssumptions, InputValidationError


def load_scenario(path: Path) -> EconomicsInputs:
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    funnel = FunnelAssumptions(**raw.pop("funnel", {}))
    return EconomicsInputs(**raw, funnel=funnel)


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate monthly capacity and unit-economics scenarios.")
    parser.add_argument("scenario", type=Path, help="JSON file containing explicit scenario assumptions")
    parser.add_argument("--output", type=Path, help="Optional JSON output path; stdout is used by default")
    args = parser.parse_args()
    try:
        result = load_scenario(args.scenario).analyze()
    except (OSError, json.JSONDecodeError, TypeError, InputValidationError) as exc:
        print(f"Scenario rejected: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
