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
        
        # Create prompt for a very brief summary
        prompt = (
            "You are an insurance claims analyzer. Create an extremely brief summary (1-2 sentences) "
            "and extract key facts from the following documents. Focus on claim amount, property damage, "
            "injuries, policy details, and incident date if present.\n\n"
            f"DOCUMENT CONTENT:\n{combined_content}\n\n"
            "Provide your response in this format:\n"
            "SUMMARY: [A 1-2 sentence summary of the claim/incident]\n"
            "KEY_FACTS: [2-4 key points in bullet format with amounts, dates, and specifics]"
        )
        
        # Prepare messages for API call
        messages = [
            {
                "role": "system", 
                "content": "You are an insurance claims analyzer. Provide extremely concise summaries and key facts only."
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
        
        # Get reference template
        # In a real implementation, this would fetch from Supabase
        reference_content = (
            "This is a reference insurance report template.\n"
            "CLAIM #: XXXXX\n"
            "DATE OF LOSS: MM/DD/YYYY\n"
            "INSURED: John Doe\n"
            "CLAIMANT: Jane Smith\n"
            "POLICY #: XXXXX\n\n"
            "SUMMARY OF CLAIM:\n"
            "The claimant alleges...\n\n"
            "INVESTIGATION:\n"
            "Our investigation found...\n\n"
            "COVERAGE ANALYSIS:\n"
            "Based on policy section X...\n\n"
            "EVALUATION:\n"
            "We recommend..."
        )
        
        # Create prompt
        prompt = (
            "You are an insurance report writer. Generate a formal insurance "
            "report based on the following case information. Format it like the "
            "reference report template below.\n\n"
            f"REFERENCE TEMPLATE:\n{reference_content}\n\n"
            f"CASE INFORMATION:\n{combined_content}\n\n"
            "Please generate a properly formatted insurance report based on "
            "this information, following the structure of the reference template."
        )
        
        # Prepare messages for API call
        messages = [
            {
                "role": "system", 
                "content": "You are an expert insurance report writer."
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
        # Create prompt
        prompt = (
            "You are an insurance report editor. Edit the following insurance "
            "report according to the instructions provided.\n\n"
            f"CURRENT REPORT:\n{current_text}\n\n"
            f"INSTRUCTIONS:\n{instructions}\n\n"
            "Please provide the edited insurance report."
        )
        
        # Prepare messages for API call
        messages = [
            {
                "role": "system", 
                "content": "You are an expert insurance report editor."
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
