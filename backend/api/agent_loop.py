from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from utils.agents_loop import AIAgentLoop
from services.docx_formatter import generate_docx
import uuid
import os
from pathlib import Path

router = APIRouter()
agent_loop = AIAgentLoop()

class AgentLoopRequest(BaseModel):
    content: str
    additional_info: Optional[str] = ""

class FeedbackDict(BaseModel):
    score: float
    suggestions: List[str]

class AgentLoopResponse(BaseModel):
    draft: str
    feedback: FeedbackDict
    iterations: int
    docx_url: Optional[str] = None

@router.post("/generate-report", response_model=AgentLoopResponse)
async def generate_report(request: AgentLoopRequest):
    try:
        # Combine user content
        full_content = f"{request.content}\n\n{request.additional_info}" if request.additional_info else request.content
        
        # Run the AI agent loop
        result = await agent_loop.generate_report(full_content)
        
        # Generate unique filename for the DOCX
        filename = f"report_{uuid.uuid4()}.docx"
        reports_dir = Path(os.getcwd()) / "generated_reports"
        reports_dir.mkdir(exist_ok=True)
        output_path = str(reports_dir / filename)
        
        # Generate DOCX (not async)
        docx_path = generate_docx(
            report_text=result["draft"],
            output_filename=output_path
        )
        
        return {
            "draft": result["draft"],
            "feedback": {
                "score": result.get("feedback", {}).get("score", 0.0),
                "suggestions": result.get("feedback", {}).get("suggestions", [])
            },
            "iterations": result.get("iterations", 1),
            "docx_url": f"/download/{os.path.basename(docx_path)}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 