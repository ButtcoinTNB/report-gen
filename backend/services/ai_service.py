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


async def generate_case_summary(document_paths: List[str], ocr_context: str = "") -> Dict[str, str]:
    """
    Generate a very brief summary of case documents highlighting key findings.
    
    Args:
        document_paths: List of paths to the uploaded documents
        ocr_context: Optional context about OCR processing for image-based documents
        
    Returns:
        Dictionary with summary and key_facts
    """
    try:
        logger.info(f"Generating case summary for {len(document_paths)} documents")
        
        # Use our improved extractor to handle different file types including images
        from services.pdf_extractor import extract_text_from_files
        
        # Extract text from all documents at once with better file handling
        extracted_content = extract_text_from_files(document_paths)
        
        if not extracted_content or extracted_content.strip() == "":
            logger.warning("No readable content extracted from documents")
            return {
                "summary": "No readable content found in the provided documents.",
                "key_facts": []
            }
            
        logger.info(f"Successfully extracted {len(extracted_content)} characters from documents")
        
        # Add OCR context to the prompt if provided
        ocr_instruction = ""
        if ocr_context:
            logger.info(f"Including OCR context in prompt: {ocr_context}")
            ocr_instruction = f"\n5. CONSAPEVOLEZZA OCR: {ocr_context}\n"
        
        # Create prompt for a very brief summary with strict instructions
        prompt = (
            "Sei un analista di sinistri assicurativi. Il tuo compito è creare un riassunto estremamente breve "
            "(1-2 frasi) ed estrarre i fatti chiave dai documenti forniti. Segui queste regole rigorose:\n\n"
            "1. SOLO FATTI: Utilizza SOLO informazioni esplicitamente dichiarate nei documenti.\n"
            "2. NESSUNA INVENZIONE: Non aggiungere alcun dettaglio non presente nei documenti.\n"
            "3. INFORMAZIONI CHIAVE: Concentrati su importo del sinistro, danni alla proprietà, lesioni, dettagli della polizza, "
            "e data dell'incidente se presenti nei documenti.\n"
            "4. SE MANCANTE: Se qualsiasi informazione chiave non è nei documenti, indicala come 'non fornita' "
            "piuttosto che fare supposizioni."
            f"{ocr_instruction}\n"
            "5. LINGUA ITALIANA: Scrivi SEMPRE in italiano, indipendentemente dalla lingua dei documenti di input.\n\n"
            f"CONTENUTO DEL DOCUMENTO:\n{extracted_content}\n\n"
            "Fornisci la tua risposta in questo formato:\n"
            "RIASSUNTO: [Un riassunto fattuale di 1-2 frasi basato SOLO sui documenti forniti]\n"
            "FATTI_CHIAVE: [2-4 punti chiave in formato puntato con importi, date e specifiche SOLO dai documenti]"
        )
        
        # Prepare system message with OCR awareness if needed
        system_content = "Sei un analista di sinistri assicurativi. Fornisci riassunti estremamente concisi e FATTUALI e fatti chiave. Non inventare dettagli non presenti nei documenti. Scrivi SEMPRE in italiano, indipendentemente dalla lingua dei documenti di input."
        if ocr_context:
            system_content += " " + ocr_context
        
        # Prepare messages for API call
        messages = [
            {
                "role": "system", 
                "content": system_content
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
            summary_match = re.search(r'RIASSUNTO:\s*(.+?)(?:\n|$)', response_text, re.DOTALL)
            summary = summary_match.group(1).strip() if summary_match else "Riassunto non disponibile"
            
            # Extract key facts as a list
            key_facts_section = re.search(r'FATTI_CHIAVE:\s*(.+?)(?:\n\n|$)', response_text, re.DOTALL)
            key_facts_text = key_facts_section.group(1).strip() if key_facts_section else ""
            
            # Convert bullet points to list items
            key_facts = []
            for line in key_facts_text.split('\n'):
                # Remove bullet point markers and clean up
                cleaned_line = re.sub(r'^[\s•\-\*]+', '', line).strip()
                if cleaned_line:
                    key_facts.append(cleaned_line)
            
            logger.info(f"Generated summary with {len(key_facts)} key facts")
            
            return {
                "summary": summary,
                "key_facts": key_facts
            }
        else:
            logger.error(f"Unexpected API response format: {result}")
            return {
                "summary": "Impossibile generare un riassunto dai documenti.",
                "key_facts": []
            }
                
    except Exception as e:
        logger.error(f"Error in generate_case_summary: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "summary": "Impossibile generare il riassunto del caso. Si è verificato un errore.",
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
        # Extract text from input documents
        from services.pdf_extractor import extract_text_from_files
        document_text = extract_text_from_files(document_paths)
        
        if not document_text or len(document_text.strip()) < 10:
            return "Nessun testo leggibile è stato estratto dai documenti forniti."
            
        logger.info(f"Extracted {len(document_text)} characters from uploaded documents")
            
        # Create a default format template with placeholders
        format_template = """
## RIEPILOGO SINISTRO
[Format placeholder for claim summary]

## INFORMAZIONI SUL RICHIEDENTE
[Format placeholder for claimant information]

## DETTAGLI INCIDENTE
[Format placeholder for incident details]

## ANALISI COPERTURA
[Format placeholder for coverage analysis]

## DANNI/FERITE
[Format placeholder for damages/injuries]

## RISULTATI INVESTIGAZIONE
[Format placeholder for investigation findings]

## VALUTAZIONE RESPONSABILITÀ
[Format placeholder for liability assessment]

## RACCOMANDAZIONE RISARCIMENTO
[Format placeholder for settlement recommendation]
"""
        
        # Prepare the system message
        system_message = (
            "Sei un esperto redattore di relazioni assicurative. DEVI utilizzare SOLO fatti esplicitamente dichiarati nei documenti dell'utente. "
            "Non inventare, presumere o allucinare ALCUNA informazione non esplicitamente fornita. Rimani strettamente fattuale. "
            "NON utilizzare ALCUNA informazione dal modello di formato per il contenuto - serve SOLO per la struttura. "
            "Scrivi SEMPRE in italiano, indipendentemente dalla lingua dei documenti di input."
        )
        
        # Prepare the prompt with strict instructions
        prompt = (
            "Sei un esperto redattore di relazioni assicurative incaricato di creare una relazione formale assicurativa.\n\n"
            "ISTRUZIONI RIGOROSE - SEGUI CON PRECISIONE:\n"
            "1. SOLO FORMATO: Utilizza il modello di formato per strutturare la tua relazione in modo professionale.\n"
            "2. SOLO CONTENUTO UTENTE: Il contenuto della tua relazione DEVE provenire ESCLUSIVAMENTE dai documenti dell'utente.\n"
            "3. NESSUNA INVENZIONE: Non aggiungere ALCUNA informazione non esplicitamente presente nei documenti dell'utente.\n"
            "4. LINGUA ITALIANA: Scrivi la relazione SEMPRE in italiano, indipendentemente dalla lingua dei documenti dell'utente.\n"
            "5. INFORMAZIONI MANCANTI: Se mancano informazioni chiave, indica 'Non fornito nei documenti' anziché inventarle.\n"
            "6. NESSUNA CREATIVITÀ: Questo è un documento assicurativo fattuale - attieniti strettamente alle informazioni nei documenti dell'utente.\n"
            f"MODELLO DI FORMATO (usa SOLO per la struttura):\n{format_template}\n\n"
            f"DOCUMENTI DELL'UTENTE (UNICA FONTE PER IL CONTENUTO):\n{document_text}\n\n"
            "Genera una relazione strutturata di sinistro assicurativo che segue il formato del modello ma "
            "utilizza SOLO fatti dai documenti dell'utente. Includi sezioni appropriate in base alle informazioni disponibili.\n\n"
            "FONDAMENTALE: NON inventare ALCUNA informazione. Utilizza solo fatti esplicitamente dichiarati nei documenti dell'utente."
        )
        
        # Prepare the messages for the API
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        # Call the LLM API
        result = await call_openrouter_api(
            messages=messages,
            max_retries=2,
            timeout=60.0
        )
        
        # Extract the response text
        if (
            result
            and "choices" in result
            and len(result["choices"]) > 0
            and "message" in result["choices"][0]
            and "content" in result["choices"][0]["message"]
        ):
            generated_text = result["choices"][0]["message"]["content"]
            logger.info(f"Generated report with {len(generated_text)} characters")
            return generated_text.strip()
        else:
            logger.error(f"Unexpected API response format: {result}")
            return "Errore: Impossibile generare il testo del report a causa di una risposta API imprevista."
            
    except Exception as e:
        logger.error(f"Error in generate_report_text: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Errore nella generazione del report: {str(e)}"


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
            "Sei un redattore di relazioni assicurative. Modifica la relazione assicurativa "
            "fornita secondo le istruzioni dell'utente, seguendo queste regole rigorose:\n\n"
            "1. PRESERVA I FATTI: Non rimuovere o modificare informazioni fattuali presenti nella relazione originale.\n"
            "2. NESSUN NUOVO FATTO: Non aggiungere nuove informazioni fattuali non presenti nella relazione originale.\n"
            "3. SOLO MODIFICHE: Apporta solo le modifiche esplicitamente richieste nelle istruzioni.\n"
            "4. FORMATTAZIONE: Puoi migliorare la formattazione, la chiarezza e la struttura mantenendo il contenuto.\n"
            "5. LINGUA ITALIANA: Scrivi SEMPRE in italiano, indipendentemente dalla lingua dell'input.\n\n"
            f"RELAZIONE ATTUALE:\n{current_text}\n\n"
            f"ISTRUZIONI:\n{instructions}\n\n"
            "Fornisci la versione modificata della relazione, apportando solo le modifiche richieste "
            "preservando tutte le informazioni fattuali. Non inventare nuovi fatti."
        )
        
        # Prepare messages for API call
        messages = [
            {
                "role": "system", 
                "content": "Sei un esperto redattore di relazioni assicurative. Modifica i documenti secondo le modifiche richieste senza aggiungere nuove informazioni fattuali non presenti nell'originale. Non allucinare o inventare dettagli. Scrivi SEMPRE in italiano, indipendentemente dalla lingua dell'input."
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
            "NOTA: Impossibile applicare le modifiche. Il servizio AI ha riscontrato un errore. "
            "Si prega di riprovare più tardi."
        )


def generate_summary(text: str) -> str:
    """
    Generate a structured summary using Google Gemini via OpenRouter API.
    Ensures output is in the document's language, defaulting to Italian.

    Args:
        text (str): The text content to summarize.

    Returns:
        str: AI-generated summary or an error message.
    """
    if not settings.OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY is missing. Set it in your environment variables.")
        return "Errore: Chiave API mancante per OpenRouter."

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
                        {"role": "system", "content": "Sei un assistente AI che genera relazioni assicurative fattuali. Utilizza solo informazioni esplicitamente fornite nel testo di input. Non inventare o allucinare alcun dettaglio. Scrivi SEMPRE in italiano, indipendentemente dalla lingua dell'input."},
                        {"role": "user", "content": f"Riassumi i seguenti dettagli del caso assicurativo utilizzando SOLO FATTI - non aggiungere alcuna informazione non presente nel testo originale:\n\n{text}\n\nFornisci un riassunto conciso e fattuale utilizzando solo informazioni esplicitamente dichiarate nel testo. Se importanti dettagli sono mancanti, annotali come 'non specificati' piuttosto che inventare informazioni. Assicura chiarezza, accuratezza fattuale e un tono professionale. Scrivi SEMPRE in italiano."}
                    ],
                    "temperature": 0.3,
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
                    return "Errore: L'AI non ha generato un riassunto valido."
                return summary
            else:
                logger.warning(f"Unexpected API response format: {result}")
                return "Errore: L'AI ha restituito un formato di risposta imprevisto."
                
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from OpenRouter: {e.response.text}")
        return f"Errore: Richiesta API fallita con stato {e.response.status_code}."
    except Exception as e:
        logger.exception("Unexpected error in generate_summary function")
        return f"Errore: {str(e)}"
