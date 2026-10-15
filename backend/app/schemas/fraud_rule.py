from pydantic import BaseModel
from typing import List, Optional

class FraudEvaluationResult(BaseModel):
    fraud_score: float
    decision: str
    primary_rule: str
    rules_triggered: List[str]
    latency_microseconds: float
    c_accelerated: bool

class RuleDefinition(BaseModel):
    rule_id: str
    name: str
    description: str
    severity: str # LOW, MEDIUM, HIGH, CRITICAL
    weight: float
