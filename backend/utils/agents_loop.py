import os
import json
import httpx
import random
from typing import Dict, List, Tuple, Optional, Callable
from pathlib import Path
import logging
import asyncio
import time
from hashlib import md5
from .api_rate_limiter import rate_limiter, rate_limited

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Safe defaults for environment variables
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")  # Empty string as fallback
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://report-gen-liard.vercel.app/")
APP_NAME = os.getenv("APP_NAME", "Generatore di Perizie")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "google/gemini-2.0-pro-exp-02-05:free")

class AIAgentLoop:
    def __init__(self, max_loops: int = 3, progress_callback: Optional[Callable] = None):
        self.max_loops = max_loops
        self.brand_guide = self._load_brand_guide()
        self.reference_examples = self._load_references()
        self.writer_prompt, self.reviewer_prompt = self._load_prompts()
        # Cache for similar refinements
        self.refinement_cache = {}
        self.cache_max_size = 50  # Maximum cache entries
        # Log setup with TTL management
        self.logs = []
        self.max_logs = 1000  # Maximum logs to keep in memory
        self.last_log_cleanup = time.time()
        self.log_cleanup_interval = 60  # Cleanup logs every 60 seconds
        # Progress callback for real-time updates
        self.progress_callback = progress_callback
        # Network resilience settings
        self.network_backoff_factor = 1.5  # Exponential backoff factor
        self.max_retries = 5  # Maximum retry attempts for transient errors
        self.is_cancelling = False  # Flag to track cancellation state
        
    def log_event(self, event_type: str, details: Dict) -> None:
        """Log an event with timestamp for debugging and monitoring"""
        current_time = time.time()
        
        # Check if we need to clean up old logs
        if current_time - self.last_log_cleanup > self.log_cleanup_interval:
            self._cleanup_logs()
            self.last_log_cleanup = current_time
        
        event = {
            "timestamp": current_time,
            "type": event_type,
            **details
        }
        self.logs.append(event)
        logger.info(f"Agent event: {event_type} - {details.get('message', '')}")
    
    def _cleanup_logs(self) -> None:
        """Cleanup old logs to prevent memory growth"""
        if len(self.logs) > self.max_logs:
            # Keep only the most recent logs
            self.logs = self.logs[-self.max_logs:]
            logger.info(f"Cleaned up logs, keeping most recent {self.max_logs} entries")
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        """Get the most recent logs for debugging or display"""
        return self.logs[-limit:] if self.logs else []
    
    def cancel_processing(self) -> None:
        """Mark current processing for cancellation"""
        self.is_cancelling = True
        self.log_event("cancel_requested", {"message": "Processing cancellation requested"})
        
    def _update_progress(self, progress: float, message: str, stage: str = None, estimated_time_remaining: float = None) -> None:
        """Update progress via callback if provided"""
        if self.progress_callback and not self.is_cancelling:
            callback_data = {"progress": progress, "message": message}
            if stage:
                callback_data["stage"] = stage
            if estimated_time_remaining is not None:
                callback_data["estimatedTimeRemaining"] = estimated_time_remaining
            self.progress_callback(**callback_data)
    
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
        
    async def _call_model(self, prompt: str, system_prompt: str, retries: int = None) -> str:
        """Make an API call to the configured model via OpenRouter with rate limiting and retries."""
        if retries is None:
            retries = self.max_retries
            
        if not OPENROUTER_API_KEY:
            self.log_event("error", {"message": "API key not configured", "detail": "OPENROUTER_API_KEY environment variable is not set"})
            raise Exception("OPENROUTER_API_KEY environment variable is not set")
            
        last_error = None
        start_time = time.time()
        
        # Get a token from the rate limiter before proceeding
        allowed = await rate_limiter.wait_for_token("openrouter", tokens=1.0, max_wait=10.0)
        if not allowed:
            self.log_event("rate_limit", {"message": "Rate limit exceeded, request dropped"})
            raise Exception("Rate limit exceeded for OpenRouter API, please try again later")
        
        for attempt in range(retries):
            if self.is_cancelling:
                self.log_event("request_cancelled", {"message": "Model call cancelled"})
                raise Exception("Operation cancelled by user")
                
            try:
                self.log_event("api_call", {"attempt": attempt + 1, "model": DEFAULT_MODEL})
                
                async with httpx.AsyncClient() as client:
                    # Calculate timeout with backoff
                    timeout = 30.0 * (1 + (attempt * 0.5))  # Increase timeout with each retry
                    
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
                        timeout=timeout
                    )
                    
                    if response.status_code == 429:
                        self.log_event("rate_limit", {"attempt": attempt + 1, "delay": self.network_backoff_factor ** attempt})
                        logger.warning(f"Rate limit hit on attempt {attempt + 1}, retrying...")
                        # Update rate limiter with this information
                        rate_limiter.get_limiter("openrouter").metrics["throttled_requests"] += 1
                        await asyncio.sleep(self.network_backoff_factor ** attempt)  # Exponential backoff
                        continue
                        
                    if response.status_code != 200:
                        self.log_event("api_error", {"status": response.status_code, "response": response.text})
                        logger.error(f"API Error: {response.status_code} - {response.text}")
                        
                        # Check for recoverable errors
                        if response.status_code in [502, 503, 504]:  # Gateway errors, likely transient
                            if attempt < retries - 1:
                                delay = self.network_backoff_factor ** attempt
                                logger.info(f"Transient error, retrying in {delay:.2f} seconds...")
                                await asyncio.sleep(delay)
                                continue
                        
                        raise Exception(f"API call failed with status {response.status_code}")
                    
                    response_data = response.json()
                    response_time = time.time() - start_time
                    self.log_event("api_success", {"response_time": response_time, "tokens": response_data.get("usage", {}).get("total_tokens", 0)})
                    
                    return response_data["choices"][0]["message"]["content"]
                    
            except (httpx.NetworkError, httpx.TimeoutException, httpx.ConnectError) as e:
                error_type = type(e).__name__
                self.log_event("network_error", {"attempt": attempt + 1, "error": str(e), "type": error_type})
                logger.error(f"Network error ({error_type}) on attempt {attempt + 1}: {e}")
                
                if attempt < retries - 1:
                    # Use exponential backoff for network errors
                    delay = self.network_backoff_factor ** attempt
                    logger.info(f"Retrying after network error in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
                    continue
                    
                last_error = e
                raise Exception(f"Network error after {retries} attempts: {str(e)}")
                
            except Exception as e:
                last_error = e
                self.log_event("api_exception", {"attempt": attempt + 1, "error": str(e)})
                logger.error(f"Error calling model (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    # Use fixed delay for other errors
                    await asyncio.sleep(1)
                    continue
                raise last_error
            
    def _evaluate_quality(self, feedback: Dict) -> Tuple[bool, str]:
        """
        Evaluate the quality of the report based on feedback
        Returns (meets_criteria, reason)
        """
        # Basic quality check based on score and suggestions
        if feedback["score"] > 0.9:
            return True, "High quality score"
        
        if feedback["score"] > 0.8 and len(feedback["suggestions"]) <= 1:
            return True, "Good quality with minimal suggestions"
        
        if len(feedback["suggestions"]) > 5:
            return False, "Too many improvement suggestions"
            
        # More detailed quality checks can be added here
        return False, "Quality threshold not met"
        
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
        estimated_completion = None
        iteration_times = []
        self.is_cancelling = False  # Reset cancellation flag
        
        try:
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
            
            # Initialize process
            self.log_event("process_start", {"max_iterations": self.max_loops, "content_length": len(user_content)})
            self._update_progress(5, "Inizializzazione del processo di generazione", "initializing")
            
            for i in range(self.max_loops):
                if self.is_cancelling:
                    self.log_event("process_cancelled", {"iteration": i, "message": "Process cancelled by user"})
                    raise Exception("Process cancelled by user")
                    
                iteration_start = time.time()
                
                # Calculate overall progress for this iteration (distribute 90% across iterations)
                base_progress = 10 + (i / self.max_loops) * 80
                
                logger.info(f"Starting iteration {i + 1}/{self.max_loops}")
                self.log_event("iteration_start", {"iteration": i + 1, "total": self.max_loops})
                
                # Update progress - Writer phase
                self._update_progress(
                    base_progress, 
                    f"L'agente di scrittura sta creando il report (iterazione {i+1}/{self.max_loops})",
                    "writing"
                )
                
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
                
                self.log_event("writer_start", {"iteration": i + 1})
                writer_start = time.time()
                draft = await self._call_model(writer_input, self.writer_prompt)
                writer_duration = time.time() - writer_start
                self.log_event("writer_complete", {
                    "iteration": i + 1, 
                    "duration": writer_duration,
                    "output_length": len(draft)
                })
                
                if self.is_cancelling:
                    self.log_event("process_cancelled", {"iteration": i, "phase": "after_writing", "message": "Process cancelled by user"})
                    raise Exception("Process cancelled by user")
                
                # Update progress - Reviewer phase
                self._update_progress(
                    base_progress + 10, 
                    f"L'agente di revisione sta analizzando il report (iterazione {i+1}/{self.max_loops})",
                    "reviewing"
                )
                
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
                
                self.log_event("reviewer_start", {"iteration": i + 1})
                reviewer_start = time.time()
                review_result = await self._call_model(reviewer_input, self.reviewer_prompt)
                reviewer_duration = time.time() - reviewer_start
                
                try:
                    feedback = json.loads(review_result)
                    self.log_event("reviewer_complete", {
                        "iteration": i + 1,
                        "duration": reviewer_duration,
                        "score": feedback["score"],
                        "suggestions_count": len(feedback["suggestions"])
                    })
                    logger.info(f"Feedback score: {feedback['score']}, suggestions: {len(feedback['suggestions'])}")
                except json.JSONDecodeError:
                    self.log_event("reviewer_parse_error", {"iteration": i + 1})
                    logger.warning("Failed to parse reviewer feedback JSON, retrying with explicit JSON instruction")
                    # Retry with explicit JSON instruction
                    review_result = await self._call_model(
                        reviewer_input + "\n\nIMPORTANTE: Rispondi SOLO con un oggetto JSON valido nel formato specificato.",
                        self.reviewer_prompt
                    )
                    try:
                        feedback = json.loads(review_result)
                        self.log_event("reviewer_retry_success", {"score": feedback["score"]})
                    except json.JSONDecodeError:
                        self.log_event("reviewer_retry_failed", {})
                        feedback = {"score": 0, "suggestions": ["Errore nel formato del feedback"]}
                        logger.error("Failed to parse reviewer feedback JSON even after retry")
                
                # Track iteration time for estimation
                iteration_time = time.time() - iteration_start
                iteration_times.append(iteration_time)
                
                # Calculate estimated time remaining
                if len(iteration_times) > 0:
                    avg_iteration_time = sum(iteration_times) / len(iteration_times)
                    remaining_iterations = self.max_loops - (i + 1)
                    estimated_remaining_seconds = avg_iteration_time * remaining_iterations
                    estimated_completion = estimated_remaining_seconds
                    
                    # Update progress with time estimate
                    self._update_progress(
                        base_progress + 20,
                        f"Analisi completata per iterazione {i+1}/{self.max_loops}",
                        "reviewing",
                        estimated_time_remaining=estimated_remaining_seconds
                    )
                
                # Check quality criteria to determine if we should continue
                meets_criteria, reason = self._evaluate_quality(feedback)
                self.log_event("quality_check", {
                    "iteration": i + 1,
                    "meets_criteria": meets_criteria,
                    "reason": reason
                })
                    
                # Exit if quality is high enough
                if meets_criteria:
                    logger.info(f"Quality threshold met at iteration {i + 1}: {reason}")
                    break
                    
            # Process complete - update final progress
            if not self.is_cancelling:
                self._update_progress(100, "Generazione report completata", "complete")
                self.log_event("process_complete", {
                    "iterations_completed": i + 1,
                    "final_score": feedback["score"],
                    "total_duration": sum(iteration_times)
                })
                
            # Clean up logs at the end of processing
            self._cleanup_logs()
                    
            return {
                "draft": draft,
                "feedback": feedback,
                "iterations": i + 1
            }
        except Exception as e:
            self.log_event("process_error", {"error": str(e), "error_type": type(e).__name__})
            # Clean up logs even on error
            self._cleanup_logs()
            raise

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