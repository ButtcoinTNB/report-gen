import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from config import settings
from pydantic import UUID4
from utils.error_handler import logger
from utils.file_processor import FileProcessor
from utils.supabase_helper import supabase_client_context


# Custom exception classes for AI service
class AIServiceError(Exception):
    """Base exception for all AI service errors"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        original_exception: Optional[Exception] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.original_exception = original_exception
        super().__init__(self.message)


class AIConnectionError(AIServiceError):
    """Raised when there's a connection error with the AI provider"""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(
            message, status_code=503, original_exception=original_exception
        )


class AITimeoutError(AIServiceError):
    """Raised when an AI request times out"""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(
            message, status_code=504, original_exception=original_exception
        )


class AIResponseError(AIServiceError):
    """Raised when the AI provider returns an error response"""

    def __init__(
        self,
        message: str,
        status_code: int,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(
            message, status_code=status_code, original_exception=original_exception
        )


class AIParsingError(AIServiceError):
    """Raised when there's an error parsing the AI response"""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(
            message, status_code=422, original_exception=original_exception
        )


async def call_openrouter_api(
    messages: List[Dict[str, str]],
    model: str = None,
    max_retries: int = 3,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    Call the OpenRouter API with retry logic.

    Args:
        messages: List of message objects for the API
        model: Model to use (defaults to settings.DEFAULT_MODEL)
        max_retries: Maximum number of retry attempts
        timeout: Timeout in seconds for the API call

    Returns:
        API response as a dictionary

    Raises:
        AIConnectionError: When there's a network connection error
        AITimeoutError: When the request times out
        AIResponseError: When the AI provider returns an error response
        AIServiceError: For other AI service errors
    """
    if model is None:
        model = settings.DEFAULT_MODEL

    # Define the operation to retry
    async def api_call_operation():
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.OPENROUTER_API_ENDPOINT,
                headers={
                    "Authorization": "Bearer " + settings.OPENROUTER_API_KEY,
                    "Content-Type": "application/json",
                    "HTTP-Referer": settings.APP_DOMAIN,
                    "X-Title": settings.APP_NAME,
                },
                json={"model": model, "messages": messages},
                timeout=timeout,
            )

            # Check for successful status code
            response.raise_for_status()

            return response.json()

    # Retry exceptions specific to network issues
    retry_exceptions = (
        httpx.ConnectError,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.ConnectTimeout,
        httpx.ReadError,
        asyncio.TimeoutError,
    )

    # Implement retry with exponential backoff
    for attempt in range(max_retries):
        try:
            # Execute the API call
            return await api_call_operation()
        except retry_exceptions as e:
            # Log the error
            logger.warning(
                f"API call failed (attempt {attempt+1}/{max_retries}): {str(e)}"
            )

            if attempt < max_retries - 1:
                # Calculate backoff time: 2^attempt * 1 second (1, 2, 4, 8, ...)
                backoff_time = min(2**attempt, 10)  # Cap at 10 seconds
                logger.info(f"Retrying in {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
            else:
                # All retries exhausted
                raise AIConnectionError(
                    f"Failed to connect to AI service after {max_retries} attempts: {str(e)}",
                    original_exception=e,
                )
        except httpx.HTTPStatusError as e:
            # Handle specific HTTP errors
            if e.response.status_code == 429:
                logger.warning("AI provider rate limit exceeded")
                if attempt < max_retries - 1:
                    backoff_time = min(
                        2**attempt * 2, 30
                    )  # Longer backoff for rate limits
                    logger.info(f"Retrying in {backoff_time} seconds...")
                    await asyncio.sleep(backoff_time)
                else:
                    raise AIResponseError(
                        "AI service rate limit exceeded",
                        status_code=429,
                        original_exception=e,
                    )
            elif e.response.status_code >= 500:
                # Server errors
                logger.error(f"AI provider server error: {e.response.status_code}")
                if attempt < max_retries - 1:
                    backoff_time = min(2**attempt, 10)
                    logger.info(f"Retrying in {backoff_time} seconds...")
                    await asyncio.sleep(backoff_time)
                else:
                    raise AIResponseError(
                        f"AI service error: {e.response.status_code}",
                        status_code=e.response.status_code,
                        original_exception=e,
                    )
            else:
                # Other HTTP errors (400, 401, 403, etc.)
                logger.error(
                    f"API call failed with status {e.response.status_code}: {str(e)}"
                )
                raise AIResponseError(
                    f"AI request failed: {e.response.status_code} - {str(e)}",
                    status_code=e.response.status_code,
                    original_exception=e,
                )
        except json.JSONDecodeError as e:
            # Handle JSON parsing errors
            logger.error(f"Failed to parse AI response: {str(e)}")
            raise AIParsingError(
                f"Failed to parse AI response: {str(e)}", original_exception=e
            )
        except Exception as e:
            # Handle other unexpected errors
            logger.error(f"Unexpected error in AI request: {str(e)}")
            raise AIServiceError(
                f"Unexpected error in AI request: {str(e)}", original_exception=e
            )

    # This should not be reached due to the exception handling above
    raise AIServiceError("All API call attempts failed with no specific error")


async def extract_template_variables(
    content: str, additional_info: str = ""
) -> Dict[str, Any]:
    """
    Extract template variables from document content and additional info.

    Args:
        content: Text content to analyze
        additional_info: Additional information provided by user

    Returns:
        Dictionary containing extracted variables

    Raises:
        AIParsingError: When there's an error parsing the AI response
        AIServiceError: For other AI service errors
    """
    try:
        messages = [
            {
                "role": "system",
                "content": "You are an expert at extracting structured information from insurance documents.",
            },
            {
                "role": "user",
                "content": f"Extract key variables from this content:\n\n{content}\n\nAdditional info:\n{additional_info}",
            },
        ]

        response = await call_openrouter_api(messages)

        try:
            return json.loads(response["choices"][0]["message"]["content"])
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise AIParsingError(
                f"Failed to parse AI response: {str(e)}", original_exception=e
            )

    except (AIConnectionError, AITimeoutError, AIResponseError):
        # Re-raise specific AI errors
        raise
    except AIParsingError:
        # Re-raise parsing errors
        raise
    except Exception as e:
        # Convert generic exceptions to AIServiceError
        raise AIServiceError(
            f"Error in variable extraction: {str(e)}", original_exception=e
        )


class StyleAnalysisCache:
    def __init__(self):
        self._cache = {}
        self._cache_dir = Path("cache")
        self._cache_file = self._cache_dir / "style_analysis_cache.json"
        self._cache_dir.mkdir(exist_ok=True)
        self._load_cache()

    def _load_cache(self):
        """Load cached style analysis from disk."""
        try:
            if self._cache_file.exists():
                # Use FileProcessor for reading the cache file
                cache_content = FileProcessor.extract_text(self._cache_file)
                self._cache = json.loads(cache_content)
        except Exception as e:
            logger.error("Error loading style analysis cache: " + str(e))
            self._cache = {}

    def _save_cache(self):
        """Save cache to disk."""
        try:
            # Create parent directory if it doesn't exist
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)

            # Convert cache to JSON string and write to file
            cache_json = json.dumps(self._cache, ensure_ascii=False, indent=2)

            with open(self._cache_file, "w", encoding="utf-8") as f:
                f.write(cache_json)
        except Exception as e:
            logger.error("Error saving style analysis cache: " + str(e))

    def get_cache_key(self, reference_paths: List[str]) -> str:
        """Generate a cache key based on file paths and modification times."""
        key_parts = []
        for path in sorted(reference_paths):
            try:
                # Use FileProcessor to get file info
                file_info = FileProcessor.get_file_info(path)
                key_parts.append(path + ":" + str(file_info.get("mtime", "")))
            except Exception:
                key_parts.append(path)
        return "|".join(key_parts)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached style analysis if available."""
        return self._cache.get(key)

    def set(self, key: str, analysis: Dict[str, Any]):
        """Cache style analysis and save to disk."""
        self._cache[key] = analysis
        self._save_cache()


# Create singleton instance
style_cache = StyleAnalysisCache()


async def analyze_reference_reports(reference_paths: List[str]) -> Dict[str, Any]:
    """
    Analyze reference reports to extract style patterns and linguistic features.

    Args:
        reference_paths: List of paths to reference report files

    Returns:
        Dictionary with analysis results, including tone, style, terminology, and structure
    """
    try:
        logger.info(f"Analyzing {len(reference_paths)} reference reports for style")

        # Check cache first
        cache = StyleAnalysisCache()
        cache_key = cache.get_cache_key(reference_paths)
        cached_analysis = cache.get(cache_key)

        if cached_analysis:
            logger.info("Using cached style analysis")
            return cached_analysis

        logger.info("No cached analysis found, generating new analysis")

        # Combine all reference reports
        combined_text = ""
        reference_texts = []  # Create a list to store the extracted texts
        for path in reference_paths:
            # Use FileProcessor to extract text from files
            text = FileProcessor.extract_text(path)
            combined_text += text + "\n\n"
            reference_texts.append(text)  # Add each text to the list

        # Create prompt for analyzing style and format
        # Avoid f-strings entirely for this section - concatenate parts safely
        joined_reports = "\n\n".join(
            [
                "=== Report " + str(i + 1) + " ===\n" + text
                for i, text in enumerate(reference_texts)
            ]
        )

        analysis_prompt = (
            "Sei un esperto analista di documenti assicurativi. Analizza questi report di riferimento "
            "per identificare il formato, lo stile e il tono di voce comuni. "
            "NON analizzare il contenuto specifico, ma solo gli elementi stilistici e strutturali.\n\n"
            "REPORT DI RIFERIMENTO:\n\n" + joined_reports + "\n\n"
            "Analizza e fornisci un JSON con:\n"
            "1. STRUTTURA: Schema comune delle sezioni e sottosezioni, inclusi titoli esatti e ordine\n"
            "2. STILE: Caratteristiche dello stile di scrittura (formalità, lunghezza frasi, uso di elenchi puntati)\n"
            "3. TONO: Tono di voce utilizzato (professionale, tecnico, oggettivo) con esempi specifici\n"
            "4. FORMATTAZIONE: Modelli esatti per date (GG/MM/AAAA), importi (€ X.XXX,XX), riferimenti (Rif: XXXXX)\n"
            "5. FRASI_COMUNI: Frasi standard utilizzate in sezioni specifiche (apertura, chiusura, transizioni)\n\n"
            "Formato JSON atteso:\n"
            "{\n"
            '  "struttura": {\n'
            '    "sezioni": ["Intestazione", "Riferimenti", "Dinamica", "Danni", "Conclusioni"],\n'
            '    "ordine": ["intestazione", "riferimenti", "dinamica", "danni", "conclusioni"],\n'
            '    "elementi_richiesti": ["data", "riferimenti_pratica", "importi", "firme"]\n'
            "  },\n"
            '  "stile": {\n'
            '    "livello_formalita": "alto/medio/basso",\n'
            '    "caratteristiche": ["frasi brevi/lunghe", "uso di tecnicismi", "struttura paragrafi"],\n'
            '    "pattern_sintattici": ["Si attesta che...", "Si è proceduto a..."]\n'
            "  },\n"
            '  "tono": {\n'
            '    "caratteristiche": ["professionale", "distaccato", "tecnico"],\n'
            '    "esempi": ["esempio frase 1", "esempio frase 2"]\n'
            "  },\n"
            '  "formattazione": {\n'
            '    "date": "GG/MM/AAAA",\n'
            '    "importi": "€ X.XXX,XX",\n'
            '    "riferimenti": "Rif: XXXXX"\n'
            "  },\n"
            '  "frasi_comuni": {\n'
            '    "apertura": ["frase apertura 1", "frase apertura 2"],\n'
            '    "chiusura": ["frase chiusura 1", "frase chiusura 2"],\n'
            '    "transizioni": ["inoltre", "pertanto", "in conclusione"]\n'
            "  }\n"
            "}"
        )

        # Get style analysis from AI
        result = await call_openrouter_api(
            messages=[
                {
                    "role": "system",
                    "content": "Sei un esperto analista di stile e formato di documenti assicurativi. "
                    "Analizza i documenti di riferimento per estrarre pattern di stile precisi, "
                    "NON contenuto specifico. Fornisci esempi concreti e pattern esatti.",
                },
                {"role": "user", "content": analysis_prompt},
            ],
            timeout=60.0,
        )

        if not (
            result
            and "choices" in result
            and len(result["choices"]) > 0
            and "message" in result["choices"][0]
            and "content" in result["choices"][0]["message"]
        ):
            raise ValueError("Errore nell'analisi dei report di riferimento")

        # Extract and validate the style guide
        style_guide = json.loads(
            re.search(r"\{[\s\S]*\}", result["choices"][0]["message"]["content"]).group(
                0
            )
        )

        # Store style guide values in separate variables to avoid f-string issues
        style_guide_json = json.dumps(style_guide, indent=2, ensure_ascii=False)

        # Create a prompt template for report generation using standard string formatting
        # to avoid any f-string backslash issues
        prompt_template = (
            "GUIDA DI STILE E FORMATO:\n"
            "{style_guide_json}\n\n"
            "ISTRUZIONI PRECISE:\n"
            "1. Usa ESATTAMENTE la struttura delle sezioni fornita, nell'ordine specificato\n"
            "2. Mantieni il livello di formalità indicato ({livello_formalita})\n"
            "3. Utilizza le frasi comuni fornite per apertura, chiusura e transizioni\n"
            "4. Segui ESATTAMENTE i pattern di formattazione per:\n"
            "   - Date: {date}\n"
            "   - Importi: {importi}\n"
            "   - Riferimenti: {riferimenti}\n"
            "5. Usa i pattern sintattici e il tono forniti negli esempi\n\n"
            "CONTENUTO DA ELABORARE:\n"
            "{content}\n\n"
            "INFORMAZIONI AGGIUNTIVE:\n"
            "{additional_info}\n\n"
            "Genera un report che segue ESATTAMENTE questo stile e formato, utilizzando il contenuto fornito."
        )

        analysis_result = {
            "style_guide": style_guide,
            "prompt_template": prompt_template,
            "style_guide_json": style_guide_json,  # Store for later use
        }

        # Cache the result
        style_cache.set(cache_key, analysis_result)
        logger.info("Cached new style analysis")

        return analysis_result

    except Exception as e:
        logger.error("Error analyzing reference reports: " + str(e))
        raise ValueError("Impossibile analizzare i report di riferimento: " + str(e))


async def generate_report_text(
    document_paths: List[str],
    additional_info: str = "",
    template_id: Optional[UUID4] = None,
) -> Dict[str, Any]:
    """
    Generate report text from document paths using OpenRouter API.

    Args:
        document_paths: List of paths to documents to use for generation
        additional_info: Additional information to include in the prompt
        template_id: Optional ID of template to use for formatting

    Returns:
        Dictionary containing the generated report text and variables

    Raises:
        AIConnectionError: When there's a network connection error to the AI service
        AITimeoutError: When the request to the AI service times out
        AIResponseError: When the AI service returns an error response
        AIParsingError: When there's an error parsing the AI response
        AIServiceError: For other AI service errors
    """
    try:
        # Extract variables from document
        variables = {}
        for path in document_paths:
            with open(path, "r") as f:
                content = f.read()
                extracted = await extract_template_variables(content, additional_info)
                variables.update(extracted)

        # Get template content if needed
        template_content = None
        if template_id:
            async with supabase_client_context() as supabase:
                response = await supabase.table("templates") \
                    .select("content") \
                    .eq("template_id", str(template_id)) \
                    .execute()
                if response.data:
                    template_content = response.data[0]["content"]

        # Generate report text
        messages = [
            {"role": "system", "content": "You are an expert insurance report writer."},
            {
                "role": "user",
                "content": f"Generate a report based on these variables:\n{json.dumps(variables, indent=2)}",
            },
        ]

        if template_content:
            messages.append(
                {
                    "role": "user",
                    "content": f"Use this template format:\n{template_content}",
                }
            )

        response = await call_openrouter_api(messages)

        try:
            content = response["choices"][0]["message"]["content"]
            return {"content": content, "variables": variables}
        except (KeyError, IndexError) as e:
            raise AIParsingError(
                f"Failed to parse AI response: {str(e)}", original_exception=e
            )

    except (AIConnectionError, AITimeoutError, AIResponseError, AIParsingError) as e:
        # Re-raise specific AI errors
        logger.error(f"AI service error in generate_report_text: {e.message}")
        raise
    except Exception as e:
        # Convert other exceptions to AIServiceError
        logger.error(f"Error in generate_report_text: {str(e)}")
        raise AIServiceError(
            f"Error generating report text: {str(e)}", original_exception=e
        )


async def refine_report_text(
    report_id: UUID4, instructions: str, current_content: str
) -> Dict[str, Any]:
    """
    Refine an existing report based on user instructions.

    Args:
        report_id: UUID of the report to refine
        instructions: User instructions for refinement
        current_content: Current content of the report

    Returns:
        Dictionary containing the refined report text

    Raises:
        AIConnectionError: When there's a network connection error to the AI service
        AITimeoutError: When the request to the AI service times out
        AIResponseError: When the AI service returns an error response
        AIParsingError: When there's an error parsing the AI response
        AIServiceError: For other AI service errors
    """
    try:
        messages = [
            {"role": "system", "content": "You are an expert insurance report writer."},
            {
                "role": "user",
                "content": f"Here is the current report:\n\n{current_content}\n\nPlease refine it based on these instructions:\n{instructions}",
            },
        ]

        # Call the OpenRouter API
        response = await call_openrouter_api(messages)

        try:
            content = response["choices"][0]["message"]["content"]
            return {"content": content}
        except (KeyError, IndexError) as e:
            raise AIParsingError(
                f"Failed to parse AI response during report refinement: {str(e)}",
                original_exception=e,
            )

    except (AIConnectionError, AITimeoutError, AIResponseError, AIParsingError) as e:
        # Re-raise specific AI errors
        logger.error(f"AI service error in refine_report_text: {e.message}")
        raise
    except Exception as e:
        # Convert other exceptions to AIServiceError
        logger.error(f"Error in refine_report_text: {str(e)}")
        raise AIServiceError(
            f"Error refining report text: {str(e)}", original_exception=e
        )


async def analyze_template(template_id: UUID4) -> Dict[str, Any]:
    """
    Analyze a template to extract its structure and formatting.

    Args:
        template_id: UUID of the template to analyze

    Returns:
        Dictionary containing the template structure and formatting

    Raises:
        AIConnectionError: When there's a network connection error to the AI service
        AITimeoutError: When the request to the AI service times out
        AIResponseError: When the AI service returns an error response
        AIParsingError: When there's an error parsing the AI response
        AIServiceError: For other AI service errors
    """
    try:
        # Get template content
        async with supabase_client_context() as supabase:
            response = await supabase.table("templates") \
                .select("content") \
                .eq("template_id", str(template_id)) \
                .execute()

            if not response.data:
                raise AIServiceError(f"Template with ID {template_id} not found")

            template_content = response.data[0]["content"]

        # Analyze template
        messages = [
            {"role": "system", "content": "You are an expert document analyzer."},
            {
                "role": "user",
                "content": f"Analyze this template and identify its structure, sections, and any placeholders:\n\n{template_content}\n\nProvide a JSON response with keys 'structure', 'sections', and 'placeholders'.",
            },
        ]

        response = await call_openrouter_api(messages)

        try:
            content = response["choices"][0]["message"]["content"]

            # Try to parse as JSON, if it's not valid JSON, return as text
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # If not valid JSON, return as text
                return {"analysis": content}

        except (KeyError, IndexError) as e:
            raise AIParsingError(
                f"Failed to parse AI response during template analysis: {str(e)}",
                original_exception=e,
            )

    except (AIConnectionError, AITimeoutError, AIResponseError, AIParsingError) as e:
        # Re-raise specific AI errors
        logger.error(f"AI service error in analyze_template: {e.message}")
        raise
    except Exception as e:
        # Convert other exceptions to AIServiceError
        logger.error(f"Error in analyze_template: {str(e)}")
        raise AIServiceError(
            f"Error analyzing template: {str(e)}", original_exception=e
        )


async def get_report_files(report_id: UUID4) -> List[str]:
    """
    Get all files associated with a report.

    Args:
        report_id: The UUID of the report

    Returns:
        List of file paths

    Raises:
        AIServiceError: When there's an error retrieving the files
    """
    try:
        async with supabase_client_context() as supabase:
            response = await supabase.table("reports") \
                .select("document_ids") \
                .eq("report_id", str(report_id)) \
                .execute()

            if not response.data:
                raise AIServiceError(f"Report with ID {report_id} not found")

            document_ids = response.data[0].get("document_ids", [])
            if not document_ids:
                return []

            paths = []
            for doc_id in document_ids:
                file_response = await supabase.table("files") \
                    .select("storage_path") \
                    .eq("file_id", doc_id) \
                    .execute()

                if file_response.data:
                    paths.append(file_response.data[0]["storage_path"])

            return paths

    except Exception as e:
        logger.error(f"Error getting report files: {str(e)}")
        raise AIServiceError(
            f"Error retrieving report files: {str(e)}", original_exception=e
        )


async def get_template_content(template_id: UUID4) -> str:
    """
    Get the content of a template.

    Args:
        template_id: The UUID of the template

    Returns:
        Template content

    Raises:
        AIServiceError: When there's an error retrieving the template
    """
    try:
        async with supabase_client_context() as supabase:
            response = await supabase.table("templates") \
                .select("content") \
                .eq("template_id", str(template_id)) \
                .execute()

            if not response.data:
                raise AIServiceError(f"Template with ID {template_id} not found")

            return response.data[0]["content"]

    except Exception as e:
        logger.error(f"Error getting template content: {str(e)}")
        raise AIServiceError(
            f"Error retrieving template content: {str(e)}", original_exception=e
        )
