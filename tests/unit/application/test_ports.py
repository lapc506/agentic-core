import inspect

from agentic_core.application.ports import (
    alert,
    cost_tracking,
    embedding_provider,
    embedding_store,
    graph,
    graph_store,
    logging,
    memory,
    metrics,
    session,
    tool,
    tracing,
)


def test_all_ports_are_abstract():
    modules = [
        memory, session, embedding_provider, embedding_store,
        graph_store, tool, graph, tracing, metrics,
        cost_tracking, logging, alert,
    ]
    found = 0
    for mod in modules:
        for name, cls in inspect.getmembers(mod, inspect.isclass):
            if name.endswith("Port"):
                assert inspect.isabstract(cls), f"{name} must be abstract"
                found += 1
    assert found == 12
