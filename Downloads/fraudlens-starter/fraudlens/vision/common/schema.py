"""SHARED OUTPUT CONTRACT. Every analyzer must return an AnalysisResult.
Change this file only after agreeing as a team (it affects all 3 members)."""
from typing import List, Literal
from pydantic import BaseModel, Field

Category = Literal[
    "banking_kyc", "upi_payment", "phishing", "fake_job", "romance",
    "legitimate", "unknown",
]
Source = Literal["text", "conversation", "screenshot", "url"]
TACTICS = ["urgency", "authority", "fear", "reward", "isolation"]


class AnalysisResult(BaseModel):
    source: Source
    signals: List[str] = Field(default_factory=list)   # concrete evidence found
    tactics: List[str] = Field(default_factory=list)   # manipulation techniques
    category: Category = "unknown"
    score: float = Field(0.0, ge=0.0, le=1.0)          # 0 = safe, 1 = scam
    explanation: str = ""


class Verdict(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    recommendation: Literal["safe", "warn", "block"]
    category: Category = "unknown"
    tactics: List[str] = Field(default_factory=list)
    signals: List[str] = Field(default_factory=list)
    explanation: str = ""
    details: List[AnalysisResult] = Field(default_factory=list)
