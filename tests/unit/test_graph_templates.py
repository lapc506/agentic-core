"""Tests for graph templates. Run without LangGraph (fallback mode)."""
from __future__ import annotations

from agentic_core.graph_templates.llm_compiler import LLMCompilerGraphTemplate, LLMCompilerState
from agentic_core.graph_templates.orchestrator import OrchestratorGraphTemplate, OrchestratorState
from agentic_core.graph_templates.plan_execute import PlanExecuteGraphTemplate, PlanExecuteState
from agentic_core.graph_templates.react import ReactGraphTemplate, ReactState
from agentic_core.graph_templates.reflexion import ReflexionGraphTemplate, ReflexionState
from agentic_core.graph_templates.supervisor import SupervisorGraphTemplate, SupervisorState

# -- React --

def test_react_builds():
    t = ReactGraphTemplate(max_iterations=10)
    graph = t.build_graph()
    assert graph is not None


async def test_react_think_increments():
    t = ReactGraphTemplate()
    state: ReactState = {"messages": [], "iterations": 0, "max_iterations": 5, "done": False}
    result = await t._think(state)
    assert result["iterations"] == 1


async def test_react_should_continue_done():
    t = ReactGraphTemplate()
    assert t._should_continue({"done": True}) == "end"


async def test_react_should_continue_max():
    t = ReactGraphTemplate(max_iterations=3)
    assert t._should_continue({"iterations": 3, "max_iterations": 3}) == "end"


async def test_react_should_continue_no_tools():
    t = ReactGraphTemplate()
    assert t._should_continue({"iterations": 1, "tool_calls": []}) == "end"


async def test_react_should_continue_has_tools():
    t = ReactGraphTemplate()
    assert t._should_continue({"iterations": 1, "tool_calls": [{"name": "x"}]}) == "continue"


# -- Plan-Execute --

def test_plan_execute_builds():
    t = PlanExecuteGraphTemplate()
    graph = t.build_graph()
    assert graph is not None


async def test_plan_execute_plan():
    t = PlanExecuteGraphTemplate()
    state: PlanExecuteState = {"messages": [], "plan": ["step1", "step2"]}
    result = await t._plan(state)
    assert result["current_step"] == 0


async def test_plan_execute_step():
    t = PlanExecuteGraphTemplate()
    state: PlanExecuteState = {"plan": ["a", "b"], "current_step": 0, "results": []}
    result = await t._execute_step(state)
    assert len(result["results"]) == 1
    assert result["current_step"] == 1


async def test_plan_execute_after_execute_end():
    t = PlanExecuteGraphTemplate()
    assert t._after_execute({"plan": ["a"], "current_step": 1}) == "end"


async def test_plan_execute_after_execute_next():
    t = PlanExecuteGraphTemplate()
    assert t._after_execute({"plan": ["a", "b"], "current_step": 1}) == "next_step"


async def test_plan_execute_after_execute_replan():
    t = PlanExecuteGraphTemplate()
    assert t._after_execute({"plan": ["a"], "current_step": 0, "needs_replan": True}) == "replan"


# -- Reflexion --

def test_reflexion_builds():
    t = ReflexionGraphTemplate()
    graph = t.build_graph()
    assert graph is not None


async def test_reflexion_act_increments():
    t = ReflexionGraphTemplate()
    state: ReflexionState = {"attempts": 0}
    result = await t._act(state)
    assert result["attempts"] == 1


async def test_reflexion_should_retry_quality_ok():
    t = ReflexionGraphTemplate()
    assert t._should_retry({"quality_ok": True}) == "accept"


async def test_reflexion_should_retry_max():
    t = ReflexionGraphTemplate(max_attempts=2)
    assert t._should_retry({"quality_ok": False, "attempts": 2, "max_attempts": 2}) == "accept"


async def test_reflexion_should_retry_bad_quality():
    t = ReflexionGraphTemplate()
    assert t._should_retry({"quality_ok": False, "attempts": 1}) == "retry"


# -- LLM-Compiler --

def test_llm_compiler_builds():
    t = LLMCompilerGraphTemplate()
    graph = t.build_graph()
    assert graph is not None


async def test_llm_compiler_execute_parallel():
    t = LLMCompilerGraphTemplate()
    state: LLMCompilerState = {"dag": [{"id": "a"}, {"id": "b"}]}
    result = await t._execute_parallel(state)
    assert "a" in result["parallel_results"]
    assert "b" in result["parallel_results"]


async def test_llm_compiler_join():
    t = LLMCompilerGraphTemplate()
    state: LLMCompilerState = {"parallel_results": {"a": "r1", "b": "r2"}}
    result = await t._join(state)
    assert "a=r1" in result["joined_output"]
    assert result["done"] is True


# -- Supervisor --

def test_supervisor_builds():
    t = SupervisorGraphTemplate(delegate_names=["support", "billing"])
    graph = t.build_graph()
    assert graph is not None


async def test_supervisor_route():
    t = SupervisorGraphTemplate(delegate_names=["support", "billing"])
    state: SupervisorState = {}
    result = await t._route(state)
    assert result["routed_to"] == "support"


async def test_supervisor_delegate():
    t = SupervisorGraphTemplate()
    state: SupervisorState = {"routed_to": "support", "delegate_results": {}}
    result = await t._delegate(state)
    assert "support" in result["delegate_results"]


async def test_supervisor_after_delegate_more():
    t = SupervisorGraphTemplate(delegate_names=["a", "b"])
    assert t._after_delegate({"delegate_results": {"a": "r"}}) == "more"


async def test_supervisor_after_delegate_done():
    t = SupervisorGraphTemplate(delegate_names=["a", "b"])
    assert t._after_delegate({"delegate_results": {"a": "r", "b": "r"}}) == "done"


async def test_supervisor_synthesize():
    t = SupervisorGraphTemplate()
    state: SupervisorState = {"delegate_results": {"a": "r1", "b": "r2"}}
    result = await t._synthesize(state)
    assert "a: r1" in result["final_response"]
    assert result["done"] is True


# -- Orchestrator --

def test_orchestrator_builds():
    t = OrchestratorGraphTemplate()
    graph = t.build_graph()
    assert graph is not None


async def test_orchestrator_phases():
    t = OrchestratorGraphTemplate()
    state: OrchestratorState = {}
    state = await t._analyze(state)
    assert state["phase"] == "analyze"
    state = await t._brainstorm(state)
    assert state["phase"] == "brainstorm"
    state = await t._choose(state)
    assert state["phase"] == "choose"
    state = await t._generate_spec(state)
    assert state["phase"] == "spec"
    state = await t._execute(state)
    assert state["phase"] == "execute"


async def test_orchestrator_after_execute_end():
    t = OrchestratorGraphTemplate()
    assert t._after_execute({}) == "end"


async def test_orchestrator_after_execute_optimize():
    t = OrchestratorGraphTemplate()
    assert t._after_execute({"skills_to_optimize": ["skill1"]}) == "optimize"
