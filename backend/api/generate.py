from fastapi import APIRouter, HTTPException
import requests
import os
import json
from config import settings
from typing import Dict, Any, List
from services.pdf_extractor import extract_text_from_files, extract_text_from_file
from services.ai_service import generate_case_summary
from utils.id_mapper import ensure_id_is_int

router = APIRouter(tags=["AI Processing"])


def fetch_reference_reports():
    """Fetches stored reference reports from Supabase or local files."""
    try:
        from supabase import create_client, Client
        
        # Initialize Supabase client
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Fetch reference reports from the database
        response = supabase.table("reference_reports").select("*").execute()
        
        if hasattr(response, 'data') and response.data:
            print(f"Successfully fetched {len(response.data)} reference reports from Supabase")
            return response.data
        else:
            print("No reference reports found in Supabase, or empty response")
            # Fall through to local file check
            
    except Exception as e:
        print(f"Error fetching reference reports from Supabase: {str(e)}")
    
    # Search for local files
    reference_data = []
    
    # Check different possible locations for reference reports
    possible_dirs = [
        os.path.join("backend", "reference_reports"),  # Check inside backend folder
        "reference_reports",  # Check in root folder
        os.path.join(settings.UPLOAD_DIR, "templates")  # Check in templates directory
    ]
    
    for dir_path in possible_dirs:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            print(f"Looking for reference PDFs in {dir_path}")
            
            reference_files = [
                os.path.join(dir_path, f) 
                for f in os.listdir(dir_path) 
                if f.lower().endswith(".pdf")
            ]
            
            if reference_files:
                print(f"Found {len(reference_files)} reference files: {reference_files}")
                
                for file_path in reference_files:
                    try:
                        extracted_text = extract_text_from_file(file_path)
                        reference_data.append({
                            "id": os.path.basename(file_path),
                            "name": os.path.basename(file_path),
                            "extracted_text": extracted_text,
                            "file_path": file_path
                        })
                    except Exception as e:
                        print(f"Error extracting text from {file_path}: {str(e)}")
                
                if reference_data:
                    return reference_data
                    
    if not reference_data:
        print("No reference reports found in local directories")
        
    return reference_data


def get_report_files(report_id: str) -> List[Dict[str, Any]]:
    """
    Get the list of files associated with a report_id from the metadata file.
    
    Args:
        report_id: The ID of the report to get files for
        
    Returns:
        List of file information dictionaries
    """
    report_dir = os.path.join(settings.UPLOAD_DIR, report_id)
    metadata_path = os.path.join(report_dir, "metadata.json")
    
    if not os.path.exists(metadata_path):
        return []
    
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
            return metadata.get("files", [])
    except Exception as e:
        print(f"Error reading report metadata: {str(e)}")
        return []


@router.post("/")
async def generate_report(text: dict):
    reference_reports = fetch_reference_reports()

    if not reference_reports:
        return {"error": "No reference reports found in database or local directories."}

    # Use all available reference reports, but limit total context size 
    # to avoid exceeding token limits
    max_report_chars = 20000  # Adjust based on token limits of your model
    context = ""
    reports_used = 0
    
    # Sort by relevance, assuming shorter reports are more likely to be relevant templates
    # This is a simple heuristic - you might want to implement more sophisticated selection
    sorted_reports = sorted(
        reference_reports, 
        key=lambda r: len(r.get("extracted_text", "")),
    )
    
    for report in sorted_reports:
        report_text = report.get("extracted_text", "")
        # Skip empty reports
        if not report_text.strip():
            continue
            
        # Check if adding this report would exceed our size limit
        if len(context) + len(report_text) > max_report_chars:
            # If we already have some context, stop adding more
            if context:
                break
            # If this is the first report and it's too large, truncate it
            report_text = report_text[:max_report_chars]
        
        # Add a separator if we already have content
        if context:
            context += "\n\n--- NEXT REFERENCE REPORT ---\n\n"
        
        context += report_text
        reports_used += 1
    
    print(f"Using {reports_used} reference reports for generation (total {len(context)} chars)")

    prompt = (
        "You're an expert insurance report writer. Follow these important instructions:\n\n"
        "1. REFERENCE REPORTS: I'm providing reference reports ONLY to show you the correct FORMAT, "
        "STRUCTURE, STYLE, and TONE OF VOICE. DO NOT memorize or use any factual content from these references.\n\n"
        "2. CASE NOTES: Generate a new report using ONLY the information from the user's case notes.\n\n"
        "3. LANGUAGE: Generate the report in the SAME LANGUAGE as the case notes (either Italian or English).\n\n"
        f"REFERENCE REPORTS (for format/style only):\n{context}\n\n"
        f"CASE NOTES (use this content for your report):\n{text['content']}\n\n"
        "Generate a structured insurance claim report that includes common sections such as:\n"
        "- CLAIM SUMMARY\n"
        "- CLAIMANT INFORMATION\n"
        "- INCIDENT DETAILS\n"
        "- COVERAGE ANALYSIS\n"
        "- DAMAGES/INJURIES\n"
        "- INVESTIGATION FINDINGS\n"
        "- LIABILITY ASSESSMENT\n"
        "- SETTLEMENT RECOMMENDATION\n\n"
        "Important: Match the professional tone, formatting, and style of the reference reports, "
        "but ONLY use facts from the case notes."
    )

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json={"model": settings.DEFAULT_MODEL, "prompt": prompt},
        headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
    )

    return response.json()


@router.post("/from-id")
async def generate_report_from_id(data: Dict[str, Any]):
    """
    Generate a report based on uploaded files identified by report_id
    
    Args:
        data: A dictionary containing report_id
        
    Returns:
        Generated report content
    """
    report_id = data.get("report_id")
    
    if not report_id:
        raise HTTPException(status_code=400, detail="report_id is required")
    
    print(f"Received report generation request with ID: {report_id}")
    
    try:
        # If report_id is a UUID, the files will be in a directory named with the UUID
        # This relies on files being stored using the UUID as a directory name
        report_files = get_report_files(report_id)
        
        if not report_files:
            raise HTTPException(
                status_code=404, 
                detail=f"No files found for report ID: {report_id}"
            )
        
        # Extract text from all files
        file_paths = [file["path"] for file in report_files]
        file_contents = extract_text_from_files(file_paths)
        
        # If we have very little content, provide a more detailed message
        if len(file_contents.strip()) < 100:
            file_statuses = []
            for file in report_files:
                path = file["path"]
                exists = os.path.exists(path)
                size = os.path.getsize(path) if exists else 0
                file_statuses.append(f"{file['filename']}: Exists={exists}, Size={size} bytes")
            
            file_contents += "\n\nFile Status:\n" + "\n".join(file_statuses)
            
        print(f"Extracted {len(file_contents)} characters of text from {len(file_paths)} files")
        
        # Get reference reports to use as style templates
        reference_reports = fetch_reference_reports()
        
        # Check if we have any reference reports
        if not reference_reports:
            context = "Professional insurance claim report with sections for Summary, Details, Assessment, and Recommendations."
        else:
            context = "\n\n".join([r.get("extracted_text", "") for r in reference_reports[:2]])
        
        # Call the OpenRouter API
        prompt = (
            "You're an expert insurance report writer. Follow these important instructions:\n\n"
            "1. REFERENCE REPORTS: I'm providing reference reports ONLY to show you the correct FORMAT, "
            "STRUCTURE, STYLE, and TONE OF VOICE. DO NOT memorize or use any factual content from these references.\n\n"
            "2. USER DOCUMENTS: Generate a new report using ONLY the information from the user's case documents.\n\n"
            "3. LANGUAGE: Generate the report in the SAME LANGUAGE as the case documents (either Italian or English).\n\n"
            f"REFERENCE REPORTS (for format/style only):\n{context}\n\n"
            f"CASE DOCUMENTS (use this content for your report):\n{file_contents}\n\n"
            "Generate a structured insurance claim report that includes common sections such as:\n"
            "- CLAIM SUMMARY\n"
            "- CLAIMANT INFORMATION\n"
            "- INCIDENT DETAILS\n"
            "- COVERAGE ANALYSIS\n"
            "- DAMAGES/INJURIES\n"
            "- INVESTIGATION FINDINGS\n"
            "- LIABILITY ASSESSMENT\n"
            "- SETTLEMENT RECOMMENDATION\n\n"
            "Important: Match the professional tone, formatting, and style of the reference reports, "
            "but ONLY use facts from the case documents."
        )
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "model": settings.DEFAULT_MODEL,
                "messages": [{"role": "user", "content": prompt}]
            },
            headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}
        )
        
        # Extract the generated content from the response
        response_data = response.json()
        print("OpenRouter API response:", response_data)
        
        if "choices" in response_data and len(response_data["choices"]) > 0:
            generated_text = response_data["choices"][0]["message"]["content"]
        else:
            # Fallback if API response is unexpected
            generated_text = (
                "## Error Generating Report\n\n"
                "The AI model was unable to generate a report from your documents.\n\n"
                "### Document Contents:\n\n"
                f"{file_contents[:500]}...\n\n"
                "### API Response:\n\n"
                f"{json.dumps(response_data, indent=2)}"
            )
        
        return {"content": generated_text}
        
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        return {
            "content": f"Error generating report: {str(e)}. Please try again.",
            "error": str(e)
        }


# Very simple test endpoint to check routing
@router.post("/simple-test")
async def simple_test(data: Dict[str, Any]):
    """A very simple test endpoint to check routing"""
    return {"message": "Simple test endpoint works!", "received": data}


@router.post("/summarize")
async def summarize_documents(data: Dict[str, Any]):
    """
    Generate a brief summary of uploaded documents
    
    Args:
        data: A dictionary containing report_id
        
    Returns:
        Brief summary and key facts
    """
    report_id = data.get("report_id")
    
    if not report_id:
        raise HTTPException(status_code=400, detail="report_id is required")
    
    print(f"Received summary request for ID: {report_id}")
    
    try:
        # If report_id is a UUID, the files will be in a directory named with the UUID
        report_files = get_report_files(report_id)
        
        if not report_files:
            raise HTTPException(
                status_code=404, 
                detail=f"No files found for report ID: {report_id}"
            )
        
        # Extract file paths
        file_paths = [file["path"] for file in report_files]
        
        # Generate the summary
        summary_result = await generate_case_summary(file_paths)
        
        print(f"Generated summary: {summary_result['summary']}")
        print(f"Key facts identified: {len(summary_result['key_facts'])}")
        
        return summary_result
        
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        return {
            "summary": f"Error generating summary: {str(e)}. Please try again.",
            "key_facts": [],
            "error": str(e)
        }
