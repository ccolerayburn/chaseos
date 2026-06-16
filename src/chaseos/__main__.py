"""ChaseOS application entrypoint."""

from __future__ import annotations

import sys

from chaseos.app.tray_app import run


def main() -> int:
    """Launch the ChaseOS tray shell."""

    return run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
