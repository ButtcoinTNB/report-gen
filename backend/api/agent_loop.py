from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from utils.agents_loop import AIAgentLoop
from services.docx_formatter import generate_docx

router = APIRouter()
agent_loop = AIAgentLoop()

class AgentLoopRequest(BaseModel):
    content: str
    additional_info: Optional[str] = ""

class AgentLoopResponse(BaseModel):
    draft: str
    feedback: Dict
    iterations: int
    docx_url: Optional[str] = None

@router.post("/generate-report", response_model=AgentLoopResponse)
async def generate_report(request: AgentLoopRequest):
    try:
        # Combine user content
        full_content = f"{request.content}\n\n{request.additional_info}" if request.additional_info else request.content
        
        # Run the AI agent loop
        result = await agent_loop.generate_report(full_content)
        
        # Generate docx preview (if you have this functionality)
        docx_url = await generate_docx(result["draft"])
        
        return {
            **result,
            "docx_url": docx_url
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 