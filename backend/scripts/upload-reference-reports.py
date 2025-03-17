import os
import sys
import fitz  # PyMuPDF
import requests

# Add the parent directory to the Python path so we can import the config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Now import from the settings object
from config import settings

# Use settings instead of direct import
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY


def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        
        # Process each page and extract text
        for i, page in enumerate(doc):
            page_text = page.get_text()
            text += f"\n\n--- PAGE {i+1} ---\n\n{page_text}"
            
        print(f"  - Extracted {len(text)} characters from {len(doc)} pages")
        return text
    except Exception as e:
        print(f"  - Error extracting text from {pdf_path}: {str(e)}")
        return None


def store_in_supabase(report_name, extracted_text):
    """Stores extracted report text in Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: Supabase credentials not configured")
        print("Please set SUPABASE_URL and SUPABASE_KEY in your .env file")
        return False
    
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }

        data = {"report_name": report_name, "extracted_text": extracted_text}

        print(f"  - Uploading to Supabase: {report_name} ({len(extracted_text)} characters)")
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/reference_reports", json=data, headers=headers
        )

        if response.status_code == 201:
            print(f"✅ Successfully uploaded {report_name}")
            return True
        else:
            print(f"❌ Failed to upload {report_name}: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error uploading {report_name}: {str(e)}")
        return False


def process_reports(folder_path):
    """Processes all PDFs in the given folder and stores them in Supabase."""
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("No PDF files found in the specified folder.")
        return
    
    print(f"\nProcessing {len(pdf_files)} PDF files...")
    
    for i, filename in enumerate(pdf_files):
        print(f"\n[{i+1}/{len(pdf_files)}] Processing: {filename}")
        pdf_path = os.path.join(folder_path, filename)
        
        # Check file size
        file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # Size in MB
        if file_size > 30:  # Skip files larger than 10MB
            print(f"  - Skipping (file too large): {file_size:.2f} MB")
            skipped_count += 1
            continue
            
        # Extract text
        extracted_text = extract_text_from_pdf(pdf_path)
        
        if not extracted_text:
            error_count += 1
            continue
            
        # Upload to Supabase
        if store_in_supabase(filename, extracted_text):
            success_count += 1
        else:
            error_count += 1
    
    # Print summary
    print(f"\n=== Summary ===")
    print(f"Total processed: {len(pdf_files)}")
    print(f"Successfully uploaded: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Skipped (too large): {skipped_count}")
    
    if success_count > 0:
        print("\n✅ Reference reports uploaded successfully to Supabase!")
        print("These will now be used as formatting templates for generating insurance reports.")
    else:
        print("\n❌ No reports were successfully uploaded.")
        print("Please check your PDF files and Supabase credentials and try again.")


if __name__ == "__main__":
    # Default folder path
    default_folder = "backend/reference_reports/"
    
    # Check if the default folder exists, if not try alternative paths
    if not os.path.exists(default_folder):
        alternative_paths = [
            "reference_reports/",                     # Try root level folder
            "../reference_reports/",                  # Try parent directory
            os.path.join(settings.UPLOAD_DIR, "templates/")  # Try in the uploads directory
        ]
        
        for path in alternative_paths:
            if os.path.exists(path):
                folder = path
                print(f"Using reference reports folder: {os.path.abspath(folder)}")
                break
        else:
            folder = default_folder
            print(f"Warning: Reference reports folder {os.path.abspath(folder)} not found.")
            print("Please create this directory and add your PDF reference reports.")
            print("You can also specify a custom path when running this script.")
    else:
        folder = default_folder
        print(f"Using reference reports folder: {os.path.abspath(folder)}")
    
    # Check if the folder has any PDF files
    pdf_files = [f for f in os.listdir(folder) if f.lower().endswith('.pdf')] if os.path.exists(folder) else []
    
    if not pdf_files:
        print("No PDF files found in the reference reports folder.")
        print("Please add your reference report PDFs to the folder and run this script again.")
    else:
        print(f"Found {len(pdf_files)} PDF files: {', '.join(pdf_files)}")
        process_reports(folder)
