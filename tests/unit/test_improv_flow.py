from chaseos.ai.improv_client import Message
from chaseos.ritual.stages import RitualStage
from chaseos.ritual.startup_sequence import StartupSequence


def render_response_text(response) -> str:
    return "\n".join(line.render() for line in response.lines)


def advance_to_innovation(sequence: StartupSequence) -> None:
    sequence.handle_input("/start")
    sequence.handle_input("clear calm focused rested and ready")
    sequence.handle_input("/approve")
    sequence.handle_input("done")
    sequence.handle_input("done")


class RecordingImprovClient:
    def __init__(self) -> None:
        self.messages: tuple[Message, ...] = ()

    def respond(self, messages: tuple[Message, ...] | list[Message]) -> str:
        self.messages = tuple(messages)
        return "Yes, and the pattern becomes visible before anyone repeats it."


def test_improv_uses_local_fallback_when_api_is_not_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("CHASEOS_IMPROV_API", raising=False)
    sequence = StartupSequence(data_dir=tmp_path)
    advance_to_innovation(sequence)

    response = sequence.handle_input("we keep asking the same first question")

    assert sequence.current_stage == RitualStage.INNOVATION
    assert "yes-and (local)" in render_response_text(response)


def test_injected_improv_client_receives_only_improv_context(tmp_path) -> None:
    client = RecordingImprovClient()
    sequence = StartupSequence(data_dir=tmp_path, improv_client=client)
    private_check_in = "clear calm focused rested with private startup note"
    sequence.handle_input("/start")
    sequence.handle_input(private_check_in)
    sequence.handle_input("/approve")
    sequence.handle_input("done")
    sequence.handle_input("done")

    response = sequence.handle_input("we keep asking the same first question")
    message_text = "\n".join(message.content for message in client.messages)

    assert "yes-and (api)" in render_response_text(response)
    assert private_check_in not in message_text
    assert "we keep asking the same first question" in message_text


def test_takeaway_command_exits_improv_loop(tmp_path) -> None:
    sequence = StartupSequence(data_dir=tmp_path)
    advance_to_innovation(sequence)

    response = sequence.handle_input("/takeaway make the first question visible")

    assert sequence.current_stage == RitualStage.POSTER_APPROVAL
    assert sequence.session.innovation_takeaway == "make the first question visible"
    assert "DISPLAY 1 ART PLAN" in render_response_text(response)


def test_empty_takeaway_stays_in_improv_loop(tmp_path) -> None:
    sequence = StartupSequence(data_dir=tmp_path)
    advance_to_innovation(sequence)

    response = sequence.handle_input("/takeaway")

    assert sequence.current_stage == RitualStage.INNOVATION
    assert "takeaway missing" in render_response_text(response)
