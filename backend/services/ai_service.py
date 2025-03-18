import httpx
from typing import List, Dict, Any, Callable, Optional
import os
import asyncio
from config import settings
from utils.error_handler import handle_exception, logger, retry_operation
import re
import json
from pathlib import Path


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


async def extract_template_variables(document_text: str, additional_info: str = "") -> Dict[str, Any]:
    """
    Extract variables needed for the report template from document text and additional user information.
    The function performs a two-step analysis:
    1. First analyzes documents to extract initial information
    2. Then incorporates user's additional information, giving it priority
    
    Args:
        document_text: Text extracted from uploaded documents
        additional_info: Additional information provided by the user
        
    Returns:
        Dictionary containing template variables and analysis results
    """
    try:
        # Step 1: Initial document analysis
        initial_prompt = (
            "Sei un esperto analista di documenti assicurativi. Analizza il seguente testo per estrarre "
            "informazioni rilevanti per un report assicurativo. Per ogni campo, indica anche il livello "
            "di confidenza dell'informazione estratta (ALTA/MEDIA/BASSA) e se sono necessarie ulteriori informazioni.\n\n"
            "DOCUMENTI ORIGINALI:\n"
            f"{document_text}\n\n"
            "Estrai le seguenti informazioni nel formato JSON:\n"
            "{\n"
            '  "nome_azienda": {"valore": "Nome dell\'azienda", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "indirizzo_azienda": {"valore": "Indirizzo", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "cap": {"valore": "CAP", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "city": {"valore": "Città", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "vs_rif": {"valore": "Riferimento cliente", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "rif_broker": {"valore": "Riferimento broker", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "polizza": {"valore": "Numero polizza", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "ns_rif": {"valore": "Riferimento interno", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "dinamica_eventi_accertamenti": {"valore": "Descrizione eventi", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "foto_intervento": {"valore": "Descrizione foto", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "causa_danno": {"valore": "Causa del danno", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "item1": {"valore": "Prima voce danno", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "totale_item1": {"valore": "Importo primo danno", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "item2": {"valore": "Seconda voce danno", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "totale_item2": {"valore": "Importo secondo danno", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "item3": {"valore": "Terza voce danno", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "totale_item3": {"valore": "Importo terzo danno", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "item4": {"valore": "Quarta voce danno", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "totale_item4": {"valore": "Importo quarto danno", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "item5": {"valore": "Quinta voce danno", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "totale_item5": {"valore": "Importo quinto danno", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "item6": {"valore": "Sesta voce danno", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "totale_item6": {"valore": "Importo sesto danno", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "totale_danno": {"valore": "Totale danni", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false},\n'
            '  "lista_allegati": {"valore": "Elenco allegati", "confidenza": "ALTA/MEDIA/BASSA", "richiede_verifica": true/false}\n'
            "}\n\n"
            "ISTRUZIONI IMPORTANTI:\n"
            "1. ANALISI ACCURATA: Analizza attentamente il contenuto per trovare le informazioni rilevanti\n"
            "2. LIVELLO CONFIDENZA: Indica ALTA se l'informazione è chiaramente presente e affidabile, "
            "MEDIA se è deducibile ma non esplicita, BASSA se è incerta o poco chiara\n"
            "3. RICHIEDE VERIFICA: Indica true se l'informazione necessita di verifica o completamento\n"
            "4. FORMATO IMPORTI: Converti tutti gli importi in formato numerico (es. '1250.00')\n"
            "5. NO INVENZIONI: Se un'informazione non è presente, usa 'Non fornito' come valore"
        )

        # Call API for initial analysis
        initial_result = await call_openrouter_api(
            messages=[
                {
                    "role": "system",
                    "content": "Sei un esperto analista di documenti assicurativi specializzato nell'estrazione "
                              "di informazioni con valutazione della confidenza. Analizza attentamente i documenti "
                              "e indica quali informazioni necessitano di verifica o completamento."
                },
                {"role": "user", "content": initial_prompt}
            ],
            timeout=45.0
        )

        # Process initial analysis
        if not (
            initial_result
            and "choices" in initial_result
            and len(initial_result["choices"]) > 0
            and "message" in initial_result["choices"][0]
            and "content" in initial_result["choices"][0]["message"]
        ):
            logger.error(f"Unexpected API response format in initial analysis: {initial_result}")
            return {}

        # Extract initial variables with confidence levels
        initial_analysis = json.loads(
            re.search(r'\{[\s\S]*\}', initial_result["choices"][0]["message"]["content"]).group(0)
        )

        # Step 2: If additional info is provided, incorporate it
        if additional_info.strip():
            merge_prompt = (
                "Sei un esperto analista di documenti assicurativi. Hai già analizzato i documenti originali "
                "e ora devi incorporare le informazioni aggiuntive fornite dall'utente. Le informazioni dell'utente "
                "hanno priorità sui dati estratti dai documenti.\n\n"
                "ANALISI INIZIALE:\n"
                f"{json.dumps(initial_analysis, indent=2, ensure_ascii=False)}\n\n"
                "INFORMAZIONI AGGIUNTIVE DELL'UTENTE:\n"
                f"{additional_info}\n\n"
                "Fornisci il JSON finale aggiornato mantenendo la stessa struttura ma:\n"
                "1. Aggiorna i valori con le informazioni dell'utente dove fornite\n"
                "2. Imposta confidenza=ALTA per i campi forniti dall'utente\n"
                "3. Imposta richiede_verifica=false per i campi forniti dall'utente\n"
                "4. Mantieni i valori originali per i campi non menzionati dall'utente"
            )

            # Call API for merging information
            merge_result = await call_openrouter_api(
                messages=[
                    {
                        "role": "system",
                        "content": "Sei un esperto analista incaricato di combinare l'analisi iniziale "
                                  "con le informazioni aggiuntive dell'utente, dando priorità a queste ultime."
                    },
                    {"role": "user", "content": merge_prompt}
                ],
                timeout=45.0
            )

            if (
                merge_result
                and "choices" in merge_result
                and len(merge_result["choices"]) > 0
                and "message" in merge_result["choices"][0]
                and "content" in merge_result["choices"][0]["message"]
            ):
                try:
                    merged_analysis = json.loads(
                        re.search(r'\{[\s\S]*\}', merge_result["choices"][0]["message"]["content"]).group(0)
                    )
                    initial_analysis = merged_analysis
                except Exception as e:
                    logger.error(f"Error parsing merged analysis: {str(e)}")

        # Post-process the variables
        final_variables = {}
        fields_needing_attention = []
        
        # Add current date
        from datetime import datetime
        final_variables["data_oggi"] = datetime.now().strftime("%d/%m/%Y")

        # Process each field
        for field, data in initial_analysis.items():
            value = data["valore"]
            confidence = data["confidenza"]
            needs_verification = data["richiede_verifica"]

            # Handle amount fields
            if field.startswith("totale_") and value != "Non fornito":
                try:
                    # Handle different number formats
                    amount_str = str(value).replace('€', '').strip()
                    if ',' in amount_str and '.' in amount_str:
                        if amount_str.index('.') < amount_str.index(','):
                            amount_str = amount_str.replace('.', '').replace(',', '.')
                        else:
                            amount_str = amount_str.replace(',', '')
                    elif ',' in amount_str:
                        amount_str = amount_str.replace(',', '.')
                    
                    amount = float(amount_str)
                    final_variables[field] = f"{amount:.2f}"
                except (ValueError, TypeError):
                    final_variables[field] = "0.00"
                    if confidence != "ALTA":
                        fields_needing_attention.append(f"Verifica importo per {field}")
            else:
                final_variables[field] = value

            # Track fields needing attention
            if needs_verification or confidence in ["BASSA", "MEDIA"]:
                fields_needing_attention.append(
                    f"Verifica {field}: confidenza {confidence.lower()}"
                )

        # Calculate total if needed
        if final_variables["totale_danno"] == "Non fornito" or final_variables["totale_danno"] == "0.00":
            total = 0.0
            has_items = False
            for i in range(1, 7):
                item_total = final_variables[f"totale_item{i}"]
                if item_total != "Non fornito":
                    try:
                        total += float(str(item_total))
                        has_items = True
                    except (ValueError, TypeError):
                        continue
            if has_items:
                final_variables["totale_danno"] = f"{total:.2f}"

        return {
            "variables": final_variables,
            "fields_needing_attention": fields_needing_attention,
            "analysis_details": initial_analysis  # Include full analysis for UI feedback
        }

    except Exception as e:
        logger.error(f"Error extracting template variables: {str(e)}")
        return {
            "variables": {},
            "fields_needing_attention": ["Errore nell'analisi dei documenti"],
            "analysis_details": {}
        }


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
                with open(self._cache_file, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
        except Exception as e:
            logger.error(f"Error loading style analysis cache: {str(e)}")
            self._cache = {}
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving style analysis cache: {str(e)}")
    
    def get_cache_key(self, reference_paths: List[str]) -> str:
        """Generate a cache key based on file paths and modification times."""
        key_parts = []
        for path in sorted(reference_paths):
            try:
                mtime = Path(path).stat().st_mtime
                key_parts.append(f"{path}:{mtime}")
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
    Analyze reference reports to extract format, style, and tone of voice patterns.
    Uses caching to improve performance when analyzing the same set of reports multiple times.
    
    Args:
        reference_paths: List of paths to reference report files
        
    Returns:
        Dictionary containing style guide and format patterns
    """
    try:
        # Check cache first
        cache_key = style_cache.get_cache_key(reference_paths)
        cached_analysis = style_cache.get(cache_key)
        
        if cached_analysis:
            logger.info("Using cached style analysis")
            return cached_analysis
        
        # Extract text from reference reports
        from services.pdf_extractor import extract_text_from_file
        reference_texts = []
        
        for path in reference_paths:
            text = extract_text_from_file(path)
            if text and len(text.strip()) > 0:
                reference_texts.append(text)
        
        if not reference_texts:
            raise ValueError("No valid reference reports found for analysis")
        
        # Create prompt for analyzing style and format
        analysis_prompt = (
            "Sei un esperto analista di documenti assicurativi. Analizza questi report di riferimento "
            "per identificare il formato, lo stile e il tono di voce comuni. "
            "NON analizzare il contenuto specifico, ma solo gli elementi stilistici e strutturali.\n\n"
            "REPORT DI RIFERIMENTO:\n\n"
            f"{chr(10).join(['=== Report ' + str(i+1) + ' ===\n' + text + '\n\n' for i, text in enumerate(reference_texts)])}\n\n"
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
            '  },\n'
            '  "stile": {\n'
            '    "livello_formalita": "alto/medio/basso",\n'
            '    "caratteristiche": ["frasi brevi/lunghe", "uso di tecnicismi", "struttura paragrafi"],\n'
            '    "pattern_sintattici": ["Si attesta che...", "Si è proceduto a..."]\n'
            '  },\n'
            '  "tono": {\n'
            '    "caratteristiche": ["professionale", "distaccato", "tecnico"],\n'
            '    "esempi": ["esempio frase 1", "esempio frase 2"]\n'
            '  },\n'
            '  "formattazione": {\n'
            '    "date": "GG/MM/AAAA",\n'
            '    "importi": "€ X.XXX,XX",\n'
            '    "riferimenti": "Rif: XXXXX"\n'
            '  },\n'
            '  "frasi_comuni": {\n'
            '    "apertura": ["frase apertura 1", "frase apertura 2"],\n'
            '    "chiusura": ["frase chiusura 1", "frase chiusura 2"],\n'
            '    "transizioni": ["inoltre", "pertanto", "in conclusione"]\n'
            '  }\n'
            "}"
        )
        
        # Get style analysis from AI
        result = await call_openrouter_api(
            messages=[
                {
                    "role": "system",
                    "content": "Sei un esperto analista di stile e formato di documenti assicurativi. "
                              "Analizza i documenti di riferimento per estrarre pattern di stile precisi, "
                              "NON contenuto specifico. Fornisci esempi concreti e pattern esatti."
                },
                {"role": "user", "content": analysis_prompt}
            ],
            timeout=60.0
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
            re.search(r'\{[\s\S]*\}', result["choices"][0]["message"]["content"]).group(0)
        )
        
        # Create a prompt template for report generation
        prompt_template = (
            "GUIDA DI STILE E FORMATO:\n"
            f"{json.dumps(style_guide, indent=2, ensure_ascii=False)}\n\n"
            "ISTRUZIONI PRECISE:\n"
            "1. Usa ESATTAMENTE la struttura delle sezioni fornita, nell'ordine specificato\n"
            "2. Mantieni il livello di formalità indicato ({stile[livello_formalita]})\n"
            "3. Utilizza le frasi comuni fornite per apertura, chiusura e transizioni\n"
            "4. Segui ESATTAMENTE i pattern di formattazione per:\n"
            "   - Date: {formattazione[date]}\n"
            "   - Importi: {formattazione[importi]}\n"
            "   - Riferimenti: {formattazione[riferimenti]}\n"
            "5. Usa i pattern sintattici e il tono forniti negli esempi\n\n"
            "CONTENUTO DA ELABORARE:\n"
            "{content}\n\n"
            "INFORMAZIONI AGGIUNTIVE:\n"
            "{additional_info}\n\n"
            "Genera un report che segue ESATTAMENTE questo stile e formato, utilizzando il contenuto fornito."
        )
        
        analysis_result = {
            "style_guide": style_guide,
            "prompt_template": prompt_template
        }
        
        # Cache the result
        style_cache.set(cache_key, analysis_result)
        logger.info("Cached new style analysis")
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error analyzing reference reports: {str(e)}")
        raise ValueError(f"Impossibile analizzare i report di riferimento: {str(e)}")


async def generate_report_text(
    document_paths: List[str],
    additional_info: str = "",
    template_id: int = None
) -> Dict[str, Any]:
    """
    Generate a report based on uploaded documents and additional user information.
    Uses style and format from reference reports.
    
    Args:
        document_paths: List of paths to the uploaded documents
        additional_info: Additional information provided by the user
        template_id: ID of the template to use for formatting
        
    Returns:
        Dictionary containing report text and template variables
    """
    try:
        # Extract text from input documents
        from services.pdf_extractor import extract_text_from_files
        document_text = extract_text_from_files(document_paths)
        
        if not document_text or len(document_text.strip()) < 10:
            return {
                "error": "Nessun testo leggibile è stato estratto dai documenti forniti.",
                "template_variables": {}
            }
            
        logger.info(f"Extracted {len(document_text)} characters from uploaded documents")
        
        # Get reference reports
        reference_reports = []
        reference_dirs = [
            Path("backend/reference_reports"),
            Path("reference_reports"),
            Path(settings.UPLOAD_DIR) / "templates"
        ]
        
        for dir_path in reference_dirs:
            if dir_path.exists():
                reference_reports.extend([
                    str(f) for f in dir_path.glob("*.pdf")
                ])
        
        if not reference_reports:
            raise ValueError("No reference reports found for style analysis")
            
        # Analyze reference reports for style and format
        style_analysis = await analyze_reference_reports(reference_reports)
        
        # Extract template variables from the documents and additional info
        template_variables = await extract_template_variables(document_text, additional_info)
        logger.info("Successfully extracted template variables")
        
        # Create the generation prompt using the template from style analysis
        generation_prompt = style_analysis["prompt_template"].format(
            content=document_text,
            additional_info=additional_info
        )
        
        # Generate the report content
        result = await call_openrouter_api(
            messages=[
                {
                    "role": "system",
                    "content": "Sei un esperto redattore di relazioni assicurative. "
                              "Genera il report seguendo ESATTAMENTE il formato e lo stile forniti, "
                              "utilizzando SOLO le informazioni dai documenti dell'utente."
                },
                {"role": "user", "content": generation_prompt}
            ],
            timeout=60.0
        )
        
        if (
            result
            and "choices" in result
            and len(result["choices"]) > 0
            and "message" in result["choices"][0]
            and "content" in result["choices"][0]["message"]
        ):
            report_content = result["choices"][0]["message"]["content"]
            
            return {
                "report_text": report_content,
                "template_variables": template_variables["variables"],
                "fields_needing_attention": template_variables.get("fields_needing_attention", []),
                "style_guide": style_analysis["style_guide"]  # Include style guide for reference
            }
        else:
            raise ValueError("Errore nella generazione del report")
            
    except Exception as e:
        logger.error(f"Error in generate_report_text: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "error": "Impossibile generare il report. Si è verificato un errore.",
            "template_variables": {}
        }


async def refine_report_text(report_path: str, instructions: str) -> str:
    """
    Refine a report based on user instructions.
    
    Args:
        report_path: Path to the original report file
        instructions: User instructions for refinement
        
    Returns:
        Refined report text
    """
    try:
        # Extract text from the original report
        from services.pdf_extractor import extract_text_from_file
        original_text = extract_text_from_file(report_path)
        
        if not original_text:
            raise ValueError("Could not extract text from original report")
        
        # Create prompt for refinement
        prompt = (
            "Sei un esperto redattore di relazioni assicurative. Il tuo compito è modificare una relazione "
            "esistente seguendo le istruzioni dell'utente. Segui queste regole rigorose:\n\n"
            "1. MANTIENI I FATTI: Non rimuovere o alterare informazioni fattuali come date, importi, o dettagli specifici.\n"
            "2. NESSUNA INVENZIONE: Non aggiungere nuove informazioni fattuali non presenti nell'originale.\n"
            "3. SOLO MODIFICHE RICHIESTE: Apporta solo le modifiche specificamente richieste nelle istruzioni.\n"
            "4. MIGLIORA LA CHIAREZZA: Puoi migliorare la struttura e la chiarezza mantenendo il contenuto originale.\n"
            "5. MANTIENI IL FORMATO: Preserva il formato del documento, inclusi titoli e sezioni.\n\n"
            f"RELAZIONE ORIGINALE:\n{original_text}\n\n"
            f"ISTRUZIONI DELL'UTENTE:\n{instructions}\n\n"
            "Fornisci la versione modificata della relazione, mantenendo tutte le informazioni fattuali "
            "e apportando solo le modifiche richieste."
        )
        
        # Call OpenRouter API
        result = await call_openrouter_api(
            messages=[
                {
                    "role": "system",
                    "content": "Sei un esperto redattore di relazioni assicurative. Modifica i documenti secondo le "
                              "istruzioni mantenendo accuratezza e professionalità. Non inventare nuovi fatti."
                },
                {"role": "user", "content": prompt}
            ],
            timeout=45.0
        )
        
        if (
            result
            and "choices" in result
            and len(result["choices"]) > 0
            and "message" in result["choices"][0]
            and "content" in result["choices"][0]["message"]
        ):
            refined_text = result["choices"][0]["message"]["content"]
            
            # Validate the refined text
            if len(refined_text) < len(original_text) * 0.5:
                logger.warning("Refined text is significantly shorter than original")
                raise ValueError("La versione modificata sembra incompleta")
                
            return refined_text
        else:
            logger.error(f"Unexpected API response format: {result}")
            raise ValueError("Errore durante la modifica del report")
            
    except Exception as e:
        logger.error(f"Error in refine_report_text: {str(e)}")
        raise ValueError(f"Impossibile modificare il report: {str(e)}")
