from chaseos.app.command_router import KNOWN_COMMANDS, CommandRouter, route_command


def test_phase_two_commands_are_reserved() -> None:
    assert "/help" in KNOWN_COMMANDS
    assert "/version" in KNOWN_COMMANDS
    assert "/doctor" in KNOWN_COMMANDS
    assert "/start" in KNOWN_COMMANDS
    assert "/clear" in KNOWN_COMMANDS
    assert "/exit" in KNOWN_COMMANDS
    assert "/approve" in KNOWN_COMMANDS
    assert "/change" in KNOWN_COMMANDS
    assert "/regenerate" in KNOWN_COMMANDS
    assert "/monitors" in KNOWN_COMMANDS
    assert "/monitor" in KNOWN_COMMANDS
    assert "/detect" in KNOWN_COMMANDS
    assert "/assign" in KNOWN_COMMANDS
    assert "/auto" in KNOWN_COMMANDS
    assert "/save" in KNOWN_COMMANDS
    assert "/wallpapers" in KNOWN_COMMANDS
    assert "/generate" in KNOWN_COMMANDS
    assert "/apply" in KNOWN_COMMANDS
    assert "/wallpaper" in KNOWN_COMMANDS
    assert "/verify" in KNOWN_COMMANDS
    assert "/assets" in KNOWN_COMMANDS
    assert "/prepare" in KNOWN_COMMANDS
    assert "/daily" in KNOWN_COMMANDS
    assert "/export" in KNOWN_COMMANDS
    assert "/startup" in KNOWN_COMMANDS
    assert "/install" in KNOWN_COMMANDS
    assert "/uninstall" in KNOWN_COMMANDS
    assert "/release" in KNOWN_COMMANDS
    assert "/photos" in KNOWN_COMMANDS
    assert "/index" in KNOWN_COMMANDS
    assert "/photo" in KNOWN_COMMANDS
    assert "/takeaway" in KNOWN_COMMANDS


def test_help_is_recognized() -> None:
    result = route_command("/help")

    assert result.recognized is True
    assert result.command == "/help"
    assert result.action == "respond"
    assert any("/start" in line.text for line in result.lines)


def test_help_includes_major_command_groups() -> None:
    text = "\n".join(line.text for line in route_command("/help").lines)

    assert "Startup ritual" in text
    assert "Wallpaper verification and apply" in text
    assert "Monitor mapping" in text
    assert "Headless usage" in text


def test_help_wallpapers_mentions_dry_run_and_explicit_confirm() -> None:
    text = "\n".join(line.text for line in route_command("/help wallpapers").lines)

    assert "/apply wallpapers --dry-run" in text
    assert "/apply wallpapers --confirm" in text
    assert "explicit live apply command" in text


def test_help_safety_mentions_public_and_raw_check_in_privacy() -> None:
    text = "\n".join(line.text for line in route_command("/help safety").lines)

    assert "Raw check-in text is not persisted by default." in text
    assert "Display 1 generated art has no readable text and no general local photos." in text


def test_version_is_recognized() -> None:
    result = route_command("/version")

    assert result.recognized is True
    assert result.command == "/version"


def test_doctor_is_recognized() -> None:
    result = route_command("/doctor")

    assert result.recognized is True
    assert result.command == "/doctor"


def test_start_is_recognized() -> None:
    result = route_command("/start")

    assert result.recognized is True
    assert result.command == "/start"
    assert result.action == "respond"
    assert result.lines[0].text == "start sequence command recognized."


def test_change_captures_single_word_request() -> None:
    result = route_command("/change calmer")

    assert result.recognized is True
    assert result.command == "/change"
    assert result.change_request == "calmer"
    assert result.lines[0].text == "change request captured: calmer"


def test_change_captures_multi_word_request() -> None:
    result = route_command("/change more cyberpunk")

    assert result.recognized is True
    assert result.command == "/change"
    assert result.change_request == "more cyberpunk"


def test_unknown_command_returns_friendly_result() -> None:
    result = route_command("/bogus")

    assert result.recognized is False
    assert result.action == "respond"
    assert result.lines[0].text == "unknown command. type /help unless you enjoy guessing."


def test_empty_input_is_noop() -> None:
    result = CommandRouter().route("   ")

    assert result.recognized is True
    assert result.action == "noop"
    assert result.lines == ()


def test_normal_text_is_text_input() -> None:
    result = route_command("done")

    assert result.recognized is True
    assert result.action == "text"
    assert result.argument == "done"


def test_monitors_command_is_recognized() -> None:
    result = route_command("/monitors")

    assert result.recognized is True
    assert result.command == "/monitors"


def test_clear_is_recognized() -> None:
    result = route_command("/clear")

    assert result.recognized is True
    assert result.command == "/clear"
    assert result.action == "clear"


def test_exit_is_recognized() -> None:
    result = route_command("/exit")

    assert result.recognized is True
    assert result.command == "/exit"
    assert result.action == "exit"


def test_wallpapers_command_is_recognized() -> None:
    result = route_command("/wallpapers")

    assert result.recognized is True
    assert result.command == "/wallpapers"


def test_generate_wallpapers_command_is_recognized() -> None:
    result = route_command("/generate wallpapers")

    assert result.recognized is True
    assert result.command == "/generate wallpapers"


def test_apply_wallpapers_defaults_to_dry_run_command() -> None:
    result = route_command("/apply wallpapers")

    assert result.recognized is True
    assert result.command == "/apply wallpapers"
    assert result.argument == ""


def test_apply_wallpapers_dry_run_command_is_recognized() -> None:
    result = route_command("/apply wallpapers --dry-run")

    assert result.recognized is True
    assert result.command == "/apply wallpapers"
    assert result.argument == "--dry-run"


def test_apply_wallpapers_confirm_command_is_recognized() -> None:
    result = route_command("/apply wallpapers --confirm")

    assert result.recognized is True
    assert result.command == "/apply wallpapers"
    assert result.argument == "--confirm"


def test_detect_monitors_command_is_recognized() -> None:
    result = route_command("/detect monitors")

    assert result.recognized is True
    assert result.command == "/detect monitors"


def test_monitor_roles_command_is_recognized() -> None:
    result = route_command("/monitor roles")

    assert result.recognized is True
    assert result.command == "/monitor roles"


def test_assign_monitor_command_is_recognized() -> None:
    result = route_command("/assign display 1 public")

    assert result.recognized is True
    assert result.command == "/assign"
    assert result.argument == "display 1 public"


def test_auto_assign_monitors_command_is_recognized() -> None:
    result = route_command("/auto assign monitors")

    assert result.recognized is True
    assert result.command == "/auto assign monitors"


def test_save_and_reset_monitors_commands_are_recognized() -> None:
    save = route_command("/save monitors")
    reset = route_command("/reset monitors")

    assert save.recognized is True
    assert save.command == "/save monitors"
    assert reset.recognized is True
    assert reset.command == "/reset monitors"


def test_reset_wallpapers_command_is_recognized() -> None:
    result = route_command("/reset wallpapers")

    assert result.recognized is True
    assert result.command == "/reset wallpapers"


def test_wallpaper_status_and_diagnostics_commands_are_recognized() -> None:
    status = route_command("/wallpaper status")
    diagnostics = route_command("/wallpaper diagnostics")

    assert status.recognized is True
    assert status.command == "/wallpaper status"
    assert diagnostics.recognized is True
    assert diagnostics.command == "/wallpaper diagnostics"


def test_verify_wallpapers_command_is_recognized() -> None:
    result = route_command("/verify wallpapers")

    assert result.recognized is True
    assert result.command == "/verify wallpapers"


def test_assets_status_command_is_recognized() -> None:
    result = route_command("/assets status")

    assert result.recognized is True
    assert result.command == "/assets status"


def test_daily_status_and_summary_commands_are_recognized() -> None:
    status = route_command("/daily status")
    summary = route_command("/daily summary")

    assert status.recognized is True
    assert status.command == "/daily status"
    assert summary.recognized is True
    assert summary.command == "/daily summary"


def test_export_support_commands_are_recognized() -> None:
    dry_run = route_command("/export support --dry-run")
    redacted = route_command("/export support --redacted")

    assert dry_run.recognized is True
    assert dry_run.command == "/export support"
    assert dry_run.argument == "--dry-run"
    assert redacted.recognized is True
    assert redacted.command == "/export support"
    assert redacted.argument == "--redacted"


def test_startup_commands_are_recognized() -> None:
    status = route_command("/startup status")
    enable = route_command("/startup enable")
    disable = route_command("/startup disable")

    assert status.command == "/startup status"
    assert enable.command == "/startup enable"
    assert disable.command == "/startup disable"


def test_shortcut_install_commands_are_recognized() -> None:
    install = route_command("/install shortcut")
    uninstall = route_command("/uninstall shortcut")

    assert install.command == "/install shortcut"
    assert uninstall.command == "/uninstall shortcut"


def test_release_info_command_is_recognized() -> None:
    result = route_command("/release info")

    assert result.recognized is True
    assert result.command == "/release info"


def test_prepare_wallpapers_command_is_recognized() -> None:
    result = route_command("/prepare wallpapers --takeaway useful insight")

    assert result.recognized is True
    assert result.command == "/prepare wallpapers"
    assert result.argument == "--takeaway useful insight"


def test_takeaway_command_captures_text() -> None:
    result = route_command("/takeaway useful insight")

    assert result.recognized is True
    assert result.command == "/takeaway"
    assert result.argument == "useful insight"


def test_photo_status_command_is_recognized() -> None:
    result = route_command("/photos")

    assert result.recognized is True
    assert result.command == "/photos"


def test_index_photos_command_is_recognized() -> None:
    result = route_command("/index photos")

    assert result.recognized is True
    assert result.command == "/index photos"


def test_photo_source_command_is_recognized() -> None:
    result = route_command("/photo source")

    assert result.recognized is True
    assert result.command == "/photo source"
