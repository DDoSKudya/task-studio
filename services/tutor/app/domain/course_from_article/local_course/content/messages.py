from __future__ import annotations

from app.domain.course_from_article.common.runtime.course_context import (
    get_course_profile,
    get_strategy_pack,
)
from app.domain.course_from_article.curriculum.outline.course_locale import locale_line
from app.domain.course_from_article.curriculum.outline.course_profile import (
    practice_needs_code_starter,
)
from app.domain.course_from_article.local_course.curriculum.inventory import TopicSeed
from app.domain.course_from_article.local_course.policy.schemas import (
    ORDER_SCHEMA,
    PRACTICE_ITEM_SCHEMA,
    QUIZ_BATCH_SCHEMA,
    QUIZ_ITEM_SCHEMA,
    schema_prompt_hint,
)
from app.domain.prompt_compose import (
    compose_prompt,
    course_from_article_system_prompt,
    course_from_article_theory_prose_prompt,
)


def _composed_stage(stage: str) -> str:
    return course_from_article_system_prompt(
        stage=stage,
        compact=False,
        course_profile=get_course_profile(),
        local_runtime=True,
        strategy_pack=get_strategy_pack(),
    )


def order_system_prompt() -> str:
    return compose_prompt(
        _composed_stage("analyze"),
        "You order course topics as a book: simplest complete whole-task first "
        "(epitome), then chapters that add one condition each; traps last. "
        "Title words like intro are hints, not the order. "
        "Keep denser source excerpts earlier only when they are prerequisites; "
        "do not bury a long foundation topic at the end. "
        "Never place 'Введение' / Introduction after advanced topics. "
        "Chapters named Итоги / Заключение / Summary belong only at the end. "
        "If several articles are mixed, build ONE rising arc — do not restart "
        "the course with a second 'what is X' after deep chapters. "
        "Use only the given ids. Do not drop ids. Do not invent ids. "
        + schema_prompt_hint(ORDER_SCHEMA),
    )


def order_user_message(seeds: list[TopicSeed], *, locale: str) -> str:
    lines = []
    for index, seed in enumerate(seeds):
        claim = " ".join(seed.excerpt.split())[:220]
        lines.append(
            f"{index}: {seed.title} | source={seed.source_title} | "
            f"objective={seed.objective[:140]} | claim={claim}"
        )
    return (
        f"{locale_line(locale)}\n"
        "Return JSON order as the ids in teaching sequence "
        "(epitome → elaborations → traps → wrap-up).\n"
        "Compare claims across ALL topics before ordering. Put ids that teach the "
        "same idea in merge_groups; merge only semantic duplicates, not prerequisite "
        "and advanced views of one subject. Every merged id must still occur in order.\n"
        "Outcomes must be in the course locale.\n"
        "Longer excerpts are denser source, not automatically harder topics.\n"
        "Do not put wrap-up / summary chapters in the middle.\n"
        "Topics:\n" + "\n".join(lines)
    )


def quiz_system_prompt(locale: str = "ru", *, chunk: int = 1) -> str:
    schema = QUIZ_ITEM_SCHEMA if chunk == 1 else QUIZ_BATCH_SCHEMA
    return compose_prompt(
        _composed_stage("quizzes"),
        locale_line(locale),
        "Write MCQs for ONE chapter in the course locale. "
        "Follow active strategy briefs (claim-mcq): full-text choices only — "
        "never bare A/B/C/D or A) prefixes. "
        "Test a decision or contrast from this chapter's theory, not the title. "
        "Assign a different explicit theory claim to every requested question before writing JSON. "
        "Do not create several paraphrases of one claim. "
        "Vary the correct answer index. " + schema_prompt_hint(schema),
    )


def _quiz_json_example(chunk: int) -> str:
    one = (
        '{"question":"...","choices":["full text A","full text B",'
        '"full text C","full text D"],"answer":0}'
    )
    if chunk == 1:
        return f"Return one object: {one}"
    return f'Return {{"quizzes":[{one}]}}'


def quiz_user_message(
    *,
    locale: str,
    chunk: int,
    title: str,
    objective: str,
    theory: str,
    already: list[str],
    article_seeds: str = "",
    prior_digest: str = "",
    chapter_index: int = 0,
    chapter_total: int = 1,
) -> str:
    prior = "\n".join(f"- {question}" for question in already[-40:])
    seeds = (
        f"Article checks to adapt into the course locale:\n{article_seeds}\n"
        if article_seeds.strip()
        else ""
    )
    spaced = ""
    if prior_digest.strip():
        spaced = (
            "This is not the first chapter. The tested skill stays THIS chapter's "
            "objective, but at least one stem should need an earlier idea as context "
            "(not a recap of the earlier title).\n"
            f"Earlier chapter residue:\n{prior_digest[:800]}\n"
        )
    total = max(1, chapter_total)
    index = max(0, min(chapter_index, total - 1))
    if index <= 1:
        bloom = (
            "Bloom band: early chapter — prefer identify / distinguish / "
            "predict-from-example stems. Avoid abstract trade-off essays.\n"
        )
    elif index >= max(total - 2, 3):
        bloom = (
            "Bloom band: late chapter — prefer choose / justify / diagnose stems "
            "grounded in THIS chapter (still one correct choice).\n"
        )
    else:
        bloom = (
            "Bloom band: middle chapter — prefer apply / contrast / next-step stems "
            "for the chapter objective.\n"
        )
    return (
        f"{locale_line(locale)}\n"
        f"Need exactly {chunk} NEW quizzes.\n"
        f"Chapter: {title}\n"
        f"Objective: {objective}\n"
        f"{bloom}"
        f"Already written:\n{prior or '(none)'}\n"
        "Each new stem must test a theory claim not tested by any item above. "
        "Change both the claim and the cognitive operation; changing wording alone is not novel.\n"
        f"{spaced}"
        f"{seeds}"
        f"Chapter theory:\n{theory[:3500]}\n"
        f"{_quiz_json_example(chunk)}\n"
    )


def practice_io_contract(locale: str) -> str:
    ru = (locale or "ru").casefold().startswith("ru")
    if practice_needs_code_starter(get_course_profile()):
        if ru:
            return (
                "Это закрепление шага главы, не экзамен. "
                "В content — одно-два предложения: что дописать. "
                "В template — стартовый код с именем из главы, не solve(). "
                "Предпочти completion problem: возьми worked example из теории, "
                "удали 2–4 решающие строки, оставь TODO. "
                "Подписи «Дано:» не обязательны."
            )
        return (
            "This is a drill, not an exam. "
            "content: one or two sentences of what to finish. "
            "template: starter named for the chapter, not solve(). "
            "Prefer a completion problem: copy the worked example from theory, "
            "delete 2–4 decisive lines, leave TODO. "
            "Given/Expected labels are optional."
        )
    if ru:
        return (
            "Это закрепление шага, не код. "
            "В content — короткое задание (сравнить, переписать, ответить). "
            "template может быть пустым. Не выдумывай код или стек."
        )
    return (
        "This is a non-code drill. "
        "content is a short writing or case task. "
        "template may be empty. Do not invent a coding runtime."
    )


def practice_system_prompt(locale: str = "ru") -> str:
    stage = "code" if practice_needs_code_starter(get_course_profile()) else "tasks"
    pack = (get_strategy_pack() or "").strip()
    ladder_hint = (
        "Emit exactly ONE drill for this chapter claim (preserve pack: no multi-rung ladder). "
        if pack == "preserve-7b"
        else (
            "When several tasks are for one chapter, emit a ladder on the SAME skill "
            "(easy scaffold → less scaffold → short authentic); do not invent new tools. "
        )
    )
    return compose_prompt(
        _composed_stage(stage),
        locale_line(locale),
        "Write the brief in the course locale, even if the excerpt was not. "
        f"{practice_io_contract(locale)} "
        "The learner repeats a step from theory to feel sure — not to be tested. "
        f"{ladder_hint}"
        "Do not invent facts or tools the chapter did not teach. "
        "Prefer ONE flat JSON object with title, content, template "
        "(not a nested tasks array) when asked for a single drill. "
        "For code drills, template MUST be one plain string with newlines inside "
        '(example: "def foo():\\n    ..."), NEVER a JSON array of lines. '
        "For non-code drills, template may be empty. " + schema_prompt_hint(PRACTICE_ITEM_SCHEMA),
    )


def theory_system_prompt(locale: str = "ru") -> str:
    return compose_prompt(
        course_from_article_theory_prose_prompt(
            compact=False,
            course_profile=get_course_profile(),
            local_runtime=True,
            strategy_pack=get_strategy_pack(),
        ),
        locale_line(locale),
        "Teach ONE chapter fragment in the course locale (translate ideas if needed). "
        "Follow active strategy briefs (montage vs literary-expand) and the domain overlay. "
        "One idea; calm prose; no labeled pedagogy boxes; no quizzes/homework in theory. "
        "Cover concrete facts from the excerpt; do not invent missing facts or paste the "
        "excerpt unchanged. Code/math fences only when the excerpt itself has them.",
    )


def _spine_prompt_block(spine: dict[str, str] | None) -> str:
    if not spine:
        return ""
    lines = [
        f"Book throughline: {spine['throughline']}" if spine.get("throughline") else "",
        f"Voice: {spine['voice']}" if spine.get("voice") else "",
        f"Address the reader as {spine['address']}" if spine.get("address") else "",
        f"Glossary: {spine['glossary']}" if spine.get("glossary") else "",
        f"Metaphors: {spine['metaphors']}" if spine.get("metaphors") else "",
    ]
    packed = "\n".join(line for line in lines if line)
    return f"{packed}\n" if packed else ""


def theory_window_user_message(
    *,
    locale: str,
    title: str,
    objective: str,
    excerpt: str,
    window_index: int,
    window_count: int,
    prior_digest: str,
    book_spine: dict[str, str] | None = None,
    next_title: str = "",
) -> str:
    prior = prior_digest.strip()
    if window_index > 1:
        continuity = (
            "Continue THIS chapter. Do not write a new introduction or repeat the opening hook. "
            + (f"The previous fragment already taught:\n{prior}\n" if prior else "")
            + "Cover only the new excerpt facts. Same voice as the fragment above.\n"
        )
    elif prior:
        continuity = (
            "This is the opening of a new chapter in the same book. "
            "Start from something already known (given), then one new move. "
            f"Previous chapter ended on:\n{prior}\n"
            "Extend or contrast that — do not recap it and do not restart the course.\n"
        )
    else:
        continuity = (
            "This is chapter 1 of the book (epitome). Open with one miniature "
            "complete working story a beginner could finish after this chapter "
            "alone — then name the pieces. Forbidden: glossary-only open or "
            "'what you will learn'. Later fragments will continue that story.\n"
        )
    hinge = (
        f"Next chapter will be: {next_title}. End with one bridge sentence toward it.\n"
        if next_title and window_index >= window_count
        else ""
    )
    return (
        f"{locale_line(locale)}\n"
        f"{_spine_prompt_block(book_spine)}"
        f"Chapter: {title}\n"
        f"Objective: {objective}\n"
        f"Fragment {window_index}/{window_count}.\n"
        f"{continuity}"
        f"{hinge}"
        f"Excerpt:\n{excerpt[:3500]}\n"
        "The excerpt may be another language. Teach every fact in the course locale; "
        "do not paste source-language prose. "
        "Teach this excerpt fully in 1–3 concise paragraphs; add more only when "
        "the fragment contains distinct steps that cannot fit without losing facts. "
        "Every named fact, term, or step from the excerpt must appear in teaching "
        "prose (not only inside a fence). "
        "Finish every sentence; do not end a fragment mid-list or mid-metaphor. "
        "Do not summarize away detail. Do not copy the excerpt verbatim."
    )


def theory_patch_user_message(
    *,
    locale: str,
    title: str,
    excerpt: str,
    draft: str,
    must_fix: list[str],
) -> str:
    fixes = "\n".join(f"- {item}" for item in must_fix[:5])
    return (
        f"{locale_line(locale)}\n"
        f"Chapter: {title}\n"
        f"Apply these fixes, keep every named fact/step from the excerpt, markdown only:\n{fixes}\n"
        f"Excerpt:\n{excerpt[:2500]}\n"
        f"Draft:\n{draft[:4000]}\n"
    )


def quiz_patch_user_message(
    *,
    locale: str,
    theory: str,
    quiz: dict[str, object],
    must_fix: list[str],
) -> str:
    fixes = "\n".join(f"- {item}" for item in must_fix[:5])
    return (
        f"{locale_line(locale)}\n"
        f"Fixes:\n{fixes}\n"
        f"Current quiz JSON:\n{quiz}\n"
        f"Chapter theory:\n{theory[:2500]}\n"
        "Return one repaired object with full-text choices "
        '(never bare "A"/"B"/"C"/"D"), answer index 0-based.'
    )


def practice_patch_user_message(
    *,
    locale: str,
    theory: str,
    task: dict[str, object],
    must_fix: list[str],
) -> str:
    fixes = "\n".join(f"- {item}" for item in must_fix[:5])
    return (
        f"{locale_line(locale)}\n"
        f"Fixes:\n{fixes}\n"
        f"{practice_io_contract(locale)}\n"
        f"Current task JSON:\n{task}\n"
        f"Chapter theory:\n{theory[:2500]}\n"
        "Return one repaired task in the schema."
    )


def practice_user_message(
    *,
    locale: str,
    runtime: str,
    runtime_version: str,
    chunk: int,
    title: str,
    objective: str,
    theory: str,
    already: list[str],
    article_seeds: str = "",
) -> str:
    prior = "\n".join(f"- {item}" for item in already[:8])
    seeds = (
        f"Article labs to adapt into the course locale:\n{article_seeds}\n"
        if article_seeds.strip()
        else ""
    )
    runtime_line = ""
    if practice_needs_code_starter(get_course_profile()):
        runtime_line = f"Runtime: {runtime} {runtime_version}\n"
    ladder = ""
    if chunk > 1 or already:
        ladder = (
            "Ladder on THIS chapter skill only: next item(s) must be harder than "
            "already-written ones by fading scaffold — same tools/facts, not a new topic.\n"
        )
    return (
        f"{locale_line(locale)}\n"
        f"{runtime_line}"
        f"Need exactly {chunk} NEW task(s).\n"
        f"Chapter: {title}\n"
        f"Objective: {objective}\n"
        f"Already written:\n{prior or '(none)'}\n"
        f"{ladder}"
        f"{seeds}"
        f"{practice_io_contract(locale)}\n"
        f"Chapter theory:\n{theory[:3000]}\n"
    )
