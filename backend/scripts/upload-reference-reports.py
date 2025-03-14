import os
import fitz  # PyMuPDF
import requests
from config import SUPABASE_URL, SUPABASE_KEY


def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    doc = fitz.open(pdf_path)
    text = "\n".join([page.get_text() for page in doc])
    return text


def store_in_supabase(report_name, extracted_text):
    """Stores extracted report text in Supabase."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    data = {"report_name": report_name, "extracted_text": extracted_text}

    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/reference_reports", json=data, headers=headers
    )

    if response.status_code == 201:
        print(f"✅ Successfully uploaded {report_name}")
    else:
        print(f"❌ Failed to upload {report_name}: {response.text}")


def process_reports(folder_path):
    """Processes all PDFs in the given folder and stores them in Supabase."""
    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(folder_path, filename)
            extracted_text = extract_text_from_pdf(pdf_path)
            store_in_supabase(filename, extracted_text)


if __name__ == "__main__":
    folder = "backend/reference_reports/"  # Place your reference PDFs here
    process_reports(folder)
