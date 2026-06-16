from chaseos.app.command_router import KNOWN_COMMANDS, CommandRouter, route_command


def test_phase_two_commands_are_reserved() -> None:
    assert "/help" in KNOWN_COMMANDS
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
    assert "/photos" in KNOWN_COMMANDS
    assert "/index" in KNOWN_COMMANDS
    assert "/photo" in KNOWN_COMMANDS


def test_help_is_recognized() -> None:
    result = route_command("/help")

    assert result.recognized is True
    assert result.command == "/help"
    assert result.action == "respond"
    assert any("/start" in line.text for line in result.lines)


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
