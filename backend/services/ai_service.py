import httpx
from typing import List
import os
from config import settings


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
    document_content = []
    
    # Extract text from documents
    for path in document_paths:
        with open(path, "r") as file:
            try:
                document_content.append(file.read())
            except UnicodeDecodeError:
                # If not a text file, add placeholder
                document_content.append(f"[Non-text file: {os.path.basename(path)}]")
    
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
    
    try:
        # Call OpenRouter API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.DEFAULT_MODEL,
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are an expert insurance report writer."
                        },
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=30.0
            )
            
            result = response.json()
            if (
                result
                and "choices" in result
                and len(result["choices"]) > 0
                and "message" in result["choices"][0]
                and "content" in result["choices"][0]["message"]
            ):
                return result["choices"][0]["message"]["content"]
            else:
                raise Exception(f"Unexpected API response format: {result}")
                
    except Exception as e:
        # Log the error for debugging
        error_message = f"Error calling OpenRouter API: {str(e)}"
        print(f"ERROR: {error_message}")
        
        # Provide a more helpful error message for the user
        raise Exception(
            "Unable to generate report text. The AI service is currently unavailable. "
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
    # Create prompt
    prompt = (
        "You are an insurance report editor. Edit the following insurance "
        "report according to the instructions provided.\n\n"
        f"CURRENT REPORT:\n{current_text}\n\n"
        f"INSTRUCTIONS:\n{instructions}\n\n"
        "Please provide the edited insurance report."
    )
    
    try:
        # Call OpenRouter API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.DEFAULT_MODEL,
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are an expert insurance report editor."
                        },
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=30.0
            )
            
            result = response.json()
            if (
                result
                and "choices" in result
                and len(result["choices"]) > 0
                and "message" in result["choices"][0]
                and "content" in result["choices"][0]["message"]
            ):
                return result["choices"][0]["message"]["content"]
            else:
                return "Error: Unexpected API response format."
    
    except Exception as e:
        # Return original text if API call fails
        print(f"Warning: Error calling OpenRouter API: {str(e)}")
        return current_text
