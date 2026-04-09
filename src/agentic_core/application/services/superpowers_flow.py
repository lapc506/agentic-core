from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from agentic_core.domain.entities.roadmap import Roadmap

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from agentic_core.application.services.gsd_sequencer import GSDSequencer, RoadmapResult

logger = logging.getLogger(__name__)


@dataclass
class TerrainReport:
    architecture: str = ""
    conventions: list[str] = field(default_factory=list)
    stack: list[str] = field(default_factory=list)


@dataclass
class GapReport:
    security: list[str] = field(default_factory=list)
    ux: list[str] = field(default_factory=list)
    implementation: list[str] = field(default_factory=list)


@dataclass
class Approach:
    name: str
    description: str
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)


@dataclass
class SuperpowersResult:
    terrain: TerrainReport
    gaps: GapReport
    chosen_approach: Approach | None
    spec: str
    roadmap_result: RoadmapResult | None


class SuperpowersFlow:
    """Full engineering cycle: map terrain -> research gaps -> brainstorm ->
    HITL choose -> generate spec -> create roadmap -> HITL approve -> GSD execute."""

    def __init__(
        self,
        gsd: GSDSequencer,
        terrain_analyzer: Callable[[], Awaitable[TerrainReport]] | None = None,
        gap_researcher: Callable[[str], Awaitable[GapReport]] | None = None,
        brainstormer: Callable[[str, TerrainReport, GapReport], Awaitable[list[Approach]]] | None = None,
        spec_generator: Callable[[Approach], Awaitable[str]] | None = None,
        roadmap_creator: Callable[[str], Awaitable[Roadmap]] | None = None,
        hitl_callback: Callable[[str, list[Any]], Awaitable[int]] | None = None,
    ) -> None:
        self._gsd = gsd
        self._terrain_analyzer = terrain_analyzer
        self._gap_researcher = gap_researcher
        self._brainstormer = brainstormer
        self._spec_generator = spec_generator
        self._roadmap_creator = roadmap_creator
        self._hitl = hitl_callback

    async def run(self, idea: str) -> SuperpowersResult:
        # Phase 1: Map terrain
        terrain = await self._map_terrain()
        logger.info("Terrain mapped: %d conventions, stack=%s", len(terrain.conventions), terrain.stack)

        # Phase 2: Research gaps
        gaps = await self._research_gaps(idea)
        logger.info("Gaps found: security=%d, ux=%d, impl=%d",
                    len(gaps.security), len(gaps.ux), len(gaps.implementation))

        # Phase 3: Brainstorm approaches
        approaches = await self._brainstorm(idea, terrain, gaps)
        logger.info("Generated %d approaches", len(approaches))

        # Phase 4: HITL — user chooses approach
        chosen_idx = await self._hitl_choose("Choose an approach:", approaches)
        chosen = approaches[chosen_idx] if approaches else None

        if chosen is None:
            return SuperpowersResult(terrain=terrain, gaps=gaps, chosen_approach=None,
                                     spec="", roadmap_result=None)

        # Phase 5: Generate spec
        spec = await self._generate_spec(chosen)

        # Phase 6: Create roadmap
        roadmap = await self._create_roadmap(spec)

        # Phase 7: HITL — user approves roadmap
        await self._hitl_choose("Approve roadmap?", ["Approve", "Reject"])

        # Phase 8: Execute via GSD
        roadmap_result = await self._gsd.execute_roadmap(roadmap)

        return SuperpowersResult(
            terrain=terrain,
            gaps=gaps,
            chosen_approach=chosen,
            spec=spec,
            roadmap_result=roadmap_result,
        )

    async def _map_terrain(self) -> TerrainReport:
        if self._terrain_analyzer:
            return await self._terrain_analyzer()
        return TerrainReport(architecture="unknown", conventions=[], stack=[])

    async def _research_gaps(self, idea: str) -> GapReport:
        if self._gap_researcher:
            return await self._gap_researcher(idea)
        return GapReport()

    async def _brainstorm(self, idea: str, terrain: TerrainReport, gaps: GapReport) -> list[Approach]:
        if self._brainstormer:
            return await self._brainstormer(idea, terrain, gaps)
        return [Approach(name="Default", description="Direct implementation")]

    async def _generate_spec(self, approach: Approach) -> str:
        if self._spec_generator:
            return await self._spec_generator(approach)
        return f"Spec for approach: {approach.name}"

    async def _create_roadmap(self, spec: str) -> Roadmap:
        if self._roadmap_creator:
            return await self._roadmap_creator(spec)
        return Roadmap(title="Generated Roadmap", objectives=["Implement spec"])

    async def _hitl_choose(self, prompt: str, options: list[Any]) -> int:
        if self._hitl:
            return await self._hitl(prompt, options)
        return 0  # Default: first option
