import os
import json
import httpx
import random
from typing import Dict, List, Tuple
from pathlib import Path
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIAgentLoop:
    def __init__(self, max_loops: int = 3):
        self.max_loops = max_loops
        self.brand_guide = self._load_brand_guide()
        self.reference_examples = self._load_references()
        self.writer_prompt, self.reviewer_prompt = self._load_prompts()
        
    def _load_brand_guide(self) -> str:
        """Load the brand guide from the data directory."""
        guide_path = Path(__file__).parent.parent / "data" / "brand_guide.txt"
        with open(guide_path, "r", encoding="utf-8") as f:
            return f.read()
            
    def _load_references(self) -> List[Dict]:
        """Load and randomly select reference reports for style examples."""
        refs_path = Path(__file__).parent.parent / "data" / "reference_reports.jsonl"
        references = []
        with open(refs_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    references.append(json.loads(line))
        # Randomly select 5 examples to avoid bias
        return random.sample(references, min(5, len(references)))
            
    def _load_prompts(self) -> Tuple[str, str]:
        """Load the system prompts from prompts.json."""
        prompts_path = Path(__file__).parent.parent / "data" / "prompts.json"
        with open(prompts_path, "r", encoding="utf-8") as f:
            prompts = json.load(f)
            return prompts["writer_system_prompt"], prompts["reviewer_system_prompt"]
        
    async def _call_model(self, prompt: str, system_prompt: str, retries: int = 2) -> str:
        """Make an API call to the configured model via OpenRouter with retries."""
        last_error = None
        
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions"),
                        headers={
                            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": os.getenv("FRONTEND_URL", "http://localhost:3000"),
                            "X-Title": os.getenv("APP_NAME", "Generatore di Perizie")
                        },
                        json={
                            "model": os.getenv("DEFAULT_MODEL", "google/gemini-2.0-pro-exp-02-05:free"),
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": prompt}
                            ]
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 429:
                        logger.warning(f"Rate limit hit on attempt {attempt + 1}, retrying...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                        
                    if response.status_code != 200:
                        logger.error(f"API Error: {response.status_code} - {response.text}")
                        raise Exception(f"API call failed with status {response.status_code}")
                        
                    return response.json()["choices"][0]["message"]["content"]
                    
            except Exception as e:
                last_error = e
                logger.error(f"Error calling model (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise last_error
            
    async def generate_report(self, user_content: str) -> Dict:
        """Run the AI agent loop to generate and refine the report."""
        draft = ""
        feedback = {"score": 0, "suggestions": []}
        
        # Format reference examples for prompts
        style_examples = "\n".join([
            f"=== ESEMPIO {i+1} ===\nInput:\n{ex['messages'][0]['content']}\n\nOutput:\n{ex['messages'][1]['content']}\n"
            for i, ex in enumerate(self.reference_examples)
        ])
        
        for i in range(self.max_loops):
            logger.info(f"Starting iteration {i + 1}/{self.max_loops}")
            
            # Writer agent generates/refines the report
            writer_input = f"""
            === GUIDA BRAND ===
            {self.brand_guide}

            === RIFERIMENTI STILISTICI ===
            {style_examples}

            === CONTENUTO UTENTE ===
            {user_content}

            {f'=== FEEDBACK PRECEDENTE ===\\n' + '\\n'.join(["- " + s for s in feedback["suggestions"]]) if feedback["suggestions"] else ''}
            """
            
            draft = await self._call_model(writer_input, self.writer_prompt)
            
            # Reviewer agent analyzes the draft
            reviewer_input = f"""
            === GUIDA BRAND ===
            {self.brand_guide}

            === RIFERIMENTI STILISTICI ===
            {style_examples}

            === CONTENUTO UTENTE ===
            {user_content}

            === TESTO GENERATO ===
            {draft}
            """
            
            review_result = await self._call_model(reviewer_input, self.reviewer_prompt)
            
            try:
                feedback = json.loads(review_result)
                logger.info(f"Feedback score: {feedback['score']}, suggestions: {len(feedback['suggestions'])}")
            except json.JSONDecodeError:
                logger.warning("Failed to parse reviewer feedback JSON, retrying with explicit JSON instruction")
                # Retry with explicit JSON instruction
                review_result = await self._call_model(
                    reviewer_input + "\n\nIMPORTANTE: Rispondi SOLO con un oggetto JSON valido nel formato specificato.",
                    self.reviewer_prompt
                )
                try:
                    feedback = json.loads(review_result)
                except json.JSONDecodeError:
                    feedback = {"score": 0, "suggestions": ["Errore nel formato del feedback"]}
                    logger.error("Failed to parse reviewer feedback JSON even after retry")
                
            # Exit if quality is high enough or minimal suggestions
            if feedback["score"] > 0.9 or (feedback["score"] > 0.8 and len(feedback["suggestions"]) <= 1):
                logger.info(f"Quality threshold met at iteration {i + 1}")
                break
                
        return {
            "draft": draft,
            "feedback": feedback,
            "iterations": i + 1
        } 