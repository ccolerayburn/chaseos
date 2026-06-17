# ChaseOS

ChaseOS is an on-demand Windows tray app that opens a small terminal-style dark command
window for a 15-minute work startup ritual.

The first version asks one natural-language check-in, interprets it into practical
non-clinical work-start signals, describes a generated cyberpunk/minimal theme in text,
asks for approval or changes, and prepares daily visual outputs for a known four-monitor
layout.

## Setup

```powershell
cd C:\_Codex\chaseos
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Run

```powershell
python -m chaseos
```

This launches the Phase 8 PySide6 tray shell and terminal window. On a fresh machine,
the local virtual environment command is also reliable:

```powershell
.\.venv\Scripts\python.exe -m chaseos
```

## Test

```powershell
pytest
```

Or, from the local virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Current Phase 9 Scope

- Windows-first PySide6 tray app.
- Small resizable terminal-style GUI, dark gray background, muted amber monospaced text.
- No dashboard UI and no visual theme preview.
- System tray icon with show/hide behavior.
- Right-click tray menu with ChaseOS placeholder actions.
- Scrollable terminal output and single command input line.
- Commands such as `/help`, `/start`, `/approve`, `/change calmer`, `/regenerate`,
  `/monitors`, `/detect monitors`, `/monitor roles`, `/assign display 1 public`,
  `/auto assign monitors`, `/save monitors`, `/reset monitors`, `/photos`,
  `/index photos`, `/photo source`, `/wallpapers`, `/generate wallpapers`,
  `/apply wallpapers --dry-run`, `/apply wallpapers --confirm`, `/reset wallpapers`,
  `/clear`, and `/exit`.
- `/start` runs the full text-only 15-minute ritual flow.
- The header shows current ritual stage, elapsed time, and remaining target time.
- The ritual captures a private check-in and runs deterministic local interpretation.
- ChaseOS produces practical non-clinical signals, a startup mode, and a real text
  theme plan.
- Theme approval supports `/approve`, `/change <request>`, `/regenerate`, and `/skip`.
- Mindfulness, verse, innovation, work ramp, and applying remain text-first.
- After the innovation takeaway, ChaseOS creates a text-free Display 1 art plan
  seeded only by the public-safe innovation takeaway.
- Display 1 art approval supports `/approve`, `/change <request>`, `/regenerate`,
  `/poster`, and `/skip`.
- On poster approval, ChaseOS renders a real 1080x1920 PNG for Display 1 and saves
  metadata next to it.
- During the APPLYING stage, ChaseOS renders private 1920x1080 wallpapers for Displays
  4, 2, and 3.
- ChaseOS can index the local Lightroom export folder and blend private local photos
  into Displays 4 and 3 when the approved theme requests photo use.
- Display 2 remains generated/minimal by default for low visual noise.
- ChaseOS detects Windows monitor geometry when available, falls back safely to the
  known four-monitor layout when detection is unavailable, and persists ChaseOS monitor
  role mappings.
- Private wallpapers are generated locally and can be applied per monitor only after
  explicit confirmation.
- Runtime generated files should eventually live under `%LOCALAPPDATA%\ChaseOS`.

## Using `/start`

Run the app, then type:

```text
/start
```

ChaseOS will ask:

```text
how are you, really?
```

Answer in plain language. The Phase 8 engine interprets the answer locally into
practical work-start signals, then asks you to approve, change, regenerate, or skip the
text-only theme plan. Later in the ritual, your innovation takeaway is converted to a
public-safe seed for text-free Display 1 generated art. At the end, ChaseOS generates
private wallpapers from the selected theme only.

## Local Interpretation

ChaseOS interprets check-ins only into practical signals:

- `energy`
- `clarity`
- `pressure`
- `mood_weight`
- `focus_friction`
- `body_context`
- `social_battery`
- `readiness`

Startup modes:

- Calm Start
- Structured Start
- Gentle Start
- Momentum Start
- Deep Work Start
- Triage Start

Theme families:

- Obsidian Terminal
- Neon Noir
- Chrome Monolith
- Violet Circuit
- Redline Protocol
- Arctic Interface
- Synth Sanctuary
- Synthetic Sunrise
- Dusk Skyline
- Mako Reactor
- Lofi Dusk

Supported theme changes include:

- `/change calmer`
- `/change less visual noise`
- `/change more minimal`
- `/change more cyberpunk`
- `/change more yellow`
- `/change less cyan`
- `/change use more local photos`
- `/change no photos today`
- `/change darker`
- `/change brighter`
- `/change more contrast`
- `/change less contrast`

## Daily Public Generated Art

Display 1 is the public portrait monitor. ChaseOS renders text-free generated art:

```text
%LOCALAPPDATA%\ChaseOS\posters\YYYY-MM-DD\display_1_public_signal.png
```

Metadata is saved next to it:

```text
%LOCALAPPDATA%\ChaseOS\posters\YYYY-MM-DD\public_poster_meta.json
```

The Display 1 art engine:

- uses the public-safe innovation takeaway only as a deterministic seed
- renders no readable text and does not use fonts or glyph drawing
- never uses general Lightroom/local photos
- never uses the raw check-in for public art content
- writes the same image and metadata paths as the old poster contract

Display 1 art approval commands:

- `/approve`
- `/skip`
- `/poster`
- `/regenerate`
- `/change more cyberpunk`
- `/change lofi`
- `/change ff7` or `/change mako`
- `/change darker`
- `/change brighter`
- `/change more geometry`
- `/change less geometry`
- `/change no figure`
- `/change calmer skyline`

## Private Monitor Wallpapers

Display role mapping:

- Display 1: public generated art, 1080x1920
- Display 4: left atmosphere wallpaper, 1920x1080
- Display 2: center command wallpaper, 1920x1080
- Display 3: right inspiration wallpaper, 1920x1080

## Monitor Detection and Role Mapping

ChaseOS detects connected Windows monitors without admin rights when Windows exposes
monitor rectangles through normal display APIs. If real detection is unavailable, it
uses the known ChaseOS fallback layout:

- Display 1: public signal monitor, portrait 1080x1920
- Display 4: left atmosphere monitor, landscape
- Display 2: center command monitor, landscape
- Display 3: right inspiration monitor, landscape

Known layout shape:

```text
[ Display 1 portrait ] [ Display 4 landscape ] [ Display 2 landscape ] [ Display 3 landscape ]
```

Monitor commands:

- `/monitors` detects monitors and prints the current ChaseOS role mapping.
- `/detect monitors` forces a fresh detection pass.
- `/monitor roles` prints the saved role mapping.
- `/assign display 1 public`
- `/assign display 4 left`
- `/assign display 2 center`
- `/assign display 3 right`
- `/auto assign monitors` maps the known layout when possible and saves it.
- `/save monitors` saves the current mapping.
- `/reset monitors` clears the saved mapping and returns to auto-detect/fallback behavior.

Saved monitor mappings live at:

```text
%LOCALAPPDATA%\ChaseOS\config\monitor_mapping.json
```

Windows and GPU/dock behavior can change display labels, so ChaseOS stores stable IDs
when available and warns if a saved mapping appears stale.

Private wallpapers are saved under:

```text
%LOCALAPPDATA%\ChaseOS\generated\YYYY-MM-DD\
```

Files:

```text
display_4_left_atmosphere.png
display_2_center_command.png
display_3_right_inspiration.png
wallpaper_manifest.json
```

Commands:

- `/wallpapers` prints generated private wallpaper paths.
- `/generate wallpapers` generates or regenerates private wallpapers after a theme plan
  exists.
- `/apply wallpapers` previews the per-monitor application plan.
- `/apply wallpapers --dry-run` previews the per-monitor application plan.
- `/apply wallpapers --confirm` applies wallpapers to Windows per monitor.
- `/reset wallpapers` restores the previous per-monitor wallpapers when rollback state
  exists.

Private wallpapers use abstract local geometry and, when enabled by the theme, private
local photo hybrids. They do not render the raw check-in, innovation takeaway, poster
quote, ticket details, usernames, URLs, hostnames, or other readable private text.

Local photo source:

```text
C:\_Media\Photos\Lightroom\Export
```

Photo commands:

- `/photos` prints source/index status, image count, last indexed timestamp, and confirms
  public use is disabled.
- `/index photos` indexes supported local `.jpg`, `.jpeg`, `.png`, and `.webp` files.
- `/photo source` prints the configured source folder.

Photo indexing is local-only. ChaseOS stores private photo metadata under:

```text
%LOCALAPPDATA%\ChaseOS\photo_index\photo_index.json
```

The index records dimensions, orientation, average color, brightness, saturation, file
size, and indexed time. It does not run face recognition, OCR, identity inference, or
external service calls. Generated wallpaper PNGs are freshly rendered and do not preserve
source EXIF metadata.

Display 1 public generated art restrictions:

- General local photos are never used on Display 1.
- Readable text is never rendered on Display 1 art.
- If approved Display 1 art exists, it remains the Display 1 source.
- The generated `display_1_public_signal.png` placeholder is used only when no approved
  public art path is available.

## Wallpaper Application

Phase 9 adds safe per-monitor Windows wallpaper application. Phase 10 adds diagnostics
and strict preflight verification so ChaseOS can reconcile its Display 1/4/2/3 role
model with real Windows `IDesktopWallpaper` monitor IDs before any confirmed apply.

Dry-run is the default:

```text
/apply wallpapers
/apply wallpapers --dry-run
```

Real wallpaper changes require explicit confirmation:

```text
/apply wallpapers --confirm
```

Rollback:

```text
/reset wallpapers
```

Wallpaper verification workflow:

1. Run:

```text
/wallpaper status
```

2. Run:

```text
/wallpaper diagnostics
```

3. Run:

```text
/verify wallpapers
```

4. Run:

```text
/apply wallpapers --dry-run
```

5. Only after verifying the mapping manually, run:

```text
/apply wallpapers --confirm
```

6. To rollback:

```text
/reset wallpapers
```

Application state is saved under:

```text
%LOCALAPPDATA%\ChaseOS\wallpaper_state\previous_wallpapers.json
%LOCALAPPDATA%\ChaseOS\wallpaper_state\last_apply_manifest.json
```

Safety rules:

- Phase 10 still defaults to no wallpaper changes.
- `/verify wallpapers` and `/wallpaper diagnostics` never apply wallpapers.
- `/apply wallpapers --confirm` is the only real apply command.
- ChaseOS saves previous wallpaper state before applying new wallpaper paths.
- ChaseOS uses the per-monitor Windows wallpaper API.
- ChaseOS resolves monitor IDs by exact ID, device path, then rectangle.
- Confirmed apply refuses unresolved Windows monitor IDs.
- ChaseOS does not modify registry settings.
- ChaseOS does not restart Explorer.
- ChaseOS does not require admin rights.
- ChaseOS does not programmatically modify taskbar pins.
- Display 1 never uses general local photos or readable text.

If monitor mapping looks wrong, use the existing monitor commands:

- `/monitors`
- `/detect monitors`
- `/monitor roles`
- `/assign display 1 public`
- `/assign display 4 left`
- `/assign display 2 center`
- `/assign display 3 right`
- `/save monitors`

## Headless Verification

Normal GUI launch still uses the tray app:

```powershell
.\.venv\Scripts\python.exe -m chaseos
```

Run one command without opening the GUI:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/wallpaper status"
```

Short alias:

```powershell
.\.venv\Scripts\python.exe -m chaseos -c "/wallpaper status"
```

Run the built-in non-mutating wallpaper smoke:

```powershell
.\.venv\Scripts\python.exe -m chaseos --smoke wallpapers
```

Run commands from a script file:

```powershell
.\.venv\Scripts\python.exe -m chaseos --script .\wallpaper_smoke.txt
```

Script files use one command per line. Blank lines and lines starting with `#` are
ignored.

These headless commands are safe and non-mutating:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/wallpaper status"
.\.venv\Scripts\python.exe -m chaseos --command "/wallpaper diagnostics"
.\.venv\Scripts\python.exe -m chaseos --command "/verify wallpapers"
.\.venv\Scripts\python.exe -m chaseos --command "/apply wallpapers --dry-run"
.\.venv\Scripts\python.exe -m chaseos --smoke wallpapers
```

Desktop-changing commands are blocked in headless mode unless
`--allow-desktop-changes` is provided. The only real apply command is:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/apply wallpapers --confirm" --allow-desktop-changes
```

Rollback is also desktop-changing:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/reset wallpapers" --allow-desktop-changes
```

The unlock flag does not bypass Phase 9/10 validation.

## Daily Startup Ritual

Normal GUI launch:

```powershell
.\.venv\Scripts\python.exe -m chaseos
```

Start the daily ritual:

```text
/start
```

The ritual can generate the Display 1 public art, private Display 4/2/3 wallpapers,
and `wallpaper_manifest.json`. It then shows asset status, wallpaper preflight, and an
apply dry-run. It does not apply desktop wallpapers automatically.

Check today's daily state:

```text
/daily status
```

Resume today's ritual:

```text
/resume
```

Headless daily status:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/daily status"
```

Run the non-mutating startup smoke:

```powershell
.\.venv\Scripts\python.exe -m chaseos --smoke startup
```

Daily session state is saved under:

```text
%LOCALAPPDATA%\ChaseOS\sessions\YYYY-MM-DD\daily_session.json
```

Startup smoke reports are saved under:

```text
%LOCALAPPDATA%\ChaseOS\sessions\YYYY-MM-DD\last_startup_smoke.txt
%LOCALAPPDATA%\ChaseOS\sessions\YYYY-MM-DD\last_startup_smoke.json
```

After assets and preflight are ready, the explicit apply command remains:

```text
/apply wallpapers --confirm
```

Headless real apply still requires the unlock flag:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/apply wallpapers --confirm" --allow-desktop-changes
```

Daily ritual safety notes:

- Display 1 art is seeded only by the public-safe innovation takeaway.
- Raw check-in text is not persisted by default.
- Display 1 never uses Lightroom/general photos or readable text.
- `/start`, `/prepare wallpapers`, `/verify wallpapers`, smoke modes, and dry-run do not
  apply wallpapers.
- `/approve` advances the ritual and may generate assets, but it does not apply
  wallpapers.

## Operator Help And Support Export

Phase 15 adds grouped operator help, a redacted daily summary, and a redacted support
export bundle.

Help commands:

```text
/help
/help startup
/help wallpapers
/help monitors
/help photos
/help headless
/help safety
```

Daily summary:

```text
/daily summary
```

Support export:

```text
/export support --dry-run
/export support --redacted
```

Headless examples:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/help wallpapers"
.\.venv\Scripts\python.exe -m chaseos --command "/daily summary"
.\.venv\Scripts\python.exe -m chaseos --command "/export support --dry-run"
.\.venv\Scripts\python.exe -m chaseos --command "/export support --redacted"
```

The daily summary is written to:

```text
%LOCALAPPDATA%\ChaseOS\sessions\YYYY-MM-DD\daily_summary.txt
```

Support exports are written under:

```text
%LOCALAPPDATA%\ChaseOS\exports\
```

Phase 15 safety notes:

- Support export is redacted-only.
- Plain `/export support` defaults to dry-run.
- Generated images and private Lightroom photos are not included by default.
- Raw check-in text is not persisted by default.
- Help, summary, status, doctor, diagnostics, smoke, export, verify, and dry-run commands
  do not change desktop wallpapers.

## Windows Operation And Release Readiness

Normal GUI launch:

```powershell
.\.venv\Scripts\python.exe -m chaseos
```

ChaseOS uses a per-user runtime lock so a second normal GUI launch does not create a
second tray instance. Headless commands, scripts, and smoke modes still run normally.

Startup shortcut status:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/startup status"
```

Enable per-user startup:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/startup enable"
```

Disable per-user startup:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/startup disable"
```

Create a branded Start Menu shortcut for manual taskbar pinning:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/install shortcut"
```

Remove that Start Menu shortcut:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/uninstall shortcut"
```

Windows has no supported public API for taskbar pinning. After installing the shortcut,
open Start, right-click ChaseOS, and choose **Pin to taskbar** once. This does not enable
auto-startup; `/startup enable` remains separate and explicit.

Release info:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/release info"
```

Release smoke:

```powershell
.\.venv\Scripts\python.exe -m chaseos --smoke release
```

Startup management uses only the current user's Startup folder shortcut:

```text
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ChaseOS.lnk
```

Phase 16 safety notes:

- No registry Run keys.
- No scheduled tasks.
- No admin rights.
- Release smoke is non-mutating.
- Tray menu does not include apply/reset wallpaper actions.

## First-Run Readiness

Refresh dependencies, including the Windows-only wallpaper API support:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

Run the doctor:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/doctor"
```

Check asset status:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/assets status"
```

Create an innovation takeaway file:

```powershell
Set-Content -Path .\innovation_takeaway.txt -Value "A small visible improvement beats a hidden perfect plan."
```

Prepare daily Display 1 art and wallpaper assets without applying them:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/prepare wallpapers --takeaway-file .\innovation_takeaway.txt"
```

Run non-mutating smoke:

```powershell
.\.venv\Scripts\python.exe -m chaseos --smoke wallpapers
```

Only after smoke passes and the mapping looks correct, the user may manually run:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/apply wallpapers --confirm" --allow-desktop-changes
```

Rollback:

```powershell
.\.venv\Scripts\python.exe -m chaseos --command "/reset wallpapers" --allow-desktop-changes
```

Phase 12 safety notes:

- `/prepare wallpapers` generates files only.
- `/prepare wallpapers` does not apply desktop wallpapers.
- `--smoke wallpapers` does not apply desktop wallpapers.
- `/apply wallpapers --confirm` is the only wallpaper apply command.
- Display 1 never uses general local photos or readable text.

## Current Limitations

- No OpenAI yet.
- Monitor labels may vary depending on Windows, GPU, and dock behavior.
- Fallback layout is used if detection fails.
- Per-monitor wallpaper application requires Windows IDesktopWallpaper support.
- Rollback skips previous wallpaper paths that no longer exist.

## Privacy and Safety Boundaries

- Do not implement formal ADHD, depression, or anxiety questionnaires.
- Do not diagnose the user.
- Do not use clinical labels.
- Interpret check-ins only into practical work-start signals:
  `energy`, `clarity`, `pressure`, `mood_weight`, `focus_friction`, `body_context`,
  `social_battery`, and `readiness`.
- Display 1 public art must never include private check-in details or readable text.
- Display 1 public art must be seeded only from the public-safe innovation takeaway.
- Public seed text must redact ticket numbers, hostnames, URLs, emails, IPs, usernames,
  company names, internal systems, credentials, and private health details.
- Do not require admin rights.
- Do not apply wallpapers without `/apply wallpapers --confirm`.
- Do not call OpenAI, edit registry settings, restart Explorer, or programmatically pin to the taskbar.

## Monitor Layout

- Display 1: public portrait monitor, 1080x1920 generated art.
- Display 4: private landscape left atmosphere wallpaper.
- Display 2: private landscape center command wallpaper.
- Display 3: private landscape right inspiration wallpaper.

Local photo source:

```text
C:\_Media\Photos\Lightroom\Export
```

General local photos and readable text must not be used on Display 1.
