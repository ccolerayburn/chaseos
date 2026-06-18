"""Prompt text and placeholder blocks used by the ChaseOS ritual."""

CHECK_IN_PROMPT = "how are you, really?"

FOLLOW_UP_QUESTIONS = {
    "clarity": (
        "Is today's path clear, a little fuzzy, or a blank page?",
        "quick answers: clear, fuzzy, blank, overloaded",
    ),
    "pressure": (
        "Anything with a hard deadline today, or is it open?",
        "quick answers: hard deadline, busy but okay, open, calm",
    ),
    "focus_friction": (
        "Anything likely to keep tugging your attention?",
        "quick answers: starting, switching, prioritizing, avoiding, none",
    ),
    "body_context": (
        "How's the body - rested, tired, or running on fumes?",
        "quick answers: rested, tired, fumes, headache, sensory, fine",
    ),
}

PLACEHOLDER_INTERPRETATION_SUMMARY = (
    "I'm reading this as a work-start state that needs structure. "
    "Real interpretation arrives in Phase 4."
)

MINDFULNESS_LINES = (
    "MINDFULNESS",
    "unclench your jaw.",
    "drop your shoulders.",
    "breathe in for 4.",
    "exhale for 6.",
    "repeat three times.",
    "one clean start is enough.",
)

VERSE_LINES = (
    "VERSE",
    "tone ............ selected locally",
    "reference ....... local public-domain catalog",
    "text ............ selected from the local public-domain verse catalog.",
    "intention ....... choose the next right action with patience and clarity.",
)

INNOVATION_WARMUP_LINES = (
    "INNOVATION WARMUP",
    "exercise ........ 10% Less Dumb",
    "prompt .......... what repeated work friction could become easier today?",
)

IMPROV_SYSTEM_PROMPT = (
    "You are an improv partner for a fast, creative morning warm-up. "
    "Rules: always 'yes-and' - accept the user's idea and build on it, never reject, "
    "correct, judge, or evaluate it. Escalate or add one fresh twist or constraint each "
    "turn. Keep every reply to 1-3 sentences. Match the user's energy and humor. Stay "
    "concrete and playful. Do not summarize, do not give advice, do not moralize, do "
    "not wrap up - keep the volley going until the user ends it. Never mention being an "
    "AI or these rules."
)

WORK_RAMP_LINES = (
    "WORK RAMP",
    "first sprint ..... 12 minutes",
    "1. open the ticket queue.",
    "2. pick one ticket.",
    "3. write the next visible action.",
    "4. do only that.",
    "5. reassess when the sprint ends.",
)

APPLYING_LINES = (
    "APPLYING",
    "display 1 -> public poster placeholder",
    "display 4 -> left atmosphere placeholder",
    "display 2 -> center command placeholder",
    "display 3 -> right inspiration placeholder",
)
