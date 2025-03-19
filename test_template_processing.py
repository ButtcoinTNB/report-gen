#!/usr/bin/env python3
"""
Test script for template processing using docxtpl

This script demonstrates how to use the template processor to generate
a DOCX file from a template with variables extracted from text.
"""

import os
import sys
from pathlib import Path
import argparse
import json
from docxtpl import DocxTemplate, RichText

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process DOCX templates with variables")
    parser.add_argument("--template", "-t", required=True, help="Path to template.docx file")
    parser.add_argument("--output", "-o", default="output.docx", help="Output file path (default: output.docx)")
    parser.add_argument("--variables", "-v", help="Path to JSON file with variables (optional)")
    args = parser.parse_args()
    
    # Check if template exists
    if not os.path.exists(args.template):
        print(f"Error: Template file not found: {args.template}")
        return 1
    
    # If JSON file is provided, load variables from it
    variables = {}
    if args.variables and os.path.exists(args.variables):
        with open(args.variables, "r", encoding="utf-8") as f:
            try:
                variables = json.load(f)
                print(f"Loaded {len(variables)} variables from {args.variables}")
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON file: {str(e)}")
                return 1
    else:
        # Use example variables
        print("Using example variables")
        variables = {
            "nome_azienda": "Transmec Ro SRL",
            "indirizzo_azienda": "Via delle Spedizioni 23",
            "cap": "16121",
            "city": "Genova",
            "data_oggi": "18 Marzo 2025",
            "vs_rif": "2025-210",
            "rif_broker": "2025-4301",
            "polizza": "98765",
            "ns_rif": "210/25",
            "oggetto_polizza": "Gruppo Logistico",
            "assicurato": "Transmec Ro",
            "data_sinistro": "10/03/2025",
            "titolo_breve": "Danneggiamento Macchinario",
            "luogo_sinistro": "Italia / Germania",
            "merce": "10 pallets di macchinari industriali",
            "peso_merce": "8.250 kg",
            "doc_peso": "CMR",
            "valore_merce": "€ 45.320,00",
            "num_fattura": "IT-2025-104",
            "data_fattura": "11/03/2025",
            "data_luogo_intervento": "15/03/2025 c/o deposito Transmec Ro",
            "dinamica_eventi": "Il macchinario è stato caricato su un semirimorchio senza un adeguato fissaggio.",
            "dinamica_eventi_accertamenti": """
                - Il macchinario è stato caricato su un semirimorchio senza un adeguato fissaggio.
                - Durante il trasporto, si è verificato un sobbalzo che ha causato il movimento del carico.
                - All'arrivo presso il destinatario, è stato notato che il macchinario aveva subito danni strutturali.
                - La richiesta di risarcimento è stata presentata in data 12/03/2025.
            """,
            "foto_intervento": "N/A",
            "item1": "Riparazione asse X",
            "totale_item1": "€ 2.500,00",
            "item2": "Sostituzione guida lineare",
            "totale_item2": "€ 1.800,00",
            "item3": "Verifica elettronica",
            "totale_item3": "€ 600,00",
            "item4": "Olio idraulico",
            "totale_item4": "€ 150,00",
            "item5": "Manodopera specializzata",
            "totale_item5": "€ 1.000,00",
            "item6": "Test di funzionamento",
            "totale_item6": "€ 450,00",
            "totale_danno": "€ 6.500,00",
            "causa_danno": """
                Il danno è stato causato da una sistemazione inadeguata del carico durante il trasporto.
                Il macchinario non è stato fissato correttamente, risultando in uno spostamento durante il viaggio.
            """,
            "lista_allegati": """
                - Incarico peritale
                - Denuncia di sinistro
                - Incarico di trasporto
                - Fattura merce
                - Fatture riparazione
                - Documentazione fotografica
            """
        }
    
    # Process variables that should be rich text
    rich_text_fields = ["dinamica_eventi_accertamenti", "causa_danno", "lista_allegati"]
    for field in rich_text_fields:
        if field in variables:
            text = variables[field]
            rt = RichText()
            
            # Handle bullet points
            if "- " in text:
                lines = text.split("\n")
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line.startswith("- "):
                        content = line[2:]
                        rt.add("\u2022 ", bold=True)  # Unicode bullet point
                        rt.add(content)
                        if i < len(lines) - 1:
                            rt.add("\n")
            else:
                rt.add(text)
                
            variables[field] = rt
    
    # Load the template
    doc = DocxTemplate(args.template)
    
    # Check undeclared variables in the template
    undeclared_vars = doc.get_undeclared_template_variables()
    print(f"Template has {len(undeclared_vars)} variables: {', '.join(undeclared_vars)}")
    
    # Check for missing variables
    missing_vars = [var for var in undeclared_vars if var not in variables]
    if missing_vars:
        print(f"Warning: {len(missing_vars)} variables are missing: {', '.join(missing_vars)}")
        
        # Add placeholders for missing variables
        for var in missing_vars:
            variables[var] = f"[{var}]"
    
    # Render the template
    doc.render(variables)
    
    # Save the output
    doc.save(args.output)
    print(f"Successfully generated {args.output}")
    
    return 0
    
if __name__ == "__main__":
    sys.exit(main()) 