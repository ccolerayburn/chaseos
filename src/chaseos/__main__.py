"""ChaseOS application entrypoint."""

from __future__ import annotations

import sys
from collections.abc import Callable

from chaseos.app.headless import run_headless_cli


def main(
    argv: list[str] | None = None,
    tray_run: Callable[[list[str]], int] | None = None,
) -> int:
    """Launch the ChaseOS tray shell."""

    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        return run_headless_cli(args)

    if tray_run is None:
        from chaseos.app.tray_app import run as tray_run

    return tray_run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
