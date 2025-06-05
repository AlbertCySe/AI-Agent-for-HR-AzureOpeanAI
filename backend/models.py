from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union

# Pydantic Models for Request/Response Bodies

class Message(BaseModel):
    role: str
    content: str

class FollowUpQuestionRequest(BaseModel):
    messages: List[Message]

class IndividualEvaluation(BaseModel):
    question: str
    response_summary: str
    score: int
    rationale: str

class EvaluationResponse(BaseModel):
    individual_evaluations: List[IndividualEvaluation]
    overall_interview_score: int
    overall_interview_summary: str

class FullAnalysisResponse(BaseModel):
    score: Dict[str, Any]
    interview_questions: str
    extracted_resume_text: str
    extracted_jd_text: str

class AiDetectionData(BaseModel):
    classification: str
    overall_confidence_score: Union[int, str]
    formatting_consistency_score: Union[int, str]
    language_use_score: Union[int, str]
    detail_depth_score: Union[int, str]
    error_detection_score: Union[int, str]
    explanation: Optional[str] = None

class AiDetectionResponse(BaseModel):
    status: str
    data: AiDetectionData
