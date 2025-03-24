from typing import Dict, Any, List, Optional
import asyncio
import json
import uuid
import logging
from datetime import datetime

from ..models.report import ReportCreate, Report
from ..models.agent import AgentRequest, AgentResponse
from ..config import get_settings
from .task_manager import task_manager

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(self):
        self.settings = get_settings()
        self._agent_states = {}  # Keep track of agent states for recovery
        
    async def generate_report(self, report_data: ReportCreate) -> Dict[str, Any]:
        """
        Initialize the agent loop for report generation.
        Uses the task manager for asynchronous processing.
        """
        task_id = str(uuid.uuid4())
        report_id = str(uuid.uuid4())
        
        # Store initial state
        self._agent_states[report_id] = {
            "status": "initializing",
            "iterations": 0,
            "quality_score": 0,
            "start_time": datetime.utcnow().isoformat(),
            "last_update": datetime.utcnow().isoformat(),
            "file_ids": report_data.file_ids,
            "task_id": task_id
        }
        
        # Schedule the agent loop as an asynchronous task
        await task_manager.schedule_task(
            task_id=task_id,
            coroutine=self._run_agent_loop(report_id, report_data),
            task_type="report_generation",
            metadata={
                "report_id": report_id,
                "file_count": len(report_data.file_ids)
            }
        )
        
        return {
            "report_id": report_id,
            "task_id": task_id,
            "status": "processing"
        }
        
    async def _run_agent_loop(self, report_id: str, report_data: ReportCreate) -> Dict[str, Any]:
        """
        Run the writer/reviewer agent loop with resource optimization.
        This is the main processing function executed by the task manager.
        """
        try:
            self._update_agent_state(report_id, {"status": "processing"})
            
            # Extract document content - potentially resource intensive
            document_content = await self._extract_document_content(report_data.file_ids)
            
            # Run the writer/reviewer loop
            max_iterations = 3
            current_iteration = 0
            quality_threshold = 0.9  # 90% quality required
            quality_score = 0
            final_content = None
            
            while current_iteration < max_iterations and quality_score < quality_threshold:
                current_iteration += 1
                
                # Update state
                self._update_agent_state(report_id, {
                    "status": "iteration",
                    "iterations": current_iteration,
                    "last_update": datetime.utcnow().isoformat()
                })
                
                # Writer agent - generate draft (CPU/memory intensive)
                draft_content = await self._run_writer_agent(document_content, current_iteration)
                
                # Reviewer agent - evaluate quality (CPU/memory intensive)
                review_result = await self._run_reviewer_agent(document_content, draft_content)
                
                quality_score = review_result.get("quality_score", 0)
                feedback = review_result.get("feedback", "")
                
                # Update state with quality information
                self._update_agent_state(report_id, {
                    "quality_score": quality_score,
                    "last_update": datetime.utcnow().isoformat()
                })
                
                # If quality is sufficient or we're at max iterations, use this content
                if quality_score >= quality_threshold or current_iteration >= max_iterations:
                    final_content = draft_content
                    break
                
                # Otherwise, incorporate feedback for next iteration
                document_content = self._incorporate_feedback(document_content, feedback)
            
            # Generate the final report document
            report_url = await self._generate_report_document(report_id, final_content)
            
            # Calculate time saved estimate (in minutes)
            time_saved = self._calculate_time_saved(document_content)
            
            # Update the state to completed
            self._update_agent_state(report_id, {
                "status": "completed",
                "quality_score": quality_score,
                "report_url": report_url,
                "time_saved": time_saved,
                "last_update": datetime.utcnow().isoformat()
            })
            
            return {
                "report_id": report_id,
                "status": "completed",
                "quality_score": quality_score,
                "iterations": current_iteration,
                "report_url": report_url,
                "time_saved": time_saved
            }
            
        except Exception as e:
            logger.error(f"Error in agent loop for report {report_id}: {str(e)}")
            self._update_agent_state(report_id, {
                "status": "failed",
                "error": str(e),
                "last_update": datetime.utcnow().isoformat()
            })
            raise
    
    async def _extract_document_content(self, file_ids: List[str]) -> Dict[str, Any]:
        """
        Extract content from documents - uses thread pool for CPU-bound operations.
        """
        content = {}
        for file_id in file_ids:
            # This is a CPU-bound operation, run in thread pool
            file_content = await task_manager.run_in_thread(
                self._extract_single_document, file_id
            )
            content[file_id] = file_content
            
        return content
    
    def _extract_single_document(self, file_id: str) -> Dict[str, Any]:
        """
        CPU-bound operation to extract content from a single document.
        This runs in a thread pool to avoid blocking the event loop.
        """
        # Simulate document extraction
        # In production, this would use libraries like PyPDF2, python-docx, etc.
        import time
        import random
        time.sleep(random.uniform(0.5, 2.0))  # Simulate processing time
        
        return {
            "text": f"Document content for {file_id}",
            "metadata": {
                "page_count": random.randint(1, 20),
                "word_count": random.randint(100, 5000)
            }
        }
        
    async def _run_writer_agent(self, document_content: Dict[str, Any], iteration: int) -> str:
        """
        Run the writer agent to generate a report draft.
        Uses intelligent batching to optimize token usage.
        """
        # In a real implementation, this would call the OpenRouter API
        # For now, we'll simulate the writer agent
        
        # Simulate API call delay
        await asyncio.sleep(1)
        
        return f"Generated report draft (iteration {iteration})"
        
    async def _run_reviewer_agent(self, document_content: Dict[str, Any], draft_content: str) -> Dict[str, Any]:
        """
        Run the reviewer agent to evaluate draft quality.
        Uses efficient prompt engineering to minimize token usage.
        """
        # In a real implementation, this would call the OpenRouter API
        # For now, we'll simulate the reviewer agent
        
        # Simulate API call delay
        await asyncio.sleep(1)
        
        import random
        quality_score = min(random.uniform(0.7, 0.95) + (0.05 * random.random()), 1.0)
        
        return {
            "quality_score": quality_score,
            "feedback": "The report needs improvement in the following areas..."
        }
    
    def _incorporate_feedback(self, document_content: Dict[str, Any], feedback: str) -> Dict[str, Any]:
        """
        Incorporate reviewer feedback for the next iteration.
        """
        # Simply return the original content with feedback appended
        # In a real implementation, this would prepare the context for the next iteration
        document_content["feedback"] = feedback
        return document_content
        
    async def _generate_report_document(self, report_id: str, content: str) -> str:
        """
        Generate the final report document (DOCX/PDF).
        """
        # Simulate document generation
        await asyncio.sleep(2)
        
        # In a real implementation, this would create and store the document
        report_url = f"/api/reports/{report_id}/download"
        return report_url
        
    def _calculate_time_saved(self, document_content: Dict[str, Any]) -> int:
        """
        Calculate estimated time saved (in minutes) based on document complexity.
        """
        # Simple calculation based on word count
        total_words = 0
        for file_id, content in document_content.items():
            if "metadata" in content and "word_count" in content["metadata"]:
                total_words += content["metadata"]["word_count"]
                
        # Assume 30 words per minute for manual processing
        # This is a very simplistic model - a real implementation would be more sophisticated
        time_saved = total_words // 30
        
        # Ensure minimum value and reasonable maximum
        return max(min(time_saved, 480), 15)  # Between 15 minutes and 8 hours
    
    def _update_agent_state(self, report_id: str, update: Dict[str, Any]) -> None:
        """
        Update the agent state for a report.
        """
        if report_id in self._agent_states:
            self._agent_states[report_id].update(update)
            
    async def get_report_status(self, report_id: str) -> Dict[str, Any]:
        """
        Get the current status of a report generation process.
        """
        if report_id not in self._agent_states:
            return {
                "report_id": report_id,
                "status": "not_found"
            }
            
        state = self._agent_states[report_id]
        
        # If the report has a task_id, get the task status
        if "task_id" in state and state["task_id"]:
            task_status = await task_manager.get_task_status(state["task_id"])
            
            # If the task has failed, update the state
            if task_status["status"] == "failed" and state["status"] != "failed":
                self._update_agent_state(report_id, {
                    "status": "failed",
                    "error": task_status["message"],
                    "last_update": datetime.utcnow().isoformat()
                })
        
        return {
            "report_id": report_id,
            **state
        }
        
    async def cancel_report_generation(self, report_id: str) -> bool:
        """
        Cancel a report generation process.
        """
        if report_id not in self._agent_states:
            return False
            
        state = self._agent_states[report_id]
        
        # If the report has a task_id, cancel the task
        if "task_id" in state and state["task_id"]:
            await task_manager.cancel_task(state["task_id"])
            
        # Update the state
        self._update_agent_state(report_id, {
            "status": "cancelled",
            "last_update": datetime.utcnow().isoformat()
        })
        
        return True

# Singleton instance
agent_service = AgentService() 