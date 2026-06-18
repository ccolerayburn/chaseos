"""Public-domain Bible verse catalog for the startup ritual."""

from __future__ import annotations

from pydantic import BaseModel

KNOWN_TONE_TAGS = frozenset(
    {
        "wisdom",
        "peace",
        "courage",
        "perseverance",
        "diligence",
        "humility",
        "gratitude",
        "hope",
        "rest",
    }
)
PUBLIC_DOMAIN_TRANSLATIONS = frozenset({"KJV", "ASV", "WEB"})


class Verse(BaseModel):
    ref: str
    text: str
    translation: str
    tone_tags: tuple[str, ...]


VERSE_CATALOG: tuple[Verse, ...] = (
    Verse(
        ref="Proverbs 16:3",
        text="Commit thy works unto the LORD, and thy thoughts shall be established.",
        translation="KJV",
        tone_tags=("diligence", "wisdom"),
    ),
    Verse(
        ref="Isaiah 26:3",
        text="Thou wilt keep him in perfect peace, whose mind is stayed on thee.",
        translation="KJV",
        tone_tags=("peace", "rest"),
    ),
    Verse(
        ref="Joshua 1:9",
        text="Be strong and of a good courage; be not afraid, neither be thou dismayed.",
        translation="KJV",
        tone_tags=("courage", "hope"),
    ),
    Verse(
        ref="Psalm 37:5",
        text="Commit thy way unto the LORD; trust also in him; and he shall bring it to pass.",
        translation="KJV",
        tone_tags=("hope", "diligence"),
    ),
    Verse(
        ref="Psalm 46:10",
        text="Be still, and know that I am God.",
        translation="KJV",
        tone_tags=("peace", "rest"),
    ),
    Verse(
        ref="Proverbs 3:5",
        text="Trust in the LORD with all thine heart; and lean not unto thine own understanding.",
        translation="KJV",
        tone_tags=("wisdom", "humility"),
    ),
    Verse(
        ref="Proverbs 3:6",
        text="In all thy ways acknowledge him, and he shall direct thy paths.",
        translation="KJV",
        tone_tags=("wisdom", "hope"),
    ),
    Verse(
        ref="Psalm 90:17",
        text=(
            "Establish thou the work of our hands upon us; "
            "yea, the work of our hands establish thou it."
        ),
        translation="KJV",
        tone_tags=("diligence", "hope"),
    ),
    Verse(
        ref="Colossians 3:23",
        text="And whatsoever ye do, do it heartily, as to the Lord, and not unto men.",
        translation="KJV",
        tone_tags=("diligence", "humility"),
    ),
    Verse(
        ref="James 1:5",
        text="If any of you lack wisdom, let him ask of God, that giveth to all men liberally.",
        translation="KJV",
        tone_tags=("wisdom", "humility"),
    ),
    Verse(
        ref="Galatians 6:9",
        text=(
            "And let us not be weary in well doing: "
            "for in due season we shall reap, if we faint not."
        ),
        translation="KJV",
        tone_tags=("perseverance", "hope"),
    ),
    Verse(
        ref="Romans 12:11",
        text="Not slothful in business; fervent in spirit; serving the Lord.",
        translation="KJV",
        tone_tags=("diligence", "courage"),
    ),
    Verse(
        ref="Philippians 4:6",
        text=(
            "Be careful for nothing; but in every thing by prayer and supplication "
            "with thanksgiving let your requests be made known unto God."
        ),
        translation="KJV",
        tone_tags=("peace", "gratitude"),
    ),
    Verse(
        ref="Philippians 4:7",
        text=(
            "And the peace of God, which passeth all understanding, "
            "shall keep your hearts and minds through Christ Jesus."
        ),
        translation="KJV",
        tone_tags=("peace", "rest"),
    ),
    Verse(
        ref="Psalm 118:24",
        text="This is the day which the LORD hath made; we will rejoice and be glad in it.",
        translation="KJV",
        tone_tags=("gratitude", "hope"),
    ),
    Verse(
        ref="1 Thessalonians 5:18",
        text=(
            "In every thing give thanks: "
            "for this is the will of God in Christ Jesus concerning you."
        ),
        translation="KJV",
        tone_tags=("gratitude", "humility"),
    ),
    Verse(
        ref="Matthew 6:34",
        text=(
            "Take therefore no thought for the morrow: "
            "for the morrow shall take thought for the things of itself."
        ),
        translation="KJV",
        tone_tags=("peace", "wisdom"),
    ),
    Verse(
        ref="Psalm 27:14",
        text="Wait on the LORD: be of good courage, and he shall strengthen thine heart.",
        translation="KJV",
        tone_tags=("courage", "perseverance", "hope"),
    ),
    Verse(
        ref="Isaiah 40:31",
        text=(
            "They that wait upon the LORD shall renew their strength; "
            "they shall mount up with wings as eagles."
        ),
        translation="KJV",
        tone_tags=("hope", "perseverance"),
    ),
    Verse(
        ref="Psalm 55:22",
        text="Cast thy burden upon the LORD, and he shall sustain thee.",
        translation="KJV",
        tone_tags=("peace", "rest", "hope"),
    ),
    Verse(
        ref="Proverbs 4:23",
        text="Keep thy heart with all diligence; for out of it are the issues of life.",
        translation="KJV",
        tone_tags=("wisdom", "diligence"),
    ),
    Verse(
        ref="Proverbs 14:23",
        text="In all labour there is profit: but the talk of the lips tendeth only to penury.",
        translation="KJV",
        tone_tags=("diligence", "wisdom"),
    ),
    Verse(
        ref="Ecclesiastes 9:10",
        text="Whatsoever thy hand findeth to do, do it with thy might.",
        translation="KJV",
        tone_tags=("diligence", "courage"),
    ),
    Verse(
        ref="Micah 6:8",
        text=(
            "What doth the LORD require of thee, but to do justly, "
            "and to love mercy, and to walk humbly with thy God?"
        ),
        translation="KJV",
        tone_tags=("humility", "wisdom"),
    ),
    Verse(
        ref="Psalm 23:1",
        text="The LORD is my shepherd; I shall not want.",
        translation="KJV",
        tone_tags=("peace", "rest"),
    ),
    Verse(
        ref="Psalm 23:3",
        text=(
            "He restoreth my soul: "
            "he leadeth me in the paths of righteousness for his name's sake."
        ),
        translation="KJV",
        tone_tags=("rest", "hope"),
    ),
    Verse(
        ref="Psalm 31:24",
        text=(
            "Be of good courage, and he shall strengthen your heart, "
            "all ye that hope in the LORD."
        ),
        translation="KJV",
        tone_tags=("courage", "hope"),
    ),
    Verse(
        ref="Psalm 34:4",
        text="I sought the LORD, and he heard me, and delivered me from all my fears.",
        translation="KJV",
        tone_tags=("peace", "courage"),
    ),
    Verse(
        ref="Psalm 34:8",
        text="O taste and see that the LORD is good: blessed is the man that trusteth in him.",
        translation="KJV",
        tone_tags=("gratitude", "hope"),
    ),
    Verse(
        ref="Psalm 62:1",
        text="Truly my soul waiteth upon God: from him cometh my salvation.",
        translation="KJV",
        tone_tags=("rest", "peace"),
    ),
    Verse(
        ref="Psalm 121:1",
        text="I will lift up mine eyes unto the hills, from whence cometh my help.",
        translation="KJV",
        tone_tags=("hope", "courage"),
    ),
    Verse(
        ref="Psalm 127:1",
        text="Except the LORD build the house, they labour in vain that build it.",
        translation="KJV",
        tone_tags=("humility", "diligence"),
    ),
    Verse(
        ref="Proverbs 11:2",
        text="When pride cometh, then cometh shame: but with the lowly is wisdom.",
        translation="KJV",
        tone_tags=("humility", "wisdom"),
    ),
    Verse(
        ref="Proverbs 15:22",
        text=(
            "Without counsel purposes are disappointed: "
            "but in the multitude of counsellors they are established."
        ),
        translation="KJV",
        tone_tags=("wisdom", "humility"),
    ),
    Verse(
        ref="Proverbs 18:10",
        text="The name of the LORD is a strong tower: the righteous runneth into it, and is safe.",
        translation="KJV",
        tone_tags=("courage", "peace"),
    ),
    Verse(
        ref="Isaiah 41:10",
        text="Fear thou not; for I am with thee: be not dismayed; for I am thy God.",
        translation="KJV",
        tone_tags=("courage", "hope"),
    ),
    Verse(
        ref="Matthew 11:28",
        text="Come unto me, all ye that labour and are heavy laden, and I will give you rest.",
        translation="KJV",
        tone_tags=("rest", "peace"),
    ),
    Verse(
        ref="Romans 5:3",
        text="Tribulation worketh patience.",
        translation="KJV",
        tone_tags=("perseverance", "hope"),
    ),
    Verse(
        ref="Romans 8:28",
        text="All things work together for good to them that love God.",
        translation="KJV",
        tone_tags=("hope", "perseverance"),
    ),
    Verse(
        ref="1 Corinthians 15:58",
        text="Be ye stedfast, unmoveable, always abounding in the work of the Lord.",
        translation="KJV",
        tone_tags=("perseverance", "diligence"),
    ),
    Verse(
        ref="2 Corinthians 12:9",
        text="My grace is sufficient for thee: for my strength is made perfect in weakness.",
        translation="KJV",
        tone_tags=("humility", "hope"),
    ),
    Verse(
        ref="Ephesians 4:2",
        text="With all lowliness and meekness, with longsuffering, forbearing one another in love.",
        translation="KJV",
        tone_tags=("humility", "perseverance"),
    ),
    Verse(
        ref="Philippians 3:14",
        text="I press toward the mark for the prize of the high calling of God in Christ Jesus.",
        translation="KJV",
        tone_tags=("perseverance", "courage"),
    ),
    Verse(
        ref="Hebrews 12:1",
        text="Let us run with patience the race that is set before us.",
        translation="KJV",
        tone_tags=("perseverance", "diligence"),
    ),
    Verse(
        ref="James 4:10",
        text="Humble yourselves in the sight of the Lord, and he shall lift you up.",
        translation="KJV",
        tone_tags=("humility", "hope"),
    ),
)
