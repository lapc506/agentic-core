from enum import StrEnum


class SessionState(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ESCALATED = "escalated"
    COMPLETED = "completed"


class GraphTemplate(StrEnum):
    REACT = "react"
    PLAN_EXECUTE = "plan-and-execute"
    REFLEXION = "reflexion"
    LLM_COMPILER = "llm-compiler"
    SUPERVISOR = "supervisor"
    ORCHESTRATOR = "orchestrator"


class EmbeddingTaskType(StrEnum):
    SEMANTIC_SIMILARITY = "SEMANTIC_SIMILARITY"
    RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
    RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"
    CODE_RETRIEVAL_QUERY = "CODE_RETRIEVAL_QUERY"
    CLASSIFICATION = "CLASSIFICATION"
    CLUSTERING = "CLUSTERING"
    QUESTION_ANSWERING = "QUESTION_ANSWERING"
    FACT_VERIFICATION = "FACT_VERIFICATION"


class PersonaCapability(StrEnum):
    GSD = "gsd"
    SUPERPOWERS = "superpowers"
    AUTO_RESEARCH = "auto_research"
