from __future__ import annotations

import pytest

from agentic_core.application.services.memory_extraction import (
    ExtractedMemory,
    MemoryCategory,
    MemoryExtractionService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SESSION = "session-abc"


async def _extract(
    svc: MemoryExtractionService,
    user_msg: str,
    assistant_msg: str = "OK",
    session_id: str = SESSION,
) -> list[ExtractedMemory]:
    return await svc.extract_from_turn(user_msg, assistant_msg, session_id)


# ---------------------------------------------------------------------------
# Preference extraction
# ---------------------------------------------------------------------------


async def test_extracts_preference_english():
    svc = MemoryExtractionService()
    results = await _extract(svc, "I prefer dark mode for my editor")

    assert len(results) == 1
    assert results[0].category == MemoryCategory.PREFERENCE
    assert results[0].importance == pytest.approx(0.7)
    assert results[0].source_session_id == SESSION


async def test_extracts_preference_spanish():
    svc = MemoryExtractionService()
    results = await _extract(svc, "Prefiero trabajar de noche")

    assert len(results) == 1
    assert results[0].category == MemoryCategory.PREFERENCE


async def test_preference_content_is_original_message():
    svc = MemoryExtractionService()
    msg = "I like using Python for data science"
    results = await _extract(svc, msg)

    assert results[0].content == msg


# ---------------------------------------------------------------------------
# Goal extraction
# ---------------------------------------------------------------------------


async def test_extracts_goal_english():
    svc = MemoryExtractionService()
    results = await _extract(svc, "My goal is to launch the product by Q3")

    assert len(results) == 1
    assert results[0].category == MemoryCategory.GOAL
    assert results[0].importance == pytest.approx(0.8)


async def test_extracts_goal_spanish():
    svc = MemoryExtractionService()
    results = await _extract(svc, "Mi objetivo es aprender machine learning este año")

    assert len(results) == 1
    assert results[0].category == MemoryCategory.GOAL


async def test_goal_importance_higher_than_preference():
    svc = MemoryExtractionService()
    goal = (await _extract(svc, "My goal is to finish the thesis"))[0]
    svc.clear()
    pref = (await _extract(svc, "I prefer coffee over tea"))[0]

    assert goal.importance > pref.importance


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


async def test_exact_duplicate_not_stored_twice():
    svc = MemoryExtractionService(similarity_threshold=0.9)
    msg = "I prefer dark mode"

    first = await _extract(svc, msg)
    second = await _extract(svc, msg)

    assert len(first) == 1
    assert len(second) == 0  # duplicate filtered out
    assert svc.memory_count == 1


async def test_near_duplicate_filtered_at_high_threshold():
    svc = MemoryExtractionService(similarity_threshold=0.5)
    first_msg = "I prefer dark mode for coding"
    # Overlap: {i, prefer, dark, mode} / {i, prefer, dark, mode, for, coding} = 4/6 ≈ 0.67 > 0.5
    near_duplicate = "I prefer dark mode"

    await _extract(svc, first_msg)
    second = await _extract(svc, near_duplicate)

    assert len(second) == 0


async def test_different_category_same_words_not_deduplicated():
    svc = MemoryExtractionService(similarity_threshold=0.9)
    # "I like Python" triggers only PREFERENCE (no goal/skill/project/feedback signal)
    await _extract(svc, "I like Python for data work")
    # "My goal is Python data work" triggers only GOAL
    results = await _extract(svc, "My goal is Python data work")

    # Both should be stored since categories differ; dedup is per-category
    assert svc.memory_count == 2


async def test_distinct_messages_both_stored():
    svc = MemoryExtractionService()
    await _extract(svc, "I prefer TypeScript")
    await _extract(svc, "I prefer Python for backend work")

    # Jaccard between {"i","prefer","typescript"} and {"i","prefer","python","for","backend","work"}
    # intersection = {i, prefer} = 2 / union = 7 ≈ 0.29 < 0.9 → both stored
    assert svc.memory_count == 2


# ---------------------------------------------------------------------------
# Relevant memory retrieval
# ---------------------------------------------------------------------------


async def test_get_relevant_memories_returns_correct_count():
    svc = MemoryExtractionService()
    await _extract(svc, "I prefer Python")
    await _extract(svc, "My goal is to build an API")
    await _extract(svc, "I prefer dark mode")

    results = svc.get_relevant_memories("Python API", top_k=2)

    assert len(results) <= 2


async def test_get_relevant_memories_ranks_by_keyword_overlap():
    svc = MemoryExtractionService()
    await _extract(svc, "I prefer Python for data science projects")
    await _extract(svc, "My goal is to learn guitar")

    results = svc.get_relevant_memories("Python data science")

    # The Python/data science memory should rank first
    assert "Python" in results[0].content or "python" in results[0].content.lower()


async def test_get_relevant_memories_empty_store_returns_empty_list():
    svc = MemoryExtractionService()

    results = svc.get_relevant_memories("anything")

    assert results == []


async def test_get_relevant_memories_top_k_zero_returns_empty():
    svc = MemoryExtractionService()
    await _extract(svc, "I prefer dark mode")

    results = svc.get_relevant_memories("dark mode", top_k=0)

    assert results == []


# ---------------------------------------------------------------------------
# Max memory limit
# ---------------------------------------------------------------------------


async def test_max_memory_limit_enforced():
    svc = MemoryExtractionService(max_memories=3)

    # Each unique message containing "prefer" triggers one PREFERENCE memory.
    messages = [
        "I prefer option A over anything else",
        "I prefer option B over anything else",
        "I prefer option C over anything else",
        "I prefer option D over anything else",  # should be rejected
    ]
    for msg in messages:
        await _extract(svc, msg)

    assert svc.memory_count == 3


async def test_memory_count_starts_at_zero():
    svc = MemoryExtractionService()

    assert svc.memory_count == 0


async def test_clear_resets_memory_count():
    svc = MemoryExtractionService()
    await _extract(svc, "I prefer dark mode")
    assert svc.memory_count == 1

    svc.clear()
    assert svc.memory_count == 0


# ---------------------------------------------------------------------------
# No signal → no extraction
# ---------------------------------------------------------------------------


async def test_no_signal_returns_empty():
    svc = MemoryExtractionService()
    results = await _extract(svc, "Hello, how are you?")

    assert results == []
    assert svc.memory_count == 0


# ---------------------------------------------------------------------------
# At most 3 memories per turn
# ---------------------------------------------------------------------------


async def test_at_most_three_memories_extracted_per_turn():
    svc = MemoryExtractionService()
    # Trigger multiple signals in a single message
    msg = (
        "My goal is to finish the project, "
        "I prefer Python, "
        "I am skilled in backend development, "
        "building a microservice"
    )
    results = await _extract(svc, msg)

    assert len(results) <= 3


# ---------------------------------------------------------------------------
# Session ID is preserved
# ---------------------------------------------------------------------------


async def test_source_session_id_stored_correctly():
    svc = MemoryExtractionService()
    custom_session = "my-custom-session-42"
    results = await _extract(svc, "I prefer vi over emacs", session_id=custom_session)

    assert results[0].source_session_id == custom_session
