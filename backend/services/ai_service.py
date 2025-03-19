import httpx
from typing import List, Dict, Any, Callable, Optional
import os
import asyncio
from config import settings
from utils.error_handler import handle_exception, logger, retry_operation
import re
import json
from pathlib import Path
import time
import requests
from datetime import datetime


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
                    "Authorization": "Bearer " + settings.OPENROUTER_API_KEY,
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
                "API call failed (attempt " + str(attempt+1) + "/" + str(max_retries) + "): " + str(e)
            )
            
            if attempt < max_retries - 1:
                # Calculate backoff time: 2^attempt * 1 second (1, 2, 4, 8, ...)
                backoff_time = min(2 ** attempt, 10)  # Cap at 10 seconds
                logger.info("Retrying in " + str(backoff_time) + " seconds...")
                await asyncio.sleep(backoff_time)
            else:
                # This was the last attempt
                handle_exception(
                    e, 
                    "OpenRouter API call (after " + str(max_retries) + " attempts)",
                    default_status_code=503
                )
        except httpx.HTTPStatusError as e:
            # Handle HTTP error responses (4xx, 5xx)
            error_detail = "API returned " + str(e.response.status_code) + ": " + e.response.text
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


async def extract_template_variables(document_text: str, additional_info: str = "") -> Dict[str, Any]:
    """
    Extract variables from document text for use in templates.
    
    This function analyzes the document text and additional information to extract
    variables needed for report templates. It performs a two-step analysis: 
    1. First it analyzes the document to extract initial information
    2. Then it incorporates the user-provided information (which takes priority)
    
    Args:
        document_text: Text extracted from uploaded documents
        additional_info: Additional information provided by the user
        
    Returns:
        Dictionary containing template variables and analysis results
    """
    try:
        logger.info("Extracting template variables from document text")
        
        # First, try to extract structured data using pattern matching
        from services.pdf_extractor import extract_structured_data_from_text
        extracted_data = extract_structured_data_from_text(document_text)
        logger.info(f"Pattern matching extracted {len(extracted_data)} fields")
        
        # Build system prompt for AI extraction
        system_prompt = """
        Sei un assistente specializzato nell'analisi di documenti assicurativi e nell'estrazione di informazioni strutturate. 
        Il tuo compito è estrarre tutte le variabili rilevanti dai documenti forniti per popolare un template DOCX.
        
        ISTRUZIONI IMPORTANTI:
        1. Analizza attentamente il testo ed estrai TUTTE le informazioni che potrebbero essere utili per un report assicurativo.
        2. Se una informazione non è presente nel testo, indica "Non fornito" come valore.
        3. Riconosci e estrai informazioni come: numeri di polizza, date, nomi di aziende, indirizzi, descrizioni di sinistri, ecc.
        4. Fornisci i dati in formato JSON secondo lo schema specificato.
        5. Le variabili del template seguono il formato {{ nome_variabile }} e devono essere tutte popolate.
        6. Assicurati di estrarre correttamente nomi di aziende, indirizzi completi e informazioni finanziarie.
        
        SCHEMA DI OUTPUT:
        {
            "variables": {
                "nome_azienda": "Nome dell'azienda assicurata",
                "indirizzo_azienda": "Indirizzo completo dell'azienda",
                "cap": "Codice postale",
                "city": "Città",
                "data_oggi": "Data del giorno in formato italiano (es. 18 Marzo 2025)",
                "vs_rif": "Riferimento cliente",
                "rif_broker": "Riferimento broker",
                "polizza": "Numero polizza",
                "ns_rif": "Riferimento interno",
                "oggetto_polizza": "Oggetto della polizza",
                "assicurato": "Nome dell'assicurato",
                "data_sinistro": "Data del sinistro (formato GG/MM/AAAA)",
                "titolo_breve": "Breve descrizione del sinistro",
                "luogo_sinistro": "Luogo dove è avvenuto il sinistro",
                "merce": "Descrizione della merce coinvolta",
                "peso_merce": "Peso della merce",
                "doc_peso": "Documento attestante il peso",
                "valore_merce": "Valore della merce in formato monetario",
                "num_fattura": "Numero fattura",
                "data_fattura": "Data fattura",
                "data_luogo_intervento": "Data e luogo dell'intervento peritale",
                "dinamica_eventi": "Descrizione dettagliata della dinamica degli eventi",
                "foto_intervento": "Riferimento alle foto dell'intervento",
                "item1": "Prima voce di danno",
                "totale_item1": "Importo prima voce",
                "item2": "Seconda voce di danno",
                "totale_item2": "Importo seconda voce",
                "item3": "Terza voce di danno",
                "totale_item3": "Importo terza voce",
                "item4": "Quarta voce di danno",
                "totale_item4": "Importo quarta voce",
                "item5": "Quinta voce di danno",
                "totale_item5": "Importo quinta voce",
                "item6": "Sesta voce di danno",
                "totale_item6": "Importo sesta voce",
                "totale_danno": "Totale danno in formato monetario",
                "causa_danno": "Descrizione dettagliata della causa del danno",
                "lista_allegati": "Elenco degli allegati"
            },
            "fields_needing_attention": [
                "nome_campo1",
                "nome_campo2"
            ],
            "confidence": {
                "nome_campo1": 0.9,
                "nome_campo2": 0.5
            },
            "verification_needed": [
                "nome_campo1",
                "nome_campo2"
            ]
        }
        """
        
        # User prompt with the document and additional info
        user_prompt = f"""
        Analizza il seguente testo estratto da documenti assicurativi ed estrai tutte le variabili necessarie per un template di perizia.
        
        TESTO DEI DOCUMENTI:
        {document_text}
        
        INFORMAZIONI AGGIUNTIVE FORNITE DALL'UTENTE:
        {additional_info}
        
        Estrai tutte le variabili secondo lo schema richiesto. Per i campi non presenti inserisci "Non fornito" o un valore ragionevole basato sul contesto.
        Per le date mancanti, usa la data di oggi ({datetime.now().strftime('%d/%m/%Y')}) quando appropriato.
        Per i campi numerici mancanti, usa '0,00' o 'N/A' a seconda del contesto.
        Assicurati di distinguere tra informazioni estratte dai documenti e informazioni derivate o ipotizzate.
        """
        
        # Call OpenRouter API
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await call_openrouter_api(messages)
        
        if response and "choices" in response and len(response["choices"]) > 0:
            # Extract the generated response
            ai_response = response["choices"][0]["message"]["content"]
            
            # Parse the JSON from the response
            try:
                # Try to find and extract JSON from the response
                json_match = re.search(r'```(?:json)?(.*?)```', ai_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1).strip()
                else:
                    # If no code block, try to find JSON directly
                    json_str = ai_response.strip()
                    
                # Remove any markdown or text before or after the JSON
                start_idx = json_str.find('{')
                end_idx = json_str.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = json_str[start_idx:end_idx]
                
                extracted_data_ai = json.loads(json_str)
                
                # Make sure we have the expected structure
                if "variables" not in extracted_data_ai:
                    # If the AI returned a flat structure, wrap it
                    if isinstance(extracted_data_ai, dict):
                        extracted_data_ai = {"variables": extracted_data_ai}
                    else:
                        extracted_data_ai = {"variables": {}}
                        
                logger.info(f"AI extraction successful with {len(extracted_data_ai['variables'])} variables")
                
                # Merge pattern-matched data with AI-extracted data
                # Pattern-matched data takes precedence for specific fields
                for key, value in extracted_data.items():
                    if key not in extracted_data_ai["variables"] or not extracted_data_ai["variables"][key]:
                        extracted_data_ai["variables"][key] = value
                
                # Ensure all required template variables exist
                # This is the complete list of variables from the template
                required_variables = [
                    "nome_azienda", "indirizzo_azienda", "cap", "city", "data_oggi",
                    "vs_rif", "rif_broker", "polizza", "ns_rif", "oggetto_polizza",
                    "assicurato", "data_sinistro", "titolo_breve", "luogo_sinistro",
                    "merce", "peso_merce", "doc_peso", "valore_merce", "num_fattura",
                    "data_fattura", "data_luogo_intervento", "dinamica_eventi", 
                    "foto_intervento", "item1", "totale_item1", "item2", "totale_item2",
                    "item3", "totale_item3", "item4", "totale_item4", "item5", 
                    "totale_item5", "item6", "totale_item6", "totale_danno", 
                    "causa_danno", "lista_allegati"
                ]
                
                # Fill in any missing variables with default values
                for var in required_variables:
                    if var not in extracted_data_ai["variables"] or not extracted_data_ai["variables"][var]:
                        if "data" in var:
                            extracted_data_ai["variables"][var] = datetime.now().strftime("%d/%m/%Y")
                        elif "totale" in var:
                            extracted_data_ai["variables"][var] = "€ 0,00"
                        elif "item" in var:
                            extracted_data_ai["variables"][var] = "N/A"
                        else:
                            extracted_data_ai["variables"][var] = "Non fornito"
                
                # Add dynamically formatted date fields
                today = datetime.now()
                if "data_oggi" not in extracted_data_ai["variables"] or extracted_data_ai["variables"]["data_oggi"] == "Non fornito":
                    # Format date as "18 Marzo 2025"
                    months_italian = [
                        "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
                    ]
                    extracted_data_ai["variables"]["data_oggi"] = f"{today.day} {months_italian[today.month-1]} {today.year}"
                
                # Add a clean version of dynamic events for markdown parsing
                if "dinamica_eventi" in extracted_data_ai["variables"]:
                    events_text = extracted_data_ai["variables"]["dinamica_eventi"]
                    # Format as bullet points if not already
                    if not events_text.strip().startswith("- "):
                        lines = events_text.split("\n")
                        formatted_lines = []
                        for line in lines:
                            if line.strip():
                                formatted_lines.append(f"- {line.strip()}")
                        extracted_data_ai["variables"]["dinamica_eventi_accertamenti"] = "\n".join(formatted_lines)
                    else:
                        extracted_data_ai["variables"]["dinamica_eventi_accertamenti"] = events_text
                
                # Same for list of attachments
                if "lista_allegati" in extracted_data_ai["variables"]:
                    attachments_text = extracted_data_ai["variables"]["lista_allegati"]
                    if not attachments_text.strip().startswith("- "):
                        lines = attachments_text.split("\n")
                        formatted_lines = []
                        for line in lines:
                            if line.strip():
                                formatted_lines.append(f"- {line.strip()}")
                        extracted_data_ai["variables"]["lista_allegati"] = "\n".join(formatted_lines)
                
                return extracted_data_ai
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON from AI response: {str(e)}")
                logger.error(f"Response was: {ai_response}")
                # Fallback to a basic template with default values
                variables = {var: "Non fornito" for var in required_variables}
                return {"variables": variables, "fields_needing_attention": required_variables}
        
        logger.error("Failed to get usable response from OpenRouter API")
        # Return a basic set of variables
        return {
            "variables": {
                "nome_azienda": "Non fornito",
                "indirizzo_azienda": "Non fornito",
                "cap": "Non fornito",
                "city": "Non fornito",
                "data_oggi": datetime.now().strftime("%d/%m/%Y"),
                "vs_rif": "Non fornito",
                "rif_broker": "Non fornito",
                "polizza": "Non fornito",
                "ns_rif": "Non fornito",
                "oggetto_polizza": "Non fornito",
                "assicurato": "Non fornito",
                "data_sinistro": "Non fornito",
                "titolo_breve": "Non fornito",
                "luogo_sinistro": "Non fornito",
                "merce": "Non fornito",
                "peso_merce": "Non fornito",
                "doc_peso": "Non fornito",
                "valore_merce": "Non fornito",
                "num_fattura": "Non fornito",
                "data_fattura": "Non fornito",
                "data_luogo_intervento": "Non fornito",
                "dinamica_eventi": "Non fornito",
                "dinamica_eventi_accertamenti": "- Non fornito",
                "foto_intervento": "Non fornito",
                "item1": "Non fornito",
                "totale_item1": "€ 0,00",
                "item2": "Non fornito",
                "totale_item2": "€ 0,00",
                "item3": "Non fornito",
                "totale_item3": "€ 0,00",
                "item4": "Non fornito",
                "totale_item4": "€ 0,00",
                "item5": "Non fornito",
                "totale_item5": "€ 0,00",
                "item6": "Non fornito",
                "totale_item6": "€ 0,00",
                "totale_danno": "€ 0,00",
                "causa_danno": "Non fornito",
                "lista_allegati": "- Non fornito"
            },
            "fields_needing_attention": []
        }
        
    except Exception as e:
        handle_exception(e, "Template variable extraction")
        # Return a basic set of variables on error
        return {
            "variables": {
                "nome_azienda": "Non fornito",
                "indirizzo_azienda": "Non fornito",
                "cap": "Non fornito",
                "city": "Non fornito",
                "data_oggi": datetime.now().strftime("%d/%m/%Y"),
                "vs_rif": "Non fornito",
                "rif_broker": "Non fornito",
                "polizza": "Non fornito",
                "ns_rif": "Non fornito",
                "oggetto_polizza": "Non fornito",
                "assicurato": "Non fornito",
                "data_sinistro": "Non fornito",
                "titolo_breve": "Non fornito",
                "luogo_sinistro": "Non fornito",
                "merce": "Non fornito",
                "peso_merce": "Non fornito",
                "doc_peso": "Non fornito",
                "valore_merce": "Non fornito",
                "num_fattura": "Non fornito",
                "data_fattura": "Non fornito",
                "data_luogo_intervento": "Non fornito",
                "dinamica_eventi": "Non fornito",
                "dinamica_eventi_accertamenti": "- Non fornito",
                "foto_intervento": "Non fornito",
                "item1": "Non fornito",
                "totale_item1": "€ 0,00",
                "item2": "Non fornito",
                "totale_item2": "€ 0,00",
                "item3": "Non fornito",
                "totale_item3": "€ 0,00",
                "item4": "Non fornito",
                "totale_item4": "€ 0,00",
                "item5": "Non fornito",
                "totale_item5": "€ 0,00",
                "item6": "Non fornito",
                "totale_item6": "€ 0,00",
                "totale_danno": "€ 0,00",
                "causa_danno": "Non fornito",
                "lista_allegati": "- Non fornito"
            },
            "error": str(e),
            "fields_needing_attention": []
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
            logger.error("Error loading style analysis cache: " + str(e))
            self._cache = {}
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Error saving style analysis cache: " + str(e))
    
    def get_cache_key(self, reference_paths: List[str]) -> str:
        """Generate a cache key based on file paths and modification times."""
        key_parts = []
        for path in sorted(reference_paths):
            try:
                mtime = Path(path).stat().st_mtime
                key_parts.append(path + ":" + str(mtime))
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
        # Avoid f-strings entirely for this section - concatenate parts safely
        joined_reports = "\n\n".join(["=== Report " + str(i+1) + " ===\n" + text for i, text in enumerate(reference_texts)])
        
        analysis_prompt = (
            "Sei un esperto analista di documenti assicurativi. Analizza questi report di riferimento "
            "per identificare il formato, lo stile e il tono di voce comuni. "
            "NON analizzare il contenuto specifico, ma solo gli elementi stilistici e strutturali.\n\n"
            "REPORT DI RIFERIMENTO:\n\n" +
            joined_reports + "\n\n"
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
            "style_guide_json": style_guide_json  # Store for later use
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
            
        logger.info("Extracted " + str(len(document_text)) + " characters from uploaded documents")
        
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
                    str(path_obj) for path_obj in dir_path.glob("*.pdf")
                ])
        
        if not reference_reports:
            raise ValueError("No reference reports found for style analysis")
            
        # Analyze reference reports for style and format
        style_analysis = await analyze_reference_reports(reference_reports)
        
        # Extract template variables from the documents and additional info
        template_variables = await extract_template_variables(document_text, additional_info)
        logger.info("Successfully extracted template variables")
        
        # Create the generation prompt using the template from style analysis
        # Use standard string format to avoid any f-string backslash issues
        generation_prompt = style_analysis["prompt_template"].format(
            style_guide_json=style_analysis["style_guide_json"],  # Use pre-dumped JSON
            content=document_text,
            additional_info=additional_info,
            livello_formalita=style_analysis["style_guide"]["stile"]["livello_formalita"],
            date=style_analysis["style_guide"]["formattazione"]["date"],
            importi=style_analysis["style_guide"]["formattazione"]["importi"],
            riferimenti=style_analysis["style_guide"]["formattazione"]["riferimenti"]
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
            logger.error("Unexpected API response format: " + str(result))
            raise ValueError("Errore nella generazione del report")
            
    except Exception as e:
        logger.error("Error in generate_report_text: " + str(e))
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
            "RELAZIONE ORIGINALE:\n" + original_text + "\n\n"
            "ISTRUZIONI DELL'UTENTE:\n" + instructions + "\n\n"
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
            logger.error("Unexpected API response format: " + str(result))
            raise ValueError("Errore durante la modifica del report")
            
    except Exception as e:
        logger.error("Error in refine_report_text: " + str(e))
        raise ValueError("Impossibile modificare il report: " + str(e))
