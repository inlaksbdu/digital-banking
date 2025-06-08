from typing import List
from pydantic import BaseModel


class BiometricVerificationResult(BaseModel):
    face_match_score: float
    success: bool
    message: str


class CardData(BaseModel):
    field: str
    value: str
    confidence: float


class Warning(BaseModel):
    code: str
    description: str
    severity: str
    confidence: float
    decision: str


class DocumentVerificationResponse(BaseModel):
    success: bool
    transaction_id: str
    data: List[CardData]
    warnings: List[Warning]
    review_score: int
    reject_score: int
    decision: str
