from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# Client
class ClientCreate(BaseModel):
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    presenting_issue: str = ""
    notes: str = ""


class ClientResponse(BaseModel):
    id: int
    name: str
    age: Optional[int]
    gender: Optional[str]
    presenting_issue: str
    notes: str
    created_at: datetime

    class Config:
        from_attributes = True


# Session
class SessionCreate(BaseModel):
    client_id: int
    session_number: int
    raw_text: str
    technique_used: str = ""
    session_date: Optional[str] = None


class SessionUpdateScores(BaseModel):
    depression_score: float
    anxiety_score: float
    anger_score: float
    self_esteem_score: float
    key_persons: str = "[]"
    defense_mechanisms: str = "[]"
    ai_summary: str = ""
    soap_subjective: str = ""
    soap_objective: str = ""
    soap_assessment: str = ""
    soap_plan: str = ""
    risk_level: str = "none"
    risk_keywords: str = "[]"


class SessionResponse(BaseModel):
    id: int
    client_id: int
    session_number: int
    raw_text: str
    depression_score: float
    anxiety_score: float
    anger_score: float
    self_esteem_score: float
    key_persons: str
    defense_mechanisms: str
    ai_summary: str
    technique_used: str
    risk_level: str
    risk_keywords: str
    soap_subjective: str
    soap_objective: str
    soap_assessment: str
    soap_plan: str
    session_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# AI Parse result
class AIParseResult(BaseModel):
    depression_score: float
    anxiety_score: float
    anger_score: float
    self_esteem_score: float
    key_persons: list[str]
    defense_mechanisms: list[str]
    summary: str


# Comparison
class ComparisonRequest(BaseModel):
    client_id: int
    session_numbers: list[int]


# RAG Recommendation
class RAGRecommendation(BaseModel):
    case_id: str
    similarity: float
    technique_used: str
    outcome_summary: str
    suggestion: str
