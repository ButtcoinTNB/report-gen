import httpx
from typing import List, Dict, Any, Callable
import os
import asyncio
from config import settings
from utils.error_handler import handle_exception, logger, retry_operation
import re


async def call_openrouter_api(
    messages: List[Dict[str, str]],
    model: str = None,
    max_retries: int = 3,
    timeout: float = 30.0
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
    """
    if model is None:
        model = settings.DEFAULT_MODEL
    
    # Define the operation to retry
    async def api_call_operation():
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://insurance-report-generator.vercel.app",  # Your app domain
                    "X-Title": "Insurance Report Generator"  # Your app name
                },
                json={
                    "model": model,
                    "messages": messages
                },
                timeout=timeout
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
        asyncio.TimeoutError
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
                backoff_time = min(2 ** attempt, 10)  # Cap at 10 seconds
                logger.info(f"Retrying in {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
            else:
                # This was the last attempt
                handle_exception(
                    e, 
                    f"OpenRouter API call (after {max_retries} attempts)",
                    default_status_code=503
                )
        except httpx.HTTPStatusError as e:
            # Handle HTTP error responses (4xx, 5xx)
            error_detail = f"API returned {e.response.status_code}: {e.response.text}"
            logger.error(error_detail)
            handle_exception(
                Exception(error_detail),
                "OpenRouter API request",
                default_status_code=e.response.status_code
            )
        except Exception as e:
            # Handle unexpected errors
            handle_exception(e, "OpenRouter API request")
    
    # This should not be reached due to the exception handling above
    handle_exception(
        Exception("All API call attempts failed with no specific error"),
        "OpenRouter API call"
    )


async def generate_case_summary(document_paths: List[str]) -> Dict[str, str]:
    """
    Generate a very brief summary of case documents highlighting key findings.
    
    Args:
        document_paths: List of paths to the uploaded documents
        
    Returns:
        Dictionary with summary and key_facts
    """
    try:
        document_content = []
        
        # Extract text from documents
        for path in document_paths:
            try:
                with open(path, "r") as file:
                    try:
                        document_content.append(file.read())
                    except UnicodeDecodeError:
                        # If not a text file, add placeholder
                        document_content.append(f"[Non-text file: {os.path.basename(path)}]")
            except FileNotFoundError:
                logger.warning(f"Document not found: {path}")
            except Exception as e:
                logger.warning(f"Error reading document {path}: {str(e)}")
        
        if not document_content:
            return {
                "summary": "No readable content found in the provided documents.",
                "key_facts": []
            }
        
        # Combine all document content
        combined_content = "\n\n".join(document_content)
        
        # Create prompt for a very brief summary with strict instructions
        prompt = (
            "You are an insurance claims analyzer. Your task is to create an extremely brief summary "
            "(1-2 sentences) and extract key facts from the provided documents. Follow these strict rules:\n\n"
            "1. FACTS ONLY: Use ONLY information explicitly stated in the documents.\n"
            "2. NO INVENTION: Do not add any details not present in the documents.\n"
            "3. KEY INFORMATION: Focus on claim amount, property damage, injuries, policy details, "
            "and incident date if present in the documents.\n"
            "4. IF MISSING: If any key information is not in the documents, note it as 'not provided' "
            "rather than making assumptions.\n\n"
            f"DOCUMENT CONTENT:\n{combined_content}\n\n"
            "Provide your response in this format:\n"
            "SUMMARY: [A 1-2 sentence factual summary based ONLY on the provided documents]\n"
            "KEY_FACTS: [2-4 key points in bullet format with amounts, dates, and specifics ONLY from the documents]"
        )
        
        # Prepare messages for API call
        messages = [
            {
                "role": "system", 
                "content": "You are an insurance claims analyzer. Provide extremely concise, FACTUAL summaries and key facts only. Do not invent details not present in the documents."
            },
            {"role": "user", "content": prompt}
        ]
        
        # Call OpenRouter API with shorter timeout for better UX
        result = await call_openrouter_api(messages, timeout=15.0)
        
        # Extract the generated text
        if (
            result
            and "choices" in result
            and len(result["choices"]) > 0
            and "message" in result["choices"][0]
            and "content" in result["choices"][0]["message"]
        ):
            response_text = result["choices"][0]["message"]["content"]
            
            # Extract summary and key facts
            summary_match = re.search(r'SUMMARY:\s*(.+?)(?:\n|$)', response_text, re.DOTALL)
            summary = summary_match.group(1).strip() if summary_match else "Summary not available"
            
            # Extract key facts as a list
            key_facts_section = re.search(r'KEY_FACTS:\s*(.+?)(?:\n\n|$)', response_text, re.DOTALL)
            key_facts_text = key_facts_section.group(1).strip() if key_facts_section else ""
            
            # Convert bullet points to list items
            key_facts = []
            for line in key_facts_text.split('\n'):
                # Remove bullet point markers and clean up
                cleaned_line = re.sub(r'^[\s•\-\*]+', '', line).strip()
                if cleaned_line:
                    key_facts.append(cleaned_line)
            
            return {
                "summary": summary,
                "key_facts": key_facts
            }
        else:
            logger.error(f"Unexpected API response format: {result}")
            return {
                "summary": "Unable to generate summary from documents.",
                "key_facts": []
            }
                
    except Exception as e:
        logger.error(f"Error in generate_case_summary: {str(e)}")
        return {
            "summary": "Unable to generate case summary. An error occurred.",
            "key_facts": []
        }


async def generate_report_text(
    document_paths: List[str], template_id: int
) -> str:
    """
    Generate a report based on uploaded documents using OpenRouter API.
    
    Args:
        document_paths: List of paths to the uploaded documents
        template_id: ID of the template to use for formatting
        
    Returns:
        Generated report text
    """
    try:
        document_content = []
        
        # Extract text from documents
        for path in document_paths:
            try:
                with open(path, "r") as file:
                    try:
                        document_content.append(file.read())
                    except UnicodeDecodeError:
                        # If not a text file, add placeholder
                        document_content.append(f"[Non-text file: {os.path.basename(path)}]")
            except FileNotFoundError:
                logger.warning(f"Document not found: {path}")
            except Exception as e:
                logger.warning(f"Error reading document {path}: {str(e)}")
        
        if not document_content:
            return "Error: No readable content found in the provided documents."
        
        # Combine all document content
        combined_content = "\n\n".join(document_content)
        
        # Get reference templates from backend
        reference_content = ""
        
        # Define possible locations for reference reports
        possible_dirs = [
            os.path.join("backend", "reference_reports"),
            "reference_reports",
            os.path.join(settings.UPLOAD_DIR, "templates")
        ]
        
        # Find reference PDFs to use as format templates
        found_references = False
        for dir_path in possible_dirs:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                reference_files = [
                    os.path.join(dir_path, f) 
                    for f in os.listdir(dir_path) 
                    if f.lower().endswith(".pdf") 
                    or f.lower().endswith(".txt") 
                    or f.lower().endswith(".docx")
                ]
                
                if reference_files:
                    logger.info(f"Found {len(reference_files)} reference files in {dir_path}")
                    
                    # Use the first reference file (or ideally, use one that matches template_id)
                    try:
                        for ref_file in reference_files[:2]:  # Use up to 2 references
                            try:
                                with open(ref_file, "r") as f:
                                    file_content = f.read()
                                    if file_content.strip():
                                        reference_content += f"\n\n--- REFERENCE DOCUMENT: {os.path.basename(ref_file)} ---\n\n"
                                        reference_content += file_content
                                        found_references = True
                            except UnicodeDecodeError:
                                logger.warning(f"Cannot read binary file as reference: {ref_file}")
                            except Exception as e:
                                logger.warning(f"Error reading reference file {ref_file}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error processing reference files: {str(e)}")
                
                if found_references:
                    break

        # If no reference files were found, use a minimal structural outline
        if not reference_content:
            logger.warning("No reference templates found. Using minimal structure.")
            reference_content = (
                "INSURANCE REPORT STRUCTURE\n\n"
                "CLAIM INFORMATION:\n- Claim Number\n- Date of Loss\n- Insured Name\n- Policy Number\n\n"
                "CLAIM SUMMARY:\n[Brief description of what happened]\n\n"
                "COVERAGE DETAILS:\n[Policy coverage relevant to this claim]\n\n"
                "DAMAGE ASSESSMENT:\n[Details of the damages/injuries]\n\n"
                "INVESTIGATION FINDINGS:\n[Facts discovered during investigation]\n\n"
                "LIABILITY DETERMINATION:\n[Analysis of liability]\n\n"
                "RECOMMENDATIONS:\n[Settlement or action recommendations]"
            )
        
        # Create prompt with strict instructions about using reference only for format
        prompt = (
            "You are an insurance report writer. Generate a formal insurance "
            "report based ONLY on the case information provided. Follow these strict instructions:\n\n"
            "1. FORMAT & STRUCTURE: Use the reference documents ONLY for format, structure, and style.\n"
            "2. CONTENT: ALL content MUST come ONLY from the case information provided.\n"
            "3. NO HALLUCINATION: Do not invent ANY details not present in the case information.\n"
            "4. LANGUAGE: Use the same language as the case documents (English or Italian).\n\n"
            f"REFERENCE FORMAT (use ONLY for structure/style):\n{reference_content}\n\n"
            f"CASE INFORMATION (use ONLY this for content):\n{combined_content}\n\n"
            "IMPORTANT: Generate a properly formatted insurance report based ONLY on the "
            "factual information provided in the case information. Use the reference only for "
            "formatting guidance. If certain information is missing, note that it is 'Not provided' "
            "rather than inventing details."
        )
        
        # Prepare messages for API call
        messages = [
            {
                "role": "system", 
                "content": "You are an expert insurance report writer. Use only factual information provided by the user. Do not invent or hallucinate any details."
            },
            {"role": "user", "content": prompt}
        ]
        
        # Call OpenRouter API with retry logic
        result = await call_openrouter_api(messages)
        
        # Extract the generated text
        if (
            result
            and "choices" in result
            and len(result["choices"]) > 0
            and "message" in result["choices"][0]
            and "content" in result["choices"][0]["message"]
        ):
            return result["choices"][0]["message"]["content"]
        else:
            logger.error(f"Unexpected API response format: {result}")
            return "Error: The AI service returned an unexpected response format."
                
    except Exception as e:
        logger.error(f"Error in generate_report_text: {str(e)}")
        return (
            "Unable to generate report text. The AI service encountered an error. "
            "Please try again later or contact support if the problem persists."
        )


async def refine_report_text(current_text: str, instructions: str) -> str:
    """
    Refine a report based on user instructions using OpenRouter API.
    
    Args:
        current_text: Current report text
        instructions: User instructions for refinement
        
    Returns:
        Refined report text
    """
    try:
        # Create prompt with explicit instructions to avoid hallucination
        prompt = (
            "You are an insurance report editor. Edit the provided insurance "
            "report according to the user's instructions, following these strict rules:\n\n"
            "1. PRESERVE FACTS: Do not remove or change factual information present in the original report.\n"
            "2. NO NEW FACTS: Do not add any new factual information not present in the original report.\n"
            "3. EDITS ONLY: Make only the changes explicitly requested in the instructions.\n"
            "4. FORMATTING: You may improve formatting, clarity, and structure while preserving content.\n\n"
            f"CURRENT REPORT:\n{current_text}\n\n"
            f"INSTRUCTIONS:\n{instructions}\n\n"
            "Provide the edited version of the report, making only the changes requested "
            "while preserving all factual information. Do not invent new facts."
        )
        
        # Prepare messages for API call
        messages = [
            {
                "role": "system", 
                "content": "You are an expert insurance report editor. Edit documents according to requested changes without adding any new factual information not present in the original. Do not hallucinate or invent details."
            },
            {"role": "user", "content": prompt}
        ]
        
        # Call OpenRouter API with retry logic
        result = await call_openrouter_api(messages)
        
        # Extract the refined text
        if (
            result
            and "choices" in result
            and len(result["choices"]) > 0
            and "message" in result["choices"][0]
            and "content" in result["choices"][0]["message"]
        ):
            return result["choices"][0]["message"]["content"]
        else:
            logger.error(f"Unexpected API response format: {result}")
            return current_text  # Return original text on error
                
    except Exception as e:
        logger.error(f"Error in refine_report_text: {str(e)}")
        return (
            f"{current_text}\n\n"
            "NOTE: Unable to apply refinements. The AI service encountered an error. "
            "Please try again later."
        )


def generate_summary(text: str) -> str:
    """
    Generate a structured summary using OpenRouter API.

    Args:
        text (str): The text content to summarize.

    Returns:
        str: AI-generated summary or an error message.
    """
    if not settings.OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY is missing. Set it in your environment variables.")
        return "Error: Missing API key for OpenRouter."

    try:
        # Create a synchronous version of the OpenRouter API call for simplicity
        with httpx.Client() as client:
            response = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://insurance-report-generator.vercel.app",
                    "X-Title": "Insurance Report Generator"
                },
                json={
                    "model": settings.DEFAULT_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are an AI assistant that generates factual insurance reports. Only use information explicitly provided in the input text. Do not invent or hallucinate any details."},
                        {"role": "user", "content": f"Summarize the following insurance case details with FACTS ONLY - do not add any information not present in the original text:\n\n{text}\n\nProvide a concise, factual summary using only information explicitly stated in the text. If important details are missing, note them as 'not specified' rather than inventing information. Ensure clarity, factual accuracy, and a professional tone."}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 300
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                summary = result["choices"][0]["message"]["content"].strip()
                if not summary:
                    logger.warning("AI response was empty or invalid.")
                    return "Error: AI did not generate a valid summary."
                return summary
            else:
                logger.warning(f"Unexpected API response format: {result}")
                return "Error: AI returned an unexpected response format."
                
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from OpenRouter: {e.response.text}")
        return f"Error: API request failed with status {e.response.status_code}."
    except Exception as e:
        logger.exception("Unexpected error in generate_summary function")
        return f"Error: {str(e)}"
