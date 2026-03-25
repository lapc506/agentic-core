from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class BinaryEvalRule(BaseModel, frozen=True):
    name: str
    question: str
    expected: bool
    evaluator: Literal["llm", "code", "regex"]


class EvalResult(BaseModel, frozen=True):
    rule_name: str
    passed: bool
    actual: bool
    detail: str | None = None
