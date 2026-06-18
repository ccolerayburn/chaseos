"""Innovation improv scenario selection and local fallback responses."""

from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path

from chaseos.storage.paths import get_chaseos_data_dir

RECENT_SCENARIO_LIMIT = 30

SCENARIO_BANK: tuple[str, ...] = (
    (
        'A coworker calls the tool you built "too complicated." '
        "You get 60 seconds and you cannot defend it - what do you cut first?"
    ),
    (
        "The thing that broke this morning will break again next week. "
        "You can only fix the cause or the symptom today, not both. Pick, and say why."
    ),
    "You have to explain today's hardest task to a brand-new hire in one sentence. Go.",
    "A process everyone tolerates is quietly costing an hour a day. Name it and kill it.",
    (
        "You can automate exactly one thing you did yesterday. "
        "Which, and what do you do with the freed hour?"
    ),
    "The Sunday stream has to run with one fewer person next week. What changes?",
    (
        "Someone asks for a feature that's really a workaround for a missing one. "
        "What's the missing one?"
    ),
    "You can delete one recurring meeting forever. Which, and what replaces it?",
    (
        "A dashboard nobody reads still gets built every month. "
        "What would make someone actually open it?"
    ),
    "You're handed a problem with no clear owner. What's your first move to make it real?",
    "The fastest fix and the right fix disagree today. Argue for the one you'd skip.",
    "Give yesterday's annoyance a name, a villain origin story, and a weakness.",
    "XRay is useful but nobody trusts the output yet. What proof would make it boringly credible?",
    (
        "A ticket arrives with half the needed facts missing. "
        "What one question would prevent the next three replies?"
    ),
    "A user describes a symptom, not the problem. Translate it into one testable hypothesis.",
    "The best fix is invisible when it works. How do you make its value visible?",
    (
        "A process has seven steps because nobody wanted to choose. "
        "Which step is secretly doing the work?"
    ),
    "A church AV handoff has to survive a new volunteer. What gets written down first?",
    (
        "The Sunday stream fails five minutes before service. "
        "What tiny checklist would have caught it?"
    ),
    "You inherit a script nobody wants to touch. What one guardrail makes it less scary?",
    "A teammate says, 'That's just how we do it.' What do you ask next?",
    "Your future self opens this project in 30 days. What breadcrumb saves them ten minutes?",
    "A noisy alert fires every day but rarely matters. What would make it earn its sound?",
    "A report is technically correct and practically useless. What does it need to answer?",
    "A task feels huge because the first step is fake. Rename the first real step.",
    "A workflow needs courage, not more polish. Where do you ship the rough version?",
    "A customer gives vague feedback. Turn it into one observable behavior.",
    "A queue is full of repeats. What pattern is trying to introduce itself?",
    "A tool asks for too much information up front. What can it infer instead?",
    "A handoff keeps failing because the owner is implied. What sentence makes ownership explicit?",
    "A small bug is teaching you about a larger design flaw. What is the lesson?",
    "A process is slow because it waits for permission. What decision can be pre-approved?",
    "You can remove one field from a form today. Which one stops pretending to matter?",
    "A thing works on your machine and nowhere else. What assumption did your machine hide?",
    "A volunteer has ten minutes to learn the setup. What must be obvious without asking?",
    "You have one hour to make tomorrow calmer. What do you prepare now?",
)

LOCAL_TWISTS: tuple[str, ...] = (
    "Yes, and now make it survive a tired future version of you.",
    "Yes, and add one constraint: it has to be explainable in one sentence.",
    "Yes, and imagine someone else has to run it without context tomorrow.",
    "Yes, and shrink it until the first move takes under five minutes.",
    "Yes, and make the win visible enough that nobody has to ask whether it helped.",
    "Yes, and remove one step before you add anything new.",
)


class RecentScenarioStore:
    def __init__(self, base_path: Path | str | None = None) -> None:
        self.base_path = Path(base_path) if base_path is not None else None

    @property
    def path(self) -> Path:
        return get_chaseos_data_dir(self.base_path) / "improv" / "recent_scenarios.json"

    def load(self) -> tuple[str, ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ()
        return tuple(str(item) for item in payload.get("recent", ()) if str(item).strip())

    def record(self, scenario: str) -> None:
        recent = [scenario, *self.load()]
        deduped = list(dict.fromkeys(recent))[:RECENT_SCENARIO_LIMIT]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"recent": deduped}, indent=2), encoding="utf-8")


def select_scenario(
    run_date: date,
    recent_scenarios: tuple[str, ...] | list[str] = (),
) -> str:
    pool = [scenario for scenario in SCENARIO_BANK if scenario not in recent_scenarios]
    if not pool:
        pool = list(SCENARIO_BANK)
    rng = random.Random(run_date.isoformat())
    return pool[rng.randrange(len(pool))]


def local_yes_and(turn_count: int) -> str:
    return LOCAL_TWISTS[turn_count % len(LOCAL_TWISTS)]
