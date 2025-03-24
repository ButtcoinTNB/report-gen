from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class AgentRequest(BaseModel):
    """Base model for agent requests."""
    content: str = Field(..., description="Content to process")
    max_tokens: Optional[int] = Field(2000, description="Maximum tokens in response")
    temperature: Optional[float] = Field(0.7, description="Temperature for response generation")
    options: Optional[Dict[str, Any]] = Field(None, description="Additional options")

class WriterAgentRequest(AgentRequest):
    """Model for writer agent requests."""
    document_content: Dict[str, Any] = Field(..., description="Document content and metadata")
    iteration: int = Field(1, description="Current iteration number")
    previous_feedback: Optional[str] = Field(None, description="Feedback from previous iteration")

class ReviewerAgentRequest(AgentRequest):
    """Model for reviewer agent requests."""
    document_content: Dict[str, Any] = Field(..., description="Original document content")
    draft_content: str = Field(..., description="Draft content to review")
    iteration: int = Field(1, description="Current iteration number")
    
class AgentResponse(BaseModel):
    """Base model for agent responses."""
    content: str = Field(..., description="Generated content")
    tokens_used: int = Field(..., description="Number of tokens used")
    completion_time: float = Field(..., description="Time taken to generate response (seconds)")

class WriterAgentResponse(AgentResponse):
    """Model for writer agent responses."""
    pass

class ReviewerAgentResponse(AgentResponse):
    """Model for reviewer agent responses."""
    quality_score: float = Field(..., description="Quality score (0-1)")
    feedback: str = Field(..., description="Feedback for improvement")
    improvement_areas: List[str] = Field(..., description="Areas needing improvement") 