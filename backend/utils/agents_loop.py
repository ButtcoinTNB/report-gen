import os
import json
import httpx
import random
from typing import Dict, List, Tuple
from pathlib import Path
import logging
import asyncio
import time
from hashlib import md5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Safe defaults for environment variables
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")  # Empty string as fallback
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://report-gen-liard.vercel.app/")
APP_NAME = os.getenv("APP_NAME", "Generatore di Perizie")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "google/gemini-2.0-pro-exp-02-05:free")

class AIAgentLoop:
    def __init__(self, max_loops: int = 3):
        self.max_loops = max_loops
        self.brand_guide = self._load_brand_guide()
        self.reference_examples = self._load_references()
        self.writer_prompt, self.reviewer_prompt = self._load_prompts()
        # Cache for similar refinements
        self.refinement_cache = {}
        self.cache_max_size = 50  # Maximum cache entries
        
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
        
    def _load_template(self) -> str:
        """Load the template.docx file for format reference."""
        template_path = Path(__file__).parent.parent / "reference_reports" / "template.docx"
        with open(template_path, "rb") as f:
            return f.read()
        
    async def _call_model(self, prompt: str, system_prompt: str, retries: int = 2) -> str:
        """Make an API call to the configured model via OpenRouter with retries."""
        if not OPENROUTER_API_KEY:
            raise Exception("OPENROUTER_API_KEY environment variable is not set")
            
        last_error = None
        
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        OPENROUTER_API_URL,
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": FRONTEND_URL,
                            "X-Title": APP_NAME
                        },
                        json={
                            "model": DEFAULT_MODEL,
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
            
    def _get_instruction_hash(self, instruction_text: str) -> str:
        """Generate a simplified hash for similar instructions."""
        # Normalize text by removing punctuation and converting to lowercase
        import re
        from hashlib import md5
        
        # Normalize text
        normalized = re.sub(r'[^\w\s]', '', instruction_text.lower())
        words = normalized.split()
        
        # Sort words to make order-independent
        words.sort()
        
        # Take only the first 10 words for similarity
        key_words = ' '.join(words[:10])
        
        # Generate MD5 hash
        return md5(key_words.encode()).hexdigest()
        
    async def generate_report(self, user_content: str) -> Dict:
        """Run the AI agent loop to generate and refine the report."""
        draft = ""
        feedback = {"score": 0, "suggestions": []}
        
        # Format reference examples for prompts
        style_examples = "\n".join([
            f"=== ESEMPIO {i+1} ===\nInput:\n{ex['messages'][0]['content']}\n\nOutput:\n{ex['messages'][1]['content']}\n"
            for i, ex in enumerate(self.reference_examples)
        ])

        # Pre-format feedback section
        def format_feedback():
            if not feedback["suggestions"]:
                return ""
            suggestions = "\n".join(f"- {s}" for s in feedback["suggestions"])
            return f"=== FEEDBACK PRECEDENTE ===\n{suggestions}"
        
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

            {format_feedback()}
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

    async def refine_report(self, refinement_prompt: str, progress_callback=None) -> Dict:
        """
        Run a special refinement loop based on user instructions.
        
        This is similar to generate_report but focuses on specific refinement instructions
        and starts with an existing draft content.
        
        Args:
            refinement_prompt: A formatted prompt with the current content and refinement instructions
            progress_callback: Optional callback for progress reporting
            
        Returns:
            Dict with draft, feedback and iterations
        """
        # Extract content and instructions from the refinement prompt
        content_start = refinement_prompt.find("CONTENUTO ATTUALE DEL REPORT:")
        instructions_start = refinement_prompt.find("ISTRUZIONI PER IL MIGLIORAMENTO:")
        
        if content_start > -1 and instructions_start > -1:
            content = refinement_prompt[content_start + len("CONTENUTO ATTUALE DEL REPORT:"):instructions_start].strip()
            instructions = refinement_prompt[instructions_start + len("ISTRUZIONI PER IL MIGLIORAMENTO:"):].strip()
        else:
            # Fallback if the format is different
            content = refinement_prompt
            instructions = "Migliora il report mantenendo lo stesso stile e struttura."
        
        # Notify progress
        if progress_callback:
            progress_callback(0.05, "Analyzing instructions and content")
        
        # Check cache for similar instructions
        instruction_hash = self._get_instruction_hash(instructions)
        cache_key = f"{instruction_hash}_{len(content) % 1000}"  # Include content length signature
        
        # Only use cache for relatively simple instructions to avoid confusion
        if len(instructions.split()) < 20 and cache_key in self.refinement_cache:
            cached_result = self.refinement_cache[cache_key]
            logger.info(f"Using cached refinement pattern (hash: {instruction_hash[:8]})")
            
            # Update the cached entry's usage timestamp
            cached_result["last_used"] = time.time()
            
            if progress_callback:
                progress_callback(0.3, "Using cached refinement pattern")
            
            # For cached results, we still need to run the model once to apply to this content
            # but we can skip the review phase and multiple iterations
            writer_input = f"""
            === ISTRUZIONI ===
            Applica il seguente pattern di raffinamento al testo fornito:
            {instructions}
            
            === PATTERN ESEMPIO ===
            {cached_result['pattern']}
            
            === DOCUMENTO ATTUALE ===
            {content}
            """
            
            draft = await self._call_model(writer_input, self.writer_prompt)
            
            if progress_callback:
                progress_callback(0.9, "Cached pattern applied successfully")
            
            # Return with cached feedback but mark as from cache
            return {
                "draft": draft,
                "feedback": cached_result["feedback"],
                "iterations": 1,  # Only one iteration when using cache
                "from_cache": True
            }
            
        # Normal processing if no cache hit
        draft = ""
        feedback = {"score": 0, "suggestions": []}
        
        # Analyze content to detect sections and structure
        content_lines = content.split('\n')
        content_word_count = len(' '.join(content_lines).split())
        has_sections = any(line.strip().startswith('#') for line in content_lines)
        
        if progress_callback:
            progress_callback(0.1, "Preparing refinement strategy")
        
        # Optimize references - only use 2 examples for refinement to save tokens
        subset_count = min(2, len(self.reference_examples))
        selected_examples = random.sample(self.reference_examples, subset_count)
        style_examples = "\n".join([
            f"=== ESEMPIO {i+1} ===\nOutput:\n{ex['messages'][1]['content']}"
            for i, ex in enumerate(selected_examples)
        ])
        
        # Refinement usually needs fewer iterations
        max_refinement_loops = 2
        
        # Create a compressed version of the brand guide to save tokens
        compressed_brand_guide = "\n".join([
            line for line in self.brand_guide.split('\n')
            if line.strip() and not line.strip().startswith('#')
        ])
        
        for i in range(max_refinement_loops):
            logger.info(f"Starting refinement iteration {i + 1}/{max_refinement_loops}")
            
            # Report progress at each iteration
            if progress_callback:
                iteration_progress = 0.1 + (i / max_refinement_loops) * 0.7
                progress_callback(iteration_progress, f"Refinement iteration {i + 1}/{max_refinement_loops}")
            
            # Optimize prompt length based on content size
            if content_word_count > 1000:
                # For larger documents, focus only on the required information
                writer_input = f"""
                MODIFICA REPORT: Segui precisamente queste istruzioni per migliorare il report.
                
                STILE RICHIESTO: Formale, chiaro, professionale. Mantieni la struttura attuale.
                
                ISTRUZIONI: {instructions}
                
                DOCUMENTO:
                {content}
                """
            else:
                # For smaller documents, include more context
                writer_input = f"""
                === GUIDA STILE ===
                {compressed_brand_guide}

                === ISTRUZIONI ===
                {instructions}
                
                === DOCUMENTO ATTUALE ===
                {content}
                
                IMPORTANTE: Implementa le modifiche richieste mantenendo struttura e informazioni esistenti.
                """
            
            if progress_callback:
                progress_callback(iteration_progress + 0.15, "Generating refined content")
            
            draft = await self._call_model(writer_input, self.writer_prompt)
            
            if progress_callback:
                progress_callback(iteration_progress + 0.25, "Evaluating refinement quality")
            
            # Optimized reviewer prompt
            reviewer_input = f"""
            === REVISIONE ===
            Valuta queste modifiche:
            
            ISTRUZIONI: {instructions}
            
            TESTO MODIFICATO:
            {draft}
            
            Rispondi SOLO con un JSON nel formato: {{"score": float, "suggestions": []}}
            Score: 0-1 (0.9+ se le modifiche rispettano perfettamente le istruzioni)
            """
            
            review_result = await self._call_model(reviewer_input, self.reviewer_prompt)
            
            try:
                feedback = json.loads(review_result)
                logger.info(f"Feedback score: {feedback['score']}, suggestions: {len(feedback['suggestions'])}")
            except json.JSONDecodeError:
                logger.warning("Failed to parse reviewer feedback JSON, retrying with explicit JSON instruction")
                review_result = await self._call_model(
                    reviewer_input + "\n\nIMPORTANTE: RISPONDI SOLO CON JSON VALIDO {\"score\": 0.X, \"suggestions\": []}",
                    self.reviewer_prompt
                )
                try:
                    feedback = json.loads(review_result)
                except json.JSONDecodeError:
                    feedback = {"score": 0, "suggestions": ["Errore nel formato del feedback"]}
                    logger.error("Failed to parse reviewer feedback JSON even after retry")
            
            # Exit early if quality is high enough to save resources
            if feedback["score"] > 0.8:
                logger.info(f"Quality threshold met at refinement iteration {i + 1}")
                break
        
        if progress_callback:
            progress_callback(0.85, "Finalizing refinement results")
        
        # Store successful refinements in cache if they meet quality threshold
        if feedback["score"] > 0.8 and len(instructions.split()) < 20:
            # Extract a pattern from the refinement for future use
            pattern = f"""
            PRIMA:
            {content[:min(500, len(content))]}
            ...
            
            DOPO:
            {draft[:min(500, len(draft))]}
            ...
            """
            
            # Store in cache
            self.refinement_cache[cache_key] = {
                "pattern": pattern,
                "feedback": feedback,
                "last_used": time.time()
            }
            
            # Prune cache if it exceeds maximum size
            if len(self.refinement_cache) > self.cache_max_size:
                # Remove oldest entries based on last_used timestamp
                oldest = sorted(self.refinement_cache.items(), key=lambda x: x[1]["last_used"])
                for key, _ in oldest[:len(self.refinement_cache) - self.cache_max_size]:
                    del self.refinement_cache[key]
                    
            logger.info(f"Added refinement pattern to cache (hash: {instruction_hash[:8]})")
        
        if progress_callback:
            progress_callback(1.0, "Refinement completed")
        
        return {
            "draft": draft,
            "feedback": feedback,
            "iterations": i + 1
        } 