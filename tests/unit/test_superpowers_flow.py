from __future__ import annotations

from agentic_core.application.services.gsd_sequencer import GSDSequencer
from agentic_core.application.services.superpowers_flow import SuperpowersFlow


async def test_superpowers_default_flow():
    gsd = GSDSequencer()
    flow = SuperpowersFlow(gsd)
    result = await flow.run("Build a feature")

    assert result.terrain is not None
    assert result.chosen_approach is not None
    assert result.chosen_approach.name == "Default"
    assert result.spec != ""
    assert result.roadmap_result is not None
    assert result.roadmap_result.success


async def test_superpowers_with_custom_brainstorm():
    from agentic_core.application.services.superpowers_flow import (
        Approach,
        GapReport,
        TerrainReport,
    )

    async def custom_brainstorm(idea: str, terrain: TerrainReport, gaps: GapReport) -> list[Approach]:
        return [
            Approach(name="A", description="Approach A", pros=["fast"], cons=["fragile"]),
            Approach(name="B", description="Approach B", pros=["solid"], cons=["slow"]),
        ]

    async def hitl(prompt: str, options: list) -> int:
        return 1  # Choose B

    gsd = GSDSequencer()
    flow = SuperpowersFlow(gsd, brainstormer=custom_brainstorm, hitl_callback=hitl)
    result = await flow.run("Build X")

    assert result.chosen_approach is not None
    assert result.chosen_approach.name == "B"
