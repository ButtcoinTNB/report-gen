#!/usr/bin/env python
import datetime
import glob
import os
import sys

# Add the parent directory to the Python path so we can import modules properly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now we can import from the backend modules
import argparse

from config import settings
from services.pdf_extractor import extract_text_from_file

from supabase import Client, create_client


def upload_reference_pdfs(directory_path):
    """
    Upload all PDF files from a directory to Supabase as reference reports
    """
    # Initialize Supabase client
    try:
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        print(f"Connected to Supabase at {settings.SUPABASE_URL}")
    except Exception as e:
        print(f"Error connecting to Supabase: {str(e)}")
        return False

    # Use existing templates bucket
    bucket_name = "templates"
    print(f"Using existing bucket: '{bucket_name}'")

    # Find all PDF files in the directory
    pdf_files = glob.glob(os.path.join(directory_path, "*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {directory_path}")
        return False

    print(f"Found {len(pdf_files)} PDF files to upload:")
    for pdf in pdf_files:
        print(f"  - {os.path.basename(pdf)}")

    # Upload each PDF file to Supabase
    success_count = 0
    for pdf_path in pdf_files:
        try:
            file_name = os.path.basename(pdf_path)
            print(f"\nUploading {file_name}...")

            # Extract text from the PDF
            text_content = extract_text_from_file(pdf_path)
            if not text_content or len(text_content) < 100:
                print(
                    f"Warning: {file_name} has very little text content ({len(text_content)} chars). Check the file."
                )
            else:
                print(
                    f"Extracted {len(text_content)} characters of text from {file_name}"
                )

            # Read file as binary for storage
            with open(pdf_path, "rb") as file:
                file_content = file.read()

            # Upload to Supabase Storage
            storage_path = f"{file_name}"
            storage_response = supabase.storage.from_(bucket_name).upload(
                storage_path, file_content, {"content-type": "application/pdf"}
            )

            if "error" in storage_response:
                print(f"Error uploading to storage: {storage_response['error']}")
                continue

            # Get public URL
            file_url = supabase.storage.from_(bucket_name).get_public_url(storage_path)

            # Add entry to database
            report_data = {
                "name": file_name,
                "file_path": storage_path,
                "url": file_url,
                "extracted_text": text_content,
                "created_at": str(datetime.datetime.now()),
            }

            response = supabase.table("reference_reports").insert(report_data).execute()

            if response.data:
                print(f"Successfully uploaded and registered {file_name}")
                success_count += 1
            else:
                print(f"Error inserting into database: {response}")

        except Exception as e:
            print(f"Error processing {os.path.basename(pdf_path)}: {str(e)}")

    print(
        f"\nUpload complete: {success_count} out of {len(pdf_files)} files uploaded successfully!"
    )
    return success_count > 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload reference PDFs to Supabase")
    parser.add_argument(
        "--dir",
        type=str,
        default="backend/reference_reports",
        help="Directory containing reference PDFs (default: backend/reference_reports)",
    )

    args = parser.parse_args()
    directory = args.dir

    if not os.path.exists(directory):
        print(f"Error: Directory {directory} does not exist")
        sys.exit(1)

    result = upload_reference_pdfs(directory)
    if result:
        print(
            "PDFs uploaded successfully! The AI will now use these as reference templates."
        )
    else:
        print("Failed to upload PDFs. Please check the errors above.")
