# ChaseOS Agent Instructions

## Overview

ChaseOS is an on-demand Windows tray app that opens a small terminal-style command
window and guides a 15-minute work startup ritual.

The user answers one natural-language check-in: "How are you, really?" ChaseOS converts
that response into practical non-clinical work-start signals, describes a generated
cyberpunk/minimal theme in text, asks for approval or changes, generates daily visual
assets, and eventually applies private wallpapers per monitor.

## Product Principles

- Keep the app quiet, fast, and local-first.
- Treat ChaseOS as a private launch console, not a dashboard.
- Prefer one focused ritual flow over broad navigation.
- Make the user feel oriented for work without pathologizing their state.
- Keep public-facing output separate from private check-in content.

## UI Rules

- ChaseOS is an on-demand Windows tray app.
- The main UI is a small terminal-style dark command window.
- The default window should be modest in size and resizable.
- Use a dark gray background.
- Use muted darker yellow or amber monospaced text.
- Do not build a dashboard UI.
- Do not build a visual theme preview.
- Describe generated themes in text and ask for approval.
- Support commands such as `/approve`, `/change calmer`, and `/regenerate`.
- The full ritual target is 15 minutes.

## Privacy and Safety Rules

- Do not implement formal ADHD, depression, or anxiety questionnaires.
- Do not diagnose the user.
- Do not use clinical labels.
- Interpret check-ins only into practical signals:
  - `energy`
  - `clarity`
  - `pressure`
  - `mood_weight`
  - `focus_friction`
  - `body_context`
  - `social_battery`
  - `readiness`
- Avoid mental-health scoring language.
- Keep private check-in text out of public-facing files.
- Do not call OpenAI in Phase 1.
- Do not require admin rights.
- Do not modify registry settings.
- Do not modify taskbar pins or icons yet.

## Public Poster Rules

- Display 1 is public-facing.
- The public poster must be 1080x1920 unless a later phase explicitly changes it.
- The public poster must never include private check-in details.
- The public poster should be based only on the innovation exercise takeaway.
- Redact ticket numbers, hostnames, URLs, emails, IPs, usernames, company names, internal
  systems, credentials, and private health details from public content.
- General local photos must not be used on Display 1 by default.

## Monitor Layout Rules

- Display 1: portrait public-facing monitor, public innovation poster.
- Display 4: landscape private monitor, left atmosphere wallpaper.
- Display 2: landscape private monitor, center command wallpaper.
- Display 3: landscape private monitor, right inspiration wallpaper.
- Do not apply wallpapers yet in Phase 1.

## Local Photo Source Rules

- Later phases may index photos from:

```text
C:\_Media\Photos\Lightroom\Export
```

- Treat local photos as private unless explicitly classified otherwise.
- Never use general local photos for the public Display 1 poster by default.

## Testing Expectations

- Keep tests focused and fast.
- Test command parsing, check-in signal boundaries, public redaction, theme generation,
  timer behavior, poster safety, and wallpaper output dimensions as those modules mature.
- Public poster tests must verify that raw check-in text cannot leak.
- Tests should run with `pytest`.

## Runtime Storage Expectations

- Runtime generated files should eventually go under:

```text
%LOCALAPPDATA%\ChaseOS
```

- Do not store generated assets in the source tree except temporary test fixtures.
- Do not persist secrets in project files.

## Coding Standards

- Python 3.11+.
- PySide6 for the tray app and terminal-style GUI.
- Pillow for poster and wallpaper rendering.
- Pydantic for data models.
- pytest for tests.
- Use a `src/` layout.
- Keep modules small and boring.
- Prefer explicit data models over loose dictionaries.
- Keep Windows-specific code isolated under `windows/`.
- Keep public safety code close to poster generation.

## Done Criteria

- The scaffold exists.
- `python -m chaseos` works after editable install and prints:

```text
ChaseOS scaffold ready.
```

- `pytest` runs successfully.
- README exists and explains setup, run, tests, MVP scope, and safety boundaries.
- AGENTS.md captures durable project rules.

