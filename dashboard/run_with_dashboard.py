"""
Optional zero-edit launcher (Mode B).

Runs mad_cat.py with the dashboard logging handler attached to the root logger
first, so no source file is modified. Everything after the script name is passed
straight through to mad_cat.py.

    # from repo root:
    python3 dashboard/run_with_dashboard.py -c list.csv --yes

Works when the attackers' loggers propagate to the root logger (the logging
default). If nothing shows up in the dashboard's event stream, they don't
propagate - use Mode A instead (two lines in mad_cat.py's main).
"""

from __future__ import annotations

import logging
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent   # .../MAD-CAT/dashboard
REPO = HERE.parent                       # .../MAD-CAT  (repo root)

# Put the REPO ROOT on sys.path so mad_cat.py's own imports (attackers, config,
# ...) resolve exactly as if you'd run `python3 mad_cat.py` from the repo root.
# (The bug in the first cut inserted the dashboard/ dir here instead.)
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from dashboard.event_emitter import attach_dashboard_logging  # noqa: E402


def main() -> None:
    # keep console output working even if mad_cat relies on basicConfig (which
    # becomes a no-op once our handler is attached to root).
    root = logging.getLogger()
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        logging.basicConfig(level=logging.INFO)

    attach_dashboard_logging()

    target = REPO / "mad_cat.py"
    if not target.exists():
        sys.exit(f"mad_cat.py not found at {target} - run from the repo layout.")

    sys.argv = [str(target)] + sys.argv[1:]
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()