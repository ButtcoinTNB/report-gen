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
    report_id: str
    additional_info: Optional[str] = ""

class RefineReportRequest(BaseModel):
    report_id: str
    content: str
    instructions: str

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
        # Get the report content from the uploaded files
        report_dir = Path(os.getcwd()) / "uploads" / request.report_id
        metadata_file = report_dir / "metadata.json"
        
        if not metadata_file.exists():
            raise HTTPException(status_code=404, detail="Report not found")
            
        # Run the AI agent loop with the report content and additional info
        result = await agent_loop.generate_report(str(metadata_file), request.additional_info)
        
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

@router.post("/refine-report", response_model=AgentLoopResponse)
async def refine_report(request: RefineReportRequest):
    try:
        # Validate the report exists
        report_dir = Path(os.getcwd()) / "uploads" / request.report_id
        if not os.path.exists(report_dir):
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Refine the report using the AI agent loop
        # We create a special instruction format for refinement
        refinement_prompt = f"""
        CONTENUTO ATTUALE DEL REPORT:
        {request.content}
        
        ISTRUZIONI PER IL MIGLIORAMENTO:
        {request.instructions}
        """
        
        # Call the agent loop with the refinement prompt
        result = await agent_loop.refine_report(refinement_prompt)
        
        # Generate unique filename for the DOCX
        filename = f"refined_report_{uuid.uuid4()}.docx"
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