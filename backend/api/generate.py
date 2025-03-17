from fastapi import APIRouter, HTTPException
import requests
import os
import json
from config import settings
from typing import Dict, Any, List
from services.pdf_extractor import extract_text_from_files, extract_text_from_file
from services.ai_service import generate_case_summary
from utils.id_mapper import ensure_id_is_int
import time

router = APIRouter(tags=["AI Processing"])


def fetch_reference_reports():
    """
    Fetches stored reference reports from Supabase or local files.
    
    Returns:
        List of reference report data with extracted text
    """
    try:
        from supabase import create_client, Client
        
        # Initialize Supabase client
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Fetch reference reports from the database
        response = supabase.table("reference_reports").select("*").execute()
        
        if hasattr(response, 'data') and response.data:
            print(f"Successfully fetched {len(response.data)} reference reports from Supabase")
            
            # Ensure each report has the expected fields
            valid_reports = []
            for report in response.data:
                if "extracted_text" in report and report["extracted_text"]:
                    valid_reports.append(report)
                else:
                    print(f"Warning: Reference report {report.get('id', 'unknown')} missing extracted text")
                    
            if valid_reports:
                return valid_reports
            else:
                print("No valid reference reports found in Supabase (missing extracted text)")
                # Fall through to local file check
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
            print(f"Looking for reference reports in {dir_path}")
            
            # Look for PDFs, Word docs, and text files
            reference_files = [
                os.path.join(dir_path, f) 
                for f in os.listdir(dir_path) 
                if f.lower().endswith((".pdf", ".docx", ".doc", ".txt"))
            ]
            
            if reference_files:
                print(f"Found {len(reference_files)} reference files: {[os.path.basename(f) for f in reference_files]}")
                
                for file_path in reference_files:
                    try:
                        print(f"Extracting text from reference file: {file_path}")
                        extracted_text = extract_text_from_file(file_path)
                        
                        if not extracted_text or extracted_text.startswith("Error:"):
                            print(f"Warning: Could not extract text from {file_path}: {extracted_text}")
                            continue
                            
                        reference_data.append({
                            "id": os.path.basename(file_path),
                            "name": os.path.basename(file_path),
                            "extracted_text": extracted_text,
                            "file_path": file_path
                        })
                        print(f"Successfully extracted {len(extracted_text)} characters from {file_path}")
                    except Exception as e:
                        print(f"Error extracting text from {file_path}: {str(e)}")
                
                if reference_data:
                    print(f"Successfully loaded {len(reference_data)} reference documents")
                    return reference_data
                else:
                    print(f"Could not extract text from any files in {dir_path}, trying next directory")
                    
    if not reference_data:
        print("No reference reports found in any local directories")
        
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

    # Updated with stricter instructions matching /from-id endpoint format
    prompt = (
        "You are an expert insurance report writer tasked with creating a formal insurance report.\n\n"
        "STRICT INSTRUCTIONS - FOLLOW PRECISELY:\n"
        "1. FORMAT ONLY: Use reference reports ONLY for format, structure, style, and professional tone.\n"
        "2. USER CONTENT ONLY: The content of your report MUST come EXCLUSIVELY from the user's case notes.\n"
        "3. NO INVENTION: Do not add ANY information not explicitly present in the case notes.\n"
        "4. MATCH LANGUAGE: Write the report in Italian by default, unless the case notes are clearly in English.\n"
        "5. MISSING INFO: If key information is missing, state 'Non fornito nei documenti' rather than inventing it.\n"
        "6. NO CREATIVITY: This is a factual insurance document - stick strictly to information in the case notes.\n\n"
        f"REFERENCE FORMAT (use ONLY for structure/style/tone):\n{context}\n\n"
        f"CASE NOTES (ONLY SOURCE FOR CONTENT):\n{text['content']}\n\n"
        "Generate a structured insurance claim report that follows the format of the reference but "
        "ONLY uses facts from the case notes. Include sections like:\n"
        "- RIEPILOGO SINISTRO\n"
        "- INFORMAZIONI SUL RICHIEDENTE\n"
        "- DETTAGLI INCIDENTE\n"
        "- ANALISI COPERTURA\n"
        "- DANNI/FERITE\n"
        "- RISULTATI INVESTIGAZIONE\n"
        "- VALUTAZIONE RESPONSABILITÀ\n"
        "- RACCOMANDAZIONE RISARCIMENTO\n\n"
        "CRITICAL: Do NOT invent ANY information. Only use facts explicitly stated in the case notes."
    )

    # Updated to use messages array with system message like /from-id endpoint
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json={
            "model": settings.DEFAULT_MODEL,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are an expert insurance report writer. You MUST ONLY use facts explicitly stated in the user's case notes. Do not invent, assume, or hallucinate ANY information not explicitly provided. Remain strictly factual."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2  # Lower temperature for more factual output
        },
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
        
        # Log file information for debugging purposes
        print(f"Found {len(report_files)} files for report ID {report_id}:")
        for idx, file in enumerate(report_files):
            print(f"  File {idx+1}: {file['filename']} ({file['type']}) at {file['path']}")
            
            # Check if files actually exist
            if not os.path.exists(file['path']):
                print(f"WARNING: File path doesn't exist: {file['path']}")
        
        # Extract text from all files
        file_paths = [file["path"] for file in report_files]
        extraction_start_time = time.time()
        print(f"Starting text extraction from {len(file_paths)} files...")
        
        try:
            file_contents = extract_text_from_files(file_paths)
            extraction_time = time.time() - extraction_start_time
            print(f"Text extraction completed in {extraction_time:.2f} seconds")
            
            # Check if multimodal extraction was used
            used_multimodal = "[Extracted using AI Vision technology]" in file_contents
            
            # Check for specific OCR markers that indicate image-based documents
            ocr_markers = ["[OCR failed", "No readable text detected in image", "Image file detected"]
            has_ocr_content = any(marker in file_contents for marker in ocr_markers)
            
            # Check if the extraction returned an error message
            if file_contents.startswith("Error:") or "Error extracting text" in file_contents:
                is_protected_file = any(
                    msg in file_contents for msg in 
                    ["password-protected", "encrypted", "protected", "binary format"]
                )
                
                if is_protected_file:
                    error_msg = "One or more files appear to be password-protected or in an unsupported format."
                    return {
                        "content": f"## Document Access Error\n\n{error_msg}\n\nPlease try uploading the document again after removing any password protection, or convert it to a more compatible format like PDF or plain DOCX without encryption.\n\n**Technical Details:**\n\n{file_contents}",
                        "extraction_error": error_msg
                    }
                else:
                    error_msg = "An error occurred while extracting text from your documents"
                    return {
                        "content": f"## Document Processing Error\n\n{error_msg}\n\nPlease check your documents and try again with a different format.\n\n**Technical Details:**\n\n{file_contents}",
                        "extraction_error": error_msg
                    }
            
            # If we only have OCR content (from images) but very little actual text
            if has_ocr_content and len(file_contents.strip()) < 500 and not used_multimodal:
                print("WARNING: Document appears to be primarily image-based with little text")
                return {
                    "content": f"## Image-Based Document Detected\n\nYour document appears to be primarily image-based. While we've attempted to extract text using OCR technology, the results may be limited. For best results, please consider uploading a text-based document.\n\n### OCR Results:\n\n{file_contents}\n\nIf the text above is incomplete or inaccurate, please try providing a text-based document version instead.",
                    "ocr_limited": True
                }
            
        except Exception as extract_error:
            error_msg = f"Error extracting text from files: {str(extract_error)}"
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            return {
                "content": f"## Error Extracting Text\n\nWe encountered a problem extracting text from your documents: {str(extract_error)}\n\nPlease try again with a different file format or contact support.",
                "extraction_error": str(extract_error)
            }
        
        # If we have very little content and multimodal wasn't used, provide a detailed message
        if len(file_contents.strip()) < 100 and not used_multimodal:
            print("WARNING: Extracted less than 100 characters of text")
            file_statuses = []
            for file in report_files:
                path = file["path"]
                exists = os.path.exists(path)
                size = os.path.getsize(path) if exists else 0
                file_statuses.append(f"{file['filename']}: Exists={exists}, Size={size} bytes")
            
            # Add file status information to the extracted content for debugging
            file_status_text = "\n\nFile Status:\n" + "\n".join(file_statuses)
            
            if file_contents.strip() == "":
                print("ERROR: No text extracted from any files")
                return {
                    "content": f"## Error: No Text Extracted\n\nWe couldn't extract any text from your documents. This might be because:\n\n- The files contain only images without OCR\n- The files are password protected\n- The files are in a format we can't read\n- The files are corrupted\n\nPlease try again with different documents or convert them to a different format.{file_status_text}",
                    "extraction_error": "No text extracted from files"
                }
            
            # Check if there's a meaningful error message in the extracted content
            if "Error:" in file_contents or "Warning:" in file_contents:
                print(f"WARNING: Error messages found in extracted content: {file_contents}")
                return {
                    "content": f"## Document Processing Issue\n\nWe had some issues processing your documents:\n\n```\n{file_contents}\n```\n\nPlease consider:\n\n1. Converting your documents to PDF\n2. Removing any password protection\n3. Using files that contain actual text content (not just images)\n\n{file_status_text}",
                    "extraction_error": "Error messages in extracted content"
                }
            
            file_contents += file_status_text
            
        print(f"Extracted {len(file_contents)} characters of text from {len(file_paths)} files")
        
        # Add a note if multimodal extraction was used
        multimodal_note = ""
        if used_multimodal:
            multimodal_note = "\n\nNote: Advanced AI Vision technology was used to analyze your document directly."
        
        # Get reference reports to use as style templates
        reference_reports = fetch_reference_reports()
        
        # Check if we have any reference reports
        if not reference_reports:
            context = "Professional insurance claim report with sections for Summary, Details, Assessment, and Recommendations."
            print("WARNING: No reference reports found, using minimal structure.")
        else:
            print(f"Using {len(reference_reports)} reference reports for formatting guidance.")
            # Join the content of up to 2 reference reports to provide formatting guidance
            context = "\n\n--- NEXT REFERENCE REPORT ---\n\n".join(
                [r.get("extracted_text", "") for r in reference_reports[:2]]
            )
        
        # Call the OpenRouter API with strong instructions about using only user content
        prompt = (
            "You are an expert insurance report writer tasked with creating a formal insurance report.\n\n"
            "STRICT INSTRUCTIONS - FOLLOW PRECISELY:\n"
            "1. FORMAT ONLY: Use reference reports ONLY for format, structure, style, and professional tone.\n"
            "2. USER CONTENT ONLY: The content of your report MUST come EXCLUSIVELY from the user's documents.\n"
            "3. NO INVENTION: Do not add ANY information not explicitly present in the user's documents.\n"
            "4. MATCH LANGUAGE: Write the report in the same language as the user documents (either Italian or English).\n"
            "5. MISSING INFO: If key information is missing, state 'Not provided in the documents' rather than inventing it.\n"
            "6. NO CREATIVITY: This is a factual insurance document - stick strictly to information in the user's documents.\n"
            "7. OCR AWARENESS: Some content may come from OCR of images and may contain errors - focus on the most reliable information."
            f"{multimodal_note}\n\n"
            f"REFERENCE FORMAT (use ONLY for structure/style/tone):\n{context}\n\n"
            f"USER DOCUMENTS (ONLY SOURCE FOR CONTENT):\n{file_contents}\n\n"
            "Generate a structured insurance claim report that follows the format of the reference but "
            "ONLY uses facts from the user documents. Include sections like:\n"
            "- CLAIM SUMMARY\n"
            "- CLAIMANT INFORMATION\n"
            "- INCIDENT DETAILS\n"
            "- COVERAGE ANALYSIS\n"
            "- DAMAGES/INJURIES\n"
            "- INVESTIGATION FINDINGS\n"
            "- LIABILITY ASSESSMENT\n"
            "- SETTLEMENT RECOMMENDATION\n\n"
            "CRITICAL: Do NOT invent ANY information. Only use facts explicitly stated in the user's documents."
        )
        
        try:
            api_start_time = time.time()
            print(f"Calling OpenRouter API with prompt length {len(prompt)} characters...")
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={
                    "model": settings.DEFAULT_MODEL,
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are an expert insurance report writer. You MUST ONLY use facts explicitly stated in the user's documents. Do not invent, assume, or hallucinate ANY information not explicitly provided. Remain strictly factual. If content appears to be from OCR with potential errors, focus on the most reliable information."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2  # Lower temperature for more factual output
                },
                headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}
            )
            
            api_time = time.time() - api_start_time
            print(f"OpenRouter API call completed in {api_time:.2f} seconds")
            
            # Extract the generated content from the response
            response_data = response.json()
            print(f"OpenRouter API response status: {response.status_code}")
            
            if "choices" in response_data and len(response_data["choices"]) > 0:
                generated_text = response_data["choices"][0]["message"]["content"]
                
                # Add a note about multimodal processing if it was used
                if used_multimodal:
                    generated_text = (
                        "**Note: Advanced AI Vision technology was used to analyze your document directly.**\n\n" 
                        + generated_text
                    )
                    
                return {
                    "content": generated_text,
                    "used_multimodal": used_multimodal
                }
            else:
                # Fallback if API response is unexpected
                error_text = (
                    "## Error Generating Report\n\n"
                    "The AI model was unable to generate a report from your documents.\n\n"
                    "### Document Contents:\n\n"
                    f"{file_contents[:500]}...\n\n"
                    "### API Response:\n\n"
                    f"{json.dumps(response_data, indent=2)}"
                )
                print("ERROR: Unexpected API response format")
                print(json.dumps(response_data, indent=2))
                return {"content": error_text, "api_error": response_data}
        
        except Exception as api_error:
            error_msg = f"Error calling OpenRouter API: {str(api_error)}"
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            
            return {
                "content": f"## Error Generating Report\n\nWe encountered a problem while generating your report: {str(api_error)}\n\nText was successfully extracted from your documents, but the AI service encountered an error.",
                "api_error": str(api_error)
            }
        
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            "content": f"## Error Generating Report\n\nWe encountered a problem: {str(e)}.\n\nPlease try again or contact support.",
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
        
        # Log file information for debugging
        print(f"Found {len(report_files)} files for report ID {report_id}:")
        for idx, file in enumerate(report_files):
            print(f"  File {idx+1}: {file['filename']} ({file['type']}) at {file['path']}")
            
            # Check if files actually exist
            if not os.path.exists(file['path']):
                print(f"WARNING: File path doesn't exist: {file['path']}")
        
        # Extract file paths
        file_paths = [file["path"] for file in report_files]
        
        # Extract text from files first to validate content
        try:
            extraction_start_time = time.time()
            print(f"Starting text extraction from {len(file_paths)} files for summary...")
            
            extracted_text = extract_text_from_files(file_paths)
            extraction_time = time.time() - extraction_start_time
            print(f"Text extraction completed in {extraction_time:.2f} seconds")
            
            # Check for OCR markers or errors
            ocr_markers = ["[OCR failed", "No readable text detected in image", "Image file detected"]
            has_ocr_content = any(marker in extracted_text for marker in ocr_markers)
            has_error = extracted_text.startswith("Error:") or "Error extracting text" in extracted_text
            
            # Check if we have an extraction error
            if has_error:
                error_msg = "Error extracting text from documents"
                print(f"WARNING: {error_msg} - {extracted_text}")
                return {
                    "summary": f"We encountered an issue processing your documents. {extracted_text.split('.')[0]}.",
                    "key_facts": [],
                    "error": extracted_text
                }
                
            # Check for minimal content from OCR
            if has_ocr_content and len(extracted_text.strip()) < 300:
                print("WARNING: Document appears to be primarily image-based with little text")
                return {
                    "summary": "Your document appears to be primarily image-based. While we've attempted to extract text using OCR technology, the results are too limited for a proper summary. For best results, please consider uploading a text-based document.",
                    "key_facts": [
                        "Document is primarily image-based",
                        "Limited text content could be extracted",
                        "OCR results may be unreliable",
                        "Consider providing a text-based document"
                    ],
                    "ocr_limited": True
                }
                
            # If very little content overall, return a helpful message
            if len(extracted_text.strip()) < 100:
                print("WARNING: Extracted less than 100 characters of text")
                return {
                    "summary": "We could only extract a very small amount of text from your documents. This may be because the documents are image-based, password-protected, or in a format we can't fully process.",
                    "key_facts": [
                        "Limited text content extracted",
                        "Document may be primarily graphical",
                        "Consider providing a text-based version"
                    ],
                    "limited_content": True
                }
            
        except Exception as extract_error:
            error_msg = f"Error during text extraction: {str(extract_error)}"
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            return {
                "summary": "Error processing documents. Please try uploading in a different format.",
                "key_facts": [],
                "error": str(extract_error)
            }
            
        # Generate the summary using our AI function that includes strict factual instructions
        try:
            # Pass additional context if we have OCR content
            ocr_context = ""
            if has_ocr_content:
                ocr_context = "Note: Some content appears to be from OCR of images and may contain errors. Focus on the most reliable information."
                
            summary_result = await generate_case_summary(file_paths, ocr_context)
            
            print(f"Generated summary: {summary_result['summary']}")
            print(f"Key facts identified: {len(summary_result['key_facts'])}")
            
            # Add a note to the summary if OCR was used
            if has_ocr_content:
                summary_result["summary"] = "Note: Your document appears to contain image-based content. Our system used OCR to extract text, which may result in some inaccuracies. " + summary_result["summary"]
                summary_result["ocr_used"] = True
                
            return summary_result
            
        except Exception as summary_error:
            error_msg = f"Error generating summary: {str(summary_error)}"
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            return {
                "summary": f"Error generating summary: {str(summary_error)}. Please try again.",
                "key_facts": [],
                "error": str(summary_error)
            }
        
    except Exception as e:
        print(f"Error in summarize_documents endpoint: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            "summary": f"Error processing request: {str(e)}. Please try again.",
            "key_facts": [],
            "error": str(e)
        }
